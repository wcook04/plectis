"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.pattern_route_readiness` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: BUNDLE_RESULT_NAME, REPORT_SCHEMA, EXPECTED_AUDIT_SCHEMA, LEDGER_NAME, MANIFEST_NAME, STANDARD_NAME, AUDIT_NAME, ROUTER_NAME, ROUTE_CARDS_NAME, FIXTURE_SPECS_NAME, DECISION_MATRIX_NAME, DAG_NAME, INTERNAL_GRAPH_NAME, SOURCE_REPORT_NAME, SUPERSESSION_REPORT_NAME, ORGAN_CLUSTERS_NAME, JSON_INPUT_NAMES, ALL_INPUT_NAMES, REQUIRED_FIXTURE_CONTRACT_KEYS, REQUIRED_SELECTOR_OPENINGS, AUTHORITY_CEILING, ANTI_CLAIM, build_route_readiness_validation_report, validate_route_readiness_bundle
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)


BUNDLE_RESULT_NAME = "exported_route_readiness_bundle_validation_result.json"
REPORT_SCHEMA = "microcosm_pattern_route_readiness_validation_report_v1"
EXPECTED_AUDIT_SCHEMA = "extracted_pattern_route_readiness_audit_v1"
LEDGER_NAME = "pattern_ledger_rows.jsonl"
MANIFEST_NAME = "bundle_manifest.json"
STANDARD_NAME = "std_extracted_pattern_route_readiness.json"
AUDIT_NAME = "extracted_pattern_route_readiness_audit.json"
ROUTER_NAME = "extracted_pattern_row_to_organ_router.json"
ROUTE_CARDS_NAME = "extracted_pattern_organ_route_cards.json"
FIXTURE_SPECS_NAME = "extracted_pattern_organ_fixture_specs.json"
DECISION_MATRIX_NAME = "extracted_pattern_route_decision_matrix.json"
DAG_NAME = "extracted_pattern_organ_dependency_dag.json"
INTERNAL_GRAPH_NAME = "extracted_pattern_internal_routing_graph.json"
SOURCE_REPORT_NAME = "source_route_readiness_validation_report.json"
SUPERSESSION_REPORT_NAME = "extracted_pattern_supersession_report.md"
ORGAN_CLUSTERS_NAME = "extracted_pattern_organ_clusters.md"

JSON_INPUT_NAMES = (
    AUDIT_NAME,
    ROUTER_NAME,
    ROUTE_CARDS_NAME,
    FIXTURE_SPECS_NAME,
    DECISION_MATRIX_NAME,
    DAG_NAME,
    INTERNAL_GRAPH_NAME,
)
ALL_INPUT_NAMES = (
    MANIFEST_NAME,
    STANDARD_NAME,
    LEDGER_NAME,
    *JSON_INPUT_NAMES,
    SOURCE_REPORT_NAME,
    SUPERSESSION_REPORT_NAME,
    ORGAN_CLUSTERS_NAME,
)
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
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "pattern_route_readiness_selector_validation_only",
    "public_leaf_authority": False,
    "individual_pattern_row_selection_authorized": False,
    "source_authority_above_imported_bundle": False,
    "release_authorized": False,
    "publication_authorized": False,
    "private_data_equivalence_claim": False,
}
ANTI_CLAIM = (
    "Pattern route-readiness validates the imported selector overlays and proves "
    "that mined rows route through organs, fixture contracts, and no-standalone "
    "gates. It does not make any mined row a standalone public leaf, authorize "
    "publication, or claim private macro source authority."
)


def _bundle_public_root(input_dir: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_bundle_public_root` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir).resolve(strict=False)
    for candidate in (input_path, *input_path.parents):
        if (candidate / "src/microcosm_core").is_dir() and (candidate / "examples").is_dir():
            return candidate
        if (candidate / "core/private_state_forbidden_classes.json").is_file() and (
            candidate / "examples"
        ).is_dir():
            return candidate
    return input_path.parent


def _receipt_ref(path: Path, public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_receipt_ref` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ref = public_relative_path(path, display_root=public_root)
    if "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        return Path(*path.parts[receipts_index:]).as_posix()
    return ref


def _file_sha256(path: Path) -> str | None:
    """
    [ACTION]
    - Teleology: Implements `_file_sha256` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_read_jsonl_rows` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
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


def _as_list(value: Any) -> list[Any]:
    """
    [ACTION]
    - Teleology: Implements `_as_list` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_as_dict` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, Mapping) else {}


def _as_str_list(value: Any) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_as_str_list` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_finding` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload: dict[str, Any] = {
        "severity": severity,
        "rule": rule,
        "message": message,
        "body_in_receipt": False,
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


def _source_manifest(input_dir: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_manifest` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    by_path = {
        str(row.get("path") or ""): row
        for row in _as_list(manifest.get("files"))
        if isinstance(row, Mapping)
    }
    rows: list[dict[str, Any]] = []
    for name in ALL_INPUT_NAMES:
        path = input_dir / name
        declared = by_path.get(name, {})
        actual_sha = _file_sha256(path)
        expected_sha = declared.get("sha256")
        rows.append(
            {
                "path": name,
                "source_ref": declared.get("source_ref"),
                "exists": path.is_file(),
                "sha256": actual_sha,
                "expected_sha256": expected_sha,
                "digest_status": (
                    "match"
                    if actual_sha and expected_sha == actual_sha
                    else "not_declared"
                    if actual_sha and expected_sha is None
                    else "mismatch"
                ),
            }
        )
    return {
        "inputs": rows,
        "all_expected_digests_matched": all(
            row["digest_status"] in {"match", "not_declared"} for row in rows
        ),
    }


def _load_json_inputs(input_dir: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_json_inputs` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payloads: dict[str, Any] = {}
    for name in JSON_INPUT_NAMES:
        path = input_dir / name
        if not path.is_file():
            findings.append(
                _finding(
                    severity="error",
                    rule="missing_required_input",
                    source=name,
                    message=f"Missing required route-readiness input: {name}",
                )
            )
            payloads[name] = {}
            continue
        try:
            payload = read_json_strict(path)
        except Exception as exc:
            findings.append(
                _finding(
                    severity="error",
                    rule="invalid_json_input",
                    source=name,
                    message=f"Invalid JSON in {name}: {exc}",
                )
            )
            payloads[name] = {}
            continue
        payloads[name] = payload if isinstance(payload, dict) else {}
    return payloads


def _fixture_pattern_ids(specs: Iterable[Mapping[str, Any]]) -> set[str]:
    """
    [ACTION]
    - Teleology: Implements `_fixture_pattern_ids` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ids: set[str] = set()
    for spec in specs:
        ids.update(_as_str_list(spec.get("parent_pattern_ids")))
        ids.update(_as_str_list(spec.get("carry_with_pattern_ids")))
    return ids


def _router_pattern_ids(routers: Iterable[Mapping[str, Any]]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_router_pattern_ids` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ids: list[str] = []
    for router in routers:
        ids.extend(_as_str_list(router.get("match_pattern_ids")))
    return ids


def _expected_summary(inputs: Mapping[str, Any]) -> dict[str, int]:
    """
    [ACTION]
    - Teleology: Implements `_expected_summary` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    router = _as_dict(inputs.get(ROUTER_NAME))
    route_cards = _as_dict(inputs.get(ROUTE_CARDS_NAME))
    fixture = _as_dict(inputs.get(FIXTURE_SPECS_NAME))
    matrix = _as_dict(inputs.get(DECISION_MATRIX_NAME))
    audit = _as_dict(inputs.get(AUDIT_NAME))

    family_routers = [row for row in _as_list(router.get("family_routers")) if isinstance(row, Mapping)]
    fixture_specs = [row for row in _as_list(fixture.get("organ_fixture_specs")) if isinstance(row, Mapping)]
    router_pattern_ids = _router_pattern_ids(family_routers)
    standalone_specs = [row for row in fixture_specs if row.get("should_become_standalone_leaf") is True]
    child_or_private_specs = [row for row in fixture_specs if row.get("should_become_standalone_leaf") is not True]
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


def _iter_declared_pattern_refs(inputs: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    """
    [ACTION]
    - Teleology: Implements `_iter_declared_pattern_refs` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    router = _as_dict(inputs.get(ROUTER_NAME))
    for row in _as_list(router.get("family_routers")):
        if not isinstance(row, Mapping):
            continue
        for pattern_id in _as_str_list(row.get("match_pattern_ids")):
            yield ROUTER_NAME, pattern_id
    for row in _as_list(router.get("pattern_id_hot_routes")):
        if isinstance(row, Mapping) and isinstance(row.get("pattern_id"), str):
            yield ROUTER_NAME, row["pattern_id"]

    route_cards = _as_dict(inputs.get(ROUTE_CARDS_NAME))
    for card in _as_list(route_cards.get("route_cards")):
        if not isinstance(card, Mapping):
            continue
        for field in ("anchor_pattern_ids", "do_not_select_alone_pattern_ids"):
            for pattern_id in _as_str_list(card.get(field)):
                yield ROUTE_CARDS_NAME, pattern_id

    fixture_specs = _as_dict(inputs.get(FIXTURE_SPECS_NAME))
    for spec in _as_list(fixture_specs.get("organ_fixture_specs")):
        if not isinstance(spec, Mapping):
            continue
        for field in ("parent_pattern_ids", "carry_with_pattern_ids", "standalone_exclusions"):
            for pattern_id in _as_str_list(spec.get(field)):
                yield FIXTURE_SPECS_NAME, pattern_id

    matrix = _as_dict(inputs.get(DECISION_MATRIX_NAME))
    for pattern_id in _as_str_list(matrix.get("hard_no_standalone_pattern_ids")):
        yield DECISION_MATRIX_NAME, pattern_id
    for row in _as_list(matrix.get("family_route_decisions")):
        if not isinstance(row, Mapping):
            continue
        for field in ("parent_pattern_ids", "fold_or_evidence_pattern_ids"):
            for pattern_id in _as_str_list(row.get(field)):
                yield DECISION_MATRIX_NAME, pattern_id
    for row in _as_list(matrix.get("duplicate_or_overlap_decisions")):
        if not isinstance(row, Mapping):
            continue
        for pattern_id in _as_str_list(row.get("pattern_ids")):
            yield DECISION_MATRIX_NAME, pattern_id

    audit = _as_dict(inputs.get(AUDIT_NAME))
    for row in _as_list(audit.get("intentional_router_overlaps")):
        if isinstance(row, Mapping) and isinstance(row.get("pattern_id"), str):
            yield AUDIT_NAME, row["pattern_id"]


def _find_cycle(nodes: set[str], edges: Iterable[Mapping[str, Any]]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_find_cycle` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
        """
        [ACTION]
        - Teleology: Implements `_find_cycle.visit` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
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


def _overlay_name_exists(input_dir: Path, overlay_ref: str) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_overlay_name_exists` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = Path(overlay_ref)
    if (input_dir / overlay_ref).is_file():
        return True
    return (input_dir / path.name).is_file()


def _validate_report(
    *,
    input_dir: Path,
    manifest: Mapping[str, Any],
    inputs: Mapping[str, Any],
    load_findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_report` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings = list(load_findings)
    source_manifest = _source_manifest(input_dir, manifest)
    for row in source_manifest["inputs"]:
        if row.get("exists") is not True:
            findings.append(
                _finding(
                    severity="error",
                    rule="missing_manifest_input",
                    source=str(row.get("path")),
                    message="Manifest input is missing from the route-readiness bundle.",
                )
            )
        elif row.get("digest_status") == "mismatch":
            findings.append(
                _finding(
                    severity="error",
                    rule="manifest_digest_mismatch",
                    source=str(row.get("path")),
                    message="Manifest input digest does not match the copied macro source digest.",
                    expected=row.get("expected_sha256"),
                    observed=row.get("sha256"),
                )
            )

    ledger_path = input_dir / LEDGER_NAME
    ledger_rows = _read_jsonl_rows(ledger_path)
    invalid_jsonl = [row for row in ledger_rows if row.get("_invalid_jsonl")]
    for row in invalid_jsonl:
        findings.append(
            _finding(
                severity="error",
                rule="invalid_ledger_jsonl",
                source=LEDGER_NAME,
                message=str(row.get("_error") or "invalid jsonl row"),
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
                source=LEDGER_NAME,
                identifier=str(pattern_id),
                message="Extracted pattern ledger pattern_id values must be unique.",
            )
        )

    audit = _as_dict(inputs.get(AUDIT_NAME))
    if audit.get("schema_version") != EXPECTED_AUDIT_SCHEMA:
        findings.append(
            _finding(
                severity="error",
                rule="audit_schema_mismatch",
                source=AUDIT_NAME,
                message="Route readiness audit schema_version does not match.",
                expected=EXPECTED_AUDIT_SCHEMA,
                observed=audit.get("schema_version"),
            )
        )

    actual_ledger_hash = _file_sha256(ledger_path)
    declared_source = _as_dict(audit.get("source_ledger"))
    if declared_source.get("parsed_pattern_row_count") != len(ledger_ids):
        findings.append(
            _finding(
                severity="error",
                rule="source_ledger_row_count_mismatch",
                source=AUDIT_NAME,
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
                source=AUDIT_NAME,
                message="Readiness audit source ledger hash is stale.",
                expected=actual_ledger_hash,
                observed=declared_source.get("sha256"),
            )
        )
    expected_source_evidence = f"{len(ledger_ids)} parsed pattern rows, sha256 {actual_ledger_hash}"
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
                source=AUDIT_NAME,
                message="Readiness audit must carry a source_ledger_freshness gate.",
            )
        )
    elif freshness_gate.get("evidence") != expected_source_evidence:
        findings.append(
            _finding(
                severity="error",
                rule="source_ledger_freshness_gate_evidence_mismatch",
                source=AUDIT_NAME,
                identifier="source_ledger_freshness",
                message="Readiness audit source ledger freshness gate evidence is stale.",
                expected=expected_source_evidence,
                observed=freshness_gate.get("evidence"),
            )
        )

    for overlay in _as_str_list(audit.get("input_overlays")):
        if not _overlay_name_exists(input_dir, overlay):
            findings.append(
                _finding(
                    severity="error",
                    rule="missing_input_overlay",
                    source=AUDIT_NAME,
                    identifier=overlay,
                    message="Readiness audit names an input overlay that is not in the public bundle.",
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
                    source=AUDIT_NAME,
                    identifier=key,
                    message="Readiness audit summary is stale or inconsistent with companion overlays.",
                    expected=expected,
                    observed=observed,
                )
            )

    router = _as_dict(inputs.get(ROUTER_NAME))
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
                source=ROUTER_NAME,
                message="Every duplicate family-router pattern ref must be listed as an intentional overlap.",
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
                    message="Routing overlay references a pattern_id that is absent from the ledger.",
                )
            )

    fixture = _as_dict(inputs.get(FIXTURE_SPECS_NAME))
    fixture_specs = [row for row in _as_list(fixture.get("organ_fixture_specs")) if isinstance(row, Mapping)]
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
            if not contract.get(key):
                findings.append(
                    _finding(
                        severity="error",
                        rule="fixture_contract_missing_required_key",
                        source=FIXTURE_SPECS_NAME,
                        identifier=f"{spec_id}:{key}",
                        message="Fixture specs must carry executable inputs, negative cases, validator/check, and anti-claim.",
                    )
                )
        if not _as_str_list(row.get("route_to_organ_ids")):
            findings.append(
                _finding(
                    severity="error",
                    rule="fixture_spec_missing_route_to_organ_ids",
                    source=FIXTURE_SPECS_NAME,
                    identifier=spec_id,
                    message="Fixture spec must name the organ ids it can make selectable.",
                )
            )

    readiness_rows = [row for row in _as_list(audit.get("organ_readiness")) if isinstance(row, Mapping)]
    readiness_ids = {
        row.get("readiness_id") for row in readiness_rows if isinstance(row.get("readiness_id"), str)
    }
    for row in readiness_rows:
        readiness_id = str(row.get("readiness_id") or "<missing>")
        if row.get("individual_row_selection") != "forbidden":
            findings.append(
                _finding(
                    severity="error",
                    rule="readiness_allows_individual_row_selection",
                    source=AUDIT_NAME,
                    identifier=readiness_id,
                    message="Readiness rows must forbid individual row selection.",
                    observed=row.get("individual_row_selection"),
                )
            )
        route_to = _as_str_list(row.get("route_to_organ_ids"))
        if not route_to:
            findings.append(
                _finding(
                    severity="error",
                    rule="readiness_missing_route_to_organ_ids",
                    source=AUDIT_NAME,
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
                    source=AUDIT_NAME,
                    identifier=readiness_id,
                    message="Readiness route_to_organ_ids must be backed by fixture specs.",
                    observed=missing_fixture_routes,
                )
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
                source=AUDIT_NAME,
                message="Selector contract must say a pattern-id route is not leaf readiness.",
            )
        )
    observed_openings = set(_as_str_list(selector.get("selector_must_open")))
    missing_openings = sorted(REQUIRED_SELECTOR_OPENINGS - observed_openings)
    if missing_openings:
        findings.append(
            _finding(
                severity="error",
                rule="selector_contract_missing_required_opening",
                source=AUDIT_NAME,
                message="Selector contract must open all companion overlays.",
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
                source=AUDIT_NAME,
                message="Selector contract names targets that are not defined.",
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
                source=AUDIT_NAME,
                message="Root substrate lock references undefined readiness ids.",
                observed=missing_root_readiness,
            )
        )

    dag = _as_dict(inputs.get(DAG_NAME))
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
                    source=DAG_NAME,
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
                source=DAG_NAME,
                message="Organ dependency DAG must remain acyclic.",
                observed=cycle,
            )
        )

    route_cards = _as_dict(inputs.get(ROUTE_CARDS_NAME))
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
                    source=ROUTE_CARDS_NAME,
                    identifier=card_id,
                    message="Route card organ_ids must resolve in the dependency DAG.",
                    observed=missing_card_nodes,
                )
            )

    hard_no_standalone_ids = set(
        _as_str_list(_as_dict(inputs.get(DECISION_MATRIX_NAME)).get("hard_no_standalone_pattern_ids"))
    )
    selectable_pattern_ids = selector_targets & ledger_ids
    illegal_selectable = sorted(hard_no_standalone_ids & selectable_pattern_ids)
    if illegal_selectable:
        findings.append(
            _finding(
                severity="error",
                rule="hard_no_standalone_marked_selectable",
                source=AUDIT_NAME,
                message="Hard no-standalone pattern ids cannot appear in selector targets.",
                observed=illegal_selectable,
            )
        )

    error_count = sum(1 for finding in findings if finding.get("severity") == "error")
    warning_count = sum(1 for finding in findings if finding.get("severity") == "warning")
    return {
        "schema_version": REPORT_SCHEMA,
        "artifact_role": "public_pattern_route_readiness_machine_check",
        "authority_boundary": "source_faithful_public_refactor_over_copied_macro_route_overlays_not_leaf_authority",
        "governing_standard": STANDARD_NAME,
        "bundle_id": manifest.get("bundle_id"),
        "source_manifest": source_manifest,
        "summary": {
            "status": "ok" if error_count == 0 else "needs_route_readiness_repair",
            "error_count": error_count,
            "warning_count": warning_count,
            "ledger_pattern_count": len(ledger_ids),
            "organ_readiness_count": len(readiness_rows),
            "fixture_spec_count": len(fixture_specs),
            "route_card_count": len(_as_list(_as_dict(inputs.get(ROUTE_CARDS_NAME)).get("route_cards"))),
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
            "selector_may_select_after_roots": _as_str_list(selector.get("selector_may_select_after_roots")),
            "selector_must_fold_or_defer": _as_str_list(selector.get("selector_must_fold_or_defer")),
            "selector_must_open": _as_str_list(selector.get("selector_must_open")),
            "hard_no_standalone_pattern_id_count": len(hard_no_standalone_ids),
            "standalone_pattern_leaf_candidate_count": observed_summary.get(
                "standalone_pattern_leaf_candidate_count"
            ),
        },
        "findings": findings,
        "anti_claim": ANTI_CLAIM,
    }


def build_route_readiness_validation_report(input_dir: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_route_readiness_validation_report` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    bundle_dir = Path(input_dir)
    manifest = read_json_strict(bundle_dir / MANIFEST_NAME)
    if not isinstance(manifest, dict):
        manifest = {}
    load_findings: list[dict[str, Any]] = []
    inputs = _load_json_inputs(bundle_dir, load_findings)
    return _validate_report(
        input_dir=bundle_dir,
        manifest=manifest,
        inputs=inputs,
        load_findings=load_findings,
    )


def validate_route_readiness_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_route_readiness_bundle` for `microcosm_core.macro_tools.pattern_route_readiness` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    bundle_dir = Path(input_dir)
    public_root = _bundle_public_root(bundle_dir)
    manifest = read_json_strict(bundle_dir / MANIFEST_NAME)
    if not isinstance(manifest, dict):
        manifest = {}
    report = build_route_readiness_validation_report(bundle_dir)
    input_paths = [bundle_dir / name for name in ALL_INPUT_NAMES if (bundle_dir / name).is_file()]
    forbidden_terms = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan_result = scan_paths(input_paths, forbidden_classes=forbidden_terms, display_root=public_root)
    source_report = read_json_strict(bundle_dir / SOURCE_REPORT_NAME)
    if not isinstance(source_report, dict):
        source_report = {}

    status = (
        PASS
        if scan_result.get("status") == PASS and report.get("summary", {}).get("status") == "ok"
        else "blocked"
    )
    receipt_ref = _receipt_ref(Path(out_dir) / BUNDLE_RESULT_NAME, public_root)
    public_runtime_refs = [
        public_relative_path(path, display_root=public_root)
        for path in input_paths
    ]
    result = {
        "schema_version": "microcosm_pattern_route_readiness_bundle_validation_result_v1",
        "receipt_id": "receipt.microcosm.pattern_binding_contract.route_readiness_bundle",
        "organ_id": "pattern_binding_contract",
        "fixture_id": "first_wave.pattern_binding_contract.exported_route_readiness_bundle",
        "created_at": utc_now(),
        "status": status,
        "input_mode": "exported_route_readiness_bundle",
        "bundle_id": manifest.get("bundle_id"),
        "bundle_manifest_schema_version": manifest.get("schema_version"),
        "source_import_class": manifest.get("source_import_class"),
        "copied_macro_source_refs": manifest.get("copied_macro_source_refs", []),
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
        "counts_as_real_substrate_progress": status == PASS,
        "real_substrate_progress_count": 1 if status == PASS else 0,
        "route_readiness_summary": report.get("summary", {}),
        "route_readiness_report": report,
        "source_validation_report_summary": source_report.get("summary", {}),
        "source_validation_report_ref": public_relative_path(
            bundle_dir / SOURCE_REPORT_NAME,
            display_root=public_root,
        ),
        "selection_contract": report.get("selection_contract", {}),
        "source_manifest": report.get("source_manifest", {}),
        "public_runtime_refs": public_runtime_refs,
        "secret_exclusion_scan": scan_result,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "receipt_paths": [receipt_ref],
    }
    write_json_atomic(Path(out_dir) / BUNDLE_RESULT_NAME, result)
    return result
