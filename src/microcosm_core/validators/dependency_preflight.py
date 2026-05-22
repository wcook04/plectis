from __future__ import annotations

import argparse
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
from microcosm_core.runtime_shell import RUNTIME_STEPS
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.dependency_preflight"
ACCEPTED_ORGAN_IDS = [step.organ_id for step in RUNTIME_STEPS]
ACCEPTANCE_PLAN_REL = Path("core/acceptance/first_wave_acceptance.json")
AUTHORITY_SNAPSHOT_REL = Path("receipts/runtime_shell/public_authority_map.json")
EVIDENCE_CLASS_REGISTRY_REL = Path("core/organ_evidence_classes.json")
DEFERRED_ORGAN_IDS = ["formal_math_lean_proof_organ"]


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _organ_registry(public_root: Path) -> dict[str, Any]:
    return read_json_strict(public_root / "core/organ_registry.json")


def _accepted_from_registry(registry: dict[str, Any]) -> list[str]:
    return [
        str(row.get("organ_id"))
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _fixture_input_exists(public_root: Path, rel: str) -> bool:
    return (public_root / rel).exists()


def _public_fixture_manifest(public_root: Path, organ_id: str, row: dict[str, Any]) -> Path:
    macro_manifest = Path(str(row.get("fixture_manifest") or ""))
    manifest_name = macro_manifest.name or f"{organ_id}.fixture_manifest.json"
    manifest_path = public_root / "core/fixture_manifests" / manifest_name
    if manifest_path.is_file():
        return manifest_path
    canonical_path = (
        public_root / "core/fixture_manifests" / f"{organ_id}.fixture_manifest.json"
    )
    return canonical_path if canonical_path.is_file() else manifest_path


def _public_manifest_inputs(manifest_path: Path) -> list[str]:
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


def _negative_case_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("negative_cases", "cases", "rows"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return len(rows)
        return sum(1 for value in payload.values() if isinstance(value, (dict, list)))
    return 0


def _id_counts(ids: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in ids:
        counts[item] = counts.get(item, 0) + 1
    return counts


def _duplicates(ids: list[str]) -> list[str]:
    return sorted(item for item, count in _id_counts(ids).items() if count > 1)


def _accepted_plan_organs(public_root: Path) -> list[str]:
    path = public_root / ACCEPTANCE_PLAN_REL
    if not path.is_file():
        return []
    payload = read_json_strict(path)
    return [
        str(row.get("organ_id"))
        for row in _rows(payload, "accepted_current_authority_organs")
        if row.get("organ_id")
    ]


def _evidence_class_rows(public_root: Path) -> list[dict[str, Any]]:
    path = public_root / EVIDENCE_CLASS_REGISTRY_REL
    if not path.is_file():
        return []
    payload = read_json_strict(path)
    return _rows(payload, "organ_evidence_classes")


def _authority_snapshot(public_root: Path) -> dict[str, Any]:
    path = public_root / AUTHORITY_SNAPSHOT_REL
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _surface_mentions_organ(surface: dict[str, Any], organ_id: str) -> bool:
    slug = organ_id.replace("_", "-")
    text = " ".join(
        str(surface.get(key) or "")
        for key in ("surface_id", "command", "endpoint", "authority_role")
    )
    return organ_id in text or slug in text


def _add_lifecycle_defect(
    defects: list[dict[str, Any]],
    defect_id: str,
    *,
    organ_id: str | None = None,
    surface: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    defect: dict[str, Any] = {"defect_id": defect_id}
    if organ_id is not None:
        defect["organ_id"] = organ_id
    if surface is not None:
        defect["surface"] = surface
    if detail:
        defect["detail"] = detail
    defects.append(defect)


def _consumer_contract_row(
    surface_id: str,
    *,
    required_for_organ_ids: list[str],
    observed_organ_ids: list[str],
    owner_surface: str,
    receipt_ref: str | None = None,
) -> dict[str, Any]:
    missing = [
        organ_id for organ_id in required_for_organ_ids if organ_id not in observed_organ_ids
    ]
    stale = [
        organ_id for organ_id in observed_organ_ids if organ_id not in required_for_organ_ids
    ]
    row: dict[str, Any] = {
        "surface_id": surface_id,
        "status": PASS if not missing and not stale else "blocked",
        "required_for_organ_ids": required_for_organ_ids,
        "observed_organ_ids": observed_organ_ids,
        "missing_organ_ids": missing,
        "stale_organ_ids": stale,
        "owner_surface": owner_surface,
    }
    if receipt_ref is not None:
        row["receipt_ref"] = receipt_ref
    return row


def _organ_lifecycle_convergence(
    *,
    accepted: list[str],
    runtime_ids: list[str],
    accepted_plan_ids: list[str],
    evidence_ids: list[str],
    organ_authority_ids: list[str],
    command_path_organs: set[str],
    public_lens_organs: set[str],
    fixture_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    fixture_pass_ids = [
        str(row.get("organ_id"))
        for row in fixture_checks
        if row.get("organ_id") and row.get("status") == PASS
    ]
    ordered_command_path_organs = [
        organ_id for organ_id in accepted if organ_id in command_path_organs
    ]
    ordered_public_lens_organs = [
        organ_id for organ_id in accepted if organ_id in public_lens_organs
    ]
    consumer_surfaces = [
        _consumer_contract_row(
            "runtime_steps",
            required_for_organ_ids=accepted,
            observed_organ_ids=runtime_ids,
            owner_surface="microcosm_core.runtime_shell.RUNTIME_STEPS",
        ),
        _consumer_contract_row(
            "first_wave_acceptance_plan",
            required_for_organ_ids=accepted,
            observed_organ_ids=accepted_plan_ids,
            owner_surface=ACCEPTANCE_PLAN_REL.as_posix(),
        ),
        _consumer_contract_row(
            "organ_evidence_class_registry",
            required_for_organ_ids=accepted,
            observed_organ_ids=evidence_ids,
            owner_surface=EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        ),
        _consumer_contract_row(
            "public_authority_organ_rows",
            required_for_organ_ids=accepted,
            observed_organ_ids=organ_authority_ids,
            owner_surface="RuntimeShell.authority().organ_authority",
            receipt_ref=AUTHORITY_SNAPSHOT_REL.as_posix(),
        ),
        _consumer_contract_row(
            "public_command_lens_rows",
            required_for_organ_ids=ordered_command_path_organs,
            observed_organ_ids=ordered_public_lens_organs,
            owner_surface="RuntimeShell.authority().surface_authority",
            receipt_ref=AUTHORITY_SNAPSHOT_REL.as_posix(),
        ),
        _consumer_contract_row(
            "fixture_bundle_checks",
            required_for_organ_ids=accepted,
            observed_organ_ids=fixture_pass_ids,
            owner_surface="core/fixture_manifests/*.fixture_manifest.json",
        ),
    ]
    affected_surfaces = [
        row["surface_id"] for row in consumer_surfaces if row["status"] != PASS
    ]
    affected_organs = sorted(
        {
            organ_id
            for row in consumer_surfaces
            if row["status"] != PASS
            for organ_id in [*row["missing_organ_ids"], *row["stale_organ_ids"]]
        }
    )
    return {
        "schema_version": "organ_lifecycle_convergence_v1",
        "status": PASS if not affected_surfaces else "blocked",
        "source_registry_ref": "core/organ_registry.json",
        "evidence_registry_ref": EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
        "organ_count": len(accepted),
        "consumer_surfaces": consumer_surfaces,
        "affected_consumer_surfaces": affected_surfaces,
        "changed_organ_ids": affected_organs,
        "negative_guard_surface_refs": [
            "non-consumer notes, demos, and incidental receipts are excluded from the "
            "organ lifecycle contract unless listed in checked_surfaces"
        ],
        "false_positive_guard_result": PASS if not affected_surfaces else "not_applicable",
        "required_snapshot_refs": [
            AUTHORITY_SNAPSHOT_REL.as_posix(),
            "receipts/preflight/dependency_preflight.json",
        ],
        "incidental_receipt_churn_excluded": True,
        "validation_refs": [
            "microcosm_core.validators.dependency_preflight",
            "tests/test_dependency_preflight.py",
        ],
        "public_authority_boundary": (
            "consumer-contract convergence only; not release, source, proof, or "
            "provider-call authority"
        ),
        "release_authority": False,
        "proof_authority": False,
        "source_body_exported": False,
        "next_reentry_condition": (
            "rerun dependency preflight after accepted organ, evidence-class, "
            "runtime-step, public authority, or fixture-manifest changes"
        ),
    }


def _organ_lifecycle_coverage(
    public_root: Path,
    registry: dict[str, Any],
    *,
    accepted: list[str],
    fixture_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    runtime_ids = list(ACCEPTED_ORGAN_IDS)
    accepted_plan_ids = _accepted_plan_organs(public_root)
    evidence_rows = _evidence_class_rows(public_root)
    evidence_ids = [str(row.get("organ_id")) for row in evidence_rows if row.get("organ_id")]
    evidence_class_by_id = {
        str(row.get("organ_id")): str(row.get("evidence_class"))
        for row in evidence_rows
        if row.get("organ_id")
    }
    registry_rows_by_id = {
        str(row.get("organ_id")): row
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority" and row.get("organ_id")
    }
    authority = _authority_snapshot(public_root)
    surface_rows = _rows(authority, "surface_authority")
    organ_authority_rows = _rows(authority, "organ_authority")
    organ_authority_ids = [
        str(row.get("organ_id")) for row in organ_authority_rows if row.get("organ_id")
    ]
    command_path = [
        str(command) for command in authority.get("command_path", []) if isinstance(command, str)
    ]

    defects: list[dict[str, Any]] = []

    for organ_id in sorted(set(accepted) - set(runtime_ids)):
        _add_lifecycle_defect(defects, "accepted_without_runtime_step", organ_id=organ_id)
    for organ_id in sorted(set(runtime_ids) - set(accepted)):
        _add_lifecycle_defect(defects, "runtime_step_without_accepted_organ", organ_id=organ_id)
    if accepted and set(accepted) == set(runtime_ids):
        accepted_order_status = PASS
    else:
        accepted_order_status = "blocked"

    for organ_id in sorted(set(accepted) - set(accepted_plan_ids)):
        _add_lifecycle_defect(defects, "accepted_without_acceptance_plan", organ_id=organ_id)
    for organ_id in sorted(set(accepted_plan_ids) - set(accepted)):
        _add_lifecycle_defect(defects, "acceptance_plan_without_accepted_organ", organ_id=organ_id)

    for organ_id in sorted(set(accepted) - set(evidence_ids)):
        _add_lifecycle_defect(defects, "missing_evidence_class", organ_id=organ_id)
    for organ_id in sorted(set(evidence_ids) - set(accepted)):
        _add_lifecycle_defect(defects, "evidence_class_without_accepted_organ", organ_id=organ_id)
    for organ_id in _duplicates(evidence_ids):
        _add_lifecycle_defect(defects, "duplicate_evidence_class", organ_id=organ_id)

    fixture_by_id = {str(row.get("organ_id")): row for row in fixture_checks}
    for organ_id in accepted:
        row = fixture_by_id.get(organ_id, {})
        if row.get("status") != PASS:
            _add_lifecycle_defect(
                defects,
                "missing_fixture_bundle",
                organ_id=organ_id,
                detail={
                    "missing_fixture_inputs": row.get("missing_fixture_inputs", []),
                    "fixture_manifest": row.get("fixture_manifest"),
                },
            )
        registry_row = registry_rows_by_id.get(organ_id, {})
        if not registry_row.get("generated_receipts"):
            _add_lifecycle_defect(defects, "missing_receipt_ref", organ_id=organ_id)

    if not authority:
        _add_lifecycle_defect(
            defects,
            "missing_snapshot_projection",
            surface=AUTHORITY_SNAPSHOT_REL.as_posix(),
        )
    else:
        surface_counts = authority.get("surface_counts", {})
        declared_surface_count = (
            surface_counts.get("surface_authority_count")
            if isinstance(surface_counts, dict)
            else None
        )
        declared_organ_count = (
            surface_counts.get("organ_authority_count")
            if isinstance(surface_counts, dict)
            else None
        )
        if declared_surface_count != len(surface_rows):
            _add_lifecycle_defect(
                defects,
                "stale_surface_authority_count",
                detail={
                    "declared_surface_authority_count": declared_surface_count,
                    "actual_surface_authority_count": len(surface_rows),
                },
            )
        if declared_organ_count != len(organ_authority_rows):
            _add_lifecycle_defect(
                defects,
                "stale_organ_authority_count",
                detail={
                    "declared_organ_authority_count": declared_organ_count,
                    "actual_organ_authority_count": len(organ_authority_rows),
                },
            )
        if len(surface_rows) != len(accepted):
            _add_lifecycle_defect(
                defects,
                "stale_expected_surface_count",
                detail={
                    "surface_authority_count": len(surface_rows),
                    "accepted_organ_count": len(accepted),
                },
            )
        for organ_id in sorted(set(accepted) - set(organ_authority_ids)):
            _add_lifecycle_defect(defects, "missing_snapshot_projection", organ_id=organ_id)
        for organ_id in sorted(set(organ_authority_ids) - set(accepted)):
            _add_lifecycle_defect(defects, "snapshot_projection_without_organ", organ_id=organ_id)
        for organ_id in _duplicates(organ_authority_ids):
            _add_lifecycle_defect(defects, "duplicate_snapshot_projection", organ_id=organ_id)

        command_path_organs = {
            organ_id
            for organ_id in accepted
            if any(organ_id.replace("_", "-") in command for command in command_path)
        }
        public_lens_organs = {
            organ_id
            for organ_id in command_path_organs
            if any(_surface_mentions_organ(surface, organ_id) for surface in surface_rows)
        }
        for organ_id in sorted(command_path_organs):
            if organ_id not in public_lens_organs:
                _add_lifecycle_defect(defects, "missing_public_lens", organ_id=organ_id)
    if not authority:
        command_path_organs = set()
        public_lens_organs = set()

    for organ_id, evidence_class in sorted(evidence_class_by_id.items()):
        if evidence_class != "external_subprocess_witness":
            continue
        registry_row = registry_rows_by_id.get(organ_id, {})
        if not registry_row.get("current_authority_receipt") or not registry_row.get(
            "generated_receipts"
        ):
            _add_lifecycle_defect(
                defects,
                "external_subprocess_witness_without_tool_receipt",
                organ_id=organ_id,
            )

    coverage_counts = {
        "accepted_organ_count": len(accepted),
        "runtime_step_count": len(runtime_ids),
        "acceptance_plan_organ_count": len(accepted_plan_ids),
        "evidence_class_row_count": len(evidence_ids),
        "organ_authority_row_count": len(organ_authority_ids),
        "surface_authority_row_count": len(surface_rows),
        "fixture_check_count": len(fixture_checks),
    }
    convergence = _organ_lifecycle_convergence(
        accepted=accepted,
        runtime_ids=runtime_ids,
        accepted_plan_ids=accepted_plan_ids,
        evidence_ids=evidence_ids,
        organ_authority_ids=organ_authority_ids,
        command_path_organs=command_path_organs,
        public_lens_organs=public_lens_organs,
        fixture_checks=fixture_checks,
    )
    return {
        "schema_version": "organ_lifecycle_coverage_v1",
        "status": PASS if not defects else "blocked",
        "defect_count": len(defects),
        "defects": defects,
        "accepted_order_status": accepted_order_status,
        "coverage_counts": coverage_counts,
        "organ_lifecycle_convergence": convergence,
        "checked_surfaces": [
            "core/organ_registry.json",
            ACCEPTANCE_PLAN_REL.as_posix(),
            EVIDENCE_CLASS_REGISTRY_REL.as_posix(),
            AUTHORITY_SNAPSHOT_REL.as_posix(),
            "core/fixture_manifests/*.fixture_manifest.json",
            "fixtures/first_wave/<organ_id>/input",
        ],
        "required_invariants": [
            "accepted organ ids equal RuntimeShell.RUNTIME_STEPS ids",
            "accepted organ ids match first-wave acceptance rows",
            "accepted organ ids have exactly one evidence-class row",
            "accepted organ ids have public authority snapshot rows",
            "public command-path organs have a matching public lens row",
            "fixture manifests and fixture inputs exist for accepted organs",
            "external subprocess witnesses carry tool/receipt evidence refs",
        ],
        "anti_claim": (
            "Organ lifecycle coverage checks public convergence only; it does not "
            "authorize release, provider calls, source mutation, or private-data "
            "equivalence."
        ),
    }


def run_dependency_preflight(
    readiness_path: str | Path,
    negative_matrix_path: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    output_file = Path(out_path)
    public_root = _public_root_for_path(output_file)
    readiness_file = Path(readiness_path)
    negative_matrix_file = Path(negative_matrix_path)
    readiness = read_json_strict(readiness_file)
    negative_matrix = read_json_strict(negative_matrix_file)
    registry = _organ_registry(public_root)

    accepted = _accepted_from_registry(registry)
    readiness_by_id = {
        str(row.get("organ_id")): row for row in _rows(readiness, "organ_readiness")
    }
    blocked_codes: list[str] = []
    fixture_checks: list[dict[str, Any]] = []
    dependency_checks: list[dict[str, Any]] = []
    for organ_id in accepted:
        row = readiness_by_id.get(organ_id, {})
        public_manifest = _public_fixture_manifest(public_root, organ_id, row)
        manifest_inputs = _public_manifest_inputs(public_manifest)
        missing_deps = [
            dep
            for dep in row.get("build_dependencies", [])
            if dep not in accepted and dep not in DEFERRED_ORGAN_IDS
        ]
        if missing_deps:
            blocked_codes.append("MISSING_ACCEPTED_BUILD_DEPENDENCY")
        dependency_checks.append(
            {
                "organ_id": organ_id,
                "build_dependencies": row.get("build_dependencies", []),
                "missing_dependencies": missing_deps,
                "status": PASS if not missing_deps else "blocked",
            }
        )
        macro_fixture_inputs = [str(path) for path in row.get("fixture_inputs", [])]
        fixture_inputs = manifest_inputs or macro_fixture_inputs
        missing_inputs = [
            rel for rel in fixture_inputs if not _fixture_input_exists(public_root, rel)
        ]
        if missing_inputs:
            blocked_codes.append("MISSING_FIXTURE_INPUT")
        fixture_checks.append(
            {
                "organ_id": organ_id,
                "fixture_id": row.get("fixture_id"),
                "fixture_manifest": _display(public_manifest, public_root=public_root)
                if public_manifest.is_file()
                else None,
                "input_source": "public_fixture_manifest"
                if manifest_inputs
                else "macro_readiness_fixture_inputs",
                "macro_fixture_input_ref_count": len(macro_fixture_inputs),
                "fixture_input_count": len(fixture_inputs),
                "missing_fixture_inputs": missing_inputs,
                "status": PASS if not missing_inputs else "blocked",
            }
        )

    missing_runtime_ids = [organ_id for organ_id in accepted if organ_id not in ACCEPTED_ORGAN_IDS]
    runtime_only_ids = [organ_id for organ_id in ACCEPTED_ORGAN_IDS if organ_id not in accepted]
    wave_order_checks = {
        "status": PASS
        if not missing_runtime_ids and not runtime_only_ids
        else "blocked_wave_order_mismatch",
        "expected_runtime_ids": ACCEPTED_ORGAN_IDS,
        "observed_accepted_order": accepted,
        "accepted_without_runtime_step": missing_runtime_ids,
        "runtime_step_without_accepted_organ": runtime_only_ids,
    }
    if wave_order_checks["status"] != PASS:
        blocked_codes.append("ACCEPTED_ORGAN_ORDER_MISMATCH")

    lifecycle_coverage = _organ_lifecycle_coverage(
        public_root,
        registry,
        accepted=accepted,
        fixture_checks=fixture_checks,
    )
    if lifecycle_coverage["status"] != PASS:
        blocked_codes.append("ORGAN_LIFECYCLE_COVERAGE_DEFECT")

    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
            [readiness_file, negative_matrix_file, public_root / "core/organ_registry.json"],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    if scan["blocking_hit_count"]:
        blocked_codes.append("PRIVATE_STATE_SCAN_BLOCKED")

    blocked_codes = sorted(set(blocked_codes))
    status = PASS if not blocked_codes else "blocked"
    receipt = {
        "schema_version": "dependency_preflight_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "checked_organs": accepted,
        "toolchain_checks": {
            "python_validator_runtime": PASS,
            "lean_lake_execution": "bounded_public_witness_only",
            "provider_calls": "not_authorized",
            "trading_or_financial_advice": "not_authorized",
        },
        "fixture_precondition_checks": fixture_checks,
        "wave_order_checks": wave_order_checks,
        "organ_lifecycle_coverage": lifecycle_coverage,
        "dependency_checks": dependency_checks,
        "negative_matrix_case_count": _negative_case_count(negative_matrix),
        "blocked_dependency_count": len(blocked_codes),
        "blocked_dependency_codes": blocked_codes,
        "anti_claim": "Dependency preflight validates accepted public runtime-spine ordering and fixture presence only; it does not authorize Lean/Lake beyond the bounded public witness fixture, hosted release operations, credentialed provider calls, or secret export.",
        "private_state_scan": scan,
        "authority_ceiling": {
            "status": PASS,
            "dependency_preflight_authority": "accepted_public_runtime_spine_preflight_only",
            "lean_lake_authorized": "bounded_public_witness_only",
            "trading_or_financial_advice_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "receipt_paths": [_display(output_file, public_root=public_root)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run public dependency preflight")
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--negative-matrix", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.dependency_preflight "
        f"--readiness {args.readiness} --negative-matrix {args.negative_matrix} --out {args.out}"
    )
    receipt = run_dependency_preflight(
        args.readiness,
        args.negative_matrix,
        args.out,
        command=command,
    )
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
