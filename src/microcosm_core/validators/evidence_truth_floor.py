"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.validators.evidence_truth_floor` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: CHECKER_ID, EVIDENCE_CLASS_REGISTRY_REL, ORGAN_REGISTRY_REL, FIRST_WAVE_RECEIPTS_REL, FIXTURE_ECHO_CLASS, REAL_RUNTIME_STATUS, REAL_RUNTIME_CLASSIFICATION, ALLOWED_REAL_SUBSTRATE_DISPOSITIONS, REAL_SUBSTRATE_DISPOSITION, RETAINED_REGRESSION_VALIDATOR_DISPOSITION, SYNTHETIC_TRUTH_BUCKET, PUBLIC_REFACTOR_STATUS_MARKERS, PUBLIC_REFACTOR_CLASSIFICATION_MARKERS, audit_evidence_truth_floor, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.evidence_truth_floor"
EVIDENCE_CLASS_REGISTRY_REL = Path("core/organ_evidence_classes.json")
ORGAN_REGISTRY_REL = Path("core/organ_registry.json")
FIRST_WAVE_RECEIPTS_REL = Path("receipts/first_wave")
FIXTURE_ECHO_CLASS = "fixture_echo_smoke"
REAL_RUNTIME_STATUS = "real_runtime_receipt_landed"
REAL_RUNTIME_CLASSIFICATION = "real_runtime_receipt"
ALLOWED_REAL_SUBSTRATE_DISPOSITIONS = frozenset(
    {
        "real_substrate_capsule",
        "retained_regression_validator",
        "deleted_or_demoted_historical_artifact",
        "blocked_secret_only",
    }
)
REAL_SUBSTRATE_DISPOSITION = "real_substrate_capsule"
RETAINED_REGRESSION_VALIDATOR_DISPOSITION = "retained_regression_validator"
SYNTHETIC_TRUTH_BUCKET = "regression_negative_fixture"
PUBLIC_REFACTOR_STATUS_MARKERS = (
    "public_refactor_landed",
    "source_faithful_refactor_landed",
    "extension_of_existing_public_refactor_landed",
)
PUBLIC_REFACTOR_CLASSIFICATION_MARKERS = (
    "public_refactor",
    "source_faithful_refactor",
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    Resolve the public Plectis root that anchors all registry/receipt reads.

    - Teleology: every audit read is relative to one public root; this fixes that root so callers can pass any path inside it.
    - Guarantee: returns the nearest ancestor (or self) named ``microcosm-substrate`` or carrying the pyproject + ``src/microcosm_core`` + private-state-forbidden marker; falls back to resolved CWD when none matches.
    - Fails: never raises; on no marker match returns ``Path.cwd().resolve(strict=False)`` rather than erroring.
    - When-needed: inspect when audit reads resolve against the wrong tree or a private root is mistaken for the public one.
    - Escalates-to: ``core/private_state_forbidden_classes.json`` presence check in this body; ``audit_evidence_truth_floor`` is the sole caller.
    - Non-goal: does not assert the resolved root is a real release root or private-root-equivalent; only locates the public anchor by marker.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    Extract the dict-typed rows under ``key`` from a registry payload, dropping malformed entries.

    - Teleology: registry list fields may hold non-dict junk; this normalizes them to a clean list of row dicts.
    - Guarantee: returns only the elements of ``payload[key]`` that are ``dict`` instances; non-list or missing values yield ``[]``.
    - Fails: never raises; returns ``[]`` when the key is absent or the value is not a list.
    - When-needed: inspect when registry rows are silently dropped because they are not JSON objects.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _accepted_registry_rows_by_organ(public_root: Path) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    Index the accepted-authority organ-registry rows by ``organ_id`` for disposition cross-checks.

    - Teleology: the disposition guard needs the authoritative registry row per organ; this builds that lookup.
    - Guarantee: returns ``{organ_id: row}`` for every ``implemented_organs`` row whose ``status`` is ``accepted_current_authority`` and that carries an ``organ_id``.
    - Fails: raises ``ValueError`` when ``core/organ_registry.json`` is not a JSON object; propagates ``read_json_strict`` errors on missing/invalid JSON.
    - When-needed: inspect when an organ's disposition issue references the wrong registry row or accepted rows go missing.
    - Escalates-to: ``core/organ_registry.json`` (``implemented_organs`` / ``status``); ``read_json_strict`` in ``microcosm_core.schemas``.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    registry = read_json_strict(public_root / ORGAN_REGISTRY_REL)
    if not isinstance(registry, dict):
        raise ValueError(f"{ORGAN_REGISTRY_REL} must be a JSON object")
    return {
        str(row.get("organ_id")): row
        for row in _rows(registry, "implemented_organs")
        if row.get("organ_id") and row.get("status") == "accepted_current_authority"
    }


def _synthetic_disposition_value(row: dict[str, Any]) -> str:
    """
    [ACTION]
    Normalize the ``synthetic_acceptance_disposition`` field, which may be a string or nested dict.

    - Teleology: the disposition can be authored as either a bare string or a ``{"disposition": ...}`` object; this collapses both to one string.
    - Guarantee: returns the inner ``disposition`` string when the field is a dict, the field itself when it is a string, else ``""``.
    - Fails: never raises; returns ``""`` for absent or unexpectedly-typed values.
    - When-needed: inspect when a row's synthetic disposition reads as empty despite being present in some other shape.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = row.get("synthetic_acceptance_disposition")
    if isinstance(value, dict):
        return str(value.get("disposition") or "")
    if isinstance(value, str):
        return value
    return ""


def _disposition_issue(
    organ_id: str,
    evidence_class_row: dict[str, Any],
    registry_row: dict[str, Any],
) -> dict[str, Any] | None:
    """
    [ACTION]
    Detect a fixture_echo_smoke row whose registry disposition illegitimately claims real-substrate progress.

    - Teleology: a synthetic negative-fixture organ must be dispositioned as a retained regression validator, never counted as product progress; this is the guard that catches violations.
    - Guarantee: returns ``None`` when disposition+synthetic-disposition+truth-bucket all match the synthetic contract; otherwise an issue dict with a ``code`` of ``synthetic_acceptance_progress_flag_mismatch`` / ``invalid_synthetic_acceptance_disposition`` / ``missing_synthetic_acceptance_dispositions`` plus the offending fields.
    - Fails: never raises; encodes every defect (missing fields, out-of-set dispositions, real-progress flag, wrong truth bucket) into the returned issue envelope.
    - When-needed: inspect when a synthetic fixture appears to be laundered into real progress, or when a disposition-issue code needs decoding.
    - Escalates-to: ``ALLOWED_REAL_SUBSTRATE_DISPOSITIONS`` / ``RETAINED_REGRESSION_VALIDATOR_DISPOSITION`` / ``SYNTHETIC_TRUTH_BUCKET`` constants above; organ registry ``real_substrate_disposition`` field.
    - Non-goal: does not mutate or repair the registry row and does not authorize reclassification; only reports the disposition mismatch.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    disposition = str(registry_row.get("real_substrate_disposition") or "")
    synthetic_disposition = _synthetic_disposition_value(registry_row)
    truth_bucket = str(registry_row.get("truth_accounting_bucket") or "")
    counts_as_progress = registry_row.get("counts_as_real_substrate_progress") is True
    evidence_class = str(evidence_class_row.get("evidence_class") or "")
    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    mismatch_reasons: list[str] = []

    if not disposition:
        missing_fields.append("real_substrate_disposition")
    elif disposition not in ALLOWED_REAL_SUBSTRATE_DISPOSITIONS:
        invalid_fields.append("real_substrate_disposition")
    if not synthetic_disposition:
        missing_fields.append("synthetic_acceptance_disposition")
    elif synthetic_disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION:
        invalid_fields.append("synthetic_acceptance_disposition")
    if counts_as_progress:
        mismatch_reasons.append("fixture_echo_smoke_counts_as_real_substrate_progress")
    if disposition and disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION:
        mismatch_reasons.append("fixture_echo_smoke_disposition_claims_real_substrate")
    if truth_bucket != SYNTHETIC_TRUTH_BUCKET:
        mismatch_reasons.append("fixture_echo_smoke_truth_bucket_mismatch")

    if not missing_fields and not invalid_fields and not mismatch_reasons:
        return None
    if mismatch_reasons:
        code = "synthetic_acceptance_progress_flag_mismatch"
    elif invalid_fields:
        code = "invalid_synthetic_acceptance_disposition"
    else:
        code = "missing_synthetic_acceptance_dispositions"
    return {
        "organ_id": organ_id,
        "code": code,
        "current_evidence_class": evidence_class,
        "registry_evidence_class": registry_row.get("evidence_class"),
        "truth_accounting_bucket": truth_bucket,
        "counts_as_real_substrate_progress": counts_as_progress,
        "real_substrate_disposition": disposition,
        "synthetic_acceptance_disposition": synthetic_disposition,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "mismatch_reasons": mismatch_reasons,
    }


def _display(path: Path, *, public_root: Path) -> str:
    """
    [ACTION]
    Render a path as a public-root-relative posix string for receipt references.

    - Teleology: receipts must cite paths relative to the public root, never absolute host paths, to stay portable and leak-free.
    - Guarantee: returns the posix path relative to ``public_root`` when ``path`` is under it; otherwise the path's own posix form.
    - Fails: never raises; catches ``ValueError`` from ``relative_to`` and falls back to ``path.as_posix()``.
    - When-needed: inspect when a ``receipt_ref`` shows an absolute or unexpectedly non-relative path.
    - Non-goal: does not guarantee the rendered path is inside the public root; an out-of-root path is returned verbatim.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return path.resolve(strict=False).relative_to(public_root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_json_receipt_files(root: Path):
    """
    [ACTION]
    Recursively yield every ``.json`` file under ``root``, tolerating filesystem races and bad entries.

    - Teleology: a fallback receipt sweep when the named-receipt convention misses; walks the receipt directory for any JSON evidence.
    - Guarantee: yields ``Path`` objects for regular ``.json`` files (symlinks not followed) found at any depth beneath ``root``.
    - Fails: never raises; swallows per-entry and per-scandir ``OSError`` (e.g. unreadable dir, vanished entry) and continues or returns empty.
    - When-needed: inspect when receipt discovery silently finds nothing despite files existing, or skips unreadable subtrees.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        yield from _iter_json_receipt_files(Path(entry.path))
                    elif (
                        entry.is_file(follow_symlinks=False)
                        and entry.name.endswith(".json")
                    ):
                        yield Path(entry.path)
                except OSError:
                    continue
    except OSError:
        return


def _receipt_paths(public_root: Path, organ_id: str) -> list[Path]:
    """
    [ACTION]
    Resolve the receipt files to inspect for one organ, preferring the canonical named receipts.

    - Teleology: locates an organ's first-wave receipts so the truth-floor can read evidence; named receipts win, with a directory sweep as fallback.
    - Guarantee: returns the existing subset of the three canonical names (validation_receipt/result/board) if any exist; else a sorted full ``.json`` sweep of the organ receipt dir; else ``[]``.
    - Fails: never raises; returns ``[]`` when the organ receipt directory is absent or empty.
    - When-needed: inspect when an organ's evidence is read from an unexpected receipt file or no receipts are found.
    - Escalates-to: ``FIRST_WAVE_RECEIPTS_REL`` constant and the ``receipts/first_wave/<organ_id>/`` layout; ``_iter_json_receipt_files`` for the fallback sweep.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    receipt_dir = public_root / FIRST_WAVE_RECEIPTS_REL / organ_id
    names = (
        f"{organ_id}_validation_receipt.json",
        f"{organ_id}_result.json",
        f"{organ_id}_board.json",
    )
    paths = [receipt_dir / name for name in names if (receipt_dir / name).is_file()]
    if paths:
        return paths
    if receipt_dir.is_dir():
        return sorted(_iter_json_receipt_files(receipt_dir))
    return []


def _verification(payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Extract the ``body_import_verification`` sub-object from a receipt payload.

    - Teleology: body-import proof fields live in a nested verification block; this isolates it for downstream extraction.
    - Guarantee: returns ``payload["body_import_verification"]`` when it is a dict, else ``{}``.
    - Fails: never raises; returns ``{}`` for missing or non-dict values.
    - When-needed: inspect when verification fields read as empty despite being present on the receipt.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = payload.get("body_import_verification")
    return value if isinstance(value, dict) else {}


def _body_in_receipt(payload: dict[str, Any], verification: dict[str, Any]) -> bool | None:
    """
    [ACTION]
    Read the tri-state ``body_in_receipt`` flag, preferring the verification block over the payload.

    - Teleology: a candidate must be body-free (source body NOT embedded in the receipt); this surfaces that flag for the proof gate.
    - Guarantee: returns the first ``bool`` found under ``body_in_receipt`` in ``verification`` then ``payload``; ``None`` when neither carries a boolean.
    - Fails: never raises; returns ``None`` when the flag is absent or non-boolean (treated downstream as proof-incomplete).
    - When-needed: inspect when a receipt is wrongly judged body-bearing/body-free during candidate or proof-gap evaluation.
    - Non-goal: does not verify the receipt actually excludes the source body; only reports the asserted flag.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for source in (verification, payload):
        value = source.get("body_in_receipt")
        if isinstance(value, bool):
            return value
    return None


def _list_count(value: Any) -> int:
    """
    [ACTION]
    Count list elements defensively, treating any non-list as length zero.

    - Teleology: receipt ref fields may be absent or wrongly typed; this yields a safe count for proof arithmetic.
    - Guarantee: returns ``len(value)`` when ``value`` is a list, else ``0``.
    - Fails: never raises; returns ``0`` for ``None`` or non-list inputs.
    - When-needed: inspect when a ref count reads zero despite data being present in a non-list shape.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return len(value) if isinstance(value, list) else 0


def _ref_values(verification: dict[str, Any], plural_key: str, singular_key: str) -> list[str]:
    """
    [ACTION]
    Merge a plural-list ref field and a singular ref field into a de-duplicated, order-preserving list.

    - Teleology: receipts express refs as either a list or a single value; this unifies both into one clean ref list for proof counting.
    - Guarantee: returns non-empty, whitespace-stripped string refs from ``plural_key`` (if a list) plus ``singular_key`` (if non-blank), with duplicates removed and first-seen order kept.
    - Fails: never raises; returns ``[]`` when neither key holds usable ref strings.
    - When-needed: inspect when source/target/validation ref counts look wrong or contain blanks/duplicates.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    refs: list[str] = []
    plural = verification.get(plural_key)
    if isinstance(plural, list):
        refs.extend(str(ref) for ref in plural if str(ref).strip())
    singular = verification.get(singular_key)
    if str(singular or "").strip():
        refs.append(str(singular))
    return list(dict.fromkeys(refs))


def _is_public_body_ref(ref: str) -> bool:
    """
    [ACTION]
    Decide whether a ref points at real public substrate rather than a fixture, receipt, or generated projection.

    - Teleology: real-progress proof must cite genuine public body, not self-referential fixtures/receipts or machine-generated projections; this is the anti-laundering ref classifier.
    - Guarantee: returns ``False`` when the (prefix-stripped) ref begins with ``fixtures/`` or ``receipts/`` or contains a generated-projection marker; ``True`` otherwise.
    - Fails: never raises; a plain string in, a bool out.
    - When-needed: inspect when a candidate's source/target ref is accepted or rejected as "public body" during proof-gap evaluation.
    - Escalates-to: the ``generated_markers`` tuple in this body; ``_proof_gap_from_evidence`` is the consumer.
    - Non-goal: does not confirm the ref resolves to an existing file or that the body is leak-free; only classifies the ref string shape.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    normalized = ref.removeprefix("microcosm-substrate/")
    if normalized.startswith(("fixtures/", "receipts/")):
        return False
    generated_markers = (
        "/generated_",
        ".generated.",
        "generated_projection",
        "projection_receipt",
    )
    return not any(marker in normalized for marker in generated_markers)


def _receipt_evidence(public_root: Path, path: Path) -> dict[str, Any] | None:
    """
    [ACTION]
    Read one receipt file and project it into the normalized evidence dict the truth-floor consumes.

    - Teleology: downstream candidate and proof-gap logic need a flat, typed view of a receipt's status, body-import, refs, and secret-scan; this builds it from a raw receipt.
    - Guarantee: returns an evidence dict with ``receipt_ref``, ``status``, body-import status/classification, tri-state ``body_in_receipt``, source/target/validation ref lists and counts, ``input_ref_count``, and ``secret_exclusion_scan_status``.
    - Fails: returns ``None`` when the receipt JSON is not an object; propagates ``read_json_strict`` errors on unreadable/invalid JSON.
    - When-needed: inspect when a receipt's evidence fields feed candidate/proof-gap logic incorrectly or read as empty.
    - Escalates-to: ``_verification`` / ``_body_in_receipt`` / ``_ref_values`` helpers; the receipt schema written by the body-import pipeline.
    - Non-goal: does not validate the receipt's claims; it only transcribes asserted fields into the evidence shape.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = read_json_strict(path)
    if not isinstance(payload, dict):
        return None
    verification = _verification(payload)
    body_import_status = str(
        payload.get("body_import_status")
        or verification.get("body_import_status")
        or ""
    )
    classification = str(verification.get("classification") or "")
    body_in_receipt = _body_in_receipt(payload, verification)
    status = str(payload.get("status") or verification.get("status") or "")
    source_refs = _ref_values(verification, "source_refs", "source_ref")
    target_refs = _ref_values(verification, "target_refs", "target_ref")
    validation_refs = _ref_values(verification, "validation_refs", "validation_ref")
    return {
        "receipt_ref": _display(path, public_root=public_root),
        "status": status,
        "body_import_status": body_import_status,
        "body_import_classification": classification,
        "body_in_receipt": body_in_receipt,
        "source_refs": source_refs,
        "target_refs": target_refs,
        "validation_refs": validation_refs,
        "source_ref_count": len(source_refs),
        "target_ref_count": len(target_refs),
        "validation_ref_count": len(validation_refs),
        "input_ref_count": _list_count(verification.get("input_refs")),
        "secret_exclusion_scan_status": (
            payload.get("secret_exclusion_scan", {}).get("status")
            if isinstance(payload.get("secret_exclusion_scan"), dict)
            else None
        ),
    }


def _candidate_from_evidence(
    organ_id: str,
    row: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    """
    [ACTION]
    Flag a fixture_echo_smoke row whose receipt looks eligible for product-progress reclassification review.

    - Teleology: surfaces (advisory only) synthetic rows backed by a passing, body-free real-runtime or public-refactor receipt that an owner should review for reclassification.
    - Guarantee: returns ``None`` unless the receipt is body-free + ``status=="pass"`` and matches the real-runtime or public-refactor markers; on match returns a candidate dict with ``candidate_classification`` and recommended evidence-class/truth-bucket.
    - Fails: never raises; non-qualifying or ambiguous receipts yield ``None`` (no candidate).
    - When-needed: inspect when a synthetic row is or is not nominated as a reclassification candidate.
    - Escalates-to: ``REAL_RUNTIME_STATUS`` / ``PUBLIC_REFACTOR_*_MARKERS`` constants; the ``anti_claim`` in ``audit_evidence_truth_floor``.
    - Non-goal: does NOT promote the row or authorize reclassification; emits an owner-review candidate only, gated separately by the proof-gap guard.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    body_import_status = str(evidence.get("body_import_status") or "")
    classification = str(evidence.get("body_import_classification") or "")
    body_in_receipt = evidence.get("body_in_receipt")
    status = str(evidence.get("status") or "")
    eligible_body_free = body_in_receipt is False
    if (
        body_import_status == REAL_RUNTIME_STATUS
        and classification == REAL_RUNTIME_CLASSIFICATION
        and status == "pass"
        and eligible_body_free
    ):
        return {
            "organ_id": organ_id,
            "candidate_classification": "real_runtime_receipt_candidate",
            "current_evidence_class": row.get("evidence_class"),
            "recommended_evidence_class": "semantic_validator",
            "recommended_truth_accounting_bucket": "real_import_validation",
            "reason": (
                "fixture_echo_smoke row has a passing body-free real runtime receipt "
                "verification; it should be reviewed for product-progress reclassification."
            ),
            "evidence": evidence,
        }
    if (
        any(marker in body_import_status for marker in PUBLIC_REFACTOR_STATUS_MARKERS)
        and any(marker in classification for marker in PUBLIC_REFACTOR_CLASSIFICATION_MARKERS)
        and status == "pass"
        and eligible_body_free
    ):
        return {
            "organ_id": organ_id,
            "candidate_classification": "source_faithful_refactor_candidate",
            "current_evidence_class": row.get("evidence_class"),
            "recommended_evidence_class": "algorithmic_projection",
            "recommended_truth_accounting_bucket": "source_faithful_refactor",
            "reason": (
                "fixture_echo_smoke row has a passing body-free public refactor "
                "verification; it should be reviewed for product-progress reclassification."
            ),
            "evidence": evidence,
        }
    return None


def _proof_gap_from_evidence(
    organ_id: str,
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    """
    [ACTION]
    Block a candidate-marked receipt that lacks the public-body proof required to count toward real progress.

    - Teleology: a receipt that claims candidate status (real-runtime or public-refactor markers) but cannot prove it with public source/target/validation refs and a passing secret scan is a truth-floor breach; this catches it.
    - Guarantee: returns ``None`` for non-candidate receipts or fully-proven ones; otherwise an issue dict ``code=="fixture_echo_receipt_without_public_body_proof"`` listing every ``missing_proof_field`` (status, body-free, public source/target refs, validation ref, secret-scan pass).
    - Fails: never raises; emits a blocking issue envelope rather than throwing, and short-circuits this receipt's candidacy in the caller.
    - When-needed: inspect when a candidate receipt is blocked, or to decode which proof field a synthetic row is missing.
    - Escalates-to: ``_is_public_body_ref`` for the ref-shape rule; ``audit_evidence_truth_floor.proof_gap_guard`` for the aggregated guard contract.
    - Non-goal: does not authorize promotion when proof passes; absence of a gap means review-eligible, not reclassified.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    body_import_status = str(evidence.get("body_import_status") or "")
    classification = str(evidence.get("body_import_classification") or "")
    status = str(evidence.get("status") or "")
    body_in_receipt = evidence.get("body_in_receipt")
    has_candidate_marker = (
        body_import_status == REAL_RUNTIME_STATUS
        and classification == REAL_RUNTIME_CLASSIFICATION
    ) or (
        any(marker in body_import_status for marker in PUBLIC_REFACTOR_STATUS_MARKERS)
        and any(
            marker in classification
            for marker in PUBLIC_REFACTOR_CLASSIFICATION_MARKERS
        )
    )
    if not has_candidate_marker:
        return None
    missing_proof_fields: list[str] = []
    if status != "pass":
        missing_proof_fields.append("status=pass")
    if body_in_receipt is not False:
        missing_proof_fields.append("body_in_receipt=false")
    if int(evidence.get("source_ref_count") or 0) <= 0:
        missing_proof_fields.append("source_ref")
    elif not any(_is_public_body_ref(ref) for ref in evidence.get("source_refs", [])):
        missing_proof_fields.append(
            "source_ref_public_substrate_not_fixture_receipt_or_generated_projection"
        )
    if int(evidence.get("target_ref_count") or 0) <= 0:
        missing_proof_fields.append("target_ref")
    elif not any(_is_public_body_ref(ref) for ref in evidence.get("target_refs", [])):
        missing_proof_fields.append(
            "target_ref_public_body_not_fixture_receipt_or_generated_projection"
        )
    if int(evidence.get("validation_ref_count") or 0) <= 0:
        missing_proof_fields.append("validation_ref")
    if evidence.get("secret_exclusion_scan_status") != "pass":
        missing_proof_fields.append("secret_exclusion_scan.status=pass")
    if not missing_proof_fields:
        return None
    return {
        "organ_id": organ_id,
        "code": "fixture_echo_receipt_without_public_body_proof",
        "receipt_ref": evidence.get("receipt_ref"),
        "body_import_status": body_import_status,
        "body_import_classification": classification,
        "missing_proof_fields": missing_proof_fields,
        "evidence": evidence,
    }


def audit_evidence_truth_floor(public_root: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    Public truth-floor audit: ensure fixture_echo_smoke (synthetic) evidence is never laundered into real product progress.

    - Teleology: the module's entry point; scans every ``fixture_echo_smoke`` evidence-class row, runs the disposition guard and the public-body proof guard, and lists owner-review reclassification candidates.
    - Guarantee: returns a ``microcosm_evidence_truth_floor_audit_v1`` receipt with ``status`` ``"pass"`` only when ``blocking_issue_count`` (disposition + proof-gap issues) is zero, else ``"blocked"``, plus the disposition_guard, proof_gap_guard, advisory candidates, and a standing ``anti_claim``.
    - Fails: raises ``ValueError`` when ``core/organ_evidence_classes.json`` (or the organ registry) is not a JSON object; propagates ``read_json_strict`` errors; otherwise reports defects as ``status=="blocked"`` rather than raising.
    - When-needed: inspect when validating that synthetic fixtures are not counted as real substrate progress, or when triaging a blocked truth-floor receipt.
    - Escalates-to: ``tests`` for this validator under ``microcosm-substrate/tests``; ``core/organ_evidence_classes.json`` + ``core/organ_registry.json`` as source authority; the emitted receipt's ``disposition_guard`` / ``proof_gap_guard`` blocks.
    - Non-goal: a ``pass`` does NOT authorize release, reclassification, or promotion of any row; candidates remain advisory and still require owner review plus public-body proof (per the receipt ``anti_claim``).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    root = _public_root_for_path(public_root)
    registry = read_json_strict(root / EVIDENCE_CLASS_REGISTRY_REL)
    if not isinstance(registry, dict):
        raise ValueError(f"{EVIDENCE_CLASS_REGISTRY_REL} must be a JSON object")
    accepted_registry_rows = _accepted_registry_rows_by_organ(root)

    candidates: list[dict[str, Any]] = []
    disposition_issues: list[dict[str, Any]] = []
    proof_gap_issues: list[dict[str, Any]] = []
    inspected_fixture_echo_rows = 0
    for row in _rows(registry, "organ_evidence_classes"):
        if row.get("evidence_class") != FIXTURE_ECHO_CLASS:
            continue
        organ_id = str(row.get("organ_id") or "")
        if not organ_id:
            continue
        inspected_fixture_echo_rows += 1
        registry_row = accepted_registry_rows.get(organ_id)
        if registry_row is not None:
            issue = _disposition_issue(organ_id, row, registry_row)
            if issue is not None:
                disposition_issues.append(issue)
        for path in _receipt_paths(root, organ_id):
            evidence = _receipt_evidence(root, path)
            if evidence is None:
                continue
            proof_gap = _proof_gap_from_evidence(organ_id, evidence)
            if proof_gap is not None:
                proof_gap_issues.append(proof_gap)
                continue
            candidate = _candidate_from_evidence(organ_id, row, evidence)
            if candidate is not None:
                candidates.append(candidate)
                break

    counts_by_classification: dict[str, int] = {}
    for candidate in candidates:
        key = str(candidate["candidate_classification"])
        counts_by_classification[key] = counts_by_classification.get(key, 0) + 1
    disposition_issue_counts: dict[str, int] = {}
    for issue in disposition_issues:
        key = str(issue["code"])
        disposition_issue_counts[key] = disposition_issue_counts.get(key, 0) + 1
    proof_gap_issue_counts: dict[str, int] = {}
    for issue in proof_gap_issues:
        key = str(issue["code"])
        proof_gap_issue_counts[key] = proof_gap_issue_counts.get(key, 0) + 1
    blocking_issue_count = len(disposition_issues) + len(proof_gap_issues)

    return {
        "schema_version": "microcosm_evidence_truth_floor_audit_v1",
        "checker_id": CHECKER_ID,
        "status": "pass" if blocking_issue_count == 0 else "blocked",
        "source_ref": EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        "registry_ref": ORGAN_REGISTRY_REL.as_posix(),
        "receipt_root_ref": FIRST_WAVE_RECEIPTS_REL.as_posix(),
        "inspected_fixture_echo_row_count": inspected_fixture_echo_rows,
        "candidate_count": len(candidates),
        "candidate_counts_by_classification": dict(sorted(counts_by_classification.items())),
        "blocking_issue_count": blocking_issue_count,
        "disposition_issue_counts_by_code": dict(
            sorted(disposition_issue_counts.items())
        ),
        "proof_gap_issue_counts_by_code": dict(
            sorted(proof_gap_issue_counts.items())
        ),
        "advisory_only": blocking_issue_count == 0,
        "disposition_guard": {
            "schema_version": "microcosm_synthetic_acceptance_disposition_guard_v1",
            "allowed_dispositions": sorted(ALLOWED_REAL_SUBSTRATE_DISPOSITIONS),
            "required_synthetic_disposition": (
                RETAINED_REGRESSION_VALIDATOR_DISPOSITION
            ),
            "fixture_echo_smoke_must_not_count_as_real_progress": True,
            "issue_count": len(disposition_issues),
            "issues": sorted(
                disposition_issues,
                key=lambda item: (str(item["code"]), str(item["organ_id"])),
            ),
        },
        "proof_gap_guard": {
            "schema_version": "microcosm_fixture_receipt_public_body_proof_guard_v1",
            "candidate_receipts_require_source_target_validation_refs": True,
            "candidate_receipts_reject_fixture_receipt_or_generated_projection_refs": True,
            "candidate_receipts_require_secret_exclusion_scan_pass": True,
            "issue_count": len(proof_gap_issues),
            "issues": sorted(
                proof_gap_issues,
                key=lambda item: (str(item["code"]), str(item["organ_id"])),
            ),
        },
        "candidates": sorted(
            candidates,
            key=lambda item: (
                str(item["candidate_classification"]),
                str(item["organ_id"]),
            ),
        ),
        "anti_claim": (
            "This audit is a truth-floor finder, not an automatic promotion. A row "
            "still needs owner review and public body proof before fixture evidence can "
            "count as product progress."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI wrapper: run the truth-floor audit over ``--root`` and emit/print the receipt with a status-coded exit.

    - Teleology: makes ``audit_evidence_truth_floor`` runnable as a command-line checker that prints or writes a JSON receipt.
    - Guarantee: returns ``0`` when the audit receipt ``status`` is ``"pass"``, else ``1``; writes the receipt atomically to ``--out`` when given, otherwise prints it as sorted indented JSON.
    - Fails: returns exit ``1`` on a blocked audit; propagates ``ValueError`` / ``read_json_strict`` errors from the underlying audit; ``argparse`` exits non-zero on bad args.
    - When-needed: inspect when wiring this validator into a CI/check lane or interpreting its process exit code.
    - Escalates-to: ``audit_evidence_truth_floor`` for the receipt contract; ``write_json_atomic`` in ``microcosm_core.receipts``.
    - Non-goal: exit ``0`` reports a clean truth floor only; it does not authorize release, promotion, or reclassification.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Path inside the public Plectis root.",
    )
    parser.add_argument("--out", help="Optional JSON receipt path.")
    args = parser.parse_args(argv)

    receipt = audit_evidence_truth_floor(args.root)
    if args.out:
        write_json_atomic(args.out, receipt)
    else:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
