from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from microcosm_core import project_substrate
from microcosm_core.architecture_kernel import load_kernel_manifest, read_json_if_exists
from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import write_json_atomic


CHECKER_ID = "checker.microcosm.validators.research_kernel_density"
REQUIRED_PRIMITIVE_FIELDS = [
    "primitive_id",
    "public_name",
    "what_it_does",
    "input",
    "output",
    "state_ref",
    "runtime_commands",
    "event_span",
    "evidence_relation",
    "macro_analogue",
    "public_boundary",
]
REQUIRED_PATTERN_SURFACE_FIELDS = [
    "surface_id",
    "state_ref",
    "evidence_ref",
    "binding_standard_refs",
    "projection_rule",
    "private_source_bodies_included",
]
REQUIRED_README_PHRASES = [
    "executable research prototype",
    "Run one command as a local witness",
    "Inspect the architecture",
    "small on purpose",
    "Evidence receipts are the black-box recorder",
]
FORBIDDEN_README_PHRASES = [
    "production-ready developer platform",
    "release-ready agent platform",
    "Receipts Are Authority",
]


def _public_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _kernel_findings(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    manifest = load_kernel_manifest(root)
    findings: list[dict[str, Any]] = []
    blocking_codes: list[str] = []
    primitives = manifest.get("primitives", [])
    primitive_rows = [row for row in primitives if isinstance(row, dict)] if isinstance(primitives, list) else []
    if manifest.get("posture") != "executable_research_prototype":
        blocking_codes.append("KERNEL_POSTURE_NOT_RESEARCH_PROTOTYPE")
    if manifest.get("release_authorized") is not False:
        blocking_codes.append("KERNEL_RELEASE_CEILING_MISSING")
    pattern_surface = manifest.get("pattern_surface")
    if not isinstance(pattern_surface, dict):
        blocking_codes.append("KERNEL_PATTERN_SURFACE_MISSING")
    else:
        missing = [field for field in REQUIRED_PATTERN_SURFACE_FIELDS if field not in pattern_surface]
        if missing:
            blocking_codes.append("KERNEL_PATTERN_SURFACE_FIELD_MISSING")
            findings.append(
                {
                    "finding_id": "kernel_pattern_surface_field_missing",
                    "missing_fields": missing,
                }
            )
        if pattern_surface.get("state_ref") != ".microcosm/patterns.json":
            blocking_codes.append("KERNEL_PATTERN_SURFACE_STATE_REF_INVALID")
        if pattern_surface.get("private_source_bodies_included") is not False:
            blocking_codes.append("KERNEL_PATTERN_SURFACE_PRIVATE_BODY_CEILING_MISSING")
    if len(primitive_rows) < 7:
        blocking_codes.append("KERNEL_PRIMITIVE_SET_TOO_THIN")
    for row in primitive_rows:
        missing = [field for field in REQUIRED_PRIMITIVE_FIELDS if not row.get(field)]
        if missing:
            blocking_codes.append("KERNEL_PRIMITIVE_FIELD_MISSING")
            findings.append(
                {
                    "finding_id": "kernel_primitive_field_missing",
                    "primitive_id": row.get("primitive_id"),
                    "missing_fields": missing,
                }
            )
    commands = [
        command
        for row in primitive_rows
        for command in row.get("runtime_commands", [])
        if isinstance(command, str)
    ]
    if "microcosm explain <project> <route_id>" not in commands:
        blocking_codes.append("KERNEL_EXPLAIN_COMMAND_MISSING")
    return findings, blocking_codes


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _has_json_file(path: Path) -> bool:
    return path.is_dir() and any(_iter_json_payload_files(path))


def _iter_json_payload_files(root: Path):
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        yield from _iter_json_payload_files(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False) and entry.name.endswith(".json"):
                        yield Path(entry.path)
                except OSError:
                    continue
    except OSError:
        return


def _iter_state_payload_files(state: Path):
    yield from _iter_json_payload_files(state)
    yield state / "events.jsonl"


def _explanation_ref(explanations: Path, path: Path) -> str:
    try:
        rel = path.resolve(strict=False).relative_to(explanations.resolve(strict=False))
    except ValueError:
        rel = Path(path.name)
    return f".microcosm/explanations/{rel.as_posix()}"


def _file_contains_any(path: Path, markers: tuple[str, ...]) -> bool:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return any(any(marker in line for marker in markers) for line in handle)


def _project_findings(project: Path) -> tuple[list[dict[str, Any]], list[str]]:
    findings: list[dict[str, Any]] = []
    blocking_codes: list[str] = []
    state = project / ".microcosm"
    required_state = [
        "architecture.json",
        "state_index.json",
        "graph.json",
        "routes.json",
        "work_items.json",
        "truth_readiness.json",
        "events.jsonl",
    ]
    for rel in required_state:
        if not (state / rel).is_file():
            blocking_codes.append("PROJECT_RESEARCH_KERNEL_STATE_MISSING")
            findings.append(
                {
                    "finding_id": "project_research_kernel_state_missing",
                    "state_ref": f".microcosm/{rel}",
                }
            )
    explanations = state / "explanations"
    if not _has_json_file(explanations):
        blocking_codes.append("PROJECT_ROUTE_EXPLANATION_MISSING")
    graph = read_json_if_exists(state / "graph.json")
    if graph and graph.get("edge_count", 0) < 6:
        blocking_codes.append("PROJECT_GRAPH_TOO_THIN")
    architecture = read_json_if_exists(state / "architecture.json")
    if not isinstance(architecture.get("pattern_surface"), dict):
        blocking_codes.append("PROJECT_PATTERN_SURFACE_MISSING")
    patterns_payload = read_json_if_exists(state / "patterns.json")
    routes_payload = read_json_if_exists(state / "routes.json")
    pattern_ids = {
        str(row.get("pattern_id"))
        for row in _rows(patterns_payload, "patterns")
        if row.get("pattern_id")
    }
    unresolved_routes: list[dict[str, Any]] = []
    for route in _rows(routes_payload, "routes"):
        pattern_refs = route.get("pattern_refs", [])
        if not isinstance(pattern_refs, list):
            pattern_refs = []
        unresolved = [
            str(ref)
            for ref in pattern_refs
            if ref is not None and str(ref) not in pattern_ids
        ]
        if unresolved:
            unresolved_routes.append(
                {
                    "route_id": route.get("route_id"),
                    "unresolved_pattern_refs": unresolved,
                }
            )
    if unresolved_routes:
        blocking_codes.append("PROJECT_ROUTE_PATTERN_REF_UNRESOLVED")
        findings.append(
            {
                "finding_id": "project_route_pattern_ref_unresolved",
                "routes": unresolved_routes,
            }
        )
    missing_bindings: list[str] = []
    unresolved_bindings: list[dict[str, Any]] = []
    missing_standard_bindings: list[str] = []
    unresolved_standard_bindings: list[dict[str, Any]] = []
    explanation_files = (
        sorted(_iter_json_payload_files(explanations)) if explanations.is_dir() else []
    )
    for path in explanation_files:
        explanation_ref = _explanation_ref(explanations, path)
        payload = read_json_if_exists(path)
        bindings = _rows(payload, "pattern_bindings")
        if not bindings:
            missing_bindings.append(explanation_ref)
            continue
        unresolved = [row.get("pattern_id") for row in bindings if row.get("resolved") is not True]
        if unresolved:
            unresolved_bindings.append(
                {
                    "explanation_ref": explanation_ref,
                    "unresolved_pattern_refs": unresolved,
                }
            )
        standard_bindings = _rows(payload, "standard_bindings")
        if not standard_bindings:
            missing_standard_bindings.append(explanation_ref)
            continue
        unresolved_standards = [
            row.get("standard_id") for row in standard_bindings if row.get("resolved") is not True
        ]
        if unresolved_standards:
            unresolved_standard_bindings.append(
                {
                    "explanation_ref": explanation_ref,
                    "unresolved_standard_refs": unresolved_standards,
                }
            )
    if missing_bindings:
        blocking_codes.append("PROJECT_EXPLANATION_PATTERN_BINDINGS_MISSING")
        findings.append(
            {
                "finding_id": "project_explanation_pattern_bindings_missing",
                "explanation_files": missing_bindings,
            }
        )
    if unresolved_bindings:
        blocking_codes.append("PROJECT_EXPLANATION_PATTERN_BINDING_UNRESOLVED")
        findings.append(
            {
                "finding_id": "project_explanation_pattern_binding_unresolved",
                "explanations": unresolved_bindings,
            }
        )
    if missing_standard_bindings:
        blocking_codes.append("PROJECT_EXPLANATION_STANDARD_BINDINGS_MISSING")
        findings.append(
            {
                "finding_id": "project_explanation_standard_bindings_missing",
                "explanation_files": missing_standard_bindings,
            }
        )
    if unresolved_standard_bindings:
        blocking_codes.append("PROJECT_EXPLANATION_STANDARD_BINDING_UNRESOLVED")
        findings.append(
            {
                "finding_id": "project_explanation_standard_binding_unresolved",
                "explanations": unresolved_standard_bindings,
            }
        )
    work_payload = read_json_if_exists(state / "work_items.json")
    work_rows = _rows(work_payload, "work_items")
    if not work_rows:
        blocking_codes.append("PROJECT_WORK_TRANSACTION_MISSING")
    work_contract_gaps: list[dict[str, Any]] = []
    for row in work_rows:
        missing = [
            field
            for field in [
                "route_snapshot",
                "satisfaction_contract",
                "integration_contract",
                "state_history",
                "event_refs",
                "evidence_refs",
            ]
            if not row.get(field)
        ]
        closeout = row.get("closeout")
        if row.get("status") == "closed" and not isinstance(closeout, dict):
            missing.append("closeout")
        if isinstance(closeout, dict):
            if closeout.get("satisfaction_contract_met") is not True:
                missing.append("closeout.satisfaction_contract_met")
            if closeout.get("integration_contract_met") is not True:
                missing.append("closeout.integration_contract_met")
        if missing:
            work_contract_gaps.append(
                {
                    "work_id": row.get("work_id"),
                    "missing_fields": sorted(set(missing)),
                }
            )
    if work_contract_gaps:
        blocking_codes.append("PROJECT_WORK_TRANSACTION_CONTRACT_INCOMPLETE")
        findings.append(
            {
                "finding_id": "project_work_transaction_contract_incomplete",
                "work_items": work_contract_gaps,
            }
        )
    compile_card = project_substrate.compile_project_card(project)
    truth_surface = compile_card.get("truth_readiness_surface")
    if not isinstance(truth_surface, dict) or not truth_surface:
        blocking_codes.append("PROJECT_TRUTH_READINESS_SURFACE_MISSING")
    else:
        truth_accounting = truth_surface.get("truth_accounting")
        observatory = truth_surface.get("observatory_surface")
        authority = truth_surface.get("authority_ceiling")
        if truth_surface.get("surface_id") != "public_microcosm_truth_readiness":
            blocking_codes.append("PROJECT_TRUTH_READINESS_SURFACE_INVALID")
        if truth_surface.get("status") != PASS:
            blocking_codes.append("PROJECT_TRUTH_READINESS_SURFACE_NOT_PASSING")
        if not isinstance(truth_accounting, dict):
            blocking_codes.append("PROJECT_TRUTH_ACCOUNTING_MISSING")
        else:
            required_truth_checks = [
                "project_local_state_refs_complete",
                "route_selected",
                "route_explanation_available",
                "work_transaction_closed",
                "event_stream_present",
                "evidence_refs_present",
                "graph_present",
                "observatory_surface_available",
            ]
            failed_truth_checks = [
                key for key in required_truth_checks if truth_accounting.get(key) is not True
            ]
            if truth_accounting.get("source_files_mutated") is not False:
                failed_truth_checks.append("source_files_mutated")
            if truth_accounting.get("release_authorized") is not False:
                failed_truth_checks.append("release_authorized")
            if failed_truth_checks:
                blocking_codes.append("PROJECT_TRUTH_ACCOUNTING_INCOMPLETE")
                findings.append(
                    {
                        "finding_id": "project_truth_accounting_incomplete",
                        "failed_checks": failed_truth_checks,
                    }
                )
        if not isinstance(observatory, dict):
            blocking_codes.append("PROJECT_OBSERVATORY_SURFACE_MISSING")
        else:
            if observatory.get("compact_endpoint") != "/project/observatory-card":
                blocking_codes.append("PROJECT_OBSERVATORY_CARD_ENDPOINT_MISSING")
            if observatory.get("expanded_endpoint") != "/project/observatory":
                blocking_codes.append("PROJECT_OBSERVATORY_ENDPOINT_MISSING")
            if "microcosm serve <project>" not in str(observatory.get("command") or ""):
                blocking_codes.append("PROJECT_OBSERVATORY_COMMAND_MISSING")
        if not isinstance(authority, dict) or authority.get("release_authorized") is not False:
            blocking_codes.append("PROJECT_TRUTH_READINESS_RELEASE_CEILING_MISSING")
    leaked_refs: list[str] = []
    project_abs = project.resolve(strict=False).as_posix()
    for path in _iter_state_payload_files(state):
        if not path.is_file():
            continue
        if _file_contains_any(path, (project_abs, "/Users/")):
            leaked_refs.append(path.relative_to(state).as_posix())
    if leaked_refs:
        blocking_codes.append("PROJECT_STATE_HOST_PATH_LEAK")
        findings.append(
            {
                "finding_id": "project_state_host_path_leak",
                "state_refs": sorted(leaked_refs),
            }
        )
    return findings, blocking_codes


def validate_density(
    root: str | Path,
    out_path: str | Path,
    *,
    command: str,
    project: str | Path | None = None,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    output_file = Path(out_path)
    readme = public_root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    missing_readme_phrases = [phrase for phrase in REQUIRED_README_PHRASES if phrase not in text]
    forbidden_readme_phrases = [phrase for phrase in FORBIDDEN_README_PHRASES if phrase in text]
    blocking_codes: list[str] = []
    findings: list[dict[str, Any]] = []
    if missing_readme_phrases:
        blocking_codes.append("README_RESEARCH_POSTURE_MISSING")
    if forbidden_readme_phrases:
        blocking_codes.append("README_RESEARCH_POSTURE_OVERCLAIM")
    kernel_findings, kernel_codes = _kernel_findings(public_root)
    findings.extend(kernel_findings)
    blocking_codes.extend(kernel_codes)
    project_ref = None
    if project is not None:
        project_path = Path(project).expanduser().resolve(strict=False)
        project_ref = project_path.name
        project_findings, project_codes = _project_findings(project_path)
        findings.extend(project_findings)
        blocking_codes.extend(project_codes)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan_paths_input = [
        path
        for path in [
            public_root / "README.md",
            public_root / "AGENTS.md",
            public_root / "core/architecture_kernel.json",
            public_root / "core/public_standard_pressure.json",
        ]
        if path.is_file()
    ]
    scan = scan_paths(scan_paths_input, forbidden_classes=policy, display_root=public_root)
    safe_scan = dict(scan)
    safe_scan.pop("forbidden_output_fields", None)
    if safe_scan["blocking_hit_count"]:
        blocking_codes.append("PRIVATE_STATE_SCAN_BLOCKED")
    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "research_kernel_density_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "project_ref": project_ref,
        "missing_readme_phrases": missing_readme_phrases,
        "forbidden_readme_phrases": forbidden_readme_phrases,
        "findings": findings,
        "blocking_codes": blocking_codes,
        "private_state_scan": safe_scan,
        "density_assertions": {
            "readme_declares_research_prototype": "README_RESEARCH_POSTURE_MISSING" not in blocking_codes,
            "kernel_primitives_have_runtime_hooks": "KERNEL_PRIMITIVE_FIELD_MISSING" not in blocking_codes,
            "kernel_declares_pattern_surface": "KERNEL_PATTERN_SURFACE_MISSING" not in blocking_codes
            and "KERNEL_PATTERN_SURFACE_FIELD_MISSING" not in blocking_codes,
            "route_pattern_refs_resolve": "PROJECT_ROUTE_PATTERN_REF_UNRESOLVED" not in blocking_codes,
            "explanations_include_pattern_bindings": "PROJECT_EXPLANATION_PATTERN_BINDINGS_MISSING"
            not in blocking_codes,
            "explanations_include_standard_bindings": "PROJECT_EXPLANATION_STANDARD_BINDINGS_MISSING"
            not in blocking_codes,
            "route_standard_refs_resolve": "PROJECT_EXPLANATION_STANDARD_BINDING_UNRESOLVED"
            not in blocking_codes,
            "route_explanation_available": "PROJECT_ROUTE_EXPLANATION_MISSING" not in blocking_codes,
            "work_transaction_contract_present": "PROJECT_WORK_TRANSACTION_CONTRACT_INCOMPLETE"
            not in blocking_codes
            and "PROJECT_WORK_TRANSACTION_MISSING" not in blocking_codes,
            "truth_readiness_surface_available": "PROJECT_TRUTH_READINESS_SURFACE_MISSING"
            not in blocking_codes
            and "PROJECT_TRUTH_READINESS_SURFACE_INVALID" not in blocking_codes
            and "PROJECT_TRUTH_READINESS_SURFACE_NOT_PASSING" not in blocking_codes,
            "observatory_surface_available": "PROJECT_OBSERVATORY_SURFACE_MISSING"
            not in blocking_codes
            and "PROJECT_OBSERVATORY_CARD_ENDPOINT_MISSING" not in blocking_codes
            and "PROJECT_OBSERVATORY_ENDPOINT_MISSING" not in blocking_codes
            and "PROJECT_OBSERVATORY_COMMAND_MISSING" not in blocking_codes,
            "desktop_sandbox_relative_refs": "PROJECT_STATE_HOST_PATH_LEAK" not in blocking_codes,
            "evidence_is_drilldown": True,
            "release_authorized": False,
        },
        "authority_ceiling": {
            "release_authorized": False,
            "hosting_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": "Research-kernel density validation proves public prototype posture, local-state architecture density, and real-substrate import pressure. It does not authorize hosted release operations, credentialed provider calls, unsafe source mutation, or secret export.",
        "receipt_paths": [_public_relative(public_root, output_file)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public research-kernel density")
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--project")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    project_display = Path(args.project).name if args.project else None
    command = (
        "python -m microcosm_core.validators.research_kernel_density "
        f"--root {args.root} --out {args.out}"
        + (f" --project {project_display}" if project_display else "")
    )
    receipt = validate_density(args.root, args.out, command=command, project=args.project)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
