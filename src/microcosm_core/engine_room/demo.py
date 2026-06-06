"""Staged Engine Room composition demo.

The shared Microcosm organ registry and generated atlas are separate authority
surfaces. This runner stays inside the staged Engine Room capsule lane and
executes each public fixture exercise in sequence without mutating shared
registry, ORGANS, acceptance, or atlas files.
"""

from __future__ import annotations

import argparse
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "engine_room_demo_v1"
ORGAN_ID = "engine_room_demo"
CLAIM_CEILING = (
    "Sequential public fixture runner for staged Engine Room capsules. It is "
    "not shared organ-registry integration, not acceptance authority, and not "
    "a release gate."
)

EXPECTED_JEWEL_TARGETS = frozenset(
    {
        "lean_and_or_proof_search",
        "lean_statement_only_hammer",
        "lean_adversarial_ablation",
        "lean_blind_tactic_policy",
        "metabolism_runtime",
        "metabolism_reconciler",
        "command_run_singleflight",
        "generated_projection_drift_gate",
        "derived_fact_provider_engine",
        "public_projection_leak_gate",
        "egress_self_compliance_gate",
        "navigation_fitness_benchmark",
        "bridge_campaign_dag",
        "annex_knowledge_router",
    }
)


@dataclass(frozen=True)
class CapsuleExercise:
    capsule_id: str
    module_name: str
    input_dir: str
    jewel_targets: tuple[str, ...]
    evaluator_name: str = "evaluate_fixture_dir"
    cli_subcommand: str = "evaluate-fixtures"

    @property
    def public_exercise(self) -> str:
        return (
            f"PYTHONPATH=src python3 -m {self.module_name} {self.cli_subcommand} "
            f"--input {self.input_dir} --json"
        )


CAPSULES: tuple[CapsuleExercise, ...] = (
    CapsuleExercise(
        "engine_room_lean_proof_search_lab",
        "microcosm_core.engine_room.lean_proof_search_lab",
        "fixtures/first_wave/engine_room_lean_proof_search_lab/input",
        (
            "lean_and_or_proof_search",
            "lean_statement_only_hammer",
            "lean_adversarial_ablation",
            "lean_blind_tactic_policy",
        ),
    ),
    CapsuleExercise(
        "engine_room_metabolism_runtime",
        "microcosm_core.engine_room.metabolism_runtime",
        "fixtures/first_wave/engine_room_metabolism_runtime/input",
        ("metabolism_runtime", "metabolism_reconciler"),
    ),
    CapsuleExercise(
        "engine_room_command_run_singleflight",
        "microcosm_core.engine_room.command_run_singleflight",
        "fixtures/first_wave/engine_room_command_run_singleflight/input",
        ("command_run_singleflight",),
    ),
    CapsuleExercise(
        "engine_room_generated_projection_drift_gate",
        "microcosm_core.engine_room.generated_projection_drift_gate",
        "fixtures/first_wave/engine_room_generated_projection_drift_gate/input",
        ("generated_projection_drift_gate",),
    ),
    CapsuleExercise(
        "engine_room_derived_fact_provider_engine",
        "microcosm_core.engine_room.derived_fact_provider_engine",
        "fixtures/first_wave/engine_room_derived_fact_provider_engine/input",
        ("derived_fact_provider_engine",),
    ),
    CapsuleExercise(
        "engine_room_public_projection_leak_gate",
        "microcosm_core.engine_room.public_projection_leak_gate",
        "fixtures/first_wave/engine_room_public_projection_leak_gate/input",
        ("public_projection_leak_gate",),
    ),
    CapsuleExercise(
        "engine_room_egress_self_compliance_gate",
        "microcosm_core.engine_room.egress_self_compliance_gate",
        "fixtures/first_wave/engine_room_egress_self_compliance_gate/input",
        ("egress_self_compliance_gate",),
    ),
    CapsuleExercise(
        "engine_room_navigation_fitness_benchmark",
        "microcosm_core.engine_room.navigation_fitness_benchmark",
        "fixtures/first_wave/engine_room_navigation_fitness_benchmark/input",
        ("navigation_fitness_benchmark",),
    ),
    CapsuleExercise(
        "engine_room_bridge_campaign_dag",
        "microcosm_core.engine_room.bridge_campaign_dag",
        "fixtures/first_wave/engine_room_bridge_campaign_dag/input",
        ("bridge_campaign_dag",),
        "validate_fixture_dir",
        "validate-fixtures",
    ),
    CapsuleExercise(
        "engine_room_annex_knowledge_router",
        "microcosm_core.engine_room.annex_knowledge_router",
        "fixtures/first_wave/engine_room_annex_knowledge_router/input",
        ("annex_knowledge_router",),
    ),
)


def default_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _compact_summary(receipt: Mapping[str, Any]) -> dict[str, Any]:
    summary = receipt.get("summary")
    if isinstance(summary, Mapping):
        return dict(summary)
    compact: dict[str, Any] = {}
    for key in ("case_count", "passed_case_count", "status"):
        if key in receipt:
            compact[key] = receipt[key]
    return compact


def _relative_module_path(module_name: str) -> Path:
    return Path("src", *module_name.split(".")).with_suffix(".py")


def _load_json(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else {}


def _extract_ids(rows: Any) -> set[str]:
    ids: set[str] = set()
    if not isinstance(rows, list):
        return ids
    for row in rows:
        if isinstance(row, str):
            ids.add(row)
        elif isinstance(row, Mapping):
            for key in ("organ_id", "id"):
                value = row.get(key)
                if isinstance(value, str):
                    ids.add(value)
                    break
    return ids


def _shared_surface_ids(*, root: Path) -> dict[str, list[str]]:
    registry = _load_json(root / "core" / "organ_registry.json")
    acceptance = _load_json(root / "core" / "acceptance" / "first_wave_acceptance.json")
    atlas = _load_json(root / "core" / "organ_atlas.json")
    return {
        "registry_ids": sorted(_extract_ids(registry.get("implemented_organs"))),
        "acceptance_ids": sorted(_extract_ids(acceptance.get("accepted_current_authority_organs"))),
        "atlas_ids": sorted(_extract_ids(atlas.get("organs"))),
    }


def _capsule_surface_row(exercise: CapsuleExercise, *, root: Path) -> dict[str, Any]:
    expected_paths = {
        "module_source": _relative_module_path(exercise.module_name),
        "fixture_input_dir": Path(exercise.input_dir),
        "fixture_manifest": Path("core", "fixture_manifests", f"{exercise.capsule_id}.fixture_manifest.json"),
        "paper_module": Path("paper_modules", f"{exercise.capsule_id}.md"),
        "standard": Path("standards", f"std_microcosm_{exercise.capsule_id}.json"),
        "test": Path("tests", f"test_{exercise.capsule_id}.py"),
    }
    rows = {
        name: {
            "path": path.as_posix(),
            "exists": (root / path).exists(),
        }
        for name, path in expected_paths.items()
    }
    missing = [name for name, row in rows.items() if not row["exists"]]
    return {
        "capsule_id": exercise.capsule_id,
        "jewel_targets": list(exercise.jewel_targets),
        "surface_status": rows,
        "missing_surface_kinds": missing,
        "status": "pass" if not missing else "fail",
    }


def run_capsule(exercise: CapsuleExercise, *, root: Path) -> dict[str, Any]:
    module = importlib.import_module(exercise.module_name)
    input_dir = root / exercise.input_dir
    if not hasattr(module, exercise.evaluator_name):
        raise AttributeError(f"{exercise.module_name} has no {exercise.evaluator_name}")
    receipt = getattr(module, exercise.evaluator_name)(input_dir)
    return {
        "capsule_id": exercise.capsule_id,
        "module": exercise.module_name,
        "status": receipt.get("status"),
        "case_count": receipt.get("case_count"),
        "passed_case_count": receipt.get("passed_case_count"),
        "jewel_targets": list(exercise.jewel_targets),
        "public_exercise": exercise.public_exercise,
        "summary": _compact_summary(receipt),
    }


def audit_controller_coverage(*, root: Path | None = None, run_exercises: bool = True) -> dict[str, Any]:
    base = root or default_root()
    capsule_rows = [_capsule_surface_row(exercise, root=base) for exercise in CAPSULES]
    covered_targets = {target for exercise in CAPSULES for target in exercise.jewel_targets}
    missing_targets = sorted(EXPECTED_JEWEL_TARGETS - covered_targets)
    unexpected_targets = sorted(covered_targets - EXPECTED_JEWEL_TARGETS)
    missing_surface_capsules = [
        row for row in capsule_rows if row["missing_surface_kinds"]
    ]
    demo_receipt = run_demo(root=base) if run_exercises else None
    shared_ids = _shared_surface_ids(root=base)
    capsule_ids = {exercise.capsule_id for exercise in CAPSULES}
    shared_missing = {
        name: sorted(capsule_ids - set(ids))
        for name, ids in shared_ids.items()
    }
    per_capsule_integrated = all(not values for values in shared_missing.values())
    composition_organ_integrated = all(
        ORGAN_ID in set(ids) for ids in shared_ids.values()
    )
    shared_integrated = per_capsule_integrated or composition_organ_integrated
    staged_pass = (
        not missing_targets
        and not unexpected_targets
        and not missing_surface_capsules
        and (demo_receipt is None or demo_receipt.get("status") == "pass")
    )
    return {
        "schema_version": "engine_room_controller_audit_v1",
        "organ_id": ORGAN_ID,
        "status": "pass" if staged_pass else "fail",
        "controller_completion_status": (
            "staged_capsules_pass_shared_registry_integrated"
            if staged_pass and shared_integrated
            else "staged_capsules_pass_shared_integration_pending"
            if staged_pass
            else "staged_capsules_incomplete"
        ),
        "claim_ceiling": CLAIM_CEILING,
        "expected_jewel_count": len(EXPECTED_JEWEL_TARGETS),
        "covered_jewel_count": len(covered_targets),
        "covered_jewel_targets": sorted(covered_targets),
        "missing_jewel_targets": missing_targets,
        "unexpected_jewel_targets": unexpected_targets,
        "capsule_count": len(CAPSULES),
        "capsule_surface_rows": capsule_rows,
        "missing_surface_capsule_count": len(missing_surface_capsules),
        "shared_registry_mutated": False,
        "shared_surface_ids": shared_ids,
        "shared_surface_missing_capsule_ids": shared_missing,
        "composition_organ_integrated": composition_organ_integrated,
        "per_capsule_shared_integration": per_capsule_integrated,
        "shared_integration_status": "integrated" if shared_integrated else "pending",
        "demo_receipt": demo_receipt,
    }


def run_demo(*, root: Path | None = None, capsule_ids: Sequence[str] = ()) -> dict[str, Any]:
    base = root or default_root()
    selected = set(capsule_ids)
    exercises = [exercise for exercise in CAPSULES if not selected or exercise.capsule_id in selected]
    rows = [run_capsule(exercise, root=base) for exercise in exercises]
    target_ids = sorted({target for exercise in exercises for target in exercise.jewel_targets})
    passed = sum(1 for row in rows if row.get("status") == "pass")
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "status": "pass" if rows and passed == len(rows) else "fail",
        "claim_ceiling": CLAIM_CEILING,
        "capsule_count": len(rows),
        "passed_capsule_count": passed,
        "covered_jewel_count": len(target_ids),
        "covered_jewel_targets": target_ids,
        "shared_registry_mutated": False,
        "registry_integration_status": "staged_capsules_only_shared_integration_blocked_elsewhere",
        "rows": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the staged Engine Room capsule demo.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Execute staged Engine Room fixture exercises.")
    run.add_argument("--root", default=None)
    run.add_argument("--capsule-id", action="append", default=[])
    run.add_argument("--json", action="store_true")

    audit = subparsers.add_parser("audit", help="Audit staged Engine Room controller coverage.")
    audit.add_argument("--root", default=None)
    audit.add_argument("--skip-exercises", action="store_true")
    audit.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "run":
        root = Path(args.root).resolve() if args.root else default_root()
        receipt = run_demo(root=root, capsule_ids=args.capsule_id)
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {receipt['status']} capsules={receipt['passed_capsule_count']}/{receipt['capsule_count']}")
        return 0 if receipt["status"] == "pass" else 1
    if args.command == "audit":
        root = Path(args.root).resolve() if args.root else default_root()
        receipt = audit_controller_coverage(root=root, run_exercises=not args.skip_exercises)
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            print(
                f"{ORGAN_ID}: {receipt['status']} "
                f"targets={receipt['covered_jewel_count']}/{receipt['expected_jewel_count']} "
                f"shared={receipt['shared_integration_status']}"
            )
        return 0 if receipt["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
