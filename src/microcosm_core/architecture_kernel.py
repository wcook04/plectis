from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core.receipts import utc_now, write_json_atomic
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
        "Microcosm is an executable research prototype of a local project substrate: "
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
            "runtime_commands": ["microcosm observe <project>"],
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
            "runtime_commands": ["microcosm evidence list <project>", "microcosm evidence inspect <project> <ref>"],
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
    return Path(__file__).resolve().parents[2]


def state_dir(project: str | Path) -> Path:
    return Path(project).expanduser().resolve(strict=False) / STATE_DIR


def project_relative(project: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(project.resolve(strict=False)).as_posix()
    except ValueError:
        return path.name


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _dedupe_strings(items: list[Any]) -> list[str]:
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


def load_kernel_manifest(root: str | Path | None = None) -> dict[str, Any]:
    root_path = Path(root).resolve(strict=False) if root is not None else public_root()
    manifest = read_json_if_exists(root_path / "core/architecture_kernel.json")
    if not manifest:
        manifest = dict(_DEFAULT_KERNEL)
    primitives = manifest.get("primitives", [])
    if isinstance(primitives, list):
        manifest["primitive_count"] = len([row for row in primitives if isinstance(row, dict)])
    return manifest


def pattern_surface_contract(root: str | Path | None = None) -> dict[str, Any]:
    surface = load_kernel_manifest(root).get("pattern_surface")
    if isinstance(surface, dict) and surface:
        return dict(surface)
    return dict(_PATTERN_SURFACE_CONTRACT)


def load_standard_pressure_surface(root: str | Path | None = None) -> dict[str, Any]:
    root_path = Path(root).resolve(strict=False) if root is not None else public_root()
    payload = read_json_if_exists(root_path / _STANDARD_PRESSURE_REF)
    if payload:
        return payload
    return dict(_DEFAULT_STANDARD_PRESSURE_SURFACE)


def standard_pressure_contract(root: str | Path | None = None) -> dict[str, Any]:
    surface = load_standard_pressure_surface(root)
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
    rows = load_standard_pressure_surface(root).get("rows", [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _route_pattern_refs(route: dict[str, Any]) -> list[str]:
    refs = route.get("pattern_refs", [])
    if isinstance(refs, list):
        return [str(ref) for ref in refs if ref is not None and str(ref)]
    fallback = _PATTERN_BY_ROUTE.get(str(route.get("route_id") or ""))
    return [fallback] if fallback else []


def _pattern_rows_by_id(pattern_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = pattern_payload.get("patterns", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("pattern_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("pattern_id")
    }


def _pattern_bindings(pattern_payload: dict[str, Any], pattern_refs: list[str]) -> list[dict[str, Any]]:
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


def standard_pressure_refs_for_route(route: dict[str, Any]) -> list[str]:
    route_id = str(route.get("route_id") or route.get("row_id") or "")
    refs = route.get("standard_pressure_refs", [])
    if isinstance(refs, list) and refs:
        return [str(ref) for ref in refs if ref is not None and str(ref)]
    selected: list[str] = []
    for row in standard_pressure_rows():
        row_refs = row.get("route_refs", [])
        if row_refs == ["*"] or route_id in row_refs:
            standard_id = row.get("standard_id")
            if standard_id:
                selected.append(str(standard_id))
    return selected


def _standard_pressure_bindings(route: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_id = {
        str(row.get("standard_id")): row
        for row in standard_pressure_rows()
        if row.get("standard_id")
    }
    contract = standard_pressure_contract()
    bindings: list[dict[str, Any]] = []
    for standard_id in standard_pressure_refs_for_route(route):
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


def build_state_index(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    pattern_surface = pattern_surface_contract()
    standard_pressure = standard_pressure_contract()
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
            count = len(list(path.glob("*.json"))) if path.is_dir() else 0
            exists = path.is_dir()
        else:
            count = None
            exists = path.is_file()
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


def build_graph(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    routes = read_json_if_exists(state / "routes.json").get("routes", [])
    work_items = read_json_if_exists(state / "work_items.json").get("work_items", [])
    patterns = read_json_if_exists(state / "patterns.json").get("patterns", [])
    pattern_surface = pattern_surface_contract()
    standard_pressure = standard_pressure_contract()
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
    for row in standard_pressure_rows():
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
    for row in standard_pressure_rows():
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
            for standard_id in standard_pressure_refs_for_route(row):
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
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    state.mkdir(parents=True, exist_ok=True)
    (state / EVIDENCE_DIR).mkdir(parents=True, exist_ok=True)
    (state / EXPLANATION_DIR).mkdir(parents=True, exist_ok=True)
    manifest = dict(load_kernel_manifest())
    pattern_surface = pattern_surface_contract()
    standard_pressure = load_standard_pressure_surface()
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
    build_graph(project)
    build_state_index(project)
    return payload


def explain_route(project_path: str | Path, route_id: str) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    state = state_dir(project)
    routes_payload = read_json_if_exists(state / "routes.json")
    pattern_payload = read_json_if_exists(state / "patterns.json")
    work_payload = read_json_if_exists(state / "work_items.json")
    events = read_jsonl(state / EVENT_STREAM)
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
    standard_bindings = _standard_pressure_bindings(route)
    patterns = [row["pattern"] for row in pattern_bindings if isinstance(row.get("pattern"), dict)]
    pattern_surface = pattern_surface_contract()
    work_items = [
        row
        for row in work_payload.get("work_items", [])
        if isinstance(row, dict) and row.get("route_id") == route.get("route_id")
    ]
    event_refs = [
        {
            "event_id": row.get("event_id"),
            "span": row.get("span"),
            "status": row.get("status"),
        }
        for row in events
        if row.get("span") in {"project.route", "project.explain", "work.create", "work.run"}
    ][-12:]
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
    selected_work = work_items[-1] if work_items else {}
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
        "standard_pressure_surface": standard_pressure_contract(),
        "standard_pressure_refs": standard_pressure_refs_for_route(route),
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
