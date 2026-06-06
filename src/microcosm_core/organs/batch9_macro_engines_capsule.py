from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import math
import re
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict, deque
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch9_macro_engines_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

EXPECTED_MECHANISMS: tuple[str, ...] = (
    "lineage_temporal_provenance_chain_resolver",
    "approval_sign_off_claim_adjudicator",
    "python_ast_symbol_index_doc_tree",
    "finance_news_dedup_cluster_ranker",
    "mission_graph_topological_compiler",
    "dependency_pin_drift_auditor",
    "config_authority_drift_audit",
    "heterogeneous_graph_edge_extractor",
    "work_atlas_cell_histogram_aggregator",
    "host_pressure_admission_decision_gate",
    "doctrine_file_enrichment_multihop_join",
    "worker_job_budget_forbidden_surface_gate",
    "milestone_relative_promotion_quality_accounting",
)

EXPECTED_MODULE_IDS: tuple[str, ...] = (
    "lineage_temporal_provenance_chain_resolver",
    "approval_sign_off_claim_adjudicator",
    "python_ast_symbol_index_doc_tree",
    "finance_news_dedup_cluster_ranker",
    "mission_graph_topological_compiler",
    "dependency_pin_drift_auditor",
    "config_authority_drift_audit",
    "heterogeneous_graph_edge_extractor",
    "work_atlas_cell_histogram_aggregator",
    "host_pressure_admission_decision_gate",
    "doctrine_file_enrichment_multihop_join",
    "worker_job_budget_forbidden_surface_gate",
    "milestone_relative_promotion_quality_accounting",
)

FINANCE_MODULE_ID = "finance_news_dedup_cluster_ranker"
MISSION_GRAPH_MODULE_ID = "mission_graph_topological_compiler"
DEPENDENCY_PIN_MODULE_ID = "dependency_pin_drift_auditor"
CONFIG_AUTHORITY_MODULE_ID = "config_authority_drift_audit"
HOST_PRESSURE_MODULE_ID = "host_pressure_admission_decision_gate"
LINEAGE_MODULE_ID = "lineage_temporal_provenance_chain_resolver"
APPROVAL_MODULE_ID = "approval_sign_off_claim_adjudicator"
AST_MODULE_ID = "python_ast_symbol_index_doc_tree"
DOCTRINE_MODULE_ID = "doctrine_file_enrichment_multihop_join"
WORKER_GATE_MODULE_ID = "worker_job_budget_forbidden_surface_gate"
MILESTONE_MODULE_ID = "milestone_relative_promotion_quality_accounting"
WORK_ATLAS_MODULE_ID = "work_atlas_cell_histogram_aggregator"
HETEROGENEOUS_MODULE_ID = "heterogeneous_graph_edge_extractor"

TEXT_BACKED_MODULE_IDS: tuple[str, ...] = (
    FINANCE_MODULE_ID,
    MISSION_GRAPH_MODULE_ID,
    WORK_ATLAS_MODULE_ID,
    HETEROGENEOUS_MODULE_ID,
)
PATH_BACKED_MODULE_IDS: tuple[str, ...] = (
    LINEAGE_MODULE_ID,
    APPROVAL_MODULE_ID,
    AST_MODULE_ID,
    DEPENDENCY_PIN_MODULE_ID,
    CONFIG_AUTHORITY_MODULE_ID,
    HOST_PRESSURE_MODULE_ID,
    DOCTRINE_MODULE_ID,
    WORKER_GATE_MODULE_ID,
    MILESTONE_MODULE_ID,
)

EXPECTED_NEGATIVE_CASES = {
    "lineage_self_loop_pruned": ("BATCH9_LINEAGE_SELF_LOOP_PRUNED",),
    "approval_preacquired_claim_refused": ("BATCH9_APPROVAL_PREACQUIRED_CLAIM_REFUSED",),
    "ast_syntax_error_gap": ("BATCH9_AST_SYNTAX_ERROR_GAP",),
    "finance_duplicate_headline_collapsed": ("BATCH9_FINANCE_DUPLICATE_HEADLINE_COLLAPSED",),
    "mission_graph_missing_target": ("BATCH9_MISSION_GRAPH_MISSING_TARGET",),
    "dependency_pin_drift_detected": ("BATCH9_DEPENDENCY_PIN_DRIFT_DETECTED",),
    "config_authority_mutation_allowed_rejected": (
        "BATCH9_CONFIG_AUTHORITY_MUTATION_ALLOWED_REJECTED",
    ),
    "heterogeneous_edge_relation_normalized": (
        "BATCH9_EDGE_RELATION_NORMALIZED",
    ),
    "work_atlas_routed_reason_excluded": ("BATCH9_WORK_ATLAS_ROUTED_REASON_EXCLUDED",),
    "host_pressure_auto_policy_blocks": ("BATCH9_HOST_PRESSURE_AUTO_POLICY_BLOCKS",),
    "doctrine_enrichment_unindexed_empty": ("BATCH9_DOCTRINE_UNINDEXED_EMPTY",),
    "worker_forbidden_surface_blocked": ("BATCH9_WORKER_FORBIDDEN_SURFACE_BLOCKED",),
    "milestone_missing_committed_at_bucketed": (
        "BATCH9_MILESTONE_MISSING_COMMITTED_AT_BUCKETED",
    ),
}

NEGATIVE_CASE_RUNTIME_CHECKS: dict[str, tuple[str, str, str]] = {
    "lineage_self_loop_pruned": (
        "lineage_temporal_provenance_chain_resolver",
        "self_loop_pruned",
        "BATCH9_LINEAGE_SELF_LOOP_PRUNED",
    ),
    "approval_preacquired_claim_refused": (
        "approval_sign_off_claim_adjudicator",
        "preacquired_claim_refused",
        "BATCH9_APPROVAL_PREACQUIRED_CLAIM_REFUSED",
    ),
    "ast_syntax_error_gap": (
        "python_ast_symbol_index_doc_tree",
        "syntax_error_gap",
        "BATCH9_AST_SYNTAX_ERROR_GAP",
    ),
    "finance_duplicate_headline_collapsed": (
        "finance_news_dedup_cluster_ranker",
        "duplicate_collapsed",
        "BATCH9_FINANCE_DUPLICATE_HEADLINE_COLLAPSED",
    ),
    "mission_graph_missing_target": (
        "mission_graph_topological_compiler",
        "missing_target_error",
        "BATCH9_MISSION_GRAPH_MISSING_TARGET",
    ),
    "dependency_pin_drift_detected": (
        "dependency_pin_drift_auditor",
        "drifted_count",
        "BATCH9_DEPENDENCY_PIN_DRIFT_DETECTED",
    ),
    "config_authority_mutation_allowed_rejected": (
        "config_authority_drift_audit",
        "mutation_allowed_rejected",
        "BATCH9_CONFIG_AUTHORITY_MUTATION_ALLOWED_REJECTED",
    ),
    "heterogeneous_edge_relation_normalized": (
        "heterogeneous_graph_edge_extractor",
        "normalized_relation_count",
        "BATCH9_EDGE_RELATION_NORMALIZED",
    ),
    "work_atlas_routed_reason_excluded": (
        "work_atlas_cell_histogram_aggregator",
        "route_reason_histogram",
        "BATCH9_WORK_ATLAS_ROUTED_REASON_EXCLUDED",
    ),
    "host_pressure_auto_policy_blocks": (
        "host_pressure_admission_decision_gate",
        "auto_policy_blocked",
        "BATCH9_HOST_PRESSURE_AUTO_POLICY_BLOCKS",
    ),
    "doctrine_enrichment_unindexed_empty": (
        "doctrine_file_enrichment_multihop_join",
        "miss_empty_envelope",
        "BATCH9_DOCTRINE_UNINDEXED_EMPTY",
    ),
    "worker_forbidden_surface_blocked": (
        "worker_job_budget_forbidden_surface_gate",
        "blocked_job_status",
        "BATCH9_WORKER_FORBIDDEN_SURFACE_BLOCKED",
    ),
    "milestone_missing_committed_at_bucketed": (
        "milestone_relative_promotion_quality_accounting",
        "missing_committed_at_count_since_last_milestone",
        "BATCH9_MILESTONE_MISSING_COMMITTED_AT_BUCKETED",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch9_public_macro_engines_capsule_not_live_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "standard_authority": (
        "public_batch9_source_open_capsule_and_source_body_digest_contract_only"
    ),
    "provider_dispatch": False,
    "host_state_truth": False,
    "live_doctrine_truth": False,
    "real_news_truth": False,
    "market_advice": False,
    "work_ledger_authority": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Batch 9 validates copied non-secret macro source bodies plus public "
    "source-faithful exercises for provenance lineage, approval adjudication, "
    "Python AST indexing, finance headline clustering, mission graph waves, "
    "dependency pin drift, config authority audit, heterogeneous edge "
    "extraction, WorkAtlas aggregation, host-pressure admission, doctrine "
    "enrichment, worker pre-dispatch gating, and milestone-relative quality "
    "accounting. It is not live authority, not real market or doctrine truth, "
    "not provider dispatch, not Work Ledger truth, not source mutation "
    "permission, not publication authority, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/server/lineage.py": (
        "def _extract_links(",
        "def _select_primary_parent(",
        "def _select_truth_parent(",
    ),
    "system/lib/approval_registry.py": (
        "def list_approvals(",
        "def _acquire_claim(",
        "def decide_approval(",
    ),
    "system/lib/python_documentation_tree.py": (
        "ast.parse",
        "ast.FunctionDef",
        "def build_file_entry(",
    ),
    "system/server/ui/src/lib/financePresentation.ts": (
        "function extractHeadline(",
        "function normalizeHeadlineFingerprint(",
        "export function clusterNewsRows(",
    ),
    "system/server/graph.py": (
        "def compile_graph_snapshot(",
        "Group Closure Scoping",
        "waves.append(sorted(current_wave))",
    ),
    "tools/dev/check_pin_drift.py": (
        "def parse_requirements(",
        "DRIFTED",
        "UNPARSEABLE",
    ),
    "system/lib/config_authority_registry.py": (
        "def validate_config_authority_registry(",
        "duplicate_config_id",
        "generated_projection_or_cache",
    ),
    "system/server/ui/src/pages/RootNavigator.tsx": (
        "GENERIC_EDGE_FIELD_MAP",
        "function normalizeEdgeRelationToken(",
        "top_dependencies",
    ),
    "system/server/ui/src/components/intelligence/WorkAtlas.tsx": (
        "function aggregateCell(",
        "route_reason keys for marks where overlays.unrouted is true",
        "function cellMarksPerRow(",
    ),
    "system/lib/admission_consumer.py": (
        "ADMISSION_POLICY_VALUES",
        "def normalize_admission_policy(",
        "def build_admission_consumer_decision(",
    ),
    "system/server/doctrine_enrichment.py": (
        "class DoctrineEnrichmentService",
        "self._mechanisms_by_path",
        "def get_file_doctrine(",
    ),
    "system/lib/type_a_worker_harness.py": (
        "def _enforce_budget(",
        "def _contains_forbidden_surface(",
        "forbidden_surfaces",
    ),
    "system/lib/population_lane_metrics.py": (
        "missing_committed_at",
        "applied_count",
        "classify_blockers_and_next_action",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 9 Macro Engines Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _deep_update(base: dict[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def _source_manifest_payload(input_path: Path, public_root: Path) -> dict[str, Any]:
    local = input_path / "source_module_manifest.json"
    if local.is_file():
        return _load_json(local)
    return _load_json(public_root / SPEC.source_manifest_ref)


def _source_manifest_path(input_path: Path, public_root: Path) -> Path:
    local = input_path / "source_module_manifest.json"
    if local.is_file():
        return local
    return public_root / SPEC.source_manifest_ref


def _source_rows(input_path: Path, public_root: Path) -> dict[str, Mapping[str, Any]]:
    rows = _source_manifest_payload(input_path, public_root).get("modules")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("module_id")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("module_id")
    }


def _source_module_text(
    input_path: Path,
    public_root: Path,
    module_id: str,
) -> str | None:
    target = _source_module_path(input_path, public_root, module_id)
    if target is None or not target.is_file():
        return None
    return target.read_text(encoding="utf-8")


def _source_module_path(
    input_path: Path,
    public_root: Path,
    module_id: str,
) -> Path | None:
    manifest_path = _source_manifest_path(input_path, public_root)
    row = _source_rows(input_path, public_root).get(module_id)
    if not isinstance(row, Mapping):
        return None
    rel_path = str(row.get("path") or "")
    if rel_path:
        target = manifest_path.parent / rel_path
    else:
        target_ref = str(row.get("target_ref") or "")
        target_ref = target_ref.removeprefix("microcosm-substrate/")
        target = public_root / target_ref
    return target


def _load_python_source_module(module_path: Path, module_id: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        f"_microcosm_batch9_{module_id}",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load source module {module_id}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _infer_public_root(input_dir: Path) -> Path:
    for parent in (input_dir, *input_dir.parents):
        if (parent / SPEC.source_manifest_ref).is_file():
            return parent
    return input_dir


def _truthy_negative_observation(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() != "pass"
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(value)


_TS_STRING_RE = re.compile(r"['\"]([^'\"]+)['\"]")
_TS_STOPWORDS_RE = re.compile(
    r"const\s+STOPWORDS\s*=\s*new\s+Set\(\s*\[(?P<body>.*?)\]\s*\)",
    re.DOTALL,
)
_TS_NORMALIZE_FILTER_RE = re.compile(
    r"\.filter\(\s*\(token\)\s*=>\s*token\.length\s*>\s*(?P<min>\d+)"
    r"\s*&&\s*!STOPWORDS\.has\(token\)\s*\)",
    re.DOTALL,
)
_TS_NORMALIZE_SLICE_RE = re.compile(r"\.slice\(\s*0\s*,\s*(?P<limit>\d+)\s*\)")
_TS_EDGE_FIELD_MAP_RE = re.compile(
    r"const\s+GENERIC_EDGE_FIELD_MAP:.*?=\s*\[(?P<body>.*?)\]\s*;",
    re.DOTALL,
)
_TS_EDGE_FIELD_ENTRY_RE = re.compile(
    r"\{\s*field:\s*'(?P<field>[^']+)'\s*,\s*relation:\s*'(?P<relation>[^']+)'"
    r"\s*,\s*targetKind:\s*'(?P<target_kind>[^']+)'(?P<rest>[^}]*)\}",
    re.DOTALL,
)


def _source_backed_finance_contract(source_text: str | None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not source_text:
        findings.append(
            finding(
                "BATCH9_FINANCE_SOURCE_BODY_MISSING",
                "finance_news_dedup_cluster_ranker requires the copied financePresentation.ts body.",
                subject_id=FINANCE_MODULE_ID,
            )
        )
        return {"status": "blocked", "findings": findings, "body_in_receipt": False}
    required = (
        "function extractHeadline(",
        "function normalizeHeadlineFingerprint(",
        "export function clusterNewsRows(",
        "clusters.get(normalizedHeadline)",
    )
    missing = [anchor for anchor in required if anchor not in source_text]
    if missing:
        findings.append(
            finding(
                "BATCH9_FINANCE_SOURCE_ANCHOR_MISSING",
                "Copied financePresentation.ts body is missing load-bearing clustering anchors.",
                expected=list(required),
                observed={"missing": missing},
                subject_id=FINANCE_MODULE_ID,
            )
        )
    stopwords_match = _TS_STOPWORDS_RE.search(source_text)
    stopwords = {
        token.strip().lower()
        for token in _TS_STRING_RE.findall(
            stopwords_match.group("body") if stopwords_match else ""
        )
        if token.strip()
    }
    if not stopwords:
        findings.append(
            finding(
                "BATCH9_FINANCE_STOPWORDS_NOT_DERIVED",
                "Copied financePresentation.ts body must expose STOPWORDS for fingerprinting.",
                subject_id=FINANCE_MODULE_ID,
            )
        )
    filter_match = _TS_NORMALIZE_FILTER_RE.search(source_text)
    token_min_length = int(filter_match.group("min")) + 1 if filter_match else 2
    if filter_match is None:
        findings.append(
            finding(
                "BATCH9_FINANCE_TOKEN_FILTER_NOT_DERIVED",
                "Copied financePresentation.ts body must expose the normalizeHeadlineFingerprint token filter.",
                subject_id=FINANCE_MODULE_ID,
            )
        )
    slice_match = _TS_NORMALIZE_SLICE_RE.search(source_text)
    token_limit = int(slice_match.group("limit")) if slice_match else 8
    if slice_match is None:
        findings.append(
            finding(
                "BATCH9_FINANCE_TOKEN_LIMIT_NOT_DERIVED",
                "Copied financePresentation.ts body must expose the normalizeHeadlineFingerprint token limit.",
                subject_id=FINANCE_MODULE_ID,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "stopwords": stopwords,
        "token_min_length": token_min_length,
        "token_limit": token_limit,
        "uses_normalized_headline_key": "clusters.get(normalizedHeadline)" in source_text,
        "findings": findings,
        "body_in_receipt": False,
    }


def _negative_case_observed(
    case_id: str,
    runtime_exercises: Mapping[str, Mapping[str, Any]],
) -> bool:
    check = NEGATIVE_CASE_RUNTIME_CHECKS.get(case_id)
    if check is None:
        return False
    mechanism_id, field, _code = check
    result = runtime_exercises.get(mechanism_id)
    if not isinstance(result, Mapping):
        return False
    if case_id == "worker_forbidden_surface_blocked":
        return result.get(field) == "blocked"
    if case_id == "work_atlas_routed_reason_excluded":
        histogram = result.get(field)
        return (
            isinstance(histogram, Mapping)
            and bool(histogram)
            and "should_not_count" not in histogram
            and result.get("top_reason") != "should_not_count"
        )
    return _truthy_negative_observation(result.get(field))


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    check = NEGATIVE_CASE_RUNTIME_CHECKS.get(case_id)
    if check is None:
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    manifest = _load_json(input_dir / PROBE_MANIFEST_NAME)
    fixtures = manifest.get("positive_fixture")
    if not isinstance(fixtures, Mapping):
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    case_payload = _load_json(input_dir / f"{case_id}.json")
    fixture_patch = case_payload.get("fixture_patch")
    if not isinstance(fixture_patch, Mapping):
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    case_fixtures = _deep_update(deepcopy(dict(fixtures)), fixture_patch)
    public_root = _infer_public_root(input_dir)
    source_bodies = {
        module_id: body
        for module_id in TEXT_BACKED_MODULE_IDS
        for body in [_source_module_text(input_dir, public_root, module_id)]
        if body is not None
    }
    source_paths = {
        module_id: path
        for module_id in PATH_BACKED_MODULE_IDS
        for path in [_source_module_path(input_dir, public_root, module_id)]
        if path is not None
    }
    try:
        runtime_exercises = _run_all_exercises(case_fixtures, source_bodies, source_paths)
    except Exception:
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    _mechanism_id, _field, expected_code = check
    if not _negative_case_observed(case_id, runtime_exercises):
        return {"status": "pass", "error_codes": [], "body_in_receipt": False}
    return {
        "status": "blocked",
        "error_codes": [expected_code],
        "body_in_receipt": False,
    }


def _mechanism_status(
    mechanism: Mapping[str, Any],
    rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    module_ids = [
        str(item)
        for item in mechanism.get("source_module_ids", [])
        if isinstance(item, str) and item
    ]
    missing_modules = [module_id for module_id in module_ids if module_id not in rows]
    return {
        "mechanism_id": str(mechanism.get("mechanism_id") or ""),
        "status": "pass" if not missing_modules else "blocked",
        "source_module_ids": module_ids,
        "evidence_class": mechanism.get("evidence_class"),
        "source_to_target_relation": mechanism.get("source_to_target_relation"),
        "claim_ceiling": mechanism.get("claim_ceiling"),
        "public_exercise": mechanism.get("public_exercise"),
        "negative_case": mechanism.get("negative_case"),
        "missing_modules": missing_modules,
        "body_in_receipt": False,
    }


def _normalize_run_id(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def resolve_lineage(contexts: Mapping[str, Mapping[str, Any]], start_run_id: str) -> dict[str, Any]:
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = start_run_id
    cycle_detected = False
    while current:
        if current in seen:
            cycle_detected = True
            break
        seen.add(current)
        ctx = contexts.get(current, {})
        temporal = ctx.get("temporal_contract")
        temporal = temporal if isinstance(temporal, Mapping) else {}
        validation_status = str(temporal.get("validation_status") or "").lower()
        source = _normalize_run_id(ctx.get("source_run_id") or ctx.get("source"))
        feed = _normalize_run_id(ctx.get("feed_source_run_id") or ctx.get("feed_source"))
        replay = _normalize_run_id(temporal.get("replay_source_run_id"))
        truth = _normalize_run_id(temporal.get("truth_run_id"))
        if validation_status == "feed_replay":
            truth = None
            parent = replay or feed
            relation = "replay_source" if replay else "feed_source"
        elif str(ctx.get("mission_name") or ctx.get("subject_group") or "").lower() in {
            "oracle",
            "audit",
        }:
            parent = source or feed
            relation = "source_run" if source else "feed_source"
        else:
            parent = source or feed or truth
            relation = "source_run" if source else ("feed_source" if feed else "truth_run")
        if parent == current:
            parent = None
            relation = "self"
        chain.append(
            {
                "run_id": current,
                "parent_run_id": parent,
                "relation": relation,
                "truth_run_id": truth,
                "validation_status": validation_status or None,
            }
        )
        current = parent or ""
    return {
        "status": "pass",
        "chain": chain,
        "chain_run_ids": [row["run_id"] for row in chain],
        "cycle_detected": cycle_detected,
        "self_loop_pruned": bool(chain and chain[0]["relation"] == "self"),
    }


def adjudicate_approval(
    request: Mapping[str, Any],
    decision: Mapping[str, Any],
    active_claims: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    approval_id = str(request.get("approval_id") or request.get("id") or "")
    nonce = str(decision.get("nonce") or "")
    claim = active_claims.get(approval_id)
    if claim and claim.get("nonce") != nonce:
        return {
            "status": "refused",
            "ok": False,
            "reason": "preacquired_claim",
            "approval_id": approval_id,
        }
    if request.get("nonce") and request.get("nonce") != nonce:
        return {
            "status": "refused",
            "ok": False,
            "reason": "stale_nonce",
            "approval_id": approval_id,
        }
    action = str(decision.get("decision") or "approve").lower()
    if action not in {"approve", "reject", "veto", "lease"}:
        return {
            "status": "refused",
            "ok": False,
            "reason": "unknown_decision",
            "approval_id": approval_id,
        }
    return {
        "status": "pass",
        "ok": True,
        "approval_id": approval_id,
        "decision": action,
        "overlay": {"decision": action, "source_kind": request.get("source_kind")},
    }


def _write_public_approval_request(repo_root: Path, request: Mapping[str, Any]) -> str:
    approval_id = str(request.get("approval_id") or request.get("id") or "APPROVAL_1")
    requests_dir = repo_root / "state/approvals/requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "approval_request_v1",
        "approval_id": approval_id,
        "source_ref": str(request.get("source_ref") or f"fixture/{approval_id}"),
        "title": str(request.get("title") or f"Fixture approval {approval_id}"),
        "detail": str(request.get("detail") or "Public Microcosm fixture approval."),
        "status": "pending",
        "action_kind": "decide",
        "decision_mode": "overlay_only",
        "severity": str(request.get("severity") or "P2"),
        "metadata": {
            "origin_kind": "batch9_public_fixture",
            "decision_mode": "overlay_only",
            "fixture_nonce": request.get("nonce"),
        },
        "body_in_receipt": False,
    }
    (requests_dir / f"{approval_id}.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return approval_id


def _write_public_approval_claims(
    repo_root: Path,
    active_claims: Mapping[str, Mapping[str, Any]],
    source_state_hashes: Mapping[str, str] | None = None,
) -> None:
    if not active_claims:
        return
    source_state_hashes = source_state_hashes or {}
    claims_path = repo_root / "state/approvals/claims.json"
    claims_path.parent.mkdir(parents=True, exist_ok=True)
    claims: dict[str, dict[str, Any]] = {}
    for approval_id, raw_claim in active_claims.items():
        claim = raw_claim if isinstance(raw_claim, Mapping) else {}
        claims[str(approval_id)] = {
            "approval_id": str(approval_id),
            "source_state_hash": str(
                claim.get("source_state_hash")
                or source_state_hashes.get(str(approval_id))
                or "fixture"
            ),
            "actor_id": str(claim.get("actor_id") or "batch9_preacquired_fixture"),
            "claimed_at": str(claim.get("claimed_at") or "2026-01-01T00:00:00+00:00"),
            "expires_at": str(claim.get("expires_at") or "2999-01-01T00:00:00+00:00"),
            "nonce": str(claim.get("nonce") or "preacquired"),
        }
    claims_path.write_text(
        json.dumps(
            {
                "schema": "approval_claims_v1",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "claims": claims,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def source_backed_approval_adjudication(
    request: Mapping[str, Any],
    decision: Mapping[str, Any],
    active_claims: Mapping[str, Mapping[str, Any]],
    module_path: Path | None,
) -> dict[str, Any]:
    if module_path is None or not module_path.is_file():
        return {
            "status": "blocked",
            "ok": False,
            "approval_id": str(request.get("approval_id") or request.get("id") or ""),
            "preacquired_claim_refused": False,
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
        }
    try:
        module = _load_python_source_module(module_path, APPROVAL_MODULE_ID)
        source_text = module_path.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="batch9-approval-") as tmp:
            repo_root = Path(tmp)
            approval_id = _write_public_approval_request(repo_root, request)
            current = module.list_approvals(repo_root)
            source_state_hashes = {
                str(row.get("approval_id")): str(row.get("source_state_hash") or "")
                for row in current.get("records") or []
                if isinstance(row, Mapping) and row.get("approval_id")
            }
            _write_public_approval_claims(
                repo_root,
                active_claims,
                source_state_hashes,
            )
            decision_result = module.decide_approval(
                repo_root,
                approval_id=approval_id,
                decision=str(decision.get("decision") or "approve"),
                actor_id=str(decision.get("actor_id") or "batch9_fixture"),
                reason=str(decision.get("reason") or "batch9 public fixture"),
            )
    except Exception as exc:
        return {
            "status": "blocked",
            "ok": False,
            "approval_id": str(request.get("approval_id") or request.get("id") or ""),
            "preacquired_claim_refused": False,
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
        }
    error_code = str(decision_result.get("error_code") or "")
    ok = bool(decision_result.get("ok"))
    return {
        "status": "pass" if ok or error_code == "claim_conflict" else "blocked",
        "ok": ok,
        "approval_id": str(request.get("approval_id") or request.get("id") or ""),
        "decision": str(decision.get("decision") or "approve").lower(),
        "decision_error_code": error_code or None,
        "preacquired_claim_refused": error_code == "claim_conflict",
        "source_body_loaded": True,
        "source_contract_status": "pass",
        "source_contract": {
            "module_id": APPROVAL_MODULE_ID,
            "required_callables": [
                "list_approvals",
                "_acquire_claim",
                "decide_approval",
            ],
            "claim_conflict_enforced": (
                "if existing and not _claim_expired(existing):" in source_text
            ),
        },
    }


def build_ast_doc_tree(files: Mapping[str, str]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for path, source in sorted(files.items()):
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            warnings.append(
                {
                    "path": path,
                    "warning": "syntax_error",
                    "lineno": exc.lineno,
                    "message": exc.msg,
                }
            )
            continue
        symbols: list[dict[str, Any]] = []

        def visit(node: ast.AST, parents: tuple[str, ...] = ()) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    kind = "class" if isinstance(child, ast.ClassDef) else "function"
                    qualname = ".".join((*parents, child.name))
                    symbols.append(
                        {
                            "name": child.name,
                            "qualname": qualname,
                            "kind": kind,
                            "lineno": getattr(child, "lineno", None),
                            "end_lineno": getattr(child, "end_lineno", None),
                            "docstring": ast.get_docstring(child) or "",
                        }
                    )
                    visit(child, (*parents, child.name))
                else:
                    visit(child, parents)

        visit(tree)
        entries.append(
            {
                "path": path,
                "module_docstring": ast.get_docstring(tree) or "",
                "symbols": symbols,
                "symbol_count": len(symbols),
            }
        )
    return {
        "status": "pass",
        "files": entries,
        "derivation_warnings": warnings,
        "warning_count": len(warnings),
    }


def _write_runtime_contexts(
    runs_dir: Path,
    contexts: Mapping[str, Any],
) -> None:
    for run_id, ctx in contexts.items():
        if not isinstance(ctx, Mapping):
            continue
        run_dir = runs_dir / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "runtime_context.json").write_text(
            json.dumps(dict(ctx), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _lineage_cycle_detected(module: Any, runs_dir: Path, run_id: str) -> bool:
    context_path = runs_dir / run_id / "runtime_context.json"
    if not context_path.is_file():
        return False
    cache: dict[str, dict[str, Any]] = {}
    primary = module._resolve_primary_lineage(run_id, runs_dir, cache)
    lineage_run_ids = {
        str(item)
        for item in primary.get("lineage_run_ids") or []
        if isinstance(item, str)
    }
    root_run_id = str(primary.get("root_run_id") or "")
    if not root_run_id:
        return False
    root_ctx = module._load_context(root_run_id, runs_dir, cache)
    next_run_id, _relation = module._select_primary_parent(root_run_id, root_ctx)
    return bool(next_run_id and next_run_id in lineage_run_ids)


def source_backed_lineage(
    data: Mapping[str, Any],
    module_path: Path | None,
) -> dict[str, Any]:
    if module_path is None or not module_path.is_file():
        return {
            "status": "blocked",
            "chain_run_ids": [],
            "self_loop_pruned": False,
            "cycle_detected": False,
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
        }
    try:
        module = _load_python_source_module(module_path, LINEAGE_MODULE_ID)
        contexts = data.get("contexts") if isinstance(data.get("contexts"), Mapping) else {}
        start_run_id = str(data.get("start_run_id") or "RUN_SUBJECT")
        start_ctx = contexts.get(start_run_id) if isinstance(contexts.get(start_run_id), Mapping) else {}
        with tempfile.TemporaryDirectory(prefix="batch9-lineage-") as tmp:
            runs_dir = Path(tmp) / "state/runs"
            _write_runtime_contexts(runs_dir, contexts)
            primary_packet = module.build_temporal_lineage(
                start_run_id,
                dict(start_ctx),
                runs_dir,
            )
            primary = (
                primary_packet.get("primary")
                if isinstance(primary_packet, Mapping)
                else {}
            )
            self_primary = (
                module._resolve_primary_lineage("RUN_SELF", runs_dir, {})
                if (runs_dir / "RUN_SELF" / "runtime_context.json").is_file()
                else {}
            )
            cycle_detected = _lineage_cycle_detected(module, runs_dir, "RUN_A")
    except Exception as exc:
        return {
            "status": "blocked",
            "chain_run_ids": [],
            "self_loop_pruned": False,
            "cycle_detected": False,
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
        }
    chain_run_ids = [
        str(item)
        for item in primary.get("lineage_run_ids") or []
        if isinstance(item, str)
    ]
    return {
        "status": "pass" if chain_run_ids else "blocked",
        "chain_run_ids": chain_run_ids,
        "self_loop_pruned": bool(self_primary.get("relation") == "self"),
        "cycle_detected": cycle_detected,
        "source_body_loaded": True,
        "source_contract_status": "pass",
        "source_contract": {
            "module_id": LINEAGE_MODULE_ID,
            "required_callables": [
                "build_temporal_lineage",
                "_resolve_primary_lineage",
                "_select_primary_parent",
            ],
            "truth_parent_supported": hasattr(module, "_select_truth_parent"),
        },
    }


def _entry_qualified_symbols(entry: Mapping[str, Any]) -> list[str]:
    qualified: list[str] = []
    for class_row in entry.get("classes") or []:
        if not isinstance(class_row, Mapping):
            continue
        class_name = str(class_row.get("name") or "")
        if class_name:
            qualified.append(class_name)
        for method_row in class_row.get("methods") or []:
            if not isinstance(method_row, Mapping):
                continue
            method_name = str(method_row.get("name") or "")
            if class_name and method_name:
                qualified.append(f"{class_name}.{method_name}")
    for function_row in entry.get("functions") or []:
        if not isinstance(function_row, Mapping):
            continue
        function_name = str(function_row.get("name") or "")
        if function_name:
            qualified.append(function_name)
    return qualified


def source_backed_ast_doc_tree(
    files: Mapping[str, str],
    module_path: Path | None,
) -> dict[str, Any]:
    if module_path is None or not module_path.is_file():
        return {
            "status": "blocked",
            "symbol_count": 0,
            "syntax_error_gap": False,
            "qualified_symbols": [],
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
        }
    try:
        module = _load_python_source_module(module_path, AST_MODULE_ID)
        qualified_symbols: list[str] = []
        seen_symbols: set[str] = set()
        syntax_error_gap = False
        with tempfile.TemporaryDirectory(prefix="batch9-python-doc-") as tmp:
            repo_root = Path(tmp)
            for rel_path, source in sorted(files.items()):
                file_path = repo_root / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(source, encoding="utf-8")
                entry = module.build_file_entry(file_path, repo_root=repo_root)
                syntax_error_gap = syntax_error_gap or entry.get("status") == "parse_error"
                for symbol in _entry_qualified_symbols(entry):
                    if symbol not in seen_symbols:
                        seen_symbols.add(symbol)
                        qualified_symbols.append(symbol)
    except Exception as exc:
        return {
            "status": "blocked",
            "symbol_count": 0,
            "syntax_error_gap": False,
            "qualified_symbols": [],
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
        }
    return {
        "status": "pass",
        "symbol_count": len(qualified_symbols),
        "syntax_error_gap": syntax_error_gap,
        "qualified_symbols": qualified_symbols,
        "source_body_loaded": True,
        "source_contract_status": "pass",
        "source_contract": {
            "module_id": AST_MODULE_ID,
            "required_callables": ["build_file_entry"],
            "entry_count": len(files),
        },
    }


_STOPWORDS = {
    "a",
    "an",
    "and",
    "amid",
    "as",
    "at",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}


def _headline(row: Mapping[str, Any]) -> str:
    text = str(row.get("text") or row.get("headline") or row.get("title") or "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Headline unavailable"
    for delimiter in (". ", "!", "? ", " - ", " | ", " -- ", "\n"):
        text = text.split(delimiter, 1)[0]
    return text[:140].strip()


def _headline_fingerprint(headline: str, contract: Mapping[str, Any]) -> tuple[str, list[str]]:
    normalized = unicodedata.normalize("NFKD", headline)
    normalized = re.sub(r"[#*_`~]", " ", normalized)
    normalized = "".join(
        char if char.isalnum() or char.isspace() else " "
        for char in normalized
    )
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    stopwords = contract.get("stopwords")
    if not isinstance(stopwords, set):
        stopwords = _STOPWORDS
    token_min_length = int(contract.get("token_min_length") or 2)
    token_limit = int(contract.get("token_limit") or 8)
    tokens = [
        token
        for token in normalized.split()
        if len(token) >= token_min_length and token not in stopwords
    ][:token_limit]
    if len(tokens) >= 3:
        return " ".join(tokens), tokens
    return normalized[:32], tokens


def cluster_news_rows(
    rows: list[Mapping[str, Any]],
    *,
    source_text: str | None = None,
) -> dict[str, Any]:
    contract = _source_backed_finance_contract(source_text)
    if contract["status"] != "pass":
        return {
            "status": "blocked",
            "cluster_count": 0,
            "clusters": [],
            "duplicate_collapsed": False,
            "source_body_loaded": bool(source_text),
            "source_contract_status": contract["status"],
            "source_contract_findings": contract["findings"],
            "body_in_receipt": False,
        }
    clusters: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        headline = _headline(row)
        fingerprint, tokens = _headline_fingerprint(headline, contract)
        if not fingerprint:
            continue
        matched = clusters.get(fingerprint)
        if matched is None:
            matched = clusters[fingerprint] = {
                "id": f"news:{index}:{fingerprint}",
                "headline": headline,
                "normalized_headline": fingerprint,
                "token_set": set(tokens),
                "items": [],
                "score": 0.0,
            }
        matched["items"].append({"headline": headline, "row": dict(row)})
        matched["token_set"] = set(matched["token_set"]).union(tokens)
        confidence = float(row.get("confidence") or 0.0)
        relevance = float(row.get("relevance") or 0.0)
        matched["score"] = len(matched["items"]) * 3 + max(
            float(matched["score"]),
            confidence + relevance,
        )
    output = []
    for cluster in clusters.values():
        output.append(
            {
                "id": cluster["id"],
                "headline": cluster["headline"],
                "normalized_headline": cluster["normalized_headline"],
                "item_count": len(cluster["items"]),
                "score": cluster["score"],
                "tokens": sorted(cluster["token_set"]),
            }
        )
    output.sort(key=lambda row: (-row["score"], row["headline"]))
    return {
        "status": "pass",
        "cluster_count": len(output),
        "clusters": output,
        "duplicate_collapsed": any(row["item_count"] >= 2 for row in output),
        "source_body_loaded": True,
        "source_contract_status": contract["status"],
        "source_contract": {
            "stopword_count": len(contract["stopwords"]),
            "token_min_length": contract["token_min_length"],
            "token_limit": contract["token_limit"],
            "uses_normalized_headline_key": contract["uses_normalized_headline_key"],
        },
    }


def source_backed_dependency_pin_audit(
    requirements: list[str],
    installed: Mapping[str, str],
    module_path: Path | None,
) -> dict[str, Any]:
    empty_buckets: dict[str, list[dict[str, Any]]] = {
        "ok": [],
        "drifted": [],
        "missing": [],
        "unparseable": [],
    }
    if module_path is None or not module_path.is_file():
        return {
            "status": "blocked",
            "buckets": empty_buckets,
            "drifted_count": 0,
            "missing_count": 0,
            "unparseable_count": 0,
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
        }
    try:
        module = _load_python_source_module(module_path, DEPENDENCY_PIN_MODULE_ID)
        parse_requirements = getattr(module, "parse_requirements")
        evaluate_pins = getattr(module, "evaluate")
        with tempfile.TemporaryDirectory(prefix="batch9-pin-drift-") as tmp:
            requirements_path = Path(tmp) / "requirements.txt"
            requirements_path.write_text("\n".join(requirements) + "\n", encoding="utf-8")
            pinned = parse_requirements(requirements_path)
            ok, drifted, missing, unparseable = evaluate_pins(
                pinned,
                {str(name): str(version) for name, version in installed.items()},
            )
    except Exception as exc:
        return {
            "status": "blocked",
            "buckets": empty_buckets,
            "drifted_count": 0,
            "missing_count": 0,
            "unparseable_count": 0,
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
        }

    buckets = {
        "ok": [
            {"name": name, "specifier": specifier, "version": version}
            for name, specifier, version in ok
        ],
        "drifted": [
            {"name": name, "specifier": specifier, "version": version}
            for name, specifier, version in drifted
        ],
        "missing": [
            {"name": name, "specifier": specifier}
            for name, specifier in missing
        ],
        "unparseable": [
            {"name": name, "specifier": specifier, "reason": reason}
            for name, specifier, reason in unparseable
        ],
    }
    return {
        "status": "pass",
        "buckets": buckets,
        "drifted_count": len(buckets["drifted"]),
        "missing_count": len(buckets["missing"]),
        "unparseable_count": len(buckets["unparseable"]),
        "source_body_loaded": True,
        "source_contract_status": "pass",
        "source_contract": {
            "module_id": DEPENDENCY_PIN_MODULE_ID,
            "required_callables": ["parse_requirements", "evaluate"],
            "parsed_requirement_count": len(pinned),
        },
    }


def _source_backed_mission_graph_contract(source_text: str | None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not source_text:
        findings.append(
            finding(
                "BATCH9_MISSION_GRAPH_SOURCE_BODY_MISSING",
                "mission_graph_topological_compiler requires the copied graph.py body.",
                subject_id=MISSION_GRAPH_MODULE_ID,
            )
        )
        return {"status": "blocked", "findings": findings, "body_in_receipt": False}
    required = (
        "def compile_graph_snapshot(",
        'target_group = getattr(target_node, "group", "unknown")',
        "waves.append(sorted(current_wave))",
    )
    missing = [anchor for anchor in required if anchor not in source_text]
    if missing:
        findings.append(
            finding(
                "BATCH9_MISSION_GRAPH_SOURCE_ANCHOR_MISSING",
                "Copied graph.py body is missing load-bearing mission graph anchors.",
                expected=list(required),
                observed={"missing": missing},
                subject_id=MISSION_GRAPH_MODULE_ID,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "findings": findings,
        "group_closure_enabled": (
            "grp == target_group" in source_text
            and 'target_group != "unknown"' in source_text
        ),
        "upstream_dependency_walk_enabled": (
            "if dep not in scope:" in source_text and "queue.append(dep)" in source_text
        ),
        "sorted_waves": "waves.append(sorted(current_wave))" in source_text,
        "body_in_receipt": False,
    }


def compile_mission_graph(
    nodes: list[Mapping[str, Any]],
    target_id: str,
    *,
    source_text: str | None = None,
) -> dict[str, Any]:
    contract = _source_backed_mission_graph_contract(source_text)
    if contract["status"] != "pass":
        return {
            "status": "blocked",
            "nodes": [],
            "edges": [],
            "waves": [],
            "topology_error": "source_contract_blocked",
            "cycle_nodes": [],
            "source_body_loaded": bool(source_text),
            "source_contract_status": contract["status"],
            "source_contract_findings": contract["findings"],
            "body_in_receipt": False,
        }
    by_id = {str(node.get("id")): node for node in nodes if node.get("id")}
    if target_id not in by_id:
        return {
            "status": "blocked",
            "nodes": [],
            "edges": [],
            "waves": [],
            "topology_error": f"Target node '{target_id}' not found.",
            "source_body_loaded": True,
            "source_contract_status": contract["status"],
            "source_contract": {
                "module_id": MISSION_GRAPH_MODULE_ID,
                "group_closure_enabled": contract["group_closure_enabled"],
                "upstream_dependency_walk_enabled": (
                    contract["upstream_dependency_walk_enabled"]
                ),
                "sorted_waves": contract["sorted_waves"],
            },
        }
    target_group = by_id[target_id].get("group")
    if contract["group_closure_enabled"]:
        scope: set[str] = {
            node_id
            for node_id, node in by_id.items()
            if target_group and node.get("group") == target_group
        } or {target_id}
    else:
        scope = {target_id}
    if contract["upstream_dependency_walk_enabled"]:
        queue = deque(scope)
        while queue:
            node_id = queue.popleft()
            for dep in by_id.get(node_id, {}).get("dependencies", []) or []:
                dep_id = str(dep)
                if dep_id in by_id and dep_id not in scope:
                    scope.add(dep_id)
                    queue.append(dep_id)
    edges = [
        {"source": str(dep), "target": node_id}
        for node_id in sorted(scope)
        for dep in by_id[node_id].get("dependencies", []) or []
        if str(dep) in scope
    ]
    indegree = {node_id: 0 for node_id in scope}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        outgoing[edge["source"]].append(edge["target"])
        indegree[edge["target"]] += 1
    ready = sorted(node_id for node_id, value in indegree.items() if value == 0)
    waves: list[list[str]] = []
    seen: set[str] = set()
    while ready:
        wave = ready
        waves.append(sorted(wave) if contract["sorted_waves"] else wave)
        next_ready: list[str] = []
        for node_id in wave:
            seen.add(node_id)
            for target in outgoing[node_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    next_ready.append(target)
        ready = sorted(next_ready)
    cycle_nodes = sorted(scope - seen)
    return {
        "status": "pass" if not cycle_nodes else "blocked",
        "nodes": sorted(scope),
        "edges": edges,
        "waves": waves,
        "topology_error": "cycle_detected" if cycle_nodes else None,
        "cycle_nodes": cycle_nodes,
        "source_body_loaded": True,
        "source_contract_status": contract["status"],
        "source_contract": {
            "module_id": MISSION_GRAPH_MODULE_ID,
            "group_closure_enabled": contract["group_closure_enabled"],
            "upstream_dependency_walk_enabled": contract["upstream_dependency_walk_enabled"],
            "sorted_waves": contract["sorted_waves"],
        },
    }


def _canonical_pkg(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_req_line(line: str) -> tuple[str, str] | None:
    raw = line.split("#", 1)[0].strip()
    if not raw or raw.startswith("-r") or raw.startswith("git+"):
        return None
    match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*([<>=!~].*)?$", raw)
    if not match:
        return ("", raw)
    return (_canonical_pkg(match.group(1)), (match.group(2) or "").strip())


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value)[:4])


def _specifier_ok(version: str, specifier: str) -> bool:
    if not specifier:
        return True
    current = _version_tuple(version)
    for piece in [part.strip() for part in specifier.split(",") if part.strip()]:
        match = re.match(r"(==|>=|<=|>|<)\s*([0-9][A-Za-z0-9_.-]*)", piece)
        if not match:
            return False
        op, expected = match.groups()
        expected_tuple = _version_tuple(expected)
        if op == "==" and current != expected_tuple:
            return False
        if op == ">=" and current < expected_tuple:
            return False
        if op == "<=" and current > expected_tuple:
            return False
        if op == ">" and current <= expected_tuple:
            return False
        if op == "<" and current >= expected_tuple:
            return False
    return True


def audit_dependency_pins(requirements: list[str], installed: Mapping[str, str]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "ok": [],
        "drifted": [],
        "missing": [],
        "unparseable": [],
    }
    installed_map = {_canonical_pkg(name): str(version) for name, version in installed.items()}
    for line in requirements:
        parsed = _parse_req_line(line)
        if parsed is None:
            continue
        name, specifier = parsed
        if not name:
            buckets["unparseable"].append({"line": line, "reason": "parse_failed"})
            continue
        version = installed_map.get(name)
        if version is None:
            buckets["missing"].append({"name": name, "specifier": specifier})
        elif _specifier_ok(version, specifier):
            buckets["ok"].append({"name": name, "version": version, "specifier": specifier})
        else:
            buckets["drifted"].append({"name": name, "version": version, "specifier": specifier})
    return {
        "status": "pass",
        "buckets": buckets,
        "drifted_count": len(buckets["drifted"]),
        "missing_count": len(buckets["missing"]),
        "unparseable_count": len(buckets["unparseable"]),
    }


_CONFIG_AUTHORITY_ROW_REQUIRED: tuple[str, ...] = (
    "config_id",
    "canonical_label",
    "class",
    "authority_owner",
    "authority_path",
    "loader",
    "writer",
    "governing_standard",
    "schema_or_validator",
    "stored_default_current_effective_semantics",
    "context_dimensions",
    "override_precedence",
    "mutability_class",
    "safe_edit_gate",
    "consumer_edges",
    "dependency_edges",
    "projection_surfaces",
    "frontend_routes",
    "agent_entry_routes",
    "diagnostics",
    "redaction_policy",
    "last_verified",
    "effective_trace",
)
_CONFIG_AUTHORITY_TRACE_REQUIRED: tuple[str, ...] = (
    "effective_value_or_redacted_summary",
    "winning_source",
    "authority_path",
    "override_chain",
    "context_used",
    "validator",
    "consumers",
    "mutation_allowed",
    "mutation_blocked_reason",
    "rollback_route",
    "refresh_or_rebuild_route",
)


def _config_authority_as_list(value: Any, *, default: list[str] | None = None) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if value is None:
        return list(default or [])
    return [value]


def _config_authority_macro_payload(
    payload: Mapping[str, Any],
    known_roots: set[str],
) -> dict[str, Any]:
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    normalized_rows: list[dict[str, Any]] = []
    for index, row_value in enumerate(rows):
        if not isinstance(row_value, Mapping):
            row_value = {"config_id": f"rows[{index}]", "class": "invalid_fixture_row"}
        row = dict(row_value)
        config_id = str(row.get("config_id") or f"rows[{index}]")
        root = str(row.get("authority_path") or row.get("root") or f"config/{config_id}.json")
        row_class = str(
            row.get("class")
            or row.get("authority_class")
            or row.get("row_class")
            or "source_config"
        )
        trace = (
            row.get("effective_trace")
            if isinstance(row.get("effective_trace"), Mapping)
            else {}
        )
        mutation_allowed = bool(trace.get("mutation_allowed"))
        normalized_trace = {
            "effective_value_or_redacted_summary": str(
                trace.get("effective_value_or_redacted_summary")
                or row.get("stored_default_current_effective_semantics")
                or "public-safe configuration row"
            ),
            "winning_source": str(trace.get("winning_source") or root or config_id),
            "authority_path": str(trace.get("authority_path") or root),
            "override_chain": _config_authority_as_list(
                trace.get("override_chain"),
                default=[root],
            ),
            "context_used": _config_authority_as_list(
                trace.get("context_used"),
                default=["public_fixture"],
            ),
            "validator": str(
                trace.get("validator")
                or row.get("schema_or_validator")
                or "validate_config_authority_registry"
            ),
            "consumers": _config_authority_as_list(
                trace.get("consumers"),
                default=_config_authority_as_list(row.get("consumer_edges")),
            ),
            "mutation_allowed": mutation_allowed,
            "mutation_blocked_reason": str(
                trace.get("mutation_blocked_reason")
                or ("" if mutation_allowed else "read_only_public_fixture")
            ),
            "rollback_route": str(trace.get("rollback_route") or "restore_public_fixture"),
            "refresh_or_rebuild_route": str(
                trace.get("refresh_or_rebuild_route")
                or "refresh_batch9_macro_engines_capsule_fixture"
            ),
        }
        normalized_rows.append(
            {
                "config_id": config_id,
                "canonical_label": str(row.get("canonical_label") or config_id),
                "class": row_class,
                "authority_owner": str(row.get("authority_owner") or "microcosm_public_fixture"),
                "authority_path": root,
                "loader": str(row.get("loader") or "batch9_macro_engines_capsule_fixture_loader"),
                "writer": str(row.get("writer") or "owner_controlled_source_authority"),
                "governing_standard": str(
                    row.get("governing_standard")
                    or "codex/standards/std_config_authority_registry.json"
                ),
                "schema_or_validator": str(
                    row.get("schema_or_validator") or "validate_config_authority_registry"
                ),
                "stored_default_current_effective_semantics": str(
                    row.get("stored_default_current_effective_semantics")
                    or "public-safe configuration row"
                ),
                "context_dimensions": _config_authority_as_list(
                    row.get("context_dimensions"),
                    default=["public_fixture"],
                ),
                "override_precedence": _config_authority_as_list(
                    row.get("override_precedence"),
                    default=[root],
                ),
                "mutability_class": str(row.get("mutability_class") or "read_only_source"),
                "safe_edit_gate": str(row.get("safe_edit_gate") or "owner_claim_required"),
                "consumer_edges": _config_authority_as_list(row.get("consumer_edges")),
                "dependency_edges": _config_authority_as_list(row.get("dependency_edges")),
                "projection_surfaces": _config_authority_as_list(row.get("projection_surfaces")),
                "frontend_routes": _config_authority_as_list(row.get("frontend_routes")),
                "agent_entry_routes": _config_authority_as_list(row.get("agent_entry_routes")),
                "diagnostics": _config_authority_as_list(row.get("diagnostics")),
                "redaction_policy": str(row.get("redaction_policy") or "public_safe_metadata_only"),
                "last_verified": str(row.get("last_verified") or "2026-06-05T00:00:00Z"),
                "effective_trace": normalized_trace,
            }
        )
    diagnostics = [
        item
        for row in normalized_rows
        for item in row.get("diagnostics", [])
        if isinstance(item, Mapping)
    ]
    return {
        "kind": "config_authority_registry",
        "schema_version": "config_authority_registry_v1",
        "generated_at": str(payload.get("generated_at") or "2026-06-05T00:00:00Z"),
        "row_count": len(normalized_rows),
        "diagnostic_count": len(diagnostics),
        "known_roots": sorted(known_roots),
        "api_routes": _config_authority_as_list(payload.get("api_routes")),
        "rows": normalized_rows,
    }


def _config_authority_standard_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    row_classes = {
        str(row.get("class"))
        for row in rows
        if isinstance(row, Mapping) and str(row.get("class") or "")
    }
    row_classes.update(
        {
            "generated_projection_or_cache",
            "host_local_adapter_config",
            "secret_or_private_config",
            "source_config",
        }
    )
    return {
        "row_classes": sorted(row_classes),
        "row_contract_required": list(_CONFIG_AUTHORITY_ROW_REQUIRED),
        "effective_trace_required": list(_CONFIG_AUTHORITY_TRACE_REQUIRED),
    }


def source_backed_config_authority_audit(
    payload: Mapping[str, Any],
    known_roots: set[str],
    module_path: Path | None,
) -> dict[str, Any]:
    if module_path is None or not module_path.is_file():
        return {
            "status": "blocked",
            "row_count": 0,
            "findings": [{"code": "source_module_missing"}],
            "warning_count": 0,
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
        }
    try:
        module = _load_python_source_module(module_path, CONFIG_AUTHORITY_MODULE_ID)
        validate_registry = getattr(module, "validate_config_authority_registry")
        normalized_payload = _config_authority_macro_payload(payload, known_roots)
        with tempfile.TemporaryDirectory(prefix="batch9-config-authority-") as tmp:
            repo_root = Path(tmp)
            standard_path = repo_root / "codex/standards/std_config_authority_registry.json"
            standard_path.parent.mkdir(parents=True, exist_ok=True)
            standard_path.write_text(
                json.dumps(
                    _config_authority_standard_contract(normalized_payload),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            validation = validate_registry(normalized_payload, repo_root=repo_root)
    except Exception as exc:
        return {
            "status": "blocked",
            "row_count": 0,
            "findings": [
                {
                    "code": "source_contract_exception",
                    "exception_type": type(exc).__name__,
                }
            ],
            "warning_count": 0,
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
        }

    findings = validation.get("errors") if isinstance(validation.get("errors"), list) else []
    warnings = validation.get("warnings") if isinstance(validation.get("warnings"), list) else []
    return {
        "status": "pass" if bool(validation.get("valid")) and not findings else "blocked",
        "row_count": int(validation.get("row_count") or 0),
        "findings": list(findings),
        "warning_count": len(warnings),
        "source_body_loaded": True,
        "source_contract_status": "pass",
        "source_contract": {
            "module_id": CONFIG_AUTHORITY_MODULE_ID,
            "required_callables": ["validate_config_authority_registry"],
            "normalized_kind": "config_authority_registry",
            "standard_row_class_count": len(
                _config_authority_standard_contract(
                    _config_authority_macro_payload(payload, known_roots)
                )["row_classes"]
            ),
        },
    }


EDGE_FIELD_MAP = {
    "top_dependencies": ("depends_on", "paper_module", False),
    "dependencies": ("depends_on", "paper_module", False),
    "top_dependents": ("depended_on_by", "paper_module", False),
    "dependents": ("depended_on_by", "paper_module", False),
    "related_principles": ("governed_by", "principle", False),
    "principle_edges": ("related_to", "principle", True),
    "top_principle_edges": ("related_to", "principle", True),
    "related_mechanisms": ("implemented_by", "mechanism", False),
    "mechanism_edges": ("implemented_by", "mechanism", True),
    "top_mechanism_edges": ("implemented_by", "mechanism", True),
    "related_concepts": ("related_to", "concept", False),
    "concept_edges": ("related_to", "concept", True),
    "top_concept_edges": ("related_to", "concept", True),
    "related_principles_by_axiom": ("compresses", "principle", False),
    "code_loci": ("implements", "code_locus", False),
}
ALLOWED_RELATIONS = {
    "depends_on",
    "depended_on_by",
    "governed_by",
    "implemented_by",
    "related_to",
    "compresses",
    "implements",
}


def _source_backed_edge_field_map(source_text: str | None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not source_text:
        findings.append(
            finding(
                "BATCH9_HETEROGENEOUS_EDGE_SOURCE_BODY_MISSING",
                "heterogeneous_graph_edge_extractor requires the copied RootNavigator.tsx body.",
                subject_id=HETEROGENEOUS_MODULE_ID,
            )
        )
        return {
            "status": "blocked",
            "edge_field_map": EDGE_FIELD_MAP,
            "field_count": len(EDGE_FIELD_MAP),
            "findings": findings,
            "body_in_receipt": False,
        }

    required = (
        "const GENERIC_EDGE_FIELD_MAP",
        "function normalizeEdgeRelationToken(",
        "function extractGenericEdges(",
    )
    missing = [anchor for anchor in required if anchor not in source_text]
    if missing:
        findings.append(
            finding(
                "BATCH9_HETEROGENEOUS_EDGE_SOURCE_ANCHOR_MISSING",
                "Copied RootNavigator.tsx body is missing load-bearing relation extraction anchors.",
                expected=list(required),
                observed={"missing": missing},
                subject_id=HETEROGENEOUS_MODULE_ID,
            )
        )

    block = _TS_EDGE_FIELD_MAP_RE.search(source_text)
    parsed: dict[str, tuple[str, str, bool]] = {}
    if block is None:
        findings.append(
            finding(
                "BATCH9_HETEROGENEOUS_EDGE_MAP_NOT_DERIVED",
                "Copied RootNavigator.tsx body must expose GENERIC_EDGE_FIELD_MAP.",
                subject_id=HETEROGENEOUS_MODULE_ID,
            )
        )
    else:
        for match in _TS_EDGE_FIELD_ENTRY_RE.finditer(block.group("body")):
            parsed[match.group("field")] = (
                match.group("relation"),
                match.group("target_kind"),
                "takeRelationFromRow: true" in match.group("rest"),
            )

    if not parsed:
        parsed = dict(EDGE_FIELD_MAP)
    for required_field in ("top_dependencies", "principle_edges", "code_loci"):
        if required_field not in parsed:
            findings.append(
                finding(
                    "BATCH9_HETEROGENEOUS_EDGE_FIELD_MISSING",
                    "Copied RootNavigator.tsx relation map must include the required public edge field.",
                    subject_id=required_field,
                )
            )

    return {
        "status": "pass" if not findings else "blocked",
        "edge_field_map": parsed,
        "field_count": len(parsed),
        "findings": findings,
        "body_in_receipt": False,
    }


def _source_normalize_edge_relation(relation: str, source_text: str | None) -> str:
    token = relation.strip().lower()
    if not token:
        return "related_to"
    if source_text and "function normalizeEdgeRelationToken(" in source_text:
        if token in {"implements", "implemented_by"}:
            return token
        if token in {"grounds", "instantiated_by", "refines"}:
            return "related_to"
        if token in {"depends_on", "depended_on_by"}:
            return token
        if token in {"governs", "governed_by"}:
            return token
        if token in {"compresses", "compressed_by"}:
            return "compresses"
        if token in {"sources", "evidence", "related_to", "explains"}:
            return token
        return "related_to"
    return token if token in ALLOWED_RELATIONS else "related_to"


def extract_heterogeneous_edges(
    row: Mapping[str, Any],
    source_id: str,
    source_text: str | None = None,
) -> dict[str, Any]:
    source_contract = _source_backed_edge_field_map(source_text)
    edge_field_map = source_contract["edge_field_map"]
    edges: list[dict[str, Any]] = []
    normalized_relations = 0
    for field, (default_relation, target_kind, take_relation) in edge_field_map.items():
        values = row.get(field)
        if not isinstance(values, list):
            continue
        for index, item in enumerate(values):
            relation = default_relation
            relation_from_row = False
            target = item
            if isinstance(item, Mapping):
                target = item.get("target") or item.get("id") or item.get("path")
                raw_relation = item.get("relation")
                if take_relation and raw_relation:
                    raw_relation_token = str(raw_relation).strip().lower()
                    relation = _source_normalize_edge_relation(raw_relation_token, source_text)
                    relation_from_row = True
                    if relation != raw_relation_token:
                        normalized_relations += 1
            if not target:
                continue
            normalized_relation = _source_normalize_edge_relation(str(relation), source_text)
            if normalized_relation != relation:
                relation = normalized_relation
                if not relation_from_row:
                    normalized_relations += 1
            edges.append(
                {
                    "id": f"{source_id}:{field}:{index}",
                    "source": source_id,
                    "target": str(target),
                    "target_kind": target_kind,
                    "relation": relation,
                    "source_field": field,
                }
            )
    return {
        "status": "pass" if source_contract["status"] == "pass" else "blocked",
        "edges": edges,
        "edge_count": len(edges),
        "normalized_relation_count": normalized_relations,
        "source_body_loaded": source_text is not None,
        "source_contract_status": source_contract["status"],
        "source_contract_findings": source_contract["findings"],
        "source_contract": {
            "module_id": HETEROGENEOUS_MODULE_ID,
            "required_anchors": [
                "GENERIC_EDGE_FIELD_MAP",
                "normalizeEdgeRelationToken",
                "extractGenericEdges",
            ],
            "derived_field_count": source_contract["field_count"],
            "top_dependencies_relation": edge_field_map.get(
                "top_dependencies",
                ("", "", False),
            )[0],
            "principle_edges_take_relation_from_row": edge_field_map.get(
                "principle_edges",
                ("", "", False),
            )[2],
        },
    }


def aggregate_work_atlas_cell(marks: list[Mapping[str, Any]]) -> dict[str, Any]:
    return _aggregate_work_atlas_cell(marks, count_route_reasons_when_unrouted=True)


def _aggregate_work_atlas_cell(
    marks: list[Mapping[str, Any]],
    *,
    count_route_reasons_when_unrouted: bool,
) -> dict[str, Any]:
    overlays = Counter()
    type_count = Counter()
    reason_count = Counter()
    reason_kind: dict[str, str] = {}
    for mark in marks:
        overlay = mark.get("overlays") if isinstance(mark.get("overlays"), Mapping) else {}
        for key in ("unrouted", "blocked", "stale", "signoff_required", "high_unlock"):
            if overlay.get(key):
                overlays[key] += 1
        work_type = str(mark.get("work_item_type") or "unknown")
        type_count[work_type] += 1
        if not count_route_reasons_when_unrouted or overlay.get("unrouted"):
            explanation = (
                mark.get("route_explanation")
                if isinstance(mark.get("route_explanation"), Mapping)
                else {}
            )
            reason = str(explanation.get("route_reason") or "unknown_reason")
            reason_count[reason] += 1
            if explanation.get("reason_kind"):
                reason_kind[reason] = str(explanation.get("reason_kind"))
    count = len(marks)
    cols = max(1, math.ceil(math.sqrt(count * 1.6))) if count else 0
    rows = max(1, math.ceil(count / cols)) if count else 0
    top_type = type_count.most_common(1)[0][0] if type_count else None
    top_reason = reason_count.most_common(1)[0][0] if reason_count else None
    return {
        "status": "pass",
        "count": count,
        "overlays": dict(overlays),
        "type_histogram": dict(type_count),
        "route_reason_histogram": dict(reason_count),
        "top_type": top_type,
        "top_reason": top_reason,
        "top_reason_kind": reason_kind.get(top_reason) if top_reason else None,
        "grid": {"cols": cols, "rows": rows},
    }


def _source_backed_work_atlas_contract(source_text: str | None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not source_text:
        findings.append({"code": "source_body_missing", "module_id": WORK_ATLAS_MODULE_ID})
        return {
            "status": "blocked",
            "findings": findings,
            "source_body_loaded": False,
            "unrouted_route_reason_gate": False,
        }
    required = (
        "function aggregateCell(",
        "const reasonCount = new Map<string, number>();",
        "if (o.unrouted) {",
        "routeReasonHistogram: Object.fromEntries(reasonCount)",
        "function cellMarksPerRow(",
    )
    missing = [anchor for anchor in required if anchor not in source_text]
    if missing:
        findings.append(
            {
                "code": "work_atlas_source_anchor_missing",
                "module_id": WORK_ATLAS_MODULE_ID,
                "missing": missing,
            }
        )
    return {
        "status": "pass" if not findings else "blocked",
        "findings": findings,
        "source_body_loaded": True,
        "unrouted_route_reason_gate": "if (o.unrouted) {" in source_text,
    }


def source_backed_aggregate_work_atlas_cell(
    marks: list[Mapping[str, Any]],
    source_text: str | None,
) -> dict[str, Any]:
    contract = _source_backed_work_atlas_contract(source_text)
    aggregate = _aggregate_work_atlas_cell(
        marks,
        count_route_reasons_when_unrouted=bool(contract["unrouted_route_reason_gate"]),
    )
    return {
        **aggregate,
        "status": "pass" if contract["status"] == "pass" else "blocked",
        "source_body_loaded": contract["source_body_loaded"],
        "source_contract_status": contract["status"],
        "source_contract_findings": contract["findings"],
        "source_contract": {
            "module_id": WORK_ATLAS_MODULE_ID,
            "required_anchors": [
                "function aggregateCell(",
                "if (o.unrouted) {",
                "routeReasonHistogram: Object.fromEntries(reasonCount)",
                "function cellMarksPerRow(",
            ],
            "unrouted_route_reason_gate": contract["unrouted_route_reason_gate"],
        },
    }


def admission_decision(quote: Mapping[str, Any], policy: str) -> dict[str, Any]:
    policy_value = str(policy or "auto").lower()
    if policy_value not in {"auto", "warn", "off"}:
        raise ValueError("unknown_policy")
    admission = quote.get("host_pressure_admission")
    admission = admission if isinstance(admission, Mapping) else {}
    decision_body = admission.get("admission")
    decision_body = decision_body if isinstance(decision_body, Mapping) else {}
    if policy_value == "off" or admission.get("status") != "available":
        return {"status": "pass", "allow": True, "result": "allow"}
    recommendation = str(quote.get("recommendation") or "")
    decision = str(admission.get("decision") or decision_body.get("decision") or "")
    should_block = bool(admission.get("should_block_run")) and (
        decision == "require_operator_override" or recommendation.startswith("queue_")
    )
    if not should_block:
        return {"status": "pass", "allow": True, "result": "allow"}
    if policy_value == "warn":
        return {"status": "warn_only", "allow": True, "blocked_result": decision}
    return {
        "status": "blocked",
        "allow": False,
        "result": "explicit_override_required"
        if decision == "require_operator_override"
        else "queue_until_pressure_clears",
    }


def source_backed_admission_decision(
    quote: Mapping[str, Any],
    policy: str,
    source_path: Path | None,
) -> dict[str, Any]:
    if source_path is None or not source_path.is_file():
        return {
            "status": "blocked",
            "decision_status": "source_module_missing",
            "allow": False,
            "result": "source_module_missing",
            "auto_policy_blocked": False,
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "body_in_receipt": False,
        }
    try:
        module = _load_python_source_module(source_path, HOST_PRESSURE_MODULE_ID)
        source_text = source_path.read_text(encoding="utf-8")
        builder = getattr(module, "build_admission_consumer_decision")
        decision = builder(
            quote,
            policy=policy,
            consumer_id="batch9_host_pressure_admission_decision_gate",
            action_class="batch9_public_fixture_probe",
            block_recommendations=(),
            override_hint="public fixture proof only; no live host override",
        )
    except Exception as exc:
        return {
            "status": "blocked",
            "decision_status": "source_module_execution_failed",
            "allow": False,
            "result": type(exc).__name__,
            "auto_policy_blocked": False,
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
            "body_in_receipt": False,
        }
    required_anchors = (
        "ADMISSION_POLICY_VALUES",
        "def normalize_admission_policy(",
        "def build_admission_consumer_decision(",
        'or "summary" in recommendation',
        'return "summary_first"',
    )
    missing_anchors = [anchor for anchor in required_anchors if anchor not in source_text]
    source_contract_status = "pass" if not missing_anchors else "blocked"
    source_contract_findings = [
        {
            "code": "host_pressure_source_anchor_missing",
            "module_id": HOST_PRESSURE_MODULE_ID,
            "missing": missing_anchors,
        }
    ] if missing_anchors else []
    return {
        "status": "pass" if source_contract_status == "pass" else "blocked",
        "decision_status": decision.get("status"),
        "allow": decision.get("allow") is True,
        "result": decision.get("result"),
        "auto_policy_blocked": decision.get("allow") is False,
        "source_body_loaded": True,
        "source_contract_status": source_contract_status,
        "source_contract_findings": source_contract_findings,
        "source_contract": {
            "schema": getattr(module, "ADMISSION_CONSUMER_SCHEMA", None),
            "policy_values": list(getattr(module, "ADMISSION_POLICY_VALUES", ())),
            "tempfail_exit_code": decision.get("tempfail_exit_code"),
            "new_work_admitted": decision.get("new_work_admitted"),
            "new_heavy_work_launched": decision.get("new_heavy_work_launched"),
            "summary_recommendation_blocks": (
                'or "summary" in recommendation' in source_text
            ),
        },
        "body_in_receipt": False,
    }


def _write_doctrine_fixture_repo(repo_root: Path, payload: Mapping[str, Any]) -> None:
    doctrine_root = repo_root / "codex/doctrine"
    mechanisms_dir = doctrine_root / "mechanisms"
    concepts_dir = doctrine_root / "concepts"
    mechanisms_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir.mkdir(parents=True, exist_ok=True)
    for mechanism in payload.get("mechanisms") or []:
        if not isinstance(mechanism, Mapping):
            continue
        mechanism_id = str(mechanism.get("id") or "").strip()
        if not mechanism_id:
            continue
        (mechanisms_dir / f"{mechanism_id}.json").write_text(
            json.dumps(dict(mechanism), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    for concept in payload.get("concepts") or []:
        if not isinstance(concept, Mapping):
            continue
        concept_id = str(concept.get("id") or "").strip()
        if not concept_id:
            continue
        (concepts_dir / f"{concept_id}.json").write_text(
            json.dumps(dict(concept), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    system_map = {
        "identity": {"active_family": "09"},
        "principles": [
            dict(principle)
            for principle in payload.get("principles") or []
            if isinstance(principle, Mapping)
        ],
    }
    (doctrine_root / "system_map.json").write_text(
        json.dumps(system_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def source_backed_doctrine_enrichment(
    payload: Mapping[str, Any],
    rel_path: str,
    module_path: Path | None,
) -> dict[str, Any]:
    if module_path is None or not module_path.is_file():
        return {
            "status": "blocked",
            "mechanisms": [],
            "concepts": [],
            "principles": [],
            "counts": {
                "mechanisms": 0,
                "concepts": 0,
                "principles": 0,
                "related_files": 0,
            },
            "empty_envelope": True,
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
        }
    try:
        module = _load_python_source_module(module_path, DOCTRINE_MODULE_ID)
        with tempfile.TemporaryDirectory(prefix="batch9-doctrine-") as tmp:
            repo_root = Path(tmp)
            _write_doctrine_fixture_repo(repo_root, payload)
            service = module.DoctrineEnrichmentService(repo_root)
            envelope = service.get_file_doctrine(rel_path)
    except Exception as exc:
        return {
            "status": "blocked",
            "mechanisms": [],
            "concepts": [],
            "principles": [],
            "counts": {
                "mechanisms": 0,
                "concepts": 0,
                "principles": 0,
                "related_files": 0,
            },
            "empty_envelope": True,
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
        }
    counts = envelope.get("counts") if isinstance(envelope.get("counts"), Mapping) else {}
    empty_envelope = not bool(envelope.get("mechanisms"))
    return {
        "status": "blocked" if empty_envelope else "pass",
        "mechanisms": envelope.get("mechanisms") or [],
        "concepts": envelope.get("concepts") or [],
        "principles": envelope.get("principles") or [],
        "counts": {
            "mechanisms": int(counts.get("mechanisms") or 0),
            "concepts": int(counts.get("concepts") or 0),
            "principles": int(counts.get("principles") or 0),
            "related_files": int(counts.get("related_files") or 0),
        },
        "empty_envelope": empty_envelope,
        "source_body_loaded": True,
        "source_contract_status": "pass",
        "source_contract": {
            "module_id": DOCTRINE_MODULE_ID,
            "service_class": "DoctrineEnrichmentService",
            "method": "get_file_doctrine",
        },
    }


def enrich_doctrine_file(payload: Mapping[str, Any], rel_path: str) -> dict[str, Any]:
    mechanisms = payload.get("mechanisms") if isinstance(payload.get("mechanisms"), list) else []
    concepts = {
        str(row.get("id")): row
        for row in payload.get("concepts", [])
        if isinstance(row, Mapping) and row.get("id")
    }
    principles = {
        str(row.get("id")): row
        for row in payload.get("principles", [])
        if isinstance(row, Mapping) and row.get("id")
    }
    matched_mechanisms = []
    concept_ids: set[str] = set()
    for mechanism in mechanisms:
        if not isinstance(mechanism, Mapping):
            continue
        loci = mechanism.get("code_loci") if isinstance(mechanism.get("code_loci"), list) else []
        paths = {
            str(item.get("path") if isinstance(item, Mapping) else item)
            for item in loci
            if item
        }
        if rel_path not in paths:
            continue
        matched_mechanisms.append({"id": mechanism.get("id"), "title": mechanism.get("title")})
        for edge in mechanism.get("concept_edges", []) or []:
            if isinstance(edge, Mapping) and edge.get("target"):
                concept_ids.add(str(edge["target"]))
            elif isinstance(edge, str):
                concept_ids.add(edge)
    principle_ids: set[str] = set()
    for cid in concept_ids:
        concept = concepts.get(cid, {})
        for edge in concept.get("principle_edges", []) or []:
            if isinstance(edge, Mapping) and edge.get("target"):
                principle_ids.add(str(edge["target"]))
            elif isinstance(edge, str):
                principle_ids.add(edge)
    return {
        "status": "pass",
        "mechanisms": matched_mechanisms,
        "concepts": [{"id": cid, "title": concepts.get(cid, {}).get("title")} for cid in sorted(concept_ids)],
        "principles": [
            {"id": pid, "title": principles.get(pid, {}).get("title")}
            for pid in sorted(principle_ids)
        ],
        "counts": {
            "mechanisms": len(matched_mechanisms),
            "concepts": len(concept_ids),
            "principles": len(principle_ids),
        },
        "empty_envelope": not matched_mechanisms,
    }


def worker_job_gate(job: Mapping[str, Any]) -> dict[str, Any]:
    provider = str(job.get("provider_id") or "").lower()
    model = str(job.get("model_id") or "").lower()
    budget = job.get("provider_budget") if isinstance(job.get("provider_budget"), Mapping) else {}
    max_usd = float(budget.get("max_usd") or 0)
    paid_model = provider == "openrouter_api" and not model.startswith("free/")
    if paid_model and max_usd <= 0:
        return {"status": "blocked", "reason": "paid_model_without_budget", "allow": False}
    forbidden = [str(item) for item in job.get("forbidden_surfaces", []) if isinstance(item, str)]
    packet_text = json.dumps(job.get("input_packet", {}), sort_keys=True)
    for surface in forbidden:
        if surface and surface in packet_text:
            return {"status": "blocked", "reason": "forbidden_surface_present", "surface": surface, "allow": False}
    return {"status": "pass", "allow": True}


def _source_backed_worker_gate_contract(source_text: str | None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not source_text:
        findings.append(
            {
                "code": "worker_gate_source_body_missing",
                "module_id": WORKER_GATE_MODULE_ID,
            }
        )
        return {
            "status": "blocked",
            "findings": findings,
            "source_body_loaded": False,
            "budget_gate_enabled": False,
            "budget_guard_condition_enabled": False,
            "forbidden_surface_scan_enabled": False,
        }
    required = (
        "def _enforce_budget(",
        "openrouter_paid_model_blocked_by_provider_budget",
        "if free_only or not allow_paid or max_usd <= 0:",
        "def _contains_forbidden_surface(",
        "for pattern in forbidden:",
        "if pattern in text:",
    )
    missing = [anchor for anchor in required if anchor not in source_text]
    if missing:
        findings.append(
            {
                "code": "worker_gate_source_anchor_missing",
                "module_id": WORKER_GATE_MODULE_ID,
                "missing": missing,
            }
        )
    return {
        "status": "pass" if not findings else "blocked",
        "findings": findings,
        "source_body_loaded": True,
        "budget_gate_enabled": (
            "openrouter_paid_model_blocked_by_provider_budget" in source_text
        ),
        "budget_guard_condition_enabled": (
            "if free_only or not allow_paid or max_usd <= 0:" in source_text
        ),
        "forbidden_surface_scan_enabled": "if pattern in text:" in source_text,
    }


def source_backed_worker_job_gate(
    job: Mapping[str, Any],
    module_path: Path | None,
) -> dict[str, Any]:
    if module_path is None or not module_path.is_file():
        return {
            "status": "blocked",
            "allow": False,
            "reason": "source_module_missing",
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
        }
    contract = _source_backed_worker_gate_contract(None)
    try:
        source_text = module_path.read_text(encoding="utf-8")
        contract = _source_backed_worker_gate_contract(source_text)
        module = _load_python_source_module(module_path, WORKER_GATE_MODULE_ID)
        provider_id = str(job.get("provider_id") or "")
        model_id = str(job.get("model_id") or "")
        module._enforce_budget(job, provider_id, model_id)
        forbidden_surface = module._contains_forbidden_surface(job)
    except PermissionError as exc:
        return {
            "status": "blocked",
            "allow": False,
            "reason": str(exc),
            "source_body_loaded": True,
            "source_contract_status": contract["status"],
            "source_contract_findings": contract["findings"],
            "source_contract": {
                "module_id": WORKER_GATE_MODULE_ID,
                "required_callables": ["_enforce_budget", "_contains_forbidden_surface"],
                "budget_gate_enabled": contract["budget_gate_enabled"],
                "budget_guard_condition_enabled": contract[
                    "budget_guard_condition_enabled"
                ],
                "forbidden_surface_scan_enabled": contract[
                    "forbidden_surface_scan_enabled"
                ],
            },
        }
    except Exception as exc:
        return {
            "status": "blocked",
            "allow": False,
            "reason": type(exc).__name__,
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
        }
    if forbidden_surface:
        return {
            "status": "blocked",
            "allow": False,
            "reason": "forbidden_surface_present",
            "surface": forbidden_surface,
            "source_body_loaded": True,
            "source_contract_status": contract["status"],
            "source_contract_findings": contract["findings"],
            "source_contract": {
                "module_id": WORKER_GATE_MODULE_ID,
                "required_callables": ["_enforce_budget", "_contains_forbidden_surface"],
                "budget_gate_enabled": contract["budget_gate_enabled"],
                "budget_guard_condition_enabled": contract[
                    "budget_guard_condition_enabled"
                ],
                "forbidden_surface_scan_enabled": contract[
                    "forbidden_surface_scan_enabled"
                ],
            },
        }
    return {
        "status": "pass" if contract["status"] == "pass" else "blocked",
        "allow": True,
        "reason": (
            None
            if contract["status"] == "pass"
            else "worker_gate_source_contract_failed"
        ),
        "source_body_loaded": True,
        "source_contract_status": contract["status"],
        "source_contract_findings": contract["findings"],
        "source_contract": {
            "module_id": WORKER_GATE_MODULE_ID,
            "required_callables": ["_enforce_budget", "_contains_forbidden_surface"],
            "budget_gate_enabled": contract["budget_gate_enabled"],
            "budget_guard_condition_enabled": contract[
                "budget_guard_condition_enabled"
            ],
            "forbidden_surface_scan_enabled": contract[
                "forbidden_surface_scan_enabled"
            ],
        },
    }


def milestone_quality_accounting(runs: list[Mapping[str, Any]]) -> dict[str, Any]:
    def parse_time(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    milestones = [parse_time(row.get("milestone_at")) for row in runs if row.get("milestone_at")]
    milestones = [item for item in milestones if item is not None]
    latest = max(milestones) if milestones else None
    missing_committed_at = 0
    live_quality_eligible = 0
    green = 0
    projection_verified = 0
    for row in runs:
        run_at = parse_time(row.get("run_at"))
        if latest and run_at and run_at < latest:
            continue
        commit = row.get("apply_green_commit")
        commit = commit if isinstance(commit, Mapping) else {}
        applied_count = int(commit.get("applied_count") or 0)
        if applied_count > 0:
            live_quality_eligible += applied_count
        if applied_count > 0 and not commit.get("committed_at"):
            missing_committed_at += applied_count
        if commit.get("status") == "green" and commit.get("committed_at"):
            green += applied_count
        if row.get("projection_consumed") is True:
            projection_verified += 1
    return {
        "status": "pass",
        "latest_milestone": latest.isoformat() if latest else None,
        "live_quality_eligible_count": live_quality_eligible,
        "green_count": green,
        "projection_consumption_verified_count": projection_verified,
        "missing_committed_at_count_since_last_milestone": missing_committed_at,
    }


def source_backed_milestone_quality_accounting(
    runs: list[Mapping[str, Any]],
    module_path: Path | None,
    blocker_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expected = milestone_quality_accounting(runs)
    if module_path is None or not module_path.is_file():
        return {
            **expected,
            "status": "blocked",
            "source_body_loaded": False,
            "source_contract_status": "blocked",
            "source_contract_error": "source_module_missing",
            "source_contract_findings": [{"code": "source_module_missing"}],
        }
    try:
        module = _load_python_source_module(module_path, MILESTONE_MODULE_ID)
        compute_milestone_metrics = getattr(module, "_compute_milestone_relative_metrics")
        classify_blockers = getattr(module, "classify_blockers_and_next_action")
        with tempfile.TemporaryDirectory(prefix="batch9-milestone-quality-") as tmp:
            run_dirs: list[Path] = []
            for index, row in enumerate(runs):
                if not isinstance(row, Mapping):
                    continue
                if not row.get("run_at") and not isinstance(row.get("apply_green_commit"), Mapping):
                    continue
                run_dir = Path(tmp) / f"run_{index:03d}"
                run_dir.mkdir(parents=True, exist_ok=True)
                run_dirs.append(run_dir)
                if row.get("run_at"):
                    (run_dir / "run_meta.json").write_text(
                        json.dumps(
                            {
                                "source_mode": "live",
                                "evidence_role": "promotion",
                                "created_at": str(row.get("run_at")),
                            },
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                commit = row.get("apply_green_commit")
                if isinstance(commit, Mapping):
                    commit_payload = dict(commit)
                    if row.get("projection_consumed") is True:
                        commit_payload.setdefault("projection_consumption_verified_count", 1)
                    (run_dir / "apply_green_commit.json").write_text(
                        json.dumps(commit_payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    applied_count = int(commit_payload.get("applied_count") or 0)
                    if applied_count > 0:
                        gate_class = (
                            "green"
                            if commit_payload.get("status") == "green"
                            and commit_payload.get("committed_at")
                            else "amber"
                        )
                        (run_dir / "classifications.json").write_text(
                            json.dumps(
                                [
                                    {
                                        "row_job_id": f"batch9_fixture_{index}_{offset}",
                                        "gate_class": gate_class,
                                    }
                                    for offset in range(applied_count)
                                ],
                                indent=2,
                                sort_keys=True,
                            )
                            + "\n",
                            encoding="utf-8",
                        )
            actual = compute_milestone_metrics(
                runs=run_dirs,
                milestone_at=expected["latest_milestone"],
            )
        blocker_input = dict(blocker_metrics or {})
        if not blocker_input:
            blocker_input = {
                "promotion_readiness": {
                    "cohort_apply": (
                        expected["green_count"] >= 3
                        and expected[
                            "missing_committed_at_count_since_last_milestone"
                        ]
                        == 0
                    ),
                    "blocking_reasons": [],
                },
                "milestone_metrics": {
                    "missing_run_at_count_since_last_milestone": 0,
                    "missing_committed_at_count_since_last_milestone": expected[
                        "missing_committed_at_count_since_last_milestone"
                    ],
                    "transport_only_count_since_last_milestone": 0,
                    "transport_only_by_provider_since_last_milestone": {},
                    "transport_only_by_status_since_last_milestone": {},
                },
            }
        blocker_action = classify_blockers(blocker_input)
    except Exception as exc:
        return {
            **expected,
            "status": "blocked",
            "source_body_loaded": True,
            "source_contract_status": "blocked",
            "source_contract_error": type(exc).__name__,
            "source_contract_findings": [
                {
                    "code": "source_contract_exception",
                    "exception_type": type(exc).__name__,
                }
            ],
        }

    observed = {
        "latest_milestone": actual.get("milestone_at"),
        "live_quality_eligible_count": int(
            actual.get("live_quality_eligible_since_last_milestone") or 0
        ),
        "green_count": int(
            actual.get("live_quality_green_count_since_last_milestone") or 0
        ),
        "projection_consumption_verified_count": int(
            actual.get("projection_consumption_verified_count_since_last_milestone")
            or 0
        ),
        "missing_committed_at_count_since_last_milestone": int(
            actual.get("missing_committed_at_count_since_last_milestone") or 0
        ),
    }
    compare_fields = (
        "live_quality_eligible_count",
        "green_count",
        "projection_consumption_verified_count",
        "missing_committed_at_count_since_last_milestone",
    )
    mismatches = [
        {
            "code": "milestone_macro_metric_mismatch",
            "field": field,
            "expected": expected.get(field),
            "observed": observed.get(field),
        }
        for field in compare_fields
        if expected.get(field) != observed.get(field)
    ]
    return {
        **observed,
        "status": "pass" if not mismatches else "blocked",
        "blockers_by_class": blocker_action.get("blockers_by_class", {}),
        "next_action": blocker_action.get("next_action", {}),
        "transport_diagnostics": blocker_action.get("transport_diagnostics", {}),
        "timestamp_diagnostics": blocker_action.get("timestamp_diagnostics", {}),
        "source_body_loaded": True,
        "source_contract_status": "pass",
        "source_contract": {
            "module_id": MILESTONE_MODULE_ID,
            "required_callables": [
                "_compute_milestone_relative_metrics",
                "classify_blockers_and_next_action",
            ],
            "materialized_run_dir_count": sum(
                1
                for row in runs
                if isinstance(row, Mapping)
                and (row.get("run_at") or row.get("apply_green_commit"))
            ),
        },
        "source_contract_findings": mismatches,
    }


def _exercise_lineage(data: Mapping[str, Any]) -> dict[str, Any]:
    result = resolve_lineage(
        data.get("contexts", {}),
        str(data.get("start_run_id") or "RUN_SUBJECT"),
    )
    self_loop = resolve_lineage(data.get("contexts", {}), "RUN_SELF")
    cycle = resolve_lineage(data.get("contexts", {}), "RUN_A")
    status = (
        result["chain_run_ids"][:2] == ["RUN_SUBJECT", "RUN_FEED"]
    )
    return {
        "exercise_id": "lineage_temporal_provenance_chain_resolver",
        "status": "pass" if status else "blocked",
        "chain_run_ids": result["chain_run_ids"],
        "self_loop_pruned": self_loop["self_loop_pruned"],
        "cycle_detected": cycle["cycle_detected"],
    }


def _run_all_exercises(
    fixtures: Mapping[str, Any],
    source_bodies: Mapping[str, str] | None = None,
    source_paths: Mapping[str, Path] | None = None,
) -> dict[str, dict[str, Any]]:
    source_bodies = source_bodies or {}
    source_paths = source_paths or {}
    exercises: dict[str, dict[str, Any]] = {}
    exercises["lineage_temporal_provenance_chain_resolver"] = {
        "exercise_id": "lineage_temporal_provenance_chain_resolver",
        **source_backed_lineage(
            fixtures["lineage"],
            source_paths.get(LINEAGE_MODULE_ID),
        ),
    }
    exercises["approval_sign_off_claim_adjudicator"] = {
        "exercise_id": "approval_sign_off_claim_adjudicator",
        **source_backed_approval_adjudication(
            fixtures["approval"]["request"],
            fixtures["approval"]["decision"],
            {},
            source_paths.get(APPROVAL_MODULE_ID),
        ),
    }
    approval_preacquired = source_backed_approval_adjudication(
        fixtures["approval"]["request"],
        fixtures["approval"]["decision"],
        fixtures["approval"].get("preacquired", {}),
        source_paths.get(APPROVAL_MODULE_ID),
    )
    exercises["approval_sign_off_claim_adjudicator"]["preacquired_claim_refused"] = (
        approval_preacquired["preacquired_claim_refused"]
    )
    exercises["approval_sign_off_claim_adjudicator"][
        "preacquired_decision_error_code"
    ] = approval_preacquired.get("decision_error_code")
    ast_tree = source_backed_ast_doc_tree(
        fixtures["ast"]["files"],
        source_paths.get(AST_MODULE_ID),
    )
    exercises["python_ast_symbol_index_doc_tree"] = {
        "exercise_id": "python_ast_symbol_index_doc_tree",
        "status": ast_tree["status"],
        "symbol_count": ast_tree["symbol_count"],
        "syntax_error_gap": ast_tree["syntax_error_gap"],
        "qualified_symbols": ast_tree["qualified_symbols"],
        "source_body_loaded": ast_tree["source_body_loaded"],
        "source_contract_status": ast_tree["source_contract_status"],
        "source_contract": ast_tree.get("source_contract"),
    }
    finance = cluster_news_rows(
        fixtures["finance_news"]["rows"],
        source_text=source_bodies.get(FINANCE_MODULE_ID),
    )
    exercises["finance_news_dedup_cluster_ranker"] = {
        "exercise_id": "finance_news_dedup_cluster_ranker",
        **finance,
    }
    mission = compile_mission_graph(
        fixtures["mission_graph"]["nodes"],
        "target",
        source_text=source_bodies.get(MISSION_GRAPH_MODULE_ID),
    )
    missing = compile_mission_graph(
        fixtures["mission_graph"]["nodes"],
        str(fixtures["mission_graph"].get("negative_target_id") or "target"),
        source_text=source_bodies.get(MISSION_GRAPH_MODULE_ID),
    )
    exercises["mission_graph_topological_compiler"] = {
        "exercise_id": "mission_graph_topological_compiler",
        **mission,
        "missing_target_error": bool(missing["topology_error"]),
    }
    deps = source_backed_dependency_pin_audit(
        fixtures["dependency_pin"]["requirements"],
        fixtures["dependency_pin"]["installed"],
        source_paths.get(DEPENDENCY_PIN_MODULE_ID),
    )
    exercises["dependency_pin_drift_auditor"] = {
        "exercise_id": "dependency_pin_drift_auditor",
        **deps,
    }
    config = source_backed_config_authority_audit(
        fixtures["config_authority"]["registry"],
        set(fixtures["config_authority"]["known_roots"]),
        source_paths.get(CONFIG_AUTHORITY_MODULE_ID),
    )
    exercises["config_authority_drift_audit"] = {
        "exercise_id": "config_authority_drift_audit",
        "status": config["status"],
        "audit_status": config["status"],
        "row_count": config["row_count"],
        "audit_findings": config["findings"],
        "mutation_allowed_rejected": any(
            row.get("code") in {
                "generated_projection_mutable",
                "generated_projection_mutation_allowed",
            }
            for row in config["findings"]
        ),
        "source_body_loaded": config["source_body_loaded"],
        "source_contract_status": config["source_contract_status"],
        "source_contract": config.get("source_contract"),
    }
    edges = extract_heterogeneous_edges(
        fixtures["heterogeneous_edges"]["row"],
        "row:fixture",
        source_bodies.get(HETEROGENEOUS_MODULE_ID),
    )
    exercises["heterogeneous_graph_edge_extractor"] = {
        "exercise_id": "heterogeneous_graph_edge_extractor",
        **edges,
    }
    atlas = source_backed_aggregate_work_atlas_cell(
        fixtures["work_atlas"]["marks"],
        source_bodies.get(WORK_ATLAS_MODULE_ID),
    )
    exercises["work_atlas_cell_histogram_aggregator"] = {
        "exercise_id": "work_atlas_cell_histogram_aggregator",
        **atlas,
    }
    blocked = source_backed_admission_decision(
        fixtures["host_pressure"]["quote"],
        "auto",
        source_paths.get(HOST_PRESSURE_MODULE_ID),
    )
    exercises["host_pressure_admission_decision_gate"] = {
        "exercise_id": "host_pressure_admission_decision_gate",
        "status": blocked["status"],
        "decision_status": blocked["decision_status"],
        "allow": blocked["allow"],
        "result": blocked["result"],
        "auto_policy_blocked": blocked["auto_policy_blocked"],
        "source_body_loaded": blocked["source_body_loaded"],
        "source_contract_status": blocked["source_contract_status"],
        "source_contract_findings": blocked.get("source_contract_findings", []),
        "source_contract": blocked.get("source_contract"),
    }
    doctrine_hit = source_backed_doctrine_enrichment(
        fixtures["doctrine_enrichment"]["corpus"],
        fixtures["doctrine_enrichment"]["hit_path"],
        source_paths.get(DOCTRINE_MODULE_ID),
    )
    doctrine_miss = source_backed_doctrine_enrichment(
        fixtures["doctrine_enrichment"]["corpus"],
        fixtures["doctrine_enrichment"]["miss_path"],
        source_paths.get(DOCTRINE_MODULE_ID),
    )
    exercises["doctrine_file_enrichment_multihop_join"] = {
        "exercise_id": "doctrine_file_enrichment_multihop_join",
        **doctrine_hit,
        "miss_empty_envelope": doctrine_miss["empty_envelope"],
    }
    worker_block = source_backed_worker_job_gate(
        fixtures["worker_gate"]["blocked_job"],
        source_paths.get(WORKER_GATE_MODULE_ID),
    )
    worker_allow = source_backed_worker_job_gate(
        fixtures["worker_gate"]["allowed_job"],
        source_paths.get(WORKER_GATE_MODULE_ID),
    )
    exercises["worker_job_budget_forbidden_surface_gate"] = {
        "exercise_id": "worker_job_budget_forbidden_surface_gate",
        "status": (
            "pass"
            if worker_block["source_contract_status"] == "pass"
            and worker_allow["source_contract_status"] == "pass"
            else "blocked"
        ),
        "blocked_job_status": worker_block["status"],
        "blocked_job_allow": worker_block["allow"],
        "blocked_job_reason": worker_block.get("reason"),
        "blocked_surface": worker_block.get("surface"),
        "allowed_job_status": worker_allow["status"],
        "allowed_job_allow": worker_allow["allow"],
        "source_body_loaded": worker_block["source_body_loaded"],
        "source_contract_status": worker_block["source_contract_status"],
        "source_contract_findings": worker_block.get("source_contract_findings", []),
        "source_contract": worker_block.get("source_contract"),
    }
    milestone = source_backed_milestone_quality_accounting(
        fixtures["milestone_quality"]["runs"],
        source_paths.get(MILESTONE_MODULE_ID),
        fixtures["milestone_quality"].get("blocker_metrics"),
    )
    exercises["milestone_relative_promotion_quality_accounting"] = {
        "exercise_id": "milestone_relative_promotion_quality_accounting",
        **milestone,
    }
    return exercises


def evaluate(input_dir: Path, public_root: Path, _source_manifest: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    manifest = _load_json(input_dir / PROBE_MANIFEST_NAME)
    mechanisms = manifest.get("mechanisms")
    if not isinstance(mechanisms, list):
        mechanisms = []
        findings.append(
            finding(
                "BATCH9_PROBE_MANIFEST_INVALID",
                "Probe manifest must include a mechanisms list.",
                subject_id=PROBE_MANIFEST_NAME,
            )
        )
    fixtures = manifest.get("positive_fixture")
    if not isinstance(fixtures, Mapping):
        fixtures = {}
        findings.append(
            finding(
                "BATCH9_POSITIVE_FIXTURE_MISSING",
                "Probe manifest must include positive_fixture object.",
                subject_id=PROBE_MANIFEST_NAME,
            )
        )
    rows = _source_rows(input_dir, public_root)
    source_bodies = {
        module_id: body
        for module_id in TEXT_BACKED_MODULE_IDS
        for body in [_source_module_text(input_dir, public_root, module_id)]
        if body is not None
    }
    source_paths = {
        module_id: path
        for module_id in PATH_BACKED_MODULE_IDS
        for path in [_source_module_path(input_dir, public_root, module_id)]
        if path is not None
    }
    mechanism_rows = [
        _mechanism_status(row, rows)
        for row in mechanisms
        if isinstance(row, Mapping)
    ]
    missing_mechanisms = [
        mechanism_id
        for mechanism_id in EXPECTED_MECHANISMS
        if mechanism_id not in {row.get("mechanism_id") for row in mechanism_rows}
    ]
    if missing_mechanisms:
        findings.append(
            finding(
                "BATCH9_MECHANISM_MISSING",
                "Probe manifest is missing expected Batch-9 mechanisms.",
                expected=list(EXPECTED_MECHANISMS),
                observed=[row.get("mechanism_id") for row in mechanism_rows],
            )
        )
    blocked_mechanisms = [
        row.get("mechanism_id") for row in mechanism_rows if row.get("status") != "pass"
    ]
    if blocked_mechanisms:
        findings.append(
            finding(
                "BATCH9_MECHANISM_SOURCE_MODULE_BLOCKED",
                "One or more mechanism rows is missing source module references.",
                observed=blocked_mechanisms,
            )
        )
    try:
        runtime_exercises = _run_all_exercises(fixtures, source_bodies, source_paths)
    except Exception as exc:
        runtime_exercises = {}
        findings.append(
            finding(
                "BATCH9_RUNTIME_EXERCISE_EXCEPTION",
                f"Batch-9 runtime exercise raised {type(exc).__name__}.",
            )
        )
    failed = [
        exercise_id
        for exercise_id, result in runtime_exercises.items()
        if result.get("status") != "pass"
    ]
    if failed:
        findings.append(
            finding(
                "BATCH9_RUNTIME_EXERCISE_FAILED",
                "One or more Batch-9 public exercises failed.",
                observed=failed,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "mechanism_count": len(mechanism_rows),
        "mechanisms": mechanism_rows,
        "runtime_exercises": runtime_exercises,
        "runtime_exercise_count": len(runtime_exercises),
        "copied_macro_source_module_count": len(rows),
        "expected_module_ids": list(EXPECTED_MODULE_IDS),
        "error_codes": [],
        "findings": findings,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch9_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    ceiling = (
        result.get("authority_ceiling")
        if isinstance(result.get("authority_ceiling"), Mapping)
        else {}
    )
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "standard_authority": ceiling.get("standard_authority"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "host_state_truth": ceiling.get("host_state_truth"),
        "live_doctrine_truth": ceiling.get("live_doctrine_truth"),
        "real_news_truth": ceiling.get("real_news_truth"),
        "market_advice": ceiling.get("market_advice"),
        "work_ledger_authority": ceiling.get("work_ledger_authority"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "release_authorized": ceiling.get("release_authorized"),
        "whole_system_correctness_claim": ceiling.get(
            "whole_system_correctness_claim"
        ),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=(
            BUNDLE_INPUT_MODE
            if args.action == "validate-bundle"
            else "fixture_input"
        ),
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(
        json.dumps(
            result_card(result) if args.card else result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
