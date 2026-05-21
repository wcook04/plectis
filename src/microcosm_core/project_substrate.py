from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from microcosm_core import architecture_kernel
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


PASS = "pass"
STATE_DIR = ".microcosm"
EVIDENCE_DIR = "evidence"
EVENT_STREAM = "events.jsonl"

IGNORE_DIRS = {
    ".git",
    STATE_DIR,
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
}

PACKAGE_MANIFESTS = {
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
}

SCRIPT_NAMES = {"Makefile", "justfile", "Taskfile.yml", "taskfile.yml"}
README_NAMES = {"README.md", "README.rst", "README.txt", "README"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".swift"}
DOC_SUFFIXES = {".md", ".rst", ".txt"}


def _project_name(project: Path) -> str:
    return project.resolve(strict=False).name or "project"


def _state_dir(project: Path) -> Path:
    return project / STATE_DIR


def _evidence_dir(project: Path) -> Path:
    return _state_dir(project) / EVIDENCE_DIR


def _project_relative(project: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(project.resolve(strict=False)).as_posix()
    except ValueError:
        return path.name


def _read_project_json(project: Path, rel: str) -> dict[str, Any]:
    path = _state_dir(project) / rel
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


def _append_event(project: Path, event: dict[str, Any]) -> None:
    event_path = _state_dir(project) / EVENT_STREAM
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_evidence(project: Path, action_id: str, payload: dict[str, Any]) -> str:
    ref = f"{EVIDENCE_DIR}/{action_id}.json"
    evidence_path = _state_dir(project) / ref
    stable_ref = f"{STATE_DIR}/{ref}"
    previous_sha256 = _sha256_file(evidence_path) if evidence_path.is_file() else None
    evidence_payload = dict(payload)
    evidence_payload.setdefault("evidence_ref", stable_ref)
    evidence_payload["evidence_replacement"] = {
        "stable_ref": stable_ref,
        "policy": "stable_ref_latest_body",
        "previous_sha256": previous_sha256,
        "replacement_recorded": previous_sha256 is not None,
        "append_only_event_history_ref": f"{STATE_DIR}/{EVENT_STREAM}",
    }
    write_json_atomic(evidence_path, evidence_payload)
    return stable_ref


def _base_payload(schema_version: str, project: Path) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "created_at": utc_now(),
        "project_id": _project_name(project),
        "project_ref": ".",
        "state_ref": STATE_DIR,
        "status": PASS,
        "release_authorized": False,
        "receipts_are_drilldown_evidence": True,
    }


def _event(project: Path, span: str, status: str, **fields: Any) -> dict[str, Any]:
    rows = _read_jsonl(_state_dir(project) / EVENT_STREAM)
    event = {
        "event_id": f"evt_{len(rows) + 1:04d}",
        "created_at": utc_now(),
        "span": span,
        "status": status,
        "project_id": _project_name(project),
    }
    event.update(fields)
    return event


def _classify_file(rel: str, path: Path) -> str:
    name = path.name
    parts = set(path.parts)
    if name in README_NAMES:
        return "readme"
    if name in PACKAGE_MANIFESTS:
        return "package_manifest"
    if name in SCRIPT_NAMES or path.suffix == ".sh":
        return "script"
    if "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    if "docs" in parts or path.suffix in DOC_SUFFIXES:
        return "docs"
    if "examples" in parts:
        return "example"
    if "src" in parts or path.suffix in SOURCE_SUFFIXES:
        return "source"
    if path.suffix in {".toml", ".json", ".yaml", ".yml", ".ini", ".cfg"}:
        return "config"
    return "other"


def _walk_project(project: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(project.rglob("*")):
        rel = _project_relative(project, path)
        if any(part in IGNORE_DIRS for part in Path(rel).parts):
            continue
        if path.is_dir():
            continue
        if path.is_symlink():
            continue
        rows.append(
            {
                "path": rel,
                "name": path.name,
                "suffix": path.suffix,
                "role": _classify_file(rel, Path(rel)),
                "bytes": path.stat().st_size,
            }
        )
    return rows


def _rows_by_role(files: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_role: dict[str, list[str]] = {}
    for row in files:
        role = str(row.get("role") or "other")
        by_role.setdefault(role, []).append(str(row.get("path") or ""))
    return {key: sorted(value) for key, value in sorted(by_role.items())}


def _write_manifest(project: Path) -> dict[str, Any]:
    manifest = _base_payload("microcosm_project_manifest_v1", project)
    manifest.update(
        {
            "local_state_contract": "project_owned_state_only",
            "user_input": "project_folder",
            "useful_output": [
                "catalog",
                "patterns",
                "routes",
                "work_transactions",
                "event_stream",
                "evidence_refs",
            ],
            "state_files": [
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
                f"{STATE_DIR}/explanations/",
            ],
            "authority_ceiling": {
                "live_task_ledger_mutation_authorized": False,
                "provider_calls_authorized": False,
                "release_authorized": False,
                "source_files_mutated": False,
            },
        }
    )
    write_json_atomic(_state_dir(project) / "project_manifest.json", manifest)
    architecture_kernel.write_project_architecture(project)
    return manifest


def init_project(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    project.mkdir(parents=True, exist_ok=True)
    _state_dir(project).mkdir(parents=True, exist_ok=True)
    _evidence_dir(project).mkdir(parents=True, exist_ok=True)
    manifest = _write_manifest(project)
    event = _event(project, "project.init", PASS, evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/init.json")
    _append_event(project, event)
    evidence = dict(manifest)
    evidence["event_ref"] = f"{STATE_DIR}/{EVENT_STREAM}"
    evidence_ref = _write_evidence(project, "init", evidence)
    return {
        **_base_payload("microcosm_project_init_result_v1", project),
        "manifest_ref": f"{STATE_DIR}/project_manifest.json",
        "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "evidence_ref": evidence_ref,
    }


def index_project(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    if not (_state_dir(project) / "project_manifest.json").is_file():
        init_project(project)
    files = _walk_project(project)
    by_role = _rows_by_role(files)
    catalog = {
        **_base_payload("microcosm_project_catalog_v1", project),
        "file_count": len(files),
        "role_counts": {role: len(paths) for role, paths in by_role.items()},
        "roles": by_role,
        "files": files,
        "detected_package_manifests": by_role.get("package_manifest", []),
        "detected_source_roots": sorted(
            {Path(path).parts[0] for path in by_role.get("source", []) if Path(path).parts}
        ),
        "detected_test_roots": sorted(
            {Path(path).parts[0] for path in by_role.get("test", []) if Path(path).parts}
        ),
    }
    write_json_atomic(_state_dir(project) / "catalog.json", catalog)
    architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.index",
        PASS,
        file_count=len(files),
        catalog_ref=f"{STATE_DIR}/catalog.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/index.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(project, "index", {**catalog, "event_id": event["event_id"]})
    return {
        **_base_payload("microcosm_project_index_result_v1", project),
        "catalog_ref": f"{STATE_DIR}/catalog.json",
        "file_count": len(files),
        "role_counts": catalog["role_counts"],
        "evidence_ref": evidence_ref,
    }


def catalog_project(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = _read_project_json(project, "catalog.json")
    if not catalog:
        index_project(project)
        catalog = _read_project_json(project, "catalog.json")
    return {**catalog, "schema_version": "microcosm_project_catalog_view_v1", "status": PASS}


def discover_patterns(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = catalog_project(project)
    roles = catalog.get("roles", {}) if isinstance(catalog.get("roles"), dict) else {}
    pattern_surface = architecture_kernel.pattern_surface_contract()
    standard_refs = pattern_surface.get("binding_standard_refs", [])
    standard_refs = standard_refs if isinstance(standard_refs, list) else []

    def present(role: str) -> bool:
        value = roles.get(role, [])
        return isinstance(value, list) and bool(value)

    candidates: list[dict[str, Any]] = []
    checks = [
        ("repo_has_readme", "README-first onboarding surface", "readme"),
        ("repo_has_package_manifest", "installable or runnable package metadata", "package_manifest"),
        ("repo_has_source_core", "visible source core", "source"),
        ("repo_has_tests", "behavior tests visible", "test"),
        ("repo_has_docs", "documentation surface visible", "docs"),
        ("repo_has_examples", "example usage surface visible", "example"),
        ("repo_has_scripts", "operator scripts or admin commands visible", "script"),
    ]
    for pattern_id, title, role in checks:
        refs = roles.get(role, []) if isinstance(roles.get(role), list) else []
        candidates.append(
            {
                "pattern_id": pattern_id,
                "title": title,
                "status": PASS if refs else "missing",
                "grounded_refs": refs[:12],
                "source": "project_index",
                "pattern_surface_id": pattern_surface.get("surface_id"),
                "state_ref": f"{STATE_DIR}/patterns.json::{pattern_id}",
                "evidence_ref": pattern_surface.get("evidence_ref", f"{STATE_DIR}/{EVIDENCE_DIR}/patterns.json"),
                "standard_refs": standard_refs,
                "authority_boundary": "public_pattern_observation_not_doctrine_promotion",
            }
        )
    payload = {
        **_base_payload("microcosm_project_patterns_v1", project),
        "pattern_surface": pattern_surface,
        "patterns": candidates,
        "passing_pattern_count": sum(1 for row in candidates if row["status"] == PASS),
        "missing_pattern_count": sum(1 for row in candidates if row["status"] != PASS),
    }
    write_json_atomic(_state_dir(project) / "patterns.json", payload)
    architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.patterns",
        PASS,
        passing_pattern_count=payload["passing_pattern_count"],
        patterns_ref=f"{STATE_DIR}/patterns.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/patterns.json",
    )
    _append_event(project, event)
    payload["evidence_ref"] = _write_evidence(project, "patterns", {**payload, "event_id": event["event_id"]})
    return payload


def propose_routes(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = catalog_project(project)
    patterns = discover_patterns(project)
    roles = catalog.get("roles", {}) if isinstance(catalog.get("roles"), dict) else {}
    pattern_surface = architecture_kernel.pattern_surface_contract()

    routes: list[dict[str, Any]] = []

    def add(route_id: str, title: str, intent: str, refs: list[str], action: str) -> None:
        pattern_refs = {
            "readme_onboarding_route": ["repo_has_readme"],
            "package_runtime_route": ["repo_has_package_manifest"],
            "source_core_route": ["repo_has_source_core"],
            "test_behavior_route": ["repo_has_tests"],
            "missing_tests_route": ["repo_has_tests"],
            "docs_route": ["repo_has_docs"],
        }.get(route_id, [])
        routes.append(
            {
                "route_id": route_id,
                "title": title,
                "intent": intent,
                "grounded_refs": refs[:12],
                "action": action,
                "pattern_refs": pattern_refs,
                "pattern_surface_id": pattern_surface.get("surface_id"),
                "pattern_resolution_ref": pattern_surface.get("state_ref", f"{STATE_DIR}/patterns.json"),
                "standard_pressure_refs": architecture_kernel.standard_pressure_refs_for_route({"route_id": route_id}),
                "kernel_primitive_refs": ["catalog", "pattern", "route", "work", "event", "evidence"],
                "route_definition_ref": f"{STATE_DIR}/routes.json::{route_id}",
                "explain_command": f"microcosm explain <project> {route_id}",
                "authority": "project_local_projection_not_source_authority",
                "claims_source_authority": False,
                "source_mutation_authorized": False,
            }
        )

    readme_refs = roles.get("readme", []) if isinstance(roles.get("readme"), list) else []
    source_refs = roles.get("source", []) if isinstance(roles.get("source"), list) else []
    test_refs = roles.get("test", []) if isinstance(roles.get("test"), list) else []
    package_refs = roles.get("package_manifest", []) if isinstance(roles.get("package_manifest"), list) else []
    docs_refs = roles.get("docs", []) if isinstance(roles.get("docs"), list) else []

    if readme_refs:
        add("readme_onboarding_route", "Inspect README onboarding", "summarize public first-run path", readme_refs, "inspect")
    if package_refs:
        add("package_runtime_route", "Inspect package/runtime metadata", "find install and run surfaces", package_refs, "inspect")
    if source_refs:
        add("source_core_route", "Inspect source core", "locate primary implementation surfaces", source_refs, "inspect")
    if test_refs:
        add("test_behavior_route", "Run or inspect behavior tests", "find executable behavior checks", test_refs, "simulate")
    else:
        add("missing_tests_route", "Add behavior-test route", "project lacks visible tests", source_refs or readme_refs, "plan")
    if docs_refs:
        add("docs_route", "Inspect docs", "find user-facing explanatory surface", docs_refs, "inspect")

    payload = {
        **_base_payload("microcosm_project_routes_v1", project),
        "route_count": len(routes),
        "routes": routes,
        "pattern_summary": {
            "passing_pattern_count": patterns["passing_pattern_count"],
            "missing_pattern_count": patterns["missing_pattern_count"],
        },
    }
    write_json_atomic(_state_dir(project) / "routes.json", payload)
    architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.route",
        PASS,
        route_count=len(routes),
        routes_ref=f"{STATE_DIR}/routes.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/routes.json",
    )
    _append_event(project, event)
    payload["evidence_ref"] = _write_evidence(project, "routes", {**payload, "event_id": event["event_id"]})
    return payload


def _load_work_items(project: Path) -> list[dict[str, Any]]:
    payload = _read_project_json(project, "work_items.json")
    rows = payload.get("work_items", [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _write_work_items(project: Path, rows: list[dict[str, Any]]) -> None:
    payload = {
        **_base_payload("microcosm_project_work_items_v1", project),
        "work_item_count": len(rows),
        "work_items": rows,
    }
    write_json_atomic(_state_dir(project) / "work_items.json", payload)


def create_work(project_path: str | Path, route_id: str | None = None) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    route_payload = propose_routes(project)
    routes = route_payload.get("routes", [])
    route_rows = [row for row in routes if isinstance(row, dict)]
    if route_id:
        selected = next((row for row in route_rows if row.get("route_id") == route_id), None)
    else:
        selected = route_rows[0] if route_rows else None
    if not selected:
        return {
            **_base_payload("microcosm_project_work_create_result_v1", project),
            "status": "blocked",
            "reason": "route_not_found",
            "route_id": route_id,
        }
    rows = _load_work_items(project)
    work_id = f"work_{len(rows) + 1:04d}"
    contracts = architecture_kernel.work_contracts_for_route(selected, work_id)
    row = {
        "work_id": work_id,
        "route_id": selected["route_id"],
        "status": "created",
        "transaction_state": "created",
        "created_at": utc_now(),
        "grounded_refs": selected.get("grounded_refs", []),
        "route_snapshot": selected,
        "transaction_policy": "simulate_project_local_only",
        "workflow_definition_ref": f"{STATE_DIR}/routes.json::{selected['route_id']}",
        "workflow_execution_ref": f"{STATE_DIR}/work_items.json::{work_id}",
        "satisfaction_contract": contracts["satisfaction_contract"],
        "integration_contract": contracts["integration_contract"],
        "residual_policy": contracts["residual_policy"],
        "event_refs": [],
        "evidence_refs": [],
        "state_history": [
            {
                "state": "created",
                "span": "work.create",
                "created_at": utc_now(),
                "note": "Work transaction record created from a route snapshot.",
            },
            {
                "state": "selected",
                "span": "work.create",
                "created_at": utc_now(),
                "note": "Route selected for deterministic local simulation.",
            },
            {
                "state": "planned",
                "span": "work.create",
                "created_at": utc_now(),
                "note": "Source mutation is not authorized; run step will simulate governance only.",
            },
        ],
        "source_files_mutated": False,
    }
    rows.append(row)
    _write_work_items(project, rows)
    architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "work.create",
        PASS,
        work_id=work_id,
        route_id=selected["route_id"],
        work_items_ref=f"{STATE_DIR}/work_items.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/work_create_{work_id}.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(
        project,
        f"work_create_{work_id}",
        {
            **_base_payload("microcosm_project_work_create_receipt_v1", project),
            "event_id": event["event_id"],
            "work_item": row,
            "work_id": work_id,
            "route_id": selected["route_id"],
        },
    )
    row["event_refs"].append(
        {
            "event_id": event["event_id"],
            "span": event["span"],
            "status": event["status"],
        }
    )
    row["evidence_refs"].append(evidence_ref)
    _write_work_items(project, rows)
    return {
        **_base_payload("microcosm_project_work_create_result_v1", project),
        "work_id": work_id,
        "route_id": selected["route_id"],
        "work_items_ref": f"{STATE_DIR}/work_items.json",
        "evidence_ref": evidence_ref,
    }


def run_work(project_path: str | Path, work_id: str | None = None) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    rows = _load_work_items(project)
    if not rows:
        created = create_work(project)
        rows = _load_work_items(project)
        work_id = str(created.get("work_id") or "")
    selected = next((row for row in rows if row.get("work_id") == work_id), None) if work_id else None
    if selected is None:
        selected = next((row for row in rows if row.get("status") != "closed"), rows[-1] if rows else None)
    if selected is None:
        return {
            **_base_payload("microcosm_project_work_run_result_v1", project),
            "status": "blocked",
            "reason": "work_item_not_found",
            "work_id": work_id,
        }
    if selected.get("status") == "closed" and isinstance(selected.get("closeout"), dict):
        history = selected.get("state_history", [])
        state_machine = [
            str(row.get("state"))
            for row in history
            if isinstance(row, dict) and row.get("state")
        ]
        evidence_refs = selected.get("evidence_refs", [])
        latest_evidence_ref = evidence_refs[-1] if isinstance(evidence_refs, list) and evidence_refs else None
        return {
            **_base_payload("microcosm_project_work_run_result_v1", project),
            "work_id": selected["work_id"],
            "route_id": selected["route_id"],
            "transaction_status": PASS,
            "idempotent_replay": True,
            "state_machine": state_machine,
            "work_items_ref": f"{STATE_DIR}/work_items.json",
            "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
            "evidence_ref": latest_evidence_ref,
        }
    contracts = architecture_kernel.work_contracts_for_route(
        selected.get("route_snapshot", {"route_id": selected.get("route_id")}),
        str(selected.get("work_id") or ""),
    )
    selected.setdefault("satisfaction_contract", contracts["satisfaction_contract"])
    selected.setdefault("integration_contract", contracts["integration_contract"])
    selected.setdefault("residual_policy", contracts["residual_policy"])
    selected.setdefault("event_refs", [])
    selected.setdefault("evidence_refs", [])
    selected["status"] = "closed"
    selected["transaction_state"] = "closed"
    selected["closed_at"] = utc_now()
    history = selected.get("state_history", [])
    if not isinstance(history, list):
        history = []
    history.extend(
        [
            {
                "state": "executed_simulation",
                "span": "work.run",
                "created_at": utc_now(),
                "note": "Executed deterministic project-local simulation over route snapshot.",
            },
            {
                "state": "closed",
                "span": "work.run",
                "created_at": utc_now(),
                "note": "Closed with generated evidence and no source mutation.",
            },
        ]
    )
    selected["state_history"] = history
    selected["result"] = {
        "status": PASS,
        "summary": "Simulated a governed local transaction over project catalog state.",
        "definition_execution_separated": True,
        "workflow_definition_ref": selected.get("workflow_definition_ref"),
        "workflow_execution_ref": selected.get("workflow_execution_ref"),
        "source_files_mutated": False,
    }
    selected["closeout"] = {
        "status": PASS,
        "satisfaction_contract_met": True,
        "integration_contract_met": True,
        "residuals": [],
        "next_actions": [
            {
                "action_id": "inspect_route_explanation",
                "command": f"microcosm explain <project> {selected['route_id']}",
            },
            {
                "action_id": "inspect_event_stream",
                "command": "microcosm observe <project>",
            },
        ],
        "authority_boundary": "project_local_closeout_not_global_doctrine_promotion",
    }
    _write_work_items(project, rows)
    architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "work.run",
        PASS,
        work_id=selected["work_id"],
        route_id=selected["route_id"],
        work_items_ref=f"{STATE_DIR}/work_items.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/work_run_{selected['work_id']}.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(
        project,
        f"work_run_{selected['work_id']}",
        {
            **_base_payload("microcosm_project_work_run_receipt_v1", project),
            "event_id": event["event_id"],
            "work_item": selected,
            "work_id": selected["work_id"],
            "route_id": selected["route_id"],
            "transaction_status": PASS,
        },
    )
    event_row = {
        "event_id": event["event_id"],
        "span": event["span"],
        "status": event["status"],
    }
    if isinstance(selected.get("event_refs"), list):
        selected["event_refs"].append(event_row)
    if isinstance(selected.get("evidence_refs"), list):
        selected["evidence_refs"].append(evidence_ref)
    selected["closeout"]["event_ref"] = f"{STATE_DIR}/{EVENT_STREAM}::{event['event_id']}"
    selected["closeout"]["evidence_ref"] = evidence_ref
    _write_work_items(project, rows)
    return {
        **_base_payload("microcosm_project_work_run_result_v1", project),
        "work_id": selected["work_id"],
        "route_id": selected["route_id"],
        "transaction_status": PASS,
        "state_machine": ["created", "selected", "planned", "executed_simulation", "closed"],
        "work_items_ref": f"{STATE_DIR}/work_items.json",
        "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "evidence_ref": evidence_ref,
    }


def observe_project(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    architecture_kernel.write_project_architecture(project)
    events = _read_jsonl(_state_dir(project) / EVENT_STREAM)
    spans: dict[str, int] = {}
    for row in events:
        span = str(row.get("span") or "unknown")
        spans[span] = spans.get(span, 0) + 1
    return {
        **_base_payload("microcosm_project_observe_result_v1", project),
        "event_count": len(events),
        "spans": spans,
        "events": events[-20:],
        "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "architecture_ref": f"{STATE_DIR}/architecture.json",
        "state_index_ref": f"{STATE_DIR}/state_index.json",
        "graph_ref": f"{STATE_DIR}/graph.json",
    }


def architecture_project(project_path: str | Path) -> dict[str, Any]:
    return architecture_kernel.write_project_architecture(project_path)


def state_graph(project_path: str | Path) -> dict[str, Any]:
    architecture_kernel.write_project_architecture(project_path)
    return architecture_kernel.build_graph(project_path)


def explain_route(project_path: str | Path, route_id: str) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    if not (_state_dir(project) / "routes.json").is_file():
        propose_routes(project)
    explanation = architecture_kernel.explain_route(project, route_id)
    if explanation.get("status") != PASS:
        return explanation
    event = _event(
        project,
        "project.explain",
        PASS,
        route_id=route_id,
        explanation_ref=f"{STATE_DIR}/explanations/{route_id}.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/explain_{route_id}.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(project, f"explain_{route_id}", {**explanation, "event_id": event["event_id"]})
    explanation["event_id"] = event["event_id"]
    explanation["evidence_ref"] = evidence_ref
    write_json_atomic(_state_dir(project) / "explanations" / f"{route_id}.json", explanation)
    architecture_kernel.write_project_architecture(project)
    return explanation


def list_evidence(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    rows: list[dict[str, Any]] = []
    for path in sorted(_evidence_dir(project).glob("*.json")):
        payload = _read_project_json(project, f"{EVIDENCE_DIR}/{path.name}")
        rows.append(
            {
                "evidence_ref": f"{STATE_DIR}/{EVIDENCE_DIR}/{path.name}",
                "schema_version": payload.get("schema_version"),
                "status": payload.get("status", "unknown"),
                "project_id": payload.get("project_id", _project_name(project)),
                "created_at": payload.get("created_at"),
                "replacement_policy": (
                    payload.get("evidence_replacement", {}).get("policy")
                    if isinstance(payload.get("evidence_replacement"), dict)
                    else None
                ),
            }
        )
    return {
        **_base_payload("microcosm_project_evidence_list_v1", project),
        "evidence_count": len(rows),
        "evidence": rows,
    }


def compile_project(project_path: str | Path) -> dict[str, Any]:
    """Run the safe public substrate loop over a user-owned project."""
    project = Path(project_path).expanduser().resolve(strict=False)
    if not (_state_dir(project) / "project_manifest.json").is_file():
        init_project(project)
    index_result = index_project(project)
    catalog = catalog_project(project)
    architecture = architecture_project(project)
    patterns = discover_patterns(project)
    routes = propose_routes(project)
    route_rows = [
        row for row in routes.get("routes", []) if isinstance(row, dict)
    ]
    selected_route = next(
        (row for row in route_rows if row.get("route_id") == "readme_onboarding_route"),
        route_rows[0] if route_rows else {},
    )
    route_id = str(selected_route.get("route_id") or "")
    explanation = explain_route(project, route_id) if route_id else {}
    work_result = run_work(project)
    observed = observe_project(project)
    graph = state_graph(project)
    evidence = list_evidence(project)
    work_id = work_result.get("work_id")
    state_files = [
        f"{STATE_DIR}/catalog.json",
        f"{STATE_DIR}/patterns.json",
        f"{STATE_DIR}/routes.json",
        f"{STATE_DIR}/work_items.json",
        f"{STATE_DIR}/{EVENT_STREAM}",
        f"{STATE_DIR}/evidence/",
        f"{STATE_DIR}/graph.json",
        f"{STATE_DIR}/explanations/",
    ]
    return {
        **_base_payload("microcosm_project_compile_result_v1", project),
        "headline": "repo -> .microcosm",
        "what_happened": [
            f"created or reused {STATE_DIR}/",
            f"indexed {index_result.get('file_count', 0)} files",
            f"detected {patterns.get('passing_pattern_count', 0)} passing patterns",
            f"opened {routes.get('route_count', 0)} routes",
            f"explained {route_id}" if route_id else "no route available to explain",
            f"ran {work_id}" if work_id else "no work item available",
            f"emitted {observed.get('event_count', 0)} events",
            f"wrote {evidence.get('evidence_count', 0)} evidence refs",
        ],
        "project_ref": ".",
        "state_ref": STATE_DIR,
        "state_files": state_files,
        "file_count": index_result.get("file_count", 0),
        "role_counts": catalog.get("role_counts", {}),
        "primitive_ids": architecture.get("primitive_ids", []),
        "passing_pattern_count": patterns.get("passing_pattern_count", 0),
        "route_count": routes.get("route_count", 0),
        "route_ids": [str(row.get("route_id")) for row in route_rows if row.get("route_id")],
        "selected_route_id": route_id,
        "resolved_pattern_refs": explanation.get("pattern_refs", []),
        "resolved_standard_pressure_refs": explanation.get("standard_pressure_refs", []),
        "work_id": work_id,
        "transaction_status": work_result.get("transaction_status"),
        "idempotent_replay": work_result.get("idempotent_replay", False),
        "event_count": observed.get("event_count", 0),
        "evidence_count": evidence.get("evidence_count", 0),
        "graph_summary": {
            "node_count": graph.get("node_count", 0),
            "edge_count": graph.get("edge_count", 0),
            "graph_ref": f"{STATE_DIR}/graph.json",
        },
        "open_observatory": "microcosm serve <project> --host 127.0.0.1 --port 8765",
        "source_files_mutated": False,
        "authority_ceiling": {
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutated": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": (
            "Compile builds project-local public substrate state only. It does not "
            "authorize release, hosting, provider calls, source mutation, private-data "
            "equivalence, live Task Ledger mutation, or production readiness."
        ),
    }


def inspect_evidence(project_path: str | Path, evidence_ref: str) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    rel = evidence_ref.removeprefix(f"{STATE_DIR}/")
    payload = _read_project_json(project, rel)
    if not payload:
        return {
            **_base_payload("microcosm_project_evidence_card_v1", project),
            "status": "not_found",
            "evidence_ref": evidence_ref,
        }
    safe_keys = {
        "schema_version",
        "status",
        "project_id",
        "project_ref",
        "state_ref",
        "created_at",
        "route_id",
        "work_id",
        "event_id",
        "file_count",
        "role_counts",
        "release_authorized",
        "evidence_replacement",
    }
    return {
        **_base_payload("microcosm_project_evidence_card_v1", project),
        "evidence_ref": evidence_ref,
        "evidence": {key: payload.get(key) for key in safe_keys if key in payload},
        "body_redacted": True,
    }


def _print_json(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not isinstance(payload, dict) or payload.get("status") in {None, PASS} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="microcosm-project")
    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("project")
    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("project")
    catalog_parser = subparsers.add_parser("catalog")
    catalog_parser.add_argument("project")
    architecture_parser = subparsers.add_parser("architecture")
    architecture_parser.add_argument("project")
    patterns_parser = subparsers.add_parser("patterns")
    patterns_parser.add_argument("project")
    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("project")
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("project")
    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("project")
    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("project")
    explain_parser.add_argument("route_id")
    work_parser = subparsers.add_parser("work")
    work_sub = work_parser.add_subparsers(dest="work_command")
    create_parser = work_sub.add_parser("create")
    create_parser.add_argument("project")
    create_parser.add_argument("--route")
    run_parser = work_sub.add_parser("run")
    run_parser.add_argument("project")
    run_parser.add_argument("--work-id")
    observe_parser = subparsers.add_parser("observe")
    observe_parser.add_argument("project")
    evidence_parser = subparsers.add_parser("evidence")
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_list = evidence_sub.add_parser("list")
    evidence_list.add_argument("project")
    evidence_inspect = evidence_sub.add_parser("inspect")
    evidence_inspect.add_argument("project")
    evidence_inspect.add_argument("evidence_ref")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return _print_json(init_project(args.project))
    if args.command == "index":
        return _print_json(index_project(args.project))
    if args.command == "catalog":
        return _print_json(catalog_project(args.project))
    if args.command == "architecture":
        return _print_json(architecture_project(args.project))
    if args.command == "patterns":
        return _print_json(discover_patterns(args.project))
    if args.command == "route":
        return _print_json(propose_routes(args.project))
    if args.command == "compile":
        return _print_json(compile_project(args.project))
    if args.command == "graph":
        return _print_json(state_graph(args.project))
    if args.command == "explain":
        return _print_json(explain_route(args.project, args.route_id))
    if args.command == "work":
        if args.work_command == "create":
            return _print_json(create_work(args.project, args.route))
        if args.work_command == "run":
            return _print_json(run_work(args.project, args.work_id))
    if args.command == "observe":
        return _print_json(observe_project(args.project))
    if args.command == "evidence":
        if args.evidence_command == "list":
            return _print_json(list_evidence(args.project))
        if args.evidence_command == "inspect":
            return _print_json(inspect_evidence(args.project, args.evidence_ref))
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
