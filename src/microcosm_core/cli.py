from __future__ import annotations

import argparse

from microcosm_core import project_substrate
from microcosm_core import runtime_shell
from microcosm_core.organs import agent_route_observability_runtime
from microcosm_core.organs import executable_doctrine_grammar
from microcosm_core.organs import mission_transaction_work_spine
from microcosm_core.organs import navigation_hologram_route_plane
from microcosm_core.organs import pattern_binding_contract
from microcosm_core.organs import proof_diagnostic_evidence_spine
from microcosm_core.validators import acceptance
from microcosm_core.validators import dependency_preflight
from microcosm_core.validators import fixture_freshness
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
    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("project")
    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("project")
    explain_parser.add_argument("route_id")
    subparsers.add_parser("status")
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
    if args.command == "graph":
        return project_substrate.main(["graph", args.project])
    if args.command == "explain":
        return project_substrate.main(["explain", args.project, args.route_id])
    if args.command == "status":
        return runtime_shell.main(["status"])
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
