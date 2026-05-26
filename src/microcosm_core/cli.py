from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path

from microcosm_core import project_substrate
from microcosm_core import runtime_shell
from microcosm_core.macro_tools import finance_eval_spine
from microcosm_core.macro_tools import work_landing_control_spine
from microcosm_core.organs import agent_benchmark_integrity_anti_gaming_replay
from microcosm_core.organs import agent_memory_temporal_conflict_replay
from microcosm_core.organs import agent_monitor_redteam_falsification_replay
from microcosm_core.organs import agent_route_observability_runtime
from microcosm_core.organs import agent_sabotage_scheming_monitor_replay
from microcosm_core.organs import agent_sandbox_policy_escape_replay
from microcosm_core.organs import (
    agentic_vulnerability_discovery_patch_proof_replay,
)
from microcosm_core.organs import belief_state_process_reward_replay
from microcosm_core.organs import bridge_phase_continuity_runtime
from microcosm_core.organs import certificate_kernel_execution_lab
from microcosm_core.organs import cold_reader_route_map
from microcosm_core.organs import corpus_readiness_mathlib_absence_gate
from microcosm_core.organs import executable_doctrine_grammar
from microcosm_core.organs import formal_math_lean_proof_witness
from microcosm_core.organs import formal_evidence_cell_anchor_resolver
from microcosm_core.organs import formal_math_premise_retrieval
from microcosm_core.organs import formal_math_readiness_gate
from microcosm_core.organs import formal_math_verifier_trace_repair_loop
from microcosm_core.organs import (
    indirect_prompt_injection_information_flow_policy_replay,
)
from microcosm_core.organs import lean_std_premise_index
from microcosm_core.organs import macro_projection_import_protocol
from microcosm_core.organs import materials_chemistry_closed_loop_lab_safety_replay
from microcosm_core.organs import mathematical_strategy_atlas_hypothesis_scorer
from microcosm_core.organs import mcp_tool_authority_replay
from microcosm_core.organs import mechanistic_interpretability_circuit_attribution_replay
from microcosm_core.organs import durable_agent_work_landing_replay
from microcosm_core.organs import mission_transaction_work_spine
from microcosm_core.organs import navigation_hologram_route_plane
from microcosm_core.organs import pattern_binding_contract
from microcosm_core.organs import prediction_oracle_reconciliation
from microcosm_core.organs import proof_diagnostic_evidence_spine
from microcosm_core.organs import proof_derived_governed_mutation_authorization
from microcosm_core.organs import provider_context_recipe_budget_policy
from microcosm_core.organs import public_reveal_walkthrough
from microcosm_core.organs import research_replication_rubric_artifact_replay
from microcosm_core.organs import ring2_premise_retrieval_precision_recall_harness
from microcosm_core.organs import sleeper_memory_poisoning_quarantine_replay
from microcosm_core.organs import spatial_world_model_counterfactual_simulation_replay
from microcosm_core.organs import standards_meta_diagnostics
from microcosm_core.organs import tactic_portfolio_availability_probe
from microcosm_core.organs import target_shape_tactic_routing_gate
from microcosm_core.organs import undeclared_library_prior_symbol_classifier
from microcosm_core.organs import verifier_lab_execution_spine
from microcosm_core.organs import verifier_lab_kernel
from microcosm_core.organs import voice_to_doctrine_self_improvement_loop
from microcosm_core.organs import world_model_projection_drift_control_room
from microcosm_core.validators import acceptance
from microcosm_core.validators import dependency_preflight
from microcosm_core.validators import fixture_freshness
from microcosm_core.validators import launch_compression
from microcosm_core.validators import observatory_legibility
from microcosm_core.validators import private_state_scan
from microcosm_core.validators import public_entry_docs
from microcosm_core.validators import research_kernel_density
from microcosm_core.validators import secret_exclusion_scan
from microcosm_core.validators import standards_registry
from microcosm_core.validators import transaction_evidence_stability


MICROCOSM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROOF_LAB_INPUT = (
    MICROCOSM_ROOT / "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
)
DEFAULT_PROOF_LAB_OUT = "/tmp/microcosm-proof-lab"

FIRST_SCREEN_HELP = """First-screen route:
  microcosm tour <project>        build .microcosm and inspect route/work/event/evidence/proof refs
  microcosm compile <project>     rebuild local .microcosm state
  microcosm status --card <project> read the compressed project/runtime status lens
  microcosm workingness           inspect behavior evidence and failure gaps
  microcosm serve <project>       open the local observatory
  microcosm proof-lab --out /tmp/microcosm-proof-lab

Boundaries: local-first only; no provider calls, source mutation, release,
hosting, proof-correctness, or credential-equivalent live-access authority.
Receipts are evidence drilldowns after the behavior route is visible.
"""

PUBLIC_LENS_COMMAND_HELP = (
    ("workingness", "show behavior evidence and failure modes"),
    ("prediction-lens", "inspect prediction ledger behavior and receipts"),
    ("market-boundary", "show source-open market-boundary anti-claim lens"),
    ("corpus-lens", "inspect corpus readiness and evidence density"),
    ("trace-lens", "inspect route/event trace evidence"),
    ("repair-loop", "show verifier trace repair-loop surface"),
    ("evidence-cells", "show formal evidence cell status"),
    ("proof-loop-depth", "inspect proof loop depth without proving correctness"),
    ("verifier-lab-execution-spine-lens", "show verifier lab execution spine lens"),
    ("landing-replay", "replay durable work-landing control behavior"),
    ("view-quality", "check observatory/read-model quality gates"),
    ("projection-safety", "inspect projection safety and exclusion guards"),
    ("drift-control", "show world-model projection drift controls"),
    ("spatial-simulation", "replay spatial world-model simulation specimen"),
    ("circuit-attribution", "replay mechanistic circuit attribution specimen"),
    ("route-cleanup", "show navigation route cleanup evidence"),
    ("projection-import-map", "map macro projection import cells"),
    ("import-projector", "run source-open projection import preview"),
    ("option-surface-lens", "inspect local option-surface routing lens"),
    ("stripping-guard", "show credential stripping boundary checks"),
    ("standards-control", "inspect standards control-plane diagnostics"),
    ("hook-coverage", "show hook coverage and guardrail evidence"),
    ("replay-gauntlet", "run accepted replay gauntlet surface"),
    ("benchmark-lab", "show benchmark integrity replay lab"),
    ("legibility-scorecard", "score first-screen legibility and gaps"),
    ("intake", "show runtime projection intake board"),
    ("reveal", "show public reveal walkthrough board"),
)


def _add_root_out(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)


def _add_input_out(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)


def _add_preflight(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--negative-matrix", required=True)
    parser.add_argument("--out", required=True)


def _add_public_lens_parsers(subparsers) -> None:
    for command, help_text in PUBLIC_LENS_COMMAND_HELP:
        subparsers.add_parser(command, help=help_text)


def _print_json(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "pass" else 1


def _public_ref(path_ref: str) -> str:
    path = Path(path_ref)
    try:
        relative = path.resolve(strict=False).relative_to(MICROCOSM_ROOT)
    except ValueError:
        return path_ref
    return relative.as_posix()


def _proof_lab_command(input_path: str, out_dir: str) -> str:
    display_input = _public_ref(input_path)
    if display_input == _public_ref(str(DEFAULT_PROOF_LAB_INPUT)):
        return f"microcosm proof-lab --out {out_dir}"
    return f"microcosm proof-lab --input {display_input} --out {out_dir}"


def _receipt_refs_for_out(result: dict, out_dir: str) -> list[str]:
    refs: list[str] = []
    base = str(out_dir)
    trimmed_base = base.rstrip("/")
    for receipt_path in result.get("receipt_paths") or []:
        name = Path(str(receipt_path)).name
        if not name:
            continue
        if trimmed_base:
            refs.append(f"{trimmed_base}/{name}")
        elif base.startswith("/"):
            refs.append(f"/{name}")
        else:
            refs.append(name)
    return refs


def _proof_lab_first_screen_card(
    result: dict,
    *,
    input_path: str,
    out_dir: str,
    command: str,
) -> dict:
    metrics = result.get("proof_lab_component_metrics") or {}
    receipt_refs = _receipt_refs_for_out(result, out_dir)
    if receipt_refs:
        evidence_drilldown = f"microcosm evidence inspect {shlex.quote(receipt_refs[0])}"
    else:
        evidence_drilldown = "microcosm evidence inspect <proof-lab-receipt>"
    return {
        "schema_version": "microcosm_proof_lab_first_screen_card_v1",
        "card_id": "first_screen_verifier_lab_kernel",
        "status": result.get("status"),
        "command": command,
        "expanded_command": (
            "microcosm verifier-lab-kernel run-kernel-bundle "
            f"--input {_public_ref(input_path)} --out {out_dir}"
        ),
        "endpoint": "/proof-lab",
        "alias_endpoints": ["/verifier-lab-kernel"],
        "source_lens_endpoint": "/proof-loop-depth",
        "input_ref": _public_ref(input_path),
        "out_ref": out_dir,
        "bundle_ref": runtime_shell.PROOF_LAB_BUNDLE_REF,
        "route_id": result.get("proof_lab_route_id"),
        "route_ref": runtime_shell.PROOF_LAB_ROUTE_REF,
        "receipt_ref": receipt_refs[0] if receipt_refs else None,
        "canonical_receipt_ref": runtime_shell.PROOF_LAB_RECEIPT_REF,
        "receipt_refs": receipt_refs,
        "proof_lab_route_id": result.get("proof_lab_route_id"),
        "proof_lab_route_component_count": result.get(
            "proof_lab_route_component_count"
        ),
        "lean_lake_return_code": result.get("lean_lake_return_code"),
        "lean_compiled_declaration_count": result.get(
            "lean_compiled_declaration_count"
        ),
        "component_metrics": {
            "corpus_count": metrics.get("corpus_count"),
            "retrieval_query_count": metrics.get("retrieval_query_count"),
            "ring2_mean_precision_at_k": metrics.get("ring2_mean_precision_at_k"),
            "proof_diagnostic_accepted_count": metrics.get(
                "proof_diagnostic_accepted_count"
            ),
        },
        "safe_to_show": {
            "body_in_receipt": result.get("body_in_receipt"),
            "proof_bodies_exported": False,
            "provider_payloads_exported": False,
            "credential_equivalent_payloads_exported": False,
            "route_metadata_visible": True,
            "receipt_refs_visible": True,
        },
        "authority_ceiling": result.get("authority_ceiling"),
        "anti_claim": result.get("anti_claim"),
        "reader_action": (
            "Use route_id, route_ref, and receipt_ref to verify the bounded "
            "proof-lab route, then drill into the receipt only after the "
            "first-screen card is visible."
        ),
        "next_commands": [
            "microcosm status --card",
            "microcosm proof-loop-depth",
            evidence_drilldown,
        ],
    }


def _status_card_proof_lab_front_door_ref(payload: dict) -> dict | None:
    proof_lab = payload.get("proof_lab")
    if not isinstance(proof_lab, dict):
        return None
    return {
        "schema_version": "microcosm_status_card_proof_lab_ref_v1",
        "status": proof_lab.get("status"),
        "command": proof_lab.get("command")
        or "microcosm proof-lab --out /tmp/microcosm-proof-lab",
        "endpoint": proof_lab.get("endpoint") or "/proof-lab",
        "alias_endpoints": proof_lab.get("alias_endpoints", []),
        "source_lens_endpoint": proof_lab.get("source_lens_endpoint"),
        "route_id": proof_lab.get("route_id"),
        "route_ref": proof_lab.get("route_ref"),
        "receipt_ref": proof_lab.get("receipt_ref"),
        "route_component_count": proof_lab.get("route_component_count"),
        "lean_lake_return_code": proof_lab.get("lean_lake_return_code"),
        "lean_compiled_declaration_count": proof_lab.get(
            "lean_compiled_declaration_count"
        ),
        "safe_to_show": {
            "route_metadata_visible": True,
            "receipt_refs_visible": True,
            "proof_bodies_exported": False,
            "provider_payload_bodies_exported": False,
            "credential_equivalent_payloads_exported": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
        "authority": (
            "first-screen proof-lab route reference only, not theorem proof "
            "authority, provider authority, release authority, or source "
            "mutation authority"
        ),
    }


def _status_card_observatory_front_door_ref(payload: dict) -> dict | None:
    front_door = payload.get("front_door")
    if not isinstance(front_door, dict):
        return None
    route_selection_proof = front_door.get("route_selection_proof")
    if not isinstance(route_selection_proof, dict):
        route_selection_proof = {}
    command = front_door.get("observatory_command")
    raw_selected_route_id = front_door.get("selected_route_id")
    selected_route_id = raw_selected_route_id or "<selected_route_id>"
    route_proof_status = route_selection_proof.get("status")
    status = (
        "pass"
        if command and route_proof_status == "pass"
        else "actionable"
        if command and not raw_selected_route_id
        else "missing_route_proof"
        if command
        else "missing_command"
    )
    return {
        "schema_version": "microcosm_status_card_observatory_ref_v1",
        "status": status,
        "command": command,
        "endpoint": "/project/observatory",
        "compact_endpoint": "/project/observatory-card",
        "html_endpoint": "/",
        "status_endpoint": "/status",
        "tour_endpoint": "/tour",
        "workingness_endpoint": "/workingness",
        "proof_lab_endpoint": "/proof-lab",
        "python_lens_endpoint": "/project/python-lens",
        "route_explanation_endpoint": f"/project/explain/{selected_route_id}",
        "first_screen_route_proof_ref": route_selection_proof.get(
            "observatory_route_proof_ref"
        ),
        "status_card_ref": "microcosm status --card <project>",
        "expected_model_fields": [
            "project_summary",
            "selected_route_id",
            "first_screen_route_proof",
            "front_door_status",
            "source_open_body_import_floor",
            "python_lens",
            "causal_chain",
            "graph_summary",
            "observatory_card",
            "json_drilldowns",
            "evidence_is_drilldown",
            "proof_loop_depth_lens",
            "runtime_bridge",
        ],
        "safe_to_show": {
            "project_local_state_refs_visible": True,
            "route_metadata_visible": True,
            "receipt_refs_visible": True,
            "body_text_exported_in_observatory": False,
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
        "authority": (
            "local observatory/read-model route reference only, not hosting, "
            "release, provider, source mutation, or proof-correctness authority"
        ),
        "reader_action": (
            "Open /project/observatory-card first for the compact route/work/"
            "evidence/graph/proof/status lens, then /project/observatory for "
            "the full read model."
        ),
    }


def _status_card_surface_is_nonblocking(status: object) -> bool:
    return status in {"pass", "clear", "actionable"}


def _attach_status_card_front_door_refs(payload: dict) -> dict:
    front_door = payload.get("front_door")
    if not isinstance(front_door, dict):
        return payload
    proof_lab_ref = _status_card_proof_lab_front_door_ref(payload)
    observatory_ref = _status_card_observatory_front_door_ref(payload)
    if proof_lab_ref is not None:
        front_door["proof_lab"] = proof_lab_ref
    if observatory_ref is not None:
        front_door["observatory"] = observatory_ref

    front_door_status = payload.get("front_door_status")
    if not isinstance(front_door_status, dict):
        return payload
    surface_statuses = front_door_status.get("surface_statuses")
    if not isinstance(surface_statuses, dict):
        surface_statuses = {}
    if proof_lab_ref is not None and proof_lab_ref.get("status") is not None:
        surface_statuses["proof_lab"] = proof_lab_ref.get("status")
    if observatory_ref is not None and observatory_ref.get("status") is not None:
        surface_statuses["observatory"] = observatory_ref.get("status")
    front_door_status["surface_statuses"] = surface_statuses
    front_door_status["blocking_surface_ids"] = [
        surface_id
        for surface_id, surface_status in surface_statuses.items()
        if not _status_card_surface_is_nonblocking(surface_status)
    ]
    front_door_status["actionable_surface_ids"] = [
        surface_id
        for surface_id, surface_status in surface_statuses.items()
        if surface_status == "actionable"
    ]
    front_door_status["status"] = (
        "pass" if not front_door_status["blocking_surface_ids"] else "blocked"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="microcosm",
        description=(
            "Local-first project substrate: repo -> .microcosm without provider "
            "calls or source mutation."
        ),
        epilog=FIRST_SCREEN_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("project")
    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("project")
    catalog_parser = subparsers.add_parser("catalog")
    catalog_parser.add_argument("project")
    architecture_parser = subparsers.add_parser("architecture")
    architecture_parser.add_argument("project")
    compile_parser = subparsers.add_parser(
        "compile",
        help="build local .microcosm project state",
    )
    compile_parser.add_argument("project")
    python_lens_parser = subparsers.add_parser(
        "python-lens",
        help="inspect public Python route/readiness metadata",
    )
    python_lens_parser.add_argument("project")
    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("project")
    explain_parser = subparsers.add_parser(
        "explain",
        help="show route -> work -> event -> evidence chain",
    )
    explain_parser.add_argument("project")
    explain_parser.add_argument("route_id")
    status_parser = subparsers.add_parser(
        "status",
        help="show runtime status or compact first-screen card",
    )
    status_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact first-screen status lens",
    )
    status_parser.add_argument("project", nargs="?")
    proof_lab_parser = subparsers.add_parser(
        "proof-lab",
        help="run the first-screen verifier proof lab",
    )
    proof_lab_parser.add_argument(
        "--input",
        default=str(DEFAULT_PROOF_LAB_INPUT),
        help="exported verifier lab bundle",
    )
    proof_lab_parser.add_argument(
        "--out",
        default=DEFAULT_PROOF_LAB_OUT,
        help="directory for proof-lab receipts",
    )
    subparsers.add_parser("spine", help="show accepted public runtime spine")
    tour_parser = subparsers.add_parser(
        "tour",
        help="run the compressed cold-reader route",
    )
    tour_parser.add_argument("project", nargs="?")
    subparsers.add_parser("authority", help="show authority ceilings and anti-claims")
    _add_public_lens_parsers(subparsers)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("project", nargs="?", default=runtime_shell.DEFAULT_PROJECT_REL)
    serve_parser = subparsers.add_parser(
        "serve",
        help="serve the local observatory over project state",
    )
    serve_parser.add_argument("project", nargs="?")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    patterns_parser = subparsers.add_parser("patterns")
    patterns_parser.add_argument("project", nargs="?")
    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("route_args", nargs="*")
    work_parser = subparsers.add_parser("work")
    work_subparsers = work_parser.add_subparsers(dest="work_command")
    work_subparsers.add_parser("demo")
    work_create_parser = work_subparsers.add_parser("create")
    work_create_parser.add_argument("project")
    work_create_parser.add_argument("--route")
    work_run_parser = work_subparsers.add_parser("run")
    work_run_parser.add_argument("project")
    work_run_parser.add_argument("--work-id")
    observe_parser = subparsers.add_parser("observe")
    observe_parser.add_argument("project")
    evidence_parser = subparsers.add_parser(
        "evidence",
        help="list or inspect evidence after behavior is visible",
    )
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_list_parser = evidence_subparsers.add_parser("list")
    evidence_list_parser.add_argument("project", nargs="?")
    evidence_inspect_parser = evidence_subparsers.add_parser("inspect")
    evidence_inspect_parser.add_argument("--project")
    evidence_inspect_parser.add_argument("receipt_ref")

    scan_parser = subparsers.add_parser("private-state-scan")
    scan_parser.add_argument("--root", required=True)
    scan_parser.add_argument("--out", required=True)
    scan_parser.add_argument("--policy")
    secret_scan_parser = subparsers.add_parser("secret-exclusion-scan")
    secret_scan_parser.add_argument("--root", required=True)
    secret_scan_parser.add_argument("--out", required=True)
    secret_scan_parser.add_argument("--policy")

    public_entry_parser = subparsers.add_parser("public-entry-docs")
    _add_root_out(public_entry_parser)
    density_parser = subparsers.add_parser("research-kernel-density")
    _add_root_out(density_parser)
    density_parser.add_argument("--project")
    stability_parser = subparsers.add_parser("transaction-evidence-stability")
    _add_root_out(stability_parser)
    stability_parser.add_argument("--project", required=True)
    observatory_parser = subparsers.add_parser("observatory-legibility")
    _add_root_out(observatory_parser)
    observatory_parser.add_argument("--project", required=True)
    launch_parser = subparsers.add_parser("launch-compression")
    _add_root_out(launch_parser)
    launch_parser.add_argument("--project", required=True)

    standards_parser = subparsers.add_parser("standards-registry")
    standards_parser.add_argument("--registry", required=True)
    standards_parser.add_argument("--standards-dir", required=True)
    standards_parser.add_argument("--acceptance", required=True)
    standards_parser.add_argument("--out", required=True)

    dependency_parser = subparsers.add_parser("dependency-preflight")
    _add_preflight(dependency_parser)

    freshness_parser = subparsers.add_parser("fixture-freshness")
    _add_preflight(freshness_parser)
    freshness_parser.add_argument("--mission-dag", required=True)
    freshness_parser.add_argument("--receipt-coverage", required=True)

    organ_parser = subparsers.add_parser("pattern-binding")
    organ_parser.add_argument(
        "action",
        choices=[
            "validate",
            "validate-substrate-bundle",
            "validate-route-readiness-bundle",
        ],
    )
    _add_input_out(organ_parser)
    route_readiness_parser = subparsers.add_parser("pattern-route-readiness")
    route_readiness_parser.add_argument("action", choices=["validate-bundle"])
    _add_input_out(route_readiness_parser)

    finance_eval_parser = subparsers.add_parser("finance-eval-spine")
    finance_eval_parser.add_argument("action", choices=["validate-finance-eval-bundle"])
    _add_input_out(finance_eval_parser)
    work_landing_control_parser = subparsers.add_parser("work-landing-control-spine")
    work_landing_control_parser.add_argument("action", choices=["validate-control-bundle"])
    _add_input_out(work_landing_control_parser)

    grammar_parser = subparsers.add_parser("executable-doctrine-grammar")
    grammar_parser.add_argument(
        "action",
        choices=[
            "validate",
            "validate-standards-bundle",
            "validate-executable-grammar-metabolism-bundle",
        ],
    )
    _add_input_out(grammar_parser)

    proof_parser = subparsers.add_parser("proof-diagnostic-evidence-spine")
    proof_parser.add_argument("action", choices=["run", "run-evidence-bundle"])
    _add_input_out(proof_parser)

    formal_math_parser = subparsers.add_parser("formal-math-readiness-gate")
    formal_math_parser.add_argument("action", choices=["run", "run-readiness-bundle", "plan"])
    formal_math_parser.add_argument("--input", required=True)
    formal_math_parser.add_argument("--out")

    corpus_readiness_parser = subparsers.add_parser("corpus-readiness-mathlib-absence-gate")
    corpus_readiness_parser.add_argument("action", choices=["run", "run-projection-bundle"])
    _add_input_out(corpus_readiness_parser)

    strategy_atlas_parser = subparsers.add_parser("mathematical-strategy-atlas-hypothesis-scorer")
    strategy_atlas_parser.add_argument("action", choices=["run", "run-strategy-bundle"])
    _add_input_out(strategy_atlas_parser)

    tactic_portfolio_parser = subparsers.add_parser("tactic-portfolio-availability-probe")
    tactic_portfolio_parser.add_argument("action", choices=["run", "run-availability-bundle"])
    _add_input_out(tactic_portfolio_parser)

    target_shape_parser = subparsers.add_parser("target-shape-tactic-routing-gate")
    target_shape_parser.add_argument("action", choices=["run", "run-routing-bundle"])
    _add_input_out(target_shape_parser)

    lean_witness_parser = subparsers.add_parser("formal-math-lean-proof-witness")
    lean_witness_parser.add_argument("action", choices=["run", "run-witness-bundle"])
    _add_input_out(lean_witness_parser)

    premise_retrieval_parser = subparsers.add_parser("formal-math-premise-retrieval")
    premise_retrieval_parser.add_argument("action", choices=["run", "run-retrieval-bundle"])
    _add_input_out(premise_retrieval_parser)

    verifier_trace_parser = subparsers.add_parser("formal-math-verifier-trace-repair-loop")
    verifier_trace_parser.add_argument("action", choices=["run", "run-loop-bundle"])
    _add_input_out(verifier_trace_parser)

    verifier_lab_parser = subparsers.add_parser("verifier-lab-kernel")
    verifier_lab_parser.add_argument("action", choices=["run", "run-kernel-bundle"])
    _add_input_out(verifier_lab_parser)
    verifier_lab_parser.add_argument("--acceptance-out")

    verifier_lab_execution_parser = subparsers.add_parser(
        "verifier-lab-execution-spine"
    )
    verifier_lab_execution_parser.add_argument(
        "action", choices=["run", "run-execution-bundle"]
    )
    _add_input_out(verifier_lab_execution_parser)
    verifier_lab_execution_parser.add_argument("--acceptance-out")

    certificate_kernel_parser = subparsers.add_parser("certificate-kernel-execution-lab")
    certificate_kernel_parser.add_argument(
        "action", choices=["run", "run-certificate-bundle"]
    )
    _add_input_out(certificate_kernel_parser)
    certificate_kernel_parser.add_argument("--acceptance-out")

    evidence_cell_parser = subparsers.add_parser("formal-evidence-cell-anchor-resolver")
    evidence_cell_parser.add_argument("action", choices=["run", "run-anchor-bundle"])
    _add_input_out(evidence_cell_parser)

    symbol_classifier_parser = subparsers.add_parser("undeclared-library-prior-symbol-classifier")
    symbol_classifier_parser.add_argument("action", choices=["run", "run-symbol-bundle"])
    _add_input_out(symbol_classifier_parser)
    symbol_classifier_parser.add_argument("--acceptance-out")

    benchmark_integrity_parser = subparsers.add_parser(
        "agent-benchmark-integrity-anti-gaming-replay"
    )
    benchmark_integrity_parser.add_argument(
        "action", choices=["run", "run-benchmark-integrity-bundle"]
    )
    _add_input_out(benchmark_integrity_parser)
    benchmark_integrity_parser.add_argument("--acceptance-out")

    monitor_redteam_parser = subparsers.add_parser(
        "agent-monitor-redteam-falsification-replay"
    )
    monitor_redteam_parser.add_argument(
        "action", choices=["run", "run-monitor-bundle"]
    )
    _add_input_out(monitor_redteam_parser)
    monitor_redteam_parser.add_argument("--acceptance-out")

    sabotage_monitor_parser = subparsers.add_parser(
        "agent-sabotage-scheming-monitor-replay"
    )
    sabotage_monitor_parser.add_argument(
        "action", choices=["run", "run-sabotage-bundle"]
    )
    _add_input_out(sabotage_monitor_parser)
    sabotage_monitor_parser.add_argument("--acceptance-out")

    sandbox_policy_parser = subparsers.add_parser(
        "agent-sandbox-policy-escape-replay"
    )
    sandbox_policy_parser.add_argument(
        "action", choices=["run", "run-sandbox-bundle"]
    )
    _add_input_out(sandbox_policy_parser)
    sandbox_policy_parser.add_argument("--acceptance-out")

    prompt_injection_parser = subparsers.add_parser(
        "indirect-prompt-injection-information-flow-policy-replay"
    )
    prompt_injection_parser.add_argument(
        "action", choices=["run", "run-prompt-injection-bundle"]
    )
    _add_input_out(prompt_injection_parser)
    prompt_injection_parser.add_argument("--acceptance-out")

    agentic_vuln_parser = subparsers.add_parser(
        "agentic-vulnerability-discovery-patch-proof-replay"
    )
    agentic_vuln_parser.add_argument(
        "action", choices=["run", "run-patch-proof-bundle"]
    )
    _add_input_out(agentic_vuln_parser)
    agentic_vuln_parser.add_argument("--acceptance-out")

    memory_conflict_parser = subparsers.add_parser(
        "agent-memory-temporal-conflict-replay"
    )
    memory_conflict_parser.add_argument(
        "action", choices=["run", "run-memory-bundle"]
    )
    _add_input_out(memory_conflict_parser)
    memory_conflict_parser.add_argument("--acceptance-out")

    sleeper_memory_parser = subparsers.add_parser(
        "sleeper-memory-poisoning-quarantine-replay"
    )
    sleeper_memory_parser.add_argument(
        "action", choices=["run", "run-quarantine-bundle"]
    )
    _add_input_out(sleeper_memory_parser)
    sleeper_memory_parser.add_argument("--acceptance-out")

    mcp_tool_parser = subparsers.add_parser("mcp-tool-authority-replay")
    mcp_tool_parser.add_argument(
        "action", choices=["run", "run-tool-authority-bundle"]
    )
    _add_input_out(mcp_tool_parser)
    mcp_tool_parser.add_argument("--acceptance-out")

    governed_mutation_parser = subparsers.add_parser(
        "proof-derived-governed-mutation-authorization"
    )
    governed_mutation_parser.add_argument(
        "action", choices=["run", "run-authorization-bundle"]
    )
    _add_input_out(governed_mutation_parser)
    governed_mutation_parser.add_argument("--acceptance-out")

    belief_reward_parser = subparsers.add_parser(
        "belief-state-process-reward-replay"
    )
    belief_reward_parser.add_argument("action", choices=["run", "run-reward-bundle"])
    _add_input_out(belief_reward_parser)
    belief_reward_parser.add_argument("--acceptance-out")

    lean_std_index_parser = subparsers.add_parser("lean-std-premise-index")
    lean_std_index_parser.add_argument("action", choices=["run", "run-index-bundle"])
    _add_input_out(lean_std_index_parser)

    provider_context_parser = subparsers.add_parser("provider-context-recipe-budget-policy")
    provider_context_parser.add_argument("action", choices=["run", "run-budget-bundle"])
    _add_input_out(provider_context_parser)

    ring2_parser = subparsers.add_parser("ring2-premise-retrieval-precision-recall-harness")
    ring2_parser.add_argument("action", choices=["run", "run-precision-recall-bundle"])
    _add_input_out(ring2_parser)

    durable_landing_parser = subparsers.add_parser("durable-agent-work-landing-replay")
    durable_landing_parser.add_argument("action", choices=["run", "run-work-landing-bundle"])
    _add_input_out(durable_landing_parser)
    durable_landing_parser.add_argument("--acceptance-out")

    research_replication_parser = subparsers.add_parser(
        "research-replication-rubric-artifact-replay"
    )
    research_replication_parser.add_argument(
        "action", choices=["run", "run-replication-bundle"]
    )
    _add_input_out(research_replication_parser)
    research_replication_parser.add_argument("--acceptance-out")

    drift_control_room_parser = subparsers.add_parser(
        "world-model-projection-drift-control-room"
    )
    drift_control_room_parser.add_argument(
        "action", choices=["run", "run-drift-control-bundle"]
    )
    _add_input_out(drift_control_room_parser)
    drift_control_room_parser.add_argument("--acceptance-out")

    spatial_simulation_parser = subparsers.add_parser(
        "spatial-world-model-counterfactual-simulation-replay"
    )
    spatial_simulation_parser.add_argument(
        "action", choices=["run", "run-simulation-bundle"]
    )
    _add_input_out(spatial_simulation_parser)
    spatial_simulation_parser.add_argument("--acceptance-out")

    materials_lab_safety_parser = subparsers.add_parser(
        "materials-chemistry-closed-loop-lab-safety-replay"
    )
    materials_lab_safety_parser.add_argument(
        "action", choices=["run", "run-lab-bundle"]
    )
    _add_input_out(materials_lab_safety_parser)
    materials_lab_safety_parser.add_argument("--acceptance-out")

    circuit_attribution_parser = subparsers.add_parser(
        "mechanistic-interpretability-circuit-attribution-replay"
    )
    circuit_attribution_parser.add_argument(
        "action", choices=["run", "run-attribution-bundle"]
    )
    _add_input_out(circuit_attribution_parser)
    circuit_attribution_parser.add_argument("--acceptance-out")

    public_reveal_parser = subparsers.add_parser("public-reveal-walkthrough")
    public_reveal_parser.add_argument("action", choices=["run", "run-reveal-bundle"])
    _add_input_out(public_reveal_parser)

    macro_projection_parser = subparsers.add_parser("macro-projection-import-protocol")
    macro_projection_parser.add_argument("action", choices=["run", "run-projection-bundle", "plan"])
    macro_projection_parser.add_argument("--input", required=True)
    macro_projection_parser.add_argument("--out")

    prediction_parser = subparsers.add_parser("prediction-oracle-reconciliation")
    prediction_parser.add_argument("action", choices=["run", "run-prediction-bundle"])
    _add_input_out(prediction_parser)

    standards_meta_parser = subparsers.add_parser("standards-meta-diagnostics")
    standards_meta_parser.add_argument("action", choices=["run", "run-diagnostics-bundle"])
    _add_input_out(standards_meta_parser)
    standards_meta_parser.add_argument("--acceptance-out")

    cold_reader_parser = subparsers.add_parser("cold-reader-route-map")
    cold_reader_parser.add_argument("action", choices=["run", "run-route-map-bundle"])
    _add_input_out(cold_reader_parser)

    navigation_parser = subparsers.add_parser("navigation-hologram-route-plane")
    navigation_parser.add_argument("action", choices=["run", "validate-route-plane-bundle"])
    _add_input_out(navigation_parser)

    mission_parser = subparsers.add_parser("mission-transaction-work-spine")
    mission_parser.add_argument("action", choices=["run", "validate-mission-transaction-bundle"])
    _add_input_out(mission_parser)

    observability_parser = subparsers.add_parser("agent-route-observability-runtime")
    observability_parser.add_argument(
        "action",
        choices=[
            "run",
            "validate-observability-bundle",
            "validate-computer-use-bundle",
            "validate-session-attribution-bundle",
            "validate-multi-agent-fanin-bundle",
            "validate-bridge-dispatch-yield-resume-bundle",
            "validate-controller-heartbeat-bundle",
            "validate-agent-trace-route-repair-bundle",
            "validate-agent-observability-store-bundle",
        ],
    )
    _add_input_out(observability_parser)

    bridge_continuity_parser = subparsers.add_parser("bridge-phase-continuity-runtime")
    bridge_continuity_parser.add_argument("action", choices=["run"])
    _add_input_out(bridge_continuity_parser)

    assimilation_parser = subparsers.add_parser("pattern-assimilation-step")
    assimilation_parser.add_argument("action", nargs="?", choices=["run", "validate-assimilation-bundle"], default="run")
    _add_input_out(assimilation_parser)

    voice_to_doctrine_parser = subparsers.add_parser(
        "voice-to-doctrine-self-improvement-loop"
    )
    voice_to_doctrine_parser.add_argument("action", choices=["run", "run-bundle"])
    _add_input_out(voice_to_doctrine_parser)
    voice_to_doctrine_parser.add_argument("--acceptance-out")

    args = parser.parse_args(argv)
    if args.command == "init":
        return project_substrate.main(["init", args.project])
    if args.command == "index":
        return project_substrate.main(["index", args.project])
    if args.command == "catalog":
        return project_substrate.main(["catalog", args.project])
    if args.command == "architecture":
        return project_substrate.main(["architecture", args.project])
    if args.command == "compile":
        return project_substrate.main(["compile", args.project])
    if args.command == "python-lens":
        return project_substrate.main(["python-lens", args.project])
    if args.command == "graph":
        return project_substrate.main(["graph", args.project])
    if args.command == "explain":
        return project_substrate.main(["explain", args.project, args.route_id])
    if args.command == "status":
        command_args = ["status"]
        if args.card:
            shell = runtime_shell.RuntimeShell()
            payload = shell.status_card(args.project)
            if args.project:
                payload = _attach_status_card_front_door_refs(payload)
            return _print_json(payload)
        if args.project:
            command_args.append(args.project)
        return runtime_shell.main(command_args)
    if args.command == "proof-lab":
        command = _proof_lab_command(args.input, args.out)
        result = verifier_lab_kernel.run_kernel_bundle(
            args.input,
            args.out,
            command=command,
        )
        return _print_json(
            _proof_lab_first_screen_card(
                result,
                input_path=args.input,
                out_dir=args.out,
                command=command,
            )
        )
    if args.command == "spine":
        return runtime_shell.main(["spine"])
    if args.command == "tour":
        command_args = ["tour"]
        if args.project:
            command_args.append(args.project)
        return runtime_shell.main(command_args)
    if args.command == "authority":
        return runtime_shell.main(["authority"])
    if args.command == "workingness":
        return runtime_shell.main(["workingness"])
    if args.command == "prediction-lens":
        return runtime_shell.main(["prediction-lens"])
    if args.command == "market-boundary":
        return runtime_shell.main(["market-boundary"])
    if args.command == "corpus-lens":
        return runtime_shell.main(["corpus-lens"])
    if args.command == "trace-lens":
        return runtime_shell.main(["trace-lens"])
    if args.command == "repair-loop":
        return runtime_shell.main(["repair-loop"])
    if args.command == "evidence-cells":
        return runtime_shell.main(["evidence-cells"])
    if args.command == "proof-loop-depth":
        return runtime_shell.main(["proof-loop-depth"])
    if args.command == "verifier-lab-execution-spine-lens":
        return runtime_shell.main(["verifier-lab-execution-spine-lens"])
    if args.command == "landing-replay":
        return runtime_shell.main(["landing-replay"])
    if args.command == "view-quality":
        return runtime_shell.main(["view-quality"])
    if args.command == "projection-safety":
        return runtime_shell.main(["projection-safety"])
    if args.command == "drift-control":
        return runtime_shell.main(["drift-control"])
    if args.command == "spatial-simulation":
        return runtime_shell.main(["spatial-simulation"])
    if args.command == "circuit-attribution":
        return runtime_shell.main(["circuit-attribution"])
    if args.command == "route-cleanup":
        return runtime_shell.main(["route-cleanup"])
    if args.command == "projection-import-map":
        return runtime_shell.main(["projection-import-map"])
    if args.command == "import-projector":
        return runtime_shell.main(["import-projector"])
    if args.command == "option-surface-lens":
        return runtime_shell.main(["option-surface-lens"])
    if args.command == "stripping-guard":
        return runtime_shell.main(["stripping-guard"])
    if args.command == "standards-control":
        return runtime_shell.main(["standards-control"])
    if args.command == "hook-coverage":
        return runtime_shell.main(["hook-coverage"])
    if args.command == "replay-gauntlet":
        return runtime_shell.main(["replay-gauntlet"])
    if args.command == "benchmark-lab":
        return runtime_shell.main(["benchmark-lab"])
    if args.command == "legibility-scorecard":
        return runtime_shell.main(["legibility-scorecard"])
    if args.command == "intake":
        return runtime_shell.main(["intake"])
    if args.command == "reveal":
        return runtime_shell.main(["reveal"])
    if args.command == "run":
        return runtime_shell.main(["run", args.project])
    if args.command == "serve":
        serve_args = ["serve", "--host", args.host, "--port", str(args.port)]
        if args.project:
            serve_args.append(args.project)
        return runtime_shell.main(serve_args)
    if args.command == "patterns":
        if args.project:
            return project_substrate.main(["patterns", args.project])
        return runtime_shell.main(["patterns"])
    if args.command == "route":
        if args.route_args == ["list"]:
            return runtime_shell.main(["route", "list"])
        if len(args.route_args) == 2 and args.route_args[0] == "inspect":
            return runtime_shell.main(["route", "inspect", args.route_args[1]])
        if len(args.route_args) == 3 and args.route_args[0] == "inspect":
            return project_substrate.main(["explain", args.route_args[1], args.route_args[2]])
        if len(args.route_args) == 1:
            return project_substrate.main(["route", args.route_args[0]])
    if args.command == "work":
        if args.work_command == "demo":
            return runtime_shell.main(["work", "demo"])
        if args.work_command == "create":
            work_args = ["work", "create", args.project]
            if args.route:
                work_args.extend(["--route", args.route])
            return project_substrate.main(work_args)
        if args.work_command == "run":
            work_args = ["work", "run", args.project]
            if args.work_id:
                work_args.extend(["--work-id", args.work_id])
            return project_substrate.main(work_args)
    if args.command == "observe":
        return project_substrate.main(["observe", args.project])
    if args.command == "evidence":
        if args.evidence_command == "list":
            if args.project:
                return project_substrate.main(["evidence", "list", args.project])
            return runtime_shell.main(["evidence", "list"])
        if args.evidence_command == "inspect":
            if args.project:
                return project_substrate.main(["evidence", "inspect", args.project, args.receipt_ref])
            return runtime_shell.main(["evidence", "inspect", args.receipt_ref])
    if args.command == "private-state-scan":
        return private_state_scan.main(["--root", args.root, "--out", args.out] + (["--policy", args.policy] if args.policy else []))
    if args.command == "secret-exclusion-scan":
        return secret_exclusion_scan.main(["--root", args.root, "--out", args.out] + (["--policy", args.policy] if args.policy else []))
    if args.command == "public-entry-docs":
        return public_entry_docs.main(["--root", args.root, "--out", args.out])
    if args.command == "research-kernel-density":
        density_args = ["--root", args.root, "--out", args.out]
        if args.project:
            density_args.extend(["--project", args.project])
        return research_kernel_density.main(density_args)
    if args.command == "transaction-evidence-stability":
        return transaction_evidence_stability.main(
            ["--root", args.root, "--project", args.project, "--out", args.out]
        )
    if args.command == "observatory-legibility":
        return observatory_legibility.main(
            ["--root", args.root, "--project", args.project, "--out", args.out]
        )
    if args.command == "launch-compression":
        return launch_compression.main(
            ["--root", args.root, "--project", args.project, "--out", args.out]
        )
    if args.command == "standards-registry":
        return standards_registry.main(
            [
                "--registry",
                args.registry,
                "--standards-dir",
                args.standards_dir,
                "--acceptance",
                args.acceptance,
                "--out",
                args.out,
            ]
        )
    if args.command == "dependency-preflight":
        return dependency_preflight.main(
            [
                "--readiness",
                args.readiness,
                "--negative-matrix",
                args.negative_matrix,
                "--out",
                args.out,
            ]
        )
    if args.command == "fixture-freshness":
        return fixture_freshness.main(
            [
                "--readiness",
                args.readiness,
                "--negative-matrix",
                args.negative_matrix,
                "--mission-dag",
                args.mission_dag,
                "--receipt-coverage",
                args.receipt_coverage,
                "--out",
                args.out,
            ]
        )
    if args.command == "pattern-binding":
        return pattern_binding_contract.main([args.action, "--input", args.input, "--out", args.out])
    if args.command == "pattern-route-readiness":
        return pattern_binding_contract.main(
            [
                "validate-route-readiness-bundle",
                "--input",
                args.input,
                "--out",
                args.out,
            ]
        )
    if args.command == "finance-eval-spine":
        return finance_eval_spine.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "work-landing-control-spine":
        return work_landing_control_spine.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "executable-doctrine-grammar":
        return executable_doctrine_grammar.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "proof-diagnostic-evidence-spine":
        return proof_diagnostic_evidence_spine.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "formal-math-readiness-gate":
        formal_math_args = [args.action, "--input", args.input]
        if args.out:
            formal_math_args.extend(["--out", args.out])
        elif args.action != "plan":
            parser.error("--out is required for formal math readiness receipt-writing actions")
        return formal_math_readiness_gate.main(formal_math_args)
    if args.command == "corpus-readiness-mathlib-absence-gate":
        return corpus_readiness_mathlib_absence_gate.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "mathematical-strategy-atlas-hypothesis-scorer":
        return mathematical_strategy_atlas_hypothesis_scorer.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "tactic-portfolio-availability-probe":
        return tactic_portfolio_availability_probe.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "target-shape-tactic-routing-gate":
        return target_shape_tactic_routing_gate.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "formal-math-lean-proof-witness":
        return formal_math_lean_proof_witness.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "formal-math-premise-retrieval":
        return formal_math_premise_retrieval.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "formal-math-verifier-trace-repair-loop":
        return formal_math_verifier_trace_repair_loop.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "verifier-lab-kernel":
        verifier_lab_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            verifier_lab_args.extend(["--acceptance-out", args.acceptance_out])
        return verifier_lab_kernel.main(verifier_lab_args)
    if args.command == "verifier-lab-execution-spine":
        verifier_lab_execution_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            verifier_lab_execution_args.extend(
                ["--acceptance-out", args.acceptance_out]
            )
        return verifier_lab_execution_spine.main(verifier_lab_execution_args)
    if args.command == "certificate-kernel-execution-lab":
        certificate_kernel_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            certificate_kernel_args.extend(["--acceptance-out", args.acceptance_out])
        return certificate_kernel_execution_lab.main(certificate_kernel_args)
    if args.command == "formal-evidence-cell-anchor-resolver":
        return formal_evidence_cell_anchor_resolver.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "undeclared-library-prior-symbol-classifier":
        symbol_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            symbol_args.extend(["--acceptance-out", args.acceptance_out])
        return undeclared_library_prior_symbol_classifier.main(symbol_args)
    if args.command == "agent-benchmark-integrity-anti-gaming-replay":
        benchmark_integrity_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            benchmark_integrity_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_benchmark_integrity_anti_gaming_replay.main(
            benchmark_integrity_args
        )
    if args.command == "agent-monitor-redteam-falsification-replay":
        monitor_redteam_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            monitor_redteam_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_monitor_redteam_falsification_replay.main(monitor_redteam_args)
    if args.command == "agent-sabotage-scheming-monitor-replay":
        sabotage_monitor_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            sabotage_monitor_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_sabotage_scheming_monitor_replay.main(sabotage_monitor_args)
    if args.command == "agent-sandbox-policy-escape-replay":
        sandbox_policy_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            sandbox_policy_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_sandbox_policy_escape_replay.main(sandbox_policy_args)
    if args.command == "indirect-prompt-injection-information-flow-policy-replay":
        prompt_injection_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            prompt_injection_args.extend(["--acceptance-out", args.acceptance_out])
        return indirect_prompt_injection_information_flow_policy_replay.main(
            prompt_injection_args
        )
    if args.command == "agentic-vulnerability-discovery-patch-proof-replay":
        agentic_vuln_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            agentic_vuln_args.extend(["--acceptance-out", args.acceptance_out])
        return agentic_vulnerability_discovery_patch_proof_replay.main(
            agentic_vuln_args
        )
    if args.command == "agent-memory-temporal-conflict-replay":
        memory_conflict_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            memory_conflict_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_memory_temporal_conflict_replay.main(memory_conflict_args)
    if args.command == "sleeper-memory-poisoning-quarantine-replay":
        sleeper_memory_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            sleeper_memory_args.extend(["--acceptance-out", args.acceptance_out])
        return sleeper_memory_poisoning_quarantine_replay.main(sleeper_memory_args)
    if args.command == "mcp-tool-authority-replay":
        mcp_tool_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            mcp_tool_args.extend(["--acceptance-out", args.acceptance_out])
        return mcp_tool_authority_replay.main(mcp_tool_args)
    if args.command == "proof-derived-governed-mutation-authorization":
        governed_mutation_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            governed_mutation_args.extend(["--acceptance-out", args.acceptance_out])
        return proof_derived_governed_mutation_authorization.main(
            governed_mutation_args
        )
    if args.command == "belief-state-process-reward-replay":
        belief_reward_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            belief_reward_args.extend(["--acceptance-out", args.acceptance_out])
        return belief_state_process_reward_replay.main(belief_reward_args)
    if args.command == "lean-std-premise-index":
        return lean_std_premise_index.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "provider-context-recipe-budget-policy":
        return provider_context_recipe_budget_policy.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "ring2-premise-retrieval-precision-recall-harness":
        return ring2_premise_retrieval_precision_recall_harness.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "durable-agent-work-landing-replay":
        durable_landing_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            durable_landing_args.extend(["--acceptance-out", args.acceptance_out])
        return durable_agent_work_landing_replay.main(durable_landing_args)
    if args.command == "research-replication-rubric-artifact-replay":
        research_replication_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            research_replication_args.extend(["--acceptance-out", args.acceptance_out])
        return research_replication_rubric_artifact_replay.main(
            research_replication_args
        )
    if args.command == "world-model-projection-drift-control-room":
        drift_control_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            drift_control_args.extend(["--acceptance-out", args.acceptance_out])
        return world_model_projection_drift_control_room.main(drift_control_args)
    if args.command == "spatial-world-model-counterfactual-simulation-replay":
        spatial_simulation_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            spatial_simulation_args.extend(["--acceptance-out", args.acceptance_out])
        return spatial_world_model_counterfactual_simulation_replay.main(
            spatial_simulation_args
        )
    if args.command == "materials-chemistry-closed-loop-lab-safety-replay":
        materials_lab_safety_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            materials_lab_safety_args.extend(["--acceptance-out", args.acceptance_out])
        return materials_chemistry_closed_loop_lab_safety_replay.main(
            materials_lab_safety_args
        )
    if args.command == "mechanistic-interpretability-circuit-attribution-replay":
        circuit_attribution_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            circuit_attribution_args.extend(["--acceptance-out", args.acceptance_out])
        return mechanistic_interpretability_circuit_attribution_replay.main(
            circuit_attribution_args
        )
    if args.command == "public-reveal-walkthrough":
        return public_reveal_walkthrough.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "macro-projection-import-protocol":
        macro_args = [args.action, "--input", args.input]
        if args.out:
            macro_args.extend(["--out", args.out])
        elif args.action != "plan":
            parser.error("--out is required for macro projection receipt-writing actions")
        return macro_projection_import_protocol.main(macro_args)
    if args.command == "prediction-oracle-reconciliation":
        return prediction_oracle_reconciliation.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "standards-meta-diagnostics":
        standards_meta_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            standards_meta_args.extend(["--acceptance-out", args.acceptance_out])
        return standards_meta_diagnostics.main(standards_meta_args)
    if args.command == "cold-reader-route-map":
        return cold_reader_route_map.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "navigation-hologram-route-plane":
        return navigation_hologram_route_plane.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "mission-transaction-work-spine":
        return mission_transaction_work_spine.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "agent-route-observability-runtime":
        return agent_route_observability_runtime.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "bridge-phase-continuity-runtime":
        return bridge_phase_continuity_runtime.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "voice-to-doctrine-self-improvement-loop":
        voice_to_doctrine_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            voice_to_doctrine_args.extend(["--acceptance-out", args.acceptance_out])
        return voice_to_doctrine_self_improvement_loop.main(voice_to_doctrine_args)
    if args.command == "pattern-assimilation-step":
        if args.action == "validate-assimilation-bundle":
            return acceptance.main(
                [
                    "validate-assimilation-bundle",
                    "--input",
                    args.input,
                    "--out",
                    args.out,
                ]
            )
        return acceptance.main(
            [
                "--only",
                "pattern_assimilation_step",
                "--input",
                args.input,
                "--out",
                args.out,
            ]
        )
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
