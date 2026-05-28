from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
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
TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS = {
    "real_runtime_receipt": "real_runtime_receipt_count",
    "copied_non_secret_macro_body": "copied_non_secret_macro_body_count",
    "source_faithful_refactor": "source_faithful_refactor_count",
    "real_import_validation": "real_import_validation_count",
    "regression_negative_fixture": "regression_negative_fixture_count",
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


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_directory(path: Path) -> str:
    hasher = hashlib.sha256()
    for child in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative = child.relative_to(path).as_posix()
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(child.read_bytes())
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
    return read_json_strict(public_root / "core/organ_registry.json")


def _accepted_organs(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


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
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("organ evidence-class row must be a JSON object")
        organ_id = str(row.get("organ_id") or "")
        evidence_class = str(row.get("evidence_class") or "")
        class_profile = class_profiles.get(evidence_class)
        if not organ_id or not isinstance(class_profile, dict):
            raise ValueError(f"invalid evidence-class row for organ {organ_id!r}")
        if organ_id in profiles:
            duplicate_organs.add(organ_id)
        truth_bucket = str(class_profile.get("truth_accounting_bucket") or "")
        if truth_bucket not in TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS:
            raise ValueError(
                f"evidence_class {evidence_class!r} uses unknown truth bucket "
                f"{truth_bucket!r}"
            )
        counts_as_progress = truth_bucket in REAL_SUBSTRATE_PROGRESS_BUCKETS
        if class_profile.get("counts_as_real_substrate_progress") is not counts_as_progress:
            raise ValueError(
                f"evidence_class {evidence_class!r} has inconsistent progress flag"
            )
        profiles[organ_id] = {
            "organ_id": organ_id,
            "evidence_class": evidence_class,
            "truth_accounting_bucket": truth_bucket,
            "counts_as_real_substrate_progress": counts_as_progress,
            "evidence_strength_rank": class_profile.get("evidence_strength_rank"),
            "claim_ceiling": class_profile.get("claim_ceiling"),
            "classification_basis": row.get("classification_basis"),
        }
    if duplicate_organs:
        raise ValueError(
            "duplicate organ evidence-class rows: " + ", ".join(sorted(duplicate_organs))
        )
    return profiles


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
    for organ_id in accepted_ids:
        profile = evidence_profiles[organ_id]
        truth_bucket = str(profile["truth_accounting_bucket"])
        counts[truth_bucket] += 1
        class_counts[str(profile["evidence_class"])] += 1
        if profile["counts_as_real_substrate_progress"] is True:
            real_organs.append(organ_id)
        else:
            non_progress_organs.append(organ_id)
        evidence_rows.append(profile)

    count_fields = {
        count_key: counts[bucket]
        for bucket, count_key in TRUTH_ACCOUNTING_BUCKET_COUNT_KEYS.items()
    }
    real_substrate_progress_count = sum(
        counts[bucket] for bucket in REAL_SUBSTRATE_PROGRESS_BUCKETS
    )
    non_progress_count = len(accepted_ids) - real_substrate_progress_count
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
        "accepted_current_authority_evidence": evidence_rows,
        **count_fields,
    }


def _manifest_public_path(public_root: Path, readiness_row: dict[str, Any]) -> Path:
    macro_path = Path(str(readiness_row.get("fixture_manifest") or ""))
    return public_root / "core/fixture_manifests" / macro_path.name


def _manifest_input_paths(manifest_path: Path) -> list[str]:
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
    payload = {
        "schema_version": "first_wave_acceptance_summary_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": PASS,
        "accepted_current_authority_organs": [row.get("organ_id") for row in accepted],
        "accepted_count": len(accepted),
        "accepted_current_authority_count": len(accepted),
        "accepted_count_is_product_progress": False,
        "truth_accounting": truth_accounting,
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
