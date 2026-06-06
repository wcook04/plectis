from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch10_cold_eval_honesty_capsule"
FIXTURE_ID = "first_wave.batch10_cold_eval_honesty_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch10_cold_eval_honesty_capsule"

RESULT_NAME = "batch10_cold_eval_honesty_capsule_result.json"
BOARD_NAME = "batch10_cold_eval_honesty_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch10_cold_eval_honesty_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch10_cold_eval_honesty_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch10_cold_eval_honesty_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch10_cold_eval_honesty_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch10_cold_eval_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "cold_eval_original_runner",
    "cold_eval_scorecard_shape_audit",
    "cold_eval_claim_ceiling_gate",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_tasks": ("BATCH10_COLD_EVAL_TASKS_REQUIRED",),
    "flat_route_can_win": ("BATCH10_COLD_EVAL_NOT_ALWAYS_B_WIN",),
    "expected_ref_injection": ("BATCH10_COLD_EVAL_EXPECTED_REF_INJECTION_FORBIDDEN",),
    "private_fixture_ref": ("BATCH10_COLD_EVAL_PRIVATE_REF_REJECTED",),
}

NEGATIVE_CASE_CODES = {
    case_id: codes[0] for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch10_cold_eval_honesty_not_benchmark_or_navigation_truth",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "source_mutation_authorized": False,
    "benchmark_win_claim": False,
    "live_agent_result_claim": False,
    "navigation_truth_authority": False,
}

ANTI_CLAIM = (
    "Batch 10 Cold Eval Honesty imports and runs the real idea_microcosm "
    "cold_eval.py route-quality simulator over public fixtures, then audits "
    "the scorecard shape and claim ceiling. It is not a live agent benchmark, "
    "not navigation truth, not public release approval, and not proof that "
    "idea-first routing wins outside this deterministic fixture."
)

SOURCE_REQUIRED_ANCHORS = {
    "self-indexing-cognitive-substrate/src/idea_microcosm/cold_eval.py": (
        "SCORING_POLICY =",
        "def _score_task(",
        "def run_cold_eval(",
        "expected_ref_injection_used",
        "idea_first_packet_wins_fixture",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 10 Cold Eval Honesty Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch10_cold_eval_honesty_capsule/"
        "exported_batch10_cold_eval_honesty_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _copied_cold_eval(public_root: Path) -> Path:
    return (
        public_root
        / "examples/batch10_cold_eval_honesty_capsule/"
        "exported_batch10_cold_eval_honesty_capsule_bundle/source_modules/"
        "self-indexing-cognitive-substrate/src/idea_microcosm/cold_eval.py"
    )


def _load_cold_eval(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("batch10_copied_cold_eval", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load copied cold_eval module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["batch10_copied_cold_eval"] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _walk_strings(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        values: list[str] = []
        for child in payload.values():
            values.extend(_walk_strings(child))
        return values
    if isinstance(payload, list):
        values = []
        for child in payload:
            values.extend(_walk_strings(child))
        return values
    return [payload] if isinstance(payload, str) else []


def _workspace_source(input_path: Path) -> Path:
    return input_path / "cold_eval_workspace"


def _run_original_cold_eval(input_path: Path, public_root: Path) -> dict[str, Any]:
    module = _load_cold_eval(_copied_cold_eval(public_root))
    source_workspace = _workspace_source(input_path)
    if not (source_workspace / "evals/cold_agent_ab/tasks.json").is_file():
        return {
            "status": "blocked",
            "engine_id": "cold_eval_original_runner",
            "error_code": "BATCH10_COLD_EVAL_TASKS_REQUIRED",
            "body_in_receipt": False,
        }

    with tempfile.TemporaryDirectory(prefix="batch10_cold_eval_") as temp_dir:
        temp_root = Path(temp_dir) / "workspace"
        shutil.copytree(source_workspace, temp_root)
        result = module.run_cold_eval(
            temp_root,
            output_path="runs/cold_agent_ab/seed_scorecard.json",
            write_receipt=True,
            at="2026-05-31T00:00:00Z",
        )
        scorecard = _load_json(temp_root / "runs/cold_agent_ab/seed_scorecard.json")
        receipt = _load_json(temp_root / "receipts/cold_agent_ab_seed.json")

    summary = scorecard.get("summary", {})
    rows = scorecard.get("rows", [])
    winners = summary.get("winner_by_task", [])
    return {
        "status": "pass" if result.get("status") == "ok" and rows else "blocked",
        "engine_id": "cold_eval_original_runner",
        "source_relation": "exact_copied_macro_body_invoked",
        "result_status": result.get("status"),
        "task_count": result.get("task_count"),
        "row_count": len(rows) if isinstance(rows, list) else 0,
        "idea_first_win_count": result.get("idea_first_win_count"),
        "flat_repo_win_count": result.get("flat_repo_win_count"),
        "tie_count": result.get("tie_count"),
        "winner_by_task": winners,
        "scoring_policy": scorecard.get("scoring_policy"),
        "receipt_status": receipt.get("status"),
        "body_in_receipt": False,
    }


def _scorecard_shape_audit(original: Mapping[str, Any], input_path: Path) -> dict[str, Any]:
    tasks_path = _workspace_source(input_path) / "evals/cold_agent_ab/tasks.json"
    tasks_payload = _load_json(tasks_path) if tasks_path.is_file() else {}
    private_hits = [
        value
        for value in _walk_strings(tasks_payload)
        if "/Users/" in value or "src/ai_workflow" in value
    ]
    winners = original.get("winner_by_task") if isinstance(original.get("winner_by_task"), list) else []
    all_b_wins = bool(winners) and all(
        isinstance(row, Mapping) and row.get("winner") == "B.idea_first_packet"
        for row in winners
    )
    route_sources = tasks_payload.get("route_source_summary", {})
    flat_route_count = int(route_sources.get("flat_route_ref_count", 0) or 0)
    idea_route_count = int(route_sources.get("idea_route_ref_count", 0) or 0)
    return {
        "status": "pass" if all_b_wins and idea_route_count > flat_route_count and not private_hits else "blocked",
        "engine_id": "cold_eval_scorecard_shape_audit",
        "all_winners_are_idea_first": all_b_wins,
        "flat_route_ref_count": flat_route_count,
        "idea_route_ref_count": idea_route_count,
        "route_surface_asymmetry_visible": idea_route_count > flat_route_count,
        "private_fixture_ref_count": len(private_hits),
        "claim_language": "fixture_route_scorecard_reports_all_B_wins_but_capsule_does_not_upgrade_that_to_benchmark_truth",
        "body_in_receipt": False,
    }


def _claim_ceiling_gate(original: Mapping[str, Any], input_path: Path) -> dict[str, Any]:
    manifest = _load_json(input_path / EXERCISE_MANIFEST_NAME)
    omitted_claims = manifest.get("forbidden_claims", [])
    required_forbidden = {
        "live_agent_benchmark_win",
        "navigation_truth",
        "release_approval",
        "hosted_public_readiness",
    }
    rows_checked = original.get("row_count", 0)
    no_expected_ref_injection = manifest.get("expected_ref_injection_allowed") is False
    return {
        "status": "pass"
        if rows_checked
        and no_expected_ref_injection
        and required_forbidden.issubset(set(omitted_claims))
        else "blocked",
        "engine_id": "cold_eval_claim_ceiling_gate",
        "row_count_checked": rows_checked,
        "expected_ref_injection_allowed": manifest.get("expected_ref_injection_allowed"),
        "required_forbidden_claims_present": sorted(required_forbidden.intersection(set(omitted_claims))),
        "claim_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "body_in_receipt": False,
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    original = _run_original_cold_eval(input_path, public_root)
    shape = _scorecard_shape_audit(original, input_path)
    ceiling = _claim_ceiling_gate(original, input_path)
    engines = [original, shape, ceiling]
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    str(engine.get("error_code") or "BATCH10_COLD_EVAL_ENGINE_BLOCKED"),
                    "A Batch-10 cold-eval engine did not pass.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in engines}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "BATCH10_COLD_EVAL_ENGINE_MISSING",
                "A Batch-10 expected engine is missing from the exercise result.",
                observed=missing,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(engines),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": engines,
        "error_codes": [],
        "body_in_receipt": False,
        "findings": findings,
    }


def _mutation_target(input_path: Path, relative_path: object) -> Path:
    rel = Path(str(relative_path or ""))
    if not rel.parts or rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe negative fixture mutation path: {relative_path!r}")
    return input_path / rel


def _strings(value: object) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _apply_negative_workspace_mutation(case_id: str, input_path: Path) -> list[dict[str, Any]]:
    fixture_path = input_path / f"{case_id}.json"
    payload = _load_json(fixture_path)
    mutation = payload.get("workspace_mutation")
    if not isinstance(mutation, Mapping):
        return [
            finding(
                "BATCH10_COLD_EVAL_NEGATIVE_MUTATION_REQUIRED",
                "Negative case fixture must describe an executed workspace mutation.",
                case_id=case_id,
                subject_id=fixture_path.name,
            )
        ]
    kind = str(mutation.get("kind") or "")
    try:
        if kind == "remove_file":
            target = _mutation_target(input_path, mutation.get("path"))
            if target.is_file():
                target.unlink()
            return []
        if kind == "rewrite_tasks_route_refs":
            target = _mutation_target(input_path, mutation.get("path"))
            tasks_payload = _load_json(target)
            route_source_summary = mutation.get("route_source_summary")
            if isinstance(route_source_summary, Mapping):
                tasks_payload["route_source_summary"] = dict(route_source_summary)
            expected_refs_by_task = mutation.get("expected_refs_by_task")
            shared_expected_refs = _strings(mutation.get("expected_refs"))
            for task in tasks_payload.get("tasks", []):
                if not isinstance(task, dict):
                    continue
                refs = shared_expected_refs
                if isinstance(expected_refs_by_task, Mapping):
                    task_refs = expected_refs_by_task.get(str(task.get("id")))
                    refs = _strings(task_refs)
                if refs:
                    task["expected_refs"] = refs
            _write_json(target, tasks_payload)
            return []
        if kind == "set_manifest_field":
            target = _mutation_target(input_path, mutation.get("path"))
            manifest = _load_json(target)
            field = str(mutation.get("field") or "")
            if not field:
                raise ValueError("set_manifest_field mutation requires field")
            manifest[field] = mutation.get("value")
            _write_json(target, manifest)
            return []
        if kind == "inject_private_fixture_probe":
            target = _mutation_target(input_path, mutation.get("path"))
            tasks_payload = _load_json(target)
            tasks_payload["private_fixture_probe"] = "/Users/example/private_state_not_allowed"
            _write_json(target, tasks_payload)
            return []
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [
            finding(
                "BATCH10_COLD_EVAL_NEGATIVE_MUTATION_FAILED",
                "Negative case workspace mutation failed before evaluation.",
                case_id=case_id,
                subject_id=fixture_path.name,
                observed=str(exc),
            )
        ]
    return [
        finding(
            "BATCH10_COLD_EVAL_NEGATIVE_MUTATION_UNSUPPORTED",
            "Negative case fixture names an unsupported workspace mutation kind.",
            case_id=case_id,
            subject_id=fixture_path.name,
            observed=kind,
        )
    ]


def _run_negative_perturbation(
    case_id: str,
    input_path: Path,
    public_root: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"batch10_cold_eval_negative_{case_id}_") as tmp:
        perturbed = Path(tmp) / "input"
        shutil.copytree(input_path, perturbed)
        mutation_findings = _apply_negative_workspace_mutation(case_id, perturbed)
        if mutation_findings:
            return {
                "status": "pass",
                "engines": [],
                "findings": mutation_findings,
                "body_in_receipt": False,
            }
        source_manifest = validate_source_manifest(perturbed, SPEC, public_root=public_root)
        exercise = _evaluate(perturbed, public_root, source_manifest)
    return {
        "status": exercise.get("status"),
        "engines": exercise.get("engines", []),
        "findings": exercise.get("findings", []),
        "body_in_receipt": False,
    }


@lru_cache(maxsize=8)
def _semantic_runtime_exercises(input_ref: str) -> dict[str, Any]:
    input_path = Path(input_ref)
    public_root = public_root_for_path(input_path)
    source_manifest = validate_source_manifest(input_path, SPEC, public_root=public_root)
    exercise = _evaluate(input_path, public_root, source_manifest)
    return {
        "source_manifest": {
            key: value
            for key, value in source_manifest.items()
            if key not in {"findings", "source_manifest_path"}
        },
        "exercise": exercise,
        "negative_exercises": {
            case_id: _run_negative_perturbation(case_id, input_path, public_root)
            for case_id in EXPECTED_NEGATIVE_CASES
        },
    }


def _engine_map(exercise: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    engines = exercise.get("engines") if isinstance(exercise.get("engines"), list) else []
    return {
        str(row.get("engine_id")): row
        for row in engines
        if isinstance(row, Mapping) and row.get("engine_id")
    }


def _negative_exercise(runtime: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    cases = (
        runtime.get("negative_exercises")
        if isinstance(runtime.get("negative_exercises"), Mapping)
        else {}
    )
    case = cases.get(case_id)
    return case if isinstance(case, Mapping) else {}


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    exercise = _negative_exercise(runtime, case_id)
    engines = _engine_map(exercise)
    original = engines.get("cold_eval_original_runner", {})
    shape = engines.get("cold_eval_scorecard_shape_audit", {})
    ceiling = engines.get("cold_eval_claim_ceiling_gate", {})
    if case_id == "missing_tasks":
        return (
            exercise.get("status") == "blocked"
            and original.get("status") == "blocked"
            and original.get("error_code") == NEGATIVE_CASE_CODES[case_id]
        )
    if case_id == "flat_route_can_win":
        return (
            exercise.get("status") == "blocked"
            and shape.get("status") == "blocked"
            and (
                shape.get("all_winners_are_idea_first") is False
                or shape.get("route_surface_asymmetry_visible") is False
                or int(original.get("flat_repo_win_count") or 0) > 0
            )
        )
    if case_id == "expected_ref_injection":
        return (
            exercise.get("status") == "blocked"
            and ceiling.get("status") == "blocked"
            and ceiling.get("expected_ref_injection_allowed") is True
        )
    if case_id == "private_fixture_ref":
        return (
            exercise.get("status") == "blocked"
            and shape.get("status") == "blocked"
            and int(shape.get("private_fixture_ref_count") or 0) > 0
        )
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    expected_code = NEGATIVE_CASE_CODES.get(case_id, "")
    observed = _observed_negative_case(
        case_id,
        _semantic_runtime_exercises(str(Path(input_dir))),
    )
    return {
        "status": "blocked" if observed else "pass",
        "error_codes": [expected_code] if observed and expected_code else [],
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch10_cold_eval_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get("copied_macro_source_module_count")
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-batch10-cold-eval-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    runner = run_batch10_cold_eval_bundle if args.action == "run-batch10-cold-eval-bundle" else run
    result = runner(
        args.input,
        args.out,
        acceptance_out=args.acceptance_out,
        command=f"{ORGAN_ID} {args.action}",
    )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
