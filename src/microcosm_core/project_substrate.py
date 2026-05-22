from __future__ import annotations

import argparse
import ast
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
PYTHON_LENS_STATE = "python_lens.json"
STD_PYTHON_NAVIGATION_LADDER = [
    "module_docs",
    "file_card",
    "symbol_capsule",
    "graph_context",
    "source_span",
]
PROBE_DISPOSITION_OUTCOMES = [
    "file_local_defect",
    "standard_amendment_candidate",
    "nothing_to_refine",
]
ROUTE_UTILITY_DISPOSITION_OUTCOMES = [
    "local_projection_defect",
    "local_source_or_test_defect",
    "macro_standard_amendment_candidate",
    "nothing_to_refine",
]


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
                f"{STATE_DIR}/{PYTHON_LENS_STATE}",
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


def _project_catalog_payload(project: Path) -> dict[str, Any]:
    files = _walk_project(project)
    by_role = _rows_by_role(files)
    return {
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


def index_project(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
    if not (_state_dir(project) / "project_manifest.json").is_file():
        init_project(project)
    catalog = _project_catalog_payload(project)
    write_json_atomic(_state_dir(project) / "catalog.json", catalog)
    architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.index",
        PASS,
        file_count=catalog["file_count"],
        catalog_ref=f"{STATE_DIR}/catalog.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/index.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(project, "index", {**catalog, "event_id": event["event_id"]})
    return {
        **_base_payload("microcosm_project_index_result_v1", project),
        "catalog_ref": f"{STATE_DIR}/catalog.json",
        "file_count": catalog["file_count"],
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


def _read_text_prefix(path: Path, limit: int | None = 20000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text if limit is None else text[:limit]
    except OSError:
        return ""


def _python_lens_role(row: dict[str, Any]) -> str:
    rel = str(row.get("path") or "")
    path = Path(rel)
    parts = set(path.parts)
    name = path.name
    if name == "__init__.py":
        return "package_init"
    if name == "conftest.py":
        return "test_support"
    if "tests" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test_module"
    if "examples" in parts:
        return "example_module"
    if "scripts" in parts or "bin" in parts:
        return "script"
    if "src" in parts:
        return "source_module"
    return "python_module"


def _python_package_root(rel: str) -> str | None:
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == "src" and parts[-1] == "__init__.py":
        return f"src/{parts[1]}"
    if len(parts) >= 2 and parts[-1] == "__init__.py":
        return parts[0]
    return None


def _python_route(route_id: str, title: str, refs: list[str], readiness: str) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "title": title,
        "readiness": readiness,
        "grounded_refs": refs[:12],
        "source_mutation_authorized": False,
        "provider_calls_authorized": False,
        "authority": "project_local_python_route_lens_not_static_analysis_authority",
    }


def _python_symbol_kind(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_function"
    return "function"


def _python_span_projection(rel: str, text: str) -> dict[str, Any]:
    line_count = max(1, len(text.splitlines()))
    module_span = {
        "span_id": f"{rel}::module",
        "path": rel,
        "symbol_name": "<module>",
        "symbol_kind": "module",
        "line_start": 1,
        "line_end": line_count,
        "depth_band": "source_span",
        "body_redacted": True,
        "authority": "source_span_locator_not_source_body_or_correctness_authority",
    }
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "parse_status": "syntax_error",
            "module_has_docstring": False,
            "source_span_rows": [module_span],
            "symbol_capsule_rows": [],
            "import_edges": [],
            "parse_error": {
                "path": rel,
                "line": exc.lineno,
                "message": exc.msg,
                "body_redacted": True,
            },
        }

    source_span_rows = [module_span]
    symbol_capsule_rows: list[dict[str, Any]] = []

    def visit_scope(node: ast.AST, parents: list[str]) -> None:
        body = getattr(node, "body", [])
        for child in body if isinstance(body, list) else []:
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = ".".join([*parents, child.name])
                line_start = int(getattr(child, "lineno", 1))
                line_end = int(getattr(child, "end_lineno", line_start))
                symbol_kind = _python_symbol_kind(child)
                span_id = f"{rel}::{qualname}"
                source_span_rows.append(
                    {
                        "span_id": span_id,
                        "path": rel,
                        "symbol_name": qualname,
                        "symbol_kind": symbol_kind,
                        "line_start": line_start,
                        "line_end": line_end,
                        "depth_band": "source_span",
                        "body_redacted": True,
                        "authority": "source_span_locator_not_source_body_or_correctness_authority",
                    }
                )
                symbol_capsule_rows.append(
                    {
                        "symbol_id": span_id,
                        "path": rel,
                        "symbol_name": qualname,
                        "symbol_kind": symbol_kind,
                        "source_span_ref": span_id,
                        "depth_band": "symbol_capsule",
                        "body_redacted": True,
                    }
                )
                visit_scope(child, [*parents, child.name])
            else:
                visit_scope(child, parents)

    visit_scope(tree, [])
    import_edges: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_edges.append(
                    {
                        "path": rel,
                        "edge": "imports",
                        "target": alias.name,
                        "line": int(getattr(node, "lineno", 1)),
                        "depth_band": "graph_context",
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * int(getattr(node, "level", 0))
            target = f"{prefix}{node.module or ''}"
            import_edges.append(
                {
                    "path": rel,
                    "edge": "imports_from",
                    "target": target,
                    "line": int(getattr(node, "lineno", 1)),
                    "depth_band": "graph_context",
                }
            )
    return {
        "parse_status": "parsed",
        "module_has_docstring": ast.get_docstring(tree) is not None,
        "source_span_rows": source_span_rows,
        "symbol_capsule_rows": symbol_capsule_rows,
        "import_edges": import_edges[:48],
        "parse_error": None,
    }


def _python_route_probe_tasks(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    depth_by_route = {
        "python_package_metadata_route": "file_card",
        "python_source_core_route": "source_span",
        "python_test_behavior_route": "source_span",
        "python_entrypoint_route": "source_span",
    }
    prompts_by_route = {
        "python_package_metadata_route": "Find the package metadata source for this project.",
        "python_source_core_route": "Find the primary Python source span for this project.",
        "python_test_behavior_route": "Find the source span that proves Python behavior is tested.",
        "python_entrypoint_route": "Find the source span for a runnable Python entrypoint, if this project has one.",
    }
    tasks: list[dict[str, Any]] = []
    for row in route_rows:
        route_id = str(row.get("route_id") or "")
        readiness = str(row.get("readiness") or "missing")
        disposition = "nothing_to_refine" if readiness == PASS else "file_local_defect"
        if route_id == "python_entrypoint_route" and readiness != PASS:
            disposition = "nothing_to_refine"
        tasks.append(
            {
                "task_id": f"probe:{route_id}",
                "route_id": route_id,
                "prompt": prompts_by_route.get(route_id, f"Find the source evidence for {route_id}."),
                "expected_depth_band": depth_by_route.get(route_id, "file_card"),
                "expected_refs": row.get("grounded_refs", []),
                "readiness": readiness,
                "probe_disposition": disposition,
                "reentry_condition": (
                    "project declares a runnable Python entrypoint"
                    if route_id == "python_entrypoint_route" and readiness != PASS
                    else "route readiness changes"
                ),
            }
        )
    return tasks


def _python_probe_disposition_rows(
    route_probe_tasks: list[dict[str, Any]],
    parse_error_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task in route_probe_tasks:
        rows.append(
            {
                "disposition_id": f"disposition:{task['route_id']}",
                "subject_id": task["route_id"],
                "subject_kind": "route_probe_task",
                "outcome": task["probe_disposition"],
                "readiness": task["readiness"],
                "expected_depth_band": task["expected_depth_band"],
                "reentry_condition": task["reentry_condition"],
            }
        )
    for row in parse_error_rows:
        rows.append(
            {
                "disposition_id": f"disposition:parse:{row.get('path')}",
                "subject_id": row.get("path"),
                "subject_kind": "python_parse_projection",
                "outcome": "file_local_defect",
                "readiness": "blocked",
                "expected_depth_band": "source_span",
                "reentry_condition": "syntax parses or file is removed from Python lens scope",
                "line": row.get("line"),
                "body_redacted": True,
            }
        )
    return rows


def _disposition_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        outcome: sum(1 for row in rows if row.get("outcome") == outcome)
        for outcome in PROBE_DISPOSITION_OUTCOMES
    }


def _first_path_with_role(path_rows: list[dict[str, Any]], roles: set[str]) -> str | None:
    for row in path_rows:
        if row.get("python_role") in roles and row.get("path"):
            return str(row["path"])
    return None


def _first_symbol_ref(symbol_capsule_rows: list[dict[str, Any]], path: str | None = None) -> str | None:
    for row in symbol_capsule_rows:
        if path is not None and row.get("path") != path:
            continue
        if row.get("symbol_id"):
            return str(row["symbol_id"])
    return None


def _first_source_span_ref(
    source_span_rows: list[dict[str, Any]],
    path: str | None = None,
    *,
    prefer_non_module: bool = False,
) -> str | None:
    fallback: str | None = None
    for row in source_span_rows:
        if path is not None and row.get("path") != path:
            continue
        span_id = row.get("span_id")
        if not span_id:
            continue
        if fallback is None:
            fallback = str(span_id)
        if not prefer_non_module or row.get("symbol_kind") != "module":
            return str(span_id)
    return fallback


def _first_graph_context_ref(import_edges: list[dict[str, Any]]) -> str | None:
    for row in import_edges:
        path = row.get("path")
        target = row.get("target")
        line = row.get("line")
        if path and target:
            return f"{path}:{line}->{target}"
    return None


def _route_utility_task(
    *,
    task_id: str,
    task_intent: str,
    expected_start_band: str,
    selected_band: str,
    route_hops: list[str],
    requirement_met: bool,
    expected_file_card: str | None = None,
    expected_symbol_capsule: str | None = None,
    expected_graph_context: str | None = None,
    expected_source_span: str | None = None,
    token_or_tool_count_proxy: int | None = None,
    failure_class: str = "local_projection_defect",
    disposition: str = "local_projection_defect",
    reentry_condition: str = "route utility fixture rerun changes this result",
    not_applicable: bool = False,
) -> dict[str, Any]:
    correctness = "not_applicable" if not_applicable else (PASS if requirement_met else "blocked")
    final_disposition = "nothing_to_refine" if requirement_met or not_applicable else disposition
    return {
        "task_id": task_id,
        "task_intent": task_intent,
        "entry_surface_ref": "atlas/entry_packet.json::python_navigation_route",
        "route_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::implementation_atlas.python_navigation_assay",
        "expected_start_band": expected_start_band,
        "selected_band": selected_band,
        "route_hops": route_hops,
        "expected_file_card": expected_file_card,
        "expected_symbol_capsule": expected_symbol_capsule,
        "expected_graph_context": expected_graph_context,
        "expected_source_span": expected_source_span,
        "correctness": correctness,
        "provenance_state": "derived_from_local_ast_and_entry_route",
        "worst_state": PASS if requirement_met or not_applicable else "degraded",
        "token_or_tool_count_proxy": token_or_tool_count_proxy or len(route_hops),
        "failure_class": "none" if requirement_met else ("not_applicable" if not_applicable else failure_class),
        "disposition": final_disposition,
        "reentry_condition": reentry_condition,
        "body_redacted": True,
    }


def _route_utility_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        outcome: sum(1 for row in tasks if row.get("disposition") == outcome)
        for outcome in ROUTE_UTILITY_DISPOSITION_OUTCOMES
    }


def _python_route_utility_curriculum(
    *,
    project: Path,
    path_rows: list[dict[str, Any]],
    source_refs: list[str],
    test_refs: list[str],
    pyproject_refs: list[str],
    entrypoint_refs: list[str],
    source_span_rows: list[dict[str, Any]],
    symbol_capsule_rows: list[dict[str, Any]],
    import_edges: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
    probe_dispositions: list[dict[str, Any]],
    parse_error_rows: list[dict[str, Any]],
    write_state: bool,
) -> dict[str, Any]:
    source_card = _first_path_with_role(path_rows, {"source_module", "package_init", "python_module"})
    test_card = _first_path_with_role(path_rows, {"test_module", "test_support"})
    entrypoint_card = entrypoint_refs[0] if entrypoint_refs else None
    source_span = _first_source_span_ref(source_span_rows, source_card)
    test_span = _first_source_span_ref(source_span_rows, test_card, prefer_non_module=True)
    entrypoint_span = _first_source_span_ref(source_span_rows, entrypoint_card, prefer_non_module=True)
    symbol_ref = _first_symbol_ref(symbol_capsule_rows, source_card) or _first_symbol_ref(symbol_capsule_rows)
    graph_ref = _first_graph_context_ref(import_edges)
    route_ids = {str(row.get("route_id") or "") for row in route_rows}
    closed_probe_count = sum(
        1
        for row in probe_dispositions
        if row.get("outcome") in PROBE_DISPOSITION_OUTCOMES
    )

    tasks = [
        _route_utility_task(
            task_id="route_utility:entry_surface_to_python_assay",
            task_intent="Start from the public entry packet and reach the Python navigation assay route.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=[
                "atlas/entry_packet.json::python_navigation_route",
                f"{STATE_DIR}/{PYTHON_LENS_STATE}::navigation_assay",
            ],
            requirement_met=True,
            expected_file_card=source_card,
            reentry_condition="entry packet python_navigation_route changes",
        ),
        _route_utility_task(
            task_id="route_utility:implementation_atlas_drilldown",
            task_intent="Use the implementation atlas as the assay drilldown rather than a parallel registry.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=[
                "atlas/entry_packet.json::python_navigation_route",
                f"{STATE_DIR}/{PYTHON_LENS_STATE}::implementation_atlas.python_navigation_assay",
            ],
            requirement_met=True,
            expected_file_card=source_card,
            reentry_condition="implementation atlas route changes",
        ),
        _route_utility_task(
            task_id="route_utility:package_metadata_file_card",
            task_intent="Locate package metadata through the cheapest sufficient file-card band.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=["python_navigation_route", "route_rows.python_package_metadata_route"],
            requirement_met=bool(pyproject_refs),
            expected_file_card=pyproject_refs[0] if pyproject_refs else None,
            failure_class="local_source_or_test_defect",
            disposition="local_source_or_test_defect",
            reentry_condition="pyproject metadata is added or removed",
        ),
        _route_utility_task(
            task_id="route_utility:source_core_source_span",
            task_intent="Find the primary source-core proof locator without exporting source bodies.",
            expected_start_band="file_card",
            selected_band="source_span",
            route_hops=[
                "python_navigation_route",
                "implementation_atlas.python_navigation_assay.primary_code_cards",
                "source_span_rows",
            ],
            requirement_met=bool(source_card and source_span),
            expected_file_card=source_card,
            expected_source_span=source_span,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="source core path or source-span extraction changes",
        ),
        _route_utility_task(
            task_id="route_utility:test_behavior_source_span",
            task_intent="Find the behavior-test proof locator through the test route.",
            expected_start_band="file_card",
            selected_band="source_span",
            route_hops=[
                "python_navigation_route",
                "route_rows.python_test_behavior_route",
                "source_span_rows",
            ],
            requirement_met=bool(test_card and test_span),
            expected_file_card=test_card,
            expected_source_span=test_span,
            failure_class="local_source_or_test_defect",
            disposition="local_source_or_test_defect",
            reentry_condition="test route or test source spans change",
        ),
        _route_utility_task(
            task_id="route_utility:entrypoint_source_span",
            task_intent="Find a runnable Python entrypoint when the project declares one.",
            expected_start_band="file_card",
            selected_band="source_span",
            route_hops=[
                "python_navigation_route",
                "route_rows.python_entrypoint_route",
                "source_span_rows",
            ],
            requirement_met=bool(entrypoint_card and entrypoint_span),
            expected_file_card=entrypoint_card,
            expected_source_span=entrypoint_span,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="project declares a runnable Python entrypoint",
            not_applicable=not entrypoint_refs,
        ),
        _route_utility_task(
            task_id="route_utility:symbol_capsule_lookup",
            task_intent="Answer a symbol-level question at symbol-capsule depth before opening spans.",
            expected_start_band="symbol_capsule",
            selected_band="symbol_capsule",
            route_hops=["python_navigation_route", "symbol_capsule_rows"],
            requirement_met=bool(symbol_ref),
            expected_file_card=source_card,
            expected_symbol_capsule=symbol_ref,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="symbol extraction changes",
            not_applicable=not symbol_capsule_rows,
        ),
        _route_utility_task(
            task_id="route_utility:graph_context_lookup",
            task_intent="Answer a dependency question at graph-context depth before opening spans.",
            expected_start_band="graph_context",
            selected_band="graph_context",
            route_hops=["python_navigation_route", "graph_context_edges"],
            requirement_met=bool(graph_ref),
            expected_graph_context=graph_ref,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="import graph extraction changes",
            not_applicable=not import_edges,
        ),
        _route_utility_task(
            task_id="route_utility:probe_disposition_closure",
            task_intent="Verify every route probe is closed into a disposition before success language.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=["navigation_assay.route_probe_tasks", "navigation_assay.probe_dispositions"],
            requirement_met=closed_probe_count == len(probe_dispositions) and not parse_error_rows,
            failure_class="macro_standard_amendment_candidate",
            disposition="macro_standard_amendment_candidate",
            reentry_condition="probe disposition grammar or parse status changes",
        ),
        _route_utility_task(
            task_id="route_utility:redaction_boundary",
            task_intent="Verify route utility uses refs and spans without exporting source bodies.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=["python_navigation_route", "authority_ceiling.source_bodies_exported"],
            requirement_met=all(row.get("body_redacted") is True for row in path_rows),
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="redaction or authority-ceiling fields change",
        ),
    ]
    disposition_counts = _route_utility_counts(tasks)
    pass_count = sum(1 for row in tasks if row.get("correctness") == PASS)
    not_applicable_count = sum(1 for row in tasks if row.get("correctness") == "not_applicable")
    failed_task_count = sum(1 for row in tasks if row.get("correctness") == "blocked")
    return {
        "schema_version": "microcosm_python_route_utility_curriculum_v1",
        "curriculum_id": "microcosm_python_route_utility_curriculum",
        "assay_id": "std_python_microcosm_navigation_assay",
        "target_root": _project_name(project),
        "entry_surface_ref": "atlas/entry_packet.json::python_navigation_route",
        "route_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::implementation_atlas.python_navigation_assay",
        "task_count": len(tasks),
        "tasks": tasks,
        "route_utility_metrics": {
            "pass_count": pass_count,
            "not_applicable_count": not_applicable_count,
            "failed_task_count": failed_task_count,
            "max_route_hops": max((len(row.get("route_hops", [])) for row in tasks), default=0),
            "all_failures_disposed": all(row.get("disposition") for row in tasks),
            "known_route_id_count": len(route_ids),
        },
        "disposition_counts": disposition_counts,
        "local_projection_defects": [
            row for row in tasks if row.get("disposition") == "local_projection_defect"
        ],
        "local_source_or_test_defects": [
            row for row in tasks if row.get("disposition") == "local_source_or_test_defect"
        ],
        "macro_standard_amendment_candidates": [
            row for row in tasks if row.get("disposition") == "macro_standard_amendment_candidate"
        ],
        "nothing_to_refine_receipts": [
            {
                "task_id": row.get("task_id"),
                "selected_band": row.get("selected_band"),
                "reentry_condition": row.get("reentry_condition"),
            }
            for row in tasks
            if row.get("disposition") == "nothing_to_refine"
        ],
        "redaction_boundary_ok": all(row.get("body_redacted") is True for row in path_rows),
        "source_bodies_exported": False,
        "body_redacted": True,
        "state_written": write_state,
        "authority": "route_utility_curriculum_is_public_safe_read_model_not_source_or_release_authority",
        "reentry_condition": "rerun after entry route, Python lens, source-span, graph, symbol, or std_python policy changes",
    }


def python_lens(project_path: str | Path, *, write_state: bool = True) -> dict[str, Any]:
    """Project Python route/readiness signals without exposing source bodies."""
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = catalog_project(project) if write_state else _project_catalog_payload(project)
    roles = catalog.get("roles", {}) if isinstance(catalog.get("roles"), dict) else {}
    files = catalog.get("files", []) if isinstance(catalog.get("files"), list) else []
    python_files = [
        row
        for row in files
        if isinstance(row, dict) and str(row.get("suffix") or "") == ".py"
    ]
    path_rows: list[dict[str, Any]] = []
    source_span_rows: list[dict[str, Any]] = []
    symbol_capsule_rows: list[dict[str, Any]] = []
    import_edges: list[dict[str, Any]] = []
    parse_error_rows: list[dict[str, Any]] = []
    module_docstring_refs: list[str] = []
    for row in python_files:
        rel = str(row.get("path") or "")
        text = _read_text_prefix(project / rel, limit=None)
        span_projection = _python_span_projection(rel, text)
        source_span_rows.extend(span_projection["source_span_rows"])
        symbol_capsule_rows.extend(span_projection["symbol_capsule_rows"])
        import_edges.extend(span_projection["import_edges"])
        if span_projection["module_has_docstring"]:
            module_docstring_refs.append(rel)
        parse_error = span_projection.get("parse_error")
        if isinstance(parse_error, dict):
            parse_error_rows.append(parse_error)
        path_rows.append(
            {
                "path": rel,
                "catalog_role": row.get("role"),
                "python_role": _python_lens_role(row),
                "bytes": row.get("bytes", 0),
                "parse_status": span_projection["parse_status"],
                "has_main_guard": "__main__" in text and "__name__" in text,
                "relative_import_count": sum(
                    1 for line in text.splitlines() if line.strip().startswith("from .")
                ),
                "absolute_import_count": sum(
                    1
                    for line in text.splitlines()
                    if line.strip().startswith("import ") or line.strip().startswith("from ")
                ),
                "body_redacted": True,
            }
        )
    package_refs = roles.get("package_manifest", [])
    pyproject_refs = (
        [str(path) for path in package_refs if str(path).endswith("pyproject.toml")]
        if isinstance(package_refs, list)
        else []
    )
    source_refs = [str(row["path"]) for row in path_rows if row["python_role"] == "source_module"]
    test_refs = [
        str(row["path"])
        for row in path_rows
        if row["python_role"] in {"test_module", "test_support"}
    ]
    entrypoint_refs = [str(row["path"]) for row in path_rows if row["has_main_guard"]]
    package_roots = sorted(
        {
            root
            for root in (_python_package_root(str(row.get("path") or "")) for row in path_rows)
            if root
        }
    )
    checks = [
        {
            "check_id": "pyproject_declared",
            "status": PASS if pyproject_refs else "missing",
            "grounded_refs": pyproject_refs,
        },
        {
            "check_id": "python_source_visible",
            "status": PASS if source_refs or package_roots else "missing",
            "grounded_refs": source_refs[:12] or package_roots[:12],
        },
        {
            "check_id": "python_tests_visible",
            "status": PASS if test_refs else "missing",
            "grounded_refs": test_refs[:12],
        },
        {
            "check_id": "python_entrypoint_visible",
            "status": PASS if entrypoint_refs else "missing",
            "grounded_refs": entrypoint_refs[:12],
        },
        {
            "check_id": "python_package_roots_visible",
            "status": PASS if package_roots else "missing",
            "grounded_refs": package_roots,
        },
    ]
    route_rows = [
        _python_route(
            "python_package_metadata_route",
            "Inspect Python package metadata",
            pyproject_refs,
            PASS if pyproject_refs else "missing",
        ),
        _python_route(
            "python_source_core_route",
            "Inspect Python source core",
            source_refs or package_roots,
            PASS if source_refs or package_roots else "missing",
        ),
        _python_route(
            "python_test_behavior_route",
            "Inspect Python behavior tests",
            test_refs,
            PASS if test_refs else "missing",
        ),
        _python_route(
            "python_entrypoint_route",
            "Inspect Python entrypoint scripts",
            entrypoint_refs,
            PASS if entrypoint_refs else "missing",
        ),
    ]
    route_probe_tasks = _python_route_probe_tasks(route_rows)
    probe_dispositions = _python_probe_disposition_rows(route_probe_tasks, parse_error_rows)
    disposition_counts = _disposition_counts(probe_dispositions)
    depth_band_coverage = {
        "module_docs": len(module_docstring_refs),
        "file_card": len(path_rows),
        "symbol_capsule": len(symbol_capsule_rows),
        "graph_context": len(import_edges),
        "source_span": len(source_span_rows),
    }
    navigation_assay = {
        "schema_version": "microcosm_python_navigation_assay_v1",
        "assay_id": "std_python_microcosm_navigation_assay",
        "target_surface": "project_python_route_lens",
        "standard_ref": "macro:codex/standards/std_python.py::navigation_contract",
        "canonical_depth_ladder": STD_PYTHON_NAVIGATION_LADDER,
        "adapter_bands_quarantined": [
            "cluster_flag",
            "flag",
            "card",
            "source_span",
        ],
        "depth_band_coverage": depth_band_coverage,
        "route_probe_tasks": route_probe_tasks,
        "probe_dispositions": probe_dispositions,
        "probe_disposition_counts": disposition_counts,
        "standard_amendment_candidates": [
            row
            for row in probe_dispositions
            if row.get("outcome") == "standard_amendment_candidate"
        ],
        "file_local_defect_count": disposition_counts["file_local_defect"],
        "standard_amendment_candidate_count": disposition_counts["standard_amendment_candidate"],
        "nothing_to_refine_count": disposition_counts["nothing_to_refine"],
        "source_span_count": len(source_span_rows),
        "symbol_capsule_count": len(symbol_capsule_rows),
        "graph_edge_count": len(import_edges),
        "parse_error_count": len(parse_error_rows),
        "route_utility_curriculum_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum",
        "authority": "generated_project_local_assay_not_std_python_source_authority",
        "reentry_condition": "rerun after Python file, catalog, route-readiness, or std_python ladder changes",
    }
    primary_source_spans = [
        str(row.get("span_id"))
        for row in source_span_rows
        if isinstance(row, dict) and row.get("span_id")
    ][:12]
    python_navigation_route = {
        "route_id": "std_python_microcosm_navigation_assay",
        "surface_id": "project_python_lens",
        "command": "microcosm python-lens <project>",
        "endpoint": "/project/python-lens",
        "assay_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::navigation_assay",
        "implementation_atlas_ref": (
            f"{STATE_DIR}/{PYTHON_LENS_STATE}"
            "::implementation_atlas.python_navigation_assay"
        ),
        "canonical_depth_ladder": STD_PYTHON_NAVIGATION_LADDER,
        "depth_selection": [
            {
                "intent": "project_python_orientation",
                "start_band": "file_card",
                "drilldown_when": "task requires exact function, class, import edge, or proof span",
            },
            {
                "intent": "symbol_or_dependency_question",
                "start_band": "symbol_capsule",
                "drilldown_when": "graph edge or caller/import context decides the next file",
            },
            {
                "intent": "mutation_or_proof_question",
                "start_band": "source_span",
                "drilldown_when": "exact source locator is required without exporting bodies",
            },
        ],
        "probe_disposition_counts": disposition_counts,
        "route_utility_curriculum_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum",
        "source_bodies_exported": False,
        "body_redacted": True,
        "authority": "route_selector_over_project_local_read_model_not_release_or_static_analysis_authority",
    }
    implementation_atlas = {
        "schema_version": "microcosm_project_implementation_atlas_v1",
        "source_surface": "project_python_route_lens",
        "python_navigation_assay": {
            "assay_id": navigation_assay["assay_id"],
            "assay_ref": python_navigation_route["assay_ref"],
            "route_id": python_navigation_route["route_id"],
            "command": python_navigation_route["command"],
            "endpoint": python_navigation_route["endpoint"],
            "canonical_depth_ladder": STD_PYTHON_NAVIGATION_LADDER,
            "depth_band_coverage": depth_band_coverage,
            "file_card_count": len(path_rows),
            "symbol_capsule_count": len(symbol_capsule_rows),
            "graph_edge_count": len(import_edges),
            "source_span_count": len(source_span_rows),
            "route_probe_task_count": len(route_probe_tasks),
            "probe_disposition_counts": disposition_counts,
            "route_utility_curriculum_ref": (
                f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum"
            ),
            "standard_amendment_candidate_count": disposition_counts[
                "standard_amendment_candidate"
            ],
            "file_local_defect_count": disposition_counts["file_local_defect"],
            "nothing_to_refine_count": disposition_counts["nothing_to_refine"],
            "parse_error_count": len(parse_error_rows),
            "primary_code_cards": (
                source_refs
                or package_roots
                or [str(row["path"]) for row in path_rows]
            )[:12],
            "primary_source_spans": primary_source_spans,
            "body_redacted": True,
            "source_bodies_exported": False,
            "authority": navigation_assay["authority"],
            "reentry_condition": navigation_assay["reentry_condition"],
        },
    }
    route_utility_curriculum = _python_route_utility_curriculum(
        project=project,
        path_rows=path_rows,
        source_refs=source_refs,
        test_refs=test_refs,
        pyproject_refs=pyproject_refs,
        entrypoint_refs=entrypoint_refs,
        source_span_rows=source_span_rows,
        symbol_capsule_rows=symbol_capsule_rows,
        import_edges=import_edges,
        route_rows=route_rows,
        probe_dispositions=probe_dispositions,
        parse_error_rows=parse_error_rows,
        write_state=write_state,
    )
    navigation_assay["route_utility_task_count"] = route_utility_curriculum["task_count"]
    navigation_assay["route_utility_disposition_counts"] = route_utility_curriculum[
        "disposition_counts"
    ]
    python_navigation_route["route_utility_curriculum_ref"] = navigation_assay[
        "route_utility_curriculum_ref"
    ]
    implementation_atlas["python_navigation_assay"]["route_utility_task_count"] = (
        route_utility_curriculum["task_count"]
    )
    implementation_atlas["python_navigation_assay"]["route_utility_disposition_counts"] = (
        route_utility_curriculum["disposition_counts"]
    )
    payload = {
        **_base_payload("microcosm_project_python_lens_v1", project),
        "lens_id": "project_python_route_lens",
        "command": "microcosm python-lens <project>",
        "state_file_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        "public_claim": (
            "Microcosm exposes Python project route readiness as path-level metadata "
            "without source bodies, provider calls, or source mutation."
        ),
        "python_file_count": len(path_rows),
        "package_roots": package_roots,
        "path_rows": path_rows,
        "symbol_capsule_rows": symbol_capsule_rows,
        "source_span_rows": source_span_rows,
        "graph_context_edges": import_edges,
        "source_span_count": len(source_span_rows),
        "symbol_capsule_count": len(symbol_capsule_rows),
        "graph_edge_count": len(import_edges),
        "readiness_checks": checks,
        "passing_check_count": sum(1 for row in checks if row["status"] == PASS),
        "missing_check_count": sum(1 for row in checks if row["status"] != PASS),
        "route_rows": route_rows,
        "navigation_assay": navigation_assay,
        "python_navigation_route": python_navigation_route,
        "implementation_atlas": implementation_atlas,
        "route_utility_curriculum": route_utility_curriculum,
        "ready_route_count": sum(1 for row in route_rows if row["readiness"] == PASS),
        "standard_refs": [
            "macro:codex/standards/std_python.py::navigation_contract",
            "macro:codex/standards/std_navigation_population_acceptance.json::probe_disposition_contract",
            "standards/std_microcosm_route_decision.json",
            "standards/std_microcosm_source_capsule.json",
            "standards/std_microcosm_evidence_cell.json",
        ],
        "authority_ceiling": {
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutated": False,
            "source_bodies_exported": False,
            "static_analysis_authority_claim": False,
            "source_span_authority_claim": False,
            "private_data_equivalence_authorized": False,
        },
        "body_redacted": True,
        "anti_claim": (
            "The Python lens is a public-safe path, source-span, and route-readiness "
            "read-model. It does not execute Python, infer correctness, export source "
            "bodies, mutate source, call providers, or claim production/package quality."
        ),
        "state_written": write_state,
    }
    if not write_state:
        payload["evidence_ref"] = None
        payload["event_id"] = None
        return payload

    write_json_atomic(_state_dir(project) / PYTHON_LENS_STATE, payload)
    architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.python_lens",
        PASS,
        python_file_count=len(path_rows),
        python_lens_ref=f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/python_lens.json",
    )
    _append_event(project, event)
    payload["event_id"] = event["event_id"]
    payload["evidence_ref"] = _write_evidence(
        project,
        "python_lens",
        {**payload, "event_id": event["event_id"]},
    )
    write_json_atomic(_state_dir(project) / PYTHON_LENS_STATE, payload)
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
    python_projection = python_lens(project)
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
        f"{STATE_DIR}/{PYTHON_LENS_STATE}",
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
            f"projected Python lens over {python_projection.get('python_file_count', 0)} Python files",
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
        "python_lens_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        "python_navigation_assay_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::navigation_assay",
        "python_file_count": python_projection.get("python_file_count", 0),
        "python_ready_route_count": python_projection.get("ready_route_count", 0),
        "python_source_span_count": python_projection.get("source_span_count", 0),
        "python_navigation_assay": {
            "assay_id": (
                python_projection.get("navigation_assay", {}).get("assay_id")
                if isinstance(python_projection.get("navigation_assay"), dict)
                else None
            ),
            "canonical_depth_ladder": (
                python_projection.get("navigation_assay", {}).get("canonical_depth_ladder", [])
                if isinstance(python_projection.get("navigation_assay"), dict)
                else []
            ),
            "probe_disposition_counts": (
                python_projection.get("navigation_assay", {}).get("probe_disposition_counts", {})
                if isinstance(python_projection.get("navigation_assay"), dict)
                else {}
            ),
            "route_utility_task_count": (
                python_projection.get("navigation_assay", {}).get("route_utility_task_count", 0)
                if isinstance(python_projection.get("navigation_assay"), dict)
                else 0
            ),
            "route_utility_disposition_counts": (
                python_projection.get("navigation_assay", {}).get(
                    "route_utility_disposition_counts", {}
                )
                if isinstance(python_projection.get("navigation_assay"), dict)
                else {}
            ),
        },
        "route_utility_curriculum": python_projection.get("route_utility_curriculum", {}),
        "implementation_atlas": python_projection.get("implementation_atlas", {}),
        "python_navigation_route": python_projection.get("python_navigation_route", {}),
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
    python_lens_parser = subparsers.add_parser("python-lens")
    python_lens_parser.add_argument("project")
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
    if args.command == "python-lens":
        return _print_json(python_lens(args.project))
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
