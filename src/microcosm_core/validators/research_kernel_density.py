"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.validators.research_kernel_density` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: CHECKER_ID, REQUIRED_PRIMITIVE_FIELDS, REQUIRED_PATTERN_SURFACE_FIELDS, REQUIRED_README_PHRASES, FORBIDDEN_README_PHRASES, validate_density, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core, microcosm_core.architecture_kernel, microcosm_core.private_state_scan, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
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
    "Run one command inside a code repository",
    "Every finding in that record carries three handles",
    "not a hosted service",
    "no proof authority",
]
FORBIDDEN_README_PHRASES = [
    "production-ready developer platform",
    "release-ready agent platform",
    "Receipts Are Authority",
]


def _public_relative(root: Path, path: Path) -> str:
    """
    [ACTION]
    Render a receipt-safe relative path so emitted paths never leak host roots.

    - Teleology: keeps receipt path fields project-relative so the public density receipt never embeds an absolute host/sandbox root.
    - Guarantee: returns the POSIX relative path of `path` under `root` when containment holds; otherwise returns `path.as_posix()` verbatim.
    - Fails: never raises; on a non-containment ValueError it falls back to the absolute-style POSIX string of `path`.
    - When-needed: tracing why a `receipt_paths` entry is absolute instead of project-relative.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _kernel_findings(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """
    [ACTION]
    Audit the architecture-kernel manifest for research-prototype posture and primitive density.

    - Teleology: enforces that the kernel manifest declares research-prototype posture, a non-release ceiling, a pattern surface, and a dense-enough primitive set with runtime hooks.
    - Guarantee: returns (findings, blocking_codes); appends a `KERNEL_*` code for each violated invariant (posture, `release_authorized is not False`, pattern-surface shape/state_ref/private-body ceiling, fewer than 7 primitive rows, missing required primitive fields, missing `plectis explain` runtime command).
    - Fails: never raises here; non-conformance surfaces as `KERNEL_*` blocking codes plus structured findings; an absent manifest yields whatever empty/default `manifest.get` returns.
    - When-needed: diagnosing why density validation reports a kernel-posture or primitive-density block.
    - Escalates-to: REQUIRED_PRIMITIVE_FIELDS / REQUIRED_PATTERN_SURFACE_FIELDS constants and `load_kernel_manifest` for the source manifest shape.
    - Non-goal: passing here does not authorize release; it only attests manifest density and the declared release ceiling, not actual safety of the kernel.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    Coerce a payload list field into dict-only rows for tolerant downstream iteration.

    - Teleology: normalizes possibly-malformed JSON list fields into a clean list of dict rows so callers never crash on non-list or mixed-type values.
    - Guarantee: returns a list containing only the dict elements of `payload[key]`; returns `[]` when the value is missing or not a list.
    - Fails: never raises; malformed input degrades to an empty or filtered list.
    - When-needed: understanding why a patterns/routes/work_items section appears empty despite present-but-malformed data.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _has_json_file(path: Path) -> bool:
    """
    [ACTION]
    Report whether a directory tree contains at least one JSON payload file.

    - Teleology: cheap existence probe used to assert that a required directory (e.g. route explanations) actually carries JSON content.
    - Guarantee: returns True iff `path` is a directory and `_iter_json_payload_files` yields at least one `.json` file in its tree; otherwise False.
    - Fails: never raises; a missing or non-directory path returns False, and scandir errors inside the iterator are swallowed.
    - When-needed: diagnosing a PROJECT_ROUTE_EXPLANATION_MISSING block where the explanations directory exists but is empty.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return path.is_dir() and any(_iter_json_payload_files(path))


def _iter_json_payload_files(root: Path):
    """
    [ACTION]
    Recursively yield every `.json` file under a root, tolerating filesystem errors.

    - Teleology: provides the single recursive JSON-discovery primitive that explanation/state scans build on, isolating all scandir error handling in one place.
    - Guarantee: yields a `Path` for each regular `.json` file (symlinks not followed) found anywhere beneath `root`, depth-first.
    - Fails: never raises; per-entry OSError is skipped and a scandir failure on `root` ends the generator with no yields.
    - When-needed: confirming which JSON files a density scan actually visits when a file appears to be silently ignored.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    Enumerate the `.microcosm` payload files a host-path leak scan must inspect.

    - Teleology: defines the exact file set (all JSON plus the events JSONL stream) scanned for absolute host-path leakage in project state.
    - Guarantee: yields every `.json` file under `state`, then always yields `state / "events.jsonl"` (whether or not it exists; callers re-check `is_file`).
    - Fails: never raises; the trailing events path is emitted unconditionally and existence is the caller's responsibility.
    - When-needed: verifying coverage of the PROJECT_STATE_HOST_PATH_LEAK scan over a project's `.microcosm` directory.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    yield from _iter_json_payload_files(state)
    yield state / "events.jsonl"


def _explanation_ref(explanations: Path, path: Path) -> str:
    """
    [ACTION]
    Build the stable `.microcosm/explanations/...` ref used to name explanation findings.

    - Teleology: gives every explanation-file finding a portable, project-relative reference instead of a host-absolute path.
    - Guarantee: returns `.microcosm/explanations/<rel>` where `<rel>` is `path` relative to `explanations`, falling back to just the filename when containment fails.
    - Fails: never raises; a non-containment ValueError degrades the ref to `.microcosm/explanations/<basename>`.
    - When-needed: correlating a `project_explanation_*` finding back to its on-disk explanation file.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        rel = path.resolve(strict=False).relative_to(explanations.resolve(strict=False))
    except ValueError:
        rel = Path(path.name)
    return f".microcosm/explanations/{rel.as_posix()}"


def _file_contains_any(path: Path, markers: tuple[str, ...]) -> bool:
    """
    [ACTION]
    Stream a file line-by-line testing for any forbidden marker substring (leak probe).

    - Teleology: the substring oracle behind host-path leak detection; reads lazily so large state files do not load fully into memory.
    - Guarantee: returns True iff at least one of `markers` appears as a substring on any line of `path`; decoding errors are ignored, not failed on.
    - Fails: raises OSError if `path` cannot be opened (caller pre-filters with `is_file`); never raises on malformed bytes (`errors="ignore"`).
    - When-needed: confirming whether a specific state file actually contains an absolute host root before trusting a leak verdict.
    - Non-goal: a False result attests only that the literal markers are absent; it does not certify the file is free of all sensitive content.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return any(any(marker in line for marker in markers) for line in handle)


def _project_findings(project: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """
    [ACTION]
    Audit one imported project's `.microcosm` state for density, binding closure, and host-path safety.

    - Teleology: proves an imported real-substrate project has the full local-state spine (architecture/graph/routes/work/truth surfaces), resolved pattern+standard bindings, complete work-transaction contracts, a passing non-release truth-readiness surface, and no absolute host-path leakage.
    - Guarantee: returns (findings, blocking_codes); appends a `PROJECT_*` code for each violated invariant — missing required state files, thin graph (`edge_count < 6`), missing/invalid pattern surface, unresolved route/explanation pattern refs, missing/unresolved explanation pattern+standard bindings, missing or contract-incomplete work transactions, non-passing or release-authorized truth-readiness surface, missing observatory endpoints/command, and any state file containing the project root or `/Users/`.
    - Guarantee: the truth-readiness checks explicitly require `source_files_mutated is False` and `release_authorized is False`, so a project claiming release or source mutation is flagged, not passed.
    - Fails: never raises for content violations (they become `PROJECT_*` codes + findings); may surface filesystem/JSON errors from `read_json_if_exists`, `_file_contains_any`, or `project_substrate.compile_project_card` on unreadable inputs.
    - When-needed: diagnosing exactly which project-side invariant blocked a density receipt for a given imported project.
    - Escalates-to: `project_substrate.compile_project_card` for the truth-readiness surface, and the per-finding `state_ref`/`explanation_ref` strings for the offending file.
    - Non-goal: passing here does not authorize release, hosting, provider calls, source mutation, or private-root equivalence; it attests local-state density and host-path safety only, and asserts (not proves) the project's own non-release ceiling.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
            if "plectis serve <project>" not in str(observatory.get("command") or ""):
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
    """
    [ACTION]
    Validate public research-kernel density end-to-end and write the atomic verdict receipt.

    - Teleology: the single public entrypoint that fuses README posture, kernel manifest density, optional imported-project state, and a private-state scan into one research_kernel_density receipt with a hard non-release authority ceiling.
    - Guarantee: writes a `research_kernel_density_receipt_v1` receipt to `out_path` (atomically via `write_json_atomic`) and returns it; `status` is `PASS` iff `blocking_codes` is empty, else `"blocked"`; `blocking_codes` is the sorted unique union of README, kernel, project, and PRIVATE_STATE_SCAN codes.
    - Guarantee: the receipt always carries `authority_ceiling` with every authorization field False and an `anti_claim` disclaiming hosted release, provider calls, source mutation, and secret export; `density_assertions.release_authorized` is hardcoded False; the embedded private-state scan has `forbidden_output_fields` stripped before serialization.
    - Fails: returns a `status="blocked"` receipt (does not raise) when any posture/density/binding/leak invariant fails; may raise OSError from reading README or from `write_json_atomic` on an unwritable `out_path`.
    - When-needed: gating or auditing whether the public Plectis slice (plus an optional imported project) meets research-prototype density before any downstream packaging step.
    - Escalates-to: std research-kernel density contract and the on-disk receipt at `out_path`; `_kernel_findings` / `_project_findings` / `scan_paths` for per-domain detail.
    - Non-goal: a PASS proves prototype posture, local-state density, and import pressure only; it does NOT authorize hosted release, credentialed provider calls, source mutation, secret export, private-root equivalence, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
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
    """
    [ACTION]
    Build the CLI argument parser for the density validator.

    - Teleology: declares the command-line surface (`--root`, `--out`, optional `--project`) that maps shell invocation onto `validate_density`.
    - Guarantee: returns an ArgumentParser requiring `--root` and `--out` and accepting an optional `--project`.
    - Fails: never raises at construction; parsing missing required args later exits the process via argparse with code 2.
    - When-needed: confirming the exact accepted flags before scripting the validator.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Validate public research-kernel density")
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--project")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entrypoint: parse args, run density validation, and return a shell exit code.

    - Teleology: adapts the command line to `validate_density`, reconstructing a host-safe `command` string (project shown by name only) for the receipt.
    - Guarantee: invokes `validate_density` with the parsed root/out/project and returns 0 iff the resulting receipt `status == PASS`, else 1.
    - Fails: returns 1 on a blocked receipt; argparse exits with code 2 on bad args; propagates any OSError raised while writing the receipt.
    - When-needed: running the validator as `python -m microcosm_core.validators.research_kernel_density` and interpreting its exit status in a gate.
    - Escalates-to: `validate_density` for the full receipt and `_parser` for the accepted flags.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
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
