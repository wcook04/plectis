from __future__ import annotations

from collections import deque
import json
import os
from pathlib import Path
from typing import Any, Iterator

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
            "runtime_commands": ["microcosm route <project>", "microcosm route inspect <project> <route_id>"],
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
            "runtime_commands": ["microcosm work create <project>", "microcosm work run <project>"],
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
                "microcosm observe --card <project>",
                "microcosm observe <project>",
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
            "runtime_commands": ["microcosm evidence list <project> --limit 25", "microcosm evidence inspect <project> <ref>"],
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
            "runtime_commands": ["microcosm explain <project> <route_id>", "microcosm route inspect <project> <route_id>"],
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
            "runtime_commands": ["microcosm work run <project>", "microcosm explain <project> <route_id>"],
            "endpoint_refs": ["/project/workitems"],
            "event_span": "work.run",
            "evidence_relation": ".microcosm/evidence/work_run_*.json",
            "macro_analogue": "pattern assimilation step",
            "public_boundary": "local closeout metadata, not live learning authority",
        },
    ],
}


def public_root() -> Path:
    """Resolve the public Microcosm substrate root for source-ref reads.

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
            "command": f"microcosm work create <project> --route {route.get('route_id')}",
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
