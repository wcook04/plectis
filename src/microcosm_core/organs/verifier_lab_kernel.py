from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from microcosm_core.organs import corpus_readiness_mathlib_absence_gate
from microcosm_core.organs import formal_math_lean_proof_witness
from microcosm_core.organs import formal_math_premise_retrieval
from microcosm_core.organs import formal_math_verifier_trace_repair_loop
from microcosm_core.organs import lean_std_premise_index
from microcosm_core.organs import proof_diagnostic_evidence_spine
from microcosm_core.organs import ring2_premise_retrieval_precision_recall_harness
from microcosm_core.organs import tactic_portfolio_availability_probe
from microcosm_core.organs import target_shape_tactic_routing_gate
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "verifier_lab_kernel"
FIXTURE_ID = "first_wave.verifier_lab_kernel"
VALIDATOR_ID = "validator.microcosm.organs.verifier_lab_kernel"

PACKET_NAME = "verifier_lab_packet.json"
PROOF_LAB_ROUTE_NAME = "proof_lab_route.json"
RESULT_NAME = "verifier_lab_kernel_result.json"
BOARD_NAME = "verifier_lab_kernel_board.json"
VALIDATION_RECEIPT_NAME = "verifier_lab_kernel_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/verifier_lab_kernel_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_verifier_lab_kernel_bundle_validation_result.json"
PUBLIC_ROOT_POLICY_REL = Path("core/private_state_forbidden_classes.json")
MODULE_PUBLIC_ROOT = Path(__file__).resolve().parents[3]

NEGATIVE_INPUT_NAMES = (
    "forward_problem_leaks_candidate_body.json",
    "oracle_counted_as_forward.json",
    "provider_claims_proof.json",
    "cp2_candidate_contains_proof_body.json",
    "evolve_mutates_unbounded_artifact.json",
)

EXPECTED_NEGATIVE_CASES = {
    "forward_problem_leaks_candidate_body": [
        "VERIFIER_LAB_FORWARD_FIELD_FORBIDDEN"
    ],
    "oracle_counted_as_forward": [
        "VERIFIER_LAB_ORACLE_FORWARD_CONTAMINATION"
    ],
    "provider_claims_proof": [
        "VERIFIER_LAB_PROVIDER_PROOF_AUTHORITY_FORBIDDEN"
    ],
    "cp2_candidate_contains_proof_body": [
        "VERIFIER_LAB_CP2_PROOF_BODY_FORBIDDEN"
    ],
    "evolve_mutates_unbounded_artifact": [
        "VERIFIER_LAB_EVOLVE_SCOPE_FORBIDDEN"
    ],
}
EXPECTED_PROOF_LAB_ROUTE_ID = "formal_prover_context_strategy_gate"
EXPECTED_ROUTE_COMPONENT_ORGANS = {
    "corpus_readiness_mathlib_absence_gate",
    "lean_std_premise_index",
    "formal_math_premise_retrieval",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
    "ring2_premise_retrieval_precision_recall_harness",
    "formal_math_verifier_trace_repair_loop",
    "proof_diagnostic_evidence_spine",
    "formal_math_lean_proof_witness",
}
EXPECTED_ROUTE_PATTERN_IDS = {
    "corpus_readiness_mathlib_absence_gate",
    "lean_std_toolchain_premise_index",
    "prover_premise_retrieval_term_scoring",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
    "ring2_premise_retrieval_precision_recall_harness",
}

FORBIDDEN_FORWARD_KEYS = {
    "candidate_body",
    "ideal_body",
    "repair_body",
    "oracle_needed_premise_ids",
    "source_proof_body",
    "base_problem_index",
    "proof_body",
    "ground_truth_proof",
}
FORBIDDEN_CP2_KEYS = {
    "proof_body",
    "candidate_body",
    "ground_truth_proof",
    "oracle_template",
    "source_proof_body",
    "raw_tactic_script",
    "provider_output_body",
}
ALLOWED_CP2_ACTION_CLASSES = {
    "rewrite_direction_flip",
    "case_close_constructor",
    "induction_on_visible_head",
    "premise_exact",
    "unfold_then_simp",
    "retry_with_recipe",
}
ALLOWED_EVOLVE_ARTIFACTS = {
    "target_shape_routing_table",
    "tactic_action_priors",
    "failure_class_routing",
    "context_recipe_selection",
    "cp2_translation_templates",
    "repair_novelty_predicates",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "verifier_governed_public_kernel_receipt_only",
    "lean_lake_execution_authorized": "bounded_public_component_witness_only",
    "formal_proof_authority": False,
    "oracle_success_counts_as_forward_success": False,
    "provider_text_counts_as_proof": False,
    "cp2_outputs_are_proof_bodies": False,
    "evolve_mutates_arbitrary_code": False,
    "proof_bodies_allowed_in_receipts": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "macro_private_body_import_authorized": False,
    "release_authorized": False,
}
LEGACY_REDACTION_RECEIPT_KEYS = {
    "body_redacted",
    "matched_excerpt",
    "public_replacement_ref",
    "public_replacement_refs",
    "forbidden_output_fields",
    "redacted_output_field_labels_omitted",
}
RECEIPT_TRANSPARENCY_CONTRACT = {
    "schema_version": "verifier_lab_receipt_transparency_contract_v1",
    "receipt_body_is_public_evidence": True,
    "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
    "body_in_receipt": False,
    "real_substrate_default": True,
    "required_public_evidence_fields": [
        "theorem_or_declaration_names",
        "lean_lake_command_identity",
        "lean_return_code",
        "source_hashes",
        "declaration_counts",
        "accepted_transition_count",
        "residual_transition_count",
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
    "Verifier lab kernel composes source-available public component receipts "
    "for bounded Lean/Lake execution, tactic routing, verifier trace repair, "
    "provider-hypothesis quarantine, CP2 action candidates, bounded Evolve "
    "candidates, and structured public runtime receipts. It does not import "
    "macro proof bodies, count oracle or provider output as forward proof "
    "success, expose proof bodies, mutate source, claim benchmark solve rate, "
    "or authorize release."
)


@dataclass(frozen=True)
class ForwardProblem:
    problem_id: str
    target_shape: str
    statement_summary: str
    public_input_hash: str
    allowed_premise_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class OracleSidecar:
    sidecar_id: str
    forward_problem_id: str
    oracle_result_class: str
    counted_as_forward_success: bool = False


@dataclass(frozen=True)
class VerifierAttempt:
    attempt_id: str
    forward_problem_id: str
    verifier_result_class: str
    selected_tactic_id: str | None = None
    component_receipt_ref: str | None = None


@dataclass(frozen=True)
class VerifierResult:
    result_id: str
    attempt_id: str
    result_class: str
    verifier_receipt_ref: str


@dataclass(frozen=True)
class ProviderHypothesis:
    hypothesis_id: str
    residual_id: str
    residual_class: str
    candidate_action_classes: tuple[str, ...]
    provider_results_counted: bool = False


@dataclass(frozen=True)
class ResidualDiagnosis:
    residual_id: str
    forward_problem_id: str
    residual_class: str
    missing_primitive: str | None = None


@dataclass(frozen=True)
class RepairProposal:
    proposal_id: str
    residual_id: str
    action_class: str
    verifier_rerun_ref: str


@dataclass(frozen=True)
class EvolveCandidate:
    candidate_id: str
    mutated_artifact: str
    baseline_receipt_ref: str
    rerun_receipt_ref: str | None = None


@dataclass(frozen=True)
class ClaimBoundary:
    boundary_id: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class AuthoritySplit:
    forward_success_authority: str
    oracle_authority: str
    provider_authority: str
    evolve_authority: str


Runner = Callable[..., dict[str, Any]]


COMPONENT_RUNNERS: dict[str, dict[str, Runner]] = {
    "corpus_readiness_mathlib_absence_gate": {
        "fixture": corpus_readiness_mathlib_absence_gate.run,
        "bundle": corpus_readiness_mathlib_absence_gate.run_projection_bundle,
    },
    "lean_std_premise_index": {
        "fixture": lean_std_premise_index.run,
        "bundle": lean_std_premise_index.run_index_bundle,
    },
    "formal_math_premise_retrieval": {
        "fixture": formal_math_premise_retrieval.run,
        "bundle": formal_math_premise_retrieval.run_retrieval_bundle,
    },
    "tactic_portfolio_availability_probe": {
        "fixture": tactic_portfolio_availability_probe.run,
        "bundle": tactic_portfolio_availability_probe.run_availability_bundle,
    },
    "target_shape_tactic_routing_gate": {
        "fixture": target_shape_tactic_routing_gate.run,
        "bundle": target_shape_tactic_routing_gate.run_routing_bundle,
    },
    "formal_math_verifier_trace_repair_loop": {
        "fixture": formal_math_verifier_trace_repair_loop.run,
        "bundle": formal_math_verifier_trace_repair_loop.run_loop_bundle,
    },
    "ring2_premise_retrieval_precision_recall_harness": {
        "fixture": ring2_premise_retrieval_precision_recall_harness.run,
        "bundle": ring2_premise_retrieval_precision_recall_harness.run_precision_recall_bundle,
    },
    "proof_diagnostic_evidence_spine": {
        "fixture": proof_diagnostic_evidence_spine.run,
        "bundle": proof_diagnostic_evidence_spine.run_evidence_bundle,
    },
    "formal_math_lean_proof_witness": {
        "fixture": formal_math_lean_proof_witness.run,
        "bundle": formal_math_lean_proof_witness.run_witness_bundle,
    },
}


DEFAULT_COMPONENT_INPUTS = [
    {
        "organ_id": "corpus_readiness_mathlib_absence_gate",
        "input_rel": "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "lean_std_premise_index",
        "input_rel": "fixtures/first_wave/lean_std_premise_index/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "formal_math_premise_retrieval",
        "input_rel": "fixtures/first_wave/formal_math_premise_retrieval/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "tactic_portfolio_availability_probe",
        "input_rel": "fixtures/first_wave/tactic_portfolio_availability_probe/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "target_shape_tactic_routing_gate",
        "input_rel": "fixtures/first_wave/target_shape_tactic_routing_gate/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "formal_math_verifier_trace_repair_loop",
        "input_rel": "fixtures/first_wave/formal_math_verifier_trace_repair_loop/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "ring2_premise_retrieval_precision_recall_harness",
        "input_rel": "fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "proof_diagnostic_evidence_spine",
        "input_rel": "fixtures/first_wave/proof_diagnostic_evidence_spine/input",
        "input_mode": "fixture",
    },
    {
        "organ_id": "formal_math_lean_proof_witness",
        "input_rel": "fixtures/first_wave/formal_math_lean_proof_witness/input",
        "input_mode": "fixture",
    },
]


def _is_public_root(candidate: Path) -> bool:
    return (candidate / PUBLIC_ROOT_POLICY_REL).is_file()


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    candidates = [
        start,
        *start.parents,
        Path.cwd().resolve(strict=False),
        MODULE_PUBLIC_ROOT,
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _is_public_root(candidate):
            return candidate
    return MODULE_PUBLIC_ROOT


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (PACKET_NAME, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    route_path = input_dir / PROOF_LAB_ROUTE_NAME
    if route_path.is_file():
        paths.append(route_path)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


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


def _without_legacy_redaction_receipt_fields(value: object) -> object:
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key, child in value.items():
            if key in LEGACY_REDACTION_RECEIPT_KEYS:
                continue
            clean_key = "secret_exclusion_scan" if key == "private_state_scan" else key
            cleaned[clean_key] = _without_legacy_redaction_receipt_fields(child)
        return cleaned
    if isinstance(value, list):
        return [_without_legacy_redaction_receipt_fields(item) for item in value]
    return value


def _rewrite_json_receipt_without_legacy_redaction(path: Path) -> None:
    payload = read_json_strict(path)
    cleaned = _without_legacy_redaction_receipt_fields(payload)
    if cleaned != payload:
        write_json_atomic(path, cleaned)


def _normalize_component_receipt_surface(target: Path) -> None:
    if not target.exists():
        return
    for path in sorted(target.rglob("*.json")):
        _rewrite_json_receipt_without_legacy_redaction(path)


def _negative_case_id(row: dict[str, Any], fallback: str) -> str:
    return str(row.get("expected_negative_case_id") or row.get("case_id") or fallback)


def _validate_forward_problems(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[ForwardProblem]:
    parsed: list[ForwardProblem] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        problem_id = str(row.get("problem_id") or row.get("case_id") or "forward_problem")
        case_id = _negative_case_id(row, problem_id)
        forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_FORWARD_KEYS)
        if forbidden_keys:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_FORWARD_FIELD_FORBIDDEN",
                "ForwardProblem rows may not carry candidate, ideal, repair, oracle, source proof, or base-index fields.",
                case_id=case_id,
                subject_id=problem_id,
                subject_kind="forward_problem",
                count_observed=negative,
            )
        if not negative and problem_id and not forbidden_keys:
            parsed.append(
                ForwardProblem(
                    problem_id=problem_id,
                    target_shape=str(row.get("target_shape") or ""),
                    statement_summary=str(row.get("statement_summary") or ""),
                    public_input_hash=str(row.get("public_input_hash") or ""),
                    allowed_premise_ids=tuple(_strings(row.get("allowed_premise_ids"))),
                )
            )
    return parsed


def _validate_oracle_sidecars(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[OracleSidecar]:
    parsed: list[OracleSidecar] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        sidecar_id = str(row.get("sidecar_id") or row.get("case_id") or "oracle_sidecar")
        case_id = _negative_case_id(row, sidecar_id)
        counted = row.get("counted_as_forward_success") is True
        if counted:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_ORACLE_FORWARD_CONTAMINATION",
                "Oracle comparator success may be recorded only as oracle evidence, never as forward success.",
                case_id=case_id,
                subject_id=sidecar_id,
                subject_kind="oracle_sidecar",
                count_observed=negative,
            )
        if not negative:
            parsed.append(
                OracleSidecar(
                    sidecar_id=sidecar_id,
                    forward_problem_id=str(row.get("forward_problem_id") or ""),
                    oracle_result_class=str(row.get("oracle_result_class") or ""),
                    counted_as_forward_success=counted,
                )
            )
    return parsed


def _validate_provider_hypotheses(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[ProviderHypothesis]:
    parsed: list[ProviderHypothesis] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        hypothesis_id = str(row.get("hypothesis_id") or row.get("case_id") or "provider_hypothesis")
        case_id = _negative_case_id(row, hypothesis_id)
        proof_claim = (
            row.get("proof_authority") is True
            or row.get("provider_results_counted") is True
            or str(row.get("authority") or "").endswith("proof_authority")
        )
        if proof_claim:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_PROVIDER_PROOF_AUTHORITY_FORBIDDEN",
                "Provider/NIM output must remain an advisory hypothesis until a verifier/substrate effect exists.",
                case_id=case_id,
                subject_id=hypothesis_id,
                subject_kind="provider_hypothesis",
                count_observed=negative,
            )
        if not negative:
            parsed.append(
                ProviderHypothesis(
                    hypothesis_id=hypothesis_id,
                    residual_id=str(row.get("residual_id") or ""),
                    residual_class=str(row.get("residual_class") or ""),
                    candidate_action_classes=tuple(
                        _strings(row.get("candidate_action_classes"))
                    ),
                    provider_results_counted=row.get("provider_results_counted") is True,
                )
            )
    return parsed


def _validate_cp2_candidates(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[RepairProposal]:
    parsed: list[RepairProposal] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        candidate_id = str(row.get("candidate_id") or row.get("case_id") or "cp2_candidate")
        case_id = _negative_case_id(row, candidate_id)
        forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_CP2_KEYS)
        action_class = str(row.get("action_class") or "")
        if forbidden_keys:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_CP2_PROOF_BODY_FORBIDDEN",
                "CP2 may emit typed action candidates only, not proof bodies, raw tactic scripts, provider bodies, or oracle templates.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="cp2_action_candidate",
                count_observed=negative,
            )
        if action_class and action_class not in ALLOWED_CP2_ACTION_CLASSES:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_CP2_ACTION_CLASS_UNKNOWN",
                "CP2 action candidates must use the bounded public action-class vocabulary.",
                case_id=case_id,
                subject_id=action_class,
                subject_kind="cp2_action_class",
                count_observed=negative,
            )
        if not row.get("disconfirmation_test") and not negative:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_CP2_DISCONFIRMATION_TEST_MISSING",
                "CP2 action candidates must name a disconfirmation test before rerun promotion.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="cp2_action_candidate",
                count_observed=False,
            )
        if not negative and not forbidden_keys:
            parsed.append(
                RepairProposal(
                    proposal_id=candidate_id,
                    residual_id=str(row.get("residual_id") or ""),
                    action_class=action_class,
                    verifier_rerun_ref=str(row.get("verifier_rerun_ref") or ""),
                )
            )
    return parsed


def _validate_evolve_candidates(
    rows: list[dict[str, Any]],
    *,
    observed: dict[str, set[str]],
    positive_findings: list[dict[str, Any]],
    negative_findings: list[dict[str, Any]],
    negative: bool,
) -> list[EvolveCandidate]:
    parsed: list[EvolveCandidate] = []
    findings = negative_findings if negative else positive_findings
    for row in rows:
        candidate_id = str(row.get("candidate_id") or row.get("case_id") or "evolve_candidate")
        case_id = _negative_case_id(row, candidate_id)
        artifact = str(row.get("mutated_artifact") or "")
        unbounded = (
            artifact not in ALLOWED_EVOLVE_ARTIFACTS
            or row.get("arbitrary_code_mutation") is True
            or row.get("source_mutation_authorized") is True
        )
        if unbounded:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_EVOLVE_SCOPE_FORBIDDEN",
                "Evolve may mutate only bounded policy artifacts with rerun and leakage receipts.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="evolve_candidate",
                count_observed=negative,
            )
        if not row.get("baseline_receipt_ref") and not negative:
            _record(
                findings,
                observed,
                "VERIFIER_LAB_EVOLVE_BASELINE_RECEIPT_MISSING",
                "Evolve candidates must cite a baseline receipt before acceptance or quarantine.",
                case_id=case_id,
                subject_id=candidate_id,
                subject_kind="evolve_candidate",
                count_observed=False,
            )
        if not negative and not unbounded:
            parsed.append(
                EvolveCandidate(
                    candidate_id=candidate_id,
                    mutated_artifact=artifact,
                    baseline_receipt_ref=str(row.get("baseline_receipt_ref") or ""),
                    rerun_receipt_ref=str(row.get("rerun_receipt_ref") or "") or None,
                )
            )
    return parsed


def _validate_packet(
    packet: dict[str, Any],
    negative_payloads: dict[str, Any],
    *,
    require_negative_cases: bool,
) -> dict[str, Any]:
    observed: dict[str, set[str]] = {}
    positive_findings: list[dict[str, Any]] = []
    negative_findings: list[dict[str, Any]] = []

    forward_problems = _validate_forward_problems(
        _rows(packet, "forward_problems"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    oracle_sidecars = _validate_oracle_sidecars(
        _rows(packet, "oracle_sidecars"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    provider_hypotheses = _validate_provider_hypotheses(
        _rows(packet, "provider_hypotheses"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    cp2_candidates = _validate_cp2_candidates(
        _rows(packet, "cp2_action_candidates"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )
    evolve_candidates = _validate_evolve_candidates(
        _rows(packet, "evolve_candidates"),
        observed=observed,
        positive_findings=positive_findings,
        negative_findings=negative_findings,
        negative=False,
    )

    for payload in negative_payloads.values():
        rows = _rows(payload, "forward_problems")
        if isinstance(payload, dict) and not rows and "forward_problem" in payload:
            rows = [payload["forward_problem"]]
        _validate_forward_problems(
            rows,
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_oracle_sidecars(
            _rows(payload, "oracle_sidecars") or ([payload] if "sidecar_id" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_provider_hypotheses(
            _rows(payload, "provider_hypotheses") or ([payload] if "hypothesis_id" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_cp2_candidates(
            _rows(payload, "cp2_action_candidates") or ([payload] if "candidate_id" in payload and "action_class" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )
        _validate_evolve_candidates(
            _rows(payload, "evolve_candidates") or ([payload] if "mutated_artifact" in payload else []),
            observed=observed,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            negative=True,
        )

    residual_diagnoses = [
        ResidualDiagnosis(
            residual_id=str(row.get("residual_id") or ""),
            forward_problem_id=str(row.get("forward_problem_id") or ""),
            residual_class=str(row.get("residual_class") or ""),
            missing_primitive=str(row.get("missing_primitive") or "") or None,
        )
        for row in _rows(packet, "residual_diagnoses")
    ]
    verifier_attempts = [
        VerifierAttempt(
            attempt_id=str(row.get("attempt_id") or ""),
            forward_problem_id=str(row.get("forward_problem_id") or ""),
            verifier_result_class=str(row.get("verifier_result_class") or ""),
            selected_tactic_id=str(row.get("selected_tactic_id") or "") or None,
            component_receipt_ref=str(row.get("component_receipt_ref") or "") or None,
        )
        for row in _rows(packet, "verifier_attempts")
    ]

    expected_negative_cases = EXPECTED_NEGATIVE_CASES if require_negative_cases else {}
    missing = sorted(
        case_id for case_id in expected_negative_cases if case_id not in observed
    )
    floors = {
        "forward_problem_count": len(forward_problems),
        "oracle_sidecar_count": len(oracle_sidecars),
        "provider_hypothesis_count": len(provider_hypotheses),
        "residual_diagnosis_count": len(residual_diagnoses),
        "cp2_candidate_count": len(cp2_candidates),
        "evolve_candidate_count": len(evolve_candidates),
        "verifier_attempt_count": len(verifier_attempts),
    }
    floor_status = (
        PASS
        if floors["forward_problem_count"] >= 3
        and floors["oracle_sidecar_count"] >= 1
        and floors["provider_hypothesis_count"] >= 1
        and floors["residual_diagnosis_count"] >= 1
        and floors["cp2_candidate_count"] >= 2
        and floors["evolve_candidate_count"] >= 1
        and floors["verifier_attempt_count"] >= 3
        else "blocked"
    )
    if floor_status != PASS:
        positive_findings.append(
            _finding(
                "VERIFIER_LAB_PACKET_FLOOR_MISSING",
                "Verifier lab packet must carry forward problems, oracle sidecars, verifier attempts, provider hypotheses, residual diagnoses, CP2 candidates, and Evolve candidates.",
                case_id="packet_floor",
                subject_id=str(packet.get("kernel_id") or "verifier_lab_packet"),
                subject_kind="verifier_lab_packet",
            )
        )

    return {
        "status": PASS if not positive_findings and not missing else "blocked",
        "kernel_id": packet.get("kernel_id"),
        "source_pattern_ids": _strings(packet.get("source_pattern_ids")),
        "source_refs": _strings(packet.get("source_refs")),
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
        "expected_negative_cases": sorted(expected_negative_cases),
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in sorted(observed.items())
        },
        "missing_negative_cases": missing,
        "positive_findings": sorted(
            positive_findings,
            key=lambda row: (str(row["negative_case_id"]), str(row["error_code"])),
        ),
        "negative_findings": sorted(
            negative_findings,
            key=lambda row: (str(row["negative_case_id"]), str(row["error_code"])),
        ),
        "forward_problems": [asdict(row) for row in forward_problems],
        "oracle_sidecars": [asdict(row) for row in oracle_sidecars],
        "provider_hypotheses": [asdict(row) for row in provider_hypotheses],
        "residual_diagnoses": [asdict(row) for row in residual_diagnoses],
        "cp2_action_candidates": [asdict(row) for row in cp2_candidates],
        "evolve_candidates": [asdict(row) for row in evolve_candidates],
        "verifier_attempts": [asdict(row) for row in verifier_attempts],
        "floors": floors,
    }


def _component_specs(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _rows(packet, "component_inputs")
    if not rows:
        return list(DEFAULT_COMPONENT_INPUTS)
    seen = {
        str(row.get("organ_id") or "")
        for row in rows
        if isinstance(row, dict)
    }
    return [
        *rows,
        *[
            row
            for row in DEFAULT_COMPONENT_INPUTS
            if str(row.get("organ_id") or "") not in seen
        ],
    ]


def _validate_proof_lab_route(
    payload: dict[str, Any] | None,
    *,
    component_specs: list[dict[str, Any]],
    require_route: bool,
) -> dict[str, Any]:
    if not payload:
        return {
            "status": "blocked" if require_route else PASS,
            "route_supplied": False,
            "route_id": None,
            "error_codes": (
                ["VERIFIER_LAB_PROOF_ROUTE_MISSING"] if require_route else []
            ),
            "missing_component_organs": [],
            "missing_pattern_ids": [],
            "source_sha256": None,
            "source_ref": None,
            "available_pattern_ids": [],
            "source_refs": [],
        }

    route = payload.get("foundation_route")
    if not isinstance(route, dict):
        route = {}
    component_rows = payload.get("component_map")
    if not isinstance(component_rows, list):
        component_rows = []
    expected_organs = {
        str(row.get("component_organ_id") or "")
        for row in component_rows
        if isinstance(row, dict)
    } or EXPECTED_ROUTE_COMPONENT_ORGANS
    actual_organs = {
        str(row.get("organ_id") or "")
        for row in component_specs
        if isinstance(row, dict)
    }
    available_pattern_ids = set(_strings(route.get("available_pattern_ids")))
    error_codes: list[str] = []
    route_id = str(route.get("route_id") or payload.get("route_id") or "")
    if route_id != EXPECTED_PROOF_LAB_ROUTE_ID:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_ID_MISMATCH")
    missing_organs = sorted(expected_organs - actual_organs)
    if missing_organs:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_COMPONENT_MISSING")
    missing_patterns = sorted(EXPECTED_ROUTE_PATTERN_IDS - available_pattern_ids)
    if missing_patterns:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_PATTERN_MISSING")
    source_sha256 = str(payload.get("source_sha256") or "")
    if not source_sha256.startswith("sha256:"):
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_SOURCE_DIGEST_MISSING")
    source_refs = _strings(route.get("substrate_ref_sample"))
    if not source_refs:
        error_codes.append("VERIFIER_LAB_PROOF_ROUTE_SUBSTRATE_REFS_MISSING")

    return {
        "status": PASS if not error_codes else "blocked",
        "route_supplied": True,
        "route_id": route_id or None,
        "error_codes": error_codes,
        "missing_component_organs": missing_organs,
        "missing_pattern_ids": missing_patterns,
        "source_sha256": source_sha256 or None,
        "source_ref": payload.get("source_ref"),
        "available_pattern_ids": sorted(available_pattern_ids),
        "detailed_binding_pattern_ids": _strings(
            route.get("detailed_binding_pattern_ids")
        ),
        "component_map": [
            {
                "pattern_id": str(row.get("pattern_id") or ""),
                "component_organ_id": str(row.get("component_organ_id") or ""),
                "component_role": str(row.get("component_role") or ""),
            }
            for row in component_rows
            if isinstance(row, dict)
        ],
        "source_refs": source_refs,
        "anti_claim_floor": route.get("anti_claim_floor"),
        "next_refinement_move": route.get("next_refinement_move"),
    }


def _run_component_stack(
    packet: dict[str, Any],
    *,
    input_dir: Path,
    out_dir: Path,
    command: str,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    components_out = out_dir / "components"
    results: dict[str, dict[str, Any]] = {}
    receipt_refs: dict[str, list[str]] = {}
    for spec in _component_specs(packet):
        organ_id = str(spec.get("organ_id") or "")
        runner_set = COMPONENT_RUNNERS.get(organ_id)
        if runner_set is None:
            results[organ_id] = {
                "status": "blocked",
                "error_code": "VERIFIER_LAB_COMPONENT_UNKNOWN",
                "organ_id": organ_id,
            }
            continue
        input_rel = str(spec.get("input_rel") or "")
        input_path = public_root / input_rel
        mode = str(spec.get("input_mode") or "fixture")
        runner = runner_set["bundle" if mode.startswith("exported") else "fixture"]
        target = components_out / organ_id
        kwargs: dict[str, Any] = {"command": f"{command} :: component {organ_id}"}
        if not mode.startswith("exported"):
            kwargs["acceptance_out"] = (
                components_out
                / "acceptance"
                / f"{organ_id}_fixture_acceptance.json"
            )
        result = runner(input_path, target, **kwargs)
        _normalize_component_receipt_surface(target)
        if "acceptance_out" in kwargs:
            _rewrite_json_receipt_without_legacy_redaction(kwargs["acceptance_out"])
        results[organ_id] = _without_legacy_redaction_receipt_fields(result)
        refs = result.get("receipt_paths", [])
        receipt_refs[organ_id] = [str(ref) for ref in refs if isinstance(ref, str)]
    return {
        "status": PASS if results and all(row.get("status") == PASS for row in results.values()) else "blocked",
        "component_statuses": {
            organ_id: row.get("status") for organ_id, row in sorted(results.items())
        },
        "component_receipt_refs": receipt_refs,
        "lean_lake_return_code": (
            results.get("formal_math_lean_proof_witness", {})
            .get("lake_build", {})
            .get("return_code")
        ),
        "lean_compiled_declaration_count": results.get(
            "formal_math_lean_proof_witness", {}
        ).get("compiled_declaration_count"),
        "target_shape_route_case_count": results.get(
            "target_shape_tactic_routing_gate", {}
        ).get("route_case_count"),
        "verifier_trace_attempt_count": results.get(
            "formal_math_verifier_trace_repair_loop", {}
        ).get("attempt_count"),
        "component_results": results,
    }


def _proof_lab_component_metrics(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    corpus = results.get("corpus_readiness_mathlib_absence_gate", {})
    index = results.get("lean_std_premise_index", {})
    retrieval = results.get("formal_math_premise_retrieval", {})
    tactic = results.get("tactic_portfolio_availability_probe", {})
    target_shape = results.get("target_shape_tactic_routing_gate", {})
    ring2 = results.get("ring2_premise_retrieval_precision_recall_harness", {})
    trace_repair = results.get("formal_math_verifier_trace_repair_loop", {})
    diagnostics = results.get("proof_diagnostic_evidence_spine", {})
    witness = results.get("formal_math_lean_proof_witness", {})
    return {
        "corpus_count": corpus.get("corpus_count"),
        "mathlib_lake_project_import_available": corpus.get(
            "mathlib_lake_project_import_available"
        ),
        "lean_std_premise_count": index.get("premise_count"),
        "retrieval_query_count": retrieval.get("query_count"),
        "retrieval_mean_public_recall": retrieval.get(
            "mean_public_retrieval_recall"
        ),
        "tactic_probe_status": tactic.get("status"),
        "target_shape_route_case_count": target_shape.get("route_case_count"),
        "ring2_problem_count": ring2.get("problem_count"),
        "ring2_mean_precision_at_k": ring2.get("mean_precision_at_k"),
        "ring2_mean_recall_at_k": ring2.get("mean_recall_at_k"),
        "verifier_trace_attempt_count": trace_repair.get("attempt_count"),
        "proof_diagnostic_accepted_count": len(
            diagnostics.get("accepted_check_ids", [])
            if isinstance(diagnostics.get("accepted_check_ids"), list)
            else []
        ),
        "proof_diagnostic_rejected_count": len(
            diagnostics.get("rejected_check_ids", [])
            if isinstance(diagnostics.get("rejected_check_ids"), list)
            else []
        ),
        "lean_lake_return_code": witness.get("lake_build", {}).get(
            "return_code"
        ),
        "lean_compiled_declaration_count": witness.get(
            "compiled_declaration_count"
        ),
    }


def _claim_separation(
    packet_result: dict[str, Any],
    component_result: dict[str, Any],
) -> dict[str, Any]:
    verifier_attempts = packet_result["verifier_attempts"]
    residuals = packet_result["residual_diagnoses"]
    provider_hypotheses = packet_result["provider_hypotheses"]
    oracle_sidecars = packet_result["oracle_sidecars"]
    cp2_candidates = packet_result["cp2_action_candidates"]
    evolve_candidates = packet_result["evolve_candidates"]
    negative_cases = packet_result["observed_negative_cases"]
    return {
        "lean_verified": [
            {
                "source": "formal_math_lean_proof_witness",
                "component_status": component_result["component_statuses"].get(
                    "formal_math_lean_proof_witness"
                ),
                "compiled_declaration_count": component_result[
                    "lean_compiled_declaration_count"
                ],
                "receipt_refs": component_result["component_receipt_refs"].get(
                    "formal_math_lean_proof_witness", []
                ),
                "body_in_receipt": False,
            },
            *[
                row
                for row in verifier_attempts
                if row.get("verifier_result_class") == "lean_verified"
            ],
        ],
        "provider_suggested": provider_hypotheses,
        "oracle_compared": oracle_sidecars,
        "contract_rejected": [
            {
                "case_id": case_id,
                "error_codes": codes,
                "authority": "rejected_contract_violation_not_forward_result",
            }
            for case_id, codes in sorted(negative_cases.items())
        ],
        "retrieval_miss": [
            row
            for row in residuals
            if row.get("residual_class") == "PREMISE_RETRIEVAL_MISS"
        ],
        "cp2_translated": cp2_candidates,
        "evolve_candidate": evolve_candidates,
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
    out_dir: Path,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    packet = payloads.get("verifier_lab_packet", {})
    if not isinstance(packet, dict):
        packet = {}
    proof_lab_route = payloads.get("proof_lab_route")
    if not isinstance(proof_lab_route, dict):
        proof_lab_route = None
    negative_payloads = {
        Path(name).stem: payloads[Path(name).stem]
        for name in NEGATIVE_INPUT_NAMES
        if Path(name).stem in payloads
    }
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )

    component_specs = _component_specs(packet)
    component = _run_component_stack(
        packet,
        input_dir=input_dir,
        out_dir=out_dir,
        command=command,
    )
    proof_route = _validate_proof_lab_route(
        proof_lab_route,
        component_specs=component_specs,
        require_route=input_mode == "exported_verifier_lab_kernel_bundle",
    )
    packet_result = _validate_packet(
        packet,
        negative_payloads,
        require_negative_cases=include_negative,
    )
    findings = [
        *packet_result["positive_findings"],
        *packet_result["negative_findings"],
    ]
    error_codes = sorted(
        {
            str(row["error_code"])
            for row in findings
        }
        | set(proof_route["error_codes"])
    )
    claim_separation = _claim_separation(packet_result, component)
    status = (
        PASS
        if secret_scan["blocking_hit_count"] == 0
        and component["status"] == PASS
        and packet_result["status"] == PASS
        and proof_route["status"] == PASS
        else "blocked"
    )
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    return {
        "schema_version": "verifier_lab_kernel_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "kernel_id": packet_result["kernel_id"],
        "source_pattern_ids": packet_result["source_pattern_ids"],
        "source_refs": packet_result["source_refs"],
        "projection_receipt_refs": packet_result["projection_receipt_refs"],
        "public_runtime_refs": packet_result["public_runtime_refs"],
        "proof_lab_route": proof_route,
        "proof_lab_route_id": proof_route["route_id"],
        "proof_lab_route_source_sha256": proof_route["source_sha256"],
        "proof_lab_route_component_count": len(
            {
                row.get("component_organ_id")
                for row in proof_route.get("component_map", [])
                if isinstance(row, dict) and row.get("component_organ_id")
            }
        ),
        "proof_lab_component_metrics": _proof_lab_component_metrics(
            component["component_results"]
        ),
        "expected_negative_cases": packet_result["expected_negative_cases"],
        "observed_negative_cases": packet_result["observed_negative_cases"],
        "missing_negative_cases": packet_result["missing_negative_cases"],
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "component_statuses": component["component_statuses"],
        "component_receipt_refs": component["component_receipt_refs"],
        "lean_lake_return_code": component["lean_lake_return_code"],
        "lean_compiled_declaration_count": component["lean_compiled_declaration_count"],
        "target_shape_route_case_count": component["target_shape_route_case_count"],
        "verifier_trace_attempt_count": component["verifier_trace_attempt_count"],
        "forward_problems": packet_result["forward_problems"],
        "oracle_sidecars": packet_result["oracle_sidecars"],
        "verifier_attempts": packet_result["verifier_attempts"],
        "provider_hypotheses": packet_result["provider_hypotheses"],
        "residual_diagnoses": packet_result["residual_diagnoses"],
        "cp2_action_candidates": packet_result["cp2_action_candidates"],
        "evolve_candidates": packet_result["evolve_candidates"],
        "claim_separation": claim_separation,
        "authority_split": {
            "forward_success": "independent verifier receipt only",
            "oracle": "diagnostic comparator only",
            "provider": "advisory hypothesis only",
            "cp2": "typed action candidate plus rerun receipt only",
            "evolve": "bounded policy candidate plus rerun/quarantine receipt only",
        },
        "authority_counters": {
            "oracle_forward_success_increment_count": sum(
                1
                for row in packet_result["oracle_sidecars"]
                if row.get("counted_as_forward_success") is True
            ),
            "provider_results_counted": sum(
                1
                for row in packet_result["provider_hypotheses"]
                if row.get("provider_results_counted") is True
            ),
            "proof_body_export_count": sum(
                1
                for row in findings
                if row["error_code"]
                in {
                    "VERIFIER_LAB_FORWARD_FIELD_FORBIDDEN",
                    "VERIFIER_LAB_CP2_PROOF_BODY_FORBIDDEN",
                }
            ),
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_transparency_contract": RECEIPT_TRANSPARENCY_CONTRACT,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "verifier_lab_kernel_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "verifier_lab_kernel_public_board",
        "kernel_id": result["kernel_id"],
        "input_mode": result["input_mode"],
        "component_statuses": result["component_statuses"],
        "lab_summary": {
            "forward_problem_count": len(result["forward_problems"]),
            "oracle_sidecar_count": len(result["oracle_sidecars"]),
            "verifier_attempt_count": len(result["verifier_attempts"]),
            "provider_hypothesis_count": len(result["provider_hypotheses"]),
            "cp2_candidate_count": len(result["cp2_action_candidates"]),
            "evolve_candidate_count": len(result["evolve_candidates"]),
            "proof_lab_route_id": result["proof_lab_route_id"],
            "proof_lab_route_component_count": result[
                "proof_lab_route_component_count"
            ],
            "lean_compiled_declaration_count": result[
                "lean_compiled_declaration_count"
            ],
            "target_shape_route_case_count": result["target_shape_route_case_count"],
            "verifier_trace_attempt_count": result["verifier_trace_attempt_count"],
        },
        "proof_lab_route": result["proof_lab_route"],
        "proof_lab_component_metrics": result["proof_lab_component_metrics"],
        "claim_separation": result["claim_separation"],
        "authority_split": result["authority_split"],
        "authority_counters": result["authority_counters"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_transparency_contract": result["receipt_transparency_contract"],
        "anti_claim": result["anti_claim"],
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
    bundle_only: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    if bundle_only:
        path = out_dir / BUNDLE_RESULT_NAME
        receipt = {
            **result,
            "schema_version": "exported_verifier_lab_kernel_bundle_validation_result_v1",
            "receipt_paths": [_display(path, public_root=public_root)],
        }
        write_json_atomic(path, receipt)
        return {**result, "receipt_paths": receipt["receipt_paths"]}

    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    result_receipt = {
        **result,
        "schema_version": "verifier_lab_kernel_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    validation = {
        "schema_version": "verifier_lab_kernel_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "component_statuses": result["component_statuses"],
        "proof_lab_route": result["proof_lab_route"],
        "proof_lab_component_metrics": result["proof_lab_component_metrics"],
        "claim_separation_keys": sorted(result["claim_separation"]),
        "authority_counters": result["authority_counters"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_transparency_contract": result["receipt_transparency_contract"],
        "receipt_body_is_public_evidence": True,
        "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "verifier_lab_kernel_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "component_statuses": result["component_statuses"],
        "proof_lab_route": result["proof_lab_route"],
        "proof_lab_component_metrics": result["proof_lab_component_metrics"],
        "authority_counters": result["authority_counters"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_transparency_contract": result["receipt_transparency_contract"],
        "receipt_body_is_public_evidence": True,
        "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "verifier_lab_kernel_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.verifier_lab_kernel run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    target = Path(out_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
        out_dir=target,
    )
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
        bundle_only=False,
    )


def run_kernel_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.verifier_lab_kernel run-kernel-bundle",
) -> dict[str, Any]:
    target = Path(out_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_verifier_lab_kernel_bundle",
        include_negative=False,
        out_dir=target,
    )
    return _write_receipts(result, target, acceptance_out=None, bundle_only=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verifier_lab_kernel")
    parser.add_argument("action", choices=["run", "run-kernel-bundle"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--acceptance-out")
    args = parser.parse_args(argv)
    if args.action == "run-kernel-bundle":
        run_kernel_bundle(args.input, args.out)
    else:
        run(args.input, args.out, acceptance_out=args.acceptance_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
