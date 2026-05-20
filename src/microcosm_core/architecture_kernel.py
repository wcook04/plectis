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

_PATTERN_BY_ROUTE = {
    "readme_onboarding_route": "repo_has_readme",
    "package_runtime_route": "repo_has_package_manifest",
    "source_core_route": "repo_has_source_core",
    "test_behavior_route": "repo_has_tests",
    "missing_tests_route": "repo_has_tests",
    "docs_route": "repo_has_docs",
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
            "what_it_does": "Maps catalog roles into repo-shape pattern observations.",
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
            "what_it_does": "Turns project-grounded patterns into reversible next-action candidates.",
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
            "what_it_does": "Connects a route to grounded refs, patterns, primitives, standards, work shape, events, and evidence.",
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


def load_kernel_manifest(root: str | Path | None = None) -> dict[str, Any]:
    root_path = Path(root).resolve(strict=False) if root is not None else public_root()
    manifest = read_json_if_exists(root_path / "core/architecture_kernel.json")
    if not manifest:
        manifest = dict(_DEFAULT_KERNEL)
    primitives = manifest.get("primitives", [])
    if isinstance(primitives, list):
        manifest["primitive_count"] = len([row for row in primitives if isinstance(row, dict)])
    return manifest


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
    assets = [
        ("project", "project_manifest.json", "project root manifest"),
        ("architecture", "architecture.json", "public architecture kernel projection"),
        ("state_index", "state_index.json", "project-local substrate asset index"),
        ("graph", "graph.json", "asset graph and lineage edges"),
        ("catalog", "catalog.json", "file role catalog"),
        ("pattern", "patterns.json", "repo-shape pattern observations"),
        ("route", "routes.json", "route candidates"),
        ("work", "work_items.json", "work transaction records"),
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
        rows.append(row)
    payload = {
        **_base(project, "microcosm_project_state_index_v1"),
        "asset_count": len(rows),
        "assets": rows,
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
    nodes: list[dict[str, Any]] = [
        {"node_id": "project", "kind": "primitive", "label": "Project"},
        {"node_id": "catalog", "kind": "primitive", "label": "Catalog"},
        {"node_id": "pattern", "kind": "primitive", "label": "Pattern"},
        {"node_id": "route", "kind": "primitive", "label": "Route"},
        {"node_id": "work", "kind": "primitive", "label": "Work"},
        {"node_id": "event", "kind": "primitive", "label": "Event"},
        {"node_id": "evidence", "kind": "primitive", "label": "Evidence"},
        {"node_id": "explanation", "kind": "primitive", "label": "Explanation"},
    ]
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
        {"from": "pattern", "to": "route", "relation": "opens"},
        {"from": "route", "to": "work", "relation": "selects"},
        {"from": "work", "to": "event", "relation": "emits"},
        {"from": "event", "to": "evidence", "relation": "references"},
        {"from": "route", "to": "explanation", "relation": "explains"},
    ]
    for row in routes if isinstance(routes, list) else []:
        if isinstance(row, dict):
            pattern_id = _PATTERN_BY_ROUTE.get(str(row.get("route_id") or ""))
            if pattern_id:
                edges.append(
                    {
                        "from": f"pattern:{pattern_id}",
                        "to": f"route:{row.get('route_id')}",
                        "relation": "supports",
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
            f"{STATE_DIR}/{EVENT_STREAM}",
            f"{STATE_DIR}/{EVIDENCE_DIR}/",
            f"{STATE_DIR}/{EXPLANATION_DIR}/",
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
    pattern_id = _PATTERN_BY_ROUTE.get(str(route.get("route_id") or ""))
    patterns = [
        row
        for row in pattern_payload.get("patterns", [])
        if isinstance(row, dict) and (not pattern_id or row.get("pattern_id") == pattern_id)
    ]
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
        "detected_patterns": patterns,
        "kernel_primitives": ["catalog", "pattern", "route", "work", "event", "evidence", "explanation"],
        "standard_pressure": [
            {
                "standard_id": "local_first_boundary",
                "claim": "Project state stays in .microcosm/ and remains under the user's folder.",
            },
            {
                "standard_id": "reversible_work_transaction",
                "claim": "Work runs simulate governed transactions and do not mutate source files by default.",
            },
            {
                "standard_id": "evidence_as_drilldown",
                "claim": "Evidence references are generated black-box recorder drilldowns, not the primary cockpit.",
            },
        ],
        "work_transaction_shape": {
            "definition_ref": ".microcosm/routes.json",
            "execution_ref": ".microcosm/work_items.json",
            "state_machine": ["created", "selected", "planned", "executed_simulation", "closed"],
            "matching_work_items": work_items,
        },
        "event_refs": event_refs,
        "evidence_refs": [
            ".microcosm/evidence/routes.json",
            f".microcosm/evidence/explain_{route.get('route_id')}.json",
        ],
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
