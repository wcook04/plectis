"""
[PURPOSE]
- Teleology: Compile market_situation_graph_v0 into a backend-owned dashboard
  read model: trust strip, paginated situation queue, detail index, graph slice,
  facets, drilldowns, provenance, validation debt, display hints, and API
  contract metadata.
- Mechanism: Read the generated market situation graph sidecar as input and
  produce a stable consumption contract without introducing frontend layout or
  trading claims.
- Non-goal: This is not a second market graph, not a React/CSS component model,
  and not an investment recommendation endpoint.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib.market_situation_graph import (
    DEFAULT_LATEST_FILENAME as GRAPH_LATEST_FILENAME,
    DEFAULT_REPORT_ROOT,
    REPORT_FILENAME as GRAPH_REPORT_FILENAME,
    RUN_ARTIFACT_FILENAME as GRAPH_RUN_ARTIFACT_FILENAME,
    SCHEMA_VERSION as GRAPH_SCHEMA_VERSION,
    render_market_situation_graph,
)


SCHEMA_VERSION = "market_dashboard_read_model_v0"
RUN_ARTIFACT_FILENAME = "market_dashboard_read_model.json"
REPORT_FILENAME = "market_dashboard_read_model_v0.json"
DEFAULT_LATEST_FILENAME = "latest_market_dashboard_read_model.json"
FINANCE_ASSURANCE_BINDING_SCHEMA_VERSION = "finance_product_assurance_binding_v0"
FINANCE_ASSURANCE_SURFACE_PATH = Path(
    "microcosm-substrate/examples/finance_forecast_evaluation_spine/"
    "exported_finance_eval_bundle/finance_research_assurance_surface.json"
)
FINANCE_ASSURANCE_RECEIPT_PATH = Path(
    "microcosm-substrate/receipts/first_wave/finance_forecast_evaluation_spine/"
    "exported_finance_eval_bundle_validation_result.json"
)

DEFAULT_API_ROUTES: tuple[str, ...] = (
    "/api/market/intelligence/latest",
    "/api/market/intelligence/overview",
    "/api/market/intelligence/situations",
    "/api/market/intelligence/situations/{situation_id}",
    "/api/market/intelligence/graph",
    "/api/market/intelligence/drilldown/{source_ref_id}",
    "/api/market/intelligence/provenance",
    "/api/market/intelligence/validation-debt",
)

FRONTEND_LAYOUT_TOKENS: tuple[str, ...] = (
    "React",
    "className",
    "Tailwind",
    "CSS",
    "component",
)
TRADING_CLAIM_PATTERN = re.compile(
    r"\b(buy|sell|short|go long|price target|take profit|stop loss|strong buy|strong sell)\b",
    re.IGNORECASE,
)


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _bool_or_false(value: Any) -> bool:
    return value is True


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(row) for row in value if str(row).strip()]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _staleness_days(value: Any) -> int | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    now = datetime.now(timezone.utc)
    return max(0, (now.date() - parsed.date()).days)


def _source_ref(repo_root: Path, path: Path, *, kind: str, present: bool, status: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": kind,
        "path": _repo_rel(repo_root, repo_root / path),
        "present": present,
    }
    if status:
        row["status"] = status
    return row


def _stable_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(payload: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _render(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_market_dashboard_read_model(payload: Mapping[str, Any]) -> str:
    """Return the deterministic on-disk JSON rendering."""
    return _render(payload)


def _graph_fingerprint_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(payload)
    # Projection status is read-path freshness metadata added by loaders, not
    # part of the semantic graph identity.
    row.pop("projection_status", None)
    return row


def fingerprint_market_situation_graph(payload: Mapping[str, Any]) -> str:
    """Return the input-graph fingerprint used by the dashboard read model."""
    return _fingerprint(_graph_fingerprint_payload(payload))


def fingerprint_market_dashboard_read_model(payload: Mapping[str, Any]) -> str:
    """Return a stable fingerprint for the generated read model payload."""
    return _fingerprint(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_market_dashboard_read_model(payload), encoding="utf-8")


def _graph_path_for_run(
    repo_root: Path,
    run_id: str | None,
    report_root: Path = DEFAULT_REPORT_ROOT,
) -> Path:
    root = report_root if report_root.is_absolute() else repo_root / report_root
    if run_id:
        return root / run_id / GRAPH_REPORT_FILENAME
    return root / GRAPH_LATEST_FILENAME


def _canonical_graph_path_for_payload(
    repo_root: Path,
    payload: Mapping[str, Any],
    loaded_path: Path,
    report_root: Path = DEFAULT_REPORT_ROOT,
) -> Path:
    """Prefer the run-scoped graph path when the latest alias has identical content."""
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        return loaded_path
    run_path = _graph_path_for_run(repo_root, run_id, report_root=report_root)
    if run_path == loaded_path or not run_path.exists():
        return loaded_path
    if _read_json(run_path) == payload:
        return run_path
    return loaded_path


def _load_graph_input(
    repo_root: Path,
    *,
    run_id: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
) -> tuple[dict[str, Any], Path]:
    path = _graph_path_for_run(repo_root, run_id, report_root=report_root)
    payload = _read_json(path)
    if payload:
        if run_id is None:
            path = _canonical_graph_path_for_payload(
                repo_root,
                payload,
                path,
                report_root=report_root,
            )
        return payload, path
    if run_id:
        fallback = repo_root / "state" / "runs" / run_id / "artifacts" / GRAPH_RUN_ARTIFACT_FILENAME
        payload = _read_json(fallback)
        if payload:
            return payload, fallback
    return {}, path


def _finance_assurance_source_status(surface: Mapping[str, Any]) -> str:
    schema_version = str(surface.get("schema_version") or "")
    if not surface:
        return "missing"
    if schema_version != "finance_research_assurance_surface_v0":
        return "schema_mismatch"
    return "present"


def _feed_readiness_path(run_id: str) -> Path:
    return Path("state") / "runs" / run_id / "artifacts" / "feed_readiness_summary.json"


def _runtime_context_path(run_id: str) -> Path:
    return Path("state") / "runs" / run_id / "runtime_context.json"


def _runtime_feed_freshness_overlay(
    repo_root: Path,
    *,
    run_id: str | None,
    fallback: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not run_id:
        return None
    readiness_rel = _feed_readiness_path(run_id)
    readiness_path = repo_root / readiness_rel
    readiness = _read_json(readiness_path)
    if not readiness:
        return {
            "state": "blocked_missing_artifact",
            "latest_green_run_id": fallback.get("latest_green_run_id"),
            "latest_green_generated_at": fallback.get("latest_green_generated_at"),
            "staleness_days": fallback.get("staleness_days"),
            "scheduled_shell_count": fallback.get("scheduled_shell_count"),
            "truth_statement": (
                "The current market run is missing feed readiness artifacts; "
                "historical green proof cannot stand in for live-feed capability."
            ),
            "runtime_evidence": {
                "run_id": run_id,
                "feed_readiness_summary": _repo_rel(repo_root, readiness_path),
                "present": False,
            },
        }

    runtime_context = _read_json(repo_root / _runtime_context_path(run_id))
    status_counts = _mapping(readiness.get("status_counts"))
    success_count = _int_or_none(status_counts.get("success")) or 0
    target_count = _int_or_none(readiness.get("target_count")) or 0
    blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []
    generated_at = (
        readiness.get("generated_at")
        or runtime_context.get("as_of")
        or runtime_context.get("time_anchor")
    )
    staleness = _staleness_days(generated_at)
    ready = readiness.get("ready") is True
    all_targets_ready = target_count > 0 and success_count >= target_count
    runtime_evidence = {
        "run_id": run_id,
        "feed_readiness_summary": _repo_rel(repo_root, readiness_path),
        "present": True,
        "ready": ready,
        "target_count": target_count,
        "success_count": success_count,
        "blocker_count": len(blockers),
    }

    if ready and all_targets_ready and not blockers and staleness == 0:
        return {
            "state": "fresh_green_feed",
            "latest_green_run_id": run_id,
            "latest_green_generated_at": generated_at,
            "staleness_days": 0,
            "scheduled_shell_count": fallback.get("scheduled_shell_count"),
            "truth_statement": (
                "A fresh green feed is artifact-backed live-feed evidence, "
                "not financial advice or automatic Evolve authority."
            ),
            "runtime_evidence": runtime_evidence,
        }
    if not ready or blockers or (target_count and success_count < target_count):
        return {
            "state": "blocked_missing_artifact",
            "latest_green_run_id": fallback.get("latest_green_run_id"),
            "latest_green_generated_at": fallback.get("latest_green_generated_at"),
            "staleness_days": fallback.get("staleness_days"),
            "scheduled_shell_count": fallback.get("scheduled_shell_count"),
            "truth_statement": (
                "The current market run has feed blockers; historical green proof "
                "does not prove live-feed capability."
            ),
            "runtime_evidence": runtime_evidence,
        }
    return {
        "state": "stale_green_feed",
        "latest_green_run_id": run_id,
        "latest_green_generated_at": generated_at,
        "staleness_days": staleness,
        "scheduled_shell_count": fallback.get("scheduled_shell_count"),
        "truth_statement": (
            "The current green feed is artifact-backed but no longer same-day fresh."
        ),
        "runtime_evidence": runtime_evidence,
    }


def _build_finance_research_assurance_binding(repo_root: Path, *, run_id: str | None = None) -> dict[str, Any]:
    surface_path = repo_root / FINANCE_ASSURANCE_SURFACE_PATH
    receipt_path = repo_root / FINANCE_ASSURANCE_RECEIPT_PATH
    surface = _read_json(surface_path)
    receipt = _read_json(receipt_path)
    source_status = _finance_assurance_source_status(surface)
    receipt_status = str(receipt.get("status") or receipt.get("validation_status") or "").strip()
    receipt_finance = _mapping(receipt.get("finance_research_assurance"))

    coverage = _mapping(surface.get("module_coverage"))
    feed = _mapping(surface.get("feed_freshness"))
    latest_green = _mapping(feed.get("latest_green_run"))
    scheduled_shells = feed.get("scheduled_shells") if isinstance(feed.get("scheduled_shells"), list) else []
    demo = _mapping(surface.get("demonstration_run"))
    demo_counts = _mapping(demo.get("substantive_counts"))
    statistical = _mapping(surface.get("statistical_discipline"))
    oracle = _mapping(surface.get("oracle_evolve"))
    evolve_decision = _mapping(oracle.get("evolve_decision"))
    boundary = _mapping(surface.get("authority_boundary"))
    ui_receipts = _mapping(surface.get("ui_receipts"))
    quant = _mapping(surface.get("quant_research_experiment_spine"))
    quant_hypothesis = _mapping(quant.get("hypothesis_ledger"))
    quant_anti_overfit = _mapping(quant.get("anti_overfit_evaluator"))
    quant_comparison = _mapping(quant.get("model_comparison_discipline"))
    quant_bridge = _mapping(quant.get("oracle_evolve_bridge"))
    quant_no_advice = _mapping(quant.get("no_advice_mode"))
    quant_lineage = _mapping(quant.get("lineage_summary"))
    quant_agenda = _mapping(quant.get("research_agenda"))
    quant_agenda_budget = _mapping(quant_agenda.get("search_budget"))
    quant_agenda_policy = _mapping(quant_agenda.get("selection_policy"))
    quant_cycle = _mapping(quant.get("agenda_execution_cycle"))
    quant_cycle_plan = _mapping(quant_cycle.get("pre_analysis_plan"))
    quant_cycle_execution = _mapping(quant_cycle.get("execution"))
    quant_cycle_registry_update = _mapping(quant_cycle.get("registry_update"))
    quant_cycle_family_update = _mapping(quant_cycle.get("family_memory_update"))
    quant_cycle_recompile = _mapping(quant_cycle.get("agenda_recompile"))
    quant_cycle_bridge = _mapping(quant_cycle.get("oracle_evolve_implication"))
    quant_cycle_no_advice = _mapping(quant_cycle.get("no_advice_mode"))
    quant_registry = [
        row for row in quant.get("experiment_registry", []) if isinstance(row, Mapping)
    ]
    quant_agenda_candidates = [
        row for row in quant_agenda.get("candidate_agenda", []) if isinstance(row, Mapping)
    ]

    sequence = _string_list(statistical.get("sequence"))
    auto_apply_allowed = evolve_decision.get("auto_apply_allowed")
    if auto_apply_allowed is None:
        auto_apply_allowed = receipt_finance.get("evolve_auto_apply_allowed")
    review_gated = evolve_decision.get("review_gated")
    if review_gated is None:
        review_gated = receipt_finance.get("evolve_review_gated")
    authority_overclaim_count = _int_or_none(
        receipt_finance.get("authority_overclaim_count")
        if receipt_finance
        else boundary.get("authority_overclaim_count")
    )

    current_state = str(feed.get("current_state") or "blocked_missing_artifact")
    silent_omission_count = _int_or_none(coverage.get("silent_omission_count")) or 0
    base_freshness = {
        "state": current_state,
        "latest_green_run_id": latest_green.get("run_id"),
        "latest_green_generated_at": latest_green.get("generated_at"),
        "staleness_days": _int_or_none(latest_green.get("staleness_days")),
        "scheduled_shell_count": len(scheduled_shells),
        "truth_statement": feed.get("truth_statement"),
    }
    runtime_freshness = _runtime_feed_freshness_overlay(
        repo_root,
        run_id=run_id,
        fallback=base_freshness,
    )
    feed_freshness = runtime_freshness or base_freshness
    source_refs = [
        _source_ref(repo_root, FINANCE_ASSURANCE_SURFACE_PATH, kind="assurance_surface", present=bool(surface)),
        _source_ref(
            repo_root,
            FINANCE_ASSURANCE_RECEIPT_PATH,
            kind="validation_receipt",
            present=bool(receipt),
            status=receipt_status or None,
        ),
    ]
    if run_id:
        readiness_path = _feed_readiness_path(run_id)
        source_refs.append(
            _source_ref(
                repo_root,
                readiness_path,
                kind="runtime_feed_readiness",
                present=(repo_root / readiness_path).exists(),
                status=feed_freshness.get("state"),
            )
        )
    return {
        "schema_version": FINANCE_ASSURANCE_BINDING_SCHEMA_VERSION,
        "source_status": source_status,
        "surface_schema_version": surface.get("schema_version"),
        "surface_id": surface.get("surface_id"),
        "source_refs": source_refs,
        "module_coverage": {
            "coverage_policy": coverage.get("coverage_policy"),
            "macro_finance_module_count": _int_or_none(coverage.get("macro_finance_module_count")) or 0,
            "imported_public_body_count": _int_or_none(coverage.get("imported_public_body_count")) or 0,
            "operational_receipt_only_count": _int_or_none(
                coverage.get("operational_receipt_only_count")
            )
            or 0,
            "silent_omission_count": silent_omission_count,
            "status": (
                "complete_classification_no_silent_omissions"
                if source_status == "present" and silent_omission_count == 0
                else source_status
            ),
        },
        "feed_freshness": feed_freshness,
        "evidence_maturity": {
            "public_safe_non_empty_fixture": _bool_or_false(
                demo.get("public_safe_non_empty_fixture")
            ),
            "target_universe_count": _int_or_none(demo_counts.get("target_universe_count")) or 0,
            "evidence_construction_path_count": _int_or_none(
                demo_counts.get("evidence_construction_path_count")
            )
            or 0,
            "scoring_rule_count": _int_or_none(demo_counts.get("scoring_rule_count")) or 0,
            "pairwise_comparison_count": _int_or_none(
                demo_counts.get("pairwise_comparison_count")
            )
            or 0,
            "multiple_comparison_guard_count": _int_or_none(
                demo_counts.get("multiple_comparison_guard_count")
            )
            or 0,
            "oracle_reconciliation_count": _int_or_none(
                demo_counts.get("oracle_reconciliation_count")
            )
            or 0,
            "evolve_decision_count": _int_or_none(demo_counts.get("evolve_decision_count")) or 0,
        },
        "forecast_comparison": {
            "sequence": sequence,
            "scoring_first": "proper_scoring_rules" in sequence,
            "pairwise_equal_loss_present": "pairwise_equal_loss" in sequence,
            "multiple_comparison_guard_present": "multiple_comparison_guard" in sequence,
            "interpretation": "scoring, equal-loss evidence, multiple-comparison guard, review gate",
        },
        "oracle_evolve": {
            "decision": evolve_decision.get("decision") or "hold_for_review",
            "review_gated": review_gated is not False,
            "auto_apply_allowed": auto_apply_allowed is True,
            "oracle_reconciliation_artifact": oracle.get("oracle_reconciliation_artifact"),
            "implication_path": [
                "evidence_observed",
                "forecast_scored",
                "oracle_reconciled",
                "review_gate",
                "no_auto_apply",
            ],
        },
        "quant_research_experiment": {
            "schema_version": quant.get("schema_version"),
            "status": quant.get("status") or "missing",
            "experiment_id": quant_hypothesis.get("experiment_id"),
            "hypothesis_type": quant_hypothesis.get("hypothesis_type"),
            "public_safe_hypothesis": quant_hypothesis.get("public_safe_hypothesis"),
            "target_universe": quant_hypothesis.get("target_universe"),
            "split_policy": quant_anti_overfit.get("split_policy"),
            "anti_overfit_status": quant_anti_overfit.get("status"),
            "selection_bias_guard": quant_anti_overfit.get("selection_bias_guard"),
            "effective_sample_deficit": _int_or_none(
                quant_anti_overfit.get("effective_sample_deficit")
            )
            or 0,
            "model_comparison_output_state": quant_comparison.get("output_state"),
            "model_confidence_set_status": quant_comparison.get("model_confidence_set_status"),
            "winner_language_allowed": quant_comparison.get("winner_language_allowed") is True,
            "review_gated": quant_bridge.get("review_gated") is True,
            "auto_apply_allowed": quant_bridge.get("auto_apply_allowed") is True,
            "no_advice_enabled": quant_no_advice.get("enabled") is True,
            "receipt_markers": _string_list(
                _mapping(quant.get("operator_research_receipt")).get("required_markers")
            ),
            "lineage_status": quant_lineage.get("lineage_status"),
            "registry_count": _int_or_none(quant_lineage.get("registry_count"))
            or len(quant_registry),
            "minimum_registry_count": _int_or_none(
                quant_lineage.get("minimum_registry_count")
            )
            or 2,
            "negative_control_count": _int_or_none(
                quant_lineage.get("negative_control_count")
            )
            or sum(
                1
                for row in quant_registry
                if str(row.get("stress_role") or "").startswith("negative_control")
            ),
            "negative_or_insufficient_count": _int_or_none(
                quant_lineage.get("negative_or_insufficient_count")
            )
            or 0,
            "output_state_counts": _mapping(quant_lineage.get("output_state_counts")),
            "agenda_status": quant_agenda.get("status"),
            "agenda_candidate_count": _int_or_none(quant_agenda_budget.get("candidate_count"))
            or len(quant_agenda_candidates),
            "agenda_family_count": _int_or_none(quant_agenda_budget.get("family_count")) or 0,
            "agenda_selected_for_next_test_count": _int_or_none(
                quant_agenda_budget.get("selected_for_next_test_count")
            )
            or 0,
            "agenda_deferred_data_snooping_count": _int_or_none(
                quant_agenda_budget.get("deferred_data_snooping_count")
            )
            or 0,
            "agenda_negative_or_control_candidate_count": _int_or_none(
                quant_agenda_budget.get("negative_or_control_candidate_count")
            )
            or 0,
            "agenda_needs_more_evidence_count": _int_or_none(
                quant_agenda_budget.get("needs_more_evidence_count")
            )
            or 0,
            "agenda_completed_insufficient_evidence_count": _int_or_none(
                quant_agenda_budget.get("completed_insufficient_evidence_count")
            )
            or 0,
            "cycle_status": quant_cycle_execution.get("status"),
            "cycle_selected_candidate_id": quant_cycle.get("selected_candidate_id"),
            "cycle_result_state": quant_cycle_execution.get("result_state"),
            "cycle_pre_analysis_plan_id": quant_cycle_plan.get("plan_id"),
            "cycle_registered_before_execution": quant_cycle_plan.get(
                "registered_before_execution"
            )
            is True,
            "cycle_new_registry_count": _int_or_none(
                quant_cycle_registry_update.get("new_registry_count")
            )
            or 0,
            "cycle_next_selected_candidate_id": quant_cycle_recompile.get(
                "next_selected_candidate_id"
            ),
        },
        "quant_research_lineage": {
            "schema_version": quant_lineage.get("schema_version"),
            "lineage_status": quant_lineage.get("lineage_status"),
            "registry_count": _int_or_none(quant_lineage.get("registry_count"))
            or len(quant_registry),
            "minimum_registry_count": _int_or_none(
                quant_lineage.get("minimum_registry_count")
            )
            or 2,
            "negative_control_count": _int_or_none(
                quant_lineage.get("negative_control_count")
            )
            or sum(
                1
                for row in quant_registry
                if str(row.get("stress_role") or "").startswith("negative_control")
            ),
            "negative_or_insufficient_count": _int_or_none(
                quant_lineage.get("negative_or_insufficient_count")
            )
            or 0,
            "output_state_counts": _mapping(quant_lineage.get("output_state_counts")),
            "registry_preview": [
                {
                    "experiment_id": row.get("experiment_id"),
                    "stress_role": row.get("stress_role"),
                    "hypothesis_type": row.get("hypothesis_type"),
                    "output_state": _mapping(row.get("model_comparison")).get("output_state"),
                    "review_gated": _mapping(row.get("oracle_evolve_implication")).get(
                        "review_gated"
                    )
                    is True,
                    "auto_apply_allowed": _mapping(
                        row.get("oracle_evolve_implication")
                    ).get("auto_apply_allowed")
                    is True,
                    "no_advice_enabled": _mapping(row.get("no_advice_mode")).get(
                        "enabled"
                    )
                    is True,
                    "winner_language_allowed": _mapping(row.get("model_comparison")).get(
                        "winner_language_allowed"
                    )
                    is True,
                }
                for row in quant_registry[:4]
            ],
        },
        "quant_research_agenda": {
            "schema_version": quant_agenda.get("schema_version"),
            "agenda_id": quant_agenda.get("agenda_id"),
            "status": quant_agenda.get("status"),
            "candidate_count": _int_or_none(quant_agenda_budget.get("candidate_count"))
            or len(quant_agenda_candidates),
            "family_count": _int_or_none(quant_agenda_budget.get("family_count")) or 0,
            "selected_for_next_test_count": _int_or_none(
                quant_agenda_budget.get("selected_for_next_test_count")
            )
            or 0,
            "deferred_data_snooping_count": _int_or_none(
                quant_agenda_budget.get("deferred_data_snooping_count")
            )
            or 0,
            "negative_or_control_candidate_count": _int_or_none(
                quant_agenda_budget.get("negative_or_control_candidate_count")
            )
            or 0,
            "needs_more_evidence_count": _int_or_none(
                quant_agenda_budget.get("needs_more_evidence_count")
            )
            or 0,
            "data_snooping_guard_active": quant_agenda_budget.get(
                "data_snooping_guard_active"
            )
            is True,
            "budget_pressure": quant_agenda_budget.get("budget_pressure"),
            "performance_metric_optimization_allowed": quant_agenda_policy.get(
                "performance_metric_optimization_allowed"
            )
            is True,
            "winner_language_allowed": quant_agenda_policy.get("winner_language_allowed")
            is True,
            "candidate_preview": [
                {
                    "candidate_id": row.get("candidate_id"),
                    "rank": _int_or_none(row.get("rank")),
                    "family_id": row.get("family_id"),
                    "agenda_state": row.get("agenda_state"),
                    "selection_reason": row.get("selection_reason"),
                    "expected_failure_mode": row.get("expected_failure_mode"),
                    "data_snooping_risk": row.get("data_snooping_risk"),
                    "review_gated": row.get("review_gated") is True,
                    "auto_apply_allowed": row.get("auto_apply_allowed") is True,
                    "no_advice_enabled": row.get("no_advice_enabled") is True,
                    "winner_language_allowed": row.get("winner_language_allowed") is True,
                }
                for row in quant_agenda_candidates[:5]
            ],
            "family_memory_preview": [
                {
                    "family_id": row.get("family_id"),
                    "memory_state": row.get("memory_state"),
                    "program_implication": row.get("program_implication"),
                }
                for row in _as_list(quant_agenda.get("family_memory"))[:5]
                if isinstance(row, Mapping)
            ],
        },
        "quant_research_cycle": {
            "schema_version": quant_cycle.get("schema_version"),
            "cycle_id": quant_cycle.get("cycle_id"),
            "source_agenda_id": quant_cycle.get("source_agenda_id"),
            "selected_candidate_id": quant_cycle.get("selected_candidate_id"),
            "pre_analysis_plan_id": quant_cycle_plan.get("plan_id"),
            "registered_before_execution": quant_cycle_plan.get(
                "registered_before_execution"
            )
            is True,
            "analysis_plan_locked": quant_cycle_plan.get("analysis_plan_locked") is True,
            "post_hoc_plan_mutation_allowed": quant_cycle_plan.get(
                "post_hoc_plan_mutation_allowed"
            )
            is True,
            "execution_status": quant_cycle_execution.get("status"),
            "used_existing_evaluator": quant_cycle_execution.get(
                "used_existing_evaluator"
            )
            is True,
            "result_state": quant_cycle_execution.get("result_state"),
            "winner_language_allowed": quant_cycle_execution.get(
                "winner_language_allowed"
            )
            is True,
            "appended_experiment_id": quant_cycle_registry_update.get(
                "appended_experiment_id"
            ),
            "previous_registry_count": _int_or_none(
                quant_cycle_registry_update.get("previous_registry_count")
            )
            or 0,
            "new_registry_count": _int_or_none(
                quant_cycle_registry_update.get("new_registry_count")
            )
            or 0,
            "family_memory_family_id": quant_cycle_family_update.get("family_id"),
            "family_memory_state": quant_cycle_family_update.get("new_memory_state"),
            "agenda_recompile_status": quant_cycle_recompile.get("status"),
            "next_selected_candidate_id": quant_cycle_recompile.get(
                "next_selected_candidate_id"
            ),
            "review_gated": quant_cycle_bridge.get("review_gated") is True,
            "auto_apply_allowed": quant_cycle_bridge.get("auto_apply_allowed") is True,
            "no_advice_enabled": quant_cycle_no_advice.get("enabled") is True,
        },
        "no_advice_mode": {
            "enabled": True,
            "non_advisory_research_only": True,
            "authority_overclaim_count": authority_overclaim_count or 0,
            "prohibited_output_classes": [
                "trading_action_labels",
                "personalized_account_action",
                "portfolio_allocation",
                "performance_guarantee",
                "automatic_execution",
            ],
        },
        "consumer_markers": _string_list(ui_receipts.get("required_markers"))
        or [
            "feed_freshness_state",
            "evidence_maturity",
            "statistical_comparison_status",
            "evolve_permission_state",
            "no_advice_mode",
        ],
        "target_consumers": ["financeData", "marketIntelligence", "labOracleEvolve"],
    }


def _safe_use_level(situation: Mapping[str, Any]) -> str:
    display = situation.get("display_contract") if isinstance(situation.get("display_contract"), Mapping) else {}
    return str(display.get("safe_use_level") or "artifact_specimen_only")


def _validation_state(situation: Mapping[str, Any]) -> str:
    validation = situation.get("validation") if isinstance(situation.get("validation"), Mapping) else {}
    return str(validation.get("state") or "unknown")


def _display_state(situation: Mapping[str, Any]) -> str:
    display = situation.get("display_contract") if isinstance(situation.get("display_contract"), Mapping) else {}
    return str(display.get("display_state") or "degraded")


def _confidence_overall(situation: Mapping[str, Any]) -> float | None:
    confidence = situation.get("confidence") if isinstance(situation.get("confidence"), Mapping) else {}
    value = confidence.get("overall")
    if isinstance(value, bool) or value is None:
        return None
    try:
        return round(float(value), 3)
    except Exception:
        return None


def _source_ref_id(ref: Mapping[str, Any]) -> str:
    return "src_" + hashlib.sha1(_stable_json(ref).encode("utf-8")).hexdigest()[:12]


def _edge_lookup(graph: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for edge in graph.get("edges") or []:
        if not isinstance(edge, Mapping):
            continue
        edge_id = str(edge.get("edge_id") or "").strip()
        if edge_id:
            rows[edge_id] = edge
    return rows


def _entity_lookup(graph: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for entity in graph.get("entities") or []:
        if not isinstance(entity, Mapping):
            continue
        entity_id = str(entity.get("entity_id") or "").strip()
        if entity_id:
            rows[entity_id] = entity
    return rows


def _make_badges(situation: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"kind": "situation_type", "value": situation.get("situation_type")},
        {"kind": "horizon", "value": situation.get("horizon")},
        {"kind": "claim_level", "value": situation.get("claim_level")},
        {"kind": "validation_state", "value": _validation_state(situation)},
        {"kind": "display_state", "value": _display_state(situation)},
    ]


def _situation_card(situation: Mapping[str, Any]) -> dict[str, Any]:
    entities = [str(entity) for entity in situation.get("entities") or [] if str(entity).strip()]
    return {
        "situation_id": situation.get("situation_id"),
        "rank": int(situation.get("rank") or 999),
        "title": situation.get("title"),
        "situation_type": situation.get("situation_type"),
        "horizon": situation.get("horizon"),
        "claim_level": situation.get("claim_level"),
        "validation_state": _validation_state(situation),
        "display_state": _display_state(situation),
        "confidence_overall": _confidence_overall(situation),
        "primary_entities": entities[:4],
        "evidence_count": len(situation.get("evidence_edges") or []),
        "counterevidence_count": len(situation.get("counterevidence_edges") or []),
        "badges": _make_badges(situation),
        "detail_ref": f"detail:{situation.get('situation_id')}",
        "safe_use_level": _safe_use_level(situation),
    }


def _page_connection(items: Sequence[Mapping[str, Any]], *, limit: int = 50) -> dict[str, Any]:
    clipped = list(items[: max(0, limit)])
    has_next = len(items) > len(clipped)
    end_cursor = str(len(clipped)) if has_next else None
    return {
        "items": [dict(item) for item in clipped],
        "page_info": {
            "has_next_page": has_next,
            "end_cursor": end_cursor,
        },
        "total_count": len(items),
    }


def _situation_queue(situations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cards = [_situation_card(situation) for situation in situations]
    cards.sort(key=lambda row: (int(row.get("rank") or 999), str(row.get("situation_id") or "")))
    return _page_connection(cards, limit=50) | {
        "default_sort": "rank asc",
        "supported_filters": [
            "type",
            "horizon",
            "claim_level",
            "validation_state",
            "display_state",
            "entity",
            "provider",
        ],
    }


def _related_situations(
    situation: Mapping[str, Any],
    situations: Sequence[Mapping[str, Any]],
) -> list[str]:
    sid = str(situation.get("situation_id") or "")
    entities = {str(entity) for entity in situation.get("entities") or [] if str(entity)}
    related: list[tuple[int, str]] = []
    for other in situations:
        other_id = str(other.get("situation_id") or "")
        if not other_id or other_id == sid:
            continue
        overlap = entities & {str(entity) for entity in other.get("entities") or [] if str(entity)}
        type_match = other.get("situation_type") == situation.get("situation_type")
        if overlap or type_match:
            related.append((int(other.get("rank") or 999), other_id))
    related.sort()
    return [row[1] for row in related[:6]]


def _detail_index(situations: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for situation in situations:
        sid = str(situation.get("situation_id") or "").strip()
        if not sid:
            continue
        index[sid] = {
            "card": _situation_card(situation),
            "thesis": dict(situation.get("thesis") or {}),
            "evidence_edges": [dict(row) for row in situation.get("evidence_edges") or []],
            "counterevidence_edges": [dict(row) for row in situation.get("counterevidence_edges") or []],
            "risk_context": dict(situation.get("risk_context") or {}),
            "regime_context": dict(situation.get("regime_context") or {}),
            "validation": dict(situation.get("validation") or {}),
            "drilldown": dict(situation.get("drilldown") or {}),
            "related_situations": _related_situations(situation, situations),
            "source_refs": [dict(row) for row in situation.get("source_refs") or [] if isinstance(row, Mapping)],
        }
    return index


def _source_ref_nodes(source_refs: Mapping[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for source_ref_id, source_ref in sorted(source_refs.items()):
        if not isinstance(source_ref, Mapping):
            continue
        table_path = source_ref.get("table_path")
        label = str(table_path or source_ref.get("feed_id") or source_ref.get("kind") or source_ref_id)
        nodes.append(
            {
                "node_id": source_ref_id,
                "node_type": "source_ref",
                "label": label,
                "badges": [{"kind": "source_kind", "value": source_ref.get("kind")}],
                "detail_ref": f"source_ref:{source_ref_id}",
            }
        )
    return nodes


def _graph_slice(
    *,
    graph: Mapping[str, Any],
    situations: Sequence[Mapping[str, Any]],
    drilldown_index: Mapping[str, Any],
) -> dict[str, Any]:
    entities = _entity_lookup(graph)
    source_refs = drilldown_index.get("source_refs") if isinstance(drilldown_index.get("source_refs"), Mapping) else {}
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for situation in situations:
        sid = str(situation.get("situation_id") or "").strip()
        if not sid:
            continue
        nodes[sid] = {
            "node_id": sid,
            "node_type": "situation",
            "label": situation.get("title") or sid,
            "badges": _make_badges(situation),
            "detail_ref": f"detail:{sid}",
        }
        for entity_id in situation.get("entities") or []:
            entity_id = str(entity_id or "").strip()
            if not entity_id:
                continue
            entity = entities.get(entity_id) or {}
            nodes.setdefault(
                entity_id,
                {
                    "node_id": entity_id,
                    "node_type": str(entity.get("entity_type") or entity_id.split(":", 1)[0] or "entity"),
                    "label": entity.get("display_name") or entity_id,
                    "badges": [{"kind": "entity_type", "value": entity.get("entity_type") or "entity"}],
                    "detail_ref": f"entity:{entity_id}",
                },
            )
            edges.append(
                {
                    "edge_id": f"rel_{sid}_{entity_id}",
                    "source": sid,
                    "target": entity_id,
                    "edge_type": "relates_to",
                    "reason_code": "SITUATION_ENTITY_MEMBER",
                    "weight": 0.5,
                    "severity": "info",
                }
            )
    for source_node in _source_ref_nodes(source_refs):
        nodes[source_node["node_id"]] = source_node
    for edge in graph.get("edges") or []:
        if not isinstance(edge, Mapping):
            continue
        source = str(edge.get("situation_id") or "").strip()
        target = str(edge.get("target_entity_id") or edge.get("source_ref_id") or "").strip()
        if not source or not target:
            continue
        if source not in nodes:
            continue
        if target not in nodes and target in source_refs:
            nodes[target] = _source_ref_nodes({target: source_refs[target]})[0]
        if target not in nodes:
            continue
        edges.append(
            {
                "edge_id": edge.get("edge_id"),
                "source": source,
                "target": target,
                "edge_type": edge.get("edge_type"),
                "reason_code": edge.get("reason_code"),
                "weight": edge.get("weight"),
                "severity": edge.get("severity") or "info",
            }
        )
    return {
        "nodes": sorted(nodes.values(), key=lambda row: str(row.get("node_id") or "")),
        "edges": sorted(edges, key=lambda row: str(row.get("edge_id") or "")),
    }


def _facet(values: Iterable[Any]) -> list[dict[str, Any]]:
    counts = Counter(str(value) for value in values if value not in (None, ""))
    return [{"value": value, "count": count} for value, count in sorted(counts.items())]


def _facets(
    *,
    graph: Mapping[str, Any],
    situations: Sequence[Mapping[str, Any]],
    source_refs: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    entities = _entity_lookup(graph)
    return {
        "situation_type": _facet(situation.get("situation_type") for situation in situations),
        "horizon": _facet(situation.get("horizon") for situation in situations),
        "claim_level": _facet(situation.get("claim_level") for situation in situations),
        "validation_state": _facet(_validation_state(situation) for situation in situations),
        "display_state": _facet(_display_state(situation) for situation in situations),
        "entity_type": _facet(entity.get("entity_type") for entity in entities.values()),
        "provider": _facet(
            (ref.get("feed_id") or ref.get("provider_id") or ref.get("kind"))
            for ref in source_refs.values()
            if isinstance(ref, Mapping)
        ),
        "severity": _facet(
            edge.get("severity") or "info"
            for situation in situations
            for edge in list(situation.get("evidence_edges") or [])
            + list(situation.get("counterevidence_edges") or [])
            if isinstance(edge, Mapping)
        ),
    }


def _decorate_source_ref(source_ref_id: str, ref: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(ref)
    row["source_ref_id"] = source_ref_id
    row["route_ref"] = f"/api/market/intelligence/drilldown/{source_ref_id}"
    row["arbitrary_file_read_allowed"] = False
    return row


def _drilldown_index(graph: Mapping[str, Any], situations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    graph_drilldown = graph.get("drilldown_index") if isinstance(graph.get("drilldown_index"), Mapping) else {}
    source_refs = graph_drilldown.get("source_refs") if isinstance(graph_drilldown.get("source_refs"), Mapping) else {}
    decorated_refs = {
        str(source_ref_id): _decorate_source_ref(str(source_ref_id), ref)
        for source_ref_id, ref in source_refs.items()
        if isinstance(ref, Mapping)
    }
    return {
        "source_refs": decorated_refs,
        "source_rows": {
            source_ref_id: {
                "row_selector": ref.get("row_selector"),
                "table_path": ref.get("table_path"),
                "field_refs": ref.get("field_refs") or [],
            }
            for source_ref_id, ref in decorated_refs.items()
        },
        "mart_observation_refs": {
            str(situation.get("situation_id")): list((situation.get("drilldown") or {}).get("mart_observation_ids") or [])
            for situation in situations
            if str(situation.get("situation_id") or "").strip()
        },
        "graph_edge_refs": _edge_lookup(graph),
        "run_artifact_refs": {
            "input_graph": graph_drilldown.get("input_mart"),
            "input_mart_fingerprint": graph_drilldown.get("input_mart_fingerprint"),
        },
    }


def _provenance_index(
    *,
    repo_root: Path,
    graph: Mapping[str, Any],
    graph_path: Path,
    input_graph_fingerprint: str,
) -> dict[str, Any]:
    run_id = str(graph.get("run_id") or "")
    return {
        "prov_shape": "entity_activity_agent_derivation",
        "entities": [
            {
                "entity_id": "input_market_situation_graph",
                "kind": "generated_entity",
                "schema_version": graph.get("schema_version"),
                "path": _repo_rel(repo_root, graph_path),
                "fingerprint": input_graph_fingerprint,
            },
            {
                "entity_id": "market_dashboard_read_model",
                "kind": "generated_entity",
                "schema_version": SCHEMA_VERSION,
                "path": f"state/reports/market_feeds/{run_id}/{REPORT_FILENAME}" if run_id else None,
            },
        ],
        "activities": [
            {
                "activity_id": "build_market_dashboard_read_model",
                "kind": "projection_compile",
                "used": ["input_market_situation_graph"],
                "generated": ["market_dashboard_read_model"],
            }
        ],
        "agents": [
            {
                "agent_id": "market_dashboard_read_model_builder",
                "kind": "software_builder",
                "path": "system/lib/market_dashboard_read_model.py",
            },
            {
                "agent_id": "market_dashboard_read_model_cli",
                "kind": "builder_cli",
                "path": "tools/meta/factory/build_market_dashboard_read_model.py",
            },
        ],
        "derivations": [
            {
                "generated_entity": "market_dashboard_read_model",
                "was_derived_from": "input_market_situation_graph",
                "was_generated_by": "build_market_dashboard_read_model",
                "was_attributed_to": "market_dashboard_read_model_builder",
            }
        ],
    }


def _validation_debt(situations: Sequence[Mapping[str, Any]], graph: Mapping[str, Any]) -> dict[str, Any]:
    summary = graph.get("validation_summary") if isinstance(graph.get("validation_summary"), Mapping) else {}
    blocked: list[dict[str, Any]] = []
    for situation in situations:
        validation = situation.get("validation") if isinstance(situation.get("validation"), Mapping) else {}
        needed: list[str] = []
        if validation.get("requires_backtest") is True:
            needed.append("historical sample")
            needed.append("backtest")
        if validation.get("requires_event_study") is True:
            needed.append("event study")
        risk_context = situation.get("risk_context") if isinstance(situation.get("risk_context"), Mapping) else {}
        if risk_context.get("factor_context_status") in {"partial", "insufficient_data"}:
            needed.append("factor model")
        if needed:
            blocked.append(
                {
                    "situation_id": situation.get("situation_id"),
                    "current_state": validation.get("state"),
                    "claim_level": situation.get("claim_level"),
                    "needed_for_promotion": sorted(set(needed)),
                }
            )
    return {
        "validated_signal_count": int(summary.get("validated_signal_count") or 0),
        "requires_backtest_count": int(summary.get("requires_backtest_count") or 0),
        "requires_event_study_count": int(summary.get("requires_event_study_count") or 0),
        "blocked_promotions": blocked,
        "validation_posture": summary.get("validation_posture"),
    }


def _display_hints() -> dict[str, dict[str, Any]]:
    return {
        "overview": {
            "intent": "trust_strip",
            "recommended_visual": "status_cards",
            "required_fields": ["run_id", "graph_status", "situation_count", "validated_signal_count"],
        },
        "situation_queue": {
            "intent": "ranked_investigation_queue",
            "recommended_visual": "ranked_table",
            "required_fields": ["situation_id", "rank", "title", "claim_level", "validation_state"],
        },
        "graph_slice": {
            "intent": "evidence_network",
            "recommended_visual": "node_edge_graph",
            "required_fields": ["nodes", "edges"],
        },
        "validation_debt": {
            "intent": "claim_boundary_panel",
            "recommended_visual": "summary_plus_table",
            "required_fields": ["validated_signal_count", "blocked_promotions"],
        },
        "finance_research_assurance": {
            "intent": "operator_visible_finance_proof",
            "recommended_visual": "compact_proof_strip",
            "required_fields": [
                "feed_freshness.state",
                "module_coverage.silent_omission_count",
                "forecast_comparison.sequence",
                "oracle_evolve.review_gated",
                "no_advice_mode.enabled",
            ],
        },
    }


def _api_contract() -> dict[str, Any]:
    return {
        "contract_version": "market_intelligence_api_v0",
        "read_model_schema_version": SCHEMA_VERSION,
        "route_family": "/api/market/intelligence",
        "routes": [
            {"method": "GET", "path": route}
            for route in DEFAULT_API_ROUTES
        ],
        "filters": {
            "situations": [
                "type",
                "horizon",
                "claim_level",
                "validation_state",
                "display_state",
                "entity",
                "provider",
                "limit",
                "cursor",
            ],
            "graph": ["situation_id", "depth", "include_source_refs", "limit"],
        },
        "pagination": {
            "style": "cursor_connection_like",
            "cursor_semantics": "offset_cursor_over_ranked_situation_cards",
            "page_info_required": True,
        },
        "drilldown_policy": {
            "arbitrary_filesystem_read": False,
            "source_refs_return_metadata_only": True,
        },
        "stale_behavior": "return_structured_projection_status_not_500",
    }


def _overview(
    *,
    graph: Mapping[str, Any],
    input_graph_fingerprint: str,
    situations: Sequence[Mapping[str, Any]],
    graph_status: str,
) -> dict[str, Any]:
    claim_counts = Counter(str(situation.get("claim_level") or "unknown") for situation in situations)
    validation_counts = Counter(_validation_state(situation) for situation in situations)
    display_states = Counter(_display_state(situation) for situation in situations)
    validation_summary = graph.get("validation_summary") if isinstance(graph.get("validation_summary"), Mapping) else {}
    blocking = []
    for situation in situations:
        for edge in situation.get("counterevidence_edges") or []:
            if isinstance(edge, Mapping) and edge.get("severity") == "block":
                blocking.append({"situation_id": situation.get("situation_id"), "reason_code": edge.get("reason_code")})
    safe_use_level = _safe_use_level(situations[0]) if situations else "artifact_specimen_only"
    return {
        "run_id": graph.get("run_id"),
        "safe_use_level": safe_use_level,
        "graph_status": graph_status,
        "situation_count": len(situations),
        "edge_count": len(graph.get("edges") or []),
        "validated_signal_count": int(validation_summary.get("validated_signal_count") or 0),
        "claim_level_counts": dict(sorted(claim_counts.items())),
        "validation_state_counts": dict(sorted(validation_counts.items())),
        "display_state_counts": dict(sorted(display_states.items())),
        "top_situation_ids": [situation.get("situation_id") for situation in situations[:5]],
        "blocking_warnings": blocking,
        "freshness": {
            "input_watermark": graph.get("input_watermark"),
            "source_fingerprint": input_graph_fingerprint,
            "generated_projection_status": "in_sync",
        },
    }


def build_market_dashboard_read_model(
    repo_root: Path,
    *,
    run_id: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    graph_payload: Mapping[str, Any] | None = None,
    graph_path: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    if graph_payload is None:
        loaded, loaded_path = _load_graph_input(repo_root, run_id=run_id, report_root=report_root)
        graph_payload = loaded
        graph_path = loaded_path
    graph = dict(graph_payload or {})
    if not graph:
        return _unavailable_read_model(
            run_id=run_id,
            status="market_dashboard_read_model_input_missing",
            reason="market_situation_graph_input_missing",
            path=graph_path or _graph_path_for_run(repo_root, run_id, report_root=report_root),
        )
    if graph.get("schema_version") != GRAPH_SCHEMA_VERSION:
        return _unavailable_read_model(
            run_id=run_id or str(graph.get("run_id") or ""),
            status="market_dashboard_read_model_input_schema_mismatch",
            reason=f"expected {GRAPH_SCHEMA_VERSION}, got {graph.get('schema_version')}",
            path=graph_path or _graph_path_for_run(repo_root, run_id, report_root=report_root),
        )
    run_id = str(graph.get("run_id") or run_id or "").strip() or None
    input_graph_fingerprint = fingerprint_market_situation_graph(graph)
    graph_status = str(((graph.get("projection_status") or {}).get("status")) if isinstance(graph.get("projection_status"), Mapping) else "in_sync")
    situations = [row for row in graph.get("situations") or [] if isinstance(row, Mapping)]
    situations.sort(key=lambda row: (int(row.get("rank") or 999), str(row.get("situation_id") or "")))
    drilldown = _drilldown_index(graph, situations)
    graph_slice = _graph_slice(graph=graph, situations=situations, drilldown_index=drilldown)
    source_refs = drilldown.get("source_refs") if isinstance(drilldown.get("source_refs"), Mapping) else {}
    finance_research_assurance = _build_finance_research_assurance_binding(repo_root, run_id=run_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "input_graph_schema_version": graph.get("schema_version"),
        "input_graph_fingerprint": input_graph_fingerprint,
        "input_graph_path": _repo_rel(repo_root, graph_path or _graph_path_for_run(repo_root, run_id, report_root=report_root)),
        "projection_status": {"status": "in_sync"},
        "authority_boundary": {
            "backend_only_contract": True,
            "not_frontend_layout": True,
            "not_trading_or_investment_advice": True,
            "situations_not_recommendations": True,
            "read_model_not_source_authority": True,
            "finance_research_assurance_consumed": True,
            "financial_research_only": True,
            "no_advice_mode": True,
        },
        "build": {
            "builder": "system/lib/market_dashboard_read_model.py",
            "builder_schema_version": SCHEMA_VERSION,
            "input_graph_schema_version": graph.get("schema_version"),
            "input_graph_fingerprint": input_graph_fingerprint,
            "deterministic_render": True,
        },
        "overview": _overview(
            graph=graph,
            input_graph_fingerprint=input_graph_fingerprint,
            situations=situations,
            graph_status=graph_status,
        ),
        "situation_queue": _situation_queue(situations),
        "situation_detail_index": _detail_index(situations),
        "graph_slice": graph_slice,
        "facets": _facets(graph=graph, situations=situations, source_refs=source_refs),
        "drilldown_index": drilldown,
        "provenance_index": _provenance_index(
            repo_root=repo_root,
            graph=graph,
            graph_path=graph_path or _graph_path_for_run(repo_root, run_id, report_root=report_root),
            input_graph_fingerprint=input_graph_fingerprint,
        ),
        "validation_debt": _validation_debt(situations, graph),
        "finance_research_assurance": finance_research_assurance,
        "display_hints": _display_hints(),
        "api_contract": _api_contract(),
    }
    return payload


def _unavailable_read_model(
    *,
    run_id: str | None,
    status: str,
    reason: str,
    path: Path,
    payload_run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "input_graph_schema_version": None,
        "input_graph_fingerprint": None,
        "projection_status": {
            "status": status,
            "reason": reason,
            "path": str(path),
            "expected_run_id": run_id,
            "payload_run_id": payload_run_id,
        },
        "authority_boundary": {
            "backend_only_contract": True,
            "not_frontend_layout": True,
            "not_trading_or_investment_advice": True,
            "situations_not_recommendations": True,
            "financial_research_only": True,
            "no_advice_mode": True,
        },
        "overview": {
            "run_id": run_id,
            "graph_status": status,
            "situation_count": 0,
            "edge_count": 0,
            "validated_signal_count": 0,
            "blocking_warnings": [{"reason": reason}],
        },
        "situation_queue": _page_connection([], limit=0),
        "situation_detail_index": {},
        "graph_slice": {"nodes": [], "edges": []},
        "facets": {},
        "drilldown_index": {},
        "provenance_index": {},
        "validation_debt": {
            "validated_signal_count": 0,
            "requires_backtest_count": 0,
            "requires_event_study_count": 0,
            "blocked_promotions": [],
        },
        "finance_research_assurance": {
            "schema_version": FINANCE_ASSURANCE_BINDING_SCHEMA_VERSION,
            "source_status": "unavailable_input",
            "feed_freshness": {"state": "blocked_missing_artifact"},
            "oracle_evolve": {"review_gated": True, "auto_apply_allowed": False},
            "no_advice_mode": {
                "enabled": True,
                "non_advisory_research_only": True,
                "authority_overclaim_count": 0,
            },
        },
        "display_hints": _display_hints(),
        "api_contract": _api_contract(),
    }


def validate_market_dashboard_read_model(
    payload: Mapping[str, Any],
    *,
    strict: bool = False,
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"$.schema_version must be {SCHEMA_VERSION}")
    if not isinstance(payload.get("projection_status"), Mapping):
        errors.append("$.projection_status must be an object")
    if not isinstance(payload.get("overview"), Mapping):
        errors.append("$.overview must be an object")
    if not isinstance(payload.get("situation_queue"), Mapping):
        errors.append("$.situation_queue must be an object")
    if not isinstance(payload.get("situation_detail_index"), Mapping):
        errors.append("$.situation_detail_index must be an object")
    if not isinstance(payload.get("graph_slice"), Mapping):
        errors.append("$.graph_slice must be an object")
    if not isinstance(payload.get("api_contract"), Mapping):
        errors.append("$.api_contract must be an object")
    if errors:
        return errors

    status = str((payload.get("projection_status") or {}).get("status") or "")
    if status != "in_sync":
        return errors if not strict else errors + [f"$.projection_status.status must be in_sync for strict check, got {status!r}"]

    overview = payload.get("overview") or {}
    if not overview.get("safe_use_level"):
        errors.append("$.overview.safe_use_level is required")
    if not (payload.get("api_contract") or {}).get("contract_version"):
        errors.append("$.api_contract.contract_version is required")
    detail_index = payload.get("situation_detail_index") or {}
    queue_items = ((payload.get("situation_queue") or {}).get("items") or [])
    for item in queue_items:
        if not isinstance(item, Mapping):
            errors.append("$.situation_queue.items[] must be objects")
            continue
        sid = str(item.get("situation_id") or "")
        if not sid:
            errors.append("$.situation_queue.items[].situation_id is required")
            continue
        if sid not in detail_index:
            errors.append(f"$.situation_queue.items[{sid}].detail_ref has no detail entry")
        if not item.get("safe_use_level"):
            errors.append(f"$.situation_queue.items[{sid}].safe_use_level is required")
    for sid, detail in detail_index.items():
        if not isinstance(detail, Mapping):
            errors.append(f"$.situation_detail_index[{sid}] must be object")
            continue
        if not detail.get("evidence_edges"):
            errors.append(f"$.situation_detail_index[{sid}].evidence_edges is required")
        if not detail.get("counterevidence_edges"):
            errors.append(f"$.situation_detail_index[{sid}].counterevidence_edges is required")
        validation = detail.get("validation") if isinstance(detail.get("validation"), Mapping) else {}
        if validation.get("state") == "validated_signal" and not validation.get("validation_refs"):
            errors.append(f"$.situation_detail_index[{sid}] validated_signal lacks validation_refs")

    graph_slice = payload.get("graph_slice") or {}
    node_ids = {
        str(row.get("node_id"))
        for row in graph_slice.get("nodes") or []
        if isinstance(row, Mapping) and str(row.get("node_id") or "")
    }
    for edge in graph_slice.get("edges") or []:
        if not isinstance(edge, Mapping):
            errors.append("$.graph_slice.edges[] must be object")
            continue
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in node_ids:
            errors.append(f"$.graph_slice.edges[{edge.get('edge_id')}].source is dangling")
        if target not in node_ids:
            errors.append(f"$.graph_slice.edges[{edge.get('edge_id')}].target is dangling")

    drilldown = payload.get("drilldown_index") if isinstance(payload.get("drilldown_index"), Mapping) else {}
    source_refs = drilldown.get("source_refs") if isinstance(drilldown.get("source_refs"), Mapping) else {}
    source_rows = drilldown.get("source_rows") if isinstance(drilldown.get("source_rows"), Mapping) else {}
    for source_ref_id, ref in source_refs.items():
        if not isinstance(ref, Mapping):
            errors.append(f"$.drilldown_index.source_refs[{source_ref_id}] must be object")
            continue
        if ref.get("arbitrary_file_read_allowed") is not False:
            errors.append(f"$.drilldown_index.source_refs[{source_ref_id}].arbitrary_file_read_allowed must be false")
        route_ref = str(ref.get("route_ref") or "")
        if not route_ref.startswith("/api/market/intelligence/drilldown/"):
            errors.append(f"$.drilldown_index.source_refs[{source_ref_id}].route_ref is invalid")
        if ".." in route_ref:
            errors.append(f"$.drilldown_index.source_refs[{source_ref_id}].route_ref contains traversal")
        if source_ref_id not in source_rows:
            errors.append(f"$.drilldown_index.source_refs[{source_ref_id}] has no source_rows entry")

    validation_debt = payload.get("validation_debt") if isinstance(payload.get("validation_debt"), Mapping) else {}
    if int(validation_debt.get("validated_signal_count") or 0) > 0:
        validation_refs = payload.get("validation_refs") if isinstance(payload.get("validation_refs"), list) else []
        if not validation_refs:
            errors.append("$.validation_debt.validated_signal_count > 0 without validation_refs")

    finance_assurance = (
        payload.get("finance_research_assurance")
        if isinstance(payload.get("finance_research_assurance"), Mapping)
        else {}
    )
    if not finance_assurance:
        errors.append("$.finance_research_assurance must be an object")
    else:
        if finance_assurance.get("schema_version") != FINANCE_ASSURANCE_BINDING_SCHEMA_VERSION:
            errors.append(
                f"$.finance_research_assurance.schema_version must be "
                f"{FINANCE_ASSURANCE_BINDING_SCHEMA_VERSION}"
            )
        feed_freshness = (
            finance_assurance.get("feed_freshness")
            if isinstance(finance_assurance.get("feed_freshness"), Mapping)
            else {}
        )
        if not feed_freshness.get("state"):
            errors.append("$.finance_research_assurance.feed_freshness.state is required")
        oracle_evolve = (
            finance_assurance.get("oracle_evolve")
            if isinstance(finance_assurance.get("oracle_evolve"), Mapping)
            else {}
        )
        if oracle_evolve.get("auto_apply_allowed") is not False:
            errors.append("$.finance_research_assurance.oracle_evolve.auto_apply_allowed must be false")
        if oracle_evolve.get("review_gated") is not True:
            errors.append("$.finance_research_assurance.oracle_evolve.review_gated must be true")
        no_advice_mode = (
            finance_assurance.get("no_advice_mode")
            if isinstance(finance_assurance.get("no_advice_mode"), Mapping)
            else {}
        )
        if no_advice_mode.get("enabled") is not True:
            errors.append("$.finance_research_assurance.no_advice_mode.enabled must be true")
        if no_advice_mode.get("non_advisory_research_only") is not True:
            errors.append(
                "$.finance_research_assurance.no_advice_mode.non_advisory_research_only must be true"
            )
        module_coverage = (
            finance_assurance.get("module_coverage")
            if isinstance(finance_assurance.get("module_coverage"), Mapping)
            else {}
        )
        if int(module_coverage.get("silent_omission_count") or 0) != 0:
            errors.append("$.finance_research_assurance.module_coverage.silent_omission_count must be 0")
        forecast_comparison = (
            finance_assurance.get("forecast_comparison")
            if isinstance(finance_assurance.get("forecast_comparison"), Mapping)
            else {}
        )
        if finance_assurance.get("source_status") == "present" and not forecast_comparison.get("sequence"):
            errors.append("$.finance_research_assurance.forecast_comparison.sequence is required")
        quant_research = (
            finance_assurance.get("quant_research_experiment")
            if isinstance(finance_assurance.get("quant_research_experiment"), Mapping)
            else {}
        )
        if finance_assurance.get("source_status") == "present":
            if (
                quant_research.get("schema_version")
                != "finance_quant_research_experiment_spine_v0"
            ):
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.schema_version is required"
                )
            if quant_research.get("winner_language_allowed") is not False:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.winner_language_allowed must be false"
                )
            if quant_research.get("auto_apply_allowed") is not False:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.auto_apply_allowed must be false"
                )
            if quant_research.get("review_gated") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.review_gated must be true"
                )
            if quant_research.get("no_advice_enabled") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.no_advice_enabled must be true"
                )
            if int(quant_research.get("registry_count") or 0) < 2:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.registry_count must be at least 2"
                )
            if int(quant_research.get("negative_control_count") or 0) < 1:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.negative_control_count must be at least 1"
                )
            if int(quant_research.get("negative_or_insufficient_count") or 0) < 1:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.negative_or_insufficient_count must be at least 1"
                )
            if (
                quant_research.get("lineage_status")
                != "stress_validated_public_demo"
            ):
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.lineage_status must be stress_validated_public_demo"
                )
            if int(quant_research.get("agenda_candidate_count") or 0) < 4:
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.agenda_candidate_count must be at least 4"
                )
            if not quant_research.get("cycle_selected_candidate_id"):
                errors.append(
                    "$.finance_research_assurance.quant_research_experiment.cycle_selected_candidate_id is required"
                )
            quant_lineage = (
                finance_assurance.get("quant_research_lineage")
                if isinstance(finance_assurance.get("quant_research_lineage"), Mapping)
                else {}
            )
            for row in quant_lineage.get("registry_preview", []):
                if not isinstance(row, Mapping):
                    continue
                if row.get("winner_language_allowed") is not False:
                    errors.append(
                        "$.finance_research_assurance.quant_research_lineage.registry_preview winner_language_allowed must be false"
                    )
                if row.get("auto_apply_allowed") is not False:
                    errors.append(
                        "$.finance_research_assurance.quant_research_lineage.registry_preview auto_apply_allowed must be false"
                    )
                if row.get("review_gated") is not True:
                    errors.append(
                        "$.finance_research_assurance.quant_research_lineage.registry_preview review_gated must be true"
                    )
                if row.get("no_advice_enabled") is not True:
                    errors.append(
                        "$.finance_research_assurance.quant_research_lineage.registry_preview no_advice_enabled must be true"
                    )
            quant_agenda = (
                finance_assurance.get("quant_research_agenda")
                if isinstance(finance_assurance.get("quant_research_agenda"), Mapping)
                else {}
            )
            if quant_agenda.get("schema_version") != "finance_quant_research_agenda_v0":
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.schema_version is required"
                )
            if quant_agenda.get("status") != "compiled_public_safe":
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.status must be compiled_public_safe"
                )
            if int(quant_agenda.get("candidate_count") or 0) < 4:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.candidate_count must be at least 4"
                )
            if int(quant_agenda.get("selected_for_next_test_count") or 0) < 1:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.selected_for_next_test_count must be at least 1"
                )
            if int(quant_agenda.get("deferred_data_snooping_count") or 0) < 1:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.deferred_data_snooping_count must be at least 1"
                )
            if int(quant_agenda.get("negative_or_control_candidate_count") or 0) < 1:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.negative_or_control_candidate_count must be at least 1"
                )
            if int(quant_agenda.get("needs_more_evidence_count") or 0) < 1:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.needs_more_evidence_count must be at least 1"
                )
            if quant_agenda.get("data_snooping_guard_active") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.data_snooping_guard_active must be true"
                )
            if quant_agenda.get("performance_metric_optimization_allowed") is not False:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.performance_metric_optimization_allowed must be false"
                )
            if quant_agenda.get("winner_language_allowed") is not False:
                errors.append(
                    "$.finance_research_assurance.quant_research_agenda.winner_language_allowed must be false"
                )
            agenda_states = {
                str(row.get("agenda_state") or "")
                for row in quant_agenda.get("candidate_preview", [])
                if isinstance(row, Mapping)
            }
            for required_state in {
                "selected_for_next_test",
                "deferred_data_snooping_risk",
                "control_candidate",
                "needs_more_evidence",
            }:
                if required_state not in agenda_states:
                    errors.append(
                        f"$.finance_research_assurance.quant_research_agenda.candidate_preview missing {required_state}"
                    )
            for row in quant_agenda.get("candidate_preview", []):
                if not isinstance(row, Mapping):
                    continue
                if row.get("winner_language_allowed") is not False:
                    errors.append(
                        "$.finance_research_assurance.quant_research_agenda.candidate_preview winner_language_allowed must be false"
                    )
                if row.get("auto_apply_allowed") is not False:
                    errors.append(
                        "$.finance_research_assurance.quant_research_agenda.candidate_preview auto_apply_allowed must be false"
                    )
                if row.get("review_gated") is not True:
                    errors.append(
                        "$.finance_research_assurance.quant_research_agenda.candidate_preview review_gated must be true"
                    )
                if row.get("no_advice_enabled") is not True:
                    errors.append(
                        "$.finance_research_assurance.quant_research_agenda.candidate_preview no_advice_enabled must be true"
                    )
            quant_cycle = (
                finance_assurance.get("quant_research_cycle")
                if isinstance(finance_assurance.get("quant_research_cycle"), Mapping)
                else {}
            )
            if (
                quant_cycle.get("schema_version")
                != "finance_quant_agenda_execution_cycle_v0"
            ):
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.schema_version is required"
                )
            if quant_cycle.get("registered_before_execution") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.registered_before_execution must be true"
                )
            if quant_cycle.get("analysis_plan_locked") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.analysis_plan_locked must be true"
                )
            if quant_cycle.get("post_hoc_plan_mutation_allowed") is not False:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.post_hoc_plan_mutation_allowed must be false"
                )
            if quant_cycle.get("used_existing_evaluator") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.used_existing_evaluator must be true"
                )
            if quant_cycle.get("winner_language_allowed") is not False:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.winner_language_allowed must be false"
                )
            if not quant_cycle.get("selected_candidate_id"):
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.selected_candidate_id is required"
                )
            if not quant_cycle.get("pre_analysis_plan_id"):
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.pre_analysis_plan_id is required"
                )
            if not quant_cycle.get("appended_experiment_id"):
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.appended_experiment_id is required"
                )
            if int(quant_cycle.get("new_registry_count") or 0) <= int(
                quant_cycle.get("previous_registry_count") or 0
            ):
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.new_registry_count must increase"
                )
            if quant_cycle.get("agenda_recompile_status") != "recompiled_after_cycle":
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.agenda_recompile_status must be recompiled_after_cycle"
                )
            if not quant_cycle.get("next_selected_candidate_id"):
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.next_selected_candidate_id is required"
                )
            if quant_cycle.get("review_gated") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.review_gated must be true"
                )
            if quant_cycle.get("auto_apply_allowed") is not False:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.auto_apply_allowed must be false"
                )
            if quant_cycle.get("no_advice_enabled") is not True:
                errors.append(
                    "$.finance_research_assurance.quant_research_cycle.no_advice_enabled must be true"
                )

    if strict:
        for path, text in _string_values(payload):
            for token in FRONTEND_LAYOUT_TOKENS:
                if token in text:
                    errors.append(f"{path} contains frontend layout token {token!r}")
            if TRADING_CLAIM_PATTERN.search(text):
                errors.append(f"{path} contains trading/action claim language")
    return errors


def _string_values(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield from _string_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_values(child, f"{path}[{index}]")


def write_market_dashboard_read_model(
    repo_root: Path,
    *,
    run_id: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    latest_filename: str = DEFAULT_LATEST_FILENAME,
    graph_payload: Mapping[str, Any] | None = None,
    graph_path: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    payload = build_market_dashboard_read_model(
        repo_root,
        run_id=run_id,
        report_root=report_root,
        graph_payload=graph_payload,
        graph_path=graph_path,
    )
    actual_run_id = str(payload.get("run_id") or "").strip()
    if not actual_run_id:
        return payload
    root = report_root if report_root.is_absolute() else repo_root / report_root
    artifact_output = repo_root / "state" / "runs" / actual_run_id / "artifacts" / RUN_ARTIFACT_FILENAME
    run_output = root / actual_run_id / REPORT_FILENAME
    latest_output = root / latest_filename
    for path in (artifact_output, run_output, latest_output):
        _write_json(path, payload)
    return payload


def load_latest_market_dashboard_read_model(
    repo_root: Path,
    *,
    expected_run_id: str | None = None,
    expected_graph_fingerprint: str | None = None,
    report_root: Path = DEFAULT_REPORT_ROOT,
    latest_filename: str = DEFAULT_LATEST_FILENAME,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    root = report_root if report_root.is_absolute() else repo_root / report_root
    path = root / latest_filename
    payload = _read_json(path)
    if not payload:
        return _unavailable_read_model(
            run_id=expected_run_id,
            status="market_dashboard_read_model_missing",
            reason="latest_market_dashboard_read_model_missing",
            path=path,
        )
    if payload.get("schema_version") != SCHEMA_VERSION:
        return _unavailable_read_model(
            run_id=expected_run_id,
            status="market_dashboard_read_model_schema_mismatch",
            reason=f"expected {SCHEMA_VERSION}, got {payload.get('schema_version')}",
            path=path,
            payload_run_id=str(payload.get("run_id") or ""),
        )
    payload_run_id = str(payload.get("run_id") or "")
    if expected_run_id and payload_run_id != expected_run_id:
        return _unavailable_read_model(
            run_id=expected_run_id,
            status="market_dashboard_read_model_stale",
            reason="run_id_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
    payload_fingerprint = str(payload.get("input_graph_fingerprint") or "")
    if expected_graph_fingerprint and payload_fingerprint != expected_graph_fingerprint:
        return _unavailable_read_model(
            run_id=expected_run_id or payload_run_id,
            status="market_dashboard_read_model_stale",
            reason="input_graph_fingerprint_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
    payload["projection_status"] = {"status": "in_sync", "path": _repo_rel(repo_root, path)}
    return payload


def load_market_dashboard_read_model(
    repo_root: Path,
    run_id: str,
    *,
    report_root: Path = DEFAULT_REPORT_ROOT,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    root = report_root if report_root.is_absolute() else repo_root / report_root
    path = root / run_id / REPORT_FILENAME
    payload = _read_json(path)
    if not payload:
        artifact_path = repo_root / "state" / "runs" / run_id / "artifacts" / RUN_ARTIFACT_FILENAME
        payload = _read_json(artifact_path)
        if payload:
            path = artifact_path
    if not payload:
        return _unavailable_read_model(
            run_id=run_id,
            status="market_dashboard_read_model_missing",
            reason="run_market_dashboard_read_model_missing",
            path=path,
        )
    if payload.get("schema_version") != SCHEMA_VERSION:
        return _unavailable_read_model(
            run_id=run_id,
            status="market_dashboard_read_model_schema_mismatch",
            reason=f"expected {SCHEMA_VERSION}, got {payload.get('schema_version')}",
            path=path,
            payload_run_id=str(payload.get("run_id") or ""),
        )
    payload_run_id = str(payload.get("run_id") or "")
    if payload_run_id != run_id:
        return _unavailable_read_model(
            run_id=run_id,
            status="market_dashboard_read_model_stale",
            reason="run_id_mismatch",
            path=path,
            payload_run_id=payload_run_id,
        )
    payload["projection_status"] = {
        "status": "in_sync",
        "path": _repo_rel(repo_root, path),
        "selected_run_id": run_id,
    }
    return payload


def filter_situation_queue(
    read_model: Mapping[str, Any],
    *,
    type: str | None = None,
    horizon: str | None = None,
    claim_level: str | None = None,
    validation_state: str | None = None,
    display_state: str | None = None,
    entity: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    detail_index = read_model.get("situation_detail_index") if isinstance(read_model.get("situation_detail_index"), Mapping) else {}
    cards = [dict(row) for row in ((read_model.get("situation_queue") or {}).get("items") or []) if isinstance(row, Mapping)]

    def keep(card: Mapping[str, Any]) -> bool:
        sid = str(card.get("situation_id") or "")
        detail = detail_index.get(sid) if isinstance(detail_index.get(sid), Mapping) else {}
        if type and card.get("situation_type") != type:
            return False
        if horizon and card.get("horizon") != horizon:
            return False
        if claim_level and card.get("claim_level") != claim_level:
            return False
        if validation_state and card.get("validation_state") != validation_state:
            return False
        if display_state and card.get("display_state") != display_state:
            return False
        if entity and entity not in {str(row) for row in card.get("primary_entities") or []}:
            return False
        if provider:
            refs = detail.get("source_refs") if isinstance(detail.get("source_refs"), list) else []
            if provider not in {
                str((ref.get("feed_id") or ref.get("provider_id") or ref.get("kind")))
                for ref in refs
                if isinstance(ref, Mapping)
            }:
                return False
        return True

    matched = [card for card in cards if keep(card)]
    start = 0
    if cursor:
        try:
            start = max(0, int(cursor))
        except Exception:
            start = 0
    limit = max(1, min(200, int(limit or 50)))
    page = matched[start : start + limit]
    end = start + len(page)
    return {
        "items": page,
        "page_info": {
            "has_next_page": end < len(matched),
            "end_cursor": str(end) if end < len(matched) else None,
        },
        "total_count": len(cards),
        "matched_count": len(matched),
        "active_filters": {
            "type": type,
            "horizon": horizon,
            "claim_level": claim_level,
            "validation_state": validation_state,
            "display_state": display_state,
            "entity": entity,
            "provider": provider,
            "limit": limit,
            "cursor": cursor,
        },
    }


def resolve_situation_detail(read_model: Mapping[str, Any], situation_id: str) -> dict[str, Any]:
    detail_index = read_model.get("situation_detail_index") if isinstance(read_model.get("situation_detail_index"), Mapping) else {}
    detail = detail_index.get(situation_id)
    if not isinstance(detail, Mapping):
        return {
            "schema_version": "market_dashboard_situation_detail_v0",
            "available": False,
            "situation_id": situation_id,
            "reason": "not_found",
        }
    return {
        "schema_version": "market_dashboard_situation_detail_v0",
        "available": True,
        "situation_id": situation_id,
        "detail": dict(detail),
    }


def resolve_graph_slice(
    read_model: Mapping[str, Any],
    *,
    situation_id: str | None = None,
    depth: int = 1,
    include_source_refs: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    graph = read_model.get("graph_slice") if isinstance(read_model.get("graph_slice"), Mapping) else {}
    nodes = [dict(row) for row in graph.get("nodes") or [] if isinstance(row, Mapping)]
    edges = [dict(row) for row in graph.get("edges") or [] if isinstance(row, Mapping)]
    if situation_id:
        frontier = {situation_id}
        selected_edges: list[dict[str, Any]] = []
        for _ in range(max(1, min(3, int(depth or 1)))):
            next_frontier: set[str] = set()
            for edge in edges:
                source = str(edge.get("source") or "")
                target = str(edge.get("target") or "")
                if source in frontier or target in frontier:
                    selected_edges.append(edge)
                    next_frontier.update({source, target})
            frontier |= next_frontier
        edge_keys = {str(edge.get("edge_id") or "") for edge in selected_edges}
        edges = [edge for edge in selected_edges if str(edge.get("edge_id") or "") in edge_keys]
        node_ids = {situation_id}
        for edge in edges:
            node_ids.add(str(edge.get("source") or ""))
            node_ids.add(str(edge.get("target") or ""))
        nodes = [node for node in nodes if str(node.get("node_id") or "") in node_ids]
    if not include_source_refs:
        source_ref_ids = {str(node.get("node_id")) for node in nodes if node.get("node_type") == "source_ref"}
        nodes = [node for node in nodes if str(node.get("node_id")) not in source_ref_ids]
        edges = [
            edge
            for edge in edges
            if str(edge.get("source")) not in source_ref_ids and str(edge.get("target")) not in source_ref_ids
        ]
    limit = max(1, min(500, int(limit or 200)))
    return {
        "schema_version": "market_dashboard_graph_slice_v0",
        "situation_id": situation_id,
        "depth": depth,
        "include_source_refs": include_source_refs,
        "nodes": nodes[:limit],
        "edges": edges[:limit],
    }


def resolve_drilldown(read_model: Mapping[str, Any], source_ref_id: str) -> dict[str, Any]:
    drilldown = read_model.get("drilldown_index") if isinstance(read_model.get("drilldown_index"), Mapping) else {}
    refs = drilldown.get("source_refs") if isinstance(drilldown.get("source_refs"), Mapping) else {}
    rows = drilldown.get("source_rows") if isinstance(drilldown.get("source_rows"), Mapping) else {}
    ref = refs.get(source_ref_id)
    if not isinstance(ref, Mapping):
        return {
            "schema_version": "market_dashboard_drilldown_v0",
            "available": False,
            "source_ref_id": source_ref_id,
            "reason": "not_found",
        }
    return {
        "schema_version": "market_dashboard_drilldown_v0",
        "available": True,
        "source_ref_id": source_ref_id,
        "source_ref": dict(ref),
        "source_row": dict(rows.get(source_ref_id) or {}),
        "arbitrary_file_read_allowed": False,
    }


def resolve_provenance(read_model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "market_dashboard_provenance_v0",
        "provenance_index": dict(read_model.get("provenance_index") or {}),
        "projection_status": dict(read_model.get("projection_status") or {}),
    }


def resolve_validation_debt(read_model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "market_dashboard_validation_debt_v0",
        "validation_debt": dict(read_model.get("validation_debt") or {}),
        "projection_status": dict(read_model.get("projection_status") or {}),
    }
