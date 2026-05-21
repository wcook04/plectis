from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from microcosm_core import architecture_kernel
from microcosm_core import project_substrate
from microcosm_core.organs import agent_route_observability_runtime
from microcosm_core.organs import executable_doctrine_grammar
from microcosm_core.organs import formal_math_readiness_gate
from microcosm_core.organs import mission_transaction_work_spine
from microcosm_core.organs import navigation_hologram_route_plane
from microcosm_core.organs import pattern_binding_contract
from microcosm_core.organs import proof_diagnostic_evidence_spine
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.validators import acceptance


PASS = "pass"
DEFAULT_PROJECT_REL = "examples/runtime_shell/demo_project"


Runner = Callable[[str | Path, str | Path, str | None], dict[str, Any]]


@dataclass(frozen=True)
class RuntimeStep:
    organ_id: str
    span: str
    input_mode: str
    example_rel: str
    runner: Runner
    receipt_name: str


RUNTIME_STEPS: tuple[RuntimeStep, ...] = (
    RuntimeStep(
        organ_id="pattern_binding_contract",
        span="pattern_binding.validate",
        input_mode="exported_substrate_bundle",
        example_rel="examples/pattern_binding_contract/exported_substrate_bundle",
        runner=pattern_binding_contract.validate_substrate_bundle,
        receipt_name="exported_substrate_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="executable_doctrine_grammar",
        span="doctrine_grammar.validate",
        input_mode="exported_standards_bundle",
        example_rel="examples/executable_doctrine_grammar/exported_standards_bundle",
        runner=executable_doctrine_grammar.validate_standards_bundle,
        receipt_name="exported_standards_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="proof_diagnostic_evidence_spine",
        span="proof_evidence.run",
        input_mode="exported_evidence_bundle",
        example_rel="examples/proof_diagnostic_evidence_spine/exported_evidence_bundle",
        runner=proof_diagnostic_evidence_spine.run_evidence_bundle,
        receipt_name="exported_evidence_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="formal_math_readiness_gate",
        span="formal_math_readiness.validate",
        input_mode="exported_formal_math_readiness_bundle",
        example_rel="examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle",
        runner=formal_math_readiness_gate.run_readiness_bundle,
        receipt_name="exported_formal_math_readiness_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="navigation_hologram_route_plane",
        span="navigation_route_plane.validate",
        input_mode="exported_route_plane_bundle",
        example_rel="examples/navigation_hologram_route_plane/exported_route_plane_bundle",
        runner=navigation_hologram_route_plane.run_route_plane_bundle,
        receipt_name="exported_route_plane_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="mission_transaction_work_spine",
        span="mission_transaction.validate",
        input_mode="exported_mission_transaction_bundle",
        example_rel="examples/mission_transaction_work_spine/exported_mission_transaction_bundle",
        runner=mission_transaction_work_spine.run_mission_transaction_bundle,
        receipt_name="exported_mission_transaction_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="agent_route_observability_runtime",
        span="observability.validate",
        input_mode="exported_observability_bundle",
        example_rel="examples/agent_route_observability_runtime/exported_observability_bundle",
        runner=agent_route_observability_runtime.run_observability_bundle,
        receipt_name="exported_observability_bundle_validation_result.json",
    ),
    RuntimeStep(
        organ_id="pattern_assimilation_step",
        span="assimilation.validate",
        input_mode="exported_assimilation_bundle",
        example_rel="examples/pattern_assimilation_step/exported_assimilation_bundle",
        runner=acceptance.run_assimilation_bundle,
        receipt_name="exported_assimilation_bundle_validation_result.json",
    ),
)


def public_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _public_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _first_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                return item
    return None


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _badge_list(values: list[str]) -> str:
    if not values:
        return "<span class=\"muted\">none</span>"
    return "".join(f"<span class=\"badge\">{html.escape(value)}</span>" for value in values)


def _safe_receipt_summary(path: Path, root: Path) -> dict[str, Any]:
    payload = _read_json_if_exists(path)
    return {
        "receipt_ref": _public_relative(path, root),
        "status": payload.get("status", "unknown"),
        "schema_version": payload.get("schema_version"),
        "organ_id": payload.get("organ_id"),
        "input_mode": payload.get("input_mode"),
        "created_at": payload.get("created_at"),
    }


class RuntimeShell:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).resolve(strict=False) if root is not None else public_root()

    @property
    def runtime_receipt_dir(self) -> Path:
        return self.root / "receipts/runtime_shell"

    def organs(self) -> list[dict[str, Any]]:
        registry = _read_json_if_exists(self.root / "core/organ_registry.json")
        rows = registry.get("implemented_organs", [])
        if not isinstance(rows, list):
            return []
        by_step = {step.organ_id: step for step in RUNTIME_STEPS}
        organs: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            organ_id = str(row.get("organ_id") or "")
            step = by_step.get(organ_id)
            organs.append(
                {
                    "organ_id": organ_id,
                    "status": row.get("status"),
                    "runner": row.get("runner"),
                    "runtime_mode": "adapter_backed" if step else "registry_only",
                    "input_mode": step.input_mode if step else None,
                    "example_ref": step.example_rel if step else None,
                    "fixture_runner_backed": False if step else None,
                }
            )
        return organs

    def patterns(self) -> list[dict[str, Any]]:
        rows = _read_jsonl(
            self.root
            / "examples/pattern_binding_contract/exported_substrate_bundle/pattern_rows.jsonl"
        )
        return [
            {
                "pattern_id": str(row.get("pattern_id") or ""),
                "organ_id": row.get("organ_id"),
                "title": row.get("title"),
                "projection_posture": row.get("public_projection_posture")
                or row.get("projection_mode"),
                "source_ref_count": len(row.get("source_refs", []))
                if isinstance(row.get("source_refs"), list)
                else 0,
            }
            for row in rows
        ]

    def routes(self) -> list[dict[str, Any]]:
        payload = _read_json_if_exists(
            self.root / "examples/navigation_hologram_route_plane/exported_route_plane_bundle/route_rows.json"
        )
        return [
            {
                "route_id": str(row.get("route_id") or row.get("row_id") or ""),
                "row_id": row.get("row_id"),
                "title": row.get("title"),
                "cluster_id": row.get("cluster_id"),
                "surface_role": row.get("surface_role"),
                "projection_not_authority": not bool(row.get("claims_source_authority")),
            }
            for row in _rows(payload, "rows")
        ]

    def workitems(self) -> list[dict[str, Any]]:
        payload = _read_json_if_exists(
            self.root / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/workitems.json"
        )
        return [
            {
                "work_item_id": str(row.get("work_item_id") or ""),
                "state": row.get("state"),
                "depends_on": row.get("depends_on", []),
                "receipt_refs": row.get("receipt_refs", []),
                "projection_not_authority": row.get("projection_not_authority") is True,
            }
            for row in _rows(payload, "workitems")
        ]

    def evidence(self) -> list[dict[str, Any]]:
        receipts = sorted((self.root / "receipts").rglob("*.json"))
        return [_safe_receipt_summary(path, self.root) for path in receipts]

    def status(self) -> dict[str, Any]:
        organs = self.organs()
        adapter_backed = [row["organ_id"] for row in organs if row.get("runtime_mode") == "adapter_backed"]
        routes = self.routes()
        workitems = self.workitems()
        evidence = self.evidence()
        pattern_surface = architecture_kernel.pattern_surface_contract(self.root)
        standard_pressure = architecture_kernel.standard_pressure_contract(self.root)
        return {
            "schema_version": "microcosm_runtime_status_v1",
            "status": PASS if len(adapter_backed) == len(RUNTIME_STEPS) else "blocked",
            "posture": "executable_research_prototype",
            "public_root": _public_relative(self.root, self.root),
            "runtime_surface": {
                "commands": [
                    "microcosm init <project>",
                    "microcosm index <project>",
                    "microcosm catalog <project>",
                    "microcosm architecture <project>",
                    "microcosm compile <project>",
                    "microcosm patterns <project>",
                    "microcosm route <project>",
                    "microcosm explain <project> <route_id>",
                    "microcosm graph <project>",
                    "microcosm work create <project>",
                    "microcosm work run <project>",
                    "microcosm observe <project>",
                    "microcosm evidence list <project>",
                    "microcosm status",
                    "microcosm run examples/runtime_shell/demo_project",
                    "microcosm serve",
                    "microcosm route list",
                    "microcosm route inspect <id>",
                    "microcosm work demo",
                    "microcosm evidence list",
                    "microcosm evidence inspect <receipt>",
                ],
                "receipts_are_drilldown_evidence": True,
                "fixtures_are_tests": True,
            },
            "organ_count": len(organs),
            "adapter_backed_organ_count": len(adapter_backed),
            "fixture_runner_backed_organ_count": 0,
            "accepted_adapter_backed_organs": adapter_backed,
            "route_count": len(routes),
            "pattern_count": len(self.patterns()),
            "pattern_surface": pattern_surface,
            "standard_pressure_surface": standard_pressure,
            "workitem_count": len(workitems),
            "evidence_count": len(evidence),
            "kernel_primitive_count": architecture_kernel.load_kernel_manifest(self.root).get("primitive_count"),
            "release_authorized": False,
            "next_actions": [
                "run microcosm init <project>",
                "run microcosm compile <project>",
                "run microcosm explain <project> <route_id>",
                "open evidence only when drilldown is needed",
            ],
        }

    def inspect_route(self, route_id: str) -> dict[str, Any]:
        for route in self.routes():
            if route["route_id"] == route_id or route.get("row_id") == route_id:
                return {
                    "schema_version": "microcosm_runtime_route_card_v1",
                    "status": PASS,
                    "route": route,
                }
        return {
            "schema_version": "microcosm_runtime_route_card_v1",
            "status": "not_found",
            "route_id": route_id,
        }

    def inspect_evidence(self, receipt_ref: str) -> dict[str, Any]:
        receipt_path = self.root / receipt_ref
        if not receipt_path.is_file():
            return {
                "schema_version": "microcosm_runtime_evidence_card_v1",
                "status": "not_found",
                "receipt_ref": receipt_ref,
            }
        payload = read_json_strict(receipt_path)
        if not isinstance(payload, dict):
            return {
                "schema_version": "microcosm_runtime_evidence_card_v1",
                "status": "blocked",
                "receipt_ref": receipt_ref,
                "reason": "receipt is not a JSON object",
            }
        allowed = {
            key: payload.get(key)
            for key in (
                "schema_version",
                "receipt_id",
                "organ_id",
                "fixture_id",
                "status",
                "input_mode",
                "bundle_id",
                "created_at",
                "command",
                "anti_claim",
                "authority_ceiling",
                "receipt_paths",
            )
            if key in payload
        }
        return {
            "schema_version": "microcosm_runtime_evidence_card_v1",
            "status": PASS,
            "receipt_ref": receipt_ref,
            "receipt": allowed,
            "body_redacted": True,
        }

    def run_demo(self, project: str | Path = DEFAULT_PROJECT_REL) -> dict[str, Any]:
        project_path = Path(project)
        if not project_path.is_absolute():
            project_path = self.root / project_path
        manifest = _read_json_if_exists(project_path / "project_manifest.json")
        project_id = str(manifest.get("project_id") or "demo_project")
        run_root = self.runtime_receipt_dir / project_id
        event_rows: list[dict[str, Any]] = []
        evidence_refs: list[str] = []
        summaries: list[str] = []

        for index, step in enumerate(RUNTIME_STEPS, start=1):
            input_dir = self.root / step.example_rel
            out_dir = run_root / "organs" / step.organ_id
            command = f"microcosm run {_public_relative(project_path, self.root)}"
            result = step.runner(input_dir, out_dir, command)
            receipt_ref = _public_relative(out_dir / step.receipt_name, self.root)
            evidence_refs.append(receipt_ref)
            status = str(result.get("status") or "unknown")
            event_rows.append(
                {
                    "event_id": f"evt_{index:02d}_{step.organ_id}",
                    "span": step.span,
                    "organ_id": step.organ_id,
                    "status": status,
                    "input_mode": result.get("input_mode", step.input_mode),
                    "inputs": _public_relative(input_dir, self.root),
                    "outputs": _public_relative(out_dir, self.root),
                    "evidence_ref": receipt_ref,
                }
            )
            summaries.append(f"{step.organ_id}: {status} via {step.input_mode}")

        status = PASS if all(event["status"] == PASS for event in event_rows) else "blocked"
        trace = {
            "schema_version": "microcosm_runtime_trace_v1",
            "project_id": project_id,
            "created_at": utc_now(),
            "status": status,
            "events": event_rows,
            "otel_shape": {
                "trace_id": f"runtime_shell_{project_id}",
                "span_count": len(event_rows),
                "logs_as_events": True,
                "metrics": {
                    "runtime_steps_total": len(event_rows),
                    "runtime_steps_passed": sum(1 for event in event_rows if event["status"] == PASS),
                },
            },
        }
        result = {
            "schema_version": "microcosm_runtime_demo_result_v1",
            "project_id": project_id,
            "created_at": trace["created_at"],
            "status": status,
            "what_happened": summaries,
            "next_actions": [
                "microcosm route list",
                "microcosm evidence list",
                "microcosm serve",
            ],
            "events": event_rows,
            "evidence_refs": evidence_refs,
            "trace_ref": _public_relative(run_root / "demo_project_trace.json", self.root),
            "authority_ceiling": {
                "release_authorized": False,
                "provider_calls_authorized": False,
                "live_task_ledger_mutation_authorized": False,
                "private_data_equivalence_claim": False,
            },
            "anti_claim": (
                "The runtime shell demo executes public exported-bundle validators and emits "
                "public trace/evidence refs. It does not authorize release, hosting, "
                "provider calls, private-data equivalence, or live ledger mutation."
            ),
        }
        write_json_atomic(run_root / "demo_project_trace.json", trace)
        write_json_atomic(run_root / "demo_project_result.json", result)
        return result

    def run_work_demo(self) -> dict[str, Any]:
        step = next(item for item in RUNTIME_STEPS if item.organ_id == "mission_transaction_work_spine")
        input_dir = self.root / step.example_rel
        out_dir = self.runtime_receipt_dir / "work_demo" / "organs" / step.organ_id
        result = step.runner(input_dir, out_dir, "microcosm work demo")
        receipt_ref = _public_relative(out_dir / step.receipt_name, self.root)
        payload = {
            "schema_version": "microcosm_runtime_work_demo_v1",
            "created_at": utc_now(),
            "status": result.get("status", "unknown"),
            "workitems": self.workitems(),
            "transaction_id": result.get("transaction_id"),
            "schedulable_workitem_ids": result.get("schedulable_workitem_ids", []),
            "blocked_workitem_ids": result.get("blocked_workitem_ids", []),
            "evidence_ref": receipt_ref,
            "authority_ceiling": {
                "live_task_ledger_mutation_authorized": False,
                "live_work_ledger_mutation_authorized": False,
                "release_authorized": False,
            },
        }
        write_json_atomic(self.runtime_receipt_dir / "work_demo" / "work_demo_result.json", payload)
        return payload

    def project_observatory(self, project: str | Path | None = None) -> dict[str, Any]:
        project_path = Path(project).expanduser().resolve(strict=False) if project is not None else None
        status = self.status()
        kernel = {
            **architecture_kernel.load_kernel_manifest(self.root),
            "standard_pressure_surface": architecture_kernel.load_standard_pressure_surface(self.root),
        }
        model: dict[str, Any] = {
            "schema_version": "microcosm_project_observatory_v1",
            "status": PASS,
            "runtime_status": status,
            "kernel": kernel,
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "evidence_is_drilldown": True,
            "anti_claim": (
                "The observatory summarizes project-local public substrate state. It "
                "does not authorize release, hosting, provider calls, source mutation, "
                "private-data equivalence, or global doctrine promotion."
            ),
        }
        if project_path is None:
            model["project_summary"] = {
                "project_id": "public_runtime",
                "status": status.get("status"),
                "state_ref": None,
                "local_state_refs": [],
            }
            return model

        state = project_path / project_substrate.STATE_DIR
        if not (state / "project_manifest.json").is_file():
            project_substrate.init_project(project_path)
        if not (state / "catalog.json").is_file():
            project_substrate.index_project(project_path)
        if not (state / "patterns.json").is_file():
            project_substrate.discover_patterns(project_path)
        if not (state / "routes.json").is_file():
            project_substrate.propose_routes(project_path)
        architecture = project_substrate.architecture_project(project_path)
        graph = project_substrate.state_graph(project_path)
        catalog = project_substrate.catalog_project(project_path)
        patterns = project_substrate.discover_patterns(project_path)
        routes = project_substrate.propose_routes(project_path)
        route_rows = _rows(routes, "routes")
        selected_route = next(
            (row for row in route_rows if row.get("route_id") == "readme_onboarding_route"),
            route_rows[0] if route_rows else {},
        )
        route_id = str(selected_route.get("route_id") or "")
        explanation_path = state / "explanations" / f"{route_id}.json"
        explanation = _read_json_if_exists(explanation_path)
        if route_id and not explanation:
            explanation = project_substrate.explain_route(project_path, route_id)
        work_items = project_substrate._load_work_items(project_path)
        selected_work = next(
            (row for row in work_items if row.get("route_id") == route_id),
            work_items[-1] if work_items else {},
        )
        observe = project_substrate.observe_project(project_path)
        evidence = project_substrate.list_evidence(project_path)
        pattern_bindings = _rows(explanation, "pattern_bindings")
        standard_bindings = _rows(explanation, "standard_bindings")
        work_event_refs = selected_work.get("event_refs", []) if isinstance(selected_work, dict) else []
        work_evidence_refs = selected_work.get("evidence_refs", []) if isinstance(selected_work, dict) else []
        event_rows = _rows(observe, "events")
        evidence_rows = _rows(evidence, "evidence")
        causal_events = [
            row
            for row in event_rows
            if row.get("span") in {"project.route", "project.explain", "work.create", "work.run"}
        ][-8:]
        model.update(
            {
                "project_summary": {
                    "project_id": catalog.get("project_id") or project_path.name,
                    "project_ref": ".",
                    "status": PASS,
                    "state_ref": project_substrate.STATE_DIR,
                    "local_state_refs": [
                        ".microcosm/catalog.json",
                        ".microcosm/patterns.json",
                        ".microcosm/routes.json",
                        ".microcosm/work_items.json",
                        ".microcosm/events.jsonl",
                        ".microcosm/evidence/",
                    ],
                    "release_authorized": False,
                    "provider_calls_authorized": False,
                    "source_mutation_authorized": False,
                },
                "selected_route_id": route_id,
                "catalog_summary": {
                    "file_count": catalog.get("file_count", 0),
                    "role_counts": catalog.get("role_counts", {}),
                },
                "causal_chain": {
                    "route": {
                        "route_id": route_id,
                        "title": selected_route.get("title"),
                        "grounded_refs": selected_route.get("grounded_refs", []),
                        "pattern_refs": selected_route.get("pattern_refs", []),
                        "standard_pressure_refs": selected_route.get("standard_pressure_refs", []),
                        "source_mutation_authorized": selected_route.get("source_mutation_authorized") is True,
                        "authority": selected_route.get("authority"),
                    },
                    "pattern_bindings": [
                        {
                            "pattern_id": row.get("pattern_id"),
                            "resolved": row.get("resolved") is True,
                            "title": (row.get("pattern") or {}).get("title")
                            if isinstance(row.get("pattern"), dict)
                            else None,
                            "state_ref": row.get("state_ref"),
                        }
                        for row in pattern_bindings
                    ],
                    "standard_bindings": [
                        {
                            "standard_id": row.get("standard_id"),
                            "resolved": row.get("resolved") is True,
                            "title": (row.get("standard") or {}).get("title")
                            if isinstance(row.get("standard"), dict)
                            else None,
                            "state_ref": row.get("state_ref"),
                        }
                        for row in standard_bindings
                    ],
                    "work_transaction": {
                        "work_id": selected_work.get("work_id"),
                        "status": selected_work.get("status"),
                        "route_id": selected_work.get("route_id"),
                        "transaction_policy": selected_work.get("transaction_policy"),
                        "state_history": selected_work.get("state_history", []),
                        "satisfaction_contract": selected_work.get("satisfaction_contract"),
                        "integration_contract": selected_work.get("integration_contract"),
                        "closeout": selected_work.get("closeout"),
                        "source_files_mutated": selected_work.get("source_files_mutated") is True,
                        "event_refs": work_event_refs if isinstance(work_event_refs, list) else [],
                        "evidence_refs": work_evidence_refs if isinstance(work_evidence_refs, list) else [],
                    },
                    "events": causal_events,
                    "evidence": evidence_rows[-10:],
                    "authority_boundary": explanation.get("authority_boundary")
                    or "project_local_projection_not_source_authority",
                },
                "graph_summary": {
                    "node_count": graph.get("node_count", 0),
                    "edge_count": graph.get("edge_count", 0),
                    "key_relations": [
                        "project -> catalog",
                        "catalog -> pattern",
                        "pattern -> route",
                        "route -> explanation",
                        "route -> work",
                        "work -> event",
                        "event -> evidence",
                    ],
                    "graph_ref": ".microcosm/graph.json",
                },
                "kernel_summary": {
                    "primitive_names": [
                        row.get("public_name")
                        for row in kernel.get("primitives", [])
                        if isinstance(row, dict) and row.get("public_name")
                    ],
                    "pattern_surface_id": (architecture.get("pattern_surface") or {}).get("surface_id")
                    if isinstance(architecture.get("pattern_surface"), dict)
                    else None,
                    "standard_pressure_surface_id": (
                        architecture.get("standard_pressure_surface") or {}
                    ).get("surface_id")
                    if isinstance(architecture.get("standard_pressure_surface"), dict)
                    else None,
                },
                "json_drilldowns": {
                    "kernel": "/kernel",
                    "graph": "/project/graph",
                    "workitems": "/project/workitems",
                    "evidence": "/project/evidence",
                    "explain": f"/project/explain/{route_id}" if route_id else None,
                },
            }
        )
        return model

    def _observatory_html(self, project_path: Path | None) -> str:
        model = self.project_observatory(project_path)
        project_summary = model.get("project_summary", {})
        causal = model.get("causal_chain", {})
        route = causal.get("route", {}) if isinstance(causal.get("route"), dict) else {}
        work = causal.get("work_transaction", {}) if isinstance(causal.get("work_transaction"), dict) else {}
        graph = model.get("graph_summary", {})
        kernel = model.get("kernel_summary", {})
        pattern_bindings = causal.get("pattern_bindings", []) if isinstance(causal.get("pattern_bindings"), list) else []
        standard_bindings = causal.get("standard_bindings", []) if isinstance(causal.get("standard_bindings"), list) else []
        events = causal.get("events", []) if isinstance(causal.get("events"), list) else []
        evidence = causal.get("evidence", []) if isinstance(causal.get("evidence"), list) else []

        def dump(payload: Any) -> str:
            return html.escape(json.dumps(payload, indent=2, sort_keys=True))

        def row(label: str, value: Any) -> str:
            return (
                "<tr>"
                f"<th>{html.escape(label)}</th>"
                f"<td>{html.escape(_safe_text(value))}</td>"
                "</tr>"
            )

        def binding_rows(rows: list[Any], id_key: str) -> str:
            if not rows:
                return "<p class=\"muted\">No bindings yet.</p>"
            items = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                status = "resolved" if item.get("resolved") is True else "unresolved"
                items.append(
                    "<li>"
                    f"<strong>{html.escape(_safe_text(item.get(id_key)))}</strong>"
                    f" <span class=\"pill {status}\">{status}</span>"
                    f"<br><span class=\"muted\">{html.escape(_safe_text(item.get('title') or item.get('state_ref')))}</span>"
                    "</li>"
                )
            return f"<ul>{''.join(items)}</ul>"

        def event_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"4\" class=\"muted\">No events recorded yet.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('event_id')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('span')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('status')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('evidence_ref')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        def evidence_rows(rows: list[Any]) -> str:
            if not rows:
                return "<tr><td colspan=\"3\" class=\"muted\">No evidence refs yet.</td></tr>"
            output = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                output.append(
                    "<tr>"
                    f"<td>{html.escape(_safe_text(item.get('evidence_ref')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('status')))}</td>"
                    f"<td>{html.escape(_safe_text(item.get('replacement_policy')))}</td>"
                    "</tr>"
                )
            return "".join(output)

        state_history = [
            str(item.get("state"))
            for item in work.get("state_history", [])
            if isinstance(item, dict) and item.get("state")
        ]
        event_ref_values = [
            str(item.get("event_id"))
            for item in work.get("event_refs", [])
            if isinstance(item, dict) and item.get("event_id")
        ]
        evidence_ref_values = [
            str(item)
            for item in work.get("evidence_refs", [])
            if item
        ]
        route_id = _safe_text(route.get("route_id") or model.get("selected_route_id"))
        project_title = project_path.name if project_path is not None else "public runtime"
        endpoint_items = "".join(
            f"<li><code>{html.escape(str(endpoint))}</code></li>"
            for endpoint in (model.get("json_drilldowns") or {}).values()
            if endpoint
        )
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Microcosm Observatory</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f5f5f1; color: #171715; }}
    header {{ padding: 30px 34px 20px; border-bottom: 1px solid #d8d7d1; background: #ffffff; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    p {{ margin: 0; max-width: 980px; line-height: 1.48; color: #4b4a45; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, .85fr); gap: 16px; padding: 20px; }}
    section {{ background: #ffffff; border: 1px solid #dad8d0; border-radius: 6px; overflow: hidden; min-width: 0; }}
    section.wide {{ grid-column: 1 / -1; }}
    h2 {{ margin: 0; padding: 12px 14px; font-size: 15px; background: #eceae3; border-bottom: 1px solid #dad8d0; }}
    h3 {{ margin: 16px 0 8px; font-size: 13px; }}
    .content {{ padding: 14px; }}
    .chain {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 8px; margin: 12px 0; }}
    .node {{ border: 1px solid #d7d4ca; border-radius: 6px; padding: 10px; background: #fbfbf8; min-width: 0; }}
    .node strong {{ display: block; font-size: 12px; color: #24231f; }}
    .node span {{ color: #5b5a55; font-size: 12px; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 7px 8px; border-top: 1px solid #ebe9e2; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ width: 170px; color: #55534d; font-weight: 600; }}
    ul {{ margin: 8px 0 0; padding-left: 18px; }}
    li {{ margin: 7px 0; }}
    code {{ background: #f0efe8; border: 1px solid #dddacf; border-radius: 4px; padding: 1px 4px; }}
    .badge {{ display: inline-block; margin: 2px 5px 2px 0; padding: 3px 7px; border-radius: 999px; background: #e8f1ed; border: 1px solid #bcd8ce; font-size: 12px; }}
    .pill {{ border-radius: 999px; padding: 2px 7px; font-size: 11px; border: 1px solid #d2d0c8; }}
    .resolved {{ background: #e5f5e9; border-color: #add4b6; }}
    .unresolved {{ background: #fff1df; border-color: #e0bf84; }}
    .muted {{ color: #68665f; }}
    .ceiling {{ color: #5b2a25; background: #fff2ec; border: 1px solid #ecc7ba; border-radius: 5px; padding: 8px 10px; margin-top: 12px; }}
    details {{ margin-top: 12px; border-top: 1px solid #ebe9e2; padding-top: 10px; }}
    summary {{ cursor: pointer; color: #45433e; font-weight: 600; }}
    pre {{ margin: 10px 0 0; padding: 12px; overflow: auto; max-height: 360px; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; background: #f7f7f4; border: 1px solid #e4e1d8; border-radius: 5px; }}
    @media (max-width: 860px) {{ main {{ grid-template-columns: 1fr; padding: 12px; }} header {{ padding: 22px 18px 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Microcosm Observatory</h1>
    <p>{html.escape(project_title)} is shown as an executable research prototype: local state, resolved pattern bindings, standard pressure, route, work transaction, events, and evidence drilldowns. Release remains unauthorized.</p>
  </header>
  <main>
    <section class="wide">
      <h2>Causal Chain</h2>
      <div class="content">
        <div class="chain">
          <div class="node"><strong>Project</strong><span>{html.escape(_safe_text(project_summary.get("project_id")))}</span></div>
          <div class="node"><strong>Catalog</strong><span>{html.escape(_safe_text((model.get("catalog_summary") or {}).get("file_count")))} files</span></div>
          <div class="node"><strong>Patterns</strong><span>{_badge_list([str(row.get("pattern_id")) for row in pattern_bindings if isinstance(row, dict) and row.get("pattern_id")])}</span></div>
          <div class="node"><strong>Standards</strong><span>{_badge_list([str(row.get("standard_id")) for row in standard_bindings if isinstance(row, dict) and row.get("standard_id")][:4])}</span></div>
          <div class="node"><strong>Route</strong><span>{html.escape(route_id)}</span></div>
          <div class="node"><strong>Work</strong><span>{html.escape(_safe_text(work.get("work_id") or "not yet created"))}</span></div>
          <div class="node"><strong>Events</strong><span>{len(events)} shown</span></div>
          <div class="node"><strong>Evidence</strong><span>{len(evidence)} refs</span></div>
        </div>
        <table>
          {row("Route", route_id)}
          {row("Authority", route.get("authority") or causal.get("authority_boundary"))}
          {row("Source mutation authorized", route.get("source_mutation_authorized") is True or work.get("source_files_mutated") is True)}
          {row("Release authorized", model.get("release_authorized") is True)}
          {row("Provider calls authorized", model.get("provider_calls_authorized") is True)}
        </table>
        <p class="ceiling">Evidence is drilldown. Receipts explain what happened after the chain is visible; they are not the cockpit. Release remains unauthorized.</p>
      </div>
    </section>

    <section>
      <h2>Resolved Pattern Bindings</h2>
      <div class="content">
        {binding_rows(pattern_bindings, "pattern_id")}
      </div>
    </section>

    <section>
      <h2>Standard Pressure</h2>
      <div class="content">
        {binding_rows(standard_bindings, "standard_id")}
      </div>
    </section>

    <section>
      <h2>Work Transaction</h2>
      <div class="content">
        <table>
          {row("Work id", work.get("work_id") or "not yet created")}
          {row("Status", work.get("status") or "not yet created")}
          {row("Route snapshot", work.get("route_id") or route_id)}
          {row("Transaction policy", work.get("transaction_policy"))}
          {row("State history", " -> ".join(state_history) if state_history else "not yet run")}
          {row("Event refs", ", ".join(event_ref_values))}
          {row("Evidence refs", ", ".join(evidence_ref_values))}
        </table>
      </div>
    </section>

    <section>
      <h2>Project Graph</h2>
      <div class="content">
        <table>
          {row("Nodes", graph.get("node_count"))}
          {row("Edges", graph.get("edge_count"))}
          {row("Graph ref", graph.get("graph_ref"))}
        </table>
        <h3>Key relations</h3>
        {_badge_list([str(value) for value in graph.get("key_relations", [])])}
      </div>
    </section>

    <section class="wide">
      <h2>Events and Evidence</h2>
      <div class="content">
        <h3>Event stream</h3>
        <table>
          <thead><tr><th>Event id</th><th>Span</th><th>Status</th><th>Evidence ref</th></tr></thead>
          <tbody>{event_rows(events)}</tbody>
        </table>
        <h3>Evidence drilldowns</h3>
        <table>
          <thead><tr><th>Evidence ref</th><th>Status</th><th>Replacement policy</th></tr></thead>
          <tbody>{evidence_rows(evidence)}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Kernel and Standards</h2>
      <div class="content">
        <table>
          {row("Pattern surface", kernel.get("pattern_surface_id"))}
          {row("Standard pressure", kernel.get("standard_pressure_surface_id"))}
          {row("Primitives", ", ".join([str(value) for value in kernel.get("primitive_names", [])]))}
        </table>
      </div>
    </section>

    <section>
      <h2>JSON Drilldowns</h2>
      <div class="content">
        <p class="muted">The endpoints remain stable for inspection, tests, and automation.</p>
        <ul>{endpoint_items}</ul>
        <details>
          <summary>Raw observatory model</summary>
          <pre>{dump(model)}</pre>
        </details>
      </div>
    </section>
  </main>
</body>
</html>
"""

    def serve(self, host: str, port: int, project: str | Path | None = None) -> ThreadingHTTPServer:
        shell = self
        project_path = Path(project).expanduser().resolve(strict=False) if project is not None else None

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status_code: int, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
                encoded = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _send_html(self, status_code: int, body: str) -> None:
                encoded = body.encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:
                path = urlparse(self.path).path
                if path == "/":
                    self._send_html(200, shell._observatory_html(project_path))
                elif path == "/status":
                    self._send(200, shell.status())
                elif path == "/kernel":
                    self._send(
                        200,
                        {
                            **architecture_kernel.load_kernel_manifest(shell.root),
                            "standard_pressure_surface": architecture_kernel.load_standard_pressure_surface(shell.root),
                        },
                    )
                elif path == "/project/status" and project_path is not None:
                    self._send(200, project_substrate.observe_project(project_path))
                elif path == "/project/architecture" and project_path is not None:
                    self._send(200, project_substrate.architecture_project(project_path))
                elif path == "/project/graph" and project_path is not None:
                    self._send(200, project_substrate.state_graph(project_path))
                elif path == "/project/catalog" and project_path is not None:
                    self._send(200, project_substrate.catalog_project(project_path))
                elif path == "/project/patterns" and project_path is not None:
                    self._send(200, project_substrate.discover_patterns(project_path))
                elif path == "/project/routes" and project_path is not None:
                    self._send(200, project_substrate.propose_routes(project_path))
                elif path == "/project/workitems" and project_path is not None:
                    self._send(
                        200,
                        {
                            "schema_version": "microcosm_project_workitems_view_v1",
                            "status": PASS,
                            "work_items": project_substrate._load_work_items(project_path),
                        },
                    )
                elif path == "/project/evidence" and project_path is not None:
                    self._send(200, project_substrate.list_evidence(project_path))
                elif path == "/project/observatory" and project_path is not None:
                    self._send(200, shell.project_observatory(project_path))
                elif path.startswith("/project/explain/") and project_path is not None:
                    self._send(200, project_substrate.explain_route(project_path, unquote(path.removeprefix("/project/explain/"))))
                elif path == "/organs":
                    self._send(200, {"schema_version": "microcosm_runtime_organs_v1", "organs": shell.organs()})
                elif path == "/patterns":
                    self._send(200, {"schema_version": "microcosm_runtime_patterns_v1", "patterns": shell.patterns()})
                elif path == "/routes":
                    self._send(200, {"schema_version": "microcosm_runtime_routes_v1", "routes": shell.routes()})
                elif path == "/workitems":
                    self._send(200, {"schema_version": "microcosm_runtime_workitems_v1", "workitems": shell.workitems()})
                elif path == "/evidence":
                    self._send(200, {"schema_version": "microcosm_runtime_evidence_v1", "evidence": shell.evidence()})
                elif path.startswith("/route/"):
                    self._send(200, shell.inspect_route(unquote(path.removeprefix("/route/"))))
                else:
                    self._send(404, {"status": "not_found", "path": path})

            def do_POST(self) -> None:
                path = urlparse(self.path).path
                if path == "/demo/run":
                    self._send(200, shell.run_demo())
                    return
                if path == "/project/work/run" and project_path is not None:
                    self._send(200, project_substrate.run_work(project_path))
                    return
                self._send(404, {"status": "not_found", "path": path})

        return ThreadingHTTPServer((host, port), Handler)


def _print_json(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not isinstance(payload, dict) or payload.get("status") in {None, PASS} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="microcosm-runtime")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("project", nargs="?", default=DEFAULT_PROJECT_REL)
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("project", nargs="?")
    subparsers.add_parser("patterns")
    subparsers.add_parser("kernel")
    route_parser = subparsers.add_parser("route")
    route_sub = route_parser.add_subparsers(dest="route_command")
    route_sub.add_parser("list")
    inspect_route = route_sub.add_parser("inspect")
    inspect_route.add_argument("route_id")
    work_parser = subparsers.add_parser("work")
    work_sub = work_parser.add_subparsers(dest="work_command")
    work_sub.add_parser("demo")
    evidence_parser = subparsers.add_parser("evidence")
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_sub.add_parser("list")
    inspect_evidence = evidence_sub.add_parser("inspect")
    inspect_evidence.add_argument("receipt_ref")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    shell = RuntimeShell()

    if args.command == "status":
        return _print_json(shell.status())
    if args.command == "run":
        return _print_json(shell.run_demo(args.project))
    if args.command == "patterns":
        return _print_json({"schema_version": "microcosm_runtime_patterns_v1", "patterns": shell.patterns()})
    if args.command == "kernel":
        return _print_json(
            {
                **architecture_kernel.load_kernel_manifest(shell.root),
                "standard_pressure_surface": architecture_kernel.load_standard_pressure_surface(shell.root),
            }
        )
    if args.command == "route":
        if args.route_command == "list":
            return _print_json({"schema_version": "microcosm_runtime_routes_v1", "routes": shell.routes()})
        if args.route_command == "inspect":
            return _print_json(shell.inspect_route(args.route_id))
    if args.command == "work":
        if args.work_command == "demo":
            return _print_json(shell.run_work_demo())
    if args.command == "evidence":
        if args.evidence_command == "list":
            return _print_json({"schema_version": "microcosm_runtime_evidence_v1", "evidence": shell.evidence()})
        if args.evidence_command == "inspect":
            return _print_json(shell.inspect_evidence(args.receipt_ref))
    if args.command == "serve":
        server = shell.serve(args.host, args.port, args.project)
        print(f"microcosm runtime shell listening on http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 130
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
