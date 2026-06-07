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
    """Resolve the public microcosm-substrate root that anchors all public-relative refs.

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
    return public_relative_path(path, display_root=public_root)


def _display_context_ref(path: Path, *, public_root: Path) -> str:
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
    hasher = hashlib.sha256()
    _update_hash_from_file(hasher, path)
    return hasher.hexdigest()


def _update_hash_from_file(hasher: Any, path: Path) -> None:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            hasher.update(chunk)


def _iter_directory_files(path: Path) -> Iterator[Path]:
    with os.scandir(path) as entries:
        for entry in entries:
            child = path / entry.name
            if entry.is_dir(follow_symlinks=False):
                yield from _iter_directory_files(child)
            elif entry.is_file(follow_symlinks=False):
                yield child


def _sha256_directory(path: Path) -> str:
    hasher = hashlib.sha256()
    for child in sorted(_iter_directory_files(path)):
        relative = child.relative_to(path).as_posix()
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        _update_hash_from_file(hasher, child)
        hasher.update(b"\0")
    return hasher.hexdigest()


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    safe.pop("body_redacted", None)
    safe.pop("redacted_output_field_labels_omitted", None)
    return safe


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _load_registry(public_root: Path) -> dict[str, Any]:
    return read_json_strict(public_root / ORGAN_REGISTRY_REL)


def _accepted_organs(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _accepted_registry_profiles_by_organ(public_root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("organ_id")): row
        for row in _accepted_organs(_load_registry(public_root))
        if row.get("organ_id")
    }


def _evidence_profiles_by_organ(public_root: Path) -> dict[str, dict[str, Any]]:
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
    value = row.get("synthetic_acceptance_disposition")
    if isinstance(value, dict):
        return str(value.get("disposition") or "")
    if isinstance(value, str):
        return value
    return ""


def _is_synthetic_acceptance_row(row: dict[str, Any]) -> bool:
    return (
        row.get("evidence_class") in SYNTHETIC_EVIDENCE_CLASSES
        or row.get("truth_accounting_bucket") in SYNTHETIC_TRUTH_BUCKETS
        or row.get("counts_as_real_substrate_progress") is False
    )


def _disposition_coverage(accepted: list[dict[str, Any]]) -> dict[str, Any]:
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
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))]


def _int_value(value: Any) -> int:
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
    parser = argparse.ArgumentParser(description="Run public fixture freshness")
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--negative-matrix", required=True)
    parser.add_argument("--mission-dag", required=True)
    parser.add_argument("--receipt-coverage", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
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
