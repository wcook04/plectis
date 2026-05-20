from __future__ import annotations

import argparse

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
from microcosm_core.validators import standards_registry


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
    scan_parser = subparsers.add_parser("private-state-scan")
    scan_parser.add_argument("--root", required=True)
    scan_parser.add_argument("--out", required=True)
    scan_parser.add_argument("--policy")

    public_entry_parser = subparsers.add_parser("public-entry-docs")
    _add_root_out(public_entry_parser)

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
    assimilation_parser.add_argument("--input", required=True)
    assimilation_parser.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    if args.command == "private-state-scan":
        return private_state_scan.main(["--root", args.root, "--out", args.out] + (["--policy", args.policy] if args.policy else []))
    if args.command == "public-entry-docs":
        return public_entry_docs.main(["--root", args.root, "--out", args.out])
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
