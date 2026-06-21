from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.fixture_freshness"
ACCEPTANCE_SUMMARY_REL = "receipts/first_wave/acceptance_summary.json"
EVIDENCE_CLASS_REGISTRY_REL = "core/organ_evidence_classes.json"
ORGAN_REGISTRY_REL = "core/organ_registry.json"
TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS = {
    "real_runtime_receipt": "real_runtime_receipt_count",
    "copied_non_secret_macro_body": "copied_non_secret_macro_body_count",
    "source_faithful_refactor": "source_faithful_refactor_count",
    "real_import_validation": "real_import_validation_count",
    "regression_negative_fixture": "regression_negative_fixture_count",
    "external_fixture_witness": "external_fixture_witness_count",
    "blocked_import_debt": "blocked_import_debt_count",
    "secret_exclusion": "secret_exclusion_count",
    "legacy_adapter_or_synthetic_placeholder": (
        "legacy_adapter_or_synthetic_placeholder_count"
    ),
    "delete_or_demote_candidate": "delete_or_demote_candidate_count",
}
REAL_SUBSTRATE_PROGRESS_BUCKETS = frozenset(
    {
        "real_runtime_receipt",
        "copied_non_secret_macro_body",
        "source_faithful_refactor",
        "real_import_validation",
    }
)
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
SYNTHETIC_EVIDENCE_CLASSES = frozenset({"fixture_echo_smoke"})
SYNTHETIC_TRUTH_BUCKETS = frozenset({"regression_negative_fixture"})
HASH_CHUNK_SIZE = 1024 * 1024


def _public_root_for_path(path: str | Path) -> Path:
    """Resolve the public Plectis root that anchors all public-relative refs.

    - Teleology: protects every public-relative path/receipt resolution from anchoring at the wrong tree root (private parent or unrelated cwd).
    - Guarantee: returns a Path that is either a parent named "microcosm-substrate" or a dir holding pyproject.toml + src/microcosm_core + core/private_state_forbidden_classes.json; else the resolved cwd.
    - Fails: None — never raises; with no matching ancestor it returns Path.cwd().resolve(strict=False) as a best-effort fallback.
    - Reads: filesystem ancestors (pyproject.toml, src/microcosm_core, core/private_state_forbidden_classes.json) for the marker check.
    - Writes: None
    - When-needed: trust when deriving the root that every downstream public-relative receipt/manifest/input path joins against.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
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


def _display(path: Path, *, public_root: Path) -> str:
    """Render a path as a public-root-relative display string for receipt fields.

    - Teleology: keeps receipt-emitted paths anchored to the public substrate root so receipts never leak absolute/private path segments.
    - Guarantee: returns the public_relative_path(path, display_root=public_root) string (public-root-relative when path is under public_root).
    - Fails: never raises here; delegates entirely to public_relative_path, whose own fallback handling governs non-relative paths.
    - When-needed: inspect when a receipt_paths or *_receipt display value looks wrong relative to the public root.
    - Escalates-to: public_relative_path (microcosm_core.secret_exclusion_scan).
    """
    return public_relative_path(path, display_root=public_root)


def _display_context_ref(path: Path, *, public_root: Path) -> str:
    """Render a read-for-context path (mission DAG / receipt coverage) relative to repo or public root.

    - Teleology: produces a stable, leak-free display ref for context inputs that may live outside the public root (e.g. under repo-level state/).
    - Guarantee: returns a relative posix string — the state/... tail when "state" is in the path, else relative to public_root or its parent repo root; falls back to public_relative_path when no anchor matches; non-absolute input is returned as its own posix string.
    - Fails: never raises; ValueError from relative_to is caught and the next anchor (or the public_relative_path fallback) is used.
    - When-needed: inspect when mission_dag_node_refs.path or receipt_coverage_refs.path in the freshness receipt shows an unexpected root.
    - Escalates-to: public_relative_path (microcosm_core.secret_exclusion_scan).
    """
    if not path.is_absolute():
        return path.as_posix()
    parts = path.resolve(strict=False).parts
    if "state" in parts:
        state_index = parts.index("state")
        return Path(*parts[state_index:]).as_posix()
    repo_root = public_root.parent
    for root in (public_root, repo_root):
        try:
            return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
        except ValueError:
            continue
    return public_relative_path(path, display_root=public_root)


def _sha256(path: Path) -> str:
    """Compute the SHA-256 hex digest of a single file's bytes.

    - Teleology: provides the per-file fingerprint that makes manifest/fixture freshness drift detectable across runs.
    - Guarantee: returns the lowercase hex SHA-256 of the file's full byte content, read in HASH_CHUNK_SIZE chunks.
    - Fails: a missing/unreadable path raises OSError (FileNotFoundError/PermissionError) from path.open inside _update_hash_from_file.
    - When-needed: inspect when an input_fingerprints or fixture_manifest_sha256_by_organ value is questioned.
    """
    hasher = hashlib.sha256()
    _update_hash_from_file(hasher, path)
    return hasher.hexdigest()


def _update_hash_from_file(hasher: Any, path: Path) -> None:
    """Stream a file's bytes into an existing hash object in bounded chunks.

    - Teleology: bounds memory for large fixture inputs by chunked hashing instead of reading whole files into memory.
    - Guarantee: mutates hasher in place, feeding every byte of the file in HASH_CHUNK_SIZE reads until EOF; returns None.
    - Fails: a missing/unreadable path raises OSError (FileNotFoundError/PermissionError) from path.open.
    - When-needed: inspect when shared by _sha256 and _sha256_directory and a digest looks wrong.
    """
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            hasher.update(chunk)


def _iter_directory_files(path: Path) -> Iterator[Path]:
    """Yield every regular file under a directory tree, recursively, ignoring symlinks.

    - Teleology: enumerates the file set a directory-shaped fixture input must fingerprint, so the digest covers all contents.
    - Guarantee: yields each non-symlink regular file path under the tree; descends into non-symlink subdirectories; emits nothing for empty trees.
    - Fails: an unreadable/missing directory raises OSError from os.scandir; symlinked dirs and files are skipped, not followed.
    - When-needed: inspect when _sha256_directory's coverage of a directory fixture is questioned.
    """
    with os.scandir(path) as entries:
        for entry in entries:
            child = path / entry.name
            if entry.is_dir(follow_symlinks=False):
                yield from _iter_directory_files(child)
            elif entry.is_file(follow_symlinks=False):
                yield child


def _sha256_directory(path: Path) -> str:
    """Compute a deterministic SHA-256 over an entire directory tree's relative paths + bytes.

    - Teleology: gives a directory-shaped fixture input a single stable fingerprint that changes if any file's name or content changes.
    - Guarantee: returns a hex SHA-256 folding each file's relative posix path and content in sorted order with NUL separators, so the digest is order-independent and rename-sensitive.
    - Fails: a missing/unreadable directory or member raises OSError from os.scandir / file open.
    - When-needed: inspect when a directory entry in input_fingerprints changes unexpectedly between runs.
    """
    hasher = hashlib.sha256()
    for child in sorted(_iter_directory_files(path)):
        relative = child.relative_to(path).as_posix()
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        _update_hash_from_file(hasher, child)
        hasher.update(b"\0")
    return hasher.hexdigest()


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    """Strip body/forbidden-field detail from a secret-exclusion scan before it enters a receipt.

    - Teleology: prevents the receipt from re-emitting redacted-body or forbidden-field labels that could leak what was excluded, while keeping the scan's pass/block verdict.
    - Guarantee: returns a shallow copy of the scan with "forbidden_output_fields", "body_redacted", and "redacted_output_field_labels_omitted" removed; all other keys (status/hit counts) are preserved; the input dict is not mutated.
    - Fails: never raises; absent keys are popped with a None default.
    - When-needed: inspect when reconciling the receipt's secret_exclusion_scan block against the raw scan_paths output.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, source-body export, or whole-system correctness.
    """
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    safe.pop("body_redacted", None)
    safe.pop("redacted_output_field_labels_omitted", None)
    return safe


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Extract a list of dict rows under a payload key, dropping any non-dict entries.

    - Teleology: normalizes registry/readiness list fields to a clean dict-row list so downstream callers can assume row shape.
    - Guarantee: returns a list containing only the dict elements of payload[key]; a missing key or non-list value yields [].
    - Fails: never raises; non-dict and missing values are filtered/defaulted rather than rejected.
    - When-needed: inspect when an organ/readiness row appears dropped from a derived view.
    """
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _load_registry(public_root: Path) -> dict[str, Any]:
    """Strictly load the public organ registry JSON object.

    - Teleology: centralizes the single trusted read of core/organ_registry.json that anchors acceptance and freshness.
    - Guarantee: returns the parsed organ_registry.json object from public_root / ORGAN_REGISTRY_REL.
    - Fails: a missing file or invalid JSON propagates read_json_strict's error (OSError / parse error such as JSONDecodeError/ValueError).
    - When-needed: inspect when accepted-organ derivation or manifest pinning seems to read the wrong registry.
    - Escalates-to: read_json_strict (microcosm_core.schemas) and core/organ_registry.json.
    """
    return read_json_strict(public_root / ORGAN_REGISTRY_REL)


def _accepted_organs(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Select the registry rows whose status is accepted_current_authority.

    - Teleology: defines the authoritative accepted-organ set that all acceptance/freshness accounting iterates over.
    - Guarantee: returns the implemented_organs rows (dicts only) whose status == "accepted_current_authority"; non-matching/non-dict rows are excluded.
    - Fails: never raises; absence of implemented_organs yields [].
    - When-needed: inspect when accepted_count or the accounting population looks wrong.
    """
    return [
        row
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _accepted_registry_profiles_by_organ(public_root: Path) -> dict[str, dict[str, Any]]:
    """Index accepted organ-registry rows by organ_id.

    - Teleology: lets evidence-class assembly look up each accepted organ's registry-declared truth/evidence fields by id.
    - Guarantee: returns a dict mapping organ_id -> its accepted registry row, for every accepted organ that has a truthy organ_id.
    - Fails: a missing/invalid registry propagates read_json_strict's error via _load_registry.
    - When-needed: inspect when a registry-declared evidence/truth field is not overriding the class-profile default.
    - Escalates-to: _accepted_organs / _load_registry and core/organ_registry.json.
    """
    return {
        str(row.get("organ_id")): row
        for row in _accepted_organs(_load_registry(public_root))
        if row.get("organ_id")
    }


def _evidence_profiles_by_organ(public_root: Path) -> dict[str, dict[str, Any]]:
    """Build per-organ evidence-class profiles by fusing the evidence registry with registry overrides.

    - Teleology: produces the fail-closed truth-accounting profile (bucket, progress flag, strength rank, claim ceiling) per organ that separates real substrate from synthetic/adapter/debt evidence.
    - Guarantee: returns a dict organ_id -> profile (organ_id, evidence_class, truth_accounting_bucket, counts_as_real_substrate_progress, evidence_strength_rank, claim_ceiling, classification_basis), with registry fields overriding class-profile defaults.
    - Fails: raises ValueError when the evidence registry is not an object, is not fail_closed_no_default, lacks class_profiles/rows, a row is malformed, an evidence_class is unknown, a truth bucket is outside TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS, a progress flag is inconsistent, or organ rows duplicate; read errors propagate from read_json_strict.
    - When-needed: inspect when an organ's truth bucket, progress flag, or claim ceiling in the acceptance summary is disputed.
    - Escalates-to: core/organ_evidence_classes.json + core/organ_registry.json and read_json_strict (microcosm_core.schemas).
    - Non-goal: does not authorize release, provider calls, private-root equivalence, source-body export, or whole-system correctness.
    """
    registry = read_json_strict(public_root / EVIDENCE_CLASS_REGISTRY_REL)
    if not isinstance(registry, dict):
        raise ValueError(f"{EVIDENCE_CLASS_REGISTRY_REL} must be a JSON object")
    if registry.get("fail_closed_no_default") is not True:
        raise ValueError("organ evidence-class registry must fail closed")

    class_profiles = registry.get("class_profiles")
    rows = registry.get("organ_evidence_classes")
    if not isinstance(class_profiles, dict) or not isinstance(rows, list):
        raise ValueError("organ evidence-class registry is missing profiles or rows")

    profiles: dict[str, dict[str, Any]] = {}
    duplicate_organs: set[str] = set()
    registry_profiles = _accepted_registry_profiles_by_organ(public_root)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("organ evidence-class row must be a JSON object")
        organ_id = str(row.get("organ_id") or "")
        registry_profile = registry_profiles.get(organ_id, {})
        evidence_class = str(
            registry_profile.get("evidence_class") or row.get("evidence_class") or ""
        )
        class_profile = class_profiles.get(evidence_class)
        if not organ_id or not isinstance(class_profile, dict):
            raise ValueError(f"invalid evidence-class row for organ {organ_id!r}")
        if organ_id in profiles:
            duplicate_organs.add(organ_id)
        truth_bucket = str(
            registry_profile.get("truth_accounting_bucket")
            or class_profile.get("truth_accounting_bucket")
            or ""
        )
        if truth_bucket not in TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS:
            raise ValueError(
                f"evidence_class {evidence_class!r} uses unknown truth bucket "
                f"{truth_bucket!r}"
            )
        registry_progress = registry_profile.get("counts_as_real_substrate_progress")
        counts_as_progress = (
            registry_progress
            if isinstance(registry_progress, bool)
            else truth_bucket in REAL_SUBSTRATE_PROGRESS_BUCKETS
        )
        if (
            not registry_profile.get("truth_accounting_bucket")
            and class_profile.get("counts_as_real_substrate_progress")
            is not counts_as_progress
        ):
            raise ValueError(
                f"evidence_class {evidence_class!r} has inconsistent progress flag"
            )
        profiles[organ_id] = {
            "organ_id": organ_id,
            "evidence_class": evidence_class,
            "truth_accounting_bucket": truth_bucket,
            "counts_as_real_substrate_progress": counts_as_progress,
            "evidence_strength_rank": registry_profile.get("evidence_strength_rank")
            or class_profile.get("evidence_strength_rank"),
            "claim_ceiling": registry_profile.get("claim_ceiling")
            or class_profile.get("claim_ceiling"),
            "classification_basis": registry_profile.get("classification_basis")
            or row.get("classification_basis"),
        }
    if duplicate_organs:
        raise ValueError(
            "duplicate organ evidence-class rows: " + ", ".join(sorted(duplicate_organs))
        )
    return profiles


def _synthetic_disposition_value(row: dict[str, Any]) -> str:
    """Extract the synthetic-acceptance disposition string from a row's flexible field shape.

    - Teleology: normalizes the synthetic_acceptance_disposition field (dict or bare string) to one comparable disposition token.
    - Guarantee: returns the dict's "disposition" value, the bare string value, or "" for any other/absent shape.
    - Fails: never raises; non-dict/non-string values coerce to "".
    - When-needed: inspect when a synthetic organ's disposition is mis-classified as missing/invalid.
    """
    value = row.get("synthetic_acceptance_disposition")
    if isinstance(value, dict):
        return str(value.get("disposition") or "")
    if isinstance(value, str):
        return value
    return ""


def _is_synthetic_acceptance_row(row: dict[str, Any]) -> bool:
    """Decide whether an accepted row is a synthetic (non-real-progress) acceptance.

    - Teleology: marks fixture-echo/regression-negative/non-progress acceptances so they are held to the retained-regression disposition rule instead of the real-substrate one.
    - Guarantee: returns True iff the row's evidence_class is in SYNTHETIC_EVIDENCE_CLASSES, its truth bucket is in SYNTHETIC_TRUTH_BUCKETS, or counts_as_real_substrate_progress is exactly False; else False.
    - Fails: never raises; missing fields simply do not trip a synthetic condition.
    - When-needed: inspect when an organ is unexpectedly treated as (or excluded from) synthetic in disposition coverage.
    """
    return (
        row.get("evidence_class") in SYNTHETIC_EVIDENCE_CLASSES
        or row.get("truth_accounting_bucket") in SYNTHETIC_TRUTH_BUCKETS
        or row.get("counts_as_real_substrate_progress") is False
    )


def _disposition_coverage(accepted: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit that every accepted organ carries a valid, progress-consistent real-substrate disposition.

    - Teleology: enforces that acceptance status is paired with an explicit, allowed disposition that matches the organ's progress class (real vs retained-regression), blocking laundering of synthetic acceptances as real progress.
    - Guarantee: returns a coverage dict (schema microcosm_real_substrate_disposition_coverage_v1) whose status is PASS only when no organ is missing a required disposition, carries a disallowed disposition, or has a progress/disposition mismatch; otherwise "blocked", with the offending organ ids listed in the missing/invalid/mismatch arrays.
    - Fails: never raises; non-conforming organs are reported as "blocked" with violation lists rather than via exception.
    - When-needed: inspect when the acceptance summary reports a disposition_coverage blocker.
    - Escalates-to: organ_registry.json fields real_substrate_disposition / synthetic_acceptance_disposition and ALLOWED_REAL_SUBSTRATE_DISPOSITIONS.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, source-body export, or whole-system correctness.
    """
    disposition_counts = Counter(
        str(row.get("real_substrate_disposition") or "missing") for row in accepted
    )
    missing: list[str] = []
    invalid: list[str] = []
    mismatch: list[str] = []
    synthetic_organs: list[str] = []
    for row in accepted:
        organ_id = str(row.get("organ_id") or "")
        disposition = str(row.get("real_substrate_disposition") or "")
        synthetic_disposition = _synthetic_disposition_value(row)
        is_synthetic = _is_synthetic_acceptance_row(row)
        counts_as_progress = row.get("counts_as_real_substrate_progress") is True
        if not disposition:
            missing.append(organ_id)
        if disposition and disposition not in ALLOWED_REAL_SUBSTRATE_DISPOSITIONS:
            invalid.append(organ_id)
        if is_synthetic:
            synthetic_organs.append(organ_id)
            if not synthetic_disposition:
                missing.append(organ_id)
            elif (
                synthetic_disposition
                != RETAINED_REGRESSION_VALIDATOR_DISPOSITION
            ):
                invalid.append(organ_id)
            if counts_as_progress:
                mismatch.append(organ_id)
            if disposition and disposition != RETAINED_REGRESSION_VALIDATOR_DISPOSITION:
                mismatch.append(organ_id)
        elif counts_as_progress and disposition and disposition != REAL_SUBSTRATE_DISPOSITION:
            mismatch.append(organ_id)
        elif not counts_as_progress and disposition == REAL_SUBSTRATE_DISPOSITION:
            mismatch.append(organ_id)

    missing = sorted(set(missing))
    invalid = sorted(set(invalid))
    mismatch = sorted(set(mismatch))
    covered_count = len(accepted) - len(set(missing) | set(invalid) | set(mismatch))
    status = PASS if covered_count == len(accepted) else "blocked"
    return {
        "schema_version": "microcosm_real_substrate_disposition_coverage_v1",
        "status": status,
        "allowed_dispositions": sorted(ALLOWED_REAL_SUBSTRATE_DISPOSITIONS),
        "required_registry_field": "real_substrate_disposition",
        "required_synthetic_field": "synthetic_acceptance_disposition",
        "accepted_organ_count": len(accepted),
        "covered_count": covered_count,
        "synthetic_accepted_count": len(synthetic_organs),
        "synthetic_retained_regression_validator_organs": sorted(synthetic_organs),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "missing_synthetic_acceptance_dispositions": missing,
        "invalid_synthetic_acceptance_disposition": invalid,
        "synthetic_acceptance_progress_flag_mismatch": mismatch,
    }


def _acceptance_truth_accounting(
    accepted: list[dict[str, Any]],
    evidence_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate accepted organs into a truth-accounting breakdown separating real progress from other evidence classes.

    - Teleology: makes the accepted count honest by partitioning it across truth buckets and explicitly asserting that "accepted" is neither product progress nor evidence strength.
    - Guarantee: returns a dict (schema microcosm_acceptance_truth_accounting_v1) with per-bucket and per-class counts, real_substrate_progress_count vs non_progress_accepted_count, real/non-progress organ id lists, per-organ evidence rows, an embedded disposition_coverage, and the asserted-False flags accepted_current_authority_is_evidence_strength / accepted_count_is_product_progress.
    - Fails: raises ValueError when any accepted organ has no entry in evidence_profiles (listing the missing ids); disposition issues are reported inside disposition_coverage, not raised.
    - When-needed: inspect when the acceptance summary's truth_accounting bucket counts or progress split are disputed.
    - Escalates-to: _evidence_profiles_by_organ + _disposition_coverage and core/organ_evidence_classes.json.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, source-body export, or whole-system correctness.
    """
    accepted_ids = [str(row.get("organ_id") or "") for row in accepted]
    missing = sorted(organ_id for organ_id in accepted_ids if organ_id not in evidence_profiles)
    if missing:
        raise ValueError(
            "accepted organs missing evidence classes: " + ", ".join(missing)
        )

    counts = Counter()
    class_counts = Counter()
    real_organs: list[str] = []
    non_progress_organs: list[str] = []
    evidence_rows: list[dict[str, Any]] = []
    accepted_by_id = {str(row.get("organ_id") or ""): row for row in accepted}
    for organ_id in accepted_ids:
        profile = evidence_profiles[organ_id]
        accepted_row = accepted_by_id[organ_id]
        truth_bucket = str(profile["truth_accounting_bucket"])
        counts[truth_bucket] += 1
        class_counts[str(profile["evidence_class"])] += 1
        if profile["counts_as_real_substrate_progress"] is True:
            real_organs.append(organ_id)
        else:
            non_progress_organs.append(organ_id)
        evidence_row = dict(profile)
        evidence_row["real_substrate_disposition"] = accepted_row.get(
            "real_substrate_disposition"
        )
        if accepted_row.get("synthetic_acceptance_disposition") is not None:
            evidence_row["synthetic_acceptance_disposition"] = accepted_row.get(
                "synthetic_acceptance_disposition"
            )
        evidence_rows.append(evidence_row)

    count_fields = {
        count_key: counts[bucket]
        for bucket, count_key in TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS.items()
    }
    real_substrate_progress_count = len(real_organs)
    non_progress_count = len(non_progress_organs)
    disposition_coverage = _disposition_coverage(accepted)
    return {
        "schema_version": "microcosm_acceptance_truth_accounting_v1",
        "source_ref": EVIDENCE_CLASS_REGISTRY_REL,
        "accepted_current_authority_is_evidence_strength": False,
        "accepted_count_is_product_progress": False,
        "real_substrate_progress_count": real_substrate_progress_count,
        "non_progress_accepted_count": non_progress_count,
        "truth_accounting_bucket_counts": dict(sorted(counts.items())),
        "evidence_class_counts": dict(sorted(class_counts.items())),
        "real_substrate_progress_organs": real_organs,
        "non_progress_organs": non_progress_organs,
        "disposition_coverage": disposition_coverage,
        "accepted_current_authority_evidence": evidence_rows,
        **count_fields,
    }


def _string_list(value: Any) -> list[str]:
    """Coerce an arbitrary manifest value into a list of scalar strings.

    - Teleology: hardens parsing of manifest ref/material/id arrays so malformed entries cannot inject non-scalar values downstream.
    - Guarantee: returns a list of str() of the str/int/float items when value is a list; any non-list input yields []; non-scalar list items are dropped.
    - Fails: never raises; unexpected shapes are filtered/defaulted.
    - When-needed: inspect when manifest-derived ref/material/id lists look truncated or empty.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))]


def _int_value(value: Any) -> int:
    """Coerce an arbitrary manifest value into a non-negative-ish int count.

    - Teleology: tolerates int-or-numeric-string body counts in manifests without crashing the coverage aggregation.
    - Guarantee: returns the int when value is an int, the parsed int when value is an all-digit string, else 0.
    - Fails: never raises; non-int / non-digit-string input returns 0 (note: bare digit strings only — negatives and floats fall through to 0).
    - When-needed: inspect when a body_material_count is read as 0 despite a populated manifest field.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _normalize_public_ref(value: Any) -> str:
    """Normalize a source/manifest ref to be public-root-relative.

    - Teleology: protects public manifest/source refs in receipts from carrying a "microcosm-substrate/" prefix that would mis-join against an already-public root.
    - Guarantee: returns the string with a leading "microcosm-substrate/" stripped, else the unchanged str(value or ""); a falsy value yields "".
    - Fails: None — never raises; non-string input is coerced via str() and returned (possibly empty), never rejected.
    - Writes: None
    - When-needed: trust when reading a normalized ref out of a coverage row before joining it under public_root.
    """
    text = str(value or "")
    public_root_prefix = "microcosm-substrate/"
    if text.startswith(public_root_prefix):
        return text[len(public_root_prefix) :]
    return text


def _source_body_import_coverage(
    public_root: Path,
    accepted: list[dict[str, Any]],
) -> dict[str, Any]:
    """Audit accepted organs' source-body imports for present manifest refs and no in-receipt bodies.

    - Teleology: proves that any organ claiming copied source-body material backs it with present, public manifest refs and keeps the body out of the receipt (only fingerprints/refs, never source text).
    - Guarantee: returns a dict (schema microcosm_source_body_import_coverage_v1) with per-organ rows, body/ref counts, material-class and per-disposition tallies, and status PASS only when no source_manifest_ref is missing on disk AND no organ sets body_in_receipt=True; otherwise "blocked" with the offending ids/refs listed.
    - Fails: a present-but-invalid fixture manifest propagates read_json_strict's parse error; missing manifests/refs are recorded (missing_source_manifest_refs) and downgrade status to "blocked" rather than raising.
    - When-needed: inspect when the acceptance summary reports a source_body_imports blocker or a body_in_receipt flag.
    - Escalates-to: core/fixture_manifests/*.fixture_manifest.json (source_open_body_imports) and _source_module_manifest_coverage.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, source-body export, or whole-system correctness.
    """
    rows: list[dict[str, Any]] = []
    missing_source_manifest_refs: list[dict[str, str]] = []
    body_in_receipt_organs: list[str] = []
    material_class_counts: Counter[str] = Counter()
    disposition_body_counts: Counter[str] = Counter()
    body_material_count = 0
    source_manifest_ref_count = 0

    for accepted_row in accepted:
        organ_id = str(accepted_row.get("organ_id") or "")
        if not organ_id:
            continue
        manifest_path = public_root / "core/fixture_manifests" / (
            f"{organ_id}.fixture_manifest.json"
        )
        if not manifest_path.is_file():
            continue
        manifest = read_json_strict(manifest_path)
        if not isinstance(manifest, dict):
            continue
        source_open = manifest.get("source_open_body_imports")
        if not isinstance(source_open, dict):
            continue

        source_manifest_refs = [
            _normalize_public_ref(ref)
            for ref in _string_list(source_open.get("source_manifest_refs"))
        ]
        material_classes = _string_list(source_open.get("material_classes"))
        body_material_ids = _string_list(source_open.get("body_material_ids"))
        row_body_count = _int_value(source_open.get("body_material_count"))
        if not row_body_count:
            row_body_count = _int_value(manifest.get("body_copied_material_count"))
        if not row_body_count:
            row_body_count = len(body_material_ids)

        for ref in source_manifest_refs:
            if not (public_root / ref).is_file():
                missing_source_manifest_refs.append(
                    {"organ_id": organ_id, "source_manifest_ref": ref}
                )
        for material_class in material_classes:
            material_class_counts[material_class] += 1

        body_material_count += row_body_count
        source_manifest_ref_count += len(source_manifest_refs)
        disposition = str(
            accepted_row.get("real_substrate_disposition") or "missing"
        )
        disposition_body_counts[disposition] += row_body_count
        if source_open.get("body_in_receipt") is True:
            body_in_receipt_organs.append(organ_id)

        preview = source_manifest_refs[:8]
        rows.append(
            {
                "organ_id": organ_id,
                "evidence_class": accepted_row.get("evidence_class"),
                "truth_accounting_bucket": accepted_row.get("truth_accounting_bucket"),
                "real_substrate_disposition": accepted_row.get(
                    "real_substrate_disposition"
                ),
                "counts_as_real_substrate_progress": accepted_row.get(
                    "counts_as_real_substrate_progress"
                ),
                "body_material_status": source_open.get("body_material_status")
                or manifest.get("body_material_status")
                or source_open.get("source_import_class"),
                "body_material_count": row_body_count,
                "material_classes": material_classes,
                "source_manifest_ref_count": len(source_manifest_refs),
                "source_manifest_refs_preview": preview,
                "source_manifest_refs_omitted": max(
                    len(source_manifest_refs) - len(preview),
                    0,
                ),
                "aggregate_floor_ref": _normalize_public_ref(
                    source_open.get("aggregate_floor_ref")
                ),
                "body_in_receipt": source_open.get("body_in_receipt") is True,
            }
        )

    status = (
        PASS
        if not missing_source_manifest_refs and not body_in_receipt_organs
        else "blocked"
    )
    return {
        "schema_version": "microcosm_source_body_import_coverage_v1",
        "status": status,
        "accepted_organ_count": len(accepted),
        "source_body_import_organ_count": len(rows),
        "body_material_count": body_material_count,
        "source_manifest_ref_count": source_manifest_ref_count,
        "material_class_counts": dict(sorted(material_class_counts.items())),
        "body_material_count_by_real_substrate_disposition": dict(
            sorted(disposition_body_counts.items())
        ),
        "body_in_receipt": bool(body_in_receipt_organs),
        "body_in_receipt_organs": sorted(body_in_receipt_organs),
        "missing_source_manifest_refs": sorted(
            missing_source_manifest_refs,
            key=lambda row: (row["organ_id"], row["source_manifest_ref"]),
        ),
        "rows": rows,
    }


def _source_module_manifest_coverage(
    source_body_imports: dict[str, Any],
) -> dict[str, Any]:
    """Project the source-body import coverage into a compact manifest-coverage receipt slice.

    - Teleology: protects the acceptance-summary claim that every source-body import has a present, public manifest ref (no body smuggled into the receipt) from silently dropping that evidence.
    - Guarantee: returns a dict carrying schema_version "microcosm_source_module_manifest_coverage_v1" plus the input's status, organ/ref counts, missing_source_manifest_refs, and body_in_receipt[_organs] verbatim.
    - Fails: a source_body_imports dict missing any required key (status, source_body_import_organ_count, source_manifest_ref_count, missing_source_manifest_refs, body_in_receipt, body_in_receipt_organs) raises KeyError.
    - Reads: in-memory source_body_imports dict (produced by _source_body_import_coverage); no I/O.
    - Writes: None
    - When-needed: inspect when reconciling the acceptance-summary source_module_manifest_coverage block against the fuller source_body_imports section.
    - Escalates-to: _source_body_import_coverage (the authoritative computation) and core/fixture_manifests/*.fixture_manifest.json.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    return {
        "schema_version": "microcosm_source_module_manifest_coverage_v1",
        "status": source_body_imports["status"],
        "source_body_import_organ_count": source_body_imports[
            "source_body_import_organ_count"
        ],
        "source_manifest_ref_count": source_body_imports["source_manifest_ref_count"],
        "missing_source_manifest_refs": source_body_imports[
            "missing_source_manifest_refs"
        ],
        "body_in_receipt": source_body_imports["body_in_receipt"],
        "body_in_receipt_organs": source_body_imports["body_in_receipt_organs"],
    }


def _acceptance_summary_blockers(
    disposition_coverage: dict[str, Any],
    source_body_imports: dict[str, Any],
) -> list[str]:
    """Collapse the two coverage sub-receipts into the acceptance summary's blocker list.

    - Teleology: derives the acceptance summary's pass/block verdict from its sub-checks rather than from raw counts, so a blocked summary names which gate failed.
    - Guarantee: returns a list containing "disposition_coverage" and/or "source_body_imports" for whichever sub-receipt status != PASS; an empty list means both passed.
    - Fails: never raises; missing/absent status keys compare unequal to PASS and add the corresponding blocker.
    - When-needed: inspect when the acceptance summary status is "blocked" and you need the failing gate name.
    """
    blockers: list[str] = []
    if disposition_coverage.get("status") != PASS:
        blockers.append("disposition_coverage")
    if source_body_imports.get("status") != PASS:
        blockers.append("source_body_imports")
    return blockers


def _manifest_public_path(public_root: Path, readiness_row: dict[str, Any]) -> Path:
    """Pin a readiness row's fixture_manifest to its public fixture-manifest location.

    - Teleology: protects manifest resolution from a readiness row pointing fixture_manifest at a macro/private path by keeping only the basename under the public dir.
    - Guarantee: returns public_root / "core/fixture_manifests" / <basename-of-readiness fixture_manifest>; an empty/missing fixture_manifest yields the directory joined with "" (path to the fixture_manifests dir).
    - Fails: None — never raises and does not check existence; existence is verified by callers (_manifest_input_paths / run_fixture_freshness emit MISSING_FIXTURE_MANIFEST).
    - Reads: public_root and readiness_row["fixture_manifest"]; no filesystem read here.
    - Writes: None
    - When-needed: trust when mapping a per-organ readiness row to the manifest path used for hashing and input enumeration.
    """
    macro_path = Path(str(readiness_row.get("fixture_manifest") or ""))
    return public_root / "core/fixture_manifests" / macro_path.name


def _manifest_input_paths(manifest_path: Path) -> list[str]:
    """Extract the declared input relative-paths from a fixture manifest.

    - Teleology: protects the per-organ fixture-input fingerprint set from being computed off a missing or malformed manifest (which would silently fingerprint nothing).
    - Guarantee: returns a list[str] of paths drawn from manifest["inputs"] (dict rows' "path" field or bare string rows); returns [] when the manifest file is absent, parses to a non-dict, or has no list-shaped inputs.
    - Fails: a present manifest with invalid JSON propagates read_json_strict's parse error (e.g. JSONDecodeError/ValueError); absence or non-dict content returns [] rather than raising.
    - Reads: the fixture manifest JSON at manifest_path (its "inputs" rows).
    - Writes: None
    - When-needed: trust when enumerating which fixture inputs an organ's freshness fingerprint covers.
    - Escalates-to: read_json_strict (microcosm_core.schemas) and core/fixture_manifests/*.fixture_manifest.json.
    """
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        return []
    inputs = manifest.get("inputs", [])
    paths: list[str] = []
    if isinstance(inputs, list):
        for row in inputs:
            if isinstance(row, dict) and row.get("path"):
                paths.append(str(row["path"]))
            elif isinstance(row, str):
                paths.append(row)
    return paths


def _write_acceptance_summary(
    public_root: Path,
    path: Path,
    *,
    accepted: list[dict[str, Any]],
    dependency_preflight_ref: str,
    fixture_freshness_ref: str,
    secret_exclusion_scan: dict[str, Any],
) -> dict[str, Any]:
    """Compose and atomically write the first-wave acceptance-summary receipt with its authority ceiling.

    - Teleology: emits the single public acceptance-summary receipt that records runtime-spine receipt presence while explicitly disclaiming release/provider/financial/private-equivalence authority.
    - Guarantee: writes a first_wave_acceptance_summary_receipt_v1 payload atomically to path and returns it; status is PASS only when truth-accounting disposition coverage and source-body imports both pass; all *_authorized fields and the authority_ceiling are hard-coded to deny release/provider/financial/private-equivalence/whole-system claims.
    - Fails: propagates ValueError/parse/OS errors from the evidence-profile build, manifest reads, or write_json_atomic; a coverage failure yields status "blocked" in the written payload, not an exception.
    - When-needed: inspect when the on-disk receipts/first_wave/acceptance_summary.json content or its blocker/status is disputed.
    - Escalates-to: receipts/first_wave/acceptance_summary.json and _acceptance_truth_accounting / _source_body_import_coverage.
    - Non-goal: does not authorize release, provider calls, trading/financial advice, private-root equivalence, source-body export, or whole-system correctness.
    """
    truth_accounting = _acceptance_truth_accounting(
        accepted,
        _evidence_profiles_by_organ(public_root),
    )
    source_body_imports = _source_body_import_coverage(public_root, accepted)
    truth_accounting["source_body_imports"] = source_body_imports
    disposition_coverage = truth_accounting["disposition_coverage"]
    source_module_manifest_coverage = _source_module_manifest_coverage(
        source_body_imports
    )
    acceptance_summary_blockers = _acceptance_summary_blockers(
        disposition_coverage,
        source_body_imports,
    )
    summary_status = PASS if not acceptance_summary_blockers else "blocked"
    substrate_ledger_path = public_root / "core/substrate_substitution_ledger.json"
    substrate_ledger = (
        read_json_strict(substrate_ledger_path)
        if substrate_ledger_path.is_file()
        else {}
    )
    substrate_summary = (
        substrate_ledger.get("summary", {})
        if isinstance(substrate_ledger, dict)
        and isinstance(substrate_ledger.get("summary"), dict)
        else {}
    )
    payload = {
        "schema_version": "first_wave_acceptance_summary_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": summary_status,
        "acceptance_summary_blockers": acceptance_summary_blockers,
        "accepted_current_authority_organs": [row.get("organ_id") for row in accepted],
        "accepted_count": len(accepted),
        "accepted_current_authority_count": len(accepted),
        "accepted_count_is_product_progress": False,
        "truth_accounting": truth_accounting,
        "disposition_coverage": disposition_coverage,
        "source_body_imports": source_body_imports,
        "source_module_manifest_coverage": source_module_manifest_coverage,
        "substrate_substitution_ledger_ref": "core/substrate_substitution_ledger.json",
        "substrate_substitution": substrate_summary,
        "deferred_organs": [],
        "dependency_preflight_receipt": dependency_preflight_ref,
        "fixture_freshness_receipt": fixture_freshness_ref,
        "standards_registry_validation_receipt": "receipts/first_wave/standards_registry_validation.json",
        "preflight_receipts": [
            dependency_preflight_ref,
            fixture_freshness_ref,
        ],
        "lean_lake_authorized": "bounded_public_witness_only",
        "release_authorized": False,
        "provider_calls_authorized": False,
        "trading_or_financial_advice_authorized": False,
        "private_data_equivalence_authorized": False,
        "secret_exclusion_scan": secret_exclusion_scan,
        "authority_ceiling": {
            "status": PASS,
            "acceptance_summary_authority": "public_runtime_spine_receipt_summary_only",
            "accepted_count_is_product_progress": False,
            "accepted_current_authority_is_evidence_strength": False,
            "whole_system_correctness": False,
            "release_authorized": False,
            "trading_or_financial_advice_authorized": False,
        },
        "anti_claim": "This acceptance summary records current public runtime-spine receipt presence only. Its accepted count is not product progress or evidence strength; the truth_accounting section separates real substrate progress from fixture, synthetic, adapter, and debt evidence classes.",
        "receipt_paths": [_display(path, public_root=public_root)],
    }
    write_json_atomic(path, payload)
    return payload


def run_fixture_freshness(
    readiness_path: str | Path,
    negative_matrix_path: str | Path,
    mission_dag_path: str | Path,
    receipt_coverage_path: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    """Run the public fixture-freshness check: fingerprint manifests/inputs, verify receipts, and scan for private-state leaks.

    - Teleology: the module's public entrypoint that proves per-organ fixture manifests, fixture inputs, and generated receipts are present and fingerprinted, with no private-state leak, before any wave is trusted.
    - Guarantee: writes a fixture_runner_freshness_receipt_v1 receipt atomically to out_path and returns it; status is PASS only when stale_receipt_codes is empty (no MISSING_FIXTURE_MANIFEST/MISSING_FIXTURE_INPUT/MISSING_RECEIPT, no PRIVATE_STATE_SCAN_BLOCKED, no ACCEPTANCE_SUMMARY_BLOCKED:*); also writes the acceptance summary as a side effect; authority_ceiling denies release/provider/private-equivalence.
    - Fails: never raises on substrate gaps — missing manifests/inputs/receipts and a blocking secret scan are recorded as stale codes and downgrade status to "blocked"; only read_json_strict parse errors / write_json_atomic OS errors propagate as exceptions.
    - When-needed: inspect when a wave is blocked on fixture freshness, or when stale_receipt_codes / input_fingerprints need explaining.
    - Escalates-to: receipts/first_wave (fixture_runner_freshness + acceptance_summary) and the negative-case test test_organ_registry_authority_floor.py.
    - Non-goal: does not authorize release, hosted operations, credentialed provider calls, Lean/Lake beyond the bounded public witness, secret export, private-root equivalence, or whole-system correctness.
    """
    output_file = Path(out_path)
    public_root = _public_root_for_path(output_file)
    readiness_file = Path(readiness_path)
    negative_matrix_file = Path(negative_matrix_path)
    mission_dag_file = Path(mission_dag_path)
    receipt_coverage_file = Path(receipt_coverage_path)
    readiness = read_json_strict(readiness_file)
    registry = _load_registry(public_root)
    accepted = _accepted_organs(registry)
    readiness_by_id = {
        str(row.get("organ_id")): row for row in _rows(readiness, "organ_readiness")
    }

    manifest_hashes: dict[str, str] = {}
    input_fingerprints: dict[str, dict[str, str]] = {}
    stale_codes: list[str] = []
    checked_receipts: list[str] = []
    for organ in accepted:
        organ_id = str(organ.get("organ_id"))
        readiness_row = readiness_by_id.get(organ_id, {})
        manifest_path = _manifest_public_path(public_root, readiness_row)
        if manifest_path.is_file():
            manifest_hashes[organ_id] = _sha256(manifest_path)
        else:
            stale_codes.append(f"MISSING_FIXTURE_MANIFEST:{organ_id}")
        input_fingerprints[organ_id] = {}
        fixture_inputs = _manifest_input_paths(manifest_path) or [
            str(path) for path in readiness_row.get("fixture_inputs", [])
        ]
        for rel in fixture_inputs:
            path = public_root / str(rel)
            if path.is_file():
                input_fingerprints[organ_id][str(rel)] = _sha256(path)
            elif path.is_dir():
                input_fingerprints[organ_id][str(rel)] = _sha256_directory(path)
            else:
                stale_codes.append(f"MISSING_FIXTURE_INPUT:{organ_id}:{rel}")
        for rel in organ.get("generated_receipts", []):
            if str(rel).startswith("state/"):
                continue
            path = public_root / str(rel)
            checked_receipts.append(str(rel))
            if not path.is_file():
                stale_codes.append(f"MISSING_RECEIPT:{rel}")

    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
            [
                readiness_file,
                negative_matrix_file,
                mission_dag_file,
                receipt_coverage_file,
                public_root / "core/organ_registry.json",
                public_root / "core/acceptance/first_wave_acceptance.json",
            ],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    if scan["blocking_hit_count"]:
        stale_codes.append("PRIVATE_STATE_SCAN_BLOCKED")
    stale_codes = sorted(set(stale_codes))
    status = PASS if not stale_codes else "blocked"
    receipt_paths = [_display(output_file, public_root=public_root)]
    acceptance_summary_path = public_root / ACCEPTANCE_SUMMARY_REL
    acceptance_summary_scan = dict(scan)
    acceptance_summary_scan["hits"] = []
    acceptance_summary_scan["hit_count"] = 0
    acceptance_summary_scan["blocking_hit_count"] = 0
    acceptance_summary = _write_acceptance_summary(
        public_root,
        acceptance_summary_path,
        accepted=accepted,
        dependency_preflight_ref="receipts/preflight/dependency_preflight.json",
        fixture_freshness_ref=_display(output_file, public_root=public_root),
        secret_exclusion_scan=acceptance_summary_scan,
    )
    receipt_paths.append(_display(acceptance_summary_path, public_root=public_root))
    summary_blockers = _string_list(
        acceptance_summary.get("acceptance_summary_blockers")
    )
    if acceptance_summary["status"] != PASS and not summary_blockers:
        summary_blockers = ["unknown"]
    stale_codes = sorted(
        set(
            stale_codes
            + [
                f"ACCEPTANCE_SUMMARY_BLOCKED:{blocker}"
                for blocker in summary_blockers
            ]
        )
    )
    status = PASS if not stale_codes else "blocked"

    receipt = {
        "schema_version": "fixture_runner_freshness_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "checked_receipts": checked_receipts,
        "fixture_manifest_sha256_by_organ": manifest_hashes,
        "mission_dag_node_refs": {
            "path": _display_context_ref(mission_dag_file, public_root=public_root),
            "status": "read_for_freshness_context",
        },
        "receipt_coverage_refs": {
            "path": _display_context_ref(receipt_coverage_file, public_root=public_root),
            "status": "read_for_freshness_context",
        },
        "input_fingerprints": input_fingerprints,
        "stale_receipt_count": len(stale_codes),
        "stale_receipt_codes": stale_codes,
        "acceptance_summary_receipt": _display(acceptance_summary_path, public_root=public_root),
        "acceptance_summary_status": acceptance_summary["status"],
        "secret_exclusion_scan": scan,
        "anti_claim": "Fixture freshness validates manifest, fixture, and receipt presence/fingerprints only; it does not authorize Lean/Lake beyond the bounded public witness fixture, hosted release operations, credentialed provider calls, or secret export.",
        "authority_ceiling": {
            "status": PASS,
            "fixture_freshness_authority": "public_receipt_freshness_and_fingerprint_summary_only",
            "lean_lake_authorized": "bounded_public_witness_only",
            "release_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the fixture-freshness command.

    - Teleology: defines the required input/output paths so the checker is invocable as a module from the runtime spine.
    - Guarantee: returns an ArgumentParser requiring --readiness, --negative-matrix, --mission-dag, --receipt-coverage, and --out.
    - Fails: never raises at build time; missing required args trigger argparse's SystemExit only later, during parse_args.
    - When-needed: inspect when the CLI surface (flag names/requirements) of this checker is in question.
    """
    parser = argparse.ArgumentParser(description="Run public fixture freshness")
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--negative-matrix", required=True)
    parser.add_argument("--mission-dag", required=True)
    parser.add_argument("--receipt-coverage", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: run the fixture-freshness check and map its status to a process exit code.

    - Teleology: adapts run_fixture_freshness into a shell/CI-usable command with a pass/fail exit contract.
    - Guarantee: parses argv, runs run_fixture_freshness with a reconstructed command string, writes both receipts, and returns 0 when the receipt status is PASS else 1.
    - Fails: argparse raises SystemExit on missing/invalid args; read/write errors propagate from run_fixture_freshness; substrate gaps return exit 1 (not an exception).
    - When-needed: inspect when wiring this checker into a wave/CI gate and reasoning about its exit semantics.
    - Escalates-to: run_fixture_freshness and receipts/first_wave/*.json.
    """
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.fixture_freshness "
        f"--readiness {args.readiness} --negative-matrix {args.negative_matrix} "
        f"--mission-dag {args.mission_dag} --receipt-coverage {args.receipt_coverage} "
        f"--out {args.out}"
    )
    receipt = run_fixture_freshness(
        args.readiness,
        args.negative_matrix,
        args.mission_dag,
        args.receipt_coverage,
        args.out,
        command=command,
    )
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
