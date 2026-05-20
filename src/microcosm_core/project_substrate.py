from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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


def _write_evidence(project: Path, action_id: str, payload: dict[str, Any]) -> str:
    ref = f"{EVIDENCE_DIR}/{action_id}.json"
    write_json_atomic(_state_dir(project) / ref, payload)
    return f"{STATE_DIR}/{ref}"


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
                f"{STATE_DIR}/catalog.json",
                f"{STATE_DIR}/patterns.json",
                f"{STATE_DIR}/routes.json",
                f"{STATE_DIR}/work_items.json",
                f"{STATE_DIR}/{EVENT_STREAM}",
                f"{STATE_DIR}/{EVIDENCE_DIR}/",
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
            }
        )
    payload = {
        **_base_payload("microcosm_project_patterns_v1", project),
        "patterns": candidates,
        "passing_pattern_count": sum(1 for row in candidates if row["status"] == PASS),
        "missing_pattern_count": sum(1 for row in candidates if row["status"] != PASS),
    }
    write_json_atomic(_state_dir(project) / "patterns.json", payload)
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

    routes: list[dict[str, Any]] = []

    def add(route_id: str, title: str, intent: str, refs: list[str], action: str) -> None:
        routes.append(
            {
                "route_id": route_id,
                "title": title,
                "intent": intent,
                "grounded_refs": refs[:12],
                "action": action,
                "authority": "project_local_projection_not_source_authority",
                "claims_source_authority": False,
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
    row = {
        "work_id": work_id,
        "route_id": selected["route_id"],
        "status": "created",
        "created_at": utc_now(),
        "grounded_refs": selected.get("grounded_refs", []),
        "transaction_policy": "simulate_project_local_only",
        "source_files_mutated": False,
    }
    rows.append(row)
    _write_work_items(project, rows)
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
    selected["status"] = "closed"
    selected["closed_at"] = utc_now()
    selected["result"] = {
        "status": PASS,
        "summary": "Simulated a governed local transaction over project catalog state.",
        "source_files_mutated": False,
    }
    _write_work_items(project, rows)
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
    return {
        **_base_payload("microcosm_project_work_run_result_v1", project),
        "work_id": selected["work_id"],
        "route_id": selected["route_id"],
        "transaction_status": PASS,
        "work_items_ref": f"{STATE_DIR}/work_items.json",
        "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "evidence_ref": evidence_ref,
    }


def observe_project(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve(strict=False)
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
    }


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
            }
        )
    return {
        **_base_payload("microcosm_project_evidence_list_v1", project),
        "evidence_count": len(rows),
        "evidence": rows,
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
    patterns_parser = subparsers.add_parser("patterns")
    patterns_parser.add_argument("project")
    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("project")
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
    if args.command == "patterns":
        return _print_json(discover_patterns(args.project))
    if args.command == "route":
        return _print_json(propose_routes(args.project))
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
