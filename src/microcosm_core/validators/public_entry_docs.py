from __future__ import annotations

import argparse
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


CHECKER_ID = "checker.microcosm.validators.public_entry_docs"
FIXTURE_ID = "first_wave.public_entry_docs"
REQUIRED_DOCS = [
    "README.md",
    "AGENTS.md",
    "paper_modules/pattern_binding_contract.md",
    "paper_modules/executable_doctrine_grammar.md",
    "paper_modules/proof_diagnostic_evidence_spine.md",
    "paper_modules/formal_math_readiness_gate.md",
    "paper_modules/corpus_readiness_mathlib_absence.md",
    "paper_modules/mathematical_strategy_atlas.md",
    "paper_modules/tactic_portfolio_availability.md",
    "paper_modules/target_shape_tactic_routing.md",
    "paper_modules/formal_math_premise_retrieval.md",
    "paper_modules/formal_math_verifier_trace_repair_loop.md",
    "paper_modules/formal_evidence_cell_anchor_resolver.md",
    "paper_modules/undeclared_library_prior_classifier.md",
    "paper_modules/lean_std_premise_index.md",
    "paper_modules/ring2_premise_precision_recall.md",
    "paper_modules/agent_benchmark_integrity_anti_gaming_replay.md",
    "paper_modules/durable_agent_work_landing_replay.md",
    "paper_modules/research_replication_rubric_artifact_replay.md",
    "paper_modules/world_model_projection_drift_control_room.md",
    "paper_modules/spatial_world_model_counterfactual_simulation_replay.md",
    "paper_modules/mechanistic_interpretability_circuit_attribution_replay.md",
    "paper_modules/provider_context_recipe_budget.md",
    "paper_modules/public_reveal_walkthrough.md",
    "paper_modules/macro_projection_import_protocol.md",
    "paper_modules/formal_math_lean_proof_witness.md",
    "paper_modules/prediction_oracle_reconciliation.md",
    "paper_modules/standards_meta_diagnostics.md",
    "paper_modules/cold_reader_route_map.md",
    "paper_modules/agent_monitor_redteam_falsification_replay.md",
    "paper_modules/agent_memory_temporal_conflict_replay.md",
    "paper_modules/sleeper_memory_poisoning_quarantine_replay.md",
    "paper_modules/mcp_tool_authority_replay.md",
    "paper_modules/proof_derived_governed_mutation_authorization.md",
    "paper_modules/cold_clone_probe.md",
    "skills/cold_start_navigation.md",
]
ACCEPTED_ORGAN_IDS = [
    "pattern_binding_contract",
    "executable_doctrine_grammar",
    "proof_diagnostic_evidence_spine",
    "formal_math_readiness_gate",
    "corpus_readiness_mathlib_absence_gate",
    "mathematical_strategy_atlas_hypothesis_scorer",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
    "lean_std_premise_index",
    "formal_math_premise_retrieval",
    "formal_math_verifier_trace_repair_loop",
    "formal_evidence_cell_anchor_resolver",
    "undeclared_library_prior_symbol_classifier",
    "ring2_premise_retrieval_precision_recall_harness",
    "agent_benchmark_integrity_anti_gaming_replay",
    "provider_context_recipe_budget_policy",
    "formal_math_lean_proof_witness",
    "navigation_hologram_route_plane",
    "mission_transaction_work_spine",
    "durable_agent_work_landing_replay",
    "research_replication_rubric_artifact_replay",
    "world_model_projection_drift_control_room",
    "spatial_world_model_counterfactual_simulation_replay",
    "mechanistic_interpretability_circuit_attribution_replay",
    "agent_route_observability_runtime",
    "pattern_assimilation_step",
    "public_reveal_walkthrough",
    "macro_projection_import_protocol",
    "prediction_oracle_reconciliation",
    "standards_meta_diagnostics",
    "cold_reader_route_map",
    "agent_monitor_redteam_falsification_replay",
    "agent_memory_temporal_conflict_replay",
    "sleeper_memory_poisoning_quarantine_replay",
    "mcp_tool_authority_replay",
    "proof_derived_governed_mutation_authorization",
]
REQUIRED_PHRASES_BY_DOC = {
    "README.md": [
        "repo -> .microcosm",
        "microcosm compile .",
        "executable research prototype",
        "local project operating substrate",
        ".microcosm/",
        "Architecture Kernel",
        "microcosm explain <project> <route_id>",
        "Evidence receipts are the black-box recorder",
        "Internal Runtime Spine",
        "formal_math_readiness_gate",
        "corpus_readiness_mathlib_absence_gate",
        "mathematical_strategy_atlas_hypothesis_scorer",
        "tactic_portfolio_availability_probe",
        "target_shape_tactic_routing_gate",
        "lean_std_premise_index",
        "formal_math_premise_retrieval",
        "formal_math_verifier_trace_repair_loop",
        "formal_evidence_cell_anchor_resolver",
        "undeclared_library_prior_symbol_classifier",
        "ring2_premise_retrieval_precision_recall_harness",
        "agent_benchmark_integrity_anti_gaming_replay",
        "durable_agent_work_landing_replay",
        "research_replication_rubric_artifact_replay",
        "world_model_projection_drift_control_room",
        "spatial_world_model_counterfactual_simulation_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "provider_context_recipe_budget_policy",
        "formal_math_lean_proof_witness",
        "public_reveal_walkthrough",
        "macro_projection_import_protocol",
        "prediction_oracle_reconciliation",
        "standards_meta_diagnostics",
        "cold_reader_route_map",
        "agent_monitor_redteam_falsification_replay",
        "agent_memory_temporal_conflict_replay",
        "sleeper_memory_poisoning_quarantine_replay",
        "mcp_tool_authority_replay",
        "proof_derived_governed_mutation_authorization",
        "sleeper_memory_poisoning_quarantine_replay",
        "mcp_tool_authority_replay",
        "proof_derived_governed_mutation_authorization",
        "formal-math-lean-proof-witness",
        "corpus-readiness-mathlib-absence-gate",
        "mathematical-strategy-atlas-hypothesis-scorer",
        "tactic-portfolio-availability-probe",
        "target-shape-tactic-routing-gate",
        "lean-std-premise-index",
        "formal-math-premise-retrieval",
        "formal-math-verifier-trace-repair-loop",
        "formal-evidence-cell-anchor-resolver",
        "undeclared-library-prior-symbol-classifier",
        "ring2-premise-retrieval-precision-recall-harness",
        "agent-benchmark-integrity-anti-gaming-replay",
        "durable-agent-work-landing-replay",
        "research-replication-rubric-artifact-replay",
        "world-model-projection-drift-control-room",
        "spatial-world-model-counterfactual-simulation-replay",
        "mechanistic-interpretability-circuit-attribution-replay",
        "provider-context-recipe-budget-policy",
        "microcosm reveal",
        "macro-projection-import-protocol",
        "prediction-oracle-reconciliation",
        "standards-meta-diagnostics",
        "cold-reader-route-map",
        "agent-monitor-redteam-falsification-replay",
        "agent-memory-temporal-conflict-replay",
        "sleeper-memory-poisoning-quarantine-replay",
        "mcp-tool-authority-replay",
        "proof-derived-governed-mutation-authorization",
        "sleeper-memory-poisoning-quarantine-replay",
        "mcp-tool-authority-replay",
        "proof-derived-governed-mutation-authorization",
        "not trading or financial advice",
        "not authorize release",
    ],
    "AGENTS.md": [
        "microcosm compile <project>",
        "repo -> `.microcosm`",
        "executable research prototype",
        "local project operating substrate",
        "microcosm init <project>",
        "microcosm explain <project> <route_id>",
        "Accepted Public Runtime Spine",
        "Do not widen Lean/Lake",
        "formal_math_lean_proof_witness",
        "corpus_readiness_mathlib_absence_gate",
        "mathematical_strategy_atlas_hypothesis_scorer",
        "tactic_portfolio_availability_probe",
        "target_shape_tactic_routing_gate",
        "lean_std_premise_index",
        "formal_math_premise_retrieval",
        "formal_math_verifier_trace_repair_loop",
        "formal_evidence_cell_anchor_resolver",
        "undeclared_library_prior_symbol_classifier",
        "ring2_premise_retrieval_precision_recall_harness",
        "agent_benchmark_integrity_anti_gaming_replay",
        "durable_agent_work_landing_replay",
        "research_replication_rubric_artifact_replay",
        "world_model_projection_drift_control_room",
        "spatial_world_model_counterfactual_simulation_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "provider_context_recipe_budget_policy",
        "Fixtures Are Tests",
        "Receipts Are Evidence",
        "public_reveal_walkthrough",
        "macro_projection_import_protocol",
        "prediction_oracle_reconciliation",
        "standards_meta_diagnostics",
        "cold_reader_route_map",
        "agent_monitor_redteam_falsification_replay",
        "agent_memory_temporal_conflict_replay",
        "mcp_tool_authority_replay",
        "proof_derived_governed_mutation_authorization",
        "formal-math-lean-proof-witness",
        "corpus-readiness-mathlib-absence-gate",
        "mathematical-strategy-atlas-hypothesis-scorer",
        "tactic-portfolio-availability-probe",
        "target-shape-tactic-routing-gate",
        "lean-std-premise-index",
        "formal-math-premise-retrieval",
        "formal-math-verifier-trace-repair-loop",
        "formal-evidence-cell-anchor-resolver",
        "undeclared-library-prior-symbol-classifier",
        "ring2-premise-retrieval-precision-recall-harness",
        "agent-benchmark-integrity-anti-gaming-replay",
        "durable-agent-work-landing-replay",
        "research-replication-rubric-artifact-replay",
        "world-model-projection-drift-control-room",
        "spatial-world-model-counterfactual-simulation-replay",
        "mechanistic-interpretability-circuit-attribution-replay",
        "provider-context-recipe-budget-policy",
        "microcosm reveal",
        "macro-projection-import-protocol",
        "prediction-oracle-reconciliation",
        "standards-meta-diagnostics",
        "cold-reader-route-map",
        "agent-monitor-redteam-falsification-replay",
        "agent-memory-temporal-conflict-replay",
        "mcp-tool-authority-replay",
        "proof-derived-governed-mutation-authorization",
        "Do not treat prediction fixtures as trading or financial advice",
    ],
}
FORBIDDEN_PHRASES_BY_DOC = {
    "README.md": [
        "runnable, synthetic, and receipt-driven",
        "private reconstruction control plane",
        "public synthetic microcosm",
    ],
    "AGENTS.md": [
        "source reconstruction workspace",
        "Use only synthetic fixtures",
        "Receipts Are Authority",
        "macro reconstruction contracts",
    ],
}


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key, [])
    return [row for row in rows if isinstance(row, dict)]


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


def _normalized_text(text: str) -> str:
    return " ".join(text.split())


def _accepted_organs(public_root: Path) -> list[str]:
    registry = read_json_strict(public_root / "core/organ_registry.json")
    return [
        str(row.get("organ_id"))
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def validate_public_entry_docs(
    root: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    output_file = Path(out_path)
    missing_docs: list[str] = []
    missing_required_phrases_by_doc: dict[str, list[str]] = {}
    forbidden_phrases_by_doc: dict[str, list[str]] = {}
    stale_first_slice_only_phrases: list[str] = []
    doc_paths: list[Path] = []
    for rel in REQUIRED_DOCS:
        path = public_root / rel
        doc_paths.append(path)
        if not path.is_file():
            missing_docs.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        normalized = _normalized_text(text)
        missing_phrases = [
            phrase
            for phrase in REQUIRED_PHRASES_BY_DOC.get(rel, [])
            if phrase not in normalized
        ]
        if missing_phrases:
            missing_required_phrases_by_doc[rel] = missing_phrases
        forbidden_phrases = [
            phrase for phrase in FORBIDDEN_PHRASES_BY_DOC.get(rel, []) if phrase in text
        ]
        if forbidden_phrases:
            forbidden_phrases_by_doc[rel] = forbidden_phrases
        if "only implemented\n   organ here is `pattern_binding_contract`" in text:
            stale_first_slice_only_phrases.append(rel)
        if "only implemented organ here is `pattern_binding_contract`" in text:
            stale_first_slice_only_phrases.append(rel)

    accepted = _accepted_organs(public_root)
    missing_accepted_organs = [
        organ_id for organ_id in ACCEPTED_ORGAN_IDS if organ_id not in accepted
    ]
    unexpected_accepted_organs = [
        organ_id for organ_id in accepted if organ_id not in ACCEPTED_ORGAN_IDS
    ]
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
            [public_root / rel for rel in REQUIRED_DOCS if (public_root / rel).is_file()],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    blocking_codes: list[str] = []
    if missing_docs:
        blocking_codes.append("MISSING_PUBLIC_ENTRY_DOC")
    if missing_required_phrases_by_doc:
        blocking_codes.append("MISSING_REQUIRED_ENTRY_PHRASE")
    if stale_first_slice_only_phrases:
        blocking_codes.append("STALE_FIRST_SLICE_ONLY_ENTRY_TEXT")
    if forbidden_phrases_by_doc:
        blocking_codes.append("PUBLIC_ENTRY_DOC_ROUTE_DRIFT")
    if missing_accepted_organs or unexpected_accepted_organs:
        blocking_codes.append("ACCEPTED_ORGAN_REGISTRY_MISMATCH")
    if scan["blocking_hit_count"]:
        blocking_codes.append("PRIVATE_STATE_SCAN_BLOCKED")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "public_entry_docs_validation_receipt_v1",
        "checker_id": CHECKER_ID,
        "fixture_id": FIXTURE_ID,
        "status": status,
        "command": command,
        "required_docs": REQUIRED_DOCS,
        "missing_docs": missing_docs,
        "missing_required_phrases_by_doc": missing_required_phrases_by_doc,
        "forbidden_phrases_by_doc": forbidden_phrases_by_doc,
        "stale_first_slice_only_phrases": sorted(set(stale_first_slice_only_phrases)),
        "accepted_current_authority_organs": accepted,
        "missing_accepted_organs": missing_accepted_organs,
        "unexpected_accepted_organs": unexpected_accepted_organs,
        "deferred_organs": [],
        "blocking_codes": blocking_codes,
        "private_state_scan": scan,
        "authority_ceiling": {
            "status": PASS,
            "entry_docs_authority": "public_entry_navigation_and_docs_only",
            "lean_lake_authorized": "bounded_public_witness_only",
            "trading_or_financial_advice_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": "Public entry-doc validation proves only standalone public entry documentation, paper module, and cold-start navigation presence. It does not authorize Lean/Lake beyond the bounded public witness organ, public release, hosted-public readiness, publication, recipient work, provider calls, private-data equivalence, or whole-system correctness.",
        "receipt_paths": [_display(output_file, public_root=public_root)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public entry docs")
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.public_entry_docs "
        f"--root {args.root} --out {args.out}"
    )
    receipt = validate_public_entry_docs(args.root, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
