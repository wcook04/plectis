from __future__ import annotations

import argparse

from microcosm_core import project_substrate
from microcosm_core import runtime_shell
from microcosm_core.organs import agent_benchmark_integrity_anti_gaming_replay
from microcosm_core.organs import agent_memory_temporal_conflict_replay
from microcosm_core.organs import agent_monitor_redteam_falsification_replay
from microcosm_core.organs import agent_route_observability_runtime
from microcosm_core.organs import agent_sabotage_scheming_monitor_replay
from microcosm_core.organs import agent_sandbox_policy_escape_replay
from microcosm_core.organs import belief_state_process_reward_replay
from microcosm_core.organs import cold_reader_route_map
from microcosm_core.organs import corpus_readiness_mathlib_absence_gate
from microcosm_core.organs import executable_doctrine_grammar
from microcosm_core.organs import formal_math_lean_proof_witness
from microcosm_core.organs import formal_evidence_cell_anchor_resolver
from microcosm_core.organs import formal_math_premise_retrieval
from microcosm_core.organs import formal_math_readiness_gate
from microcosm_core.organs import formal_math_verifier_trace_repair_loop
from microcosm_core.organs import lean_std_premise_index
from microcosm_core.organs import macro_projection_import_protocol
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
from microcosm_core.organs import world_model_projection_drift_control_room
from microcosm_core.validators import acceptance
from microcosm_core.validators import dependency_preflight
from microcosm_core.validators import fixture_freshness
from microcosm_core.validators import launch_compression
from microcosm_core.validators import observatory_legibility
from microcosm_core.validators import private_state_scan
from microcosm_core.validators import public_entry_docs
from microcosm_core.validators import research_kernel_density
from microcosm_core.validators import standards_registry
from microcosm_core.validators import transaction_evidence_stability


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="microcosm")
    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("project")
    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("project")
    catalog_parser = subparsers.add_parser("catalog")
    catalog_parser.add_argument("project")
    architecture_parser = subparsers.add_parser("architecture")
    architecture_parser.add_argument("project")
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("project")
    python_lens_parser = subparsers.add_parser("python-lens")
    python_lens_parser.add_argument("project")
    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("project")
    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("project")
    explain_parser.add_argument("route_id")
    subparsers.add_parser("status")
    subparsers.add_parser("spine")
    tour_parser = subparsers.add_parser("tour")
    tour_parser.add_argument("project", nargs="?")
    subparsers.add_parser("authority")
    subparsers.add_parser("prediction-lens")
    subparsers.add_parser("market-boundary")
    subparsers.add_parser("corpus-lens")
    subparsers.add_parser("trace-lens")
    subparsers.add_parser("repair-loop")
    subparsers.add_parser("evidence-cells")
    subparsers.add_parser("proof-loop-depth")
    subparsers.add_parser("landing-replay")
    subparsers.add_parser("view-quality")
    subparsers.add_parser("projection-safety")
    subparsers.add_parser("drift-control")
    subparsers.add_parser("spatial-simulation")
    subparsers.add_parser("circuit-attribution")
    subparsers.add_parser("route-cleanup")
    subparsers.add_parser("projection-import-map")
    subparsers.add_parser("import-projector")
    subparsers.add_parser("option-surface-lens")
    subparsers.add_parser("stripping-guard")
    subparsers.add_parser("standards-control")
    subparsers.add_parser("hook-coverage")
    subparsers.add_parser("replay-gauntlet")
    subparsers.add_parser("benchmark-lab")
    subparsers.add_parser("legibility-scorecard")
    subparsers.add_parser("intake")
    subparsers.add_parser("reveal")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("project", nargs="?", default=runtime_shell.DEFAULT_PROJECT_REL)
    serve_parser = subparsers.add_parser("serve")
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
    evidence_parser = subparsers.add_parser("evidence")
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
    organ_parser.add_argument("action", choices=["validate", "validate-substrate-bundle"])
    _add_input_out(organ_parser)

    grammar_parser = subparsers.add_parser("executable-doctrine-grammar")
    grammar_parser.add_argument("action", choices=["validate", "validate-standards-bundle"])
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
    observability_parser.add_argument("action", choices=["run", "validate-observability-bundle"])
    _add_input_out(observability_parser)

    assimilation_parser = subparsers.add_parser("pattern-assimilation-step")
    assimilation_parser.add_argument("action", nargs="?", choices=["run", "validate-assimilation-bundle"], default="run")
    _add_input_out(assimilation_parser)

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
        return runtime_shell.main(["status"])
    if args.command == "spine":
        return runtime_shell.main(["spine"])
    if args.command == "tour":
        command_args = ["tour"]
        if args.project:
            command_args.append(args.project)
        return runtime_shell.main(command_args)
    if args.command == "authority":
        return runtime_shell.main(["authority"])
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
