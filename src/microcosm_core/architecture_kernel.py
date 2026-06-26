from __future__ import annotations

from collections import deque
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator, Mapping

from microcosm_core.receipts import (
    utc_now,
    write_local_state_json_atomic as write_json_atomic,
)
from microcosm_core.schemas import read_json_strict


PASS = "pass"
STATE_DIR = ".microcosm"
EVIDENCE_DIR = "evidence"
EVENT_STREAM = "events.jsonl"
EXPLANATION_DIR = "explanations"
TRUTH_READINESS_STATE = "truth_readiness.json"

REFERENCE_CASE_ASSERTION_PREDICATES = [
    "join_integrity",
    "selection_binding",
    "scope_completeness",
    "execution_terminality",
    "authority_boundedness",
    "replay_equivalence",
    "state_delta_scope",
    "record_classification_matrix",
    "projection_fidelity",
]

_PATTERN_BY_ROUTE = {
    "readme_onboarding_route": "repo_has_readme",
    "package_runtime_route": "repo_has_package_manifest",
    "source_core_route": "repo_has_source_core",
    "test_behavior_route": "repo_has_tests",
    "missing_tests_route": "repo_has_tests",
    "docs_route": "repo_has_docs",
}

_PATTERN_SURFACE_CONTRACT = {
    "surface_id": "public_microcosm_pattern_surface",
    "state_ref": ".microcosm/patterns.json",
    "evidence_ref": ".microcosm/evidence/patterns.json",
    "binding_standard_refs": [
        "standards/std_microcosm_pattern.json",
        "standards/std_microcosm_pattern_binding_contract.json",
    ],
    "assimilation_policy_ref": "core/pattern_assimilation_policy.json",
    "organ_refs": ["pattern_binding_contract", "pattern_assimilation_step"],
    "projection_rule": (
        "Catalog role observations become public pattern rows; routes carry "
        "pattern_refs that must resolve against local .microcosm/patterns.json "
        "before explanation."
    ),
    "private_source_bodies_included": False,
}

_STANDARD_PRESSURE_REF = "core/public_standard_pressure.json"

_DEFAULT_STANDARD_PRESSURE_SURFACE = {
    "schema_version": "public_microcosm_standard_pressure_v1",
    "surface_id": "public_microcosm_standard_pressure",
    "state_ref": ".microcosm/architecture.json::standard_pressure_surface",
    "source_ref": _STANDARD_PRESSURE_REF,
    "authority_posture": "public_safe_standard_pressure_projection_not_doctrine_authority",
    "private_source_bodies_included": False,
    "anti_claim": (
        "Standard pressure rows are public-safe constraints over local Microcosm "
        "state. They do not promote global doctrine, authorize source mutation, "
        "or prove release readiness."
    ),
    "rows": [
        {
            "standard_id": "json_contract_markdown_projection",
            "title": "JSON Contract, Markdown Projection",
            "claim": "Project-local JSON is the contract; markdown and browser views are projections.",
            "source_refs": [
                "principles:pri_001",
                "standards/std_microcosm_standard.json",
            ],
            "kernel_primitive_refs": ["project", "catalog", "route", "work", "evidence"],
            "route_refs": ["*"],
            "runtime_hook": "architecture.write_project_architecture",
            "authority_boundary": "public_contract_projection_not_private_doctrine_body",
        },
        {
            "standard_id": "substrate_derived_projection",
            "title": "Substrate-Derived Projection",
            "claim": "Explanations must derive from local state files instead of hand-authored proof prose.",
            "source_refs": [
                "principles:pri_121",
                "paper_modules:system_self_comprehension_root",
            ],
            "kernel_primitive_refs": ["catalog", "pattern", "route", "explanation"],
            "route_refs": ["*"],
            "runtime_hook": "architecture.explain_route",
            "authority_boundary": "local_state_projection_not_source_authority",
        },
        {
            "standard_id": "projection_lineage_not_authority",
            "title": "Projection Lineage, Not Authority",
            "claim": "Generated route, graph, explanation, and evidence views must expose lineage and anti-claims.",
            "source_refs": [
                "principles:pri_142",
                "paper_modules:navigation_hologram_theory",
            ],
            "kernel_primitive_refs": ["route", "event", "evidence", "explanation"],
            "route_refs": ["*"],
            "runtime_hook": "architecture.build_graph",
            "authority_boundary": "generated_projection_interface_not_owner_source",
        },
        {
            "standard_id": "reversible_work_transaction",
            "title": "Reversible Work Transaction",
            "claim": "A work run records definition, execution, contracts, state history, and closeout without mutating source.",
            "source_refs": [
                "paper_modules:operational_work_item_spine",
                "standards/std_microcosm_work_item.json",
                "standards/std_microcosm_mission.json",
            ],
            "kernel_primitive_refs": ["route", "work", "event", "evidence", "assimilation"],
            "route_refs": ["*"],
            "runtime_hook": "project_substrate.create_work/run_work",
            "authority_boundary": "project_local_simulation_not_live_task_ledger_mutation",
        },
        {
            "standard_id": "evidence_as_black_box_recorder",
            "title": "Evidence As Black-Box Recorder",
            "claim": "Events and receipts record what happened; they are drilldown evidence, not the cockpit.",
            "source_refs": [
                "organs:proof_diagnostic_evidence_spine",
                "organs:agent_route_observability_runtime",
                "standards/std_microcosm_evidence_graph.json",
            ],
            "kernel_primitive_refs": ["event", "evidence", "explanation"],
            "route_refs": ["*"],
            "runtime_hook": "project_substrate.observe_project/list_evidence",
            "authority_boundary": "local_observability_not_live_telemetry_authority",
        },
        {
            "standard_id": "assimilation_without_promotion",
            "title": "Assimilation Without Promotion",
            "claim": "Closeout records next local actions and residuals without promoting global doctrine.",
            "source_refs": [
                "core/pattern_assimilation_policy.json",
                "organs:pattern_assimilation_step",
            ],
            "kernel_primitive_refs": ["work", "assimilation", "evidence"],
            "route_refs": ["*"],
            "runtime_hook": "project_substrate.run_work",
            "authority_boundary": "local_closeout_metadata_not_global_learning_authority",
        },
    ],
}

_DEFAULT_KERNEL = {
    "schema_version": "microcosm_architecture_kernel_v1",
    "kernel_id": "microcosm_executable_research_kernel",
    "posture": "executable_research_prototype",
    "job_sentence": (
        "Plectis is an executable research prototype of a local project substrate: "
        "bring a folder, build project-local state, inspect the architecture behind "
        "routes, work, events, and evidence."
    ),
    "local_first": True,
    "release_authorized": False,
    "source_mutation_default": False,
    "provider_calls_authorized": False,
    "receipts_are_drilldown_evidence": True,
    "anti_claim": (
        "This kernel describes the public research-prototype substrate only. It does "
        "not authorize production readiness, release, hosting, publication, provider "
        "calls, source mutation, private-data equivalence, or whole-system correctness."
    ),
    "pattern_surface": _PATTERN_SURFACE_CONTRACT,
    "standard_pressure_surface_ref": _STANDARD_PRESSURE_REF,
    "primitives": [
        {
            "primitive_id": "project",
            "public_name": "Project",
            "what_it_does": "Names the user-owned folder and creates project-local Microcosm state.",
            "input": "project folder",
            "output": ".microcosm/project_manifest.json",
            "state_ref": ".microcosm/project_manifest.json",
            "runtime_commands": ["microcosm init <project>"],
            "endpoint_refs": ["/project/status"],
            "event_span": "project.init",
            "evidence_relation": ".microcosm/evidence/init.json",
            "macro_analogue": "bounded substrate root / authority boundary",
            "public_boundary": "project-local projection, not source authority",
        },
        {
            "primitive_id": "catalog",
            "public_name": "Catalog",
            "what_it_does": "Classifies files into public repo roles.",
            "input": "project files",
            "output": ".microcosm/catalog.json",
            "state_ref": ".microcosm/catalog.json",
            "runtime_commands": ["microcosm index <project>", "microcosm catalog <project>"],
            "endpoint_refs": ["/project/catalog"],
            "event_span": "project.index",
            "evidence_relation": ".microcosm/evidence/index.json",
            "macro_analogue": "kind atlas / source inventory",
            "public_boundary": "file-role projection; does not read private parent state",
        },
        {
            "primitive_id": "pattern",
            "public_name": "Pattern",
            "what_it_does": (
                "Maps catalog roles into repo-shape pattern observations through "
                "the public pattern surface."
            ),
            "input": "catalog",
            "output": ".microcosm/patterns.json",
            "state_ref": ".microcosm/patterns.json",
            "runtime_commands": ["microcosm patterns <project>"],
            "endpoint_refs": ["/project/patterns"],
            "event_span": "project.patterns",
            "evidence_relation": ".microcosm/evidence/patterns.json",
            "macro_analogue": "pattern atlas / pattern binding",
            "public_boundary": "public heuristic observation, not doctrine promotion",
        },
        {
            "primitive_id": "standard",
            "public_name": "Standard",
            "what_it_does": "Records public constraints for reversible local state.",
            "input": "architecture kernel + route/work records",
            "output": "standard pressure rows inside explanations",
            "state_ref": ".microcosm/architecture.json",
            "runtime_commands": ["microcosm architecture <project>", "microcosm explain <project> <route_id>"],
            "endpoint_refs": ["/project/architecture"],
            "event_span": "project.architecture",
            "evidence_relation": ".microcosm/state_index.json",
            "macro_analogue": "standards / principles / axioms",
            "public_boundary": "public pressure rows, not global doctrine authority",
        },
        {
            "primitive_id": "route",
            "public_name": "Route",
            "what_it_does": (
                "Turns project-grounded pattern_refs into reversible next-action "
                "candidates after resolving them against .microcosm/patterns.json."
            ),
            "input": "catalog + pattern observations",
            "output": ".microcosm/routes.json",
            "state_ref": ".microcosm/routes.json",
            "runtime_commands": ["plectis route <project>", "plectis route inspect <project> <route_id>"],
            "endpoint_refs": ["/project/routes", "/project/explain/<route_id>"],
            "event_span": "project.route",
            "evidence_relation": ".microcosm/evidence/routes.json",
            "macro_analogue": "navigation hologram / option surface / route plane",
            "public_boundary": "route projection, not command authorization over user source",
        },
        {
            "primitive_id": "work",
            "public_name": "Work",
            "what_it_does": "Records a deterministic governed transaction over the project-local route snapshot.",
            "input": "selected route",
            "output": ".microcosm/work_items.json",
            "state_ref": ".microcosm/work_items.json",
            "runtime_commands": ["plectis work create <project>", "plectis work run <project>"],
            "endpoint_refs": ["/project/workitems", "/project/work/run"],
            "event_span": "work.create / work.run",
            "evidence_relation": ".microcosm/evidence/work_*.json",
            "macro_analogue": "mission transaction / WorkItem spine",
            "public_boundary": "simulated project-local transaction; no source mutation by default",
        },
        {
            "primitive_id": "event",
            "public_name": "Event",
            "what_it_does": "Emits a causal trace for project substrate operations.",
            "input": "runtime operations",
            "output": ".microcosm/events.jsonl",
            "state_ref": ".microcosm/events.jsonl",
            "runtime_commands": [
                "plectis observe --card <project>",
                "plectis observe <project>",
            ],
            "endpoint_refs": ["/project/status"],
            "event_span": "project.* / work.*",
            "evidence_relation": ".microcosm/events.jsonl",
            "macro_analogue": "observability runtime / trace stream",
            "public_boundary": "local event stream, not live telemetry authority",
        },
        {
            "primitive_id": "evidence",
            "public_name": "Evidence",
            "what_it_does": "Keeps generated receipts as black-box recorder drilldowns.",
            "input": "runtime operations",
            "output": ".microcosm/evidence/*.json",
            "state_ref": ".microcosm/evidence/",
            "runtime_commands": ["plectis evidence list <project> --limit 25", "plectis evidence inspect <project> <ref>"],
            "endpoint_refs": ["/project/evidence"],
            "event_span": "evidence.drilldown",
            "evidence_relation": ".microcosm/evidence/*.json",
            "macro_analogue": "evidence membrane / receipts",
            "public_boundary": "drilldown evidence, not the cockpit",
        },
        {
            "primitive_id": "explanation",
            "public_name": "Explanation",
            "what_it_does": (
                "Connects a route to grounded refs, resolved pattern bindings, "
                "primitives, standards, work shape, events, and evidence."
            ),
            "input": "route id + local state",
            "output": ".microcosm/explanations/<route_id>.json",
            "state_ref": ".microcosm/explanations/",
            "runtime_commands": ["microcosm explain <project> <route_id>", "plectis route inspect <project> <route_id>"],
            "endpoint_refs": ["/project/explain/<route_id>"],
            "event_span": "project.explain",
            "evidence_relation": ".microcosm/evidence/explain_<route_id>.json",
            "macro_analogue": "self-comprehension / route rationale",
            "public_boundary": "explanation of public local state only",
        },
        {
            "primitive_id": "assimilation",
            "public_name": "Assimilation",
            "what_it_does": "Captures reversible next-action and closeout signals without promoting global doctrine.",
            "input": "work result + explanation + event stream",
            "output": "next_actions and closeout fields",
            "state_ref": ".microcosm/work_items.json",
            "runtime_commands": ["plectis work run <project>", "microcosm explain <project> <route_id>"],
            "endpoint_refs": ["/project/workitems"],
            "event_span": "work.run",
            "evidence_relation": ".microcosm/evidence/work_run_*.json",
            "macro_analogue": "pattern assimilation step",
            "public_boundary": "local closeout metadata, not live learning authority",
        },
    ],
}


def public_root() -> Path:
    """Resolve the public Plectis substrate root for source-ref reads.

    - Teleology: anchors every source-custody read (kernel manifest, standard-pressure surface) to the package's own public root, never an ambient cwd.
    - Guarantee: returns the absolute `parents[2]` of this module file; stable regardless of caller cwd.
    - Fails: never raises; returns a Path that may not exist if the package tree is relocated.
    - When-needed: inspect when a manifest/surface read resolves against an unexpected directory.
    - Reads: derives from `__file__` only; reads no manifest itself.
    - Non-goal: does not authorize source-body export, release, or whole-system correctness.
    """
    return Path(__file__).resolve().parents[2]


def state_dir(project: str | Path) -> Path:
    """Compute the project-local `.microcosm` state directory path.

    - Teleology: single source of the project-local state root so every builder writes under one bounded `.microcosm` boundary.
    - Guarantee: returns `<resolved project>/.microcosm` (STATE_DIR); user-expanded, non-strict resolve so a not-yet-created project still yields a path.
    - Fails: never raises; returns a path that may not exist on disk.
    - When-needed: inspect when generated artifacts land outside the expected project-local directory.
    - Reads: no file read; pure path computation from `project`.
    - Non-goal: does not create the directory, read parent/private state, or authorize source mutation.
    """
    return Path(project).expanduser().resolve(strict=False) / STATE_DIR


def project_relative(project: Path, path: Path) -> str:
    """Render a path relative to the project root for project-local refs.

    - Teleology: keep emitted source-refs project-relative so generated state never leaks absolute private host paths.
    - Guarantee: returns the POSIX path of `path` relative to `project`; on a non-subpath returns the bare `path.name` instead.
    - Fails: never raises; ValueError on non-relative paths is caught and degraded to `path.name`.
    - When-needed: inspect when a generated ref shows an absolute path or an unexpected basename.
    - Reads: filesystem-resolves both paths (non-strict); reads no file contents.
    - Non-goal: does not authorize export of out-of-tree paths or public-safe equivalence.
    """
    try:
        return path.resolve(strict=False).relative_to(project.resolve(strict=False)).as_posix()
    except ValueError:
        return path.name


def _path_is_file(path: Path) -> bool:
    """Test whether a path is a regular file, swallowing OS errors.

    - Teleology: OSError-safe existence probe so state reads degrade to empty rather than crashing on permission/FS faults.
    - Guarantee: returns True only when `path.is_file()` is True; any OSError is treated as False.
    - Fails: never raises; OSError -> returns False.
    - When-needed: inspect when an existing state file is reported as absent under FS/permission trouble.
    - Non-goal: does not distinguish missing-vs-unreadable; not an authority on file content validity.
    """
    try:
        return path.is_file()
    except OSError:
        return False


def _path_is_dir(path: Path) -> bool:
    """Test whether a path is a directory, swallowing OS errors.

    - Teleology: OSError-safe directory probe so evidence/explanation directory scans degrade to empty rather than crash.
    - Guarantee: returns True only when `path.is_dir()` is True; any OSError is treated as False.
    - Fails: never raises; OSError -> returns False.
    - When-needed: inspect when an existing evidence/explanation directory is reported as absent under FS/permission trouble.
    - Non-goal: does not list or validate directory contents.
    """
    try:
        return path.is_dir()
    except OSError:
        return False


def read_json_if_exists(path: Path) -> dict[str, Any]:
    """Read a JSON object from a path, returning {} when absent or non-object.

    - Teleology: tolerant manifest/state reader so a missing project-local artifact yields an empty dict instead of an error, letting builders fall back to defaults.
    - Guarantee: returns the parsed dict when `path` is a readable file whose JSON root is an object; returns {} when the file is missing or the root is not a dict.
    - Fails: surfaces JSON/decoding errors from `read_json_strict` on a present-but-malformed file (does not swallow parse errors); missing file -> {} (no raise).
    - When-needed: inspect when a builder unexpectedly uses defaults despite a state file appearing to exist.
    - Reads: `path` (any project-local or source JSON object file).
    - Escalates-to: `microcosm_core.schemas.read_json_strict` for the strict-parse contract.
    - Non-goal: does not validate schema, authorize source-body export, or treat the read as release authority.
    """
    if not _path_is_file(path):
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of object rows.

    - Teleology: materialize the project-local event stream (`.microcosm/events.jsonl`) into dict rows for downstream evidence/explanation reads.
    - Guarantee: returns the list of dict rows from the file; non-dict lines and blank lines are skipped; missing file -> [].
    - Fails: surfaces `json.loads` errors on a present-but-malformed line (does not swallow parse errors); missing file -> [] (no raise).
    - When-needed: inspect when the event stream appears empty or a malformed line breaks observability.
    - Reads: `path` (typically `.microcosm/events.jsonl`).
    - Non-goal: does not validate event schema or treat the stream as live telemetry authority.
    """
    return list(_iter_jsonl_dict_rows(path))


def _iter_jsonl_dict_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Stream object rows from a JSONL file without buffering the whole file.

    - Teleology: streaming primitive behind `read_jsonl` and event-ref reads so large event streams are scanned line-by-line.
    - Guarantee: yields each non-blank line parsed as JSON when its root is a dict; non-dict roots are skipped; missing file yields nothing.
    - Fails: surfaces `json.loads` errors on a malformed line; missing file -> empty iterator (no raise).
    - When-needed: inspect when event-stream iteration stops early or raises on a corrupt line.
    - Reads: `path` line-by-line, UTF-8.
    - Non-goal: does not validate row schema or close-out completeness.
    """
    if not _path_is_file(path):
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                yield payload


def _read_explanation_event_refs(path: Path, *, limit: int = 12) -> list[dict[str, Any]]:
    """Collect the last N route/work event refs for a route explanation.

    - Teleology: feed the causal-chain proof of `explain_route` with the most recent explanation-relevant events without inlining full event bodies.
    - Guarantee: returns up to `limit` most-recent rows whose `span` is in {project.route, project.explain, work.create, work.run}, each reduced to {event_id, span, status}; `limit <= 0` -> [].
    - Fails: surfaces `json.loads` errors from the underlying stream on a malformed line; missing file -> [] (no raise).
    - When-needed: inspect when an explanation shows too few or stale event refs.
    - Reads: `path` (the event stream).
    - Non-goal: does not prove correctness or act as live telemetry authority; refs are drilldown pointers only.
    """
    if limit <= 0:
        return []
    spans = {"project.route", "project.explain", "work.create", "work.run"}
    refs: deque[dict[str, Any]] = deque(maxlen=limit)
    for row in _iter_jsonl_dict_rows(path):
        if row.get("span") not in spans:
            continue
        refs.append(
            {
                "event_id": row.get("event_id"),
                "span": row.get("span"),
                "status": row.get("status"),
            }
        )
    return list(refs)


def _exercised_primitives_from_event_refs(
    causal_event_refs: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Occurrence: which primitives this run actually exercised, from event spans.

    - Teleology: the explanation must distinguish what a run EXERCISED (occurrence)
      from the declared kernel catalog (declaration). A primitive is exercised iff
      one of its non-glob ``event_span`` tokens exactly matches a span present in
      this run's ``causal_event_refs``. This is the honest occurrence field; the
      top-level ``kernel_primitives`` list is a declared catalog, not run-derived,
      so the two need not — and generally do not — match.
    - Guarantee: returns ``(exercised_event_spans, exercised_primitives)``, both
      sorted and de-duplicated; ``exercised_primitives`` is a subset of the
      manifest's declared primitive_ids; glob spans (e.g. ``project.* / work.*``)
      never mark a primitive exercised because they would match everything.
    - Fails: never raises; non-dict rows and odd manifest entries are skipped; an
      empty ref list yields ``([], [])``.
    - When-needed: inspect when an explanation claims a primitive ran whose span is
      absent from this run's event refs (the occurrence-vs-declaration trap).
    - Non-goal: does not assert correctness or that every declared primitive ran.
    """
    spans = sorted(
        {
            str(row.get("span"))
            for row in causal_event_refs
            if isinstance(row, dict) and row.get("span")
        }
    )
    span_set = set(spans)
    exercised: set[str] = set()
    for prim in manifest.get("primitives", []):
        if not isinstance(prim, dict):
            continue
        primitive_id = prim.get("primitive_id")
        if not primitive_id:
            continue
        tokens = [tok.strip() for tok in str(prim.get("event_span", "")).split("/")]
        if any(tok and "*" not in tok and tok in span_set for tok in tokens):
            exercised.add(str(primitive_id))
    return spans, sorted(exercised)


def _execution_instance(
    selected_work: dict[str, Any] | None,
    route_id: str | None,
    state_history: list[str],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Single-execution partition of a route explanation, correlated by work_id.

    - Teleology: a route accumulates many work transactions over time, so the
      causal_chain_proof's top-level event/evidence refs are the route NEIGHBOURHOOD
      (every run), not one invocation. This partition scopes the witness to the
      SELECTED work transaction's OWN ``event_refs``/``evidence_refs`` — which the
      runtime correlates to it by ``work_id`` at emission — so events or evidence from
      other runs of the same route cannot enter it. This is correlation closure built
      from existing fields, not an inferred run boundary.
    - Guarantee: returns the selected work's correlated refs plus exercised spans /
      primitives derived only from THIS execution's events; selection_basis records
      that the work is chosen by the representative first-closed heuristic, NOT causal
      invocation binding; correlation_status / single_execution_scoped report VERIFIED
      correlation, so a missing/empty selected_work yields empty refs, ``[]`` exercised
      sets, correlation_status ``no_selected_work``, and single_execution_scoped False.
    - Fails: never raises; non-list ref fields are treated as empty.
    - When-needed: inspect when a route explanation appears to mix events or evidence
      from more than one run.
    - Non-goal: does not assert the execution is terminal/complete (see
      causal_chain status) nor that it is eligible as the public reference witness.
    """
    work = selected_work if isinstance(selected_work, dict) else {}
    raw_event_refs = work.get("event_refs")
    raw_evidence_refs = work.get("evidence_refs")
    event_refs = _dedupe_event_refs(
        raw_event_refs if isinstance(raw_event_refs, list) else []
    )
    evidence_refs = _dedupe_strings(
        raw_evidence_refs if isinstance(raw_evidence_refs, list) else []
    )
    spans, primitives = _exercised_primitives_from_event_refs(event_refs, manifest)
    has_correlated_work = bool(work.get("work_id")) and bool(event_refs)
    return {
        "scope_mode": "single_work_transaction",
        "selection_basis": "representative_first_closed_work_not_causal_invocation",
        "correlation_status": (
            "work_correlated" if has_correlated_work else "no_selected_work"
        ),
        "single_execution_scoped": has_correlated_work,
        "correlation_basis": "selected_work_transaction_work_id",
        "selected_work_id": work.get("work_id"),
        "selected_work_status": work.get("status"),
        "route_id": route_id,
        "state_history": state_history,
        "event_refs": event_refs,
        "event_ref_count": len(event_refs),
        "evidence_refs": evidence_refs,
        "evidence_ref_count": len(evidence_refs),
        "exercised_event_spans": spans,
        "exercised_primitives": primitives,
        "note": (
            "Representative single-work partition: scoped to the SELECTED work "
            "transaction's own work_id-correlated event_refs/evidence_refs, so other "
            "runs of this route cannot enter it. selection_basis is the first-closed "
            "heuristic — representative for browsing, NOT the transaction caused by a "
            "specific command invocation; a causal invocation-bound witness is a "
            "separate reference-case artifact. correlation_status and "
            "single_execution_scoped report VERIFIED correlation, not the requested "
            "scope_mode (an absent selected work does not self-certify)."
        ),
    }


def command_state_snapshot(project_path: str | Path) -> dict[str, Any]:
    """Snapshot the project-local execution state at command boundaries.

    - Teleology: the command-causality assay needs a before/after boundary so
      ambient history cannot masquerade as execution output just because it is
      nearby in the same route.
    - Guarantee: returns stable ids/refs for work rows, event rows, and evidence
      receipts under `.microcosm`; no source files are read and no state is
      mutated.
    - Fails: malformed JSON/JSONL surfaces errors; missing state surfaces empty
      lists.
    - When-needed: take a before snapshot, run one command, then build a
      reference execution case with this snapshot as `before_state`.
    - Non-goal: does not prove correctness or define causality by itself; it is
      only the boundary input to a relation-based assay.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    work_payload = read_json_if_exists(state / "work_items.json")
    work_ids = [
        str(row.get("work_id"))
        for row in work_payload.get("work_items", [])
        if isinstance(row, dict) and row.get("work_id")
    ]
    event_ids = [
        str(row.get("event_id"))
        for row in _iter_jsonl_dict_rows(state / EVENT_STREAM)
        if row.get("event_id")
    ]
    evidence_root = state / EVIDENCE_DIR
    evidence_refs: list[str] = []
    if _path_is_dir(evidence_root):
        for root, _dirs, files in os.walk(evidence_root):
            for name in files:
                if not name.endswith(".json"):
                    continue
                path = Path(root) / name
                evidence_refs.append(project_relative(project, path))
    return {
        "schema_version": "microcosm_command_state_snapshot_v1",
        "project_ref": ".",
        "state_ref": STATE_DIR,
        "work_ids": sorted(work_ids),
        "event_ids": sorted(event_ids),
        "evidence_refs": sorted(evidence_refs),
    }


def _snapshot_delta(
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any],
) -> dict[str, Any]:
    """Compute set deltas between command-state snapshots."""
    if not isinstance(before_state, dict):
        return {
            "status": "not_supplied",
            "new_work_ids": [],
            "new_event_ids": [],
            "new_evidence_refs": [],
        }

    def _new_values(key: str) -> list[str]:
        before = {
            str(item)
            for item in before_state.get(key, [])
            if isinstance(item, str) and item
        }
        after = [
            str(item)
            for item in after_state.get(key, [])
            if isinstance(item, str) and item
        ]
        return [item for item in after if item not in before]

    return {
        "status": "available",
        "new_work_ids": _new_values("work_ids"),
        "new_event_ids": _new_values("event_ids"),
        "new_evidence_refs": _new_values("evidence_refs"),
    }


def _evidence_ref_exists(project: Path, evidence_ref: str) -> bool:
    """Return whether a project-local evidence ref resolves under `.microcosm`."""
    prefix = f"{STATE_DIR}/"
    rel = evidence_ref.removeprefix(prefix)
    return _path_is_file(state_dir(project) / rel)


def _work_state_history(work: dict[str, Any]) -> list[str]:
    """Extract ordered state names from a work row."""
    history = work.get("state_history")
    if not isinstance(history, list):
        return []
    return [
        str(row.get("state"))
        for row in history
        if isinstance(row, dict) and row.get("state")
    ]


def _semantic_digest(payload: dict[str, Any]) -> str:
    """Stable digest over a canonical semantic payload."""
    body = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def build_reference_execution_case(
    project_path: str | Path,
    route_id: str,
    command_result: dict[str, Any],
    *,
    command_kind: str = "work.run",
    before_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a command-root execution case from returned handles and local state.

    - Teleology: answer "what exactly did THIS command cause?" without relying on
      first-closed/last-closed heuristics, route neighbourhood aggregation, or an
      opaque trace id. The root is the command-returned `work_id`; events and
      evidence enter only through preserved work/event/evidence relations.
    - Guarantee: returns a typed occurrence graph, record classifications,
      topology-preserving aliases, semantic digest, independent predicate statuses,
      and ambient-history exclusions. A selected older same-route work row cannot
      enter the occurrence witness unless it is the returned `work_id`.
    - Fails: never raises for missing work ids; missing refs become failed
      predicates in the returned case.
    - Reads: `.microcosm/work_items.json`, `.microcosm/events.jsonl`,
      `.microcosm/evidence/`, and the route explanation if present.
    - Non-goal: does not make the route explanation or architecture page eligible
      as the public witness; projection fidelity is reported separately.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    work_id = str(command_result.get("work_id") or "")
    work_payload = read_json_if_exists(state / "work_items.json")
    work_items = [
        row
        for row in work_payload.get("work_items", [])
        if isinstance(row, dict)
    ]
    selected_work = next(
        (row for row in work_items if row.get("work_id") == work_id),
        None,
    )
    work = selected_work if isinstance(selected_work, dict) else {}
    event_refs = _dedupe_event_refs(
        work.get("event_refs") if isinstance(work.get("event_refs"), list) else []
    )
    evidence_refs = _dedupe_strings(
        work.get("evidence_refs") if isinstance(work.get("evidence_refs"), list) else []
    )
    events_by_id = {
        str(row.get("event_id")): row
        for row in _iter_jsonl_dict_rows(state / EVENT_STREAM)
        if row.get("event_id")
    }
    event_ids = [str(row.get("event_id")) for row in event_refs if row.get("event_id")]
    missing_event_ids = [
        event_id for event_id in event_ids if event_id not in events_by_id
    ]
    missing_evidence_refs = [
        ref for ref in evidence_refs if not _evidence_ref_exists(project, ref)
    ]
    same_route_work_ids = [
        str(row.get("work_id"))
        for row in work_items
        if row.get("route_id") == route_id and row.get("work_id")
    ]
    ambient_work_ids = [
        candidate for candidate in same_route_work_ids if candidate != work_id
    ]
    selected_event_id_set = set(event_ids)
    ambient_event_ids = [
        event_id
        for event_id, row in events_by_id.items()
        if row.get("route_id") == route_id and event_id not in selected_event_id_set
    ]
    returned_evidence_ref = str(command_result.get("evidence_ref") or "")
    returned_ref_set = {returned_evidence_ref} if returned_evidence_ref else set()
    event_aliases = {
        event_id: f"event_{index}"
        for index, event_id in enumerate(event_ids, start=1)
    }
    evidence_aliases = {
        evidence_ref: f"evidence_{index}"
        for index, evidence_ref in enumerate(evidence_refs, start=1)
    }
    work_alias = "work_1" if work_id else None
    records: list[dict[str, Any]] = []
    if work_alias:
        records.append(
            {
                "alias": work_alias,
                "record_type": "work_transaction",
                "classification": "direct_child",
                "truth_class": "occurrence",
                "source_ref": f"{STATE_DIR}/work_items.json::{work_id}",
                "binding": "command_result.work_id",
                "status": work.get("status"),
                "included_in_occurrence_witness": bool(work),
            }
        )
    for event_ref in event_refs:
        event_id = str(event_ref.get("event_id") or "")
        records.append(
            {
                "alias": event_aliases.get(event_id),
                "record_type": "event",
                "classification": "causal_descendant",
                "truth_class": "occurrence",
                "source_ref": f"{STATE_DIR}/{EVENT_STREAM}::{event_id}",
                "binding": "work_item.event_refs",
                "span": event_ref.get("span"),
                "status": event_ref.get("status"),
                "included_in_occurrence_witness": event_id in selected_event_id_set,
            }
        )
    for evidence_ref in evidence_refs:
        records.append(
            {
                "alias": evidence_aliases.get(evidence_ref),
                "record_type": "evidence",
                "classification": (
                    "direct_child"
                    if evidence_ref in returned_ref_set
                    else "causal_descendant"
                ),
                "truth_class": "occurrence",
                "source_ref": evidence_ref,
                "binding": (
                    "command_result.evidence_ref"
                    if evidence_ref in returned_ref_set
                    else "work_item.evidence_refs"
                ),
                "included_in_occurrence_witness": True,
            }
        )
    structural_records = [
        {
            "record_type": "route",
            "classification": "structural_lookup",
            "truth_class": "structure",
            "source_ref": f"{STATE_DIR}/routes.json::{route_id}",
            "included_in_occurrence_witness": False,
        },
        {
            "record_type": "authority_ceiling",
            "classification": "structural_constitutional_lookup",
            "truth_class": "constitution",
            "source_ref": "architecture_kernel._base",
            "included_in_occurrence_witness": False,
        },
    ]
    ambient_records = [
        {
            "record_type": "work_transaction",
            "classification": "ambient_history",
            "truth_class": "occurrence",
            "source_ref": f"{STATE_DIR}/work_items.json::{ambient_work_id}",
            "route_id": route_id,
            "included_in_occurrence_witness": False,
            "exclusion_reason": (
                "same_route_work_not_reachable_from_command_result_work_id"
            ),
        }
        for ambient_work_id in ambient_work_ids
    ]
    ambient_records.extend(
        {
            "record_type": "event",
            "classification": "ambient_history",
            "truth_class": "occurrence",
            "source_ref": f"{STATE_DIR}/{EVENT_STREAM}::{ambient_event_id}",
            "route_id": route_id,
            "included_in_occurrence_witness": False,
            "exclusion_reason": (
                "same_route_event_not_reachable_from_command_result_work_id"
            ),
        }
        for ambient_event_id in ambient_event_ids
    )
    record_classification_matrix = [
        *records,
        *structural_records,
        *ambient_records,
    ]
    record_classification_counts: dict[str, int] = {}
    for row in record_classification_matrix:
        classification = str(row.get("classification") or "")
        if not classification:
            continue
        record_classification_counts[classification] = (
            record_classification_counts.get(classification, 0) + 1
        )
    alias_map = {
        "execution": {"command_result": "execution_1"},
        "work": {work_id: work_alias} if work_alias else {},
        "events": event_aliases,
        "evidence": evidence_aliases,
    }
    semantic_nodes: list[dict[str, Any]] = [
        {
            "alias": "execution_1",
            "kind": "command_invocation",
            "command_kind": command_kind,
            "route_id": route_id,
        }
    ]
    if work_alias:
        semantic_nodes.append(
            {
                "alias": work_alias,
                "kind": "work_transaction",
                "status": work.get("status"),
                "state_history": _work_state_history(work),
                "route_id": route_id,
                "source_files_mutated": work.get("source_files_mutated") is True,
            }
        )
    for event_ref in event_refs:
        event_id = str(event_ref.get("event_id") or "")
        semantic_nodes.append(
            {
                "alias": event_aliases.get(event_id),
                "kind": "event",
                "span": event_ref.get("span"),
                "status": event_ref.get("status"),
            }
        )
    for evidence_ref in evidence_refs:
        semantic_nodes.append(
            {
                "alias": evidence_aliases.get(evidence_ref),
                "kind": "evidence",
                "returned_by_command": evidence_ref in returned_ref_set,
            }
        )
    semantic_edges: list[dict[str, str]] = []
    if work_alias:
        semantic_edges.append(
            {"from": "execution_1", "to": work_alias, "relation": "returned_work_id"}
        )
    for event_id in event_ids:
        alias = event_aliases.get(event_id)
        if work_alias and alias:
            semantic_edges.append(
                {"from": work_alias, "to": alias, "relation": "work_event_ref"}
            )
    for evidence_ref in evidence_refs:
        alias = evidence_aliases.get(evidence_ref)
        if work_alias and alias:
            semantic_edges.append(
                {"from": work_alias, "to": alias, "relation": "work_evidence_ref"}
            )
    semantic_graph = {
        "schema_version": "microcosm_reference_execution_semantic_graph_v1",
        "nodes": semantic_nodes,
        "edges": semantic_edges,
    }
    semantic_digest = _semantic_digest(semantic_graph)
    occurrence_witness_refs = _dedupe_strings(
        [str(row.get("source_ref") or "") for row in records]
    )
    explanation = read_json_if_exists(state / EXPLANATION_DIR / f"{route_id}.json")
    proof = explanation.get("causal_chain_proof") if isinstance(explanation, dict) else {}
    proof = proof if isinstance(proof, dict) else {}
    execution_instance = proof.get("execution_instance")
    execution_instance = execution_instance if isinstance(execution_instance, dict) else {}
    projection_selected_work_id = execution_instance.get("selected_work_id") or proof.get(
        "selected_work_id"
    )
    projection_fidelity_ok = (
        projection_selected_work_id == work_id if projection_selected_work_id else None
    )
    state_delta = _snapshot_delta(before_state, command_state_snapshot(project))
    state_delta_work_ids = _dedupe_strings(
        state_delta.get("new_work_ids")
        if isinstance(state_delta.get("new_work_ids"), list)
        else []
    )
    state_delta_event_ids = _dedupe_strings(
        state_delta.get("new_event_ids")
        if isinstance(state_delta.get("new_event_ids"), list)
        else []
    )
    state_delta_evidence_refs = _dedupe_strings(
        state_delta.get("new_evidence_refs")
        if isinstance(state_delta.get("new_evidence_refs"), list)
        else []
    )
    command_reference_case_ref = str(command_result.get("reference_execution_case_ref") or "")
    allowed_state_delta_evidence_refs = set(evidence_refs)
    if command_reference_case_ref:
        allowed_state_delta_evidence_refs.add(command_reference_case_ref)
    unexpected_state_delta_event_ids = []
    for event_id in state_delta_event_ids:
        if event_id in selected_event_id_set:
            continue
        event_row = events_by_id.get(event_id)
        event_work_id = str(event_row.get("work_id") or "") if event_row else ""
        event_route_id = str(event_row.get("route_id") or "") if event_row else ""
        if event_work_id and event_work_id != work_id:
            unexpected_state_delta_event_ids.append(event_id)
        elif event_route_id == route_id and event_work_id != work_id:
            unexpected_state_delta_event_ids.append(event_id)
    state_delta_scope = state_delta["status"] == "not_supplied" or (
        state_delta["status"] == "available"
        and all(item == work_id for item in state_delta_work_ids)
        and not unexpected_state_delta_event_ids
        and all(
            item in allowed_state_delta_evidence_refs
            for item in state_delta_evidence_refs
        )
    )
    assertion_matrix = [
        {
            "claim_id": "work_row_and_receipts_join_without_missing_refs",
            "truth_class": "occurrence",
            "authority_ref": f"{STATE_DIR}/work_items.json::{work_id}",
            "claim_value": not missing_event_ids and not missing_evidence_refs,
            "execution_binding": "work_1 -> event_* / evidence_*",
            "evidence_refs": evidence_refs,
            "eligibility_predicate": "join_integrity",
        },
        {
            "claim_id": "command_returned_work_id_selects_case_root",
            "truth_class": "occurrence",
            "authority_ref": "command_result.work_id",
            "claim_value": work_id or None,
            "execution_binding": "execution_1 -> work_1",
            "evidence_refs": [f"{STATE_DIR}/work_items.json::{work_id}"]
            if work_id
            else [],
            "eligibility_predicate": "selection_binding",
        },
        {
            "claim_id": "work_refs_define_causal_descendants",
            "truth_class": "occurrence",
            "authority_ref": f"{STATE_DIR}/work_items.json::{work_id}",
            "claim_value": {
                "event_ids": event_ids,
                "evidence_refs": evidence_refs,
            },
            "execution_binding": "work_1 -> event_* / evidence_*",
            "evidence_refs": evidence_refs,
            "eligibility_predicate": "scope_completeness",
        },
        {
            "claim_id": "work_transaction_reached_terminal_state",
            "truth_class": "occurrence",
            "authority_ref": f"{STATE_DIR}/work_items.json::{work_id}",
            "claim_value": work.get("status"),
            "execution_binding": "work_1.status",
            "evidence_refs": evidence_refs,
            "eligibility_predicate": "execution_terminality",
        },
        {
            "claim_id": "source_mutation_is_constitutionally_excluded",
            "truth_class": "constitution",
            "authority_ref": f"{STATE_DIR}/work_items.json::{work_id}",
            "claim_value": work.get("source_files_mutated") is not True,
            "execution_binding": "work_1.source_files_mutated",
            "evidence_refs": evidence_refs,
            "eligibility_predicate": "authority_boundedness",
        },
        {
            "claim_id": "state_delta_contains_root_or_descendant",
            "truth_class": "occurrence",
            "authority_ref": f"{STATE_DIR}/state_index.json",
            "claim_value": state_delta,
            "execution_binding": "execution_1 -> state_delta",
            "evidence_refs": state_delta_evidence_refs,
            "eligibility_predicate": "replay_equivalence",
        },
        {
            "claim_id": "state_delta_excludes_ambient_history",
            "truth_class": "occurrence",
            "authority_ref": f"{STATE_DIR}/state_index.json",
            "claim_value": state_delta_scope,
            "execution_binding": "execution_1 -> state_delta",
            "evidence_refs": state_delta_evidence_refs,
            "eligibility_predicate": "state_delta_scope",
        },
        {
            "claim_id": "record_classification_matrix_partitions_command_scope",
            "truth_class": "projection",
            "authority_ref": "reference_execution_case.record_classification_matrix",
            "claim_value": record_classification_counts,
            "execution_binding": "record_classification_matrix",
            "evidence_refs": occurrence_witness_refs,
            "eligibility_predicate": "record_classification_matrix",
        },
        {
            "claim_id": "public_architecture_projection_matches_case_root",
            "truth_class": "projection",
            "authority_ref": f"{STATE_DIR}/{EXPLANATION_DIR}/{route_id}.json",
            "claim_value": projection_selected_work_id,
            "execution_binding": projection_selected_work_id,
            "evidence_refs": [f"{STATE_DIR}/{EXPLANATION_DIR}/{route_id}.json"],
            "eligibility_predicate": "projection_fidelity",
        },
    ]
    assertion_predicate_ids = [
        str(row.get("eligibility_predicate") or "")
        for row in assertion_matrix
        if row.get("eligibility_predicate")
    ]
    assertion_matrix_coverage = sorted(assertion_predicate_ids) == sorted(
        REFERENCE_CASE_ASSERTION_PREDICATES
    )
    predicate_status = {
        "join_integrity": bool(work_id)
        and bool(work)
        and not missing_event_ids
        and not missing_evidence_refs,
        "selection_binding": bool(work_id) and command_result.get("work_id") == work_id,
        "scope_completeness": bool(work)
        and set(event_ids) == selected_event_id_set
        and not any(event_id in selected_event_id_set for event_id in ambient_event_ids),
        "execution_terminality": work.get("status") in {"closed", PASS},
        "authority_boundedness": work.get("source_files_mutated") is not True,
        "replay_equivalence": state_delta["status"] == "not_supplied"
        or (
            state_delta["status"] == "available"
            and (
                work_id in state_delta.get("new_work_ids", [])
                or bool(state_delta.get("new_event_ids"))
                or bool(state_delta.get("new_evidence_refs"))
            )
        ),
        "state_delta_scope": state_delta_scope,
        "record_classification_matrix": (
            bool(record_classification_matrix)
            and len(record_classification_matrix)
            == sum(record_classification_counts.values())
        ),
        "projection_fidelity": projection_fidelity_ok,
        "assertion_matrix_coverage": assertion_matrix_coverage,
    }
    command_case_eligible = all(
        predicate_status[key] is True
        for key in [
            "join_integrity",
            "selection_binding",
            "scope_completeness",
            "execution_terminality",
            "authority_boundedness",
            "replay_equivalence",
            "state_delta_scope",
            "record_classification_matrix",
            "assertion_matrix_coverage",
        ]
    )
    public_architecture_witness_eligible = (
        command_case_eligible and predicate_status["projection_fidelity"] is True
    )
    return {
        **_base(project, "microcosm_reference_execution_case_v1"),
        "case_id": "command_causality_reference_execution",
        "command_kind": command_kind,
        "route_id": route_id,
        "root_binding": {
            "binding_kind": "command_returned_work_id",
            "work_id": work_id or None,
            "command_result_schema": command_result.get("schema_version"),
        },
        "record_classifications": records,
        "structural_and_constitutional_lookups": structural_records,
        "ambient_history_excluded": {
            "work_ids": ambient_work_ids,
            "event_ids": ambient_event_ids,
            "records": ambient_records,
            "policy": "same-route ambient records are excluded unless reachable from command_result.work_id through work/event/evidence refs",
        },
        "record_classification_matrix": record_classification_matrix,
        "record_classification_counts": record_classification_counts,
        "state_delta": state_delta,
        "alias_map": alias_map,
        "semantic_graph": semantic_graph,
        "semantic_digest": semantic_digest,
        "occurrence_witness_refs": occurrence_witness_refs,
        "predicate_status": predicate_status,
        "predicate_details": {
            "missing_event_ids": missing_event_ids,
            "missing_evidence_refs": missing_evidence_refs,
            "projection_selected_work_id": projection_selected_work_id,
        },
        "command_case_eligible": command_case_eligible,
        "public_architecture_witness_eligible": public_architecture_witness_eligible,
        "required_assertion_predicates": list(REFERENCE_CASE_ASSERTION_PREDICATES),
        "assertion_matrix": assertion_matrix,
        "anti_claim": (
            "This case is a command-root occurrence assay. It does not make the "
            "route explanation, architecture page, release surface, or whole-system "
            "correctness claim eligible unless projection_fidelity and the other "
            "independent predicates pass."
        ),
    }


def _dict_rows(value: Any) -> list[dict[str, Any]]:
    """Return dict rows from a list-like payload and ignore malformed values."""
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _event_number_from_id(event_id: object) -> int | None:
    token = str(event_id or "")
    if not token.startswith("evt_"):
        return None
    try:
        return int(token.rsplit("_", 1)[-1])
    except ValueError:
        return None


def _truth_row_authority_ref(row: dict[str, Any]) -> str:
    """Return the authority/source ref used to classify a truth row."""
    return str(row.get("source_ref") or row.get("authority_ref") or "")


def _truth_row_identity(row: dict[str, Any]) -> str:
    """Build a stable comparison key for rendered truth rows."""
    claim_id = row.get("claim_id")
    if isinstance(claim_id, str) and claim_id:
        return f"claim_id:{claim_id}"
    authority_ref = _truth_row_authority_ref(row)
    if authority_ref:
        return f"authority_ref:{authority_ref}"
    alias = row.get("alias")
    if isinstance(alias, str) and alias:
        return f"alias:{alias}"
    return ""


def reference_state_delta_refs(state_delta: Any) -> list[str]:
    """Return rendered state refs implied by a reference case state_delta."""
    delta = state_delta if isinstance(state_delta, dict) else {}
    work_ids = _dedupe_strings(
        delta.get("new_work_ids")
        if isinstance(delta.get("new_work_ids"), list)
        else []
    )
    event_ids = _dedupe_strings(
        delta.get("new_event_ids")
        if isinstance(delta.get("new_event_ids"), list)
        else []
    )
    evidence_refs = _dedupe_strings(
        delta.get("new_evidence_refs")
        if isinstance(delta.get("new_evidence_refs"), list)
        else []
    )
    return _dedupe_strings(
        [
            *[f"{STATE_DIR}/work_items.json::{work_id}" for work_id in work_ids],
            *[f"{STATE_DIR}/{EVENT_STREAM}::{event_id}" for event_id in event_ids],
            *evidence_refs,
        ]
    )


def _expected_reference_semantic_graph(
    *,
    route_id: str,
    command_kind: str,
    work: dict[str, Any],
    event_refs: list[dict[str, Any]],
    evidence_refs: list[str],
    returned_evidence_ref: str = "",
) -> dict[str, Any]:
    """Reconstruct a reference-case graph directly from raw project state."""
    work_id = str(work.get("work_id") or "")
    work_alias = "work_1" if work_id else None
    event_ids = [str(row.get("event_id")) for row in event_refs if row.get("event_id")]
    event_aliases = {
        event_id: f"event_{index}"
        for index, event_id in enumerate(event_ids, start=1)
    }
    evidence_aliases = {
        evidence_ref: f"evidence_{index}"
        for index, evidence_ref in enumerate(evidence_refs, start=1)
    }
    returned_ref_set = {returned_evidence_ref} if returned_evidence_ref else set()
    nodes: list[dict[str, Any]] = [
        {
            "alias": "execution_1",
            "kind": "command_invocation",
            "command_kind": command_kind,
            "route_id": route_id,
        }
    ]
    if work_alias:
        nodes.append(
            {
                "alias": work_alias,
                "kind": "work_transaction",
                "status": work.get("status"),
                "state_history": _work_state_history(work),
                "route_id": route_id,
                "source_files_mutated": work.get("source_files_mutated") is True,
            }
        )
    for event_ref in event_refs:
        event_id = str(event_ref.get("event_id") or "")
        nodes.append(
            {
                "alias": event_aliases.get(event_id),
                "kind": "event",
                "span": event_ref.get("span"),
                "status": event_ref.get("status"),
            }
        )
    for evidence_ref in evidence_refs:
        nodes.append(
            {
                "alias": evidence_aliases.get(evidence_ref),
                "kind": "evidence",
                "returned_by_command": evidence_ref in returned_ref_set,
            }
        )
    edges: list[dict[str, str]] = []
    if work_alias:
        edges.append(
            {"from": "execution_1", "to": work_alias, "relation": "returned_work_id"}
        )
    for event_id in event_ids:
        alias = event_aliases.get(event_id)
        if work_alias and alias:
            edges.append(
                {"from": work_alias, "to": alias, "relation": "work_event_ref"}
            )
    for evidence_ref in evidence_refs:
        alias = evidence_aliases.get(evidence_ref)
        if work_alias and alias:
            edges.append(
                {"from": work_alias, "to": alias, "relation": "work_evidence_ref"}
            )
    return {
        "schema_version": "microcosm_reference_execution_semantic_graph_v1",
        "nodes": nodes,
        "edges": edges,
    }


def verify_reference_execution_case(
    project_path: str | Path,
    case: dict[str, Any],
    *,
    rendered_witness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Independently verify a command-root reference execution case.

    - Teleology: triangulate the case from raw work/event/evidence state so the
      producer's confidence, renderer fields, and ambient route history cannot
      self-certify a public witness.
    - Guarantee: rereads work rows, event stream, evidence refs, route
      explanation, assertion rows, and optional rendered witness card; returns a
      pass/fail receipt with independent predicate details.
    - Fails: never raises for missing case fields; malformed project JSON/JSONL
      still surfaces via the strict readers.
    - Reads: `.microcosm/work_items.json`, `.microcosm/events.jsonl`,
      `.microcosm/evidence/`, and `.microcosm/explanations/<route>.json`.
    - Non-goal: does not rebuild the case or mutate project state.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    root_binding = case.get("root_binding")
    root_binding = root_binding if isinstance(root_binding, dict) else {}
    work_id = str(root_binding.get("work_id") or "")
    route_id = str(case.get("route_id") or "")
    command_kind = str(case.get("command_kind") or "")
    work_payload = read_json_if_exists(state / "work_items.json")
    work_items = _dict_rows(work_payload.get("work_items"))
    work = next((row for row in work_items if row.get("work_id") == work_id), {})
    work = work if isinstance(work, dict) else {}
    event_refs = _dedupe_event_refs(
        work.get("event_refs") if isinstance(work.get("event_refs"), list) else []
    )
    evidence_refs = _dedupe_strings(
        work.get("evidence_refs") if isinstance(work.get("evidence_refs"), list) else []
    )
    event_ids = [str(row.get("event_id")) for row in event_refs if row.get("event_id")]
    events_by_id = {
        str(row.get("event_id")): row
        for row in _iter_jsonl_dict_rows(state / EVENT_STREAM)
        if row.get("event_id")
    }
    missing_event_ids = [
        event_id for event_id in event_ids if event_id not in events_by_id
    ]
    missing_evidence_refs = [
        ref for ref in evidence_refs if not _evidence_ref_exists(project, ref)
    ]
    closeout = work.get("closeout")
    closeout = closeout if isinstance(closeout, dict) else {}
    returned_evidence_ref = str(closeout.get("evidence_ref") or "")
    if not returned_evidence_ref and evidence_refs:
        returned_evidence_ref = evidence_refs[-1]
    if not returned_evidence_ref:
        for row in _dict_rows(case.get("record_classifications")):
            if row.get("binding") == "command_result.evidence_ref":
                returned_evidence_ref = str(row.get("source_ref") or "")
                break
    expected_graph = _expected_reference_semantic_graph(
        route_id=route_id,
        command_kind=command_kind,
        work=work,
        event_refs=event_refs,
        evidence_refs=evidence_refs,
        returned_evidence_ref=returned_evidence_ref,
    )
    expected_semantic_digest = _semantic_digest(expected_graph)
    allowed_occurrence_refs = {
        f"{STATE_DIR}/work_items.json::{work_id}",
        *[f"{STATE_DIR}/{EVENT_STREAM}::{event_id}" for event_id in event_ids],
        *evidence_refs,
    }
    allowed_truth_occurrence_refs = {
        *allowed_occurrence_refs,
        f"{STATE_DIR}/state_index.json",
    }
    case_occurrence_refs = _dedupe_strings(
        [
            str(row.get("source_ref") or "")
            for row in _dict_rows(case.get("record_classifications"))
            if row.get("truth_class") == "occurrence"
            and row.get("included_in_occurrence_witness") is not False
        ]
    )
    case_occurrence_witness_refs = _dedupe_strings(
        case.get("occurrence_witness_refs")
        if isinstance(case.get("occurrence_witness_refs"), list)
        else []
    )
    missing_occurrence_refs = [
        ref for ref in sorted(allowed_occurrence_refs) if ref not in case_occurrence_refs
    ]
    unexpected_case_occurrence_refs = [
        ref for ref in case_occurrence_refs if ref not in allowed_occurrence_refs
    ]
    missing_occurrence_witness_refs = [
        ref
        for ref in sorted(allowed_occurrence_refs)
        if ref not in case_occurrence_witness_refs
    ]
    unexpected_occurrence_witness_refs = [
        ref for ref in case_occurrence_witness_refs if ref not in allowed_occurrence_refs
    ]
    case_created_at = str(case.get("created_at") or "")
    selected_event_numbers = [
        event_number
        for event_id in event_ids
        if (event_number := _event_number_from_id(event_id)) is not None
    ]
    max_selected_event_number = (
        max(selected_event_numbers) if selected_event_numbers else None
    )

    def _row_visible_when_case_was_created(row: Mapping[str, Any]) -> bool:
        created_at = str(row.get("created_at") or "")
        return not case_created_at or not created_at or created_at <= case_created_at

    def _event_visible_when_case_was_created(
        event_id: str,
        row: Mapping[str, Any],
    ) -> bool:
        event_number = _event_number_from_id(event_id)
        if max_selected_event_number is not None and event_number is not None:
            return event_number <= max_selected_event_number
        return _row_visible_when_case_was_created(row)

    def _work_visible_when_case_was_created(row: Mapping[str, Any]) -> bool:
        row_work_id = str(row.get("work_id") or "")
        if row_work_id == work_id:
            return True
        row_event_numbers = [
            event_number
            for event_ref in _dict_rows(row.get("event_refs"))
            if (
                event_number := _event_number_from_id(event_ref.get("event_id"))
            )
            is not None
        ]
        if max_selected_event_number is not None and row_event_numbers:
            return min(row_event_numbers) <= max_selected_event_number
        return _row_visible_when_case_was_created(row)

    same_route_work_ids = [
        str(row.get("work_id"))
        for row in work_items
        if row.get("route_id") == route_id
        and row.get("work_id")
        and _work_visible_when_case_was_created(row)
    ]
    ambient_work_refs = {
        f"{STATE_DIR}/work_items.json::{candidate}"
        for candidate in same_route_work_ids
        if candidate != work_id
    }
    selected_event_id_set = set(event_ids)
    ambient_event_refs = {
        f"{STATE_DIR}/{EVENT_STREAM}::{event_id}"
        for event_id, row in events_by_id.items()
        if row.get("route_id") == route_id
        and event_id not in selected_event_id_set
        and _event_visible_when_case_was_created(event_id, row)
    }
    ambient_occurrence_refs_in_case = sorted(
        (set(case_occurrence_refs) | set(case_occurrence_witness_refs))
        & (ambient_work_refs | ambient_event_refs)
    )
    expected_record_classification_rows: list[dict[str, Any]] = []
    if work_id:
        expected_record_classification_rows.append(
            {
                "record_type": "work_transaction",
                "classification": "direct_child",
                "truth_class": "occurrence",
                "source_ref": f"{STATE_DIR}/work_items.json::{work_id}",
                "binding": "command_result.work_id",
                "included_in_occurrence_witness": bool(work),
            }
        )
    for event_ref in event_refs:
        event_id = str(event_ref.get("event_id") or "")
        expected_record_classification_rows.append(
            {
                "record_type": "event",
                "classification": "causal_descendant",
                "truth_class": "occurrence",
                "source_ref": f"{STATE_DIR}/{EVENT_STREAM}::{event_id}",
                "binding": "work_item.event_refs",
                "included_in_occurrence_witness": event_id in selected_event_id_set,
            }
        )
    for evidence_ref in evidence_refs:
        direct_child = (
            bool(returned_evidence_ref) and evidence_ref == returned_evidence_ref
        )
        expected_record_classification_rows.append(
            {
                "record_type": "evidence",
                "classification": (
                    "direct_child" if direct_child else "causal_descendant"
                ),
                "truth_class": "occurrence",
                "source_ref": evidence_ref,
                "binding": "command_result.evidence_ref"
                if direct_child
                else "work_item.evidence_refs",
                "included_in_occurrence_witness": True,
            }
        )
    expected_record_classification_rows.extend(
        [
            {
                "record_type": "route",
                "classification": "structural_lookup",
                "truth_class": "structure",
                "source_ref": f"{STATE_DIR}/routes.json::{route_id}",
                "binding": "",
                "included_in_occurrence_witness": False,
            },
            {
                "record_type": "authority_ceiling",
                "classification": "structural_constitutional_lookup",
                "truth_class": "constitution",
                "source_ref": "architecture_kernel._base",
                "binding": "",
                "included_in_occurrence_witness": False,
            },
        ]
    )
    expected_record_classification_rows.extend(
        {
            "record_type": "work_transaction",
            "classification": "ambient_history",
            "truth_class": "occurrence",
            "source_ref": ambient_ref,
            "binding": "",
            "included_in_occurrence_witness": False,
        }
        for ambient_ref in sorted(ambient_work_refs)
    )
    expected_record_classification_rows.extend(
        {
            "record_type": "event",
            "classification": "ambient_history",
            "truth_class": "occurrence",
            "source_ref": ambient_ref,
            "binding": "",
            "included_in_occurrence_witness": False,
        }
        for ambient_ref in sorted(ambient_event_refs)
    )

    record_classification_matrix_violations: list[dict[str, Any]] = []

    def _classification_row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            str(row.get("source_ref") or ""),
            str(row.get("record_type") or ""),
            str(row.get("classification") or ""),
            str(row.get("truth_class") or ""),
            str(row.get("binding") or ""),
            row.get("included_in_occurrence_witness"),
        )

    def _classification_key_payload(key: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "source_ref": key[0],
            "record_type": key[1],
            "classification": key[2],
            "truth_class": key[3],
            "binding": key[4],
            "included_in_occurrence_witness": key[5],
        }

    def _key_counts(rows: list[dict[str, Any]]) -> dict[tuple[Any, ...], int]:
        counts: dict[tuple[Any, ...], int] = {}
        for row in rows:
            key = _classification_row_key(row)
            counts[key] = counts.get(key, 0) + 1
        return counts

    raw_record_classification_matrix = case.get("record_classification_matrix")
    if not isinstance(raw_record_classification_matrix, list):
        record_classification_matrix_violations.append(
            {
                "field": "record_classification_matrix",
                "reason": "record_classification_matrix_missing_or_invalid",
                "rendered": type(raw_record_classification_matrix).__name__,
            }
        )
    record_classification_rows = _dict_rows(raw_record_classification_matrix)
    normalized_record_classification_rows: list[dict[str, Any]] = []
    for index, row in enumerate(record_classification_rows):
        normalized = {
            "source_ref": str(row.get("source_ref") or ""),
            "record_type": str(row.get("record_type") or ""),
            "classification": str(row.get("classification") or ""),
            "truth_class": str(row.get("truth_class") or ""),
            "binding": str(row.get("binding") or ""),
            "included_in_occurrence_witness": row.get(
                "included_in_occurrence_witness"
            ),
        }
        missing_fields = [
            field_name
            for field_name in (
                "source_ref",
                "record_type",
                "classification",
                "truth_class",
            )
            if not normalized[field_name]
        ]
        if missing_fields:
            record_classification_matrix_violations.append(
                {
                    "row_index": index,
                    "reason": "record_classification_matrix_missing_fields",
                    "missing": missing_fields,
                }
            )
        if not isinstance(normalized["included_in_occurrence_witness"], bool):
            record_classification_matrix_violations.append(
                {
                    "row_index": index,
                    "field": "included_in_occurrence_witness",
                    "reason": "record_classification_matrix_inclusion_flag_invalid",
                    "rendered": normalized["included_in_occurrence_witness"],
                }
            )
        normalized_record_classification_rows.append(normalized)
    expected_classification_key_counts = _key_counts(
        expected_record_classification_rows
    )
    case_classification_key_counts = _key_counts(
        normalized_record_classification_rows
    )
    missing_record_classification_rows: list[dict[str, Any]] = []
    unexpected_record_classification_rows: list[dict[str, Any]] = []
    for key, expected_count in expected_classification_key_counts.items():
        missing_count = expected_count - case_classification_key_counts.get(key, 0)
        if missing_count > 0:
            missing_record_classification_rows.append(
                {**_classification_key_payload(key), "count": missing_count}
            )
    for key, rendered_count in case_classification_key_counts.items():
        unexpected_count = rendered_count - expected_classification_key_counts.get(
            key, 0
        )
        if unexpected_count > 0:
            unexpected_record_classification_rows.append(
                {**_classification_key_payload(key), "count": unexpected_count}
            )
    if missing_record_classification_rows:
        record_classification_matrix_violations.append(
            {
                "reason": "record_classification_matrix_missing_rows",
                "missing": missing_record_classification_rows,
            }
        )
    if unexpected_record_classification_rows:
        record_classification_matrix_violations.append(
            {
                "reason": "record_classification_matrix_unexpected_rows",
                "rendered": unexpected_record_classification_rows,
            }
        )

    def _classification_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            classification = str(row.get("classification") or "")
            if not classification:
                continue
            counts[classification] = counts.get(classification, 0) + 1
        return counts

    expected_record_classification_counts = _classification_counts(
        expected_record_classification_rows
    )
    rendered_counts_value = case.get("record_classification_counts")
    rendered_record_classification_counts: dict[str, int] = {}
    invalid_rendered_record_classification_counts: dict[str, Any] = {}
    if isinstance(rendered_counts_value, dict):
        for key, value in rendered_counts_value.items():
            if (
                not isinstance(key, str)
                or not isinstance(value, int)
                or isinstance(value, bool)
            ):
                invalid_rendered_record_classification_counts[str(key)] = value
                continue
            rendered_record_classification_counts[key] = value
    else:
        record_classification_matrix_violations.append(
            {
                "field": "record_classification_counts",
                "reason": "record_classification_counts_missing_or_invalid",
                "rendered": type(rendered_counts_value).__name__,
            }
        )
    if invalid_rendered_record_classification_counts:
        record_classification_matrix_violations.append(
            {
                "field": "record_classification_counts",
                "reason": "record_classification_counts_invalid_values",
                "rendered": invalid_rendered_record_classification_counts,
            }
        )
    if rendered_record_classification_counts != expected_record_classification_counts:
        record_classification_matrix_violations.append(
            {
                "field": "record_classification_counts",
                "reason": "record_classification_counts_mismatch",
                "expected": expected_record_classification_counts,
                "rendered": rendered_record_classification_counts,
            }
        )
    ambient_history = case.get("ambient_history_excluded")
    ambient_history = ambient_history if isinstance(ambient_history, dict) else {}
    normalized_ambient_history_rows: list[dict[str, Any]] = []
    for row in _dict_rows(ambient_history.get("records")):
        normalized_ambient_history_rows.append(
            {
                "source_ref": str(row.get("source_ref") or ""),
                "record_type": str(row.get("record_type") or ""),
                "classification": str(row.get("classification") or ""),
                "truth_class": str(row.get("truth_class") or ""),
                "binding": str(row.get("binding") or ""),
                "included_in_occurrence_witness": row.get(
                    "included_in_occurrence_witness"
                ),
            }
        )
    expected_ambient_history_rows = [
        row
        for row in expected_record_classification_rows
        if row.get("classification") == "ambient_history"
    ]
    if _key_counts(normalized_ambient_history_rows) != _key_counts(
        expected_ambient_history_rows
    ):
        record_classification_matrix_violations.append(
            {
                "field": "ambient_history_excluded.records",
                "reason": "ambient_history_records_mismatch",
                "expected": sorted(
                    [
                        _classification_key_payload(key)
                        for key in _key_counts(expected_ambient_history_rows)
                    ],
                    key=lambda row: str(row.get("source_ref") or ""),
                ),
                "rendered": sorted(
                    [
                        _classification_key_payload(key)
                        for key in _key_counts(normalized_ambient_history_rows)
                    ],
                    key=lambda row: str(row.get("source_ref") or ""),
                ),
            }
        )
    record_classification_matrix_ok = not record_classification_matrix_violations
    alias_map = case.get("alias_map")
    alias_map = alias_map if isinstance(alias_map, dict) else {}
    work_aliases = alias_map.get("work")
    work_aliases = work_aliases if isinstance(work_aliases, dict) else {}
    semantic_graph = case.get("semantic_graph")
    semantic_graph = semantic_graph if isinstance(semantic_graph, dict) else {}
    semantic_edges = _dict_rows(semantic_graph.get("edges"))
    work_record_sources = {
        str(row.get("source_ref") or "")
        for row in _dict_rows(case.get("record_classifications"))
        if row.get("binding") == "command_result.work_id"
    }
    selection_binding = (
        root_binding.get("binding_kind") == "command_returned_work_id"
        and bool(work_id)
        and bool(work)
        and work_aliases.get(work_id) == "work_1"
        and f"{STATE_DIR}/work_items.json::{work_id}" in work_record_sources
        and any(
            edge.get("from") == "execution_1"
            and edge.get("to") == "work_1"
            and edge.get("relation") == "returned_work_id"
            for edge in semantic_edges
        )
    )
    scope_completeness = (
        bool(work)
        and not missing_occurrence_refs
        and not unexpected_case_occurrence_refs
        and not missing_occurrence_witness_refs
        and not unexpected_occurrence_witness_refs
        and not ambient_occurrence_refs_in_case
    )
    execution_terminality = work.get("status") in {"closed", PASS}
    authority_boundedness = work.get("source_files_mutated") is not True
    state_delta = case.get("state_delta")
    state_delta = state_delta if isinstance(state_delta, dict) else {}
    delta_status = str(state_delta.get("status") or "")
    delta_work_ids = _dedupe_strings(
        state_delta.get("new_work_ids")
        if isinstance(state_delta.get("new_work_ids"), list)
        else []
    )
    delta_event_ids = _dedupe_strings(
        state_delta.get("new_event_ids")
        if isinstance(state_delta.get("new_event_ids"), list)
        else []
    )
    delta_evidence_refs = _dedupe_strings(
        state_delta.get("new_evidence_refs")
        if isinstance(state_delta.get("new_evidence_refs"), list)
        else []
    )
    unexpected_delta_work_ids = [
        item for item in delta_work_ids if item != work_id
    ]
    unexpected_delta_event_ids = []
    for event_id in delta_event_ids:
        if event_id in event_ids:
            continue
        event_row = events_by_id.get(event_id)
        event_work_id = str(event_row.get("work_id") or "") if event_row else ""
        event_route_id = str(event_row.get("route_id") or "") if event_row else ""
        if event_work_id and event_work_id != work_id:
            unexpected_delta_event_ids.append(event_id)
        elif event_route_id == route_id and event_work_id != work_id:
            unexpected_delta_event_ids.append(event_id)
    reference_case_ref = str(work.get("reference_execution_case_ref") or "")
    case_evidence_ref = str(case.get("evidence_ref") or "")
    allowed_delta_evidence_refs = set(evidence_refs)
    for ref in (reference_case_ref, case_evidence_ref):
        if ref:
            allowed_delta_evidence_refs.add(ref)
    unexpected_delta_evidence_refs = [
        item for item in delta_evidence_refs if item not in allowed_delta_evidence_refs
    ]
    state_delta_scope_violations: list[dict[str, Any]] = []
    if unexpected_delta_work_ids:
        state_delta_scope_violations.append(
            {
                "field": "new_work_ids",
                "reason": "state_delta_work_id_outside_command_root",
                "expected": [work_id] if work_id else [],
                "unexpected": unexpected_delta_work_ids,
            }
        )
    if unexpected_delta_event_ids:
        state_delta_scope_violations.append(
            {
                "field": "new_event_ids",
                "reason": "state_delta_event_id_outside_selected_work",
                "expected": event_ids,
                "unexpected": unexpected_delta_event_ids,
            }
        )
    if unexpected_delta_evidence_refs:
        state_delta_scope_violations.append(
            {
                "field": "new_evidence_refs",
                "reason": "state_delta_evidence_ref_outside_selected_work",
                "expected": sorted(allowed_delta_evidence_refs),
                "unexpected": unexpected_delta_evidence_refs,
            }
        )
    if delta_status not in {"available", "not_supplied"}:
        state_delta_scope_violations.append(
            {
                "field": "status",
                "reason": "state_delta_status_unknown",
                "expected": ["available", "not_supplied"],
                "rendered": delta_status,
            }
        )
    state_delta_scope = not state_delta_scope_violations
    expected_rendered_state_delta_refs = reference_state_delta_refs(state_delta)
    after_state = command_state_snapshot(project)
    after_work_ids = set(after_state.get("work_ids", []))
    after_event_ids = set(after_state.get("event_ids", []))
    after_evidence_refs = set(after_state.get("evidence_refs", []))
    missing_delta_work_ids = [
        item for item in delta_work_ids if item not in after_work_ids
    ]
    missing_delta_event_ids = [
        item for item in delta_event_ids if item not in after_event_ids
    ]
    missing_delta_evidence_refs = [
        item for item in delta_evidence_refs if item not in after_evidence_refs
    ]
    delta_has_root_or_descendant = (
        work_id in delta_work_ids
        or any(event_id in delta_event_ids for event_id in event_ids)
        or any(ref in delta_evidence_refs for ref in evidence_refs)
    )
    if delta_status == "not_supplied":
        replay_equivalence = True
        replay_equivalence_basis = "not_supplied_legacy_unasserted"
    elif delta_status == "available":
        replay_equivalence = (
            delta_has_root_or_descendant
            and not missing_delta_work_ids
            and not missing_delta_event_ids
            and not missing_delta_evidence_refs
        )
        replay_equivalence_basis = (
            "available_delta_contains_root_or_descendant"
            if replay_equivalence
            else "available_delta_missing_root_or_descendant_or_current_state_ref"
        )
    else:
        replay_equivalence = False
        replay_equivalence_basis = "state_delta_status_unknown"
    failed_predicates: list[str] = []
    assertion_matrix_rows = _dict_rows(case.get("assertion_matrix"))
    assertion_matrix_coverage_violations: list[dict[str, Any]] = []
    assertion_predicate_ids: list[str] = []
    assertion_predicate_counts: dict[str, int] = {}
    for index, row in enumerate(assertion_matrix_rows):
        predicate_id = row.get("eligibility_predicate")
        if not isinstance(predicate_id, str) or not predicate_id:
            assertion_matrix_coverage_violations.append(
                {
                    "row_index": index,
                    "reason": "assertion_matrix_missing_eligibility_predicate",
                    "rendered": predicate_id,
                }
            )
            continue
        assertion_predicate_ids.append(predicate_id)
        assertion_predicate_counts[predicate_id] = (
            assertion_predicate_counts.get(predicate_id, 0) + 1
        )
    for predicate_id in REFERENCE_CASE_ASSERTION_PREDICATES:
        count = assertion_predicate_counts.get(predicate_id, 0)
        if count == 0:
            assertion_matrix_coverage_violations.append(
                {
                    "predicate_id": predicate_id,
                    "reason": "assertion_matrix_missing_required_predicate",
                }
            )
        elif count > 1:
            assertion_matrix_coverage_violations.append(
                {
                    "predicate_id": predicate_id,
                    "reason": "assertion_matrix_duplicate_required_predicate",
                    "count": count,
                }
            )
    for predicate_id, count in sorted(assertion_predicate_counts.items()):
        if predicate_id not in REFERENCE_CASE_ASSERTION_PREDICATES:
            assertion_matrix_coverage_violations.append(
                {
                    "predicate_id": predicate_id,
                    "reason": "assertion_matrix_unknown_predicate",
                    "count": count,
                }
            )
    assertion_matrix_coverage = not assertion_matrix_coverage_violations
    truth_class_violations: list[dict[str, Any]] = []
    truth_rows = [
        row
        for group_key in ("record_classifications", "assertion_matrix")
        for row in _dict_rows(case.get(group_key))
    ]
    truth_rows.extend(
        row
        for row in _dict_rows(case.get("structural_and_constitutional_lookups"))
    )
    compact_truth_rows = [
        row
        for group_key in ("assertion_matrix", "structural_and_constitutional_lookups")
        for row in _dict_rows(case.get(group_key))
    ]
    compact_truth_classes = [
        truth_class
        for row in compact_truth_rows
        if isinstance((truth_class := row.get("truth_class")), str)
    ]
    expected_truth_classes = sorted(set(compact_truth_classes))
    expected_truth_class_counts = {
        truth_class: compact_truth_classes.count(truth_class)
        for truth_class in expected_truth_classes
    }
    case_truth_rows_by_identity: dict[str, dict[str, Any]] = {}
    for row in truth_rows:
        identity = _truth_row_identity(row)
        if identity:
            case_truth_rows_by_identity[identity] = row
    for row in truth_rows:
        truth_class = row.get("truth_class")
        source_ref = _truth_row_authority_ref(row)
        if truth_class not in {"occurrence", "structure", "constitution", "projection"}:
            truth_class_violations.append(
                {
                    "claim_id": row.get("claim_id"),
                    "source_ref": source_ref,
                    "truth_class": truth_class,
                    "reason": "unknown_truth_class",
                }
            )
            continue
        if (
            truth_class == "occurrence"
            and source_ref != "command_result.work_id"
            and source_ref not in allowed_truth_occurrence_refs
        ):
            truth_class_violations.append(
                {
                    "claim_id": row.get("claim_id"),
                    "source_ref": source_ref,
                    "truth_class": truth_class,
                    "reason": "occurrence_claim_without_occurrence_ref",
                }
            )
    explanation = read_json_if_exists(state / EXPLANATION_DIR / f"{route_id}.json")
    proof = explanation.get("causal_chain_proof")
    proof = proof if isinstance(proof, dict) else {}
    execution_instance = proof.get("execution_instance")
    execution_instance = execution_instance if isinstance(execution_instance, dict) else {}
    projection_selected_work_id = execution_instance.get("selected_work_id") or proof.get(
        "selected_work_id"
    )
    projection_fidelity = (
        projection_selected_work_id == work_id if projection_selected_work_id else None
    )
    truth_class_authority = not truth_class_violations
    join_integrity = (
        bool(work_id)
        and bool(work)
        and not missing_event_ids
        and not missing_evidence_refs
    )
    semantic_digest_ok = case.get("semantic_digest") == expected_semantic_digest
    independent_predicate_status = {
        "join_integrity": join_integrity,
        "selection_binding": selection_binding,
        "scope_completeness": scope_completeness,
        "execution_terminality": execution_terminality,
        "authority_boundedness": authority_boundedness,
        "replay_equivalence": replay_equivalence,
        "state_delta_scope": state_delta_scope,
        "record_classification_matrix": record_classification_matrix_ok,
        "projection_fidelity": projection_fidelity,
        "truth_class_authority": truth_class_authority,
        "semantic_digest": semantic_digest_ok,
        "assertion_matrix_coverage": assertion_matrix_coverage,
    }
    command_case_eligible = (
        all(
            independent_predicate_status[key] is True
            for key in [
                "join_integrity",
                "selection_binding",
                "scope_completeness",
                "execution_terminality",
                "authority_boundedness",
                "replay_equivalence",
                "state_delta_scope",
                "record_classification_matrix",
                "truth_class_authority",
                "semantic_digest",
                "assertion_matrix_coverage",
            ]
        )
    )
    public_architecture_witness_eligible = (
        command_case_eligible and projection_fidelity is True
    )
    for predicate_id in [
        "join_integrity",
        "selection_binding",
        "scope_completeness",
        "execution_terminality",
        "authority_boundedness",
        "replay_equivalence",
        "state_delta_scope",
        "record_classification_matrix",
        "truth_class_authority",
        "semantic_digest",
        "assertion_matrix_coverage",
    ]:
        if independent_predicate_status.get(predicate_id) is not True:
            failed_predicates.append(predicate_id)
    claimed_predicates = case.get("predicate_status")
    claimed_predicates = (
        claimed_predicates if isinstance(claimed_predicates, dict) else {}
    )
    if (
        claimed_predicates.get("projection_fidelity") is True
        and projection_fidelity is not True
    ):
        failed_predicates.append("projection_fidelity")
    if case.get("command_case_eligible") is True and not command_case_eligible:
        failed_predicates.append("command_case_eligible")
    if (
        case.get("public_architecture_witness_eligible") is True
        and not public_architecture_witness_eligible
    ):
        failed_predicates.append("public_architecture_witness_eligible")
    rendered_case = {}
    if isinstance(rendered_witness, dict):
        candidate = rendered_witness.get("command_reference_execution_case")
        rendered_case = candidate if isinstance(candidate, dict) else rendered_witness
    rendered_semantic_digest = rendered_case.get("semantic_digest")
    rendered_semantic_digest_ok = (
        not rendered_semantic_digest
        or rendered_semantic_digest == expected_semantic_digest
    )
    rendered_truth_class_violations: list[dict[str, Any]] = []
    rendered_truth_rows = [
        row
        for group_key in (
            "record_classifications",
            "assertion_matrix",
            "structural_and_constitutional_lookups",
        )
        for row in _dict_rows(rendered_case.get(group_key))
    ]
    for row in rendered_truth_rows:
        rendered_truth_class = row.get("truth_class")
        rendered_authority_ref = _truth_row_authority_ref(row)
        if rendered_truth_class not in {
            "occurrence",
            "structure",
            "constitution",
            "projection",
        }:
            rendered_truth_class_violations.append(
                {
                    "claim_id": row.get("claim_id"),
                    "source_ref": rendered_authority_ref,
                    "truth_class": rendered_truth_class,
                    "reason": "unknown_rendered_truth_class",
                }
            )
            continue
        expected_row = case_truth_rows_by_identity.get(_truth_row_identity(row))
        if expected_row:
            expected_truth_class = expected_row.get("truth_class")
            expected_authority_ref = _truth_row_authority_ref(expected_row)
            if rendered_truth_class != expected_truth_class:
                rendered_truth_class_violations.append(
                    {
                        "claim_id": row.get("claim_id"),
                        "source_ref": rendered_authority_ref,
                        "expected_truth_class": expected_truth_class,
                        "rendered_truth_class": rendered_truth_class,
                        "reason": "rendered_truth_class_mismatch",
                    }
                )
            if (
                rendered_authority_ref
                and expected_authority_ref
                and rendered_authority_ref != expected_authority_ref
            ):
                rendered_truth_class_violations.append(
                    {
                        "claim_id": row.get("claim_id"),
                        "expected_source_ref": expected_authority_ref,
                        "rendered_source_ref": rendered_authority_ref,
                        "reason": "rendered_authority_ref_mismatch",
                    }
                )
        if (
            rendered_truth_class == "occurrence"
            and rendered_authority_ref != "command_result.work_id"
            and rendered_authority_ref not in allowed_truth_occurrence_refs
        ):
            rendered_truth_class_violations.append(
                {
                    "claim_id": row.get("claim_id"),
                    "source_ref": rendered_authority_ref,
                    "truth_class": rendered_truth_class,
                    "reason": "rendered_occurrence_claim_without_occurrence_ref",
                }
            )
    rendered_truth_class_authority = not rendered_truth_class_violations
    rendered_assertion_matrix_coverage_violations: list[dict[str, Any]] = []
    rendered_assertion_matrix_present = "assertion_matrix" in rendered_case
    if rendered_assertion_matrix_present:
        rendered_assertion_predicate_counts: dict[str, int] = {}
        for index, row in enumerate(_dict_rows(rendered_case.get("assertion_matrix"))):
            predicate_id = row.get("eligibility_predicate")
            if not isinstance(predicate_id, str) or not predicate_id:
                rendered_assertion_matrix_coverage_violations.append(
                    {
                        "row_index": index,
                        "reason": (
                            "rendered_assertion_matrix_missing_eligibility_predicate"
                        ),
                        "rendered": predicate_id,
                    }
                )
                continue
            rendered_assertion_predicate_counts[predicate_id] = (
                rendered_assertion_predicate_counts.get(predicate_id, 0) + 1
            )
        for predicate_id in REFERENCE_CASE_ASSERTION_PREDICATES:
            count = rendered_assertion_predicate_counts.get(predicate_id, 0)
            if count == 0:
                rendered_assertion_matrix_coverage_violations.append(
                    {
                        "predicate_id": predicate_id,
                        "reason": (
                            "rendered_assertion_matrix_missing_required_predicate"
                        ),
                    }
                )
            elif count > 1:
                rendered_assertion_matrix_coverage_violations.append(
                    {
                        "predicate_id": predicate_id,
                        "reason": (
                            "rendered_assertion_matrix_duplicate_required_predicate"
                        ),
                        "count": count,
                    }
                )
        for predicate_id, count in sorted(rendered_assertion_predicate_counts.items()):
            if predicate_id not in REFERENCE_CASE_ASSERTION_PREDICATES:
                rendered_assertion_matrix_coverage_violations.append(
                    {
                        "predicate_id": predicate_id,
                        "reason": "rendered_assertion_matrix_unknown_predicate",
                        "count": count,
                    }
                )
    rendered_assertion_matrix_coverage = (
        not rendered_assertion_matrix_coverage_violations
    )
    rendered_truth_class_summary_violations: list[dict[str, Any]] = []
    rendered_truth_classes_value = rendered_case.get("truth_classes")
    if isinstance(rendered_truth_classes_value, list):
        invalid_rendered_truth_classes = [
            item for item in rendered_truth_classes_value if not isinstance(item, str)
        ]
        rendered_truth_classes = sorted(
            set(
                item
                for item in rendered_truth_classes_value
                if isinstance(item, str)
            )
        )
        if invalid_rendered_truth_classes:
            rendered_truth_class_summary_violations.append(
                {
                    "reason": "rendered_truth_classes_invalid",
                    "rendered": invalid_rendered_truth_classes,
                }
            )
        if rendered_truth_classes != expected_truth_classes:
            rendered_truth_class_summary_violations.append(
                {
                    "reason": "rendered_truth_classes_mismatch",
                    "expected": expected_truth_classes,
                    "rendered": rendered_truth_classes,
                }
            )
    elif "truth_classes" in rendered_case:
        rendered_truth_class_summary_violations.append(
            {
                "reason": "rendered_truth_classes_invalid",
                "rendered": rendered_truth_classes_value,
            }
        )
    rendered_truth_class_counts_value = rendered_case.get("truth_class_counts")
    if isinstance(rendered_truth_class_counts_value, dict):
        rendered_truth_class_counts: dict[str, int] = {}
        invalid_rendered_truth_class_counts: dict[str, Any] = {}
        for key, value in rendered_truth_class_counts_value.items():
            if (
                not isinstance(key, str)
                or not isinstance(value, int)
                or isinstance(value, bool)
            ):
                invalid_rendered_truth_class_counts[str(key)] = value
                continue
            rendered_truth_class_counts[key] = value
        if invalid_rendered_truth_class_counts:
            rendered_truth_class_summary_violations.append(
                {
                    "reason": "rendered_truth_class_counts_invalid",
                    "rendered": invalid_rendered_truth_class_counts,
                }
            )
        if rendered_truth_class_counts != expected_truth_class_counts:
            rendered_truth_class_summary_violations.append(
                {
                    "reason": "rendered_truth_class_counts_mismatch",
                    "expected": expected_truth_class_counts,
                    "rendered": rendered_truth_class_counts,
                }
            )
    elif "truth_class_counts" in rendered_case:
        rendered_truth_class_summary_violations.append(
            {
                "reason": "rendered_truth_class_counts_invalid",
                "rendered": rendered_truth_class_counts_value,
            }
        )
    rendered_truth_class_summary_ok = not rendered_truth_class_summary_violations
    rendered_root_binding_violations: list[dict[str, Any]] = []
    expected_rendered_root_fields = {
        "selected_work_id": work_id or None,
        "root_work_id": work_id or None,
        "root_binding_kind": root_binding.get("binding_kind"),
        "root_matches_selected_work": bool(work_id),
    }
    for field_name, expected_value in expected_rendered_root_fields.items():
        if field_name not in rendered_case:
            continue
        rendered_value = rendered_case.get(field_name)
        if rendered_value != expected_value:
            rendered_root_binding_violations.append(
                {
                    "field": field_name,
                    "reason": f"rendered_{field_name}_mismatch",
                    "expected": expected_value,
                    "rendered": rendered_value,
                }
            )
    reference_case_ref = work.get("reference_execution_case_ref")
    expected_evidence_ref = (
        reference_case_ref if isinstance(reference_case_ref, str) else ""
    )
    if "evidence_ref" in rendered_case:
        rendered_evidence_ref = rendered_case.get("evidence_ref")
        if not expected_evidence_ref:
            rendered_root_binding_violations.append(
                {
                    "field": "evidence_ref",
                    "reason": "rendered_evidence_ref_without_work_reference",
                    "expected": None,
                    "rendered": rendered_evidence_ref,
                }
            )
        elif rendered_evidence_ref != expected_evidence_ref:
            rendered_root_binding_violations.append(
                {
                    "field": "evidence_ref",
                    "reason": "rendered_evidence_ref_mismatch",
                    "expected": expected_evidence_ref,
                    "rendered": rendered_evidence_ref,
                }
            )
    expected_assertion_matrix_ref = (
        f"{expected_evidence_ref}::assertion_matrix"
        if expected_evidence_ref
        else None
    )
    if "assertion_matrix_ref" in rendered_case:
        rendered_assertion_matrix_ref = rendered_case.get("assertion_matrix_ref")
        if (
            not expected_assertion_matrix_ref
            or rendered_assertion_matrix_ref != expected_assertion_matrix_ref
        ):
            rendered_root_binding_violations.append(
                {
                    "field": "assertion_matrix_ref",
                    "reason": "rendered_assertion_matrix_ref_mismatch",
                    "expected": expected_assertion_matrix_ref,
                    "rendered": rendered_assertion_matrix_ref,
                }
            )
    expected_record_classification_matrix_ref = (
        f"{expected_evidence_ref}::record_classification_matrix"
        if expected_evidence_ref
        else None
    )
    expected_rendered_record_classification_summary = {
        "record_classification_counts": expected_record_classification_counts,
        "ambient_history_ref_count": expected_record_classification_counts.get(
            "ambient_history",
            0,
        ),
        "record_classification_matrix_ref": expected_record_classification_matrix_ref,
    }
    rendered_record_classification_summary_violations: list[dict[str, Any]] = []
    record_summary_fields = set(expected_rendered_record_classification_summary)
    record_summary_present = any(
        field in rendered_case for field in record_summary_fields
    )
    if record_summary_present:
        for field_name, expected_value in (
            expected_rendered_record_classification_summary.items()
        ):
            if field_name not in rendered_case:
                rendered_record_classification_summary_violations.append(
                    {
                        "field": field_name,
                        "reason": (
                            "rendered_record_classification_summary_missing_field"
                        ),
                        "expected": expected_value,
                    }
                )
                continue
            rendered_value = rendered_case.get(field_name)
            if field_name == "record_classification_counts":
                if isinstance(rendered_value, dict):
                    rendered_counts: dict[str, int] = {}
                    invalid_rendered_counts: dict[str, Any] = {}
                    for key, value in rendered_value.items():
                        if (
                            not isinstance(key, str)
                            or not isinstance(value, int)
                            or isinstance(value, bool)
                        ):
                            invalid_rendered_counts[str(key)] = value
                            continue
                        rendered_counts[key] = value
                    if invalid_rendered_counts:
                        rendered_record_classification_summary_violations.append(
                            {
                                "field": field_name,
                                "reason": (
                                    "rendered_record_classification_counts_invalid"
                                ),
                                "rendered": invalid_rendered_counts,
                            }
                        )
                    rendered_value = rendered_counts
                else:
                    rendered_record_classification_summary_violations.append(
                        {
                            "field": field_name,
                            "reason": (
                                "rendered_record_classification_counts_invalid"
                            ),
                            "rendered": rendered_value,
                        }
                    )
                    continue
            if rendered_value != expected_value:
                rendered_record_classification_summary_violations.append(
                    {
                        "field": field_name,
                        "reason": f"rendered_{field_name}_mismatch",
                        "expected": expected_value,
                        "rendered": rendered_value,
                    }
                )
    rendered_record_classification_summary_ok = (
        not rendered_record_classification_summary_violations
    )
    rendered_root_binding_ok = not rendered_root_binding_violations
    rendered_eligibility_flag_violations: list[dict[str, Any]] = []
    expected_rendered_eligibility_flags = {
        "command_case_eligible": command_case_eligible,
        "public_architecture_witness_eligible": public_architecture_witness_eligible,
        "producer_claimed_command_case_eligible": case.get("command_case_eligible")
        is True,
        "producer_claimed_public_architecture_witness_eligible": case.get(
            "public_architecture_witness_eligible"
        )
        is True,
    }
    for field_name, expected_value in expected_rendered_eligibility_flags.items():
        if field_name not in rendered_case:
            continue
        rendered_value = rendered_case.get(field_name)
        if rendered_value is not expected_value:
            rendered_eligibility_flag_violations.append(
                {
                    "field": field_name,
                    "reason": f"rendered_{field_name}_mismatch",
                    "expected": expected_value,
                    "rendered": rendered_value,
                }
            )
    rendered_eligibility_flags_ok = not rendered_eligibility_flag_violations
    rendered_occurrence_refs = _dedupe_strings(
        rendered_case.get("occurrence_witness_refs")
        if isinstance(rendered_case.get("occurrence_witness_refs"), list)
        else []
    )
    missing_rendered_occurrence_refs = [
        ref
        for ref in sorted(allowed_occurrence_refs)
        if ref not in rendered_occurrence_refs
    ]
    unexpected_rendered_occurrence_refs = [
        ref for ref in rendered_occurrence_refs if ref not in allowed_occurrence_refs
    ]
    rendered_occurrence_refs_ok = (
        not missing_rendered_occurrence_refs
        and not unexpected_rendered_occurrence_refs
    )
    rendered_state_delta_refs: list[str] = []
    missing_rendered_state_delta_refs: list[str] = []
    unexpected_rendered_state_delta_refs: list[str] = []
    rendered_state_delta_ref_violations: list[dict[str, Any]] = []
    rendered_state_delta_refs_value = rendered_case.get("state_delta_refs")
    if isinstance(rendered_state_delta_refs_value, list):
        invalid_rendered_state_delta_refs = [
            item
            for item in rendered_state_delta_refs_value
            if not isinstance(item, str)
        ]
        rendered_state_delta_refs = _dedupe_strings(
            [
                item
                for item in rendered_state_delta_refs_value
                if isinstance(item, str)
            ]
        )
        missing_rendered_state_delta_refs = [
            ref
            for ref in expected_rendered_state_delta_refs
            if ref not in rendered_state_delta_refs
        ]
        unexpected_rendered_state_delta_refs = [
            ref
            for ref in rendered_state_delta_refs
            if ref not in expected_rendered_state_delta_refs
        ]
        if invalid_rendered_state_delta_refs:
            rendered_state_delta_ref_violations.append(
                {
                    "reason": "rendered_state_delta_refs_invalid_items",
                    "rendered": invalid_rendered_state_delta_refs,
                }
            )
        if missing_rendered_state_delta_refs:
            rendered_state_delta_ref_violations.append(
                {
                    "reason": "rendered_state_delta_refs_missing_refs",
                    "expected": expected_rendered_state_delta_refs,
                    "missing": missing_rendered_state_delta_refs,
                }
            )
        if unexpected_rendered_state_delta_refs:
            rendered_state_delta_ref_violations.append(
                {
                    "reason": "rendered_state_delta_refs_unexpected_refs",
                    "expected": expected_rendered_state_delta_refs,
                    "rendered": unexpected_rendered_state_delta_refs,
                }
            )
    elif "state_delta_refs" in rendered_case:
        rendered_state_delta_ref_violations.append(
            {
                "field": "state_delta_refs",
                "reason": "rendered_state_delta_refs_invalid",
                "rendered": rendered_state_delta_refs_value,
            }
        )
    elif expected_rendered_state_delta_refs:
        missing_rendered_state_delta_refs = list(expected_rendered_state_delta_refs)
        rendered_state_delta_ref_violations.append(
            {
                "field": "state_delta_refs",
                "reason": "rendered_state_delta_refs_missing_field",
                "expected": expected_rendered_state_delta_refs,
            }
        )
    rendered_state_delta_refs_ok = not rendered_state_delta_ref_violations
    rendered_state_delta_summary_violations: list[dict[str, Any]] = []
    expected_state_delta_ref_count = len(expected_rendered_state_delta_refs)
    expected_state_delta_refs_ref = "command_reference_execution_case.state_delta_refs"
    expected_state_delta_scope_ref = "verification_predicate_status.state_delta_scope"

    def _check_rendered_state_delta_summary(
        summary: dict[str, Any],
        *,
        scope: str,
        count_field: str,
        verified_field: str,
        ref_field: str,
        scope_verified_field: str,
        scope_ref_field: str,
    ) -> None:
        expected_fields = {
            count_field: expected_state_delta_ref_count,
            verified_field: rendered_state_delta_refs_ok,
            ref_field: expected_state_delta_refs_ref,
            scope_verified_field: state_delta_scope,
            scope_ref_field: expected_state_delta_scope_ref,
        }
        for field_name, expected_value in expected_fields.items():
            if field_name not in summary:
                rendered_state_delta_summary_violations.append(
                    {
                        "scope": scope,
                        "field": field_name,
                        "reason": "rendered_state_delta_summary_missing_field",
                        "expected": expected_value,
                    }
                )
                continue
            rendered_value = summary.get(field_name)
            if rendered_value != expected_value:
                rendered_state_delta_summary_violations.append(
                    {
                        "scope": scope,
                        "field": field_name,
                        "reason": "rendered_state_delta_summary_mismatch",
                        "expected": expected_value,
                        "rendered": rendered_value,
                    }
                )

    if isinstance(rendered_witness, dict):
        compile_summary = rendered_witness.get("compile_summary")
        if isinstance(compile_summary, dict):
            _check_rendered_state_delta_summary(
                compile_summary,
                scope="compile_summary",
                count_field="command_reference_state_delta_ref_count",
                verified_field="command_reference_state_delta_refs_verified",
                ref_field="command_reference_state_delta_refs_ref",
                scope_verified_field=(
                    "command_reference_state_delta_scope_verified"
                ),
                scope_ref_field="command_reference_state_delta_scope_ref",
            )
        causal_chain_summary = rendered_witness.get("causal_chain_summary")
        if isinstance(causal_chain_summary, dict):
            summary_case = causal_chain_summary.get("command_reference_execution_case")
            if isinstance(summary_case, dict):
                _check_rendered_state_delta_summary(
                    summary_case,
                    scope="causal_chain_summary.command_reference_execution_case",
                    count_field="state_delta_ref_count",
                    verified_field="state_delta_refs_verified",
                    ref_field="state_delta_refs_ref",
                    scope_verified_field="state_delta_scope_verified",
                    scope_ref_field="state_delta_scope_ref",
                )
    rendered_state_delta_summary_ok = not rendered_state_delta_summary_violations
    expected_rendered_predicate_details = {
        "missing_event_ids": missing_event_ids,
        "missing_evidence_refs": missing_evidence_refs,
        "projection_selected_work_id": projection_selected_work_id,
    }
    rendered_predicate_detail_violations: list[dict[str, Any]] = []
    rendered_predicate_details_value = rendered_case.get("predicate_details")
    if isinstance(rendered_predicate_details_value, dict):
        rendered_predicate_detail_keys = {
            key for key in rendered_predicate_details_value if isinstance(key, str)
        }
        invalid_rendered_predicate_detail_keys = [
            key
            for key in rendered_predicate_details_value
            if not isinstance(key, str)
        ]
        if invalid_rendered_predicate_detail_keys:
            rendered_predicate_detail_violations.append(
                {
                    "reason": "rendered_predicate_details_invalid_keys",
                    "rendered": invalid_rendered_predicate_detail_keys,
                }
            )
        missing_rendered_predicate_detail_keys = sorted(
            set(expected_rendered_predicate_details)
            - rendered_predicate_detail_keys
        )
        unexpected_rendered_predicate_detail_keys = sorted(
            rendered_predicate_detail_keys
            - set(expected_rendered_predicate_details)
        )
        if missing_rendered_predicate_detail_keys:
            rendered_predicate_detail_violations.append(
                {
                    "reason": "rendered_predicate_details_missing_keys",
                    "expected": sorted(expected_rendered_predicate_details),
                    "missing": missing_rendered_predicate_detail_keys,
                }
            )
        if unexpected_rendered_predicate_detail_keys:
            rendered_predicate_detail_violations.append(
                {
                    "reason": "rendered_predicate_details_unexpected_keys",
                    "expected": sorted(expected_rendered_predicate_details),
                    "rendered": unexpected_rendered_predicate_detail_keys,
                }
            )
        for field_name, expected_value in expected_rendered_predicate_details.items():
            if field_name not in rendered_predicate_details_value:
                continue
            rendered_value = rendered_predicate_details_value.get(field_name)
            if rendered_value != expected_value:
                rendered_predicate_detail_violations.append(
                    {
                        "field": field_name,
                        "reason": f"rendered_predicate_details_{field_name}_mismatch",
                        "expected": expected_value,
                        "rendered": rendered_value,
                    }
                )
    elif "predicate_details" in rendered_case:
        rendered_predicate_detail_violations.append(
            {
                "field": "predicate_details",
                "reason": "rendered_predicate_details_invalid",
                "rendered": rendered_predicate_details_value,
            }
        )
    rendered_predicate_details_ok = not rendered_predicate_detail_violations
    expected_rendered_predicate_status = {
        **independent_predicate_status,
        "command_case_eligible": command_case_eligible,
        "public_architecture_witness_eligible": public_architecture_witness_eligible,
        "rendered_occurrence_refs": rendered_occurrence_refs_ok,
        "rendered_state_delta_refs": rendered_state_delta_refs_ok,
        "rendered_state_delta_summary": rendered_state_delta_summary_ok,
        "rendered_predicate_details": rendered_predicate_details_ok,
        "rendered_semantic_digest": rendered_semantic_digest_ok,
        "rendered_truth_class_authority": rendered_truth_class_authority,
        "rendered_assertion_matrix_coverage": rendered_assertion_matrix_coverage,
        "rendered_truth_class_summary": rendered_truth_class_summary_ok,
        "rendered_record_classification_summary": (
            rendered_record_classification_summary_ok
        ),
        "rendered_root_binding": rendered_root_binding_ok,
        "rendered_eligibility_flags": rendered_eligibility_flags_ok,
    }
    allowed_later_rendered_predicate_status_ids = {
        "rendered_predicate_status",
        "rendered_verification_summary",
        "rendered_safe_to_show_boundary",
        "rendered_guidance_boundary",
        "rendered_late_predicate_status",
    }
    allowed_rendered_predicate_status_ids = (
        set(expected_rendered_predicate_status)
        | allowed_later_rendered_predicate_status_ids
    )
    rendered_predicate_status_violations: list[dict[str, Any]] = []
    for status_field in ("predicate_status", "verification_predicate_status"):
        rendered_predicates = rendered_case.get(status_field)
        if not isinstance(rendered_predicates, dict):
            continue
        if status_field == "predicate_status":
            expected_predicate_keys = sorted(
                key for key in claimed_predicates if isinstance(key, str)
            )
            rendered_predicate_keys = {
                key for key in rendered_predicates if isinstance(key, str)
            }
            missing_predicate_keys = sorted(
                set(expected_predicate_keys) - rendered_predicate_keys
            )
            if missing_predicate_keys:
                rendered_predicate_status_violations.append(
                    {
                        "status_field": status_field,
                        "reason": "rendered_predicate_status_missing_predicates",
                        "expected": expected_predicate_keys,
                        "missing": missing_predicate_keys,
                    }
                )
        for predicate_id, rendered_value in rendered_predicates.items():
            if predicate_id not in allowed_rendered_predicate_status_ids:
                rendered_predicate_status_violations.append(
                    {
                        "status_field": status_field,
                        "predicate_id": predicate_id,
                        "reason": "rendered_predicate_status_unexpected_predicate",
                        "rendered": rendered_value,
                    }
                )
                continue
            if predicate_id not in expected_rendered_predicate_status:
                continue
            expected_value = expected_rendered_predicate_status[predicate_id]
            if rendered_value != expected_value:
                rendered_predicate_status_violations.append(
                    {
                        "status_field": status_field,
                        "predicate_id": predicate_id,
                        "expected": expected_value,
                        "rendered": rendered_value,
                    }
                )
    rendered_predicate_status_base_ok = not rendered_predicate_status_violations
    for status_field in ("predicate_status", "verification_predicate_status"):
        rendered_predicates = rendered_case.get(status_field)
        if not isinstance(rendered_predicates, dict):
            continue
        if "rendered_predicate_status" not in rendered_predicates:
            continue
        rendered_value = rendered_predicates.get("rendered_predicate_status")
        if rendered_value != rendered_predicate_status_base_ok:
            rendered_predicate_status_violations.append(
                {
                    "status_field": status_field,
                    "predicate_id": "rendered_predicate_status",
                    "reason": "rendered_predicate_status_predicate_mismatch",
                    "expected": rendered_predicate_status_base_ok,
                    "rendered": rendered_value,
                }
            )
    rendered_predicate_status_ok = not rendered_predicate_status_violations
    if not rendered_occurrence_refs_ok:
        failed_predicates.append("rendered_occurrence_refs")
    if not rendered_state_delta_refs_ok:
        failed_predicates.append("rendered_state_delta_refs")
    if not rendered_state_delta_summary_ok:
        failed_predicates.append("rendered_state_delta_summary")
    if not rendered_predicate_details_ok:
        failed_predicates.append("rendered_predicate_details")
    if not rendered_semantic_digest_ok:
        failed_predicates.append("rendered_semantic_digest")
    if not rendered_predicate_status_ok:
        failed_predicates.append("rendered_predicate_status")
    if not rendered_truth_class_authority:
        failed_predicates.append("rendered_truth_class_authority")
    if not rendered_assertion_matrix_coverage:
        failed_predicates.append("rendered_assertion_matrix_coverage")
    if not rendered_truth_class_summary_ok:
        failed_predicates.append("rendered_truth_class_summary")
    if not rendered_record_classification_summary_ok:
        failed_predicates.append("rendered_record_classification_summary")
    if not rendered_root_binding_ok:
        failed_predicates.append("rendered_root_binding")
    if not rendered_eligibility_flags_ok:
        failed_predicates.append("rendered_eligibility_flags")
    if (
        rendered_case.get("public_architecture_witness_eligible") is True
        and not public_architecture_witness_eligible
    ):
        failed_predicates.append("rendered_public_witness_eligible")
    if (
        isinstance(rendered_witness, dict)
        and isinstance(rendered_witness.get("compile_summary"), dict)
        and rendered_witness["compile_summary"].get(
            "public_architecture_witness_eligible"
        )
        is True
        and not public_architecture_witness_eligible
    ):
        failed_predicates.append("rendered_compile_summary_witness_eligible")
    core_failed_predicates = sorted(set(failed_predicates))
    expected_rendered_status = (
        PASS if command_case_eligible and not core_failed_predicates else "blocked"
        if core_failed_predicates
        else "partial"
    )
    expected_rendered_verification_status = (
        PASS if not core_failed_predicates else "blocked"
    )
    expected_rendered_public_witness_status = (
        PASS
        if public_architecture_witness_eligible
        else "verification_blocked"
        if core_failed_predicates
        else "projection_not_eligible"
    )
    expected_rendered_verification_summary = {
        "status": expected_rendered_status,
        "verification_status": expected_rendered_verification_status,
        "verification_failed_predicates": core_failed_predicates,
        "public_witness_status": expected_rendered_public_witness_status,
    }
    rendered_verification_summary_violations: list[dict[str, Any]] = []
    for field_name in ("status", "verification_status", "public_witness_status"):
        if field_name not in rendered_case:
            continue
        rendered_value = rendered_case.get(field_name)
        expected_value = expected_rendered_verification_summary[field_name]
        if rendered_value != expected_value:
            rendered_verification_summary_violations.append(
                {
                    "field": field_name,
                    "reason": f"rendered_{field_name}_mismatch",
                    "expected": expected_value,
                    "rendered": rendered_value,
                }
            )
    rendered_failed_predicates_value = rendered_case.get(
        "verification_failed_predicates"
    )
    if isinstance(rendered_failed_predicates_value, list):
        invalid_rendered_failed_predicates = [
            item
            for item in rendered_failed_predicates_value
            if not isinstance(item, str)
        ]
        rendered_failed_predicates = sorted(
            set(
                item
                for item in rendered_failed_predicates_value
                if isinstance(item, str)
            )
        )
        if invalid_rendered_failed_predicates:
            rendered_verification_summary_violations.append(
                {
                    "field": "verification_failed_predicates",
                    "reason": "rendered_verification_failed_predicates_invalid",
                    "rendered": invalid_rendered_failed_predicates,
                }
            )
        if rendered_failed_predicates != core_failed_predicates:
            rendered_verification_summary_violations.append(
                {
                    "field": "verification_failed_predicates",
                    "reason": "rendered_verification_failed_predicates_mismatch",
                    "expected": core_failed_predicates,
                    "rendered": rendered_failed_predicates,
                }
            )
    elif "verification_failed_predicates" in rendered_case:
        rendered_verification_summary_violations.append(
            {
                "field": "verification_failed_predicates",
                "reason": "rendered_verification_failed_predicates_invalid",
                "rendered": rendered_failed_predicates_value,
            }
        )
    rendered_verification_summary_base_ok = (
        not rendered_verification_summary_violations
    )
    for status_field in ("predicate_status", "verification_predicate_status"):
        rendered_predicates = rendered_case.get(status_field)
        if not isinstance(rendered_predicates, dict):
            continue
        if "rendered_verification_summary" not in rendered_predicates:
            continue
        rendered_value = rendered_predicates.get("rendered_verification_summary")
        if rendered_value is not rendered_verification_summary_base_ok:
            rendered_verification_summary_violations.append(
                {
                    "status_field": status_field,
                    "predicate_id": "rendered_verification_summary",
                    "reason": "rendered_verification_summary_predicate_mismatch",
                    "expected": rendered_verification_summary_base_ok,
                    "rendered": rendered_value,
                }
            )
    rendered_verification_summary_ok = (
        not rendered_verification_summary_violations
    )
    if not rendered_verification_summary_ok:
        failed_predicates.append("rendered_verification_summary")
    expected_rendered_safe_to_show = {
        "receipt_ref_visible": True,
        "predicate_status_visible": True,
        "full_receipt_body_omitted": True,
        "source_files_mutated": False,
        "provider_calls_authorized": False,
        "release_authorized": False,
        "proof_correctness_claim": False,
    }
    rendered_safe_to_show_boundary_violations: list[dict[str, Any]] = []
    rendered_safe_to_show_value = rendered_case.get("safe_to_show")
    if isinstance(rendered_safe_to_show_value, dict):
        rendered_safe_to_show = rendered_safe_to_show_value
        rendered_safe_to_show_keys = {
            key for key in rendered_safe_to_show if isinstance(key, str)
        }
        invalid_rendered_safe_to_show_keys = [
            key for key in rendered_safe_to_show if not isinstance(key, str)
        ]
        if invalid_rendered_safe_to_show_keys:
            rendered_safe_to_show_boundary_violations.append(
                {
                    "reason": "rendered_safe_to_show_invalid_keys",
                    "rendered": invalid_rendered_safe_to_show_keys,
                }
            )
        missing_rendered_safe_to_show_keys = sorted(
            set(expected_rendered_safe_to_show) - rendered_safe_to_show_keys
        )
        unexpected_rendered_safe_to_show_keys = sorted(
            rendered_safe_to_show_keys - set(expected_rendered_safe_to_show)
        )
        if missing_rendered_safe_to_show_keys:
            rendered_safe_to_show_boundary_violations.append(
                {
                    "reason": "rendered_safe_to_show_missing_keys",
                    "expected": sorted(expected_rendered_safe_to_show),
                    "missing": missing_rendered_safe_to_show_keys,
                }
            )
        if unexpected_rendered_safe_to_show_keys:
            rendered_safe_to_show_boundary_violations.append(
                {
                    "reason": "rendered_safe_to_show_unexpected_keys",
                    "expected": sorted(expected_rendered_safe_to_show),
                    "rendered": unexpected_rendered_safe_to_show_keys,
                }
            )
        for field_name, expected_value in expected_rendered_safe_to_show.items():
            if field_name not in rendered_safe_to_show:
                continue
            rendered_value = rendered_safe_to_show.get(field_name)
            if rendered_value is not expected_value:
                rendered_safe_to_show_boundary_violations.append(
                    {
                        "field": field_name,
                        "reason": f"rendered_safe_to_show_{field_name}_mismatch",
                        "expected": expected_value,
                        "rendered": rendered_value,
                    }
                )
    elif "safe_to_show" in rendered_case:
        rendered_safe_to_show_boundary_violations.append(
            {
                "field": "safe_to_show",
                "reason": "rendered_safe_to_show_invalid",
                "rendered": rendered_safe_to_show_value,
            }
        )
    rendered_safe_to_show_boundary_ok = (
        not rendered_safe_to_show_boundary_violations
    )
    if not rendered_safe_to_show_boundary_ok:
        failed_predicates.append("rendered_safe_to_show_boundary")
    expected_rendered_guidance_boundary = {
        "schema_version": "microcosm_command_reference_execution_case_card_v1",
        "anti_claim": (
            case.get("anti_claim")
            if isinstance(case.get("anti_claim"), str) and case.get("anti_claim")
            else "The reference execution case is a command-root occurrence assay, "
            "not a release, hosting, or correctness claim."
        ),
        "reader_action": (
            "Use this compact card to decide whether the command-root occurrence "
            "case is eligible before treating any architecture projection as a "
            "public witness."
        ),
        "verification_ref": "architecture_kernel.verify_reference_execution_case",
    }
    rendered_guidance_boundary_violations: list[dict[str, Any]] = []
    for field_name, expected_value in expected_rendered_guidance_boundary.items():
        if field_name not in rendered_case:
            continue
        rendered_value = rendered_case.get(field_name)
        if rendered_value != expected_value:
            rendered_guidance_boundary_violations.append(
                {
                    "field": field_name,
                    "reason": f"rendered_{field_name}_mismatch",
                    "expected": expected_value,
                    "rendered": rendered_value,
                }
            )
    rendered_guidance_boundary_ok = not rendered_guidance_boundary_violations
    if not rendered_guidance_boundary_ok:
        failed_predicates.append("rendered_guidance_boundary")
    expected_late_rendered_predicate_status = {
        "rendered_verification_summary": rendered_verification_summary_ok,
        "rendered_safe_to_show_boundary": rendered_safe_to_show_boundary_ok,
        "rendered_guidance_boundary": rendered_guidance_boundary_ok,
    }
    rendered_late_predicate_status_violations: list[dict[str, Any]] = []
    for status_field in ("predicate_status", "verification_predicate_status"):
        rendered_predicates = rendered_case.get(status_field)
        if not isinstance(rendered_predicates, dict):
            continue
        for predicate_id, expected_value in (
            expected_late_rendered_predicate_status.items()
        ):
            if predicate_id not in rendered_predicates:
                continue
            rendered_value = rendered_predicates.get(predicate_id)
            if rendered_value != expected_value:
                rendered_late_predicate_status_violations.append(
                    {
                        "status_field": status_field,
                        "predicate_id": predicate_id,
                        "expected": expected_value,
                        "rendered": rendered_value,
                    }
                )
    rendered_late_predicate_status_base_ok = (
        not rendered_late_predicate_status_violations
    )
    for status_field in ("predicate_status", "verification_predicate_status"):
        rendered_predicates = rendered_case.get(status_field)
        if not isinstance(rendered_predicates, dict):
            continue
        if "rendered_late_predicate_status" not in rendered_predicates:
            continue
        rendered_value = rendered_predicates.get("rendered_late_predicate_status")
        if rendered_value != rendered_late_predicate_status_base_ok:
            rendered_late_predicate_status_violations.append(
                {
                    "status_field": status_field,
                    "predicate_id": "rendered_late_predicate_status",
                    "reason": "rendered_late_predicate_status_predicate_mismatch",
                    "expected": rendered_late_predicate_status_base_ok,
                    "rendered": rendered_value,
                }
            )
    rendered_late_predicate_status_ok = (
        not rendered_late_predicate_status_violations
    )
    if not rendered_late_predicate_status_ok:
        failed_predicates.append("rendered_late_predicate_status")
    failed_predicates = sorted(set(failed_predicates))
    return {
        **_base(project, "microcosm_reference_execution_case_verification_v1"),
        "status": PASS if not failed_predicates else "blocked",
        "case_id": case.get("case_id"),
        "route_id": route_id or None,
        "root_work_id": work_id or None,
        "expected_semantic_digest": expected_semantic_digest,
        "observed_semantic_digest": case.get("semantic_digest"),
        "predicate_status": {
            **independent_predicate_status,
            "command_case_eligible": command_case_eligible,
            "public_architecture_witness_eligible": (
                public_architecture_witness_eligible
            ),
            "rendered_occurrence_refs": rendered_occurrence_refs_ok,
            "rendered_state_delta_refs": rendered_state_delta_refs_ok,
            "rendered_state_delta_summary": rendered_state_delta_summary_ok,
            "rendered_predicate_details": rendered_predicate_details_ok,
            "rendered_predicate_status": rendered_predicate_status_ok,
            "rendered_semantic_digest": rendered_semantic_digest_ok,
            "rendered_truth_class_authority": rendered_truth_class_authority,
            "rendered_assertion_matrix_coverage": (
                rendered_assertion_matrix_coverage
            ),
            "rendered_truth_class_summary": rendered_truth_class_summary_ok,
            "rendered_record_classification_summary": (
                rendered_record_classification_summary_ok
            ),
            "rendered_root_binding": rendered_root_binding_ok,
            "rendered_eligibility_flags": rendered_eligibility_flags_ok,
            "rendered_verification_summary": rendered_verification_summary_ok,
            "rendered_safe_to_show_boundary": rendered_safe_to_show_boundary_ok,
            "rendered_guidance_boundary": rendered_guidance_boundary_ok,
            "rendered_late_predicate_status": rendered_late_predicate_status_ok,
        },
        "failed_predicates": failed_predicates,
        "predicate_details": {
            "missing_event_ids": missing_event_ids,
            "missing_evidence_refs": missing_evidence_refs,
            "projection_selected_work_id": projection_selected_work_id,
            "truth_class_violations": truth_class_violations,
            "case_occurrence_refs": case_occurrence_refs,
            "case_occurrence_witness_refs": case_occurrence_witness_refs,
            "missing_occurrence_refs": missing_occurrence_refs,
            "unexpected_case_occurrence_refs": unexpected_case_occurrence_refs,
            "missing_occurrence_witness_refs": missing_occurrence_witness_refs,
            "unexpected_occurrence_witness_refs": unexpected_occurrence_witness_refs,
            "ambient_occurrence_refs_in_case": ambient_occurrence_refs_in_case,
            "replay_equivalence_basis": replay_equivalence_basis,
            "delta_has_root_or_descendant": delta_has_root_or_descendant,
            "missing_delta_work_ids": missing_delta_work_ids,
            "missing_delta_event_ids": missing_delta_event_ids,
            "missing_delta_evidence_refs": missing_delta_evidence_refs,
            "unexpected_delta_work_ids": unexpected_delta_work_ids,
            "unexpected_delta_event_ids": unexpected_delta_event_ids,
            "unexpected_delta_evidence_refs": unexpected_delta_evidence_refs,
            "state_delta_scope_violations": state_delta_scope_violations,
            "expected_record_classification_counts": (
                expected_record_classification_counts
            ),
            "rendered_record_classification_counts": (
                rendered_record_classification_counts
            ),
            "record_classification_matrix_violations": (
                record_classification_matrix_violations
            ),
            "expected_assertion_predicates": list(
                REFERENCE_CASE_ASSERTION_PREDICATES
            ),
            "assertion_matrix_predicates": assertion_predicate_ids,
            "assertion_matrix_coverage_violations": (
                assertion_matrix_coverage_violations
            ),
            "expected_rendered_state_delta_refs": (
                expected_rendered_state_delta_refs
            ),
            "rendered_state_delta_refs": rendered_state_delta_refs,
            "missing_rendered_state_delta_refs": (
                missing_rendered_state_delta_refs
            ),
            "unexpected_rendered_state_delta_refs": (
                unexpected_rendered_state_delta_refs
            ),
            "rendered_state_delta_ref_violations": (
                rendered_state_delta_ref_violations
            ),
            "expected_rendered_state_delta_summary": {
                "state_delta_ref_count": expected_state_delta_ref_count,
                "state_delta_refs_verified": rendered_state_delta_refs_ok,
                "state_delta_refs_ref": expected_state_delta_refs_ref,
                "state_delta_scope_verified": state_delta_scope,
                "state_delta_scope_ref": expected_state_delta_scope_ref,
            },
            "rendered_state_delta_summary_violations": (
                rendered_state_delta_summary_violations
            ),
            "missing_rendered_occurrence_refs": missing_rendered_occurrence_refs,
            "unexpected_rendered_occurrence_refs": unexpected_rendered_occurrence_refs,
            "expected_rendered_predicate_details": (
                expected_rendered_predicate_details
            ),
            "rendered_predicate_detail_violations": (
                rendered_predicate_detail_violations
            ),
            "rendered_predicate_status_violations": (
                rendered_predicate_status_violations
            ),
            "rendered_semantic_digest": rendered_semantic_digest,
            "rendered_truth_class_violations": rendered_truth_class_violations,
            "rendered_assertion_matrix_coverage_violations": (
                rendered_assertion_matrix_coverage_violations
            ),
            "expected_truth_classes": expected_truth_classes,
            "expected_truth_class_counts": expected_truth_class_counts,
            "rendered_truth_class_summary_violations": (
                rendered_truth_class_summary_violations
            ),
            "expected_rendered_record_classification_summary": (
                expected_rendered_record_classification_summary
            ),
            "rendered_record_classification_summary_violations": (
                rendered_record_classification_summary_violations
            ),
            "expected_rendered_root_binding": {
                **expected_rendered_root_fields,
                "evidence_ref": expected_evidence_ref or None,
                "assertion_matrix_ref": expected_assertion_matrix_ref,
                "record_classification_matrix_ref": (
                    expected_record_classification_matrix_ref
                ),
            },
            "rendered_root_binding_violations": rendered_root_binding_violations,
            "expected_rendered_eligibility_flags": (
                expected_rendered_eligibility_flags
            ),
            "rendered_eligibility_flag_violations": (
                rendered_eligibility_flag_violations
            ),
            "expected_rendered_verification_summary": (
                expected_rendered_verification_summary
            ),
            "rendered_verification_summary_violations": (
                rendered_verification_summary_violations
            ),
            "core_failed_predicates_before_rendered_verification_summary": (
                core_failed_predicates
            ),
            "expected_rendered_safe_to_show": expected_rendered_safe_to_show,
            "rendered_safe_to_show_boundary_violations": (
                rendered_safe_to_show_boundary_violations
            ),
            "expected_rendered_guidance_boundary": (
                expected_rendered_guidance_boundary
            ),
            "rendered_guidance_boundary_violations": (
                rendered_guidance_boundary_violations
            ),
            "expected_late_rendered_predicate_status": (
                expected_late_rendered_predicate_status
            ),
            "rendered_late_predicate_status_violations": (
                rendered_late_predicate_status_violations
            ),
            "allowed_occurrence_refs": sorted(allowed_occurrence_refs),
        },
        "anti_claim": (
            "This verifier reconstructs command-case integrity from raw local "
            "records. It does not prove project correctness, release readiness, "
            "or whole-system correctness."
        ),
    }


def _dedupe_strings(items: list[Any]) -> list[str]:
    """Stringify and de-duplicate a list, preserving first-seen order.

    - Teleology: keep evidence-ref lists in explanations stable and free of repeats so drilldown pointers stay clean.
    - Guarantee: returns the order-preserving unique non-empty string forms of `items`; falsy/empty values are dropped.
    - Fails: never raises; non-string items are coerced via `str(item or "")`.
    - When-needed: inspect when an explanation's evidence_refs contain duplicate or empty entries.
    - Non-goal: does not verify that the referenced files exist.
    """
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item or "")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _dedupe_event_refs(items: list[Any]) -> list[dict[str, Any]]:
    """De-duplicate event-ref dicts by event_id, preserving first-seen order.

    - Teleology: merge event refs from the stream and from work rows into one repeat-free causal-event list for the explanation proof.
    - Guarantee: returns order-preserving unique {event_id, span, status} dicts keyed by a non-empty `event_id`; non-dict items and blank ids are dropped.
    - Fails: never raises; malformed items are skipped.
    - When-needed: inspect when causal_event_refs double-count an event or drop expected ids.
    - Non-goal: does not validate that referenced events exist in the stream.
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or "")
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        out.append(
            {
                "event_id": event_id,
                "span": item.get("span"),
                "status": item.get("status"),
            }
        )
    return out


def _public_work_transaction_is_closed(row: dict[str, Any]) -> bool:
    """Decide whether a work row is a closed, source-safe public transaction.

    - Teleology: the no-source-mutation closedness predicate that lets the explanation pick a trustworthy representative work transaction.
    - Guarantee: returns True only when `work_id` is a str AND `status` is in {closed, pass} AND `source_files_mutated` is not True.
    - Fails: never raises; missing/odd fields simply yield False.
    - When-needed: inspect when a route explanation selects an unexpected work item as its representative.
    - Reads: the in-memory `row` only; reads no file.
    - Non-goal: does not verify the transaction's evidence on disk or authorize source mutation.
    """
    return (
        isinstance(row.get("work_id"), str)
        and row.get("status") in {"closed", PASS}
        and row.get("source_files_mutated") is not True
    )


def _select_public_work_transaction(work_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the representative work transaction for an explanation.

    - Teleology: choose one work row to summarize in the causal-chain proof, preferring a closed source-safe transaction.
    - Guarantee: returns the first row passing `_public_work_transaction_is_closed`; else the last row; `{}` when `work_items` is empty.
    - Fails: never raises; empty input -> {}.
    - When-needed: inspect when selected_work_id/selected_work_status looks wrong in an explanation.
    - Non-goal: does not validate the selected transaction's on-disk evidence or correctness.
    """
    return next(
        (row for row in work_items if _public_work_transaction_is_closed(row)),
        work_items[-1] if work_items else {},
    )


def load_kernel_manifest(root: str | Path | None = None) -> dict[str, Any]:
    """Load the architecture-kernel manifest, falling back to the baked default.

    - Teleology: source-custody reader for the kernel contract (primitives, posture, anti-claim) that every architecture projection is built from.
    - Guarantee: returns the on-disk `core/architecture_kernel.json` object when present; otherwise a copy of the in-module `_DEFAULT_KERNEL`; always stamps `primitive_count` from the dict primitives.
    - Fails: surfaces strict-parse errors on a present-but-malformed manifest; absent file -> default copy (no raise).
    - When-needed: inspect when `primitive_count`, posture, or anti-claim in a projection disagrees with the source manifest.
    - Reads: `<root or public_root()>/core/architecture_kernel.json`.
    - Escalates-to: the source file `core/architecture_kernel.json` and `_DEFAULT_KERNEL` for the canonical contract.
    - Non-goal: does not authorize source mutation, release, or treat the manifest as production-readiness proof.
    """
    root_path = Path(root).resolve(strict=False) if root is not None else public_root()
    manifest = read_json_if_exists(root_path / "core/architecture_kernel.json")
    if not manifest:
        manifest = dict(_DEFAULT_KERNEL)
    primitives = manifest.get("primitives", [])
    if isinstance(primitives, list):
        manifest["primitive_count"] = len([row for row in primitives if isinstance(row, dict)])
    return manifest


def pattern_surface_contract(root: str | Path | None = None) -> dict[str, Any]:
    """Return the public pattern-surface contract (state/evidence/binding refs).

    - Teleology: expose the public pattern surface (state_ref, evidence_ref, binding_standard_refs, assimilation policy) that routes resolve pattern_refs against.
    - Guarantee: returns a copy of the manifest's `pattern_surface` dict when present and non-empty; otherwise a copy of `_PATTERN_SURFACE_CONTRACT`.
    - Fails: surfaces strict-parse errors from the underlying manifest read; otherwise no raise.
    - When-needed: inspect when pattern bindings resolve against an unexpected state/evidence ref.
    - Reads: the kernel manifest via `load_kernel_manifest(root)`.
    - Non-goal: does not promote doctrine, authorize source-body export, or include private source bodies (`private_source_bodies_included` is False).
    """
    surface = load_kernel_manifest(root).get("pattern_surface")
    if isinstance(surface, dict) and surface:
        return dict(surface)
    return dict(_PATTERN_SURFACE_CONTRACT)


def load_standard_pressure_surface(root: str | Path | None = None) -> dict[str, Any]:
    """Load the public standard-pressure surface, falling back to the default.

    - Teleology: source-custody reader for the public-safe standard-pressure rows (constraints over local state) consumed by graph/explanation builders.
    - Guarantee: returns the on-disk `core/public_standard_pressure.json` object when present; otherwise a copy of `_DEFAULT_STANDARD_PRESSURE_SURFACE`.
    - Fails: surfaces strict-parse errors on a present-but-malformed surface; absent file -> default copy (no raise).
    - When-needed: inspect when standard-pressure rows in a projection disagree with the source surface.
    - Reads: `<root or public_root()>/core/public_standard_pressure.json` (`_STANDARD_PRESSURE_REF`).
    - Escalates-to: the source file `core/public_standard_pressure.json` and `_DEFAULT_STANDARD_PRESSURE_SURFACE`.
    - Non-goal: does not promote global doctrine, authorize source mutation, or prove release readiness (rows are public-safe projections, not doctrine authority).
    """
    root_path = Path(root).resolve(strict=False) if root is not None else public_root()
    payload = read_json_if_exists(root_path / _STANDARD_PRESSURE_REF)
    if payload:
        return payload
    return dict(_DEFAULT_STANDARD_PRESSURE_SURFACE)


def standard_pressure_contract(root: str | Path | None = None) -> dict[str, Any]:
    """Project the standard-pressure surface into its compact contract header.

    - Teleology: give consumers the surface identity (surface_id, state_ref, source_ref, posture, row_count) without the full row bodies.
    - Guarantee: returns the contract dict derived from the loaded surface, with `row_count` counting dict rows and `private_source_bodies_included` normalized to a bool.
    - Fails: surfaces strict-parse errors from the underlying surface load; otherwise no raise.
    - When-needed: inspect when a projection's standard_pressure header (counts/refs) looks wrong.
    - Reads: the standard-pressure surface via `load_standard_pressure_surface(root)`.
    - Non-goal: does not include the rows themselves, promote doctrine, or authorize release.
    """
    return _standard_pressure_contract_from_surface(load_standard_pressure_surface(root))


def _standard_pressure_contract_from_surface(surface: dict[str, Any]) -> dict[str, Any]:
    """Build the compact standard-pressure contract header from a surface dict.

    - Teleology: pure projection from an already-loaded surface to its identity header, so callers holding the surface avoid a re-read.
    - Guarantee: returns {surface_id, state_ref, source_ref, authority_posture, private_source_bodies_included (bool), row_count}; missing keys fall back to defaults and `row_count` counts dict rows (0 when `rows` is not a list).
    - Fails: never raises; absent/odd fields degrade to documented defaults.
    - When-needed: inspect when a header derived from an in-hand surface disagrees with the surface contents.
    - Non-goal: does not include row bodies, promote doctrine, or authorize release.
    """
    rows = surface.get("rows", [])
    row_count = len([row for row in rows if isinstance(row, dict)]) if isinstance(rows, list) else 0
    return {
        "surface_id": surface.get("surface_id", "public_microcosm_standard_pressure"),
        "state_ref": surface.get("state_ref", ".microcosm/architecture.json::standard_pressure_surface"),
        "source_ref": surface.get("source_ref", _STANDARD_PRESSURE_REF),
        "authority_posture": surface.get(
            "authority_posture",
            "public_safe_standard_pressure_projection_not_doctrine_authority",
        ),
        "private_source_bodies_included": surface.get("private_source_bodies_included") is True,
        "row_count": row_count,
    }


def standard_pressure_rows(root: str | Path | None = None) -> list[dict[str, Any]]:
    """Return the public standard-pressure rows from the loaded surface.

    - Teleology: expose the row bodies (standard_id, claim, route_refs, authority_boundary) that constrain routes and seed graph nodes/edges.
    - Guarantee: returns the list of dict rows from the loaded surface; non-dict entries and a non-list `rows` field yield [].
    - Fails: surfaces strict-parse errors from the underlying surface load; otherwise no raise.
    - When-needed: inspect when route constraints or graph standard-pressure nodes are missing rows.
    - Reads: the standard-pressure surface via `load_standard_pressure_surface(root)`.
    - Non-goal: does not promote rows to global doctrine or authorize release.
    """
    return _standard_pressure_rows_from_surface(load_standard_pressure_surface(root))


def _standard_pressure_rows_from_surface(surface: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the dict rows from an already-loaded standard-pressure surface.

    - Teleology: pure row extractor so callers holding a surface reuse it without a re-read.
    - Guarantee: returns the dict-only entries of `surface["rows"]`; non-dict entries and a non-list `rows` field yield [].
    - Fails: never raises.
    - When-needed: inspect when rows derived from an in-hand surface look filtered or empty.
    - Non-goal: does not validate row schema or authorize doctrine promotion.
    """
    rows = surface.get("rows", [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _route_pattern_refs(route: dict[str, Any]) -> list[str]:
    """Resolve the pattern ids a route depends on, with a per-route fallback.

    - Teleology: source the pattern_refs a route resolves against, falling back to the built-in `_PATTERN_BY_ROUTE` map when the route omits them.
    - Guarantee: returns the route's own `pattern_refs` as non-empty strings when it is a list; else the single fallback for the `route_id` (or [] when none).
    - Fails: never raises; missing/odd fields degrade to the fallback or [].
    - When-needed: inspect when a route's pattern bindings resolve to unexpected ids.
    - Reads: the in-memory `route` and the module `_PATTERN_BY_ROUTE` map.
    - Non-goal: does not verify the pattern ids exist in `.microcosm/patterns.json`.
    """
    refs = route.get("pattern_refs", [])
    if isinstance(refs, list):
        return [str(ref) for ref in refs if ref is not None and str(ref)]
    fallback = _PATTERN_BY_ROUTE.get(str(route.get("route_id") or ""))
    return [fallback] if fallback else []


def _pattern_rows_by_id(pattern_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index pattern rows by pattern_id for O(1) binding lookup.

    - Teleology: turn the `.microcosm/patterns.json` row list into an id-keyed map so pattern bindings resolve quickly.
    - Guarantee: returns {pattern_id -> row} for every dict row carrying a truthy `pattern_id`; non-list `patterns` -> {}.
    - Fails: never raises; rows without an id are dropped.
    - When-needed: inspect when a pattern binding reports resolved=False despite the pattern appearing in state.
    - Reads: the in-memory `pattern_payload` (already-read patterns state).
    - Non-goal: does not read the patterns file itself or validate pattern schema.
    """
    rows = pattern_payload.get("patterns", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("pattern_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("pattern_id")
    }


def _pattern_bindings(pattern_payload: dict[str, Any], pattern_refs: list[str]) -> list[dict[str, Any]]:
    """Resolve route pattern_refs into binding rows against the pattern surface.

    - Teleology: produce the per-ref binding rows (with resolved flag, state/evidence refs, governing standard refs) that the explanation reports.
    - Guarantee: returns one binding per id in `pattern_refs`, each carrying `resolved` (True iff the id is present in `pattern_payload`), the resolved `pattern` row or None, surface `state_ref::id`, `evidence_ref`, `standard_refs`, and a public authority_boundary.
    - Fails: surfaces strict-parse errors only via the `pattern_surface_contract()` manifest read; otherwise no raise.
    - When-needed: inspect when an explanation's pattern_bindings show unexpected resolved flags or refs.
    - Reads: in-memory `pattern_payload`; pattern surface via `pattern_surface_contract()`.
    - Non-goal: does not promote patterns to doctrine or authorize source mutation; bindings are public observations only.
    """
    rows_by_id = _pattern_rows_by_id(pattern_payload)
    surface = pattern_surface_contract()
    standard_refs = surface.get("binding_standard_refs", [])
    standard_refs = standard_refs if isinstance(standard_refs, list) else []
    bindings: list[dict[str, Any]] = []
    for pattern_id in pattern_refs:
        row = rows_by_id.get(pattern_id)
        bindings.append(
            {
                "pattern_id": pattern_id,
                "resolved": row is not None,
                "pattern": row,
                "state_ref": f"{surface.get('state_ref', '.microcosm/patterns.json')}::{pattern_id}",
                "evidence_ref": surface.get("evidence_ref", ".microcosm/evidence/patterns.json"),
                "standard_refs": standard_refs,
                "authority_boundary": "public_pattern_observation_not_doctrine_promotion",
            }
        )
    return bindings


def standard_pressure_refs_for_route(
    route: dict[str, Any], *, rows: list[dict[str, Any]] | None = None
) -> list[str]:
    """Select which standard-pressure ids constrain a given route.

    - Teleology: decide the standard_ids that apply to a route, honoring an explicit per-route override before the surface's wildcard/route matching.
    - Guarantee: returns the route's own `standard_pressure_refs` (as strings) when non-empty; else the standard_ids of rows whose `route_refs` is ["*"] or contains the route id.
    - Fails: surfaces strict-parse errors only when `rows` is None and it must load the surface; otherwise no raise.
    - When-needed: inspect when a route is constrained by too many or too few standards.
    - Reads: in-memory `route`; standard rows via `standard_pressure_rows()` when `rows` is not supplied.
    - Non-goal: does not validate the standard_ids resolve to rows or authorize doctrine promotion.
    """
    route_id = str(route.get("route_id") or route.get("row_id") or "")
    refs = route.get("standard_pressure_refs", [])
    if isinstance(refs, list) and refs:
        return [str(ref) for ref in refs if ref is not None and str(ref)]
    selected: list[str] = []
    source_rows = rows if rows is not None else standard_pressure_rows()
    for row in source_rows:
        row_refs = row.get("route_refs", [])
        if row_refs == ["*"] or route_id in row_refs:
            standard_id = row.get("standard_id")
            if standard_id:
                selected.append(str(standard_id))
    return selected


def _standard_pressure_bindings(
    route: dict[str, Any],
    *,
    rows: list[dict[str, Any]] | None = None,
    contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Resolve a route's standard-pressure refs into binding rows.

    - Teleology: produce the per-standard binding rows (resolved flag, row, state/source refs) the explanation reports as constraints.
    - Guarantee: returns one binding per id from `standard_pressure_refs_for_route`, each with `resolved` (True iff the id is present in `rows`), the `standard` row or None, `state_ref` `<contract state_ref>::id`, the contract `source_ref`, and a public authority_boundary.
    - Fails: surfaces strict-parse errors only when it must load rows/contract (args None); otherwise no raise.
    - When-needed: inspect when an explanation's standard_bindings show wrong resolved flags or refs.
    - Reads: in-memory `route`; standard rows via `standard_pressure_rows()` and header via `standard_pressure_contract()` when not supplied.
    - Non-goal: does not promote standards to global doctrine or authorize source mutation.
    """
    source_rows = rows if rows is not None else standard_pressure_rows()
    rows_by_id = {
        str(row.get("standard_id")): row
        for row in source_rows
        if row.get("standard_id")
    }
    contract = contract if contract is not None else standard_pressure_contract()
    bindings: list[dict[str, Any]] = []
    for standard_id in standard_pressure_refs_for_route(route, rows=source_rows):
        row = rows_by_id.get(standard_id)
        bindings.append(
            {
                "standard_id": standard_id,
                "resolved": row is not None,
                "standard": row,
                "state_ref": f"{contract['state_ref']}::{standard_id}",
                "source_ref": contract["source_ref"],
                "authority_boundary": "public_standard_pressure_not_global_doctrine_authority",
            }
        )
    return bindings


def work_contracts_for_route(route: dict[str, Any], work_id: str | None = None) -> dict[str, Any]:
    """Build the satisfaction/integration/residual contract shape for a route.

    - Teleology: define what a reversible project-local work run must satisfy, where its state may land, and what side effects are forbidden — the contract a work transaction is judged against.
    - Guarantee: returns a dict with `satisfaction_contract` (must_satisfy/done_when, standard refs), `integration_contract` (project-local state_targets under `.microcosm`, forbidden side effects incl. source mutation/provider calls/release), and `residual_policy`; uses `work_id` or the `<work_id>` placeholder in state targets.
    - Fails: never raises; missing route id degrades to the literal "route".
    - When-needed: inspect when an explanation's work_transaction_shape contract looks wrong for a route.
    - Reads: the in-memory `route` only; reads no file.
    - Non-goal: does not execute work, mutate source, or authorize the forbidden side effects it names; it is a contract description, not an enforcer.
    """
    route_id = str(route.get("route_id") or route.get("row_id") or "route")
    work_ref = work_id or "<work_id>"
    standard_refs = [
        "reversible_work_transaction",
        "projection_lineage_not_authority",
        "evidence_as_black_box_recorder",
        "assimilation_without_promotion",
    ]
    return {
        "satisfaction_contract": {
            "contract_id": f"satisfaction:{route_id}",
            "route_id": route_id,
            "must_satisfy": [
                "route_snapshot_present",
                "workflow_definition_ref_present",
                "workflow_execution_ref_present",
                "state_history_records_created_selected_planned",
                "source_mutation_not_authorized",
                "event_and_evidence_refs_recorded_on_run",
            ],
            "done_when": [
                "transaction_state == closed",
                "closeout.satisfaction_contract_met == true",
                "closeout.integration_contract_met == true",
            ],
            "standard_pressure_refs": standard_refs,
            "authority_boundary": "project_local_contract_not_live_task_ledger_authority",
        },
        "integration_contract": {
            "contract_id": f"integration:{route_id}",
            "route_id": route_id,
            "state_targets": [
                f"{STATE_DIR}/work_items.json::{work_ref}",
                f"{STATE_DIR}/{EVENT_STREAM}",
                f"{STATE_DIR}/{EVIDENCE_DIR}/work_create_{work_ref}.json",
                f"{STATE_DIR}/{EVIDENCE_DIR}/work_run_{work_ref}.json",
            ],
            "integration_mode": "project_local_record_only",
            "forbidden_side_effects": [
                "source_file_mutation",
                "provider_call",
                "live_task_ledger_mutation",
                "global_doctrine_promotion",
                "release_or_publication",
            ],
            "standard_pressure_refs": standard_refs,
            "authority_boundary": "local_state_integration_not_external_side_effect",
        },
        "residual_policy": {
            "residual_capture_mode": "local_next_actions_only",
            "global_backlog_mutation_authorized": False,
            "nothing_to_refine_floor": [
                "stewardship_checked",
                "next_best_lane_checked",
                "reentry_condition",
            ],
        },
    }


def _base(project: Path, schema_version: str) -> dict[str, Any]:
    """Build the shared header stamped onto every generated state payload.

    - Teleology: guarantee every generated artifact carries a consistent provenance/authority header (schema, timestamp, project id, and the release/provider/source-mutation = False ceiling).
    - Guarantee: returns a fresh dict with `schema_version`, a `created_at` UTC stamp, `project_id` (resolved name or "project"), `project_ref`="." , `state_ref`=STATE_DIR, `status`=pass, and `release_authorized`/`provider_calls_authorized`/`source_files_mutated` all False.
    - Fails: never raises; an unnameable project falls back to "project".
    - When-needed: inspect when a generated payload's header (timestamp, ids, authorization flags) looks wrong.
    - Reads: resolves `project` for its name; reads no file content; `created_at` from `receipts.utc_now`.
    - Non-goal: does not flip any authorization flag True — generated output is never source-of-truth or release authority.
    """
    return {
        "schema_version": schema_version,
        "created_at": utc_now(),
        "project_id": project.resolve(strict=False).name or "project",
        "project_ref": ".",
        "state_ref": STATE_DIR,
        "status": PASS,
        "release_authorized": False,
        "provider_calls_authorized": False,
        "source_files_mutated": False,
    }


def _iter_json_children(path: Path) -> Iterator[Path]:
    """Recursively yield every `.json` file under a directory, error-tolerantly.

    - Teleology: enumerate evidence/explanation directory contents for the state-index counts without failing on a single bad entry.
    - Guarantee: yields each regular (non-symlink) `*.json` file under `path`, recursing into non-symlink subdirectories; entries that raise OSError are skipped.
    - Fails: never raises; missing/unreadable directory or entry -> that branch is silently skipped.
    - When-needed: inspect when evidence/explanation item_counts undercount on-disk files.
    - Reads: directory entries under `path` (no file contents).
    - Non-goal: does not follow symlinks, read file bodies, or validate JSON.
    """
    if not _path_is_dir(path):
        return
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False) and entry.name.endswith(
                        ".json"
                    ):
                        yield Path(entry.path)
                    elif entry.is_dir(follow_symlinks=False):
                        yield from _iter_json_children(Path(entry.path))
                except OSError:
                    continue
    except OSError:
        return


def _count_json_children(path: Path) -> int:
    """Count `.json` files under a directory tree.

    - Teleology: supply the evidence/explanation `item_count` for the state index.
    - Guarantee: returns the number of `.json` files yielded by `_iter_json_children(path)`; missing/empty dir -> 0.
    - Fails: never raises (delegates to the error-tolerant iterator).
    - When-needed: inspect when a directory's reported item_count looks wrong.
    - Non-goal: does not read or validate the counted files.
    """
    return sum(1 for _ in _iter_json_children(path))


def build_state_index(
    project_path: str | Path,
    *,
    pattern_surface: dict[str, Any] | None = None,
    standard_pressure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate and write the project-local `.microcosm/state_index.json`.

    - Teleology: project an at-a-glance index of every project-local substrate asset (existence + json counts for evidence/explanation) under the source-mutation/release = False ceiling.
    - Guarantee: writes `<project>/.microcosm/state_index.json` and returns the same payload (base header + `asset_count`, `assets` rows with exists/refs and item_count for directory kinds, embedded pattern + standard-pressure surfaces, and an explicit authority_ceiling); GENERATED output.
    - Fails: surfaces strict-parse errors from any read state file and OSError from `write_json_atomic` if the state dir is unwritable; otherwise no raise (absent assets are reported `exists: false`).
    - When-needed: inspect when the state-index undercounts assets or shows stale existence flags.
    - Reads: project-local `.microcosm/*` asset existence; pattern/standard surfaces (args or loaders).
    - Writes: `<project>/.microcosm/state_index.json`.
    - Escalates-to: rebuild via `write_project_architecture` (its caller); source surfaces `core/architecture_kernel.json` + `core/public_standard_pressure.json`.
    - Non-goal: does not authorize release or treat the generated index as source-of-truth authority (`authority`: project_local_projection).
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    pattern_surface = (
        pattern_surface if pattern_surface is not None else pattern_surface_contract()
    )
    standard_pressure = (
        standard_pressure
        if standard_pressure is not None
        else standard_pressure_contract()
    )
    assets = [
        ("project", "project_manifest.json", "project root manifest"),
        ("architecture", "architecture.json", "public architecture kernel projection"),
        ("state_index", "state_index.json", "project-local substrate asset index"),
        ("graph", "graph.json", "asset graph and lineage edges"),
        ("catalog", "catalog.json", "file role catalog"),
        ("pattern", "patterns.json", "repo-shape pattern observations"),
        ("route", "routes.json", "route candidates"),
        ("work", "work_items.json", "work transaction records"),
        ("truth_readiness", TRUTH_READINESS_STATE, "truth/readiness surface"),
        ("event", EVENT_STREAM, "runtime event stream"),
        ("evidence", EVIDENCE_DIR, "receipt drilldown directory"),
        ("explanation", EXPLANATION_DIR, "route explanation directory"),
    ]
    rows: list[dict[str, Any]] = []
    for kind, rel, description in assets:
        path = state / rel
        if kind in {"evidence", "explanation"}:
            exists = _path_is_dir(path)
            count = _count_json_children(path) if exists else 0
        else:
            count = None
            exists = _path_is_file(path)
        row: dict[str, Any] = {
            "asset_id": kind,
            "ref": f"{STATE_DIR}/{rel}",
            "exists": exists,
            "description": description,
            "authority": "project_local_projection",
        }
        if count is not None:
            row["item_count"] = count
        if kind == "pattern":
            row["surface_contract"] = pattern_surface
        if kind == "architecture":
            row["standard_pressure_contract"] = standard_pressure
        rows.append(row)
    payload = {
        **_base(project, "microcosm_project_state_index_v1"),
        "asset_count": len(rows),
        "assets": rows,
        "pattern_surface": pattern_surface,
        "standard_pressure_surface": standard_pressure,
        "authority_ceiling": {
            "project_local_projection_not_source_authority": True,
            "source_mutation_authorized": False,
            "release_authorized": False,
        },
    }
    write_json_atomic(state / "state_index.json", payload)
    return payload


def build_graph(
    project_path: str | Path,
    *,
    pattern_surface: dict[str, Any] | None = None,
    standard_pressure_surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate and write the project-local `.microcosm/graph.json` lineage graph.

    - Teleology: project the asset/lineage graph (primitive + surface + pattern/route/work/standard nodes and their relation edges) so navigation/graph views can render project-local lineage.
    - Guarantee: writes `<project>/.microcosm/graph.json` and returns the same payload (base header + node_count/edge_count, nodes, edges, embedded pattern + standard-pressure surfaces, graph_ref); nodes/edges are derived from on-disk routes/work/patterns plus the surfaces; GENERATED output.
    - Fails: surfaces strict-parse errors from any read state file and OSError from `write_json_atomic` if the state dir is unwritable; missing state files degrade to empty node/edge sets (no raise).
    - When-needed: inspect when the lineage graph is missing nodes/edges or shows stale counts.
    - Reads: `.microcosm/routes.json`, `.microcosm/work_items.json`, `.microcosm/patterns.json`; pattern/standard surfaces (args or loaders).
    - Writes: `<project>/.microcosm/graph.json`.
    - Escalates-to: rebuild via `write_project_architecture`; source surfaces `core/architecture_kernel.json` + `core/public_standard_pressure.json`.
    - Non-goal: does not authorize release or treat the generated graph as owner/source authority (it is a projection interface).
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    routes = read_json_if_exists(state / "routes.json").get("routes", [])
    work_items = read_json_if_exists(state / "work_items.json").get("work_items", [])
    patterns = read_json_if_exists(state / "patterns.json").get("patterns", [])
    pattern_surface = (
        pattern_surface if pattern_surface is not None else pattern_surface_contract()
    )
    standard_pressure_surface = (
        standard_pressure_surface
        if standard_pressure_surface is not None
        else load_standard_pressure_surface()
    )
    standard_pressure = _standard_pressure_contract_from_surface(standard_pressure_surface)
    standard_rows = _standard_pressure_rows_from_surface(standard_pressure_surface)
    nodes: list[dict[str, Any]] = [
        {"node_id": "project", "kind": "primitive", "label": "Project"},
        {"node_id": "catalog", "kind": "primitive", "label": "Catalog"},
        {"node_id": "pattern", "kind": "primitive", "label": "Pattern"},
        {
            "node_id": "pattern_surface",
            "kind": "surface",
            "label": "Public Pattern Surface",
            "state_ref": pattern_surface.get("state_ref"),
            "evidence_ref": pattern_surface.get("evidence_ref"),
        },
        {
            "node_id": "standard_pressure_surface",
            "kind": "surface",
            "label": "Public Standard Pressure",
            "state_ref": standard_pressure.get("state_ref"),
            "source_ref": standard_pressure.get("source_ref"),
        },
        {"node_id": "route", "kind": "primitive", "label": "Route"},
        {"node_id": "work", "kind": "primitive", "label": "Work"},
        {
            "node_id": "truth_readiness_surface",
            "kind": "surface",
            "label": "Truth/Readiness Surface",
            "state_ref": f"{STATE_DIR}/{TRUTH_READINESS_STATE}",
        },
        {"node_id": "event", "kind": "primitive", "label": "Event"},
        {"node_id": "evidence", "kind": "primitive", "label": "Evidence"},
        {"node_id": "explanation", "kind": "primitive", "label": "Explanation"},
    ]
    for ref in pattern_surface.get("binding_standard_refs", []):
        if isinstance(ref, str) and ref:
            nodes.append(
                {
                    "node_id": f"standard:{Path(ref).stem}",
                    "kind": "standard",
                    "label": Path(ref).stem,
                    "state_ref": ref,
                }
            )
    for row in standard_rows:
        standard_id = row.get("standard_id")
        if standard_id:
            nodes.append(
                {
                    "node_id": f"standard_pressure:{standard_id}",
                    "kind": "standard_pressure",
                    "label": row.get("title", standard_id),
                    "state_ref": f"{standard_pressure.get('state_ref')}::{standard_id}",
                }
            )
    assimilation_ref = pattern_surface.get("assimilation_policy_ref")
    if isinstance(assimilation_ref, str) and assimilation_ref:
        nodes.append(
            {
                "node_id": "assimilation_policy",
                "kind": "policy",
                "label": "Pattern Assimilation Policy",
                "state_ref": assimilation_ref,
            }
        )
    for row in patterns if isinstance(patterns, list) else []:
        if isinstance(row, dict):
            nodes.append({"node_id": f"pattern:{row.get('pattern_id')}", "kind": "pattern", "label": row.get("title")})
    for row in routes if isinstance(routes, list) else []:
        if isinstance(row, dict):
            nodes.append({"node_id": f"route:{row.get('route_id')}", "kind": "route", "label": row.get("title")})
    for row in work_items if isinstance(work_items, list) else []:
        if isinstance(row, dict):
            nodes.append({"node_id": f"work:{row.get('work_id')}", "kind": "work", "label": row.get("route_id")})
    edges: list[dict[str, Any]] = [
        {"from": "project", "to": "catalog", "relation": "indexes"},
        {"from": "catalog", "to": "pattern", "relation": "grounds"},
        {"from": "pattern", "to": "pattern_surface", "relation": "projects_to"},
        {"from": "pattern_surface", "to": "route", "relation": "opens"},
        {"from": "route", "to": "pattern_surface", "relation": "resolves_pattern_refs_against"},
        {"from": "route", "to": "standard_pressure_surface", "relation": "resolves_standard_pressure_against"},
        {"from": "pattern", "to": "route", "relation": "opens"},
        {"from": "route", "to": "work", "relation": "selects"},
        {"from": "work", "to": "truth_readiness_surface", "relation": "summarizes"},
        {"from": "explanation", "to": "truth_readiness_surface", "relation": "supports"},
        {"from": "work", "to": "event", "relation": "emits"},
        {"from": "event", "to": "evidence", "relation": "references"},
        {"from": "route", "to": "explanation", "relation": "explains"},
        {"from": "explanation", "to": "pattern_surface", "relation": "explains_against"},
        {"from": "explanation", "to": "standard_pressure_surface", "relation": "explains_against"},
    ]
    for ref in pattern_surface.get("binding_standard_refs", []):
        if isinstance(ref, str) and ref:
            edges.append(
                {
                    "from": "pattern_surface",
                    "to": f"standard:{Path(ref).stem}",
                    "relation": "governed_by",
                }
            )
    if isinstance(assimilation_ref, str) and assimilation_ref:
        edges.append({"from": "pattern_surface", "to": "assimilation_policy", "relation": "closed_by"})
    for row in standard_rows:
        standard_id = row.get("standard_id")
        if standard_id:
            edges.append(
                {
                    "from": "standard_pressure_surface",
                    "to": f"standard_pressure:{standard_id}",
                    "relation": "contains",
                }
            )
    for row in routes if isinstance(routes, list) else []:
        if isinstance(row, dict):
            for pattern_id in _route_pattern_refs(row):
                edges.append(
                    {
                        "from": f"pattern:{pattern_id}",
                        "to": f"route:{row.get('route_id')}",
                        "relation": "supports",
                    }
                )
            for standard_id in standard_pressure_refs_for_route(row, rows=standard_rows):
                edges.append(
                    {
                        "from": f"standard_pressure:{standard_id}",
                        "to": f"route:{row.get('route_id')}",
                        "relation": "constrains",
                    }
                )
    for row in work_items if isinstance(work_items, list) else []:
        if isinstance(row, dict):
            edges.append(
                {
                    "from": f"route:{row.get('route_id')}",
                    "to": f"work:{row.get('work_id')}",
                    "relation": "instantiates",
                }
            )
    payload = {
        **_base(project, "microcosm_project_asset_graph_v1"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "pattern_surface": pattern_surface,
        "standard_pressure_surface": standard_pressure,
        "graph_ref": f"{STATE_DIR}/graph.json",
    }
    write_json_atomic(state / "graph.json", payload)
    return payload


def write_project_architecture(project_path: str | Path) -> dict[str, Any]:
    """Generate the project's architecture projection and downstream graph+index.

    - Teleology: the top-level architecture-projection entrypoint — materialize `.microcosm/architecture.json` from the kernel manifest + public surfaces, then regenerate the graph and state index so all three stay consistent.
    - Guarantee: creates `.microcosm/`, `.microcosm/evidence/`, `.microcosm/explanations/`; writes `<project>/.microcosm/architecture.json` (base header + kernel manifest, primitive_ids, local_state_assets, pattern + standard-pressure surfaces, lineage, research-prototype posture with release_authorized False); then calls `build_graph` and `build_state_index`; returns the architecture payload; GENERATED output.
    - Fails: surfaces strict-parse errors from manifest/surface reads and OSError from directory creation or `write_json_atomic` if the project path is unwritable; otherwise no raise.
    - When-needed: run/inspect when a project's architecture projection (or its graph/index) is stale or missing after state changes.
    - Reads: kernel manifest via `load_kernel_manifest`; pattern/standard surfaces via their loaders; downstream reads of `.microcosm/*` state.
    - Writes: `<project>/.microcosm/architecture.json` (plus graph.json and state_index.json via callees).
    - Escalates-to: source surfaces `core/architecture_kernel.json` + `core/public_standard_pressure.json`; re-run this function to refresh.
    - Non-goal: does not authorize release/publication/provider calls/source mutation, and does not claim production-infrastructure or whole-system correctness (posture flags are False).
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    state.mkdir(parents=True, exist_ok=True)
    (state / EVIDENCE_DIR).mkdir(parents=True, exist_ok=True)
    (state / EXPLANATION_DIR).mkdir(parents=True, exist_ok=True)
    manifest = dict(load_kernel_manifest())
    pattern_surface = pattern_surface_contract()
    standard_pressure = load_standard_pressure_surface()
    standard_pressure_contract_payload = _standard_pressure_contract_from_surface(
        standard_pressure
    )
    payload = {
        **_base(project, "microcosm_project_architecture_v1"),
        "kernel": manifest,
        "primitive_ids": [
            str(row.get("primitive_id"))
            for row in manifest.get("primitives", [])
            if isinstance(row, dict)
        ],
        "local_state_assets": [
            f"{STATE_DIR}/project_manifest.json",
            f"{STATE_DIR}/architecture.json",
            f"{STATE_DIR}/state_index.json",
            f"{STATE_DIR}/graph.json",
            f"{STATE_DIR}/catalog.json",
            f"{STATE_DIR}/patterns.json",
            f"{STATE_DIR}/routes.json",
            f"{STATE_DIR}/work_items.json",
            f"{STATE_DIR}/{TRUTH_READINESS_STATE}",
            f"{STATE_DIR}/{EVENT_STREAM}",
            f"{STATE_DIR}/{EVIDENCE_DIR}/",
            f"{STATE_DIR}/{EXPLANATION_DIR}/",
        ],
        "pattern_surface": pattern_surface,
        "pattern_state_ref": pattern_surface.get("state_ref", ".microcosm/patterns.json"),
        "standard_pressure_surface": standard_pressure,
        "architecture_lineage": [
            "project folder",
            ".microcosm local state",
            "architecture kernel",
            "public pattern surface",
            "public standard pressure",
            "route graph",
            "route explanation",
            "work transaction",
            "event stream",
            "evidence membrane",
        ],
        "research_prototype_posture": {
            "small_on_purpose": True,
            "architectural_compression_is_product_standard": True,
            "production_infrastructure_claim": False,
            "release_authorized": False,
        },
    }
    write_json_atomic(state / "architecture.json", payload)
    build_graph(
        project,
        pattern_surface=pattern_surface,
        standard_pressure_surface=standard_pressure,
    )
    build_state_index(
        project,
        pattern_surface=pattern_surface,
        standard_pressure=standard_pressure_contract_payload,
    )
    return payload


def explain_route(project_path: str | Path, route_id: str) -> dict[str, Any]:
    """Generate and write a project-local route explanation with a causal-chain proof.

    - Teleology: connect one route to its grounded refs, resolved pattern/standard bindings, primitives, work-transaction shape, events, and evidence — the self-comprehension artifact for a route.
    - Guarantee: when the route id resolves, writes `<project>/.microcosm/explanations/<route_id>.json` and returns the explanation (bindings, work shape, causal_chain_proof whose `status` is pass only if every pattern+standard binding resolved and work/event/evidence refs are non-empty, else partial); the proof_scope is project-local lineage, not correctness authority; GENERATED output.
    - Fails: returns `{... "status": "not_found", "reason": "route_not_found"}` (NO write, no raise) when `route_id` matches no route; surfaces strict-parse errors from read state files and OSError from `write_json_atomic` on a resolvable route with an unwritable explanations dir.
    - When-needed: inspect when a route's explanation, causal chain, or selected work transaction looks wrong or stale.
    - Reads: `.microcosm/routes.json`, `.microcosm/patterns.json`, `.microcosm/work_items.json`, `.microcosm/events.jsonl`; pattern/standard surfaces via loaders.
    - Writes: `<project>/.microcosm/explanations/<route_id>.json` (only when the route resolves).
    - Escalates-to: reader drilldowns `.microcosm/routes.json`, `.microcosm/work_items.json`, `.microcosm/events.jsonl`, `.microcosm/evidence/`; re-run to refresh.
    - Non-goal: does not prove correctness, authorize source mutation/release/provider calls, assert private-data equivalence, or promote global doctrine (anti_claim is emitted in the payload).
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    routes_payload = read_json_if_exists(state / "routes.json")
    pattern_payload = read_json_if_exists(state / "patterns.json")
    work_payload = read_json_if_exists(state / "work_items.json")
    routes = routes_payload.get("routes", [])
    route = next(
        (
            row
            for row in routes
            if isinstance(row, dict)
            and (row.get("route_id") == route_id or row.get("row_id") == route_id)
        ),
        None,
    )
    if route is None:
        return {
            **_base(project, "microcosm_route_explanation_v1"),
            "status": "not_found",
            "route_id": route_id,
            "reason": "route_not_found",
        }
    pattern_refs = _route_pattern_refs(route)
    pattern_bindings = _pattern_bindings(pattern_payload, pattern_refs)
    standard_pressure_surface = load_standard_pressure_surface()
    standard_rows = _standard_pressure_rows_from_surface(standard_pressure_surface)
    standard_pressure_contract_payload = _standard_pressure_contract_from_surface(
        standard_pressure_surface
    )
    standard_bindings = _standard_pressure_bindings(
        route,
        rows=standard_rows,
        contract=standard_pressure_contract_payload,
    )
    patterns = [row["pattern"] for row in pattern_bindings if isinstance(row.get("pattern"), dict)]
    pattern_surface = pattern_surface_contract()
    work_items = [
        row
        for row in work_payload.get("work_items", [])
        if isinstance(row, dict) and row.get("route_id") == route.get("route_id")
    ]
    event_refs = _read_explanation_event_refs(state / EVENT_STREAM)
    work_event_refs = _dedupe_event_refs(
        [
            item
            for work in work_items
            for item in (
                work.get("event_refs", [])
                if isinstance(work.get("event_refs"), list)
                else []
            )
        ]
    )
    work_evidence_refs = _dedupe_strings(
        [
            item
            for work in work_items
            for item in (
                work.get("evidence_refs", [])
                if isinstance(work.get("evidence_refs"), list)
                else []
            )
        ]
    )
    explanation_evidence_refs = _dedupe_strings(
        [
            ".microcosm/evidence/routes.json",
            f".microcosm/evidence/explain_{route.get('route_id')}.json",
            *work_evidence_refs,
        ]
    )
    causal_event_refs = _dedupe_event_refs([*event_refs, *work_event_refs])
    selected_work = _select_public_work_transaction(work_items)
    selected_state_history = (
        [
            str(row.get("state"))
            for row in selected_work.get("state_history", [])
            if isinstance(row, dict) and row.get("state")
        ]
        if isinstance(selected_work, dict)
        and isinstance(selected_work.get("state_history"), list)
        else []
    )
    kernel_manifest = load_kernel_manifest()
    exercised_event_spans, exercised_primitives = (
        _exercised_primitives_from_event_refs(causal_event_refs, kernel_manifest)
    )
    declared_kernel_primitives = [
        str(prim.get("primitive_id"))
        for prim in kernel_manifest.get("primitives", [])
        if isinstance(prim, dict) and prim.get("primitive_id")
    ]
    execution_instance = _execution_instance(
        selected_work,
        route.get("route_id"),
        selected_state_history,
        kernel_manifest,
    )
    causal_chain_status = (
        PASS
        if route
        and all(row.get("resolved") is True for row in pattern_bindings)
        and all(row.get("resolved") is True for row in standard_bindings)
        and bool(work_items)
        and bool(causal_event_refs)
        and bool(explanation_evidence_refs)
        else "partial"
    )
    explanation = {
        **_base(project, "microcosm_route_explanation_v1"),
        "route_id": route.get("route_id"),
        "title": route.get("title"),
        "why_this_route_exists": (
            "The catalog classified project files, pattern observations mapped those "
            "roles to repo-shape signals, and the route primitive projected a reversible "
            "next action from those grounded refs."
        ),
        "grounded_refs": route.get("grounded_refs", []),
        "pattern_refs": pattern_refs,
        "pattern_surface": pattern_surface,
        "pattern_bindings": pattern_bindings,
        "pattern_evidence_refs": [
            pattern_surface.get("state_ref", ".microcosm/patterns.json"),
            pattern_surface.get("evidence_ref", ".microcosm/evidence/patterns.json"),
        ],
        "detected_patterns": patterns,
        "kernel_primitives": [
            "catalog",
            "pattern",
            "route",
            "work",
            "event",
            "evidence",
            "explanation",
        ],
        "standard_pressure_surface": standard_pressure_contract_payload,
        "standard_pressure_refs": standard_pressure_refs_for_route(
            route,
            rows=standard_rows,
        ),
        "standard_bindings": standard_bindings,
        "standard_pressure": [
            row["standard"]
            for row in standard_bindings
            if isinstance(row.get("standard"), dict)
        ],
        "work_transaction_shape": {
            "definition_ref": ".microcosm/routes.json",
            "execution_ref": ".microcosm/work_items.json",
            "state_machine": ["created", "selected", "planned", "executed_simulation", "closed"],
            "contract_shape": work_contracts_for_route(route),
            "matching_work_items": work_items,
        },
        "event_refs": event_refs,
        "evidence_refs": explanation_evidence_refs,
        "causal_chain_proof": {
            "status": causal_chain_status,
            "proof_scope": "project_local_state_lineage_not_correctness_authority",
            "route_id": route.get("route_id"),
            "route_ref": f".microcosm/routes.json::{route.get('route_id')}",
            "pattern_binding_ids": [
                row.get("pattern_id") for row in pattern_bindings if isinstance(row, dict)
            ],
            "standard_binding_ids": [
                row.get("standard_id") for row in standard_bindings if isinstance(row, dict)
            ],
            "work_ids": [
                row.get("work_id")
                for row in work_items
                if isinstance(row, dict) and row.get("work_id")
            ],
            "selected_work_id": (
                selected_work.get("work_id") if isinstance(selected_work, dict) else None
            ),
            "selected_work_status": (
                selected_work.get("status") if isinstance(selected_work, dict) else None
            ),
            "state_history": selected_state_history,
            "event_refs": causal_event_refs,
            "event_ref_count": len(causal_event_refs),
            "evidence_refs": explanation_evidence_refs,
            "evidence_ref_count": len(explanation_evidence_refs),
            "causal_scope": "route_neighbourhood_all_runs",
            "exercised_event_spans": exercised_event_spans,
            "exercised_primitives": exercised_primitives,
            "declared_kernel_primitives": declared_kernel_primitives,
            "occurrence_vs_declaration_note": (
                "exercised_primitives is derived from this run's event spans "
                "(occurrence); kernel_primitives and declared_kernel_primitives "
                "are the declared catalog (declaration) and need not be equal. The "
                "top-level event_refs/evidence_refs are route-scoped (all runs); "
                "execution_instance is the single-invocation partition."
            ),
            "execution_instance": execution_instance,
            "source_files_mutated": any(
                row.get("source_files_mutated") is True
                for row in work_items
                if isinstance(row, dict)
            ),
            "reader_drilldowns": [
                ".microcosm/routes.json",
                ".microcosm/work_items.json",
                ".microcosm/events.jsonl",
                ".microcosm/evidence/",
            ],
            "authority_boundary": "causal_chain_lineage_not_release_or_proof_correctness_authority",
        },
        "next_reversible_action": {
            "command": f"plectis work create <project> --route {route.get('route_id')}",
            "source_mutation": False,
        },
        "authority_boundary": "project_local_projection_not_source_authority",
        "macro_analogue": "navigation option surface + mission transaction + evidence membrane",
        "anti_claim": (
            "This explanation describes project-local public state only. It does not "
            "authorize source mutation, release, provider calls, private-data equivalence, "
            "or global doctrine promotion."
        ),
    }
    out_dir = state / EXPLANATION_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_dir / f"{route.get('route_id')}.json", explanation)
    return explanation
