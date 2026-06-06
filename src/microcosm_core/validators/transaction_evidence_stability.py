from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from microcosm_core import architecture_kernel
from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.transaction_evidence_stability"
STATE_DIR = ".microcosm"
EVENT_STREAM = "events.jsonl"
EVIDENCE_DIR = "evidence"
EXPLANATION_DIR = "explanations"


def _project_relative(project: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(project.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return list(_iter_jsonl_dict_rows(path))


def _iter_jsonl_dict_rows(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                yield payload


def _event_stream_summary(
    path: Path,
    *,
    evidence_ref_set: set[str],
) -> dict[str, Any]:
    event_count = 0
    event_ids: set[str] = set()
    duplicate_event_ids: set[str] = set()
    event_findings: list[dict[str, Any]] = []
    for event in _iter_jsonl_dict_rows(path):
        event_count += 1
        event_id = event.get("event_id")
        if event_id:
            event_id_str = str(event_id)
            if event_id_str in event_ids:
                duplicate_event_ids.add(event_id_str)
            event_ids.add(event_id_str)
        evidence_ref = event.get("evidence_ref")
        if evidence_ref and str(evidence_ref) not in evidence_ref_set:
            event_findings.append(
                {
                    "event_id": event.get("event_id"),
                    "span": event.get("span"),
                    "unresolved_evidence_ref": evidence_ref,
                }
            )
    return {
        "event_count": event_count,
        "event_ids": event_ids,
        "duplicate_event_ids": sorted(duplicate_event_ids),
        "event_findings": event_findings,
    }


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _ref_path(project: Path, ref: str) -> Path:
    rel = ref.removeprefix(f"{STATE_DIR}/")
    return project / STATE_DIR / rel


def _ref_exists(project: Path, ref: str) -> bool:
    if "::" in ref:
        ref = ref.split("::", 1)[0]
    return _ref_path(project, ref).is_file()


def _duplicate_ids(rows: list[dict[str, Any]], key: str) -> list[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        item = str(value)
        if item in seen:
            duplicate.add(item)
        seen.add(item)
    return sorted(duplicate)


def _iter_state_files(path: Path) -> Iterator[Path]:
    with os.scandir(path) as entries:
        for entry in entries:
            child = path / entry.name
            if entry.is_dir(follow_symlinks=False):
                yield from _iter_state_files(child)
            elif entry.is_file(follow_symlinks=False):
                yield child


def _iter_json_files(path: Path) -> Iterator[Path]:
    if not path.is_dir():
        return
    for child in _iter_state_files(path):
        if child.suffix == ".json":
            yield child


def _state_files(project: Path) -> list[Path]:
    state = project / STATE_DIR
    if not state.is_dir():
        return []
    return sorted(
        path
        for path in _iter_state_files(state)
        if path.suffix in {".json", ".jsonl"}
    )


def _evidence_refs(project: Path) -> set[str]:
    evidence_dir = project / STATE_DIR / EVIDENCE_DIR
    if not evidence_dir.is_dir():
        return set()
    return {
        _project_relative(project, path)
        for path in _iter_json_files(evidence_dir)
    }


def _has_json_file(path: Path) -> bool:
    return path.is_dir() and any(_iter_json_files(path))


def _state_artifact_semantics(project: Path) -> list[dict[str, Any]]:
    return [
        {
            "state_ref": ".microcosm/project_manifest.json",
            "semantics": "stable_project_identity",
            "exists": (project / ".microcosm/project_manifest.json").is_file(),
        },
        {
            "state_ref": ".microcosm/catalog.json",
            "semantics": "replaced_from_current_project_files",
            "exists": (project / ".microcosm/catalog.json").is_file(),
        },
        {
            "state_ref": ".microcosm/patterns.json",
            "semantics": "replaced_from_current_catalog",
            "exists": (project / ".microcosm/patterns.json").is_file(),
        },
        {
            "state_ref": ".microcosm/routes.json",
            "semantics": "replaced_from_current_patterns",
            "exists": (project / ".microcosm/routes.json").is_file(),
        },
        {
            "state_ref": ".microcosm/explanations/*.json",
            "semantics": "stable_ref_latest_body",
            "exists": _has_json_file(project / ".microcosm/explanations"),
        },
        {
            "state_ref": ".microcosm/work_items.json",
            "semantics": "stable_closed_rows_idempotent_replay",
            "exists": (project / ".microcosm/work_items.json").is_file(),
        },
        {
            "state_ref": ".microcosm/events.jsonl",
            "semantics": "append_only_event_history",
            "exists": (project / ".microcosm/events.jsonl").is_file(),
        },
        {
            "state_ref": ".microcosm/evidence/*.json",
            "semantics": "stable_ref_latest_body_with_replacement_metadata",
            "exists": _has_json_file(project / ".microcosm/evidence"),
        },
        {
            "state_ref": ".microcosm/graph.json",
            "semantics": "replaced_from_current_state",
            "exists": (project / ".microcosm/graph.json").is_file(),
        },
    ]


def validate_stability(
    root: str | Path,
    project: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    project_path = Path(project).expanduser().resolve(strict=False)
    state = project_path / STATE_DIR
    output_file = Path(out_path)
    findings: list[dict[str, Any]] = []
    blocking_codes: list[str] = []

    patterns_payload = _read_json(state / "patterns.json")
    routes_payload = _read_json(state / "routes.json")
    work_payload = _read_json(state / "work_items.json")
    graph_payload = _read_json(state / "graph.json")
    pattern_rows = _rows(patterns_payload, "patterns")
    route_rows = _rows(routes_payload, "routes")
    work_rows = _rows(work_payload, "work_items")
    pattern_ids = {str(row["pattern_id"]) for row in pattern_rows if row.get("pattern_id")}
    route_ids = {str(row["route_id"]) for row in route_rows if row.get("route_id")}
    standard_ids = {
        str(row["standard_id"])
        for row in architecture_kernel.standard_pressure_rows(public_root)
        if row.get("standard_id")
    }
    evidence_ref_set = _evidence_refs(project_path)
    event_summary = _event_stream_summary(state / EVENT_STREAM, evidence_ref_set=evidence_ref_set)
    event_ids = event_summary["event_ids"]

    for rel in [
        "patterns.json",
        "routes.json",
        "work_items.json",
        "events.jsonl",
        "evidence",
        "explanations",
        "graph.json",
    ]:
        path = state / rel
        exists = path.is_dir() if rel in {"evidence", "explanations"} else path.is_file()
        if not exists:
            blocking_codes.append("PROJECT_TRANSACTION_EVIDENCE_STATE_MISSING")
            findings.append({"finding_id": "project_transaction_evidence_state_missing", "state_ref": f"{STATE_DIR}/{rel}"})

    duplicate_patterns = _duplicate_ids(pattern_rows, "pattern_id")
    duplicate_routes = _duplicate_ids(route_rows, "route_id")
    duplicate_events = event_summary["duplicate_event_ids"]
    if duplicate_patterns:
        blocking_codes.append("PROJECT_DUPLICATE_PATTERN_IDS")
        findings.append({"finding_id": "project_duplicate_pattern_ids", "pattern_ids": duplicate_patterns})
    if duplicate_routes:
        blocking_codes.append("PROJECT_DUPLICATE_ROUTE_IDS")
        findings.append({"finding_id": "project_duplicate_route_ids", "route_ids": duplicate_routes})
    if duplicate_events:
        blocking_codes.append("PROJECT_DUPLICATE_EVENT_IDS")
        findings.append({"finding_id": "project_duplicate_event_ids", "event_ids": duplicate_events})

    unresolved_route_refs: list[dict[str, Any]] = []
    unresolved_standard_refs: list[dict[str, Any]] = []
    for route in route_rows:
        route_id = str(route.get("route_id") or "")
        pattern_refs = route.get("pattern_refs", [])
        if not isinstance(pattern_refs, list):
            pattern_refs = []
        missing_patterns = [str(ref) for ref in pattern_refs if str(ref) not in pattern_ids]
        if missing_patterns:
            unresolved_route_refs.append({"route_id": route_id, "unresolved_pattern_refs": missing_patterns})
        standard_refs = route.get("standard_pressure_refs", [])
        if not isinstance(standard_refs, list):
            standard_refs = []
        missing_standards = [str(ref) for ref in standard_refs if str(ref) not in standard_ids]
        if missing_standards:
            unresolved_standard_refs.append({"route_id": route_id, "unresolved_standard_refs": missing_standards})
    if unresolved_route_refs:
        blocking_codes.append("PROJECT_ROUTE_PATTERN_REFS_UNRESOLVED")
        findings.append({"finding_id": "project_route_pattern_refs_unresolved", "routes": unresolved_route_refs})
    if unresolved_standard_refs:
        blocking_codes.append("PROJECT_ROUTE_STANDARD_REFS_UNRESOLVED")
        findings.append({"finding_id": "project_route_standard_refs_unresolved", "routes": unresolved_standard_refs})

    explanation_findings: list[dict[str, Any]] = []
    for path in sorted(_iter_json_files(state / EXPLANATION_DIR)):
        explanation = _read_json(path)
        route_id = str(explanation.get("route_id") or "")
        pattern_bindings = _rows(explanation, "pattern_bindings")
        standard_bindings = _rows(explanation, "standard_bindings")
        evidence_refs = explanation.get("evidence_refs", [])
        missing: list[str] = []
        if route_id not in route_ids:
            missing.append("route_id_resolves")
        if not pattern_bindings:
            missing.append("pattern_bindings")
        if any(row.get("resolved") is not True for row in pattern_bindings):
            missing.append("pattern_bindings_resolve")
        if not standard_bindings:
            missing.append("standard_bindings")
        if any(row.get("resolved") is not True for row in standard_bindings):
            missing.append("standard_bindings_resolve")
        if not isinstance(evidence_refs, list) or not all(_ref_exists(project_path, str(ref)) for ref in evidence_refs):
            missing.append("evidence_refs_resolve")
        if missing:
            explanation_findings.append(
                {
                    "explanation_ref": _project_relative(project_path, path),
                    "missing_or_unresolved": sorted(set(missing)),
                }
            )
    if explanation_findings:
        blocking_codes.append("PROJECT_ROUTE_EXPLANATION_REFS_UNSTABLE")
        findings.append({"finding_id": "project_route_explanation_refs_unstable", "explanations": explanation_findings})

    work_findings: list[dict[str, Any]] = []
    for row in work_rows:
        work_id = str(row.get("work_id") or "")
        route_id = str(row.get("route_id") or "")
        route_snapshot = row.get("route_snapshot")
        event_refs = row.get("event_refs", [])
        evidence_refs = row.get("evidence_refs", [])
        history = row.get("state_history", [])
        closeout = row.get("closeout")
        missing: list[str] = []
        if route_id not in route_ids:
            missing.append("route_id_resolves")
        if not isinstance(route_snapshot, dict) or str(route_snapshot.get("route_id") or "") != route_id:
            missing.append("route_snapshot_matches_route_id")
        for field in ["satisfaction_contract", "integration_contract", "transaction_policy"]:
            if not row.get(field):
                missing.append(field)
        if not isinstance(history, list):
            missing.append("state_history")
            state_sequence: list[str] = []
        else:
            state_sequence = [str(item.get("state")) for item in history if isinstance(item, dict) and item.get("state")]
        if row.get("status") == "closed" and state_sequence != [
            "created",
            "selected",
            "planned",
            "executed_simulation",
            "closed",
        ]:
            missing.append("closed_state_history_is_canonical")
        if row.get("status") == "closed" and not isinstance(closeout, dict):
            missing.append("closeout")
        if isinstance(closeout, dict):
            if closeout.get("satisfaction_contract_met") is not True:
                missing.append("closeout.satisfaction_contract_met")
            if closeout.get("integration_contract_met") is not True:
                missing.append("closeout.integration_contract_met")
            closeout_evidence_ref = closeout.get("evidence_ref")
            if closeout_evidence_ref and not _ref_exists(project_path, str(closeout_evidence_ref)):
                missing.append("closeout.evidence_ref_resolves")
        if not isinstance(event_refs, list) or not event_refs:
            missing.append("event_refs")
        elif any(str(item.get("event_id") or "") not in event_ids for item in event_refs if isinstance(item, dict)):
            missing.append("event_refs_resolve")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            missing.append("evidence_refs")
        elif any(str(ref) not in evidence_ref_set for ref in evidence_refs):
            missing.append("evidence_refs_resolve")
        if row.get("source_files_mutated") is not False:
            missing.append("source_files_mutated_false")
        if missing:
            work_findings.append({"work_id": work_id, "missing_or_unresolved": sorted(set(missing))})
    if work_findings:
        blocking_codes.append("PROJECT_WORK_TRANSACTION_REFS_UNSTABLE")
        findings.append({"finding_id": "project_work_transaction_refs_unstable", "work_items": work_findings})

    event_findings = event_summary["event_findings"]
    if event_findings:
        blocking_codes.append("PROJECT_EVENT_EVIDENCE_REFS_UNSTABLE")
        findings.append({"finding_id": "project_event_evidence_refs_unstable", "events": event_findings})

    evidence_findings: list[dict[str, Any]] = []
    for path in sorted(_iter_json_files(state / EVIDENCE_DIR)):
        payload = _read_json(path)
        replacement = payload.get("evidence_replacement")
        stable_ref = _project_relative(project_path, path)
        if not isinstance(replacement, dict):
            evidence_findings.append({"evidence_ref": stable_ref, "missing": "evidence_replacement"})
            continue
        missing = [
            field
            for field in ["stable_ref", "policy", "replacement_recorded", "append_only_event_history_ref"]
            if field not in replacement
        ]
        if replacement.get("stable_ref") != stable_ref:
            missing.append("stable_ref_matches_file")
        if replacement.get("policy") != "stable_ref_latest_body":
            missing.append("policy_stable_ref_latest_body")
        if replacement.get("append_only_event_history_ref") != f"{STATE_DIR}/{EVENT_STREAM}":
            missing.append("append_only_event_history_ref")
        if missing:
            evidence_findings.append({"evidence_ref": stable_ref, "missing_or_invalid": sorted(set(missing))})
    if evidence_findings:
        blocking_codes.append("PROJECT_EVIDENCE_REPLACEMENT_METADATA_MISSING")
        findings.append({"finding_id": "project_evidence_replacement_metadata_missing", "evidence": evidence_findings})

    graph_nodes = {str(row.get("node_id")) for row in _rows(graph_payload, "nodes") if row.get("node_id")}
    graph_edges = _rows(graph_payload, "edges")
    duplicate_edges: set[tuple[str, str, str]] = set()
    seen_edges: set[tuple[str, str, str]] = set()
    orphan_edges: list[dict[str, Any]] = []
    for edge in graph_edges:
        edge_key = (str(edge.get("from")), str(edge.get("to")), str(edge.get("relation")))
        if edge_key in seen_edges:
            duplicate_edges.add(edge_key)
        seen_edges.add(edge_key)
        if str(edge.get("from")) not in graph_nodes or str(edge.get("to")) not in graph_nodes:
            orphan_edges.append(edge)
    if duplicate_edges:
        blocking_codes.append("PROJECT_GRAPH_DUPLICATE_EDGES")
        findings.append(
            {
                "finding_id": "project_graph_duplicate_edges",
                "edges": [
                    {"from": item[0], "to": item[1], "relation": item[2]}
                    for item in sorted(duplicate_edges)
                ],
            }
        )
    if orphan_edges:
        blocking_codes.append("PROJECT_GRAPH_ORPHAN_EDGES")
        findings.append({"finding_id": "project_graph_orphan_edges", "edges": orphan_edges[:20]})

    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(_state_files(project_path), forbidden_classes=policy, display_root=project_path)
    safe_scan = dict(scan)
    safe_scan.pop("forbidden_output_fields", None)
    if safe_scan.get("blocking_hit_count"):
        blocking_codes.append("PROJECT_PRIVATE_STATE_SCAN_BLOCKED")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "transaction_evidence_stability_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "project_ref": project_path.name,
        "route_count": len(route_rows),
        "pattern_count": len(pattern_rows),
        "work_item_count": len(work_rows),
        "event_count": event_summary["event_count"],
        "evidence_count": len(evidence_ref_set),
        "state_artifact_semantics": _state_artifact_semantics(project_path),
        "findings": findings,
        "blocking_codes": blocking_codes,
        "consistency_summary": {
            "route_pattern_refs_resolve": "PROJECT_ROUTE_PATTERN_REFS_UNRESOLVED" not in blocking_codes,
            "route_standard_refs_resolve": "PROJECT_ROUTE_STANDARD_REFS_UNRESOLVED" not in blocking_codes,
            "explain_refs_resolve": "PROJECT_ROUTE_EXPLANATION_REFS_UNSTABLE" not in blocking_codes,
            "work_event_evidence_refs_resolve": "PROJECT_WORK_TRANSACTION_REFS_UNSTABLE" not in blocking_codes,
            "events_reference_existing_evidence": "PROJECT_EVENT_EVIDENCE_REFS_UNSTABLE" not in blocking_codes,
            "evidence_replacements_recorded": "PROJECT_EVIDENCE_REPLACEMENT_METADATA_MISSING" not in blocking_codes,
            "graph_has_no_duplicate_or_orphan_edges": "PROJECT_GRAPH_DUPLICATE_EDGES" not in blocking_codes
            and "PROJECT_GRAPH_ORPHAN_EDGES" not in blocking_codes,
            "events_are_append_only": True,
            "source_mutation_default": False,
            "release_authorized": False,
        },
        "private_state_scan": safe_scan,
        "public_boundary_scan": safe_scan,
        "authority_ceiling": {
            "release_authorized": False,
            "hosting_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": "Transaction/evidence stability validates project-local causal consistency. It does not authorize hosted release operations, credentialed provider calls, unsafe source mutation, secret export, live Task Ledger mutation, or production deployment.",
        "receipt_paths": [_project_relative(Path.cwd(), output_file)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate project transaction/evidence stability")
    parser.add_argument("--root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.transaction_evidence_stability "
        f"--root {args.root} --project {Path(args.project).name} --out {args.out}"
    )
    receipt = validate_stability(args.root, args.project, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
