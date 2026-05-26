#!/usr/bin/env python3
"""Reduce prover provider receipts into Lean-checked Oracle/Foundry evidence.

The provider plane owns dispatch.  This reducer owns the next deterministic
step: treat a prover_context_hypothesis row_patch as a proof-body hypothesis,
run Lean, classify the result, and write run artifacts.  It never calls a
provider and never promotes row patches into source authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import run_prover_graph_benchmark as harness
from system.lib import provider_row_patch_review


DEFAULT_RUN_ID = "PROVER_PROVIDER_RECEIPT_REDUCER_20260511_v0"
DEFAULT_RUN_ROOT = Path("state/runs") / DEFAULT_RUN_ID
TASK_CLASS = "prover_context_hypothesis"
STRATEGY_CLASSIFICATION_TASK_CLASS = "prover_strategy_classification"
TRUTH_SIDE_FORBIDDEN_MARKERS = (
    "truth_side_proof_bodies",
    "oracle_only_repair_bodies",
    "withheld_until_oracle",
    "oracle_needed_premise_ids",
    "ideal_body",
    "repair_body",
    "retrieval_body",
)
QUALIFIED_SYMBOL_RE = re.compile(r"\b(?:Nat|List|Bool|Iff|Eq)\.[A-Za-z0-9_.']+\b")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _find_row_patch_for_receipt(receipt_id: str) -> Path | None:
    root = REPO_ROOT / "state/compute_workers/row_patches"
    if not root.is_dir():
        return None
    for path in sorted(root.rglob("*.json")):
        try:
            payload = _read_json(path)
        except Exception:
            continue
        if str(payload.get("receipt_id") or "") == receipt_id:
            return path
    return None


def _normalize_proof_body(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        raw_lines = [str(line) for line in value]
    else:
        raw_lines = str(value or "").splitlines() or [str(value or "")]
    lines: list[str] = []
    for raw in raw_lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        lines.append(line if line[:1].isspace() else f"  {line}")
    return tuple(lines)


def _problem_by_id(problem_id: str) -> harness.ProverProblem:
    for problem in harness._strategy_problem_set():
        if problem.problem_id == problem_id:
            return problem
    raise ValueError(f"unknown prover problem_id: {problem_id}")


def _problem_from_transform_job(
    *,
    input_packet: Mapping[str, Any],
    context_pack: Mapping[str, Any],
) -> harness.ProverProblem | None:
    """Recover a forward-safe external problem row embedded in a transform job."""

    row = input_packet.get("formal_problem")
    if not isinstance(row, Mapping):
        row = context_pack.get("formal_problem")
    if not isinstance(row, Mapping):
        return None
    normalized = dict(row)
    normalized.setdefault("candidate_body", [])
    normalized.setdefault("ideal_body", [])
    normalized.setdefault("visible_to_lab", ["statement", "required imports"])
    normalized.setdefault(
        "withheld_until_oracle",
        ["ideal proof body", "repair proof body", "oracle critique"],
    )
    return harness._problem_from_manifest_row(normalized)


def _provider_value(row_patch: Mapping[str, Any]) -> dict[str, Any]:
    proposed = row_patch.get("proposed_value")
    if isinstance(proposed, Mapping):
        return dict(proposed)
    return {}


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        rows: list[str] = []
        for nested in value.values():
            rows.extend(_flatten_strings(nested))
        return rows
    if isinstance(value, list | tuple):
        rows = []
        for nested in value:
            rows.extend(_flatten_strings(nested))
        return rows
    if value is None:
        return []
    return [str(value)]


def _truth_side_leakage_hits(
    *,
    provider_value: Mapping[str, Any],
    context_pack: Mapping[str, Any],
) -> list[str]:
    configured = [
        str(item).strip()
        for item in context_pack.get("forbidden_material", [])
        if str(item).strip()
    ]
    markers = sorted(set(configured + list(TRUTH_SIDE_FORBIDDEN_MARKERS)))
    output_text = "\n".join(_flatten_strings(provider_value)).lower()
    return [marker for marker in markers if len(marker) >= 4 and marker.lower() in output_text]


def _explicit_library_priors(provider_value: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("library_priors_used", "undeclared_library_prior_symbols"):
        raw = provider_value.get(key)
        if isinstance(raw, str):
            values.append(raw)
        elif isinstance(raw, list | tuple):
            values.extend(str(item) for item in raw if str(item).strip())
    return sorted(set(values))


def _undeclared_library_prior_symbols(
    *,
    provider_value: Mapping[str, Any],
    proof_body: tuple[str, ...],
    premise_index: Mapping[str, Any],
    allowed_premise_ids: list[str],
    cited_unallowed_premise_ids: list[str],
) -> list[str]:
    """Conservative detector for provider-declared library priors.

    Unknown library-prior use is hard to infer from Lean text alone without a
    full environment symbol table.  v0 therefore trusts explicit provider
    self-report and known premise-index citations; known out-of-budget
    citations are handled as PREMISE_BUDGET_VIOLATION instead.
    """

    if cited_unallowed_premise_ids:
        return []
    allowed = set(allowed_premise_ids)
    indexed_by_name: dict[str, str] = {}
    for row in premise_index.get("premises", []) if isinstance(premise_index, Mapping) else []:
        if not isinstance(row, Mapping):
            continue
        premise_id = str(row.get("premise_id") or "").strip()
        name = str(row.get("theorem_or_def_name") or "").strip()
        if premise_id and name:
            indexed_by_name[name] = premise_id
    explicit = _explicit_library_priors(provider_value)
    detected = set(explicit)
    for line in proof_body:
        for symbol in QUALIFIED_SYMBOL_RE.findall(line):
            premise_id = indexed_by_name.get(symbol)
            if premise_id and premise_id not in allowed:
                return []
    return sorted(detected)


def _classify_failure(
    *,
    receipt: Mapping[str, Any],
    provider_value: Mapping[str, Any],
    lean_status: str,
    axiom_classification: str,
    leakage_status: str,
    premise_policy_status: str,
    unallowed_premise_ids: list[str],
    cited_unallowed_premise_ids: list[str],
    undeclared_library_prior_symbols: list[str],
    malformed: bool,
) -> str:
    if receipt.get("status") != "ok" or not (receipt.get("validation_result") or {}).get("passed"):
        return "PROVIDER_CONTRACT_FAIL"
    if malformed:
        return "PROVIDER_CONTRACT_FAIL"
    if leakage_status != "PASS":
        return "SOLUTION_LEAKAGE"
    if premise_policy_status != "PASS" or unallowed_premise_ids or cited_unallowed_premise_ids:
        return "PREMISE_BUDGET_VIOLATION"
    if undeclared_library_prior_symbols:
        return "UNDECLARED_LIBRARY_PRIOR"
    if lean_status == "PASS" and axiom_classification == "CLEAN":
        return "NONE"
    stderr = str(provider_value.get("lean_stderr") or "")
    if "unknown identifier" in stderr:
        return "PREMISE_RETRIEVAL_MISS"
    return "PROOF_SYNTHESIS_FAIL"


def _review_outcome_for_error(error_class: str) -> tuple[str, str]:
    if error_class == "NONE":
        return (
            "accept_as_advisory_signal",
            "Lean accepted the provider proof hypothesis; keep advisory until an explicit apply lane promotes it.",
        )
    if error_class in {"SOLUTION_LEAKAGE", "PROVIDER_CONTRACT_FAIL"}:
        return (
            "reject",
            f"Provider proof hypothesis rejected by reducer: {error_class}.",
        )
    if error_class == "PREMISE_BUDGET_VIOLATION":
        return (
            "retry",
            "Provider proof hypothesis rejected for this context recipe; retry with an explicit premise context.",
        )
    if error_class == "UNDECLARED_LIBRARY_PRIOR":
        return (
            "bridge_escalate",
            "Provider proof hypothesis used an undeclared library prior; quarantine or score separately from recipe-clean success.",
        )
    return (
        "retry",
        f"Provider proof hypothesis did not pass Lean and should feed repair/foundry learning: {error_class}.",
    )


def _run_summary(run_root: Path, *, cap_id: str = "cap_prover_provider_receipt_reducer_v0") -> dict[str, Any]:
    reports = []
    for path in sorted((run_root / "reductions").glob("*/receipt_reduction_report.json")):
        try:
            reports.append(_read_json(path))
        except Exception:
            continue
    lean_accepted = [row for row in reports if row.get("accepted_by_lean") is True]
    recipe_accepted = [row for row in reports if row.get("recipe_policy_passed") is True]
    leakage_failures = [
        row for row in reports if (row.get("leakage_audit") or {}).get("status") != "PASS"
    ]
    premise_policy_failures = [
        row for row in reports if (row.get("premise_policy_audit") or {}).get("status") != "PASS"
    ]
    error_counts: dict[str, int] = {}
    for row in reports:
        error = str(row.get("error_class") or "UNKNOWN")
        error_counts[error] = error_counts.get(error, 0) + 1
    return {
        "schema_version": "provider_receipt_reducer_run_summary_v0",
        "run_id": run_root.name,
        "cap_id": cap_id,
        "created_at": _utc_now(),
        "receipt_count": len(reports),
        "accepted_count": len(recipe_accepted),
        "lean_accepted_count": len(lean_accepted),
        "recipe_policy_accepted_count": len(recipe_accepted),
        "leakage_failure_count": len(leakage_failures),
        "premise_policy_failure_count": len(premise_policy_failures),
        "error_counts": error_counts,
        "provider_calls_by_reducer": 0,
        "harness_owned_provider_dispatch_added": False,
        "reductions": [
            {
                "receipt_id": row.get("receipt_ref", "").split("/")[-1].removesuffix(".json"),
                "problem_id": row.get("problem_id"),
                "accepted_by_lean": row.get("accepted_by_lean"),
                "recipe_policy_passed": row.get("recipe_policy_passed"),
                "error_class": row.get("error_class"),
                "report_ref": row.get("lean_check_result_ref", "").rsplit("/", 1)[0] + "/receipt_reduction_report.json",
                "row_patch_review_ref": row.get("row_patch_review_ref"),
                "row_patch_review_outcome": row.get("row_patch_review_outcome"),
            }
            for row in reports
        ],
    }


def _reduce_strategy_classification_receipt(
    *,
    receipt: Mapping[str, Any],
    row_patch: Mapping[str, Any],
    transform_job: Mapping[str, Any],
    receipt_path: Path,
    row_patch_path: Path,
    transform_job_path: Path,
    context_pack: Mapping[str, Any],
    run_root: Path,
    cap_id: str,
) -> dict[str, Any]:
    """Reduce a provider receipt for the strategy_id_classification recipe.

    The reducer:
      - parses the provider value as a strategy advisory,
      - rejects any Lean proof body, full tactic script, or oracle material,
      - validates strategy_id against the known mathematical_strategy_atlas_v0 enum,
      - emits a provider_strategy_advisory_row instead of a proof-body learning row,
      - skips Lean execution entirely; provider text is not proof authority.
    """
    receipt_id = str(receipt.get("receipt_id") or "")
    provider_value = _provider_value(row_patch)
    known_ids = set(harness._known_strategy_ids())
    strategy_id_raw = provider_value.get("strategy_id")
    strategy_id = str(strategy_id_raw).strip() if isinstance(strategy_id_raw, str) else ""
    forbidden_audit = provider_value.get("forbidden_output_audit") or {}
    if not isinstance(forbidden_audit, Mapping):
        forbidden_audit = {}
    audit_flags = {
        key: bool(forbidden_audit.get(key))
        for key in (
            "contains_lean_proof_body",
            "contains_full_tactic_script",
            "contains_oracle_material",
        )
    }
    contains_lean_proof_body = bool(provider_value.get("lean_proof_body"))
    explicit_audit_failure = any(audit_flags.values())
    leakage_audit_status = (
        "FAIL"
        if explicit_audit_failure or contains_lean_proof_body
        else "PASS"
    )
    if not strategy_id:
        reducer_status = "missing_strategy_id"
    elif strategy_id not in known_ids:
        reducer_status = "invalid_strategy_id"
    elif leakage_audit_status == "FAIL":
        reducer_status = "invalid_leakage"
    else:
        reducer_status = "ok"
    accepted_by_reducer = reducer_status == "ok"
    confidence_value = provider_value.get("confidence")
    confidence = float(confidence_value) if isinstance(confidence_value, (int, float)) else None
    reasons = [
        str(r) for r in (provider_value.get("reasons") or []) if isinstance(r, str)
    ]
    decomposition_hint_value = provider_value.get("decomposition_hint")
    decomposition_hint = str(decomposition_hint_value) if isinstance(decomposition_hint_value, str) else ""
    expected_tactic_family = [
        str(t)
        for t in (provider_value.get("expected_tactic_family") or [])
        if isinstance(t, str)
    ]
    expected_premise_ids = [
        str(p)
        for p in (provider_value.get("expected_premise_ids") or [])
        if isinstance(p, str)
    ]
    problem_id = str(context_pack.get("target_problem_id") or "").strip()
    reduction_root = run_root / "reductions" / receipt_id
    reduction_root.mkdir(parents=True, exist_ok=True)
    strategy_advisory_row = {
        "schema_version": "provider_strategy_advisory_row_v0",
        "receipt_id": receipt_id,
        "row_patch_id": row_patch.get("patch_id"),
        "transform_job_id": transform_job.get("id"),
        "problem_id": problem_id,
        "strategy_id": strategy_id,
        "strategy_source": "provider_strategy_classification",
        "graph_role": context_pack.get("graph_role"),
        "recipe_id": (transform_job.get("provider_selection_policy") or {}).get("context_recipe_id"),
        "provider_id": receipt.get("provider_id"),
        "model_id": receipt.get("model_id"),
        "confidence": confidence,
        "reasons": reasons,
        "decomposition_hint": decomposition_hint,
        "expected_tactic_family": expected_tactic_family,
        "expected_premise_ids": expected_premise_ids,
        "provider_results_counted": False,
        "leakage_audit": {
            "status": leakage_audit_status,
            "contains_lean_proof_body": contains_lean_proof_body or audit_flags["contains_lean_proof_body"],
            "contains_full_tactic_script": audit_flags["contains_full_tactic_script"],
            "contains_oracle_material": audit_flags["contains_oracle_material"],
        },
        "reducer_status": reducer_status,
        "accepted_by_reducer": accepted_by_reducer,
        "next_action": (
            "consume strategy advisory in deterministic strategy_control search; compute strategy_match_rate"
            if accepted_by_reducer
            else "reject advisory; do not inject into deterministic search"
        ),
    }
    receipt_reduction_report = {
        "schema_version": "provider_strategy_classification_reduction_report_v0",
        "run_id": run_root.name,
        "reduced_at": _utc_now(),
        "receipt_id": receipt_id,
        "row_patch_id": row_patch.get("patch_id"),
        "transform_job_id": transform_job.get("id"),
        "provider_id": receipt.get("provider_id"),
        "model_id": receipt.get("model_id"),
        "receipt_ref": _rel(receipt_path),
        "row_patch_ref": _rel(row_patch_path),
        "transform_job_ref": _rel(transform_job_path),
        "problem_id": problem_id,
        "graph_role": context_pack.get("graph_role"),
        "recipe_id": (transform_job.get("provider_selection_policy") or {}).get("context_recipe_id"),
        "task_class": STRATEGY_CLASSIFICATION_TASK_CLASS,
        "deliverable_type": "strategy_id_classification",
        "reducer_status": reducer_status,
        "accepted_by_reducer": accepted_by_reducer,
        "strategy_advisory_row_ref": _rel(reduction_root / "strategy_advisory_row.json"),
        "leakage_audit": strategy_advisory_row["leakage_audit"],
        "known_strategy_ids": sorted(known_ids),
        "provider_results_counted": False,
        "report_hash": None,
    }
    receipt_reduction_report["report_hash"] = _sha256_json(
        {
            "strategy_advisory_row": strategy_advisory_row,
            "receipt_id": receipt_id,
        }
    )
    _write_json(reduction_root / "strategy_advisory_row.json", strategy_advisory_row)
    _write_json(reduction_root / "receipt_reduction_report.json", receipt_reduction_report)
    run_summary = _run_summary(run_root, cap_id=cap_id)
    run_summary["latest_reduction"] = {
        "receipt_id": receipt_id,
        "provider_id": receipt.get("provider_id"),
        "model_id": receipt.get("model_id"),
        "problem_id": problem_id,
        "task_class": STRATEGY_CLASSIFICATION_TASK_CLASS,
        "reducer_status": reducer_status,
        "accepted_by_reducer": accepted_by_reducer,
        "strategy_id": strategy_id,
        "receipt_reduction_report": _rel(reduction_root / "receipt_reduction_report.json"),
        "strategy_advisory_row": _rel(reduction_root / "strategy_advisory_row.json"),
    }
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def reduce_receipt(
    *,
    receipt_path: Path,
    row_patch_path: Path | None,
    transform_job_path: Path,
    run_root: Path,
    timeout_seconds: int,
    cap_id: str = "cap_prover_provider_receipt_reducer_v0",
) -> dict[str, Any]:
    receipt = _read_json(receipt_path)
    receipt_id = str(receipt.get("receipt_id") or "")
    if not receipt_id:
        raise ValueError("provider receipt is missing receipt_id")
    if row_patch_path is None:
        row_patch_path = _find_row_patch_for_receipt(receipt_id)
    if row_patch_path is None:
        raise ValueError(f"no row_patch found for receipt_id={receipt_id}")
    row_patch = _read_json(row_patch_path)
    transform_job = _read_json(transform_job_path)
    input_packet = transform_job.get("input_packet") if isinstance(transform_job.get("input_packet"), Mapping) else {}
    context_pack = (
        input_packet.get("prover_context_pack")
        if isinstance(input_packet.get("prover_context_pack"), Mapping)
        else {}
    )
    transform_task_class = str(transform_job.get("task_class") or "").strip()
    pack_deliverable_type = str(context_pack.get("deliverable_type") or "").strip()
    if (
        transform_task_class == STRATEGY_CLASSIFICATION_TASK_CLASS
        or pack_deliverable_type == "strategy_id_classification"
    ):
        return _reduce_strategy_classification_receipt(
            receipt=receipt,
            row_patch=row_patch,
            transform_job=transform_job,
            receipt_path=receipt_path,
            row_patch_path=row_patch_path,
            transform_job_path=transform_job_path,
            context_pack=context_pack,
            run_root=run_root,
            cap_id=cap_id,
        )
    problem_id = str(context_pack.get("target_problem_id") or "").strip()
    problem = _problem_from_transform_job(
        input_packet=input_packet,
        context_pack=context_pack,
    ) or _problem_by_id(problem_id)
    provider_value = _provider_value(row_patch)
    proof_body = _normalize_proof_body(provider_value.get("lean_proof_body"))
    malformed = not bool(proof_body)
    premise_ids_used = [
        str(item)
        for item in (provider_value.get("premise_ids_used") or [])
        if str(item).strip()
    ]
    allowed_premise_ids = [
        str(item)
        for item in (
            context_pack.get("allowed_premise_ids")
            or input_packet.get("allowed_premise_ids")
            or []
        )
        if str(item).strip()
    ]
    unallowed_premise_ids = sorted(set(premise_ids_used) - set(allowed_premise_ids))
    premise_index = harness._premise_index()
    cited_premise_ids = harness._premise_ids_cited(proof_body, premise_index)
    cited_unallowed_premise_ids = sorted(set(cited_premise_ids) - set(allowed_premise_ids))
    undeclared_library_prior_symbols = _undeclared_library_prior_symbols(
        provider_value=provider_value,
        proof_body=proof_body,
        premise_index=premise_index,
        allowed_premise_ids=allowed_premise_ids,
        cited_unallowed_premise_ids=cited_unallowed_premise_ids,
    )
    reduction_root = run_root / "reductions" / receipt_id
    candidate_path = reduction_root / "candidate.lean"
    lean_source = harness._lean_source(
        problem,
        graph_variant_id="provider_receipt_reducer_v0",
        body=proof_body,
        attempt_label=f"provider_receipt:{receipt_id}",
        retrieved_premise_ids=tuple(allowed_premise_ids),
        cited_premise_ids=tuple(cited_premise_ids),
    )
    _write_text(candidate_path, lean_source)
    lean_result = harness._run_lean(candidate_path, timeout_seconds=timeout_seconds)
    stdout_path = reduction_root / "lean_stdout.txt"
    stderr_path = reduction_root / "lean_stderr.txt"
    _write_text(stdout_path, str(lean_result.get("stdout") or ""))
    _write_text(stderr_path, str(lean_result.get("stderr") or ""))
    lean_status = "TIMEOUT" if lean_result.get("timeout") else ("PASS" if lean_result.get("exit_code") == 0 else "FAIL")
    sorry_present = bool(harness.SORRY_RE.search(lean_source))
    axiom_classification = harness._classify_axioms(
        str(lean_result.get("stdout") or ""),
        lean_status,
        sorry_present,
    )
    truth_side_leakage_hits = _truth_side_leakage_hits(
        provider_value=provider_value,
        context_pack=context_pack,
    )
    leakage_status = "FAIL" if truth_side_leakage_hits else "PASS"
    premise_policy_status = (
        "FAIL"
        if unallowed_premise_ids or cited_unallowed_premise_ids or undeclared_library_prior_symbols
        else "PASS"
    )
    error_class = _classify_failure(
        receipt=receipt,
        provider_value={**provider_value, "lean_stderr": lean_result.get("stderr")},
        lean_status=lean_status,
        axiom_classification=axiom_classification,
        leakage_status=leakage_status,
        premise_policy_status=premise_policy_status,
        unallowed_premise_ids=unallowed_premise_ids,
        cited_unallowed_premise_ids=cited_unallowed_premise_ids,
        undeclared_library_prior_symbols=undeclared_library_prior_symbols,
        malformed=malformed,
    )
    lean_accepted = lean_status == "PASS" and axiom_classification == "CLEAN"
    recipe_policy_passed = error_class == "NONE"
    lean_check_result = {
        "schema_version": "provider_receipt_lean_check_result_v0",
        "receipt_id": receipt_id,
        "row_patch_id": row_patch.get("patch_id"),
        "transform_job_id": transform_job.get("id"),
        "problem_id": problem.problem_id,
        "candidate_ref": _rel(candidate_path),
        "checker": "lean",
        "compile_status": lean_status,
        "exit_code": lean_result.get("exit_code"),
        "duration_ms": lean_result.get("duration_ms"),
        "timeout": lean_result.get("timeout"),
        "stdout_ref": _rel(stdout_path),
        "stderr_ref": _rel(stderr_path),
        "sorry_present": sorry_present,
        "axiom_audit_classification": axiom_classification,
        "accepted": lean_accepted,
        "recipe_policy_passed": recipe_policy_passed,
    }
    oracle_attribution = {
        "schema_version": "provider_oracle_attribution_v0",
        "receipt_id": receipt_id,
        "problem_id": problem.problem_id,
        "provider_id": receipt.get("provider_id"),
        "model_id": receipt.get("model_id"),
        "graph_role": context_pack.get("graph_role"),
        "recipe_id": (transform_job.get("provider_selection_policy") or {}).get("context_recipe_id"),
        "error_class": error_class,
        "recipe_policy_passed": recipe_policy_passed,
        "provider_text_counts_as_success": False,
        "lean_acceptance_required": True,
        "premise_ids_used": premise_ids_used,
        "allowed_premise_ids": allowed_premise_ids,
        "unallowed_premise_ids": unallowed_premise_ids,
        "cited_premise_ids": cited_premise_ids,
        "cited_unallowed_premise_ids": cited_unallowed_premise_ids,
        "undeclared_library_prior_symbols": undeclared_library_prior_symbols,
        "truth_side_leakage_hits": truth_side_leakage_hits,
        "notes": provider_value.get("notes", ""),
    }
    foundry_learning_row = {
        "schema_version": "provider_foundry_learning_row_v0",
        "receipt_id": receipt_id,
        "problem_id": problem.problem_id,
        "source": "provider_receipt_reducer_v0",
        "learning_class": "provider_success_candidate" if recipe_policy_passed else error_class,
        "graph_role": context_pack.get("graph_role"),
        "recipe_id": (transform_job.get("provider_selection_policy") or {}).get("context_recipe_id"),
        "provider_id": receipt.get("provider_id"),
        "model_id": receipt.get("model_id"),
        "lean_compile_status": lean_status,
        "axiom_audit_classification": axiom_classification,
        "promotion_boundary": "provider row_patch remains draft until Type A apply/review; Lean success plus recipe policy is advisory evidence",
        "next_repair": "promote as foundry case memory candidate" if recipe_policy_passed else "route failure into Oracle/Foundry attribution",
    }
    review_outcome, review_notes = _review_outcome_for_error(error_class)
    row_patch_review = provider_row_patch_review.build_review_record(
        row_patch,
        review_outcome=review_outcome,
        reviewed_by="prover_provider_receipt_reducer_v0",
        promotion_blocker="provider output remains non-authoritative; Lean reducer result is advisory evidence only",
        notes=review_notes,
    )
    row_patch_review_path = provider_row_patch_review.write_review_record(
        REPO_ROOT,
        row_patch_review,
        overwrite=True,
    )
    receipt_reduction_report = {
        "schema_version": "provider_receipt_reduction_report_v0",
        "run_id": run_root.name,
        "reduced_at": _utc_now(),
        "receipt_id": receipt_id,
        "row_patch_id": row_patch.get("patch_id"),
        "transform_job_id": transform_job.get("id"),
        "provider_id": receipt.get("provider_id"),
        "model_id": receipt.get("model_id"),
        "receipt_ref": _rel(receipt_path),
        "row_patch_ref": _rel(row_patch_path),
        "transform_job_ref": _rel(transform_job_path),
        "problem_id": problem.problem_id,
        "graph_role": context_pack.get("graph_role"),
        "recipe_id": (transform_job.get("provider_selection_policy") or {}).get("context_recipe_id"),
        "provider_receipt_status": receipt.get("status"),
        "validation_result": receipt.get("validation_result"),
        "context_metrics": {
            "context_pack_id": context_pack.get("context_pack_id"),
            "context_budget": context_pack.get("context_budget"),
            "bytes_out": len(str(provider_value.get("lean_proof_body") or "").encode("utf-8")),
            "latency_ms": receipt.get("latency_ms"),
            "cost": receipt.get("cost"),
            "usage": receipt.get("usage"),
        },
        "leakage_audit": {
            "status": leakage_status,
            "truth_side_leakage_hits": truth_side_leakage_hits,
            "proof_body_forward_leak": bool(truth_side_leakage_hits),
        },
        "premise_policy_audit": {
            "status": premise_policy_status,
            "allowed_premise_ids": allowed_premise_ids,
            "premise_ids_used": premise_ids_used,
            "unallowed_premise_ids": unallowed_premise_ids,
            "cited_premise_ids": cited_premise_ids,
            "cited_unallowed_premise_ids": cited_unallowed_premise_ids,
            "undeclared_library_prior_symbols": undeclared_library_prior_symbols,
            "policy": "provider hypotheses may cite only premises supplied by the active context recipe; undeclared library priors are quarantined separately from truth-side leakage",
        },
        "lean_check_result_ref": _rel(reduction_root / "lean_check_result.json"),
        "provider_oracle_attribution_ref": _rel(reduction_root / "provider_oracle_attribution.json"),
        "foundry_learning_row_ref": _rel(reduction_root / "foundry_learning_row.json"),
        "row_patch_review_ref": _rel(row_patch_review_path),
        "row_patch_review_outcome": review_outcome,
        "accepted_by_lean": lean_accepted,
        "recipe_policy_passed": recipe_policy_passed,
        "error_class": error_class,
        "report_hash": None,
    }
    receipt_reduction_report["report_hash"] = _sha256_json(
        {
            "lean_check_result": lean_check_result,
            "oracle_attribution": oracle_attribution,
            "foundry_learning_row": foundry_learning_row,
            "row_patch_review": row_patch_review,
            "receipt_id": receipt_id,
        }
    )
    _write_json(reduction_root / "lean_check_result.json", lean_check_result)
    _write_json(reduction_root / "provider_oracle_attribution.json", oracle_attribution)
    _write_json(reduction_root / "foundry_learning_row.json", foundry_learning_row)
    _write_json(reduction_root / "receipt_reduction_report.json", receipt_reduction_report)
    run_summary = _run_summary(run_root, cap_id=cap_id)
    run_summary["latest_reduction"] = {
        "receipt_id": receipt_id,
        "provider_id": receipt.get("provider_id"),
        "model_id": receipt.get("model_id"),
        "problem_id": problem.problem_id,
        "accepted_by_lean": lean_accepted,
        "recipe_policy_passed": recipe_policy_passed,
        "error_class": error_class,
        "receipt_reduction_report": _rel(reduction_root / "receipt_reduction_report.json"),
        "lean_check_result": _rel(reduction_root / "lean_check_result.json"),
        "provider_oracle_attribution": _rel(reduction_root / "provider_oracle_attribution.json"),
        "foundry_learning_row": _rel(reduction_root / "foundry_learning_row.json"),
        "row_patch_review": _rel(row_patch_review_path),
        "row_patch_review_outcome": review_outcome,
    }
    _write_json(run_root / "run_summary.json", run_summary)
    return run_summary


def compute_strategy_match_comparison(
    *,
    provider_advisory_rows: list[Mapping[str, Any]],
    deterministic_strategy_by_problem: Mapping[str, str],
    matched_problem_manifest_digest: str | None = None,
) -> dict[str, Any]:
    """Compute strategy_match_rate between provider strategy advisories and the
    deterministic strategy_control selector's choice for each matched problem.

    Inputs:
      provider_advisory_rows: list of strategy_advisory_row dicts emitted by the
        strategy-classification reducer.
      deterministic_strategy_by_problem: mapping {problem_id: deterministic strategy_id}
        from the strategy_control_graph_v0 baseline run.
      matched_problem_manifest_digest: optional digest of the shared problem manifest
        that anchors the comparison.

    Output: a provider_strategy_match_comparison_v0 receipt with per-problem rows,
    aggregate match rate, leakage/invalid/missing counts, and the explicit
    provider_results_counted=false anti-cheat field.

    This function does not call a provider or run Lean. It consumes reducer outputs
    and the deterministic strategy_control selection. Search-efficiency deltas
    (transitions, depth, branching) are NOT computed here; they require running the
    deterministic search with the provider advisory injected, which is a separate
    wave.
    """
    rows: list[dict[str, Any]] = []
    comparable_count = 0
    matches = 0
    invalid_provider_count = 0
    leakage_rejection_count = 0
    missing_provider_count = 0
    accepted_provider_count = 0
    rejected_provider_count = 0
    for advisory in provider_advisory_rows:
        problem_id = str(advisory.get("problem_id") or "").strip()
        provider_strategy = str(advisory.get("strategy_id") or "").strip()
        reducer_status = str(advisory.get("reducer_status") or "").strip()
        accepted = bool(advisory.get("accepted_by_reducer"))
        deterministic_strategy = (
            deterministic_strategy_by_problem.get(problem_id)
            if problem_id
            else None
        )
        leakage_status = str(
            (advisory.get("leakage_audit") or {}).get("status") or ""
        ).strip()
        if accepted:
            accepted_provider_count += 1
        else:
            rejected_provider_count += 1
        if reducer_status == "invalid_leakage" or leakage_status == "FAIL":
            leakage_rejection_count += 1
        if reducer_status == "invalid_strategy_id":
            invalid_provider_count += 1
        if reducer_status == "missing_strategy_id":
            missing_provider_count += 1
        is_match = False
        if (
            accepted
            and deterministic_strategy
            and provider_strategy == str(deterministic_strategy).strip()
        ):
            is_match = True
            matches += 1
        if accepted and deterministic_strategy:
            comparable_count += 1
        rows.append(
            {
                "problem_id": problem_id,
                "provider_strategy_id": provider_strategy,
                "deterministic_strategy_id": deterministic_strategy,
                "reducer_status": reducer_status,
                "accepted_by_reducer": accepted,
                "strategy_match": is_match,
                "leakage_status": leakage_status,
                "provider_receipt_id": advisory.get("receipt_id"),
                "provider_advisory_confidence": advisory.get("confidence"),
            }
        )
    strategy_match_rate = (
        matches / comparable_count if comparable_count > 0 else None
    )
    return {
        "schema_version": "provider_strategy_match_comparison_v0",
        "matched_problem_manifest_digest": matched_problem_manifest_digest,
        "comparable_count": comparable_count,
        "match_count": matches,
        "strategy_match_rate": strategy_match_rate,
        "accepted_provider_count": accepted_provider_count,
        "rejected_provider_count": rejected_provider_count,
        "invalid_provider_strategy_count": invalid_provider_count,
        "missing_provider_strategy_count": missing_provider_count,
        "leakage_rejection_count": leakage_rejection_count,
        "provider_results_counted": False,
        "anti_cheat": (
            "Provider text is never counted as proof; strategy_match_rate measures "
            "whether the provider's classification matches the deterministic "
            "strategy_control selector on the same problem manifest. "
            "Search-efficiency deltas require running deterministic search with "
            "the provider advisory injected and are emitted by a separate wave."
        ),
        "rows": rows,
    }


def _validate_summary(summary: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if summary.get("provider_calls_by_reducer") != 0:
        issues.append("reducer must not call providers")
    if summary.get("harness_owned_provider_dispatch_added") is not False:
        issues.append("reducer must not add harness-owned provider dispatch")
    latest = summary.get("latest_reduction") if isinstance(summary.get("latest_reduction"), Mapping) else {}
    if not latest.get("lean_check_result"):
        issues.append("lean_check_result missing")
    if not latest.get("provider_oracle_attribution"):
        issues.append("provider_oracle_attribution missing")
    if not latest.get("foundry_learning_row"):
        issues.append("foundry_learning_row missing")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, help="Provider receipt JSON path.")
    parser.add_argument("--row-patch", help="Row patch JSON path. Auto-discovered by receipt_id when omitted.")
    parser.add_argument("--transform-job", required=True, help="Transform job JSON path.")
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--cap-id", default="cap_prover_provider_receipt_reducer_v0")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    summary = reduce_receipt(
        receipt_path=_repo_path(args.receipt),
        row_patch_path=_repo_path(args.row_patch) if args.row_patch else None,
        transform_job_path=_repo_path(args.transform_job),
        run_root=_repo_path(args.run_root),
        timeout_seconds=args.timeout_seconds,
        cap_id=args.cap_id,
    )
    issues = _validate_summary(summary)
    if args.check and issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        latest = summary.get("latest_reduction") if isinstance(summary.get("latest_reduction"), Mapping) else {}
        print(
            f"{summary['run_id']}: receipt={latest.get('receipt_id')} "
            f"lean={latest.get('accepted_by_lean')} error={latest.get('error_class')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
