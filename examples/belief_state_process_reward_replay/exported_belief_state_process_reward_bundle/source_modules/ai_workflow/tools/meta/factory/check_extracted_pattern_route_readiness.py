#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Make macro pattern organ routing enforceable instead of leaving
  the readiness audit as prose-shaped guidance.
- Mechanism: Validate the extracted pattern ledger, route-readiness audit,
  row-to-organ router, organ route cards, fixture specs, decision matrix, and
  dependency DAG as one routing contract.
- Boundary: This is macro-side routing validation only. It does not rebuild the
  public microcosm and does not mutate historical ledger rows.

[INTERFACE]
- CLI: --check, --write-report, --json.
- Exports: build_route_readiness_validation_report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


LEDGER_REL = "state/microcosm_portfolio/extracted_patterns_ledger.jsonl"
AUDIT_REL = "state/microcosm_portfolio/extracted_pattern_route_readiness_audit.json"
ROUTER_REL = "state/microcosm_portfolio/extracted_pattern_row_to_organ_router.json"
ROUTE_CARDS_REL = "state/microcosm_portfolio/extracted_pattern_organ_route_cards.json"
FIXTURE_SPECS_REL = "state/microcosm_portfolio/extracted_pattern_organ_fixture_specs.json"
DECISION_MATRIX_REL = "state/microcosm_portfolio/extracted_pattern_route_decision_matrix.json"
DAG_REL = "state/microcosm_portfolio/extracted_pattern_organ_dependency_dag.json"
INTERNAL_GRAPH_REL = "state/microcosm_portfolio/extracted_pattern_internal_routing_graph.json"
BINDINGS_REL = "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
VALIDATION_REPORT_REL = (
    "state/microcosm_portfolio/extracted_pattern_route_readiness_validation_report.json"
)
STANDARD_REL = "codex/standards/std_extracted_pattern_route_readiness.json"

EXPECTED_AUDIT_SCHEMA = "extracted_pattern_route_readiness_audit_v1"
REPORT_SCHEMA = "extracted_pattern_route_readiness_validation_report_v1"
REQUIRED_FIXTURE_CONTRACT_KEYS = (
    "fixture_id",
    "synthetic_inputs",
    "required_steps",
    "expected_artifacts",
    "negative_cases",
    "validator_or_check",
    "anti_claim",
)
REQUIRED_SELECTOR_OPENINGS = {
    "row_to_organ_router",
    "organ_route_cards",
    "organ_fixture_specs",
    "route_readiness_audit",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            rows.append(
                {
                    "_invalid_jsonl": True,
                    "_line_number": line_number,
                    "_error": str(exc),
                }
            )
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            rows.append(
                {
                    "_invalid_jsonl": True,
                    "_line_number": line_number,
                    "_error": "jsonl row is not an object",
                }
            )
    return rows


def _hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
        path.chmod(0o644)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_str_list(value: Any) -> list[str]:
    return [item for item in _as_list(value) if isinstance(item, str)]


def _finding(
    *,
    severity: str,
    rule: str,
    message: str,
    source: str | None = None,
    identifier: str | None = None,
    expected: Any | None = None,
    observed: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "severity": severity,
        "rule": rule,
        "message": message,
    }
    if source:
        payload["source"] = source
    if identifier:
        payload["identifier"] = identifier
    if expected is not None:
        payload["expected"] = expected
    if observed is not None:
        payload["observed"] = observed
    return payload


def _source_manifest(repo_root: Path) -> dict[str, Any]:
    inputs = [
        STANDARD_REL,
        LEDGER_REL,
        AUDIT_REL,
        ROUTER_REL,
        ROUTE_CARDS_REL,
        FIXTURE_SPECS_REL,
        DECISION_MATRIX_REL,
        DAG_REL,
        INTERNAL_GRAPH_REL,
        BINDINGS_REL,
    ]
    return {
        "inputs": [
            {
                "path": rel,
                "exists": (repo_root / rel).is_file(),
                "sha256": _hash_file(repo_root / rel),
            }
            for rel in inputs
        ]
    }


def _load_json_inputs(repo_root: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    for rel in (
        AUDIT_REL,
        ROUTER_REL,
        ROUTE_CARDS_REL,
        FIXTURE_SPECS_REL,
        DECISION_MATRIX_REL,
        DAG_REL,
        INTERNAL_GRAPH_REL,
        BINDINGS_REL,
    ):
        path = repo_root / rel
        if not path.is_file():
            findings.append(
                _finding(
                    severity="error",
                    rule="missing_required_input",
                    source=rel,
                    message=f"Missing required readiness input: {rel}",
                )
            )
            payloads[rel] = {}
            continue
        try:
            payloads[rel] = _read_json(path)
        except json.JSONDecodeError as exc:
            findings.append(
                _finding(
                    severity="error",
                    rule="invalid_json_input",
                    source=rel,
                    message=f"Invalid JSON in {rel}: {exc}",
                )
            )
            payloads[rel] = {}
    return payloads


def _fixture_pattern_ids(specs: Iterable[Mapping[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for spec in specs:
        ids.update(_as_str_list(spec.get("parent_pattern_ids")))
        ids.update(_as_str_list(spec.get("carry_with_pattern_ids")))
    return ids


def _router_pattern_ids(routers: Iterable[Mapping[str, Any]]) -> list[str]:
    ids: list[str] = []
    for router in routers:
        ids.extend(_as_str_list(router.get("match_pattern_ids")))
    return ids


def _binding_routes_by_id(bindings: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    routes: dict[str, dict[str, Any]] = {}
    for collection in ("foundation_combination_routes", "frontier_combination_routes"):
        for row in _as_list(bindings.get(collection)):
            if not isinstance(row, Mapping) or not isinstance(row.get("route_id"), str):
                continue
            route = dict(row)
            route["_route_collection"] = collection
            routes[route["route_id"]] = route
    return routes


def _iter_declared_pattern_refs(inputs: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    router = _as_dict(inputs.get(ROUTER_REL))
    for row in _as_list(router.get("family_routers")):
        if not isinstance(row, Mapping):
            continue
        for pattern_id in _as_str_list(row.get("match_pattern_ids")):
            yield ROUTER_REL, pattern_id
    for row in _as_list(router.get("pattern_id_hot_routes")):
        if isinstance(row, Mapping) and isinstance(row.get("pattern_id"), str):
            yield ROUTER_REL, row["pattern_id"]

    route_cards = _as_dict(inputs.get(ROUTE_CARDS_REL))
    for card in _as_list(route_cards.get("route_cards")):
        if not isinstance(card, Mapping):
            continue
        for field in ("anchor_pattern_ids", "do_not_select_alone_pattern_ids"):
            for pattern_id in _as_str_list(card.get(field)):
                yield ROUTE_CARDS_REL, pattern_id

    fixture_specs = _as_dict(inputs.get(FIXTURE_SPECS_REL))
    for spec in _as_list(fixture_specs.get("organ_fixture_specs")):
        if not isinstance(spec, Mapping):
            continue
        for field in ("parent_pattern_ids", "carry_with_pattern_ids", "standalone_exclusions"):
            for pattern_id in _as_str_list(spec.get(field)):
                yield FIXTURE_SPECS_REL, pattern_id

    matrix = _as_dict(inputs.get(DECISION_MATRIX_REL))
    for pattern_id in _as_str_list(matrix.get("hard_no_standalone_pattern_ids")):
        yield DECISION_MATRIX_REL, pattern_id
    for row in _as_list(matrix.get("family_route_decisions")):
        if not isinstance(row, Mapping):
            continue
        for field in ("parent_pattern_ids", "fold_or_evidence_pattern_ids"):
            for pattern_id in _as_str_list(row.get(field)):
                yield DECISION_MATRIX_REL, pattern_id
    for row in _as_list(matrix.get("duplicate_or_overlap_decisions")):
        if not isinstance(row, Mapping):
            continue
        for pattern_id in _as_str_list(row.get("pattern_ids")):
            yield DECISION_MATRIX_REL, pattern_id

    audit = _as_dict(inputs.get(AUDIT_REL))
    for row in _as_list(audit.get("intentional_router_overlaps")):
        if isinstance(row, Mapping) and isinstance(row.get("pattern_id"), str):
            yield AUDIT_REL, row["pattern_id"]


def _expected_summary(inputs: Mapping[str, Any]) -> dict[str, int]:
    router = _as_dict(inputs.get(ROUTER_REL))
    route_cards = _as_dict(inputs.get(ROUTE_CARDS_REL))
    fixture = _as_dict(inputs.get(FIXTURE_SPECS_REL))
    matrix = _as_dict(inputs.get(DECISION_MATRIX_REL))
    audit = _as_dict(inputs.get(AUDIT_REL))

    family_routers = [row for row in _as_list(router.get("family_routers")) if isinstance(row, Mapping)]
    fixture_specs = [
        row for row in _as_list(fixture.get("organ_fixture_specs")) if isinstance(row, Mapping)
    ]
    router_pattern_ids = _router_pattern_ids(family_routers)
    standalone_specs = [
        row for row in fixture_specs if row.get("should_become_standalone_leaf") is True
    ]
    child_or_private_specs = [
        row for row in fixture_specs if row.get("should_become_standalone_leaf") is not True
    ]
    return {
        "organ_route_card_count": len(_as_list(route_cards.get("route_cards"))),
        "organ_fixture_spec_count": len(fixture_specs),
        "family_router_count": len(family_routers),
        "explicit_family_router_pattern_ref_count": len(router_pattern_ids),
        "unique_explicit_family_router_pattern_ref_count": len(set(router_pattern_ids)),
        "pattern_id_hot_route_count": len(_as_list(router.get("pattern_id_hot_routes"))),
        "fixture_unique_pattern_ref_count": len(_fixture_pattern_ids(fixture_specs)),
        "hard_no_standalone_pattern_id_count": len(
            _as_str_list(matrix.get("hard_no_standalone_pattern_ids"))
        ),
        "standalone_pattern_leaf_candidate_count": 0,
        "standalone_leaf_organ_spec_count": len(standalone_specs),
        "child_or_private_or_reframe_spec_count": len(child_or_private_specs),
        "known_intentional_router_overlap_count": len(
            _as_list(audit.get("intentional_router_overlaps"))
        ),
    }


def _find_cycle(nodes: set[str], edges: Iterable[Mapping[str, Any]]) -> list[str]:
    graph: dict[str, list[str]] = {node: [] for node in nodes}
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if isinstance(src, str) and isinstance(dst, str) and src in nodes and dst in nodes:
            graph[src].append(dst)

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        if node in visiting:
            try:
                return stack[stack.index(node) :] + [node]
            except ValueError:
                return [node]
        if node in visited:
            return []
        visiting.add(node)
        stack.append(node)
        for child in graph.get(node, []):
            cycle = visit(child)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return []

    for node in sorted(nodes):
        cycle = visit(node)
        if cycle:
            return cycle
    return []


def _last_refinement_status(
    *,
    audit: Mapping[str, Any],
    binding_routes: Mapping[str, Mapping[str, Any]],
    ledger_ids: set[str],
    readiness_by_id: Mapping[str, Mapping[str, Any]],
    fixture_route_organ_ids: set[str],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    refinement = _as_dict(audit.get("last_refinement"))
    status: dict[str, Any] = {
        "status": "not_enforced",
        "route_id": None,
        "readiness_id": None,
        "route_collection": None,
        "touched_pattern_count": 0,
    }
    if not refinement:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_missing",
                source=AUDIT_REL,
                message="Route readiness audit must carry a machine-checkable last_refinement block.",
            )
        )
        return status

    required_fields = (
        "summary",
        "route_id",
        "readiness_id",
        "touched_pattern_ids",
        "route_evidence_refs",
        "owner",
    )
    for field in required_fields:
        if not refinement.get(field):
            findings.append(
                _finding(
                    severity="error",
                    rule="last_refinement_field_missing",
                    source=AUDIT_REL,
                    identifier=field,
                    message="last_refinement must carry route, readiness, pattern, evidence, owner, and summary fields.",
                )
            )

    route_id = refinement.get("route_id")
    readiness_id = refinement.get("readiness_id")
    touched_pattern_ids = _as_str_list(refinement.get("touched_pattern_ids"))
    evidence_refs = _as_str_list(refinement.get("route_evidence_refs"))
    status.update(
        {
            "route_id": route_id if isinstance(route_id, str) else None,
            "readiness_id": readiness_id if isinstance(readiness_id, str) else None,
            "touched_pattern_count": len(touched_pattern_ids),
        }
    )
    if not touched_pattern_ids:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_missing_touched_patterns",
                source=AUDIT_REL,
                message="last_refinement must name the pattern ids made routable in the pass.",
            )
        )
    if not evidence_refs:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_missing_evidence_refs",
                source=AUDIT_REL,
                message="last_refinement must cite binding, readiness, and validation evidence refs.",
            )
        )

    unknown_touched = sorted(set(touched_pattern_ids) - ledger_ids)
    if unknown_touched:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_unknown_touched_pattern",
                source=AUDIT_REL,
                message="last_refinement touched_pattern_ids must resolve in the extracted pattern ledger.",
                observed=unknown_touched,
            )
        )

    route = binding_routes.get(route_id) if isinstance(route_id, str) else None
    if route is None:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_unknown_binding_route",
                source=AUDIT_REL,
                identifier=str(route_id or "<missing>"),
                message="last_refinement route_id must resolve to a foundation or frontier combination route in the substrate binding sidecar.",
            )
        )
        return status
    status["route_collection"] = route.get("_route_collection")

    readiness = readiness_by_id.get(readiness_id) if isinstance(readiness_id, str) else None
    if readiness is None:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_unknown_readiness",
                source=AUDIT_REL,
                identifier=str(readiness_id or "<missing>"),
                message="last_refinement readiness_id must resolve to an organ_readiness row.",
            )
        )
    route_target_organs = set(_as_str_list(route.get("target_existing_organs")))
    readiness_organs = set(_as_str_list(readiness.get("route_to_organ_ids"))) if readiness else set()
    if readiness is not None and not route_target_organs.intersection(readiness_organs):
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_route_readiness_organ_mismatch",
                source=AUDIT_REL,
                identifier=str(readiness_id),
                message="last_refinement route target organs must overlap the readiness row route_to_organ_ids.",
                expected=sorted(route_target_organs),
                observed=sorted(readiness_organs),
            )
        )
    if readiness_organs and not readiness_organs.intersection(fixture_route_organ_ids):
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_readiness_missing_fixture_strategy",
                source=AUDIT_REL,
                identifier=str(readiness_id),
                message="last_refinement readiness must be backed by an organ fixture strategy.",
                observed=sorted(readiness_organs),
            )
        )

    available_pattern_ids = set(_as_str_list(route.get("available_pattern_ids")))
    detailed_pattern_ids = set(_as_str_list(route.get("detailed_binding_pattern_ids")))
    missing_from_route = sorted(set(touched_pattern_ids) - available_pattern_ids)
    if missing_from_route:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_touched_patterns_not_in_route",
                source=AUDIT_REL,
                identifier=str(route_id),
                message="last_refinement touched patterns must belong to the selected combination route.",
                observed=missing_from_route,
            )
        )
    missing_detailed_touched = sorted(set(touched_pattern_ids) - detailed_pattern_ids)
    if missing_detailed_touched:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_touched_patterns_not_detailed",
                source=AUDIT_REL,
                identifier=str(route_id),
                message="last_refinement touched patterns must have detailed bindings before the route is marked current.",
                observed=missing_detailed_touched,
            )
        )
    route_missing = _as_str_list(route.get("missing_pattern_ids"))
    route_missing_detailed = _as_str_list(route.get("missing_detailed_binding_pattern_ids"))
    if route_missing or route_missing_detailed:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_route_missing_detailed_binding",
                source=BINDINGS_REL,
                identifier=str(route_id),
                message="last_refinement cannot point at a route with unresolved pattern or detailed-binding gaps.",
                observed={
                    "missing_pattern_ids": route_missing,
                    "missing_detailed_binding_pattern_ids": route_missing_detailed,
                },
            )
        )
    for field, rule, message in (
        (
            "candidate_fixture",
            "last_refinement_route_missing_fixture_strategy",
            "Combination route must carry a candidate fixture strategy before current refinement can cite it.",
        ),
        (
            "anti_claim_floor",
            "last_refinement_route_missing_anti_claim",
            "Combination route must carry an anti-claim boundary before current refinement can cite it.",
        ),
    ):
        if not route.get(field):
            findings.append(
                _finding(
                    severity="error",
                    rule=rule,
                    source=BINDINGS_REL,
                    identifier=str(route_id),
                    message=message,
                )
            )
    if not _as_str_list(route.get("substrate_ref_sample")):
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_route_missing_source_refs",
                source=BINDINGS_REL,
                identifier=str(route_id),
                message="Combination route must carry source refs before current refinement can cite it.",
            )
        )

    evidence_text = "\n".join(evidence_refs)
    evidence_requirements = {
        "binding_route_ref": [BINDINGS_REL, str(route_id)],
        "readiness_row_ref": [AUDIT_REL, str(readiness_id)],
        "route_readiness_validator_ref": ["check_extracted_pattern_route_readiness.py"],
        "substrate_binding_validator_ref": ["build_extracted_pattern_substrate_bindings.py"],
    }
    missing_evidence = [
        name
        for name, fragments in evidence_requirements.items()
        if not all(fragment in evidence_text for fragment in fragments)
    ]
    if missing_evidence:
        findings.append(
            _finding(
                severity="error",
                rule="last_refinement_missing_required_evidence_ref",
                source=AUDIT_REL,
                identifier=str(route_id),
                message="last_refinement route_evidence_refs must cite binding route, readiness row, and both validators.",
                observed=missing_evidence,
            )
        )

    status["status"] = "enforced"
    status["route_missing_pattern_count"] = len(route_missing)
    status["route_missing_detailed_binding_count"] = len(route_missing_detailed)
    status["readiness_organ_overlap"] = sorted(route_target_organs.intersection(readiness_organs))
    return status


def _validate_report(inputs: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    ledger_path = repo_root / LEDGER_REL
    ledger_rows = _read_jsonl(ledger_path)
    invalid_jsonl = [row for row in ledger_rows if row.get("_invalid_jsonl")]
    for row in invalid_jsonl:
        findings.append(
            _finding(
                severity="error",
                rule="invalid_ledger_jsonl",
                source=LEDGER_REL,
                message=row.get("_error", "invalid jsonl row"),
                identifier=str(row.get("_line_number")),
            )
        )
    ledger_ids = {
        row.get("pattern_id")
        for row in ledger_rows
        if isinstance(row.get("pattern_id"), str) and not row.get("_invalid_jsonl")
    }
    duplicate_ledger_ids = sorted(
        pattern_id
        for pattern_id, count in Counter(
            row.get("pattern_id")
            for row in ledger_rows
            if isinstance(row.get("pattern_id"), str) and not row.get("_invalid_jsonl")
        ).items()
        if count > 1
    )
    for pattern_id in duplicate_ledger_ids:
        findings.append(
            _finding(
                severity="error",
                rule="duplicate_ledger_pattern_id",
                source=LEDGER_REL,
                identifier=pattern_id,
                message="Extracted pattern ledger pattern_id values must be unique.",
            )
        )

    audit = _as_dict(inputs.get(AUDIT_REL))
    if audit.get("schema_version") != EXPECTED_AUDIT_SCHEMA:
        findings.append(
            _finding(
                severity="error",
                rule="audit_schema_mismatch",
                source=AUDIT_REL,
                message="Route readiness audit schema_version does not match.",
                expected=EXPECTED_AUDIT_SCHEMA,
                observed=audit.get("schema_version"),
            )
        )

    declared_source = _as_dict(audit.get("source_ledger"))
    actual_ledger_hash = _hash_file(ledger_path)
    if declared_source.get("path") != LEDGER_REL:
        findings.append(
            _finding(
                severity="error",
                rule="source_ledger_path_mismatch",
                source=AUDIT_REL,
                message="Readiness audit points at the wrong source ledger path.",
                expected=LEDGER_REL,
                observed=declared_source.get("path"),
            )
        )
    if declared_source.get("parsed_pattern_row_count") != len(ledger_ids):
        findings.append(
            _finding(
                severity="error",
                rule="source_ledger_row_count_mismatch",
                source=AUDIT_REL,
                message="Readiness audit source ledger row count is stale.",
                expected=len(ledger_ids),
                observed=declared_source.get("parsed_pattern_row_count"),
            )
        )
    if declared_source.get("sha256") != actual_ledger_hash:
        findings.append(
            _finding(
                severity="error",
                rule="source_ledger_hash_mismatch",
                source=AUDIT_REL,
                message="Readiness audit source ledger hash is stale.",
                expected=actual_ledger_hash,
                observed=declared_source.get("sha256"),
            )
        )
    expected_source_evidence = (
        f"{len(ledger_ids)} parsed pattern rows, sha256 {actual_ledger_hash}"
    )
    freshness_gate = next(
        (
            row
            for row in _as_list(audit.get("readiness_gate_order"))
            if isinstance(row, Mapping) and row.get("gate_id") == "source_ledger_freshness"
        ),
        None,
    )
    if freshness_gate is None:
        findings.append(
            _finding(
                severity="error",
                rule="source_ledger_freshness_gate_missing",
                source=AUDIT_REL,
                message="Readiness audit must carry a source_ledger_freshness gate in readiness_gate_order.",
            )
        )
    elif freshness_gate.get("evidence") != expected_source_evidence:
        findings.append(
            _finding(
                severity="error",
                rule="source_ledger_freshness_gate_evidence_mismatch",
                source=AUDIT_REL,
                identifier="source_ledger_freshness",
                message="Readiness audit source ledger freshness gate evidence is stale.",
                expected=expected_source_evidence,
                observed=freshness_gate.get("evidence"),
            )
        )

    for overlay in _as_str_list(audit.get("input_overlays")):
        if not (repo_root / overlay).is_file():
            findings.append(
                _finding(
                    severity="error",
                    rule="missing_input_overlay",
                    source=AUDIT_REL,
                    identifier=overlay,
                    message="Readiness audit names an input overlay that does not exist.",
                )
            )

    expected_summary = _expected_summary(inputs)
    observed_summary = _as_dict(audit.get("audit_summary"))
    for key, expected in expected_summary.items():
        observed = observed_summary.get(key)
        if observed != expected:
            findings.append(
                _finding(
                    severity="error",
                    rule="audit_summary_mismatch",
                    source=AUDIT_REL,
                    identifier=key,
                    message="Readiness audit summary is stale or inconsistent with companion overlays.",
                    expected=expected,
                    observed=observed,
                )
            )

    router = _as_dict(inputs.get(ROUTER_REL))
    router_ids = _router_pattern_ids(
        row for row in _as_list(router.get("family_routers")) if isinstance(row, Mapping)
    )
    duplicated_router_ids = sorted(
        pattern_id for pattern_id, count in Counter(router_ids).items() if count > 1
    )
    intentional_overlap_ids = sorted(
        row.get("pattern_id")
        for row in _as_list(audit.get("intentional_router_overlaps"))
        if isinstance(row, Mapping) and isinstance(row.get("pattern_id"), str)
    )
    if duplicated_router_ids != intentional_overlap_ids:
        findings.append(
            _finding(
                severity="error",
                rule="unaccounted_router_duplicate",
                source=ROUTER_REL,
                message="Every duplicate family-router pattern ref must be explicitly listed as an intentional router overlap.",
                expected=duplicated_router_ids,
                observed=intentional_overlap_ids,
            )
        )

    for source, pattern_id in sorted(set(_iter_declared_pattern_refs(inputs))):
        if pattern_id not in ledger_ids:
            findings.append(
                _finding(
                    severity="error",
                    rule="unknown_pattern_ref",
                    source=source,
                    identifier=pattern_id,
                    message="Routing overlay references a pattern_id that is absent from the extracted pattern ledger.",
                )
            )

    fixture = _as_dict(inputs.get(FIXTURE_SPECS_REL))
    fixture_specs = [
        row for row in _as_list(fixture.get("organ_fixture_specs")) if isinstance(row, Mapping)
    ]
    fixture_spec_ids = {
        row.get("spec_id") for row in fixture_specs if isinstance(row.get("spec_id"), str)
    }
    fixture_route_organ_ids = {
        organ_id
        for row in fixture_specs
        for organ_id in _as_str_list(row.get("route_to_organ_ids"))
    }

    for row in fixture_specs:
        spec_id = str(row.get("spec_id") or "<missing>")
        contract = _as_dict(row.get("fixture_contract"))
        for key in REQUIRED_FIXTURE_CONTRACT_KEYS:
            value = contract.get(key)
            if not value:
                findings.append(
                    _finding(
                        severity="error",
                        rule="fixture_contract_missing_required_key",
                        source=FIXTURE_SPECS_REL,
                        identifier=f"{spec_id}:{key}",
                        message="Fixture specs must carry synthetic inputs, negative cases, validator/check, and anti-claim before organ selection.",
                    )
                )
        if not _as_str_list(row.get("route_to_organ_ids")):
            findings.append(
                _finding(
                    severity="error",
                    rule="fixture_spec_missing_route_to_organ_ids",
                    source=FIXTURE_SPECS_REL,
                    identifier=spec_id,
                    message="Fixture spec must name the organ ids it can make selectable.",
                )
            )

    readiness_rows = [
        row for row in _as_list(audit.get("organ_readiness")) if isinstance(row, Mapping)
    ]
    readiness_ids = {
        row.get("readiness_id") for row in readiness_rows if isinstance(row.get("readiness_id"), str)
    }
    readiness_by_id = {
        row["readiness_id"]: row
        for row in readiness_rows
        if isinstance(row.get("readiness_id"), str)
    }
    for row in readiness_rows:
        readiness_id = str(row.get("readiness_id") or "<missing>")
        if row.get("individual_row_selection") != "forbidden":
            findings.append(
                _finding(
                    severity="error",
                    rule="readiness_allows_individual_row_selection",
                    source=AUDIT_REL,
                    identifier=readiness_id,
                    message="Readiness rows must forbid individual row selection; future leaves select organs.",
                    observed=row.get("individual_row_selection"),
                )
            )
        route_to = _as_str_list(row.get("route_to_organ_ids"))
        if not route_to:
            findings.append(
                _finding(
                    severity="error",
                    rule="readiness_missing_route_to_organ_ids",
                    source=AUDIT_REL,
                    identifier=readiness_id,
                    message="Readiness row must route to at least one organ id.",
                )
            )
        missing_fixture_routes = sorted(set(route_to) - fixture_route_organ_ids)
        if missing_fixture_routes:
            findings.append(
                _finding(
                    severity="error",
                    rule="readiness_route_missing_fixture_spec",
                    source=AUDIT_REL,
                    identifier=readiness_id,
                    message="Readiness route_to_organ_ids must be backed by organ fixture specs.",
                    observed=missing_fixture_routes,
                )
            )

    bindings = _as_dict(inputs.get(BINDINGS_REL))
    binding_routes = _binding_routes_by_id(bindings)
    last_refinement_contract = _last_refinement_status(
        audit=audit,
        binding_routes=binding_routes,
        ledger_ids=ledger_ids,
        readiness_by_id=readiness_by_id,
        fixture_route_organ_ids=fixture_route_organ_ids,
        findings=findings,
    )

    child_queue_ids = {
        row.get("spec_id")
        for row in _as_list(audit.get("child_or_private_fold_queue"))
        if isinstance(row, Mapping) and isinstance(row.get("spec_id"), str)
    }
    selector = _as_dict(audit.get("selector_contract"))
    if selector.get("pattern_id_route_exists_does_not_mean_leaf_ready") is not True:
        findings.append(
            _finding(
                severity="error",
                rule="selector_contract_missing_no_row_leaf_rule",
                source=AUDIT_REL,
                message="Selector contract must state that pattern-id route existence does not mean leaf readiness.",
            )
        )
    observed_openings = set(_as_str_list(selector.get("selector_must_open")))
    missing_openings = sorted(REQUIRED_SELECTOR_OPENINGS - observed_openings)
    if missing_openings:
        findings.append(
            _finding(
                severity="error",
                rule="selector_contract_missing_required_opening",
                source=AUDIT_REL,
                message="Selector contract must open all route-readiness companion overlays.",
                observed=missing_openings,
            )
        )

    selector_targets = set(_as_str_list(selector.get("selector_may_select")))
    selector_targets.update(_as_str_list(selector.get("selector_may_select_after_roots")))
    selector_targets.update(_as_str_list(selector.get("selector_must_fold_or_defer")))
    valid_selector_targets = readiness_ids | child_queue_ids | fixture_spec_ids
    unknown_selector_targets = sorted(selector_targets - valid_selector_targets)
    if unknown_selector_targets:
        findings.append(
            _finding(
                severity="error",
                rule="selector_contract_unknown_target",
                source=AUDIT_REL,
                message="Selector contract names readiness or fold targets that are not defined.",
                observed=unknown_selector_targets,
            )
        )

    root_lock = _as_dict(audit.get("root_substrate_lock"))
    root_sequence = _as_str_list(root_lock.get("minimum_sequence"))
    missing_root_readiness = sorted(set(root_sequence) - readiness_ids)
    if missing_root_readiness:
        findings.append(
            _finding(
                severity="error",
                rule="root_substrate_sequence_unknown_readiness",
                source=AUDIT_REL,
                message="Root substrate lock references readiness ids that are not defined.",
                observed=missing_root_readiness,
            )
        )

    dag = _as_dict(inputs.get(DAG_REL))
    dag_nodes = {
        row.get("organ_id")
        for row in _as_list(dag.get("organ_nodes"))
        if isinstance(row, Mapping) and isinstance(row.get("organ_id"), str)
    }
    dag_edges = [row for row in _as_list(dag.get("dependency_edges")) if isinstance(row, Mapping)]
    for edge in dag_edges:
        src = edge.get("from")
        dst = edge.get("to")
        if src not in dag_nodes or dst not in dag_nodes:
            findings.append(
                _finding(
                    severity="error",
                    rule="dependency_edge_unknown_organ",
                    source=DAG_REL,
                    identifier=f"{src}->{dst}",
                    message="Organ dependency DAG edge references an undefined organ node.",
                )
            )
    cycle = _find_cycle({node for node in dag_nodes if isinstance(node, str)}, dag_edges)
    if cycle:
        findings.append(
            _finding(
                severity="error",
                rule="dependency_dag_cycle",
                source=DAG_REL,
                message="Organ dependency DAG must remain acyclic.",
                observed=cycle,
            )
        )

    route_cards = _as_dict(inputs.get(ROUTE_CARDS_REL))
    for card in _as_list(route_cards.get("route_cards")):
        if not isinstance(card, Mapping):
            continue
        card_id = str(card.get("card_id") or "<missing>")
        card_organ_ids = set(_as_str_list(card.get("organ_ids")))
        missing_card_nodes = sorted(card_organ_ids - dag_nodes)
        if missing_card_nodes:
            findings.append(
                _finding(
                    severity="error",
                    rule="route_card_unknown_organ",
                    source=ROUTE_CARDS_REL,
                    identifier=card_id,
                    message="Route card organ_ids must resolve in the dependency DAG.",
                    observed=missing_card_nodes,
                )
            )

    hard_no_standalone_ids = set(
        _as_str_list(_as_dict(inputs.get(DECISION_MATRIX_REL)).get("hard_no_standalone_pattern_ids"))
    )
    selectable_pattern_ids = selector_targets & ledger_ids
    illegal_selectable = sorted(hard_no_standalone_ids & selectable_pattern_ids)
    if illegal_selectable:
        findings.append(
            _finding(
                severity="error",
                rule="hard_no_standalone_marked_selectable",
                source=AUDIT_REL,
                message="Hard no-standalone pattern ids cannot appear in selector targets.",
                observed=illegal_selectable,
            )
        )

    error_count = sum(1 for finding in findings if finding.get("severity") == "error")
    warning_count = sum(1 for finding in findings if finding.get("severity") == "warning")
    return {
        "schema_version": REPORT_SCHEMA,
        "artifact_role": "macro_pattern_route_readiness_machine_check",
        "authority_boundary": "validation_projection_over_macro_side_routing_overlays_not_source_authority",
        "governing_standard": STANDARD_REL,
        "source_manifest": _source_manifest(repo_root),
        "summary": {
            "status": "ok" if error_count == 0 else "needs_route_readiness_repair",
            "error_count": error_count,
            "warning_count": warning_count,
            "ledger_pattern_count": len(ledger_ids),
            "organ_readiness_count": len(readiness_rows),
            "fixture_spec_count": len(fixture_specs),
            "route_card_count": len(_as_list(_as_dict(inputs.get(ROUTE_CARDS_REL)).get("route_cards"))),
            "dependency_organ_count": len(dag_nodes),
            "dependency_edge_count": len(dag_edges),
            "router_duplicate_count": len(duplicated_router_ids),
            "intentional_router_overlap_count": len(intentional_overlap_ids),
            "standalone_pattern_leaf_candidate_count": observed_summary.get(
                "standalone_pattern_leaf_candidate_count"
            ),
        },
        "recomputed_audit_summary": expected_summary,
        "router_duplicate_resolution": {
            "duplicated_family_router_pattern_ids": duplicated_router_ids,
            "intentional_router_overlap_pattern_ids": intentional_overlap_ids,
            "status": "covered" if duplicated_router_ids == intentional_overlap_ids else "drift",
        },
        "selection_contract": {
            "root_substrate_sequence": root_sequence,
            "selector_may_select": _as_str_list(selector.get("selector_may_select")),
            "selector_may_select_after_roots": _as_str_list(
                selector.get("selector_may_select_after_roots")
            ),
            "selector_must_fold_or_defer": _as_str_list(selector.get("selector_must_fold_or_defer")),
            "hard_no_standalone_pattern_id_count": len(hard_no_standalone_ids),
            "standalone_pattern_leaf_candidate_count": observed_summary.get(
                "standalone_pattern_leaf_candidate_count"
            ),
        },
        "last_refinement_contract": last_refinement_contract,
        "findings": findings,
        "next_type_a_pass": {
            "if_status_ok": "Use this checker as the preselector gate before any future public microcosm leaf reconstruction.",
            "if_status_needs_repair": "Repair the named overlay or ledger drift before selecting organs or adding pattern rows.",
        },
    }


def build_route_readiness_validation_report(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    inputs = _load_json_inputs(repo_root, findings)
    report = _validate_report(inputs, repo_root)
    if findings:
        report["findings"] = findings + report["findings"]
        report["summary"]["error_count"] = sum(
            1 for finding in report["findings"] if finding.get("severity") == "error"
        )
        report["summary"]["warning_count"] = sum(
            1 for finding in report["findings"] if finding.get("severity") == "warning"
        )
        report["summary"]["status"] = (
            "ok" if report["summary"]["error_count"] == 0 else "needs_route_readiness_repair"
        )
    return report


def write_report(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    report = build_route_readiness_validation_report(repo_root)
    _atomic_write_json(repo_root / VALIDATION_REPORT_REL, report)
    return report


def check_report(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    expected = build_route_readiness_validation_report(repo_root)
    findings = list(expected.get("findings", []))
    report_path = repo_root / VALIDATION_REPORT_REL
    if not report_path.is_file():
        findings.append(
            _finding(
                severity="error",
                rule="missing_validation_report",
                source=VALIDATION_REPORT_REL,
                message="Route readiness validation report is missing; run --write-report.",
            )
        )
    else:
        actual = _read_json(report_path)
        if actual != expected:
            findings.append(
                _finding(
                    severity="error",
                    rule="stale_validation_report",
                    source=VALIDATION_REPORT_REL,
                    message="Route readiness validation report is stale; rerun --write-report.",
                )
            )
    error_count = sum(1 for finding in findings if finding.get("severity") == "error")
    return {
        "schema_version": "extracted_pattern_route_readiness_check_v1",
        "status": "PASS" if error_count == 0 else "FAIL",
        "error_count": error_count,
        "warning_count": sum(1 for finding in findings if finding.get("severity") == "warning"),
        "report_ref": VALIDATION_REPORT_REL,
        "expected_summary": expected.get("summary"),
        "findings": findings,
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root)
    if args.check:
        result = check_report(repo_root)
        exit_ok = result.get("status") == "PASS"
    elif args.write_report:
        result = write_report(repo_root)
        exit_ok = _as_dict(result.get("summary")).get("status") == "ok"
    else:
        result = build_route_readiness_validation_report(repo_root)
        exit_ok = _as_dict(result.get("summary")).get("status") == "ok"

    if args.json or args.check or args.write_report:
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(json.dumps({"summary": result.get("summary")}, ensure_ascii=True, sort_keys=True))
    return 0 if exit_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
