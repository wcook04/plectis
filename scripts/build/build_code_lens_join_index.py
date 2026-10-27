#!/usr/bin/env python3
"""Build the existing CodeLens index; --claim-assurance explicitly opts into v3."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import runpy
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from microcosm_core.projections.component_assurance import (
    SCHEMA_VERSION, build_join_index, extend_claim_index, collect_claim_assurance_inputs,
    refresh_navigation, _load_json,
)


def proof_binding_tools(root):
    """Maintenance-only adapter; runtime readers never import these scripts."""
    return runpy.run_path(str(Path(root) / "scripts/check/check_component_kernels.py"))


def main(argv: list[str] | None = None) -> int:
    """
    Run `scripts.build.build_code_lens_join_index` as a command-line entry point.

    The command parses argv, calls this module's builders or validators, and returns the
    status code used by the process wrapper.
    """
    parser = argparse.ArgumentParser(description="Build the code-lens join index v2.")
    parser.add_argument("--lens", type=Path, help="python-lens --full snapshot JSON")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("core/organ_registry.json"),
        help="organ registry JSON",
    )
    parser.add_argument(
        "--atlas",
        type=Path,
        default=Path("core/organ_atlas.json"),
        help="organ atlas JSON (family/wires_to/doctrine plane; optional)",
    )
    parser.add_argument(
        "--routes",
        type=Path,
        default=Path("atlas/agent_task_routes.json"),
        help="agent task routes JSON (task_class route plane; optional)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("receipts/code_lens/code_lens_join_index_v0.json"),
    )
    parser.add_argument("--refresh-navigation", action="store_true",
                        help="refresh only owner navigation in the saved index; no lens evidence rebuild")
    parser.add_argument("--capsules", type=Path, default=Path("core/paper_module_capsules.json"),
                        help="canonical capsule descriptions; existing v2 callers may omit this input")
    parser.add_argument("--claim-assurance", action="store_true",
                        help="opt into the strict v3 component/contract read model")
    parser.add_argument("--base-index", type=Path,
                        help="saved v2 join index for assurance migration; regenerate v3 with --lens")
    parser.add_argument("--repo-root", type=Path, default=Path("."),
                        help="source root for bounded assurance validation")
    args = parser.parse_args(argv)
    if args.base_index and not args.claim_assurance:
        parser.error("--base-index requires --claim-assurance")
    if args.claim_assurance:
        if args.refresh_navigation or (args.base_index and args.lens):
            parser.error("assurance requires one base index or lens; no navigation-only refresh")
        root = args.repo_root.resolve()
        def source_path(path):
            return path if path.is_absolute() else root / path
        base = None
        if args.base_index:
            base = _load_json(args.base_index, "saved v2 join index")
            if not isinstance(base, dict) or base.get("schema_version") != SCHEMA_VERSION:
                parser.error("--base-index requires a saved v2 join index; regenerate v3 with --lens from a current python-lens --full snapshot")
        elif not args.lens:
            parser.error("--lens or --base-index is required for assurance")
        registry = _load_json(source_path(args.registry), "organ registry")
        atlas = _load_json(source_path(args.atlas), "organ atlas")
        assurance = collect_claim_assurance_inputs(root, registry, atlas, proof_tools=proof_binding_tools(root))
        if base is not None:
            index = extend_claim_index(base, registry, atlas, assurance)
        else:
            lens = _load_json(args.lens, "lens snapshot")
            routes = _load_json(source_path(args.routes), "task routes")
            index = build_join_index(lens, registry, atlas=atlas, routes=routes, assurance=assurance)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
        print(f"wrote {args.out}: {len(index['nodes']['claim'])} component claims with explicit v3 assurance")
        return 0
    if args.refresh_navigation:
        if args.lens:
            parser.error("--refresh-navigation does not accept a lens input")
        index = _load_json(args.out, "saved join index")
        args.out.write_text(json.dumps(refresh_navigation(index), indent=2, sort_keys=True) + "\n")
        print(f"refreshed owner navigation only: {args.out}")
        return 0
    if not args.lens:
        parser.error("--lens is required when rebuilding source evidence")
    lens = _load_json(args.lens, "lens snapshot")
    registry = _load_json(args.registry, "organ registry")
    if not isinstance(lens, dict) or not isinstance(registry, dict):
        raise SystemExit("2: lens and registry must both be JSON objects")
    atlas = _load_json(args.atlas, "organ atlas") if args.atlas.is_file() else None
    routes = _load_json(args.routes, "agent task routes") if args.routes.is_file() else None
    capsules = _load_json(args.capsules, "paper module capsules") if args.capsules.is_file() else None
    index = build_join_index(lens, registry, atlas=atlas, routes=routes, capsules=capsules)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    rollup = index["rollup"]
    print(
        f"wrote {args.out}: {rollup['organ_count']} organs, "
        f"{rollup['organs_with_resolved_runner_source']} runner-resolved, "
        f"{rollup['claim_node_count']} claims, {rollup['route_node_count']} routes, "
        f"{rollup['edge_count']} edges; resolved="
        f"{','.join(index['graph']['resolved_edge_classes']) or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
