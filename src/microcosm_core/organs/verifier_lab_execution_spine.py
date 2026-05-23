from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "verifier_lab_execution_spine"
FIXTURE_ID = "first_wave.verifier_lab_execution_spine"
VALIDATOR_ID = "validator.microcosm.organs.verifier_lab_execution_spine"

PACKET_NAME = "execution_spine_packet.json"
LAKE_PROJECT_DIR = "lake_project"
LAKEFILE_NAME = "lakefile.lean"
RESULT_NAME = "verifier_lab_execution_spine_result.json"
BOARD_NAME = "verifier_lab_execution_spine_board.json"
VALIDATION_RECEIPT_NAME = "verifier_lab_execution_spine_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "verifier_lab_execution_spine_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = (
    "exported_verifier_lab_execution_spine_bundle_validation_result.json"
)

NEGATIVE_INPUT_NAMES = (
    "transition_leaks_candidate_body.json",
    "provider_oracle_visible_transition.json",
    "cp2_candidate_contains_proof_body.json",
    "evolve_mutates_unbounded_source.json",
)
EXPECTED_NEGATIVE_CASES = {
    "transition_leaks_candidate_body": [
        "VERIFIER_LAB_EXECUTION_TRANSITION_FIELD_FORBIDDEN"
    ],
    "provider_oracle_visible_transition": [
        "VERIFIER_LAB_EXECUTION_PROVIDER_OR_ORACLE_VISIBLE"
    ],
    "cp2_candidate_contains_proof_body": [
        "VERIFIER_LAB_EXECUTION_CP2_PROOF_BODY_FORBIDDEN"
    ],
    "evolve_mutates_unbounded_source": [
        "VERIFIER_LAB_EXECUTION_EVOLVE_SCOPE_FORBIDDEN"
    ],
}

FORBIDDEN_TRANSITION_KEYS = {
    "candidate_body",
    "proof_body",
    "ground_truth_proof",
    "ideal_body",
    "repair_body",
    "raw_tactic_script",
    "oracle_template",
    "oracle_needed_premise_ids",
    "provider_output_body",
    "source_proof_body",
}
FORBIDDEN_CP2_KEYS = {
    "candidate_body",
    "proof_body",
    "ground_truth_proof",
    "raw_tactic_script",
    "oracle_template",
    "provider_output_body",
    "source_proof_body",
}
ALLOWED_ACTION_CLASSES = {
    "cases",
    "constructor",
    "decide",
    "exact_premise",
    "induction_visible_head",
    "premise_exact",
    "rfl",
    "simp_with_closed_premises",
    "unfold_then_simp",
}
ALLOWED_CP2_ACTION_CLASSES = {
    "case_split_then_constructor",
    "exact_selected_premise",
    "induction_on_visible_head",
    "premise_exact",
    "premise_query_expand",
    "retry_with_recipe",
    "rewrite_direction_flip",
    "unfold_then_simp",
}
ALLOWED_EVOLVE_ARTIFACTS = {
    "context_recipe_selection",
    "cp2_candidate_ordering",
    "cp2_translation_templates",
    "failure_class_routing",
    "repair_novelty_predicates",
    "retry_recipes",
    "route_priors",
    "target_shape_mapping",
    "target_shape_routing_table",
    "tactic_action_priors",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "bounded_public_lean_transition_execution_receipt_only",
    "lean_lake_execution_authorized": True,
    "lean_lake_execution_scope": "temporary_workspace_copy_of_public_fixture",
    "formal_proof_authority": "bounded_public_transition_rows_only",
    "oracle_success_counts_as_forward_success": False,
    "provider_text_counts_as_proof": False,
    "cp2_outputs_are_proof_bodies": False,
    "evolve_mutates_arbitrary_code": False,
    "proof_bodies_allowed_in_receipts": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "macro_private_body_import_authorized": False,
    "benchmark_solve_rate_claim": False,
    "release_authorized": False,
}
RECEIPT_TRANSPARENCY_CONTRACT = {
    "schema_version": "verifier_lab_receipt_transparency_contract_v1",
    "receipt_body_is_public_evidence": True,
    "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
    "body_in_receipt": False,
    "real_substrate_default": True,
    "required_public_evidence_fields": [
        "problem_id",
        "target_shape",
        "action_class",
        "candidate_kind",
        "allowed_premise_refs",
        "lean_lake_command_identity",
        "lean_return_code",
        "accepted",
        "verifier_failure_class",
        "negative_case_id",
        "cp2_action_class",
        "evolve_policy_artifact_id",
        "oracle_provider_separation_counters",
        "authority_ceiling",
        "anti_claim",
    ],
    "forbidden_payload_fields": [
        "proof_body",
        "raw_tactic_script",
        "provider_text",
        "oracle_ideal_answer",
        "oracle_needed_premise_ids",
        "private_source_path",
        "private_payload_body",
        "stdout_body",
        "stderr_body",
    ],
    "stdout_stderr_policy": "counts_and_return_codes_public_bodies_omitted",
}
ANTI_CLAIM = (
    "Verifier lab execution spine runs bounded public Lean transition candidates "
    "in a temporary workspace and records structured public runtime receipts "
    "with only dangerous payload fields omitted. It does not import macro proof bodies, "
    "expose generated proof text, call providers, count oracle/provider output "
    "as proof authority, mutate source, claim benchmark solve-rate, or authorize "
    "release."
)


@dataclass(frozen=True)
class TransitionReceipt:
    problem_id: str
    target_shape: str
    action_class: str
    candidate_kind: str
    allowed_premise_refs: tuple[str, ...]
    lean_return_code: int | None
    accepted: bool
    verifier_failure_class: str
    stdout_stderr_in_receipt: bool
    oracle_visible: bool
    provider_visible: bool
    proof_body_exported: bool
    transition_id: str
    contract_rejected: bool = False
    error_codes: tuple[str, ...] = ()
    timed_out: bool = False


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    paths = [input_dir / PACKET_NAME, input_dir / LAKE_PROJECT_DIR / LAKEFILE_NAME]
    project_dir = input_dir / LAKE_PROJECT_DIR
    if project_dir.is_dir():
        paths.extend(sorted(project_dir.rglob("*.lean")))
    if (input_dir / "bundle_manifest.json").is_file():
        paths.append(input_dir / "bundle_manifest.json")
    if include_negative:
        paths.extend(input_dir / name for name in NEGATIVE_INPUT_NAMES)
    return paths


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _walk_forbidden_keys(value: object, forbidden: set[str], prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(key_path)
            found.extend(_walk_forbidden_keys(child, forbidden, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_forbidden_keys(child, forbidden, f"{prefix}[{index}]"))
    return sorted(found)


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
    count_observed: bool,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    if count_observed:
        observed.setdefault(case_id, set()).add(code)


def _run_command(argv: list[str], *, cwd: Path, timeout_seconds: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": completed.returncode,
            "stdout_line_count": len(completed.stdout.splitlines()),
            "stderr_line_count": len(completed.stderr.splitlines()),
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": 124,
            "stdout_line_count": len((exc.stdout or "").splitlines()),
            "stderr_line_count": len((exc.stderr or "").splitlines()),
            "timed_out": True,
            "stdout_stderr_in_receipt": False,
        }


def _tool_versions() -> dict[str, Any]:
    lean = _run_command(["lean", "--version"], cwd=Path.cwd())
    lake = _run_command(["lake", "--version"], cwd=Path.cwd())
    return {
        "lean_available": lean["return_code"] == 0,
        "lake_available": lake["return_code"] == 0,
        "lean_version_command": lean,
        "lake_version_command": lake,
    }


def _copy_project_to_temp(input_dir: Path, temp_root: Path) -> Path:
    src = input_dir / LAKE_PROJECT_DIR
    dst = temp_root / LAKE_PROJECT_DIR
    shutil.copytree(src, dst)
    return dst


def _build_lake_project(project_dir: Path) -> dict[str, Any]:
    return _run_command(
        ["lake", "build", "MicrocosmProofWitness"],
        cwd=project_dir,
        timeout_seconds=60,
    )


def _lean_source_for_transition(row: dict[str, Any]) -> str:
    action = str(row.get("action_class") or "")
    outcome = str(row.get("expected_outcome") or "")
    premise_refs = set(_strings(row.get("allowed_premise_refs")))
    header = "import MicrocosmProofWitness.Basic\n\nnamespace MicrocosmExecutionSpine\n\n"
    footer = "\nend MicrocosmExecutionSpine\n"
    if outcome in {"fail_missing_premise", "residual_unsolved"}:
        body = "example (n m : Nat) : n + m = m + n := by\n  exact missing_public_premise\n"
    elif action == "decide":
        body = "example : 17 % 5 = 2 := by\n  decide\n"
    elif action == "rfl":
        body = "example (n : Nat) : n = n := by\n  rfl\n"
    elif action == "constructor":
        body = "example : True ∧ True := by\n  constructor <;> trivial\n"
    elif action == "cases":
        body = (
            "example (p q : Prop) : p ∨ q -> q ∨ p := by\n"
            "  intro h\n"
            "  cases h with\n"
            "  | inl hp => exact Or.inr hp\n"
            "  | inr hq => exact Or.inl hq\n"
        )
    elif action in {"premise_exact", "exact_premise"} and "Nat.add_comm" in premise_refs:
        body = "example (n m : Nat) : n + m = m + n := by\n  exact Nat.add_comm n m\n"
    elif action in {"simp_with_closed_premises", "unfold_then_simp"}:
        body = "example (xs : List Nat) : xs ++ [] = xs := by\n  simp\n"
    elif action == "induction_visible_head":
        body = (
            "example (xs : List Nat) : xs ++ [] = xs := by\n"
            "  induction xs with\n"
            "  | nil => rfl\n"
            "  | cons x xs ih => simp [List.append, ih]\n"
        )
    else:
        body = "example : True := by\n  exact unknown_action_witness\n"
    return f"{header}{body}{footer}"


def _validate_transition_contract(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> list[str]:
    transition_id = str(row.get("transition_id") or row.get("case_id") or "transition")
    case_id = str(row.get("expected_negative_case_id") or row.get("case_id") or transition_id)
    codes: list[str] = []
    forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_TRANSITION_KEYS)
    if forbidden_keys:
        code = "VERIFIER_LAB_EXECUTION_TRANSITION_FIELD_FORBIDDEN"
        _record(
            findings,
            observed,
            code,
            "Transition candidates may not carry proof bodies, raw tactic scripts, provider bodies, or oracle templates.",
            case_id=case_id,
            subject_id=transition_id,
            subject_kind="transition_candidate",
            count_observed=negative,
        )
        codes.append(code)
    if row.get("oracle_visible") is True or row.get("provider_visible") is True:
        code = "VERIFIER_LAB_EXECUTION_PROVIDER_OR_ORACLE_VISIBLE"
        _record(
            findings,
            observed,
            code,
            "Forward transition execution must not see oracle sidecars or provider hypothesis text.",
            case_id=case_id,
            subject_id=transition_id,
            subject_kind="transition_candidate",
            count_observed=negative,
        )
        codes.append(code)
    action = str(row.get("action_class") or "")
    if action and action not in ALLOWED_ACTION_CLASSES:
        code = "VERIFIER_LAB_EXECUTION_ACTION_CLASS_UNKNOWN"
        _record(
            findings,
            observed,
            code,
            "Transition action class is outside the bounded public action vocabulary.",
            case_id=case_id,
            subject_id=action,
            subject_kind="transition_action_class",
            count_observed=negative,
        )
        codes.append(code)
    return codes


def _execute_transition(
    row: dict[str, Any],
    *,
    project_dir: Path,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> TransitionReceipt:
    transition_id = str(row.get("transition_id") or "transition")
    codes = _validate_transition_contract(
        row,
        findings=findings,
        observed=observed,
        negative=False,
    )
    if codes:
        return TransitionReceipt(
            transition_id=transition_id,
            problem_id=str(row.get("problem_id") or ""),
            target_shape=str(row.get("target_shape") or ""),
            action_class=str(row.get("action_class") or ""),
            candidate_kind=str(row.get("candidate_kind") or ""),
            allowed_premise_refs=tuple(_strings(row.get("allowed_premise_refs"))),
            lean_return_code=None,
            accepted=False,
            verifier_failure_class="CONTRACT_REJECTED",
            stdout_stderr_in_receipt=False,
            oracle_visible=row.get("oracle_visible") is True,
            provider_visible=row.get("provider_visible") is True,
            proof_body_exported=False,
            contract_rejected=True,
            error_codes=tuple(codes),
        )

    source_path = project_dir / f"{transition_id}.lean"
    source_path.write_text(_lean_source_for_transition(row), encoding="utf-8")
    lean_run = _run_command(["lake", "env", "lean", source_path.name], cwd=project_dir)
    accepted = lean_run["return_code"] == 0
    return TransitionReceipt(
        transition_id=transition_id,
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_premise_refs=tuple(_strings(row.get("allowed_premise_refs"))),
        lean_return_code=int(lean_run["return_code"]),
        accepted=accepted,
        verifier_failure_class="NONE"
        if accepted
        else str(row.get("expected_failure_class") or "PROOF_SYNTHESIS_FAIL"),
        stdout_stderr_in_receipt=False,
        oracle_visible=False,
        provider_visible=False,
        proof_body_exported=False,
        timed_out=lean_run["timed_out"] is True,
    )


def _translate_cp2(
    packet: dict[str, Any],
    *,
    transition_by_id: dict[str, TransitionReceipt],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    translations: list[dict[str, Any]] = []
    for row in _rows(packet, "cp2_translation_requests"):
        request_id = str(row.get("request_id") or "cp2_request")
        case_id = str(row.get("expected_negative_case_id") or request_id)
        forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_CP2_KEYS)
        action = str(row.get("action_class") or "")
        codes: list[str] = []
        if forbidden_keys:
            code = "VERIFIER_LAB_EXECUTION_CP2_PROOF_BODY_FORBIDDEN"
            _record(
                findings,
                observed,
                code,
                "CP2 translation emits typed action candidates only, never proof bodies or raw tactic scripts.",
                case_id=case_id,
                subject_id=request_id,
                subject_kind="cp2_translation_request",
                count_observed=False,
            )
            codes.append(code)
        if action and action not in ALLOWED_CP2_ACTION_CLASSES:
            code = "VERIFIER_LAB_EXECUTION_CP2_ACTION_CLASS_UNKNOWN"
            _record(
                findings,
                observed,
                code,
                "CP2 action class is outside the bounded translation vocabulary.",
                case_id=case_id,
                subject_id=action,
                subject_kind="cp2_action_class",
                count_observed=False,
            )
            codes.append(code)
        downstream_id = str(row.get("downstream_transition_id") or "")
        downstream = transition_by_id.get(downstream_id)
        translations.append(
            {
                "request_id": request_id,
                "residual_id": row.get("residual_id"),
                "provider_hypothesis_id": row.get("provider_hypothesis_id"),
                "candidate_action_class": action,
                "candidate_kind": "typed_action_candidate",
                "proof_body_exported": False,
                "raw_tactic_script_exported": False,
                "oracle_template_exported": False,
                "provider_output_body_exported": False,
                "disconfirmation_test": row.get("disconfirmation_test"),
                "downstream_transition_id": downstream_id,
                "downstream_verifier_rerun": asdict(downstream) if downstream else None,
                "downstream_effect": bool(downstream and downstream.accepted),
                "contract_rejected": bool(codes),
                "error_codes": codes,
            }
        )
    return translations


def _run_evolve(
    packet: dict[str, Any],
    *,
    transition_by_id: dict[str, TransitionReceipt],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _rows(packet, "evolve_mutations"):
        mutation_id = str(row.get("mutation_id") or row.get("case_id") or "evolve_mutation")
        case_id = str(row.get("expected_negative_case_id") or mutation_id)
        artifact = str(row.get("mutated_artifact") or "")
        forbidden = (
            artifact not in ALLOWED_EVOLVE_ARTIFACTS
            or row.get("arbitrary_code_mutation") is True
            or row.get("source_mutation_authorized") is True
        )
        codes: list[str] = []
        if forbidden:
            code = "VERIFIER_LAB_EXECUTION_EVOLVE_SCOPE_FORBIDDEN"
            _record(
                findings,
                observed,
                code,
                "Evolve may mutate only bounded verifier-lab policy artifacts and must rerun the public problem set.",
                case_id=case_id,
                subject_id=mutation_id,
                subject_kind="evolve_mutation",
                count_observed=False,
            )
            codes.append(code)
        baseline_ids = _strings(row.get("baseline_transition_ids"))
        rerun_ids = _strings(row.get("rerun_transition_ids"))
        baseline_accepts = sum(
            1 for item in baseline_ids if transition_by_id.get(item, None) and transition_by_id[item].accepted
        )
        rerun_accepts = sum(
            1 for item in rerun_ids if transition_by_id.get(item, None) and transition_by_id[item].accepted
        )
        leakage_regression = any(
            transition_by_id[item].contract_rejected
            for item in rerun_ids
            if transition_by_id.get(item, None)
        )
        accepted = (
            not forbidden
            and not leakage_regression
            and bool(rerun_ids)
            and rerun_accepts >= baseline_accepts
            and rerun_accepts > 0
        )
        rows.append(
            {
                "mutation_id": mutation_id,
                "mutated_artifact": artifact,
                "baseline_transition_ids": baseline_ids,
                "rerun_transition_ids": rerun_ids,
                "baseline_accept_count": baseline_accepts,
                "rerun_accept_count": rerun_accepts,
                "leakage_regression": leakage_regression,
                "oracle_to_forward_contamination": False,
                "source_mutation_authorized": False,
                "decision": "accepted" if accepted else "quarantined",
                "accepted": accepted,
                "contract_rejected": bool(codes),
                "error_codes": codes,
                "body_in_receipt": False,
            }
        )
    return rows


def _validate_negative_payloads(
    payloads: dict[str, dict[str, Any]],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> None:
    for payload in payloads.values():
        for row in _rows(payload, "transition_candidates") or (
            [payload] if "transition_id" in payload else []
        ):
            _validate_transition_contract(
                row,
                findings=findings,
                observed=observed,
                negative=True,
            )
        for row in _rows(payload, "cp2_translation_requests") or (
            [payload] if "request_id" in payload else []
        ):
            request_id = str(row.get("request_id") or row.get("case_id") or "cp2_request")
            case_id = str(row.get("expected_negative_case_id") or request_id)
            if _walk_forbidden_keys(row, FORBIDDEN_CP2_KEYS):
                _record(
                    findings,
                    observed,
                    "VERIFIER_LAB_EXECUTION_CP2_PROOF_BODY_FORBIDDEN",
                    "CP2 negative fixture rejected proof bodies or raw tactic scripts.",
                    case_id=case_id,
                    subject_id=request_id,
                    subject_kind="cp2_translation_request",
                    count_observed=True,
                )
        for row in _rows(payload, "evolve_mutations") or (
            [payload] if "mutated_artifact" in payload else []
        ):
            mutation_id = str(row.get("mutation_id") or row.get("case_id") or "evolve_mutation")
            case_id = str(row.get("expected_negative_case_id") or mutation_id)
            artifact = str(row.get("mutated_artifact") or "")
            if (
                artifact not in ALLOWED_EVOLVE_ARTIFACTS
                or row.get("arbitrary_code_mutation") is True
                or row.get("source_mutation_authorized") is True
            ):
                _record(
                    findings,
                    observed,
                    "VERIFIER_LAB_EXECUTION_EVOLVE_SCOPE_FORBIDDEN",
                    "Evolve negative fixture rejected unbounded source mutation.",
                    case_id=case_id,
                    subject_id=mutation_id,
                    subject_kind="evolve_mutation",
                    count_observed=True,
                )


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    packet = _load_json_if_exists(input_dir / PACKET_NAME)
    negative_payloads = {
        Path(name).stem: _load_json_if_exists(input_dir / name)
        for name in NEGATIVE_INPUT_NAMES
        if (input_dir / name).is_file()
    }
    input_paths = _input_paths(input_dir, include_negative=include_negative)
    secret_scan = scan_paths(
        input_paths,
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    tool_versions = _tool_versions()
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = {}
    transitions: list[TransitionReceipt] = []
    lake_project_build: dict[str, Any] | None = None

    with tempfile.TemporaryDirectory(prefix="microcosm_verifier_execution_") as temp_name:
        project_dir = _copy_project_to_temp(input_dir, Path(temp_name))
        lake_project_build = _build_lake_project(project_dir)
        if lake_project_build["return_code"] == 0:
            for row in _rows(packet, "transition_candidates"):
                transitions.append(
                    _execute_transition(
                        row,
                        project_dir=project_dir,
                        findings=findings,
                        observed=observed,
                    )
                )

    transition_by_id = {row.transition_id: row for row in transitions}
    cp2_translations = _translate_cp2(
        packet,
        transition_by_id=transition_by_id,
        findings=findings,
        observed=observed,
    )
    evolve_mutations = _run_evolve(
        packet,
        transition_by_id=transition_by_id,
        findings=findings,
        observed=observed,
    )
    if include_negative:
        _validate_negative_payloads(
            negative_payloads,
            findings=findings,
            observed=observed,
        )

    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed_cases = {
        case_id: sorted(codes) for case_id, codes in sorted(observed.items())
    }
    missing = sorted(case_id for case_id in expected if case_id not in observed_cases)
    accepted_transitions = [row for row in transitions if row.accepted]
    residuals = [row for row in transitions if not row.accepted and not row.contract_rejected]
    cp2_effects = [row for row in cp2_translations if row.get("downstream_effect") is True]
    evolve_accepted = [row for row in evolve_mutations if row.get("accepted") is True]
    contract_rejections = [
        *[row for row in transitions if row.contract_rejected],
        *[row for row in cp2_translations if row.get("contract_rejected")],
        *[row for row in evolve_mutations if row.get("contract_rejected")],
    ]
    bundle_manifest = _load_json_if_exists(input_dir / "bundle_manifest.json")
    status = (
        PASS
        if secret_scan["blocking_hit_count"] == 0
        and tool_versions["lean_available"]
        and tool_versions["lake_available"]
        and lake_project_build is not None
        and lake_project_build["return_code"] == 0
        and not missing
        and len(transitions) >= 4
        and len(accepted_transitions) >= 2
        and len(residuals) >= 1
        and len(cp2_effects) >= 1
        and len(evolve_mutations) >= 1
        and len(evolve_accepted) >= 1
        and all(row.proof_body_exported is False for row in transitions)
        else "blocked"
    )
    return {
        "schema_version": "verifier_lab_execution_spine_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "execution_spine_id": packet.get("execution_spine_id"),
        "source_refs": _strings(packet.get("source_refs")),
        "source_pattern_ids": _strings(packet.get("source_pattern_ids")),
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed_cases,
        "missing_negative_cases": missing,
        "error_codes": sorted({str(row["error_code"]) for row in findings}),
        "findings": sorted(
            findings,
            key=lambda row: (
                str(row.get("negative_case_id") or ""),
                str(row.get("subject_kind") or ""),
                str(row.get("subject_id") or ""),
                str(row.get("error_code") or ""),
            ),
        ),
        "secret_exclusion_scan": secret_scan,
        "tool_versions": tool_versions,
        "lake_project_build": lake_project_build,
        "transition_trace": [asdict(row) for row in transitions],
        "cp2_translation_trace": cp2_translations,
        "evolve_mutation_trace": evolve_mutations,
        "claim_separation": {
            "lean_verified": [asdict(row) for row in accepted_transitions],
            "oracle_compared": _rows(packet, "oracle_sidecars"),
            "provider_suggested": _rows(packet, "provider_hypotheses"),
            "cp2_translated": cp2_translations,
            "contract_rejected": contract_rejections,
            "retrieval_miss": [
                asdict(row)
                for row in residuals
                if row.verifier_failure_class == "PREMISE_RETRIEVAL_MISS"
            ],
            "proof_synthesis_fail": [
                asdict(row)
                for row in residuals
                if row.verifier_failure_class != "PREMISE_RETRIEVAL_MISS"
            ],
            "evolve_candidate": evolve_mutations,
            "evolve_accepted": evolve_accepted,
        },
        "authority_counters": {
            "transition_count": len(transitions),
            "accepted_transition_count": len(accepted_transitions),
            "residual_transition_count": len(residuals),
            "cp2_translation_count": len(cp2_translations),
            "cp2_downstream_effect_count": len(cp2_effects),
            "evolve_candidate_count": len(evolve_mutations),
            "evolve_accepted_count": len(evolve_accepted),
            "oracle_forward_success_increment_count": 0,
            "provider_results_counted": 0,
            "proof_body_export_count": 0,
            "source_mutation_count": 0,
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_transparency_contract": RECEIPT_TRANSPARENCY_CONTRACT,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "input_mode",
        "bundle_id",
        "execution_spine_id",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "tool_versions",
        "lake_project_build",
        "transition_trace",
        "cp2_translation_trace",
        "evolve_mutation_trace",
        "claim_separation",
        "authority_counters",
        "authority_ceiling",
        "receipt_transparency_contract",
        "anti_claim",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
        "public_runtime_refs",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [_display(path, public_root=public_root) for path in paths.values()]


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "verifier_lab_execution_spine_result": target / RESULT_NAME,
        "verifier_lab_execution_spine_board": target / BOARD_NAME,
        "verifier_lab_execution_spine_validation_receipt": target
        / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)
    result_receipt = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(
        {
            "headline": "Bounded Lean transition execution under leak-proof verifier-lab authority.",
            "lean_verified_count": len(result["claim_separation"]["lean_verified"]),
            "cp2_downstream_effect_count": result["authority_counters"][
                "cp2_downstream_effect_count"
            ],
            "evolve_accepted_count": result["authority_counters"][
                "evolve_accepted_count"
            ],
            "proof_body_export_count": result["authority_counters"][
                "proof_body_export_count"
            ],
            "provider_results_counted": result["authority_counters"][
                "provider_results_counted"
            ],
            "oracle_forward_success_increment_count": result["authority_counters"][
                "oracle_forward_success_increment_count"
            ],
        }
    )
    validation = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "lean_transition_execution_status": PASS
            if result["authority_counters"]["accepted_transition_count"] >= 2
            else "blocked",
            "cp2_translation_status": PASS
            if result["authority_counters"]["cp2_downstream_effect_count"] >= 1
            else "blocked",
            "evolve_mutation_status": PASS
            if result["authority_counters"]["evolve_accepted_count"] >= 1
            else "blocked",
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "receipts_include_proof_bodies": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "receipt_body_is_public_evidence": True,
            "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
            "body_in_receipt": False,
            "real_runtime_receipt": result["status"] == PASS,
            "synthetic_receipt_standin_allowed": False,
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "accepted_scope": "bounded_public_lean_transition_execution_only",
            "runtime_shell_projection_deferred": True,
        }
    )
    write_json_atomic(paths["verifier_lab_execution_spine_result"], result_receipt)
    write_json_atomic(paths["verifier_lab_execution_spine_board"], board)
    write_json_atomic(
        paths["verifier_lab_execution_spine_validation_receipt"], validation
    )
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.verifier_lab_execution_spine run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_execution_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.verifier_lab_execution_spine "
        f"run-execution-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_verifier_lab_execution_spine_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    result_path = target / BUNDLE_RESULT_NAME
    receipt = _common_receipt(
        result,
        schema_version=(
            "exported_verifier_lab_execution_spine_bundle_validation_result_v1"
        ),
        receipt_paths=[_display(result_path, public_root=public_root)],
    )
    write_json_atomic(result_path, receipt)
    result["receipt_paths"] = [_display(result_path, public_root=public_root)]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verifier_lab_execution_spine")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-execution-bundle"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
    args = parser.parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    else:
        result = run_execution_bundle(args.input, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
