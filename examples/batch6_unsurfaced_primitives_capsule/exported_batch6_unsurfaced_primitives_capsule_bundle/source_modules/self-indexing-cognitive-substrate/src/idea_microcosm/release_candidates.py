"""Build and score release-candidate portfolio rows.

[PURPOSE]
Rank public-safe release microcosm candidates without granting release authority.

[INTERFACE]
Exports candidate classification, validation helpers, and the portfolio builder.

[FLOW]
Load registry candidates, validate required fields, score rows, and emit receipts.

[DEPENDENCIES]
Uses registry JSON, receipt refs, pathlib, datetime, and release safety conventions.

[CONSTRAINTS]
Portfolio rank is evaluator guidance only, not publication permission or hosted proof.
- When-needed: Open when scoring public-safe candidate rows, selecting the next specimen, or routing from a release portfolio card into runnable microcosm builders.
- Escalates-to: registry/release_candidates.json; state/release_candidate_portfolio.json; release/publication_gate.json; microcosms/specimen_suite/release_root_contract.json
- Navigation-group: microcosm_support.release_selection
- Validator: validator.release_candidates; validator.public_boundary; validator.release_root_compiler
- Receipt: receipts/release_candidate_portfolio.json; receipts/release_candidates_seed.json
- Anti-claim: Portfolio rank is candidate-selection guidance only and cannot grant release approval, hosted-public proof, publication permission, or private-root equivalence.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "candidate_id",
    "title",
    "idea_family",
    "five_sentence_release_summary",
    "source_refs",
    "python_refs",
    "standard_refs",
    "skill_refs",
    "concept_refs",
    "receipt_refs",
    "projection_strategy",
    "improvement_delta",
    "public_safety_status",
    "runnability_status",
    "video_demo_potential",
    "external_review_potential",
    "blocked_by",
    "next_action",
    "release_priority",
    "anti_claims",
    "cold_sandbox_status",
    "hosted_public_status",
    "publication_status",
}

ALLOWED_PROJECTION_STRATEGIES = {
    "direct_extract",
    "sanitized_extract",
    "reimplementation",
    "interface_only_replica",
    "toy_analogue",
    "documentation_first",
    "blocked",
}
PRIORITY_POINTS = {"critical": 30, "high": 24, "medium": 16, "low": 8}
POTENTIAL_POINTS = {"high": 8, "medium": 5, "low": 2, "blocked": -4}
SAFETY_POINTS = {
    "public_candidate_fail_closed": 18,
    "sanitizable": 12,
    "private": 0,
    "blocked": -20,
}
RUNNABILITY_POINTS = {
    "cold_sandbox_passed": 24,
    "internal_runnable": 18,
    "clone_probe_needed": 10,
    "documentation_first": 4,
    "unknown": 0,
    "blocked": -20,
}
STRATEGY_POINTS = {
    "reimplementation": 12,
    "toy_analogue": 11,
    "interface_only_replica": 8,
    "sanitized_extract": 6,
    "documentation_first": 2,
    "direct_extract": 0,
    "blocked": -20,
}
LANDED_ROOT_PROOF_CANDIDATE_IDS = {
    "status_preserving_control_plane_microcosm",
}
ALLOWED_SPECIMEN_STATUSES = {
    "landed",
    "next_candidate",
    "candidate",
    "blocked",
}
MICROCOSM_PORTFOLIO_WORKITEM_REF = "cap_microcosm_portfolio_index_v0"
EXTERNAL_REVIEW_SIGNAL_GRAPH_WORKITEM_REF = "cap_external_review_signal_microcosm_graph_v0"
VERISOFTBENCH_CANDIDATE_ID = "verisoftbench_diagnostic_specimen_microcosm"
TELEOLOGY_GATE_PATH = Path("strategy/microcosm_teleology_gate.json")
RETIRED_REF_TOKENS = (
    "microcosms/actual_public_remote_clone_execution/",
    "microcosms/demo_receipt_storyboard/",
    "microcosms/external_public_clone_probe_receipt/",
    "microcosms/hosted_public_ci_workflow_gate/",
    "microcosms/hosted_public_remote_receipt_reconciliation/",
    "microcosms/license_citation_disclosure_gate/",
    "microcosms/operator_public_remote_clone_execution_receipt/",
    "microcosms/public_release_package_manifest_gate/",
    "microcosms/recipient_review_route_gate/",
    "microcosms/release_artifact_integrity_witness/",
    "microcosms/thiel_evidence_packet_gate/",
    "microcosms/website_card_projection_gate/",
)
SPECIMEN_BUILD_COMMANDS = {
    "atlas_navigation_bands_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-atlas-navigation-bands-specimen --root . --write-receipt",
    "cold_start_agent_skills_pack_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-cold-start-agent-skills-pack-specimen --root . --write-receipt",
    "concept_graph_cards_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concept-graph-cards-specimen --root . --write-receipt",
    "concurrency_transaction_mission_control_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
    "correction_survival_loop_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-correction-survival-loop-specimen --root . --write-receipt",
    "demo_receipt_storyboard_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-demo-receipt-storyboard-specimen --root . --write-receipt",
    "executable_grammar_metabolism_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-executable-grammar-metabolism-specimen --root . --write-receipt",
    "frontend_cockpit_hud_control_surface_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-frontend-hud-control-surface-specimen --root . --write-receipt",
    "hosted_public_ci_workflow_gate_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-hosted-public-ci-workflow-gate-specimen --root . --write-receipt",
    "external_public_clone_probe_receipt_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-external-public-clone-probe-receipt-specimen --root . --write-receipt",
    "hosted_public_remote_receipt_reconciliation_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-hosted-public-remote-receipt-reconciliation-specimen --root . --write-receipt",
    "actual_public_remote_clone_execution_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-actual-public-remote-clone-execution-specimen --root . --write-receipt",
    "operator_public_remote_clone_execution_receipt_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-operator-public-remote-clone-execution-receipt-specimen --root . --write-receipt",
    "lab_evolve_failure_replay_graph_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-lab-evolve-failure-replay-specimen --root . --write-receipt",
    "license_citation_disclosure_gate_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-license-citation-disclosure-gate-specimen --root . --write-receipt",
    "meta_diagnostics_workbench_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-meta-diagnostics-workbench-specimen --root . --write-receipt",
    "provider_harness_evaluator_authority_split_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-provider-harness-canary-specimen --root . --write-receipt",
    "public_release_package_manifest_gate_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt",
    "recipient_review_route_gate_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-recipient-review-route-gate-specimen --root . --write-receipt",
    "release_artifact_integrity_witness_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-artifact-integrity-witness-specimen --root . --write-receipt",
    "release_standards_axiom_gate_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-standards-gate-specimen --root . --write-receipt",
    "self_comprehension_navigator_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-self-comprehension-navigator-specimen --root . --write-receipt",
    "source_capsule_provenance_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-source-capsule-provenance-specimen --root . --write-receipt",
    "source_shuttle_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-source-shuttle-specimen --root . --write-receipt",
    "status_preserving_control_plane_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-status-preserving-control-plane-specimen --root . --write-receipt",
    "task_ledger_cap_economy_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-task-ledger-specimen --root . --write-receipt",
    "thiel_evidence_packet_gate_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-thiel-evidence-packet-gate-specimen --root . --write-receipt",
    "verisoftbench_diagnostic_specimen_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-verisoftbench-diagnostic-specimen --root . --write-receipt",
    "website_card_projection_gate_microcosm": "PYTHONPATH=src python3 -m idea_microcosm.cli build-website-card-projection-gate-specimen --root . --write-receipt",
}
EXTERNAL_REVIEW_SIGNAL_NODE_CLASSES = {
    "release_standards_axiom_gate_microcosm": "scope_boundary",
    "lab_evolve_failure_replay_graph_microcosm": "failure_replay",
    "provider_harness_evaluator_authority_split_microcosm": "provider_reliability_boundary",
    "verisoftbench_diagnostic_specimen_microcosm": "benchmark_diagnostic_boundary",
    "meta_diagnostics_workbench_microcosm": "meta_diagnostics_boundary",
    "frontend_cockpit_hud_control_surface_microcosm": "operator_control_surface",
    "demo_receipt_storyboard_microcosm": "demo_sequence_boundary",
    "website_card_projection_gate_microcosm": "website_projection_boundary",
    "thiel_evidence_packet_gate_microcosm": "application_evidence_boundary",
    "recipient_review_route_gate_microcosm": "recipient_review_boundary",
    "license_citation_disclosure_gate_microcosm": "license_citation_disclosure_boundary",
    "hosted_public_ci_workflow_gate_microcosm": "hosted_public_boundary",
    "external_public_clone_probe_receipt_microcosm": "external_public_clone_probe_receipt_boundary",
    "hosted_public_remote_receipt_reconciliation_microcosm": "hosted_public_remote_receipt_reconciliation_boundary",
    "actual_public_remote_clone_execution_microcosm": "actual_public_remote_clone_execution_boundary",
    "operator_public_remote_clone_execution_receipt_microcosm": "operator_public_remote_clone_execution_receipt_intake_boundary",
    "public_release_package_manifest_gate_microcosm": "package_manifest_boundary",
    "release_artifact_integrity_witness_microcosm": "artifact_integrity_boundary",
    "source_capsule_provenance_microcosm": "source_capsule_boundary",
    "source_shuttle_microcosm": "source_shuttle_boundary",
}
EXTERNAL_REVIEW_SIGNAL_EDGE_BLUEPRINTS = (
    (
        "release_standards_axiom_gate_microcosm",
        "demo_receipt_storyboard_microcosm",
        "scope_gate_constrains_demo_copy",
    ),
    (
        "lab_evolve_failure_replay_graph_microcosm",
        "verisoftbench_diagnostic_specimen_microcosm",
        "failure_replay_localizes_benchmark_diagnostic",
    ),
    (
        "provider_harness_evaluator_authority_split_microcosm",
        "verisoftbench_diagnostic_specimen_microcosm",
        "provider_boundary_preserves_evaluator_authority",
    ),
    (
        "frontend_cockpit_hud_control_surface_microcosm",
        "demo_receipt_storyboard_microcosm",
        "control_surface_feeds_demo_sequence",
    ),
    (
        "demo_receipt_storyboard_microcosm",
        "website_card_projection_gate_microcosm",
        "demo_receipt_bounds_website_copy",
    ),
    (
        "website_card_projection_gate_microcosm",
        "thiel_evidence_packet_gate_microcosm",
        "projection_gate_blocks_application_overclaim",
    ),
    (
        "thiel_evidence_packet_gate_microcosm",
        "recipient_review_route_gate_microcosm",
        "application_packet_routes_controlled_review",
    ),
    (
        "recipient_review_route_gate_microcosm",
        "license_citation_disclosure_gate_microcosm",
        "recipient_review_requires_clearance",
    ),
    (
        "license_citation_disclosure_gate_microcosm",
        "hosted_public_ci_workflow_gate_microcosm",
        "clearance_precedes_hosted_public_check",
    ),
    (
        "hosted_public_ci_workflow_gate_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "hosted_boundary_feeds_package_manifest",
    ),
    (
        "hosted_public_ci_workflow_gate_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "hosted_remote_receipt_gate_feeds_package_manifest",
    ),
    (
        "hosted_public_ci_workflow_gate_microcosm",
        "external_public_clone_probe_receipt_microcosm",
        "external_clone_probe_gate_feeds_receipt_owner",
    ),
    (
        "external_public_clone_probe_receipt_microcosm",
        "hosted_public_remote_receipt_reconciliation_microcosm",
        "clone_probe_receipt_feeds_remote_receipt_reconciliation",
    ),
    (
        "hosted_public_remote_receipt_reconciliation_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "remote_receipt_reconciliation_blocks_package_export",
    ),
    (
        "hosted_public_remote_receipt_reconciliation_microcosm",
        "actual_public_remote_clone_execution_microcosm",
        "remote_receipt_reconciliation_feeds_actual_execution_gate",
    ),
    (
        "actual_public_remote_clone_execution_microcosm",
        "operator_public_remote_clone_execution_receipt_microcosm",
        "actual_execution_gate_feeds_operator_receipt_intake",
    ),
    (
        "operator_public_remote_clone_execution_receipt_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "operator_receipt_intake_blocks_package_export",
    ),
    (
        "actual_public_remote_clone_execution_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "actual_remote_clone_execution_blocks_package_export",
    ),
    (
        "external_public_clone_probe_receipt_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "external_clone_probe_gate_feeds_package_manifest",
    ),
    (
        "hosted_public_ci_workflow_gate_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "hosted_workflow_run_receipt_gate_feeds_package_manifest",
    ),
    (
        "hosted_public_ci_workflow_gate_microcosm",
        "release_artifact_integrity_witness_microcosm",
        "hosted_artifact_attestation_feeds_integrity_witness",
    ),
    (
        "release_artifact_integrity_witness_microcosm",
        "hosted_public_ci_workflow_gate_microcosm",
        "artifact_integrity_witness_feeds_hosted_claim_replay",
    ),
    (
        "release_artifact_integrity_witness_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "artifact_integrity_witness_blocks_package_export",
    ),
    (
        "public_release_package_manifest_gate_microcosm",
        "website_card_projection_gate_microcosm",
        "artifact_digest_requirement_blocks_website_launch_copy",
    ),
    (
        "website_card_projection_gate_microcosm",
        "hosted_public_ci_workflow_gate_microcosm",
        "artifact_digest_website_card_boundary_blocks_site_projection_deployment_inference",
    ),
    (
        "hosted_public_ci_workflow_gate_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "hosted_workflow_artifact_attestation_gate_feeds_package_manifest",
    ),
    (
        "hosted_public_ci_workflow_gate_microcosm",
        "website_card_projection_gate_microcosm",
        "deployment_receipt_gate_blocks_public_site_projection",
    ),
    (
        "provider_harness_evaluator_authority_split_microcosm",
        "source_capsule_provenance_microcosm",
        "provider_evaluator_cases_feed_source_capsule_boundary",
    ),
    (
        "source_capsule_provenance_microcosm",
        "recipient_review_route_gate_microcosm",
        "source_capsule_boundary_feeds_recipient_review",
    ),
    (
        "source_capsule_provenance_microcosm",
        "public_release_package_manifest_gate_microcosm",
        "source_capsule_boundary_feeds_package_projection_gate",
    ),
    (
        "source_capsule_provenance_microcosm",
        "website_card_projection_gate_microcosm",
        "source_capsule_boundary_feeds_website_card_gate",
    ),
    (
        "website_card_projection_gate_microcosm",
        "hosted_public_ci_workflow_gate_microcosm",
        "site_projection_source_capsules_feed_hosted_public_gate",
    ),
    (
        "provider_harness_evaluator_authority_split_microcosm",
        "source_shuttle_microcosm",
        "provider_evaluator_boundary_feeds_source_shuttle",
    ),
    (
        "source_shuttle_microcosm",
        "operator_public_remote_clone_execution_receipt_microcosm",
        "source_shuttle_bounds_operator_receipt_reentry",
    ),
    (
        "source_shuttle_microcosm",
        "recipient_review_route_gate_microcosm",
        "source_shuttle_packets_bound_recipient_evidence_graph",
    ),
)
ROUTE_CLIP_KEYS = (
    "case_count",
    "source_capsule_count",
    "capsule_count",
    "semantic_carryforward_count",
    "repair_route_count",
    "teaching_rule_count",
    "blocked_claim_count",
    "missing_ref_count",
    "public_release_claim_count",
    "publication_claim_count",
    "publication_permission_claim_count",
    "private_root_equivalence_claim_count",
    "benchmark_win_claim_count",
    "self_attestation_authority_count",
    "source_clip_hash_count",
    "semantic_packet_count",
    "semantic_packet_hash_count",
    "reentry_prompt_count",
    "loss_boundary_count",
    "no_private_copy_rule_count",
    "provider_self_attestation_authority_count",
    "website_card_self_authority_count",
    "hosted_claim_replay_site_projection_case_count",
    "site_projection_source_capsule_replay_count",
    "external_public_clone_probe_gate_case_count",
    "external_public_clone_probe_missing_field_count",
    "external_public_clone_probe_required_field_count",
    "external_public_clone_probe_receipt_case_count",
    "external_public_clone_probe_receipt_missing_ref_count",
    "external_public_clone_probe_source_gate_case_count",
    "grammar_replay_external_clone_receipt_case_count",
    "grammar_replay_external_clone_receipt_source_capsule_count",
    "grammar_replay_external_clone_receipt_semantic_carryforward_count",
    "grammar_replay_external_clone_receipt_failure_replay_count",
    "grammar_replay_external_clone_receipt_repair_route_count",
    "grammar_replay_external_clone_receipt_teaching_rule_count",
    "grammar_replay_external_clone_receipt_hash_verified_count",
    "grammar_replay_external_clone_receipt_blocked_claim_count",
    "grammar_replay_external_clone_receipt_self_attestation_authority_count",
    "grammar_replay_external_clone_receipt_public_release_claim_count",
    "grammar_replay_external_clone_receipt_publication_claim_count",
    "grammar_replay_external_clone_receipt_private_root_equivalence_claim_count",
    "grammar_replay_external_clone_receipt_benchmark_win_claim_count",
    "hosted_public_remote_receipt_reconciliation_case_count",
    "hosted_public_remote_receipt_reconciliation_missing_ref_count",
    "grammar_replay_remote_reconciliation_case_count",
    "grammar_replay_remote_reconciliation_source_capsule_count",
    "grammar_replay_remote_reconciliation_semantic_carryforward_count",
    "grammar_replay_remote_reconciliation_failure_replay_count",
    "grammar_replay_remote_reconciliation_repair_route_count",
    "grammar_replay_remote_reconciliation_teaching_rule_count",
    "grammar_replay_remote_reconciliation_hash_verified_count",
    "grammar_replay_remote_reconciliation_blocked_claim_count",
    "grammar_replay_remote_reconciliation_self_attestation_authority_count",
    "grammar_replay_remote_reconciliation_public_release_claim_count",
    "grammar_replay_remote_reconciliation_publication_claim_count",
    "grammar_replay_remote_reconciliation_private_root_equivalence_claim_count",
    "grammar_replay_remote_reconciliation_benchmark_win_claim_count",
    "remote_clone_alignment_required_field_count",
    "remote_clone_alignment_missing_field_count",
    "actual_public_remote_clone_execution_case_count",
    "actual_public_remote_clone_execution_missing_ref_count",
    "actual_public_remote_clone_execution_required_field_count",
    "actual_public_remote_clone_execution_missing_field_count",
    "grammar_replay_actual_execution_case_count",
    "grammar_replay_actual_execution_source_capsule_count",
    "grammar_replay_actual_execution_semantic_carryforward_count",
    "grammar_replay_actual_execution_failure_replay_count",
    "grammar_replay_actual_execution_repair_route_count",
    "grammar_replay_actual_execution_teaching_rule_count",
    "grammar_replay_actual_execution_hash_verified_count",
    "grammar_replay_actual_execution_blocked_claim_count",
    "grammar_replay_actual_execution_self_attestation_authority_count",
    "grammar_replay_actual_execution_public_release_claim_count",
    "grammar_replay_actual_execution_publication_claim_count",
    "grammar_replay_actual_execution_private_root_equivalence_claim_count",
    "grammar_replay_actual_execution_benchmark_win_claim_count",
    "observed_execution_ref_count",
    "execution_attempt_count",
    "operator_public_remote_clone_execution_receipt_case_count",
    "operator_public_remote_clone_execution_receipt_required_field_count",
    "operator_public_remote_clone_execution_receipt_missing_field_count",
    "operator_receipt_template_field_count",
    "operator_receipt_replay_case_count",
    "operator_receipt_replay_fail_closed_count",
    "operator_receipt_replay_authority_violation_count",
    "operator_receipt_replay_source_digest_mismatch_count",
    "synthetic_operator_receipt_schema_pass_count",
    "observed_operator_receipt_ref_count",
    "accepted_operator_receipt_count",
    "operator_receipt_authority_claim_violation_count",
    "source_digest_mismatch_count",
    "grammar_replay_operator_receipt_intake_case_count",
    "grammar_replay_operator_receipt_intake_source_capsule_count",
    "grammar_replay_operator_receipt_intake_semantic_carryforward_count",
    "grammar_replay_operator_receipt_intake_failure_replay_count",
    "grammar_replay_operator_receipt_intake_repair_route_count",
    "grammar_replay_operator_receipt_intake_teaching_rule_count",
    "grammar_replay_operator_receipt_intake_hash_verified_count",
    "grammar_replay_operator_receipt_intake_blocked_claim_count",
    "grammar_replay_operator_receipt_intake_self_attestation_authority_count",
    "grammar_replay_operator_receipt_intake_public_release_claim_count",
    "grammar_replay_operator_receipt_intake_publication_claim_count",
    "grammar_replay_operator_receipt_intake_private_root_equivalence_claim_count",
    "grammar_replay_operator_receipt_intake_benchmark_win_claim_count",
    "hosted_workflow_run_receipt_gate_case_count",
    "hosted_workflow_run_receipt_missing_field_count",
    "hosted_workflow_artifact_attestation_gate_case_count",
    "hosted_workflow_artifact_attestation_missing_field_count",
    "hosted_public_remote_receipt_gate_case_count",
    "remote_receipt_missing_field_count",
    "deployment_receipt_gate_case_count",
    "deployment_receipt_missing_field_count",
    "artifact_integrity_witness_case_count",
    "artifact_digest_requirement_bridge_case_count",
    "artifact_digest_requirement_bridge_source_capsule_count",
    "artifact_digest_requirement_bridge_semantic_carryforward_count",
    "artifact_digest_requirement_bridge_repair_route_count",
    "artifact_digest_requirement_bridge_teaching_rule_count",
    "artifact_digest_requirement_bridge_blocked_claim_count",
    "artifact_digest_requirement_bridge_source_witness_hash_preserved_count",
    "artifact_digest_requirement_bridge_package_row_attachment_count",
    "artifact_digest_requirement_bridge_missing_ref_count",
    "artifact_digest_site_projection_case_count",
    "artifact_digest_site_projection_source_witness_hash_preserved_count",
    "artifact_digest_site_projection_package_row_attachment_count",
    "artifact_digest_site_projection_blocked_claim_count",
    "artifact_digest_hosted_claim_replay_case_count",
    "artifact_digest_hosted_claim_replay_blocked_claim_count",
    "artifact_digest_hosted_claim_replay_source_witness_hash_preserved_count",
    "artifact_digest_hosted_claim_replay_package_row_attachment_count",
    "artifact_digest_hosted_claim_replay_self_attestation_authority_count",
    "grammar_replay_site_projection_hosted_claim_replay_case_count",
    "grammar_replay_site_projection_hosted_claim_replay_source_capsule_count",
    "grammar_replay_site_projection_hosted_claim_replay_semantic_carryforward_count",
    "grammar_replay_site_projection_hosted_claim_replay_failure_replay_count",
    "grammar_replay_site_projection_hosted_claim_replay_repair_route_count",
    "grammar_replay_site_projection_hosted_claim_replay_teaching_rule_count",
    "grammar_replay_site_projection_hosted_claim_replay_hash_verified_count",
    "grammar_replay_site_projection_hosted_claim_replay_blocked_claim_count",
    "grammar_replay_site_projection_hosted_claim_replay_self_attestation_authority_count",
    "grammar_replay_site_projection_hosted_claim_replay_public_release_claim_count",
    "grammar_replay_site_projection_hosted_claim_replay_publication_claim_count",
    "grammar_replay_site_projection_hosted_claim_replay_private_root_equivalence_claim_count",
    "grammar_replay_site_projection_hosted_claim_replay_benchmark_win_claim_count",
    "release_artifact_integrity_witness_hosted_claim_replay_case_count",
    "release_artifact_integrity_witness_hosted_claim_blocked_claim_count",
    "release_artifact_integrity_witness_source_case_count",
    "release_artifact_integrity_witness_hosted_claim_self_attestation_authority_count",
    "executable_grammar_replay_bridge_case_count",
    "executable_grammar_replay_bridge_source_capsule_count",
    "executable_grammar_replay_bridge_semantic_carryforward_count",
    "executable_grammar_replay_bridge_repair_route_count",
    "executable_grammar_replay_bridge_teaching_rule_count",
    "executable_grammar_replay_bridge_blocked_claim_count",
    "executable_grammar_replay_bridge_evaluator_authority_count",
    "executable_grammar_replay_bridge_self_attestation_authority_count",
    "grammar_replay_bridge_route_count",
    "grammar_replay_bridge_case_count",
    "grammar_replay_bridge_source_capsule_count",
    "grammar_replay_bridge_repair_route_count",
    "grammar_replay_bridge_teaching_rule_count",
    "grammar_replay_bridge_hash_verified_count",
    "grammar_replay_bridge_self_attestation_authority_count",
    "grammar_replay_demo_card_gate_projection_block_count",
    "grammar_replay_demo_card_gate_case_count",
    "grammar_replay_demo_card_gate_source_capsule_count",
    "grammar_replay_demo_card_gate_semantic_carryforward_count",
    "grammar_replay_demo_card_gate_repair_route_count",
    "grammar_replay_demo_card_gate_teaching_rule_count",
    "grammar_replay_demo_card_gate_blocked_claim_count",
    "grammar_replay_demo_card_gate_hash_verified_count",
    "grammar_replay_demo_card_gate_evaluator_authority_count",
    "grammar_replay_demo_card_gate_self_attestation_authority_count",
    "grammar_replay_demo_card_gate_public_release_claim_count",
    "grammar_replay_demo_card_gate_publication_claim_count",
    "grammar_replay_demo_card_gate_private_root_equivalence_claim_count",
    "grammar_replay_demo_card_gate_benchmark_win_claim_count",
    "grammar_replay_demo_card_gate_missing_ref_count",
    "grammar_replay_site_projection_case_count",
    "grammar_replay_site_projection_source_capsule_count",
    "grammar_replay_site_projection_semantic_carryforward_count",
    "grammar_replay_site_projection_failure_replay_count",
    "grammar_replay_site_projection_repair_route_count",
    "grammar_replay_site_projection_teaching_rule_count",
    "grammar_replay_site_projection_hash_verified_count",
    "grammar_replay_site_projection_blocked_claim_count",
    "grammar_replay_site_projection_self_attestation_authority_count",
    "grammar_replay_site_projection_public_release_claim_count",
    "grammar_replay_site_projection_publication_claim_count",
    "grammar_replay_site_projection_private_root_equivalence_claim_count",
    "grammar_replay_site_projection_benchmark_win_claim_count",
    "grammar_replay_site_projection_missing_ref_count",
)
MICROCOSM_ROUTE_BLUEPRINTS = (
    {
        "route_id": "route.failure_replay_to_benchmark_diagnostic",
        "source_candidate_id": "lab_evolve_failure_replay_graph_microcosm",
        "target_candidate_id": "verisoftbench_diagnostic_specimen_microcosm",
        "relationship": "failure_replay_localizes_benchmark_diagnostic",
        "pattern_family": "failure_replay_teaching",
        "evidence_refs": [
            "microcosms/lab_evolve_failure_replay/replay_graph.json",
            "microcosms/lab_evolve_failure_replay/receipt.json",
            "microcosms/verisoftbench_diagnostic/diagnostic_board.json",
            "microcosms/verisoftbench_diagnostic/receipt.json",
        ],
        "command_candidate_ids": [
            "lab_evolve_failure_replay_graph_microcosm",
            "verisoftbench_diagnostic_specimen_microcosm",
        ],
        "blocked_claims": [
            "failure replay proves benchmark superiority",
            "diagnostic localization is publication permission",
        ],
        "next_refinement": "attach additional failed benchmark variants only after evaluator receipts exist",
    },
    {
        "route_id": "route.provider_canary_to_concurrency_repair_loop",
        "source_candidate_id": "provider_harness_evaluator_authority_split_microcosm",
        "target_candidate_id": "concurrency_transaction_mission_control_microcosm",
        "relationship": "provider_rejection_opens_transaction_repair",
        "pattern_family": "provider_evaluator_authority_to_transaction_repair",
        "evidence_refs": [
            "microcosms/provider_harness_canary/canary_board.json",
            "microcosms/provider_harness_canary/receipt.json",
            "microcosms/concurrency_mission_control/provider_repair_bridge.json",
            "microcosms/concurrency_mission_control/mission_board.json",
            "microcosms/concurrency_mission_control/receipt.json",
        ],
        "command_candidate_ids": [
            "provider_harness_evaluator_authority_split_microcosm",
            "concurrency_transaction_mission_control_microcosm",
        ],
        "blocked_claims": [
            "provider self-attestation closes the transaction",
            "provider output bypasses evaluator rejection",
        ],
        "next_refinement": "route provider repair outcomes into recipient-facing evidence only through evaluator receipts",
    },
    {
        "route_id": "route.task_ledger_residual_to_concurrency_replay",
        "source_candidate_id": "task_ledger_cap_economy_microcosm",
        "target_candidate_id": "concurrency_transaction_mission_control_microcosm",
        "relationship": "task_residual_becomes_stale_lease_replay",
        "pattern_family": "work_metabolism_to_concurrency_control",
        "evidence_refs": [
            "microcosms/task_ledger_cap_economy/projection.json",
            "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json",
            "microcosms/task_ledger_cap_economy/receipt.json",
            "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json",
            "microcosms/concurrency_mission_control/work_metabolism_bridge.json",
            "microcosms/concurrency_mission_control/receipt.json",
        ],
        "command_candidate_ids": [
            "task_ledger_cap_economy_microcosm",
            "concurrency_transaction_mission_control_microcosm",
        ],
        "blocked_claims": [
            "open residual is completed work",
            "stale lease can mutate protected paths without a repair transaction",
        ],
        "next_refinement": "carry residual replay summaries into the next portfolio route recommender",
    },
    {
        "route_id": "route.executable_grammar_to_failure_teaching",
        "source_candidate_id": "executable_grammar_metabolism_microcosm",
        "target_candidate_id": "lab_evolve_failure_replay_graph_microcosm",
        "relationship": "grammar_failure_becomes_replay_teaching_rule",
        "pattern_family": "executable_grammar_to_failure_replay",
        "evidence_refs": [
            "microcosms/executable_grammar_metabolism/grammar_board.json",
            "microcosms/executable_grammar_metabolism/receipt.json",
            "microcosms/lab_evolve_failure_replay/replay_graph.json",
            "microcosms/lab_evolve_failure_replay/receipt.json",
        ],
        "command_candidate_ids": [
            "executable_grammar_metabolism_microcosm",
            "lab_evolve_failure_replay_graph_microcosm",
        ],
        "blocked_claims": [
            "grammar projection is its own validator",
            "failed case can be dropped instead of replayed",
        ],
        "next_refinement": "keep the grammar replay bridge synchronized with demo storyboard routes and website-card copy gates",
    },
    {
        "route_id": "route.grammar_replay_bridge_to_demo_storyboard",
        "source_candidate_id": "lab_evolve_failure_replay_graph_microcosm",
        "target_candidate_id": "demo_receipt_storyboard_microcosm",
        "relationship": "grammar_failure_replay_feeds_demo_teaching_route",
        "pattern_family": "executable_grammar_failure_replay_to_demo_router",
        "evidence_refs": [
            "microcosms/lab_evolve_failure_replay/replay_graph.json",
            "microcosms/lab_evolve_failure_replay/receipt.json",
            "microcosms/demo_receipt_storyboard/storyboard.json",
            "microcosms/demo_receipt_storyboard/receipt.json",
        ],
        "command_candidate_ids": [
            "lab_evolve_failure_replay_graph_microcosm",
            "demo_receipt_storyboard_microcosm",
        ],
        "blocked_claims": [
            "grammar replay bridge proves publication readiness",
            "demo storyboard can hide failed grammar cases",
            "demo route proves benchmark performance",
        ],
        "next_refinement": "feed demo-safe grammar teaching cases into website-card copy gates without making cards authority",
    },
    {
        "route_id": "route.demo_storyboard_to_website_card_gate",
        "source_candidate_id": "demo_receipt_storyboard_microcosm",
        "target_candidate_id": "website_card_projection_gate_microcosm",
        "relationship": "demo_receipt_bounds_website_card_copy",
        "pattern_family": "demo_route_to_public_projection_gate",
        "evidence_refs": [
            "microcosms/demo_receipt_storyboard/storyboard.json",
            "microcosms/demo_receipt_storyboard/receipt.json",
            "microcosms/website_card_projection_gate/card_gate.json",
            "microcosms/website_card_projection_gate/receipt.json",
        ],
        "command_candidate_ids": [
            "demo_receipt_storyboard_microcosm",
            "website_card_projection_gate_microcosm",
        ],
        "blocked_claims": [
            "demo narration is public launch copy",
            "website card can omit demo receipt boundaries",
            "website card can hide failed grammar cases",
            "grammar replay bridge approves website-card copy",
        ],
        "next_refinement": "carry grammar replay card-gate cases into site projection source capsules without granting hosted-public authority",
    },
    {
        "route_id": "route.recipient_evidence_to_package_manifest_bridge",
        "source_candidate_id": "recipient_review_route_gate_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "recipient_evidence_becomes_redacted_package_row",
        "pattern_family": "recipient_evidence_graph_to_package_manifest",
        "evidence_refs": [
            "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
            "microcosms/recipient_review_route_gate/recipient_packet_omission_receipt.json",
            "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
        ],
        "command_candidate_ids": [
            "recipient_review_route_gate_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "recipient evidence graph approves public send",
            "redacted package row can rehydrate private recipient fields",
        ],
        "next_refinement": "add reviewer-question routes that cite package rows without granting public send",
    },
    {
        "route_id": "route.package_promotion_to_website_card_copy_gate",
        "source_candidate_id": "public_release_package_manifest_gate_microcosm",
        "target_candidate_id": "website_card_projection_gate_microcosm",
        "relationship": "package_promotion_blocks_website_launch_copy",
        "pattern_family": "package_manifest_boundary_to_public_projection_gate",
        "evidence_refs": [
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/public_projection_handoff.json",
            "microcosms/website_card_projection_gate/card_gate.json",
            "microcosms/website_card_projection_gate/receipt.json",
            "state/site_projection_manifest.json",
            "receipts/site_projection_manifest_latest.json",
        ],
        "command_candidate_ids": [
            "public_release_package_manifest_gate_microcosm",
            "website_card_projection_gate_microcosm",
        ],
        "extra_commands": [
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-site-projection --root . --write-receipt",
        ],
        "blocked_claims": [
            "package promotion gate approves website public-launch copy",
            "sandbox site projection approves public package promotion",
        ],
        "next_refinement": "stabilize the package/site/card cycle into a generated build-order recommendation",
    },
    {
        "route_id": "route.site_projection_source_capsules_to_hosted_public_gate",
        "source_candidate_id": "website_card_projection_gate_microcosm",
        "target_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "relationship": "site_projection_source_capsules_replay_hosted_public_claims",
        "pattern_family": "public_projection_evidence_gate",
        "evidence_refs": [
            "microcosms/website_card_projection_gate/card_gate.json",
            "microcosms/website_card_projection_gate/receipt.json",
            "state/site_projection_manifest.json",
            "site/sandbox/site_projection_manifest.json",
            "site/sandbox/site_projection_bundle.json",
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
        ],
        "command_candidate_ids": [
            "website_card_projection_gate_microcosm",
        ],
        "extra_commands": [
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-site-projection --root . --write-receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-hosted-public-ci-workflow-gate-specimen --root . --write-receipt",
        ],
        "blocked_claims": [
            "site projection source capsule proves hosted public availability",
            "site projection source capsule proves public deployment",
            "source capsule hash grants publication permission",
            "site projection can hide failed grammar cases",
            "grammar replay card gate case grants publication permission",
        ],
        "next_refinement": "teach hosted-public replay to name individual grammar failure cases before any hosted-public route can reuse them",
    },
    {
        "route_id": "route.hosted_remote_receipt_gate_to_package_manifest",
        "source_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "hosted_remote_receipt_gate_blocks_package_export",
        "pattern_family": "public_projection_evidence_gate",
        "evidence_refs": [
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "hosted_public_ci_workflow_gate_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "hosted remote receipt skeleton proves package export readiness",
            "hosted remote receipt bypasses publication gate",
            "hosted CI run intent grants public release permission",
        ],
        "next_refinement": "add deployment receipt replay after a real hosted public remote receipt exists",
    },
    {
        "route_id": "route.external_public_clone_probe_to_package_manifest",
        "source_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "external_clone_probe_gate_blocks_package_export",
        "pattern_family": "public_projection_evidence_gate",
        "evidence_refs": [
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "receipts/cold_sandbox_probe_latest.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "hosted_public_ci_workflow_gate_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "external clone probe placeholder proves package export readiness",
            "local clone receipt proves unauthenticated public clone",
            "public remote visibility can bypass publication gate",
        ],
        "next_refinement": "add hosted workflow run receipt replay after an external clone probe exists",
    },
    {
        "route_id": "route.hosted_external_clone_gate_to_clone_probe_receipt",
        "source_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "target_candidate_id": "external_public_clone_probe_receipt_microcosm",
        "relationship": "external_clone_probe_gate_feeds_receipt_owner",
        "pattern_family": "external_public_clone_probe_receipt",
        "evidence_refs": [
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
            "microcosms/external_public_clone_probe_receipt/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "hosted_public_ci_workflow_gate_microcosm",
            "external_public_clone_probe_receipt_microcosm",
        ],
        "blocked_claims": [
            "external clone probe gate proves public clone availability",
            "external clone probe receipt proves hosted public remote availability",
            "external clone probe receipt grants publication permission",
        ],
        "next_refinement": "bind a real unauthenticated external clone probe only after public remote and publication gates remain explicitly fail-closed",
    },
    {
        "route_id": "route.clone_probe_receipt_to_remote_receipt_reconciliation",
        "source_candidate_id": "external_public_clone_probe_receipt_microcosm",
        "target_candidate_id": "hosted_public_remote_receipt_reconciliation_microcosm",
        "relationship": "clone_probe_receipt_feeds_remote_receipt_reconciliation",
        "pattern_family": "hosted_public_remote_receipt_reconciliation",
        "evidence_refs": [
            "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
            "microcosms/external_public_clone_probe_receipt/receipt.json",
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json",
            "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "external_public_clone_probe_receipt_microcosm",
            "hosted_public_remote_receipt_reconciliation_microcosm",
        ],
        "blocked_claims": [
            "external clone probe receipt proves hosted public remote availability",
            "hosted remote receipt skeleton proves public remote availability",
            "remote receipt reconciliation grants publication permission",
        ],
        "next_refinement": "bind an actual public remote and external clone execution receipt before changing hosted-public copy",
    },
    {
        "route_id": "route.remote_receipt_reconciliation_to_package_manifest",
        "source_candidate_id": "hosted_public_remote_receipt_reconciliation_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "remote_receipt_reconciliation_blocks_package_export",
        "pattern_family": "hosted_public_remote_receipt_reconciliation_to_package_manifest",
        "evidence_refs": [
            "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json",
            "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "hosted_public_remote_receipt_reconciliation_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "remote receipt reconciliation proves package export readiness",
            "remote receipt reconciliation bypasses package manifest review",
            "remote receipt reconciliation grants public release status",
        ],
        "next_refinement": "carry actual hosted-public remote receipts into package rows only after publication and export gates stay explicit",
    },
    {
        "route_id": "route.remote_receipt_reconciliation_to_actual_remote_clone_execution",
        "source_candidate_id": "hosted_public_remote_receipt_reconciliation_microcosm",
        "target_candidate_id": "actual_public_remote_clone_execution_microcosm",
        "relationship": "remote_receipt_reconciliation_feeds_actual_execution_gate",
        "pattern_family": "actual_public_remote_clone_execution",
        "evidence_refs": [
            "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json",
            "microcosms/hosted_public_remote_receipt_reconciliation/receipt.json",
            "microcosms/actual_public_remote_clone_execution/execution_board.json",
            "microcosms/actual_public_remote_clone_execution/receipt.json",
            "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "hosted_public_remote_receipt_reconciliation_microcosm",
            "actual_public_remote_clone_execution_microcosm",
        ],
        "blocked_claims": [
            "remote receipt reconciliation proves actual public clone execution",
            "actual public remote clone execution contract proves public remote availability",
            "actual public remote clone execution contract grants publication permission",
        ],
        "next_refinement": "replace the fail-closed execution contract with an operator-supplied outside-world execution receipt only after publication gates remain fail-closed",
    },
    {
        "route_id": "route.actual_remote_clone_execution_to_package_manifest",
        "source_candidate_id": "actual_public_remote_clone_execution_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "actual_remote_clone_execution_blocks_package_export",
        "pattern_family": "actual_public_remote_clone_execution_to_package_manifest",
        "evidence_refs": [
            "microcosms/actual_public_remote_clone_execution/execution_board.json",
            "microcosms/actual_public_remote_clone_execution/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "microcosms/hosted_public_remote_receipt_reconciliation/reconciliation_board.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "actual_public_remote_clone_execution_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "actual public clone execution approves package export",
            "actual public clone execution bypasses package manifest review",
            "actual public clone execution grants public release status",
        ],
        "next_refinement": "carry outside-world execution receipts into package rows without treating clone reproducibility as export or publication authority",
    },
    {
        "route_id": "route.actual_execution_to_operator_receipt_intake",
        "source_candidate_id": "actual_public_remote_clone_execution_microcosm",
        "target_candidate_id": "operator_public_remote_clone_execution_receipt_microcosm",
        "relationship": "actual_execution_gate_feeds_operator_receipt_intake",
        "pattern_family": "operator_public_remote_clone_execution_receipt_intake",
        "evidence_refs": [
            "microcosms/actual_public_remote_clone_execution/execution_board.json",
            "microcosms/actual_public_remote_clone_execution/receipt.json",
            "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json",
            "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json",
            "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json",
            "microcosms/operator_public_remote_clone_execution_receipt/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "actual_public_remote_clone_execution_microcosm",
            "operator_public_remote_clone_execution_receipt_microcosm",
        ],
        "blocked_claims": [
            "operator receipt intake proves public remote availability",
            "operator receipt intake proves unauthenticated clone success",
            "operator receipt intake grants publication permission",
        ],
        "next_refinement": "evaluate a real operator-supplied outside-world receipt only after source digests and redaction boundaries pass",
    },
    {
        "route_id": "route.operator_receipt_intake_to_package_manifest",
        "source_candidate_id": "operator_public_remote_clone_execution_receipt_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "operator_receipt_intake_blocks_package_export",
        "pattern_family": "operator_public_remote_clone_execution_receipt_to_package_manifest",
        "evidence_refs": [
            "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json",
            "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json",
            "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_replay_fixtures.json",
            "microcosms/operator_public_remote_clone_execution_receipt/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "operator_public_remote_clone_execution_receipt_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "operator receipt intake approves package export",
            "operator receipt intake bypasses package manifest review",
            "operator receipt intake grants public release or publication status",
        ],
        "next_refinement": "only after an accepted receipt exists, refresh package rows and publication gate separately",
    },
    {
        "route_id": "route.clone_probe_receipt_to_package_manifest",
        "source_candidate_id": "external_public_clone_probe_receipt_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "external_clone_probe_receipt_blocks_package_export",
        "pattern_family": "external_public_clone_probe_receipt_to_package_manifest",
        "evidence_refs": [
            "microcosms/external_public_clone_probe_receipt/clone_probe_receipt.json",
            "microcosms/external_public_clone_probe_receipt/receipt.json",
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "external_public_clone_probe_receipt_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "external clone probe receipt proves package export readiness",
            "external clone probe receipt bypasses package manifest review",
            "external clone probe receipt grants public release status",
        ],
        "next_refinement": "carry the clone probe receipt requirement into package rows without treating clone reproducibility as export or publication authority",
    },
    {
        "route_id": "route.hosted_workflow_run_receipt_gate_to_package_manifest",
        "source_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "hosted_workflow_run_receipt_gate_blocks_package_export",
        "pattern_family": "public_projection_evidence_gate",
        "evidence_refs": [
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "release/publication_gate.json",
            "receipts/validation_run.json",
        ],
        "command_candidate_ids": [
            "hosted_public_ci_workflow_gate_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "hosted workflow run receipt placeholder proves package export readiness",
            "local validator output proves hosted workflow conclusion",
            "hosted workflow run can bypass publication gate",
        ],
        "next_refinement": "add workflow artifact attestation after a real hosted workflow run receipt exists",
    },
    {
        "route_id": "route.hosted_workflow_artifact_attestation_gate_to_package_manifest",
        "source_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "hosted_workflow_artifact_attestation_gate_blocks_package_export",
        "pattern_family": "public_projection_evidence_gate",
        "evidence_refs": [
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "release/publication_gate.json",
            "receipts/validation_run.json",
        ],
        "command_candidate_ids": [
            "hosted_public_ci_workflow_gate_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "workflow artifact attestation placeholder proves release artifact integrity",
            "workflow artifact attestation placeholder proves package export readiness",
            "artifact digest can bypass package manifest review",
        ],
        "next_refinement": "route package-export language through the release artifact integrity witness and keep artifact evidence below package and publication authority",
    },
    {
        "route_id": "route.hosted_artifact_attestation_to_integrity_witness",
        "source_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "target_candidate_id": "release_artifact_integrity_witness_microcosm",
        "relationship": "hosted_artifact_attestation_feeds_integrity_witness",
        "pattern_family": "hosted_artifact_attestation_to_integrity_witness",
        "evidence_refs": [
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/release_artifact_integrity_witness/integrity_witness.json",
            "microcosms/release_artifact_integrity_witness/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "hosted_public_ci_workflow_gate_microcosm",
            "release_artifact_integrity_witness_microcosm",
        ],
        "blocked_claims": [
            "workflow artifact attestation placeholder proves release artifact integrity",
            "artifact digest can be self-attested",
            "artifact witness grants publication permission",
        ],
        "next_refinement": "bind a real artifact witness requirement into package-manifest promotion rows without granting public-release authority",
    },
    {
        "route_id": "route.artifact_integrity_witness_to_hosted_claim_gate",
        "source_candidate_id": "release_artifact_integrity_witness_microcosm",
        "target_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "relationship": "artifact_integrity_witness_replays_hosted_public_claims",
        "pattern_family": "artifact_integrity_witness_to_hosted_public_claim_gate",
        "evidence_refs": [
            "microcosms/release_artifact_integrity_witness/integrity_witness.json",
            "microcosms/release_artifact_integrity_witness/receipt.json",
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "site/sandbox/site_projection_receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "release_artifact_integrity_witness_microcosm",
            "hosted_public_ci_workflow_gate_microcosm",
        ],
        "blocked_claims": [
            "release artifact integrity witness proves hosted artifact attestation",
            "release artifact integrity witness approves package export",
            "release artifact integrity witness proves public deployment",
            "release artifact integrity witness grants public release status",
        ],
        "next_refinement": "bind an external public clone probe receipt without treating local artifact integrity as hosted-public authority",
    },
    {
        "route_id": "route.artifact_integrity_witness_to_package_manifest",
        "source_candidate_id": "release_artifact_integrity_witness_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "artifact_integrity_witness_blocks_package_export",
        "pattern_family": "artifact_integrity_witness_to_package_manifest",
        "evidence_refs": [
            "microcosms/release_artifact_integrity_witness/integrity_witness.json",
            "microcosms/release_artifact_integrity_witness/receipt.json",
            "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "release_artifact_integrity_witness_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "artifact witness approves package export",
            "artifact digest can bypass package manifest review",
            "artifact digest requirement bridge approves package export",
            "package manifest approves publication",
        ],
        "next_refinement": "route artifact digest requirements into website-card projection copy without creating launch authority",
    },
    {
        "route_id": "route.artifact_digest_requirement_to_website_card_gate",
        "source_candidate_id": "public_release_package_manifest_gate_microcosm",
        "target_candidate_id": "website_card_projection_gate_microcosm",
        "relationship": "artifact_digest_requirement_blocks_website_launch_copy",
        "pattern_family": "artifact_digest_requirement_to_website_card_projection_boundary",
        "evidence_refs": [
            "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "microcosms/release_artifact_integrity_witness/integrity_witness.json",
            "microcosms/release_artifact_integrity_witness/receipt.json",
            "state/artifact_manifest.json",
            "microcosms/website_card_projection_gate/card_gate.json",
            "microcosms/website_card_projection_gate/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "public_release_package_manifest_gate_microcosm",
            "website_card_projection_gate_microcosm",
        ],
        "blocked_claims": [
            "artifact digest requirement approves website launch copy",
            "artifact digest requirement can become website-card authority",
            "website card can turn digest requirement into public availability proof",
        ],
        "next_refinement": "carry the artifact digest website-card boundary into sandbox site projection without implying public deployment",
    },
    {
        "route_id": "route.artifact_digest_website_card_to_site_projection_gate",
        "source_candidate_id": "website_card_projection_gate_microcosm",
        "target_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "relationship": "artifact_digest_website_card_boundary_blocks_site_projection_deployment_inference",
        "pattern_family": "artifact_digest_requirement_to_site_projection_boundary",
        "evidence_refs": [
            "microcosms/website_card_projection_gate/card_gate.json",
            "microcosms/website_card_projection_gate/receipt.json",
            "state/site_projection_manifest.json",
            "site/sandbox/site_projection_manifest.json",
            "site/sandbox/site_projection_bundle.json",
            "site/sandbox/site_projection_receipt.json",
            "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "microcosms/release_artifact_integrity_witness/integrity_witness.json",
            "microcosms/release_artifact_integrity_witness/receipt.json",
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "state/artifact_manifest.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "public_release_package_manifest_gate_microcosm",
            "website_card_projection_gate_microcosm",
            "hosted_public_ci_workflow_gate_microcosm",
        ],
        "extra_commands": [
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-site-projection --root . --write-receipt",
        ],
        "blocked_claims": [
            "artifact digest website-card boundary proves site deployment",
            "site projection digest is deployment evidence",
            "artifact digest requirement proves hosted public availability",
            "site projection artifact digest boundary proves hosted public availability",
        ],
        "next_refinement": "bind real deployment, hosted-public remote, and publication receipts before allowing the replayed artifact-digest boundary to affect public copy",
    },
    {
        "route_id": "route.deployment_receipt_gate_to_site_projection",
        "source_candidate_id": "hosted_public_ci_workflow_gate_microcosm",
        "target_candidate_id": "website_card_projection_gate_microcosm",
        "relationship": "deployment_receipt_gate_blocks_public_site_projection",
        "pattern_family": "public_projection_evidence_gate",
        "evidence_refs": [
            "microcosms/hosted_public_ci_workflow_gate/hosted_claim_replay.json",
            "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
            "microcosms/hosted_public_ci_workflow_gate/receipt.json",
            "state/site_projection_manifest.json",
            "site/sandbox/site_projection_manifest.json",
            "site/sandbox/site_projection_receipt.json",
            "microcosms/website_card_projection_gate/card_gate.json",
            "microcosms/website_card_projection_gate/receipt.json",
            "release/publication_gate.json",
        ],
        "command_candidate_ids": [
            "hosted_public_ci_workflow_gate_microcosm",
            "website_card_projection_gate_microcosm",
        ],
        "extra_commands": [
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-site-projection --root . --write-receipt",
        ],
        "blocked_claims": [
            "deployment receipt placeholder proves public site availability",
            "site projection digest is deployment evidence",
            "website card projection bypasses deployment gate",
        ],
        "next_refinement": "add external public clone probe after real deployment receipt exists",
    },
    {
        "route_id": "route.claim_lattice_to_release_authority_handshake",
        "source_candidate_id": "status_preserving_control_plane_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "claim_boundary_constrains_package_authority",
        "pattern_family": "claim_inference_authority_lattice_to_public_gate",
        "evidence_refs": [
            "microcosms/status_preserving_control_plane/control_plane_board.json",
            "microcosms/status_preserving_control_plane/receipt.json",
            "microcosms/specimen_suite/claim_inference_map.json",
            "microcosms/status_preserving_control_plane/claim_inference_authority_lattice.json",
            "microcosms/public_release_package_manifest_gate/release_authority_handshake.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
        ],
        "command_candidate_ids": [
            "status_preserving_control_plane_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "claim lattice promotes package copy to public release authority",
            "authority handshake can bypass publication gate",
        ],
        "next_refinement": "route authority-handshake failures into portfolio missing-mechanism recommendations",
    },
    {
        "route_id": "route.source_capsule_provenance_to_recipient_evidence_graph",
        "source_candidate_id": "source_capsule_provenance_microcosm",
        "target_candidate_id": "recipient_review_route_gate_microcosm",
        "relationship": "source_capsules_bound_recipient_review_questions",
        "pattern_family": "source_capsule_provenance_to_recipient_evidence_graph",
        "evidence_refs": [
            "microcosms/source_capsule_provenance/capsule_board.json",
            "microcosms/source_capsule_provenance/receipt.json",
            "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
            "microcosms/recipient_review_route_gate/route_gate.json",
            "microcosms/recipient_review_route_gate/receipt.json",
            "state/release_candidate_portfolio.json",
        ],
        "command_candidate_ids": [
            "source_capsule_provenance_microcosm",
            "recipient_review_route_gate_microcosm",
        ],
        "blocked_claims": [
            "source capsule provenance approves recipient public send",
            "recipient reviewer can promote generated capsules to source authority",
            "source clip hash proves publication permission",
        ],
        "next_refinement": "carry source-capsule-backed recipient questions into packet omission receipts",
    },
    {
        "route_id": "route.source_capsule_provenance_to_package_projection_gate",
        "source_candidate_id": "source_capsule_provenance_microcosm",
        "target_candidate_id": "public_release_package_manifest_gate_microcosm",
        "relationship": "source_capsules_bound_package_projection_handoff",
        "pattern_family": "source_capsule_provenance_to_public_projection_gate",
        "evidence_refs": [
            "microcosms/source_capsule_provenance/capsule_board.json",
            "microcosms/source_capsule_provenance/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/public_projection_handoff.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "state/release_candidate_portfolio.json",
        ],
        "command_candidate_ids": [
            "source_capsule_provenance_microcosm",
            "public_release_package_manifest_gate_microcosm",
        ],
        "blocked_claims": [
            "source capsule provenance approves package promotion",
            "package projection can cite generated capsules as source authority",
            "source clip hash proves public release readiness",
        ],
        "next_refinement": "route source-capsule provenance into recipient evidence graph without granting public-send authority",
    },
    {
        "route_id": "route.source_capsule_provenance_to_website_card_gate",
        "source_candidate_id": "source_capsule_provenance_microcosm",
        "target_candidate_id": "website_card_projection_gate_microcosm",
        "relationship": "source_capsules_block_website_card_overclaim",
        "pattern_family": "source_capsule_provenance_to_website_card_gate",
        "evidence_refs": [
            "microcosms/source_capsule_provenance/capsule_board.json",
            "microcosms/source_capsule_provenance/receipt.json",
            "microcosms/website_card_projection_gate/card_gate.json",
            "microcosms/website_card_projection_gate/receipt.json",
            "release/publication_gate.json",
            "state/release_candidate_portfolio.json",
        ],
        "command_candidate_ids": [
            "source_capsule_provenance_microcosm",
            "website_card_projection_gate_microcosm",
        ],
        "blocked_claims": [
            "source capsule hash approves website public copy",
            "source capsule board can become website-card authority",
            "hashed source clip grants publication permission",
        ],
        "next_refinement": "route website-card source capsules into site projection without granting public-launch authority",
    },
    {
        "route_id": "route.provider_boundary_to_source_shuttle",
        "source_candidate_id": "provider_harness_evaluator_authority_split_microcosm",
        "target_candidate_id": "source_shuttle_microcosm",
        "relationship": "provider_evaluator_boundary_feeds_source_shuttle",
        "pattern_family": "provider_evaluator_authority_to_source_shuttle",
        "evidence_refs": [
            "microcosms/provider_harness_canary/canary_board.json",
            "microcosms/provider_harness_canary/receipt.json",
            "microcosms/source_shuttle/source_shuttle_board.json",
            "microcosms/source_shuttle/receipt.json",
            "state/release_candidate_portfolio.json",
        ],
        "command_candidate_ids": [
            "provider_harness_evaluator_authority_split_microcosm",
            "source_shuttle_microcosm",
        ],
        "blocked_claims": [
            "provider output can become shuttle authority without evaluator judgment",
            "semantic packet can promote provider self-attestation",
            "source shuttle grants public release or publication permission",
        ],
        "next_refinement": "let recipient evidence graph consume source-shuttle packets only as bounded reentry evidence",
    },
    {
        "route_id": "route.source_shuttle_to_operator_receipt_intake",
        "source_candidate_id": "source_shuttle_microcosm",
        "target_candidate_id": "operator_public_remote_clone_execution_receipt_microcosm",
        "relationship": "source_shuttle_bounds_operator_receipt_reentry",
        "pattern_family": "source_shuttle_to_operator_receipt_intake",
        "evidence_refs": [
            "microcosms/source_shuttle/source_shuttle_board.json",
            "microcosms/source_shuttle/receipt.json",
            "microcosms/operator_public_remote_clone_execution_receipt/receipt_intake_board.json",
            "microcosms/operator_public_remote_clone_execution_receipt/operator_receipt_template.json",
            "microcosms/operator_public_remote_clone_execution_receipt/receipt.json",
            "state/release_candidate_portfolio.json",
        ],
        "command_candidate_ids": [
            "source_shuttle_microcosm",
            "operator_public_remote_clone_execution_receipt_microcosm",
        ],
        "blocked_claims": [
            "source shuttle reentry prompt invents an outside-world receipt",
            "operator receipt intake can rehydrate omitted private fields",
            "source clip hash proves public remote availability",
        ],
        "next_refinement": "connect source-shuttle packets to recipient evidence graph with reviewer-visible loss boundaries",
    },
    {
        "route_id": "route.source_shuttle_to_recipient_evidence_graph",
        "source_candidate_id": "source_shuttle_microcosm",
        "target_candidate_id": "recipient_review_route_gate_microcosm",
        "relationship": "source_shuttle_packets_bound_recipient_evidence_graph",
        "pattern_family": "source_shuttle_to_recipient_evidence_graph",
        "evidence_refs": [
            "microcosms/source_shuttle/source_shuttle_board.json",
            "microcosms/source_shuttle/receipt.json",
            "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge.json",
            "microcosms/recipient_review_route_gate/source_shuttle_evidence_bridge_receipt.json",
            "microcosms/recipient_review_route_gate/recipient_evidence_graph.json",
            "state/release_candidate_portfolio.json",
        ],
        "command_candidate_ids": [
            "source_shuttle_microcosm",
            "recipient_review_route_gate_microcosm",
        ],
        "blocked_claims": [
            "source shuttle packet approves recipient public send",
            "recipient evidence graph can rehydrate omitted private fields",
            "semantic packet can become source authority",
            "source clip hash proves publication permission",
        ],
        "next_refinement": "carry source-shuttle bridge cases into recipient packet omission receipts without rehydrating private fields",
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _active_refs(values: list[Any]) -> list[Any]:
    return [
        value
        for value in values
        if not (isinstance(value, str) and any(token in value for token in RETIRED_REF_TOKENS))
    ]


def _external_review_potential(candidate: dict[str, Any]) -> Any:
    return candidate.get("external_review_potential")


def _teleology_gate(root: Path) -> dict[str, Any]:
    return _load_optional_json(root / TELEOLOGY_GATE_PATH)


def _retired_candidate_ids(root: Path) -> set[str]:
    gate = _teleology_gate(root)
    return {str(value) for value in _as_list(gate.get("retired_candidate_ids")) if isinstance(value, str)}


def _active_candidate_rows(root: Path, rows: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
    retired_ids = _retired_candidate_ids(root)
    active_rows: list[dict[str, Any]] = []
    retired_seen: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidate_id = str(row.get("candidate_id", ""))
        if candidate_id in retired_ids:
            retired_seen.append(candidate_id)
            continue
        active_rows.append(row)
    return active_rows, sorted(retired_seen)


def _nonempty_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _has_landed_microcosm_receipt(candidate: dict[str, Any]) -> bool:
    if candidate.get("runnability_status") != "cold_sandbox_passed":
        return False
    for receipt_ref in _as_list(candidate.get("receipt_refs")):
        if isinstance(receipt_ref, str) and receipt_ref.startswith("microcosms/") and receipt_ref.endswith("/receipt.json"):
            return True
    return False


def candidate_specimen_status(candidate: dict[str, Any]) -> str:
    """
    Classify whether a candidate should still be selected for specimen work.

    - When-needed: Open when a portfolio row needs a landed, blocked, or still-selectable specimen decision.
    - Escalates-to: registry/release_candidates.json; state/release_candidate_portfolio.json
    - Navigation-group: microcosm_support.release_selection
    - Validator: validator.release_candidates
    - Receipt: receipts/release_candidate_portfolio.json
    - Anti-claim: Specimen status is local portfolio state, not publication readiness or external proof.
    """
    if candidate.get("candidate_id") in LANDED_ROOT_PROOF_CANDIDATE_IDS:
        return "landed"
    if _has_landed_microcosm_receipt(candidate):
        return "landed"
    if candidate.get("projection_strategy") == "blocked" or candidate.get("public_safety_status") == "blocked":
        return "blocked"
    return "candidate"


def candidate_shape_failures(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return field-level release-candidate shape failures.

    - When-needed: Open when a release-candidate registry row fails validation or needs exact required-field rules.
    - Escalates-to: registry/release_candidates.json; state/release_candidate_portfolio.json
    - Navigation-group: microcosm_support.release_selection
    - Validator: validator.release_candidates
    - Receipt: receipts/release_candidate_portfolio.json
    - Anti-claim: Passing shape checks only means the candidate row is well-formed; it is not release approval.
    """
    failures: list[dict[str, Any]] = []
    candidate_id = candidate.get("candidate_id", "<missing>")
    for field in sorted(REQUIRED_FIELDS):
        if field not in candidate or candidate.get(field) in ("", None):
            failures.append({"candidate_id": candidate_id, "field": field, "reason": "missing required field"})

    summary = candidate.get("five_sentence_release_summary")
    if not _nonempty_strings(summary) or len(summary) != 5:
        failures.append({"candidate_id": candidate_id, "field": "five_sentence_release_summary", "reason": "must contain exactly five non-empty strings"})

    for field in ("source_refs", "python_refs", "standard_refs", "skill_refs", "concept_refs", "receipt_refs", "blocked_by", "anti_claims"):
        value = candidate.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            failures.append({"candidate_id": candidate_id, "field": field, "reason": "must be a string list"})
    for field in ("source_refs", "standard_refs", "next_action", "improvement_delta", "anti_claims", "cold_sandbox_status", "hosted_public_status", "publication_status"):
        value = candidate.get(field)
        if value in ("", None, []):
            failures.append({"candidate_id": candidate_id, "field": field, "reason": "must not be empty"})

    if candidate.get("projection_strategy") not in ALLOWED_PROJECTION_STRATEGIES:
        failures.append({"candidate_id": candidate_id, "field": "projection_strategy", "reason": "unknown projection strategy"})
    if candidate.get("release_priority") not in PRIORITY_POINTS:
        failures.append({"candidate_id": candidate_id, "field": "release_priority", "reason": "unknown release priority"})
    if candidate.get("video_demo_potential") not in POTENTIAL_POINTS:
        failures.append({"candidate_id": candidate_id, "field": "video_demo_potential", "reason": "unknown video potential"})
    if _external_review_potential(candidate) not in POTENTIAL_POINTS:
        failures.append({"candidate_id": candidate_id, "field": "external_review_potential", "reason": "unknown external-review potential"})

    vague_phrases = ("cool idea", "genius", "best one", "really good")
    text = " ".join(str(candidate.get(field, "")) for field in ("title", "idea_family", "improvement_delta", "next_action")).lower()
    text += " " + " ".join(str(item) for item in _as_list(candidate.get("five_sentence_release_summary"))).lower()
    for phrase in vague_phrases:
        if phrase in text:
            failures.append({"candidate_id": candidate_id, "reason": "candidate uses vague praise instead of mechanism", "phrase": phrase})
    return failures


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Attach portfolio score components and selector rationale to one candidate row.

    - When-needed: Open when explaining why one microcosm candidate outranks another or how evidence density affects selection.
    - Escalates-to: registry/release_candidates.json; state/release_candidate_portfolio.json; release/publication_gate.json
    - Navigation-group: microcosm_support.release_selection
    - Validator: validator.release_candidates
    - Receipt: receipts/release_candidate_portfolio.json
    - Anti-claim: A high score is prioritization guidance, not publication permission or hosted-public readiness.
    """
    receipt_refs = _as_list(candidate.get("receipt_refs"))
    standard_refs = _as_list(candidate.get("standard_refs"))
    concept_refs = _as_list(candidate.get("concept_refs"))
    python_refs = _as_list(candidate.get("python_refs"))
    source_refs = _active_refs(_as_list(candidate.get("source_refs")))
    blocked_by = _as_list(candidate.get("blocked_by"))
    external_review_potential = _external_review_potential(candidate)

    evidence_density = min(24, len(receipt_refs) * 4 + len(standard_refs) * 2 + len(python_refs) * 2 + len(source_refs))
    cold_start_gain = min(10, len(concept_refs) + len(standard_refs) + len(receipt_refs))
    blocker_penalty = min(20, len(blocked_by) * 5)
    score_components = {
        "release_priority": PRIORITY_POINTS.get(candidate.get("release_priority"), 0),
        "public_safety": SAFETY_POINTS.get(candidate.get("public_safety_status"), 0),
        "runnability": RUNNABILITY_POINTS.get(candidate.get("runnability_status"), 0),
        "projection_strategy": STRATEGY_POINTS.get(candidate.get("projection_strategy"), 0),
        "evidence_density": evidence_density,
        "agent_cold_start_gain": cold_start_gain,
        "external_review_evidence": POTENTIAL_POINTS.get(external_review_potential, 0),
        "visual_explainability": POTENTIAL_POINTS.get(candidate.get("video_demo_potential"), 0),
        "blocked_by_penalty": -blocker_penalty,
    }
    score = sum(score_components.values())
    output_candidate = dict(candidate)
    output_candidate["source_refs"] = source_refs
    output_candidate["receipt_refs"] = _active_refs(receipt_refs)
    output_candidate["external_review_potential"] = external_review_potential
    return {
        **output_candidate,
        "score": score,
        "score_components": score_components,
        "specimen_status": candidate_specimen_status(candidate),
        "selector_reason": _selector_reason(candidate, score_components),
    }


def _selector_reason(candidate: dict[str, Any], score_components: dict[str, int]) -> str:
    parts = [
        f"priority={candidate.get('release_priority')}",
        f"safety={candidate.get('public_safety_status')}",
        f"runnability={candidate.get('runnability_status')}",
        f"strategy={candidate.get('projection_strategy')}",
        f"evidence_density={score_components['evidence_density']}",
        f"specimen_status={candidate_specimen_status(candidate)}",
    ]
    if candidate.get("blocked_by"):
        parts.append("blocked_by_present")
    return "; ".join(parts)


def _disclosure_level(candidate: dict[str, Any]) -> str:
    public_safety_status = candidate.get("public_safety_status")
    if public_safety_status == "public_candidate_fail_closed":
        return "public_safe_fail_closed_projection"
    if public_safety_status == "sanitizable":
        return "sanitizable_private_review_projection"
    if public_safety_status == "blocked":
        return "blocked_from_public_projection"
    return "private_or_unknown_projection"


def _license_citation_review_status(candidate: dict[str, Any]) -> str:
    candidate_id = str(candidate.get("candidate_id", ""))
    if candidate_id == "license_citation_disclosure_gate_microcosm":
        return "local_clearance_gate_available_fail_closed"
    if candidate.get("publication_status") == "fail_closed_not_publication_authority":
        return "inherits_fail_closed_publication_boundary"
    return "review_required_before_public_copy"


def _recipient_classes(candidate: dict[str, Any]) -> list[str]:
    classes = {"sandbox_reviewer", "cold_agent"}
    if candidate.get("video_demo_potential") in {"high", "medium"}:
        classes.add("visual_reviewer")
    if _external_review_potential(candidate) == "high":
        classes.add("external_review_reader")
    return sorted(classes)


def _website_index_projection_status(candidate: dict[str, Any]) -> str:
    if candidate.get("specimen_status") == "landed":
        return "indexable_from_active_microcosm_portfolio"
    return "blocked_until_candidate_lands"


def _microcosm_portfolio_row(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id", ""))
    source_refs = _active_refs(_as_list(candidate.get("source_refs")))
    python_refs = _as_list(candidate.get("python_refs"))
    standard_refs = _as_list(candidate.get("standard_refs"))
    skill_refs = _as_list(candidate.get("skill_refs"))
    concept_refs = _as_list(candidate.get("concept_refs"))
    receipt_refs = _active_refs(_as_list(candidate.get("receipt_refs")))
    return {
        "portfolio_row_id": f"microcosm_portfolio.{candidate_id}",
        "candidate_id": candidate_id,
        "title": candidate.get("title"),
        "idea_family": candidate.get("idea_family"),
        "specimen_status": candidate.get("specimen_status"),
        "score": candidate.get("score"),
        "five_sentence_release_summary": candidate.get("five_sentence_release_summary"),
        "improvement_delta": candidate.get("improvement_delta"),
        "source_refs": source_refs,
        "python_refs": python_refs,
        "standard_refs": standard_refs,
        "skill_refs": skill_refs,
        "concept_refs": concept_refs,
        "receipt_refs": receipt_refs,
        "runnable_command": SPECIMEN_BUILD_COMMANDS.get(candidate_id, "no_runnable_command_registered"),
        "disclosure_level": _disclosure_level(candidate),
        "license_citation_review_status": _license_citation_review_status(candidate),
        "recipient_classes": _recipient_classes(candidate),
        "website_index_projection_status": _website_index_projection_status(candidate),
        "claim_boundary": {
            "authority_posture": "portfolio_index_projection_not_publication_or_private_root_authority",
            "hosted_public_status": candidate.get("hosted_public_status"),
            "publication_status": candidate.get("publication_status"),
            "public_safety_status": candidate.get("public_safety_status"),
            "anti_claims": candidate.get("anti_claims"),
        },
        "next_safe_action": candidate.get("next_action"),
        "ref_counts": {
            "source_ref_count": len(source_refs),
            "python_ref_count": len(python_refs),
            "standard_ref_count": len(standard_refs),
            "skill_ref_count": len(skill_refs),
            "concept_ref_count": len(concept_refs),
            "receipt_ref_count": len(receipt_refs),
        },
    }


def _pattern_family_index(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_counts = Counter(str(row.get("idea_family")) for row in rows)
    family_rows = []
    for idea_family in sorted(family_counts):
        members = [row for row in rows if row.get("idea_family") == idea_family]
        members.sort(key=lambda row: (-int(row.get("score") or 0), str(row.get("candidate_id") or "")))
        projection_strategy_counts = Counter(str(row.get("projection_strategy")) for row in members)
        family_rows.append(
            {
                "idea_family": idea_family,
                "microcosm_count": len(members),
                "candidate_ids": [str(row.get("candidate_id")) for row in members],
                "top_candidate_id": str(members[0].get("candidate_id")),
                "receipt_ref_count": sum(len(_as_list(row.get("receipt_refs"))) for row in members),
                "python_ref_count": sum(len(_as_list(row.get("python_refs"))) for row in members),
                "projection_strategy_counts": dict(sorted(projection_strategy_counts.items())),
                "disclosure_levels": sorted({_disclosure_level(row) for row in members}),
            }
        )
    return family_rows


def _verisoftbench_registry_record(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("candidate_id") == VERISOFTBENCH_CANDIDATE_ID:
            return {
                "candidate_id": VERISOFTBENCH_CANDIDATE_ID,
                "title": row.get("title"),
                "idea_family": row.get("idea_family"),
                "status": row.get("specimen_status"),
                "runnable_command": SPECIMEN_BUILD_COMMANDS[VERISOFTBENCH_CANDIDATE_ID],
                "source_refs": _as_list(row.get("source_refs")),
                "python_refs": _as_list(row.get("python_refs")),
                "receipt_refs": _as_list(row.get("receipt_refs")),
                "standard_refs": _as_list(row.get("standard_refs")),
                "failure_replay_refs": [
                    ref
                    for ref in _as_list(row.get("receipt_refs")) + _as_list(row.get("source_refs"))
                    if "failure_replay" in str(ref) or "provider_harness" in str(ref)
                ],
                "claim_boundary": {
                    "benchmark_score_claimed": False,
                    "benchmark_win_claimed": False,
                    "public_release_claimed": False,
                    "publication_status": row.get("publication_status"),
                    "hosted_public_status": row.get("hosted_public_status"),
                    "anti_claims": row.get("anti_claims"),
                },
                "next_safe_action": row.get("next_action"),
            }
    return {
        "candidate_id": VERISOFTBENCH_CANDIDATE_ID,
        "status": "missing",
        "reason": "candidate registry did not include the VeriSoftBench diagnostic specimen row",
    }


def _external_review_signal_node(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id", ""))
    return {
        "node_id": f"external_review_signal_microcosm.{candidate_id}",
        "candidate_id": candidate_id,
        "title": candidate.get("title"),
        "idea_family": candidate.get("idea_family"),
        "evidence_class": EXTERNAL_REVIEW_SIGNAL_NODE_CLASSES[candidate_id],
        "specimen_status": candidate.get("specimen_status"),
        "score": candidate.get("score"),
        "runnable_command": SPECIMEN_BUILD_COMMANDS.get(candidate_id, "no_runnable_command_registered"),
        "disclosure_level": _disclosure_level(candidate),
        "license_citation_review_status": _license_citation_review_status(candidate),
        "website_index_projection_status": _website_index_projection_status(candidate),
        "source_refs": _active_refs(_as_list(candidate.get("source_refs"))),
        "python_refs": _as_list(candidate.get("python_refs")),
        "standard_refs": _as_list(candidate.get("standard_refs")),
        "receipt_refs": _active_refs(_as_list(candidate.get("receipt_refs"))),
        "allowed_claim_tier": "controlled_private_review_evidence_pointer",
        "claim_boundary": {
            "authority_posture": "evidence_graph_projection_not_application_publication_or_private_root_authority",
            "public_release_claimed": False,
            "publication_permission_claimed": False,
            "private_root_equivalence_claimed": False,
            "benchmark_win_claimed": False,
            "hosted_public_status": candidate.get("hosted_public_status"),
            "publication_status": candidate.get("publication_status"),
            "anti_claims": candidate.get("anti_claims"),
        },
        "next_safe_action": candidate.get("next_action"),
    }


def _external_review_signal_graph(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_by_id = {str(row.get("candidate_id")): row for row in rows}
    expected_node_ids = set(EXTERNAL_REVIEW_SIGNAL_NODE_CLASSES) & set(row_by_id)
    nodes = [
        _external_review_signal_node(row_by_id[candidate_id])
        for candidate_id in sorted(expected_node_ids)
        if candidate_id in row_by_id
    ]
    node_ids = {node["candidate_id"] for node in nodes}
    edges = []
    for source_id, target_id, relationship in EXTERNAL_REVIEW_SIGNAL_EDGE_BLUEPRINTS:
        if source_id not in node_ids or target_id not in node_ids:
            continue
        edges.append(
            {
                "edge_id": f"external_review_signal_edge.{source_id}.{target_id}",
                "source_candidate_id": source_id,
                "target_candidate_id": target_id,
                "relationship": relationship,
                "claim_boundary": "edge preserves evidence dependency only; it is not proof of application approval, public release, hosted CI, benchmark performance, or private-root equivalence",
            }
    )
    missing_node_ids = sorted(expected_node_ids - node_ids)
    return {
        "schema_version": "external_review_signal_microcosm_graph_v0",
        "kind": "external_review_signal_microcosm_graph",
        "source_work_item_ref": EXTERNAL_REVIEW_SIGNAL_GRAPH_WORKITEM_REF,
        "authority_posture": "evidence_graph_projection_not_application_publication_or_private_root_authority",
        "source_registry_ref": "registry/release_candidates.json",
        "status": "ok" if not missing_node_ids else "warn",
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "landed_node_count": sum(1 for node in nodes if node.get("specimen_status") == "landed"),
            "runnable_command_count": sum(1 for node in nodes if node.get("runnable_command") != "no_runnable_command_registered"),
            "disclosure_boundary_count": sum(1 for node in nodes if node.get("disclosure_level")),
            "license_citation_review_status_count": sum(1 for node in nodes if node.get("license_citation_review_status")),
            "public_release_claim_count": 0,
            "publication_permission_claim_count": 0,
            "private_root_equivalence_claim_count": 0,
            "benchmark_win_claim_count": 0,
            "missing_node_count": len(missing_node_ids),
        },
        "nodes": nodes,
        "edges": edges,
        "missing_node_ids": missing_node_ids,
        "anti_claims": [
            "evidence graph is not a Thiel application approval",
            "evidence graph is not publication permission",
            "evidence graph is not hosted public CI proof",
            "evidence graph is not private-root equivalence",
            "evidence graph is not a benchmark result or benchmark win",
        ],
        "next_safe_action": "Use graph nodes as controlled-review evidence pointers; cite each node's receipt and gate boundary before writing application, website, or recipient copy.",
    }


def _safe_int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _source_count_family(source_counts: dict[str, int], *base_keys: str) -> int:
    total = 0
    for key, value in source_counts.items():
        if key in base_keys or any(key.endswith(f"_{base_key}") for base_key in base_keys):
            total += _safe_int(value)
    return total


def _json_summary_clip(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("status")
    if not isinstance(source, dict):
        source = payload.get("summary")
    if not isinstance(source, dict):
        source = payload.get("microcosm_portfolio_summary")
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in ROUTE_CLIP_KEYS if key in source}


def _route_source_clip(root: Path, evidence_refs: list[str]) -> tuple[str, str, dict[str, int], list[str]]:
    parts = []
    aggregate_counts: Counter[str] = Counter()
    missing_refs = []
    for ref in evidence_refs:
        path = root / ref
        if not path.exists():
            missing_refs.append(ref)
            parts.append(f"{ref}:missing")
            continue
        summary = {}
        if path.suffix == ".json":
            try:
                summary = _json_summary_clip(_load_json(path))
            except (json.JSONDecodeError, OSError):
                summary = {}
        for key, value in summary.items():
            if isinstance(value, int):
                aggregate_counts[key] += value
        if summary:
            parts.append(f"{ref}:{json.dumps(summary, sort_keys=True, separators=(',', ':'))}")
        else:
            parts.append(f"{ref}:exists")
    source_clip = " | ".join(parts)
    source_clip_hash = hashlib.sha256(source_clip.encode("utf-8")).hexdigest()
    return source_clip, source_clip_hash, dict(sorted(aggregate_counts.items())), missing_refs


def _route_commands(blueprint: dict[str, Any]) -> list[str]:
    commands = [
        SPECIMEN_BUILD_COMMANDS[candidate_id]
        for candidate_id in _as_list(blueprint.get("command_candidate_ids"))
        if isinstance(candidate_id, str) and candidate_id in SPECIMEN_BUILD_COMMANDS
    ]
    commands.extend(
        command
        for command in _as_list(blueprint.get("extra_commands"))
        if isinstance(command, str) and command
    )
    return commands


def _route_to_command_row(
    root: Path,
    row_by_id: dict[str, dict[str, Any]],
    blueprint: dict[str, Any],
) -> dict[str, Any]:
    source_candidate_id = str(blueprint["source_candidate_id"])
    target_candidate_id = str(blueprint["target_candidate_id"])
    evidence_refs = [str(ref) for ref in _as_list(blueprint.get("evidence_refs"))]
    source_clip, source_clip_hash, source_counts, missing_refs = _route_source_clip(root, evidence_refs)
    commands = _route_commands(blueprint)
    source_row = row_by_id.get(source_candidate_id, {})
    target_row = row_by_id.get(target_candidate_id, {})
    source_capsule_count = _source_count_family(source_counts, "source_capsule_count", "capsule_count")
    semantic_carryforward_count = _source_count_family(source_counts, "semantic_carryforward_count")
    repair_route_count = _source_count_family(source_counts, "repair_route_count")
    teaching_rule_count = _source_count_family(source_counts, "teaching_rule_count")
    blocked_claim_count = _source_count_family(source_counts, "blocked_claim_count")
    blocked_claims = [str(claim) for claim in _as_list(blueprint.get("blocked_claims"))]
    return {
        "route_id": blueprint["route_id"],
        "relationship": blueprint["relationship"],
        "pattern_family": blueprint["pattern_family"],
        "source_candidate_id": source_candidate_id,
        "target_candidate_id": target_candidate_id,
        "candidate_ids": [source_candidate_id, target_candidate_id],
        "source_specimen_status": source_row.get("specimen_status"),
        "target_specimen_status": target_row.get("specimen_status"),
        "status": "ready_local_fixture" if not missing_refs and commands else "missing_refs_or_commands",
        "first_command": commands[0] if commands else "no_runnable_command_registered",
        "command_sequence": commands,
        "runnable_command_count": len(commands),
        "evidence_refs": evidence_refs,
        "receipt_refs": [
            ref for ref in evidence_refs if ref.endswith("/receipt.json") or ref.startswith("receipts/")
        ],
        "missing_refs": missing_refs,
        "missing_ref_count": len(missing_refs),
        "source_clip": source_clip,
        "source_clip_hash": source_clip_hash,
        "source_counts": source_counts,
        "semantic_carryforward": {
            "relationship": blueprint["relationship"],
            "pattern_family": blueprint["pattern_family"],
            "source_capsule_count": source_capsule_count,
            "semantic_carryforward_count": semantic_carryforward_count,
            "repair_route_count": repair_route_count,
            "teaching_rule_count": teaching_rule_count,
            "blocked_claim_count": blocked_claim_count,
            "projection_not_authority": True,
            "public_release_claimed": False,
            "publication_claimed": False,
            "private_root_equivalence_claimed": False,
            "benchmark_win_claimed": False,
        },
        "claim_boundary": {
            "authority_posture": "route_to_command_projection_not_release_or_publication_authority",
            "projection_not_authority": True,
            "self_attestation_authority_count": 0,
            "public_release_claim_count": 0,
            "publication_permission_claim_count": 0,
            "private_root_equivalence_claim_count": 0,
            "benchmark_win_claim_count": 0,
            "anti_claims": blocked_claims,
        },
        "blocked_claims": blocked_claims,
        "next_refinement": blueprint["next_refinement"],
    }


def _pattern_route_matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_family.setdefault(str(row.get("pattern_family")), []).append(row)
    matrix = []
    for pattern_family, members in sorted(by_family.items()):
        candidate_ids = sorted(
            {
                candidate_id
                for member in members
                for candidate_id in _as_list(member.get("candidate_ids"))
                if isinstance(candidate_id, str)
            }
        )
        matrix.append(
            {
                "pattern_family": pattern_family,
                "route_count": len(members),
                "candidate_ids": candidate_ids,
                "runnable_command_count": sum(_safe_int(member.get("runnable_command_count")) for member in members),
                "evidence_ref_count": sum(len(_as_list(member.get("evidence_refs"))) for member in members),
                "missing_ref_count": sum(_safe_int(member.get("missing_ref_count")) for member in members),
                "source_clip_hash_count": sum(1 for member in members if member.get("source_clip_hash")),
            }
        )
    return matrix


def _route_to_command_index(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_by_id = {str(row.get("candidate_id")): row for row in rows}
    active_blueprints = [
        blueprint
        for blueprint in MICROCOSM_ROUTE_BLUEPRINTS
        if blueprint.get("source_candidate_id") in row_by_id and blueprint.get("target_candidate_id") in row_by_id
    ]
    route_rows = [
        _route_to_command_row(root, row_by_id, blueprint)
        for blueprint in active_blueprints
    ]
    pattern_matrix = _pattern_route_matrix(route_rows)
    missing_mechanism_classes = sorted(
        set(blueprint["pattern_family"] for blueprint in active_blueprints)
        - set(row["pattern_family"] for row in route_rows)
    )
    next_route = next(
        (
            row
            for row in route_rows
            if row["route_id"] == "route.provider_canary_to_concurrency_repair_loop"
        ),
        route_rows[0] if route_rows else {},
    )
    return {
        "schema_version": "microcosm_route_to_command_index_v0",
        "kind": "microcosm_route_to_command_index",
        "source_work_item_ref": MICROCOSM_PORTFOLIO_WORKITEM_REF,
        "authority_posture": "route_index_projection_not_publication_or_release_authority",
        "source_registry_ref": "registry/release_candidates.json",
        "generated_by": {
            "builder": "idea_microcosm.release_candidates",
            "source_refs": [
                "registry/release_candidates.json",
                "state/release_candidate_portfolio.json",
            ],
            "projection_not_authority": True,
        },
        "summary": {
            "route_count": len(route_rows),
            "ready_route_count": sum(1 for row in route_rows if row.get("status") == "ready_local_fixture"),
            "pattern_family_count": len(pattern_matrix),
            "runnable_command_count": sum(_safe_int(row.get("runnable_command_count")) for row in route_rows),
            "evidence_ref_count": sum(len(_as_list(row.get("evidence_refs"))) for row in route_rows),
            "receipt_ref_count": sum(len(_as_list(row.get("receipt_refs"))) for row in route_rows),
            "missing_ref_count": sum(_safe_int(row.get("missing_ref_count")) for row in route_rows),
            "source_clip_hash_count": sum(1 for row in route_rows if row.get("source_clip_hash")),
            "semantic_carryforward_route_count": sum(
                1 for row in route_rows if row.get("semantic_carryforward", {}).get("projection_not_authority") is True
            ),
            "public_release_claim_count": 0,
            "publication_permission_claim_count": 0,
            "private_root_equivalence_claim_count": 0,
            "benchmark_win_claim_count": 0,
            "next_route_recommendation_id": next_route.get("route_id"),
        },
        "routes": route_rows,
        "pattern_route_matrix": pattern_matrix,
        "missing_mechanism_classes": missing_mechanism_classes,
        "next_route_recommendation": {
            "route_id": next_route.get("route_id"),
            "relationship": next_route.get("relationship"),
            "first_command": next_route.get("first_command"),
            "next_refinement": next_route.get("next_refinement"),
            "authority_boundary": "recommendation chooses local review order only; it does not grant public-access clearance or public-claim authority",
        },
        "anti_claims": [
            "route-to-command index is not public-status clearance",
            "route-to-command index is not public-use permission",
            "route-to-command index is not hosted public CI proof",
            "route-to-command index is not private-root equivalence",
            "route-to-command index is not a benchmark result or benchmark win",
        ],
    }


def _build_microcosm_portfolio_index(scored: list[dict[str, Any]], *, root: Path) -> dict[str, Any]:
    rows = [_microcosm_portfolio_row(candidate) for candidate in scored]
    pattern_rows = _pattern_family_index(scored)
    verisoftbench_record = _verisoftbench_registry_record(scored)
    external_review_signal_graph = _external_review_signal_graph(scored)
    route_to_command_index = _route_to_command_index(root, scored)
    landed_count = sum(1 for row in rows if row.get("specimen_status") == "landed")
    runnable_command_count = sum(1 for row in rows if row.get("runnable_command") != "no_runnable_command_registered")
    return {
        "schema_version": "microcosm_portfolio_index_v0",
        "kind": "microcosm_portfolio_index",
        "source_work_item_ref": MICROCOSM_PORTFOLIO_WORKITEM_REF,
        "authority_posture": "portfolio_index_projection_not_publication_or_private_root_authority",
        "source_registry_ref": "registry/release_candidates.json",
        "summary": {
            "microcosm_record_count": len(rows),
            "landed_microcosm_count": landed_count,
            "pattern_family_count": len(pattern_rows),
            "runnable_command_count": runnable_command_count,
            "verisoftbench_record_count": 1 if verisoftbench_record.get("status") != "missing" else 0,
            "external_review_signal_graph_node_count": external_review_signal_graph["summary"]["node_count"],
            "external_review_signal_graph_edge_count": external_review_signal_graph["summary"]["edge_count"],
            "route_to_command_count": route_to_command_index["summary"]["route_count"],
            "route_to_command_ready_count": route_to_command_index["summary"]["ready_route_count"],
            "route_to_command_missing_ref_count": route_to_command_index["summary"]["missing_ref_count"],
            "route_to_command_source_clip_hash_count": route_to_command_index["summary"]["source_clip_hash_count"],
            "route_to_command_public_claim_count": 0,
            "public_release_claim_count": 0,
            "publication_permission_claim_count": 0,
            "private_root_equivalence_claim_count": 0,
        },
        "portfolio_rows": rows,
        "pattern_family_index": pattern_rows,
        "verisoftbench_registry_record": verisoftbench_record,
        "external_review_signal_microcosm_graph": external_review_signal_graph,
        "route_to_command_index": route_to_command_index,
        "anti_claims": [
            "portfolio index is not public release approval",
            "portfolio index is not hosted CI proof",
            "portfolio index is not publication permission",
            "portfolio index is not private-root equivalence",
            "benchmark diagnostic row is not a benchmark win claim",
            "external review evidence graph is not application approval",
            "route-to-command index is not public release approval",
        ],
    }


def build_release_candidate_portfolio(
    root: Path,
    *,
    output_path: str = "state/release_candidate_portfolio.json",
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    """
    Build the ranked candidate portfolio and optional receipt.

    - When-needed: Open when a root navigator, candidate card, or cold agent needs the current specimen-selection projection and next-specimen route.
    - Escalates-to: registry/release_candidates.json; state/release_candidate_portfolio.json; release/publication_gate.json; microcosms/specimen_suite/release_root_contract.json
    - Navigation-group: microcosm_support.release_selection
    - Validator: validator.release_candidates; validator.public_boundary
    - Receipt: receipts/release_candidate_portfolio.json
    - Anti-claim: The portfolio is a ranked projection, not a public-status source; it does not publish, approve recipients, prove hosted execution, or certify private-root equivalence.
    """
    root = root.resolve()
    generated_at = at or _utc_now()
    source_path = root / "registry" / "release_candidates.json"
    source = _load_json(source_path)
    source_rows = source.get("rows", [])
    candidates, retired_candidate_ids = _active_candidate_rows(root, source_rows if isinstance(source_rows, list) else [])
    failures: list[dict[str, Any]] = []
    if source.get("authority_posture") != "public_safe_candidate_source_registry_not_publication_claim":
        failures.append({"path": "registry/release_candidates.json", "reason": "candidate registry must not be a publication claim"})
    if not isinstance(source_rows, list) or not source_rows:
        failures.append({"path": "registry/release_candidates.json", "reason": "rows must be a non-empty list"})
        candidates = []

    seen_ids: set[str] = set()
    scored = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            failures.append({"path": "registry/release_candidates.json", "reason": "candidate row must be an object"})
            continue
        candidate_id = candidate.get("candidate_id")
        if candidate_id in seen_ids:
            failures.append({"candidate_id": candidate_id, "reason": "duplicate candidate_id"})
        seen_ids.add(str(candidate_id))
        failures.extend(candidate_shape_failures(candidate))
        scored.append(score_candidate(candidate))

    scored.sort(key=lambda row: (-int(row.get("score", 0)), str(row.get("candidate_id", ""))))
    top_candidate_id = scored[0]["candidate_id"] if scored else None
    implemented_specimen_candidate_ids = [
        str(candidate.get("candidate_id"))
        for candidate in scored
        if candidate.get("specimen_status") == "landed"
    ]
    next_specimen_candidate_id = None
    for candidate in scored:
        if candidate.get("specimen_status") == "candidate":
            next_specimen_candidate_id = candidate.get("candidate_id")
            candidate["specimen_status"] = "next_candidate"
            candidate["selector_reason"] = str(candidate.get("selector_reason", "")).replace(
                "specimen_status=candidate",
                "specimen_status=next_candidate",
            )
            break
    all_candidate_specimens_landed = bool(scored) and all(
        candidate.get("specimen_status") in {"landed", "blocked"}
        for candidate in scored
    )
    microcosm_portfolio_index = _build_microcosm_portfolio_index(scored, root=root)

    status = "ok" if not failures else "failed"
    portfolio = {
        "schema_version": "release_candidate_portfolio_v0",
        "kind": "release_candidate_portfolio",
        "generated_at": generated_at,
        "status": status,
        "source_ref": "registry/release_candidates.json",
        "authority_posture": "ranked_projection_not_publication_claim",
        "teleology_gate_ref": TELEOLOGY_GATE_PATH.as_posix(),
        "active_selection_scope": "system_organ_microcosms_only",
        "retired_candidate_ids": retired_candidate_ids,
        "retired_candidate_count": len(retired_candidate_ids),
        "selection_rule": "score = priority + public_safety + runnability + projection_strategy + evidence_density + cold_start_gain + explainability/review potential - blockers",
        "next_specimen_selection_rule": "skip landed root proofs, landed microcosm specimens, and blocked candidates; choose the highest-scored remaining candidate; when none remain, mark the portfolio terminal without making a publication claim",
        "candidate_count": len(scored),
        "source_candidate_count": len(source_rows) if isinstance(source_rows, list) else 0,
        "retired_candidate_count": len(retired_candidate_ids),
        "top_candidate_id": top_candidate_id,
        "next_specimen_candidate_id": next_specimen_candidate_id,
        "all_candidate_specimens_landed": all_candidate_specimens_landed,
        "implemented_specimen_candidate_ids": implemented_specimen_candidate_ids,
        "microcosm_portfolio_index": microcosm_portfolio_index,
        "microcosm_portfolio_summary": microcosm_portfolio_index["summary"],
        "public_safety_boundary": "This portfolio does not mark any candidate as ready for public release; publication remains gated by release/publication_gate.json and fresh probe receipts.",
        "runnability_boundary": "Runnability fields are local candidate status labels until clean-run, clone, and hosted-public receipts are fresh.",
        "candidates": scored,
        "failures": failures,
    }
    output = root / output_path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(portfolio, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result: dict[str, Any] = {
        "kind": "release_candidate_portfolio_build",
        "schema_version": "release_candidate_portfolio_build_v0",
        "generated_at": generated_at,
        "status": status,
        "output": output_path,
        "candidate_count": len(scored),
        "source_candidate_count": len(source_rows) if isinstance(source_rows, list) else 0,
        "retired_candidate_count": len(retired_candidate_ids),
        "top_candidate_id": top_candidate_id,
        "next_specimen_candidate_id": next_specimen_candidate_id,
        "all_candidate_specimens_landed": all_candidate_specimens_landed,
        "implemented_specimen_candidate_ids": implemented_specimen_candidate_ids,
        "microcosm_portfolio_record_count": microcosm_portfolio_index["summary"]["microcosm_record_count"],
        "microcosm_pattern_family_count": microcosm_portfolio_index["summary"]["pattern_family_count"],
        "microcosm_runnable_command_count": microcosm_portfolio_index["summary"]["runnable_command_count"],
        "verisoftbench_record_count": microcosm_portfolio_index["summary"]["verisoftbench_record_count"],
        "external_review_signal_graph_node_count": microcosm_portfolio_index["summary"]["external_review_signal_graph_node_count"],
        "external_review_signal_graph_edge_count": microcosm_portfolio_index["summary"]["external_review_signal_graph_edge_count"],
        "route_to_command_count": microcosm_portfolio_index["summary"]["route_to_command_count"],
        "route_to_command_ready_count": microcosm_portfolio_index["summary"]["route_to_command_ready_count"],
        "route_to_command_missing_ref_count": microcosm_portfolio_index["summary"]["route_to_command_missing_ref_count"],
        "failure_count": len(failures),
        "failures": failures,
    }
    if write_receipt:
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": "receipt.release_candidate_portfolio",
            "generated_at": generated_at,
            "owner": "idea_microcosm.release_candidates",
            "claim_ref": "idea.microcosm_self_application",
            "claim_tier": "fixture_projection",
            "command": "python -m idea_microcosm.cli build-release-candidates --root . --write-receipt",
            "result": status,
            "status": status,
            "evidence_refs": [
                "registry/release_candidates.json",
                "state/release_candidate_portfolio.json",
                "release/publication_gate.json",
            ],
            "omissions": [
                "This receipt ranks public-safe candidate records only; it does not publish, clone-test, or validate external novelty.",
                "Imaginations and private-root patterns may inspire improvement deltas but do not count as public evidence."
            ],
            "summary": {
                "candidate_count": len(scored),
                "source_candidate_count": len(source_rows) if isinstance(source_rows, list) else 0,
                "retired_candidate_count": len(retired_candidate_ids),
                "top_candidate_id": top_candidate_id,
                "next_specimen_candidate_id": next_specimen_candidate_id,
                "all_candidate_specimens_landed": all_candidate_specimens_landed,
                "implemented_specimen_candidate_ids": implemented_specimen_candidate_ids,
                "microcosm_portfolio_record_count": microcosm_portfolio_index["summary"]["microcosm_record_count"],
                "microcosm_pattern_family_count": microcosm_portfolio_index["summary"]["pattern_family_count"],
                "microcosm_runnable_command_count": microcosm_portfolio_index["summary"]["runnable_command_count"],
                "verisoftbench_record_count": microcosm_portfolio_index["summary"]["verisoftbench_record_count"],
                "external_review_signal_graph_node_count": microcosm_portfolio_index["summary"]["external_review_signal_graph_node_count"],
                "external_review_signal_graph_edge_count": microcosm_portfolio_index["summary"]["external_review_signal_graph_edge_count"],
                "route_to_command_count": microcosm_portfolio_index["summary"]["route_to_command_count"],
                "route_to_command_ready_count": microcosm_portfolio_index["summary"]["route_to_command_ready_count"],
                "route_to_command_missing_ref_count": microcosm_portfolio_index["summary"]["route_to_command_missing_ref_count"],
                "failure_count": len(failures),
            },
        }
        receipt_path = root / "receipts" / "release_candidate_portfolio.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result["receipt_written"] = "receipts/release_candidate_portfolio.json"
    return result
