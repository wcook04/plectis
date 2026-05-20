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
                "run microcosm index <project>",
                "run microcosm route <project>",
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

    def _observatory_html(self, project_path: Path | None) -> str:
        status = self.status()
        project_payloads: dict[str, Any] = {}
        route_for_explain = ""
        if project_path is not None:
            architecture = project_substrate.architecture_project(project_path)
            catalog = project_substrate.catalog_project(project_path)
            patterns = project_substrate.discover_patterns(project_path)
            routes = project_substrate.propose_routes(project_path)
            route_rows = routes.get("routes", []) if isinstance(routes.get("routes"), list) else []
            if route_rows and isinstance(route_rows[0], dict):
                route_for_explain = str(route_rows[0].get("route_id") or "")
            explanation = (
                project_substrate.explain_route(project_path, route_for_explain)
                if route_for_explain
                else {"status": "not_found"}
            )
            project_payloads = {
                "architecture": architecture,
                "catalog": catalog,
                "patterns": patterns,
                "routes": routes,
                "workitems": {
                    "schema_version": "microcosm_project_workitems_view_v1",
                    "status": PASS,
                    "work_items": project_substrate._load_work_items(project_path),
                },
                "observe": project_substrate.observe_project(project_path),
                "evidence": project_substrate.list_evidence(project_path),
                "explanation": explanation,
            }

        def dump(payload: Any) -> str:
            return html.escape(json.dumps(payload, indent=2, sort_keys=True))

        project_title = project_path.name if project_path is not None else "public runtime"
        sections = [
            ("Status", status),
            (
                "Kernel",
                {
                    **architecture_kernel.load_kernel_manifest(self.root),
                    "standard_pressure_surface": architecture_kernel.load_standard_pressure_surface(self.root),
                },
            ),
        ]
        if project_payloads:
            sections.extend(
                [
                    ("Project Architecture", project_payloads["architecture"]),
                    ("Catalog", project_payloads["catalog"]),
                    ("Patterns", project_payloads["patterns"]),
                    ("Routes", project_payloads["routes"]),
                    ("Route Explanation", project_payloads["explanation"]),
                    ("Work", project_payloads["workitems"]),
                    ("Events", project_payloads["observe"]),
                    ("Evidence", project_payloads["evidence"]),
                ]
            )
        body = "\n".join(
            f"<section><h2>{html.escape(title)}</h2><pre>{dump(payload)}</pre></section>"
            for title, payload in sections
        )
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Microcosm Observatory</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; }}
    body {{ margin: 0; background: #f7f7f4; color: #171715; }}
    header {{ padding: 28px 32px 18px; border-bottom: 1px solid #d8d7d1; background: #ffffff; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    p {{ margin: 0; max-width: 900px; line-height: 1.45; color: #4b4a45; }}
    main {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; padding: 20px; }}
    section {{ background: #ffffff; border: 1px solid #dad8d0; border-radius: 6px; overflow: hidden; min-width: 0; }}
    h2 {{ margin: 0; padding: 12px 14px; font-size: 15px; background: #eceae3; border-bottom: 1px solid #dad8d0; }}
    pre {{ margin: 0; padding: 14px; overflow: auto; max-height: 420px; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }}
  </style>
</head>
<body>
  <header>
    <h1>Microcosm Observatory</h1>
    <p>{html.escape(project_title)} is shown as an executable research prototype: local state, architecture primitives, resolved pattern bindings, routes, work, events, and evidence drilldowns. Release remains unauthorized.</p>
  </header>
  <main>
    {body}
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
