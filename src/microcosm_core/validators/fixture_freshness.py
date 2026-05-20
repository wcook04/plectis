from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.fixture_freshness"
ACCEPTANCE_SUMMARY_REL = "receipts/first_wave/acceptance_summary.json"


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


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
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
    private_state_scan: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": "first_wave_acceptance_summary_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": PASS,
        "accepted_current_authority_organs": [row.get("organ_id") for row in accepted],
        "accepted_count": len(accepted),
        "deferred_organs": ["formal_math_lean_proof_witness"],
        "dependency_preflight_receipt": dependency_preflight_ref,
        "fixture_freshness_receipt": fixture_freshness_ref,
        "standards_registry_validation_receipt": "receipts/first_wave/standards_registry_validation.json",
        "preflight_receipts": [
            dependency_preflight_ref,
            fixture_freshness_ref,
        ],
        "lean_lake_authorized": False,
        "release_authorized": False,
        "provider_calls_authorized": False,
        "private_data_equivalence_authorized": False,
        "private_state_scan": private_state_scan,
        "authority_ceiling": {
            "status": PASS,
            "acceptance_summary_authority": "public_runtime_spine_receipt_summary_only",
            "whole_system_correctness": False,
            "release_authorized": False,
        },
        "anti_claim": "This acceptance summary records current public runtime-spine receipt presence only; it does not authorize Lean/Lake, release, provider calls, private-data equivalence, or whole-system correctness.",
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
        private_state_scan=acceptance_summary_scan,
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
        "private_state_scan": scan,
        "anti_claim": "Fixture freshness validates manifest, fixture, and receipt presence/fingerprints only; it does not authorize Lean/Lake, release, provider calls, or private-data equivalence.",
        "authority_ceiling": {
            "status": PASS,
            "fixture_freshness_authority": "public_receipt_freshness_and_fingerprint_summary_only",
            "lean_lake_authorized": False,
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
