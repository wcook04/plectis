"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.self_ignorance_coverage_ledger` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, EXPECTED_NEGATIVE_CASES, EXPECTED_COVERAGE_SCOPE, EXPECTED_SYSTEM_ATLAS_CHECK_COMMAND, ALLOWED_SYSTEM_ATLAS_CHECK_STATUSES, MATERIALIZED_PREFIX_BY_KIND, MATERIALIZED_ENTITY_KIND_BY_KIND, AUTHORITY_CEILING, ANTI_CLAIM, SPEC, evaluate, evaluate_negative_case, run, run_self_ignorance_bundle, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common, system.lib.kind_atlas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from microcosm_core.organs._crown_jewel_common import (
    PASS,
    CrownJewelSpec,
    finding,
    load_json_object,
    main_for_spec,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "self_ignorance_coverage_ledger"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
EXPECTED_NEGATIVE_CASES = {
    "forbidden_absence_inference": ("SELF_IGNORANCE_FORBIDDEN_ABSENCE_INFERENCE",),
    "coverage_debt_mismatch": ("SELF_IGNORANCE_COVERAGE_DEBT_MISMATCH",),
}
EXPECTED_COVERAGE_SCOPE = "live_kind_atlas_vs_generated_system_atlas_materialization_snapshot"
EXPECTED_SYSTEM_ATLAS_CHECK_COMMAND = "./repo-python tools/meta/factory/build_system_atlas.py --check"
ALLOWED_SYSTEM_ATLAS_CHECK_STATUSES = {
    PASS,
    "blocked_source_inputs_changed_since_artifact_generation",
}
MATERIALIZED_PREFIX_BY_KIND = {
    "concepts": "concept_",
    "mechanisms": "mechanism_",
    "paper_modules": "pm_",
    "principles": "principle_",
    "standards": "std_",
    "task_ledger": "workitem_",
}
MATERIALIZED_ENTITY_KIND_BY_KIND = {
    "frontend_components": "FrontendComponent",
    "frontend_views": "FrontendView",
    "raw_seed_shards": "RawSeedShard",
}
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "known_kind_atlas_to_system_atlas_materialization_debt_projection_only",
    "literal_unknown_unknown_omniscience_authorized": False,
    "absence_proof_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Self-ignorance coverage ledger projects known coverage debt between live "
    "Kind Atlas rows and generated System Atlas materialization counts. It does "
    "not claim literal unknown-unknown omniscience, absence proof, source "
    "mutation, or release authority."
)

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Self-ignorance coverage ledger",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=f"{ORGAN_ID}_result.json",
    board_name=f"{ORGAN_ID}_board.json",
    validation_receipt_name=f"{ORGAN_ID}_validation_receipt.json",
    bundle_result_name=f"exported_{ORGAN_ID}_bundle_validation_result.json",
    card_schema_version=f"{ORGAN_ID}_command_card_v1",
    required_inputs=(
        "kind_atlas_rows.json",
        "materialized_entities.json",
        "projection_protocol.json",
        "system_atlas_graph.json",
    ),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/self_ignorance_coverage_ledger/"
        "exported_self_ignorance_coverage_ledger_bundle/source_module_manifest.json"
    ),
    source_required_anchors={
        "tools/meta/factory/build_system_atlas.py": ("System Atlas", "kind"),
    },
    bundle_input_mode="exported_self_ignorance_coverage_ledger_bundle",
)


def _int_or_none(value: object) -> int | None:
    """
    [ACTION]
    - Teleology: Implements `_int_or_none` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _materialized_ids_by_kind_from_graph(
    entities: list[dict[str, Any]],
    selected_kind_ids: set[str],
) -> dict[str, set[str]]:
    """
    [ACTION]
    - Teleology: Implements `_materialized_ids_by_kind_from_graph` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ids_by_kind: dict[str, set[str]] = {kind_id: set() for kind_id in selected_kind_ids}
    for entity in entities:
        entity_id = str(entity.get("id") or entity.get("entity_id") or "")
        entity_kind = str(entity.get("kind") or entity.get("entity_kind") or "")
        if not entity_id:
            continue
        for kind_id in selected_kind_ids:
            prefix = MATERIALIZED_PREFIX_BY_KIND.get(kind_id)
            if prefix and entity_id.startswith(prefix):
                ids_by_kind.setdefault(kind_id, set()).add(entity_id)
                continue
            expected_kind = MATERIALIZED_ENTITY_KIND_BY_KIND.get(kind_id)
            if expected_kind and entity_kind == expected_kind:
                ids_by_kind.setdefault(kind_id, set()).add(entity_id)
    return ids_by_kind


def _system_atlas_graph_materialization(
    input_dir: Path,
    findings: list[dict[str, Any]],
    selected_kind_ids: set[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_system_atlas_graph_materialization` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    graph_path = input_dir / "system_atlas_graph.json"
    graph = load_json_object(
        graph_path,
        findings,
        label="System Atlas graph/source artifact",
    )
    entities = [row for row in graph.get("entities", []) if isinstance(row, dict)]
    if not entities:
        findings.append(
            finding(
                "SELF_IGNORANCE_REAL_ATLAS_GRAPH_EMPTY",
                "System Atlas graph/source artifact must carry materialized entity rows.",
                subject_id="system_atlas_graph.json",
            )
        )
    generated_by = str(graph.get("generated_by") or "")
    if generated_by and generated_by != "tools/meta/factory/build_system_atlas.py":
        findings.append(
            finding(
                "SELF_IGNORANCE_ATLAS_GRAPH_BUILDER_MISMATCH",
                "System Atlas graph/source artifact must be produced by build_system_atlas.py.",
                expected="tools/meta/factory/build_system_atlas.py",
                observed=generated_by,
            )
        )
    return {
        "status": PASS if entities else "blocked",
        "entity_count": len(entities),
        "generated_at": graph.get("generated_at"),
        "generated_by": graph.get("generated_by"),
        "ids_by_kind": _materialized_ids_by_kind_from_graph(entities, selected_kind_ids),
        "source_ref": "system_atlas_graph.json",
        "body_in_receipt": False,
    }


def _live_system_atlas_graph_materialization(
    public_root: Path,
    selected_kind_ids: set[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_live_system_atlas_graph_materialization` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    repo_root = _repo_root_for_live_kind_atlas(public_root)
    if repo_root is None:
        return {
            "status": "unavailable",
            "used": False,
            "reason": "macro_repo_root_not_available",
            "body_in_receipt": False,
        }
    graph_path = repo_root / "state/system_atlas/system_atlas.graph.json"
    if not graph_path.is_file():
        return {
            "status": "unavailable",
            "used": False,
            "reason": "live_system_atlas_graph_missing",
            "source_ref": "state/system_atlas/system_atlas.graph.json",
            "body_in_receipt": False,
        }
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "blocked",
            "used": False,
            "reason": f"live_system_atlas_graph_invalid:{exc.__class__.__name__}",
            "source_ref": "state/system_atlas/system_atlas.graph.json",
            "body_in_receipt": False,
        }
    entities = [row for row in graph.get("entities", []) if isinstance(row, dict)]
    ids_by_kind = _materialized_ids_by_kind_from_graph(entities, selected_kind_ids)
    return {
        "status": PASS,
        "used": True,
        "entity_count": len(entities),
        "generated_at": graph.get("generated_at"),
        "generated_by": graph.get("generated_by"),
        "ids_by_kind": ids_by_kind,
        "source_ref": "state/system_atlas/system_atlas.graph.json",
        "body_in_receipt": False,
    }


def _expected_entity_ids_source_backed(
    kind_atlas: dict[str, Any],
    graph_materialization: dict[str, Any],
) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_expected_entity_ids_source_backed` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        kind_atlas.get("materialized_entity_id_source_ref")
        == graph_materialization.get("source_ref")
        and graph_materialization.get("generated_by")
        == "tools/meta/factory/build_system_atlas.py"
    )


def _repo_root_for_live_kind_atlas(public_root: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_repo_root_for_live_kind_atlas` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidate = public_root.parent
    if (candidate / "system/lib/kind_atlas.py").is_file():
        return candidate
    return None


def _repo_root_for_source_validation(public_root: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_repo_root_for_source_validation` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidate = _repo_root_for_live_kind_atlas(public_root)
    if candidate is not None:
        return candidate
    cwd = Path.cwd().resolve(strict=False)
    if (cwd / "system/lib/kind_atlas.py").is_file():
        return cwd
    return None


def _entity_source_exists(repo_root: Path, kind_id: str, entity_id: str) -> bool | None:
    """
    [ACTION]
    - Teleology: Implements `_entity_source_exists` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if kind_id == "concepts" and entity_id.startswith("concept_"):
        concept_id = entity_id.removeprefix("concept_")
        return any((repo_root / "codex/doctrine/concepts").glob(f"{concept_id}_*.json"))
    if kind_id == "mechanisms" and entity_id.startswith("mechanism_"):
        mechanism_id = entity_id.removeprefix("mechanism_")
        return any((repo_root / "codex/doctrine/mechanisms").glob(f"{mechanism_id}_*.json"))
    if kind_id == "standards" and entity_id.startswith("std_"):
        return any((repo_root / "codex/standards").glob(f"**/{entity_id}.json"))
    return None


def _source_validate_expected_entity_ids(
    public_root: Path,
    ids_by_kind: dict[str, set[str]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_validate_expected_entity_ids` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    repo_root = _repo_root_for_source_validation(public_root)
    if repo_root is None:
        return {
            "status": "unavailable",
            "used": False,
            "reason": "macro_repo_root_not_available",
            "body_in_receipt": False,
        }
    unsupported: dict[str, list[str]] = {}
    checked_count = 0
    for kind_id, entity_ids in sorted(ids_by_kind.items()):
        for entity_id in sorted(entity_ids):
            exists = _entity_source_exists(repo_root, kind_id, entity_id)
            if exists is None:
                continue
            checked_count += 1
            if not exists:
                unsupported.setdefault(kind_id, []).append(entity_id)
    return {
        "status": PASS if not unsupported else "blocked",
        "used": True,
        "checked_entity_count": checked_count,
        "unsupported_entity_ids": unsupported,
        "body_in_receipt": False,
    }


def _live_kind_atlas_rows(
    public_root: Path,
    kind_ids: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_live_kind_atlas_rows` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    repo_root = _repo_root_for_live_kind_atlas(public_root)
    if repo_root is None or not kind_ids:
        return {}, {
            "status": "unavailable",
            "used": False,
            "reason": "macro_kind_atlas_builder_not_available",
        }
    try:
        from system.lib.kind_atlas import build_kind_atlas
    except ImportError as exc:
        return {}, {
            "status": "unavailable",
            "used": False,
            "reason": f"import_failed:{exc.__class__.__name__}",
        }
    payload = build_kind_atlas(repo_root, band="flag", ids=kind_ids)
    rows = payload.get("rows") if isinstance(payload, dict) else []
    live_rows = {
        str(row.get("kind_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("kind_id")
    }
    missing = [kind_id for kind_id in kind_ids if kind_id not in live_rows]
    return live_rows, {
        "status": "pass" if not missing else "partial",
        "used": bool(live_rows),
        "source": "system.lib.kind_atlas.build_kind_atlas",
        "repo_root_kind_atlas_ref": "system/lib/kind_atlas.py",
        "requested_kind_ids": kind_ids,
        "missing_kind_ids": missing,
        "projection_profile": payload.get("projection_profile"),
        "generated_at": payload.get("generated_at")
        or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _rows_with_live_kind_atlas_counts(
    rows: list[dict[str, Any]],
    public_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows_with_live_kind_atlas_counts` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    kind_ids = [
        str(row.get("kind_id"))
        for row in rows
        if row.get("kind_id") and str(row.get("kind_id")).strip()
    ]
    live_by_kind, recompute = _live_kind_atlas_rows(public_root, kind_ids)
    if not live_by_kind:
        return rows, recompute
    resolved: list[dict[str, Any]] = []
    for row in rows:
        kind_id = str(row.get("kind_id") or "")
        live = live_by_kind.get(kind_id)
        if not live:
            resolved.append(row)
            continue
        merged = dict(row)
        merged["fixture_declared_live_kind_atlas_row_count"] = row.get(
            "live_kind_atlas_row_count",
            row.get("kind_atlas_row_count"),
        )
        merged["live_kind_atlas_row_count"] = live.get("row_count")
        merged["live_kind_atlas_title"] = live.get("title")
        merged["live_kind_atlas_currentness"] = live.get("currentness")
        merged["live_kind_atlas_support_status"] = live.get("support_status")
        resolved.append(merged)
    return resolved, recompute


def _copied_build_system_atlas_evidence(source_manifest: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_copied_build_system_atlas_evidence` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    modules = source_manifest.get("modules") if isinstance(source_manifest, dict) else []
    for row in modules if isinstance(modules, list) else []:
        if not isinstance(row, dict):
            continue
        refs = {
            str(row.get("source_ref") or ""),
            str(row.get("target_ref") or ""),
            str(row.get("path") or ""),
            str(row.get("original_source_ref") or ""),
        }
        if any(ref.endswith("tools/meta/factory/build_system_atlas.py") for ref in refs):
            return {
                "status": "present",
                "source_import_class": source_manifest.get("source_import_class"),
                "module_id": row.get("module_id"),
                "path": row.get("path"),
                "source_ref": row.get("source_ref"),
                "target_ref": row.get("target_ref"),
                "original_source_ref": row.get("original_source_ref"),
                "source_ref_verification": row.get("source_ref_verification"),
                "source_to_target_relation": row.get("source_to_target_relation"),
                "digest_status": row.get("digest_status"),
                "line_count_status": row.get("line_count_status"),
                "source_target_sha256_match": row.get("source_target_sha256_match"),
                "target_expected_digest_match": row.get("target_expected_digest_match"),
                "public_safe_mode": row.get("public_safe_mode"),
                "body_in_receipt": False,
            }
    return {"status": "missing", "body_in_receipt": False}


def _projection_protocol_receipt(
    protocol: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_projection_protocol_receipt` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    finding_start = len(findings)
    coverage_scope = str(protocol.get("coverage_scope") or "")
    check_command = str(protocol.get("system_atlas_check_command") or "")
    check_status = str(protocol.get("system_atlas_check_status") or "")
    if coverage_scope != EXPECTED_COVERAGE_SCOPE:
        findings.append(
            finding(
                "SELF_IGNORANCE_PROJECTION_PROTOCOL_SCOPE_MISMATCH",
                "Projection protocol must bind the coverage scope to live Kind Atlas rows versus generated System Atlas materialization.",
                expected=EXPECTED_COVERAGE_SCOPE,
                observed=coverage_scope,
            )
        )
    if (
        check_command != EXPECTED_SYSTEM_ATLAS_CHECK_COMMAND
        or check_status not in ALLOWED_SYSTEM_ATLAS_CHECK_STATUSES
    ):
        findings.append(
            finding(
                "SELF_IGNORANCE_SYSTEM_ATLAS_CHECK_RECEIPT_INVALID",
                "Projection protocol must carry the build_system_atlas.py check receipt or a declared blocked-refresh receipt.",
                expected={
                    "system_atlas_check_command": EXPECTED_SYSTEM_ATLAS_CHECK_COMMAND,
                    "system_atlas_check_status": sorted(ALLOWED_SYSTEM_ATLAS_CHECK_STATUSES),
                },
                observed={
                    "system_atlas_check_command": check_command,
                    "system_atlas_check_status": check_status,
                },
            )
        )
    return {
        "status": PASS if len(findings) == finding_start else "blocked",
        "coverage_scope": coverage_scope,
        "system_atlas_check_command": check_command,
        "system_atlas_check_status": check_status,
        "system_atlas_refresh_blocked_by_active_source_claims": bool(
            protocol.get("system_atlas_refresh_blocked_by_active_source_claims")
        ),
        "body_in_receipt": False,
    }


def evaluate(input_dir: Path, _public_root: Path, _source_manifest: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    kind_atlas = load_json_object(input_dir / "kind_atlas_rows.json", findings, label="Kind Atlas rows")
    materialized = load_json_object(
        input_dir / "materialized_entities.json",
        findings,
        label="materialized Atlas entities",
    )
    protocol = load_json_object(
        input_dir / "projection_protocol.json",
        findings,
        label="projection protocol",
    )
    protocol_receipt = _projection_protocol_receipt(protocol, findings)
    supplied_rows = [row for row in kind_atlas.get("rows", []) if isinstance(row, dict)]
    rows, kind_atlas_recompute = _rows_with_live_kind_atlas_counts(supplied_rows, _public_root)
    selected_kind_ids = {
        str(row.get("kind_id") or "")
        for row in rows
        if str(row.get("kind_id") or "").strip()
    }
    graph_materialization = _system_atlas_graph_materialization(
        input_dir,
        findings,
        selected_kind_ids,
    )
    graph_ids_by_kind = {
        kind_id: set(ids)
        for kind_id, ids in graph_materialization.get("ids_by_kind", {}).items()
        if isinstance(ids, set)
    }
    expected_entity_source_validation = _source_validate_expected_entity_ids(
        _public_root,
        graph_ids_by_kind,
    )
    unsupported_source_ids = expected_entity_source_validation.get("unsupported_entity_ids")
    if unsupported_source_ids:
        findings.append(
            finding(
                "SELF_IGNORANCE_EXPECTED_ENTITY_ID_SOURCE_MISSING",
                "Graph-derived expected entity ids must resolve to real macro source files when the macro repo is available.",
                observed=unsupported_source_ids,
            )
        )
    graph_supplied = bool(graph_ids_by_kind)
    live_graph_materialization = _live_system_atlas_graph_materialization(
        _public_root,
        selected_kind_ids,
    )
    live_graph_ids_by_kind = {
        kind_id: set(ids)
        for kind_id, ids in live_graph_materialization.get("ids_by_kind", {}).items()
        if isinstance(ids, set)
    }
    live_graph_mismatches = {}
    if live_graph_ids_by_kind and graph_ids_by_kind:
        for kind_id in sorted(selected_kind_ids):
            bundled_ids = graph_ids_by_kind.get(kind_id, set())
            live_ids = live_graph_ids_by_kind.get(kind_id, set())
            if bundled_ids != live_ids:
                live_graph_mismatches[kind_id] = {
                    "bundled_ids_missing_from_live_graph": sorted(bundled_ids - live_ids),
                    "live_graph_ids_missing_from_bundled_slice": sorted(live_ids - bundled_ids),
                }
    if live_graph_mismatches:
        findings.append(
            finding(
                "SELF_IGNORANCE_LIVE_SYSTEM_ATLAS_GRAPH_MISMATCH",
                "Bundled System Atlas graph slice must match the live System Atlas graph when the macro repo is available.",
                observed=live_graph_mismatches,
                expected={
                    "bundled_ref": graph_materialization.get("source_ref"),
                    "live_ref": live_graph_materialization.get("source_ref"),
                },
            )
        )
    expected_ids_source_backed = _expected_entity_ids_source_backed(
        kind_atlas,
        graph_materialization,
    )
    if graph_supplied:
        entities = [
            {"kind_id": kind_id, "entity_id": entity_id}
            for kind_id, ids in sorted(graph_ids_by_kind.items())
            for entity_id in sorted(ids)
        ]
        materialized_ids = {
            entity_id
            for ids in graph_ids_by_kind.values()
            for entity_id in ids
        }
        materialized_count_by_kind: Counter[str] = Counter(
            {kind_id: len(ids) for kind_id, ids in graph_ids_by_kind.items()}
        )
    else:
        entities = [row for row in materialized.get("entities", []) if isinstance(row, dict)]
        materialized_ids = {str(row.get("entity_id")) for row in entities if row.get("entity_id")}
        materialized_count_by_kind = Counter()
        for row in entities:
            kind_id = str(row.get("kind_id") or "")
            if kind_id:
                materialized_count_by_kind[kind_id] += 1
    materialization_rows = [
        row for row in materialized.get("materialization_rows", []) if isinstance(row, dict)
    ]
    declared_materialized_count_by_kind: dict[str, int] = {}
    for row in materialization_rows:
        kind_id = str(row.get("kind_id") or "")
        count = _int_or_none(
            row.get("system_atlas_materialized_entity_count")
            if "system_atlas_materialized_entity_count" in row
            else row.get("materialized_entity_count")
        )
        if kind_id and count is not None:
            if graph_supplied:
                declared_materialized_count_by_kind[kind_id] = count
            else:
                materialized_count_by_kind[kind_id] = count
    count_mismatches = {
        kind_id: {
            "declared_materialized_count": declared_count,
            "graph_derived_materialized_count": int(materialized_count_by_kind.get(kind_id, 0)),
        }
        for kind_id, declared_count in sorted(declared_materialized_count_by_kind.items())
        if declared_count != int(materialized_count_by_kind.get(kind_id, 0))
    }
    if count_mismatches:
        findings.append(
            finding(
                "SELF_IGNORANCE_MATERIALIZATION_COUNT_NOT_GRAPH_DERIVED",
                "Declared materialization counts must match the real System Atlas graph-derived entity set.",
                observed=count_mismatches,
            )
        )
    expected_debt = {
        str(row.get("entity_id"))
        for row in kind_atlas.get("expected_known_debt", [])
        if isinstance(row, dict) and row.get("entity_id")
    }
    expected_debt_by_kind = {
        str(row.get("kind_id")): int(row["expected_debt_count"])
        for row in kind_atlas.get("expected_known_debt", [])
        if isinstance(row, dict)
        and row.get("kind_id")
        and isinstance(row.get("expected_debt_count"), int)
    }
    required_ids: set[str] = set()
    expected_ids_by_kind: dict[str, set[str]] = defaultdict(set)
    kind_counts: Counter[str] = Counter()
    live_row_count_by_kind: dict[str, int] = {}
    count_debt_rows: list[dict[str, Any]] = []
    observed_debt_by_kind: dict[str, int] = {}
    expected_entity_id_mismatches: dict[str, dict[str, Any]] = {}
    unsupported_expected_entity_ids: list[str] = []
    for row in rows:
        kind_id = str(row.get("kind_id") or "")
        kind_counts[kind_id] += 1
        declared_expected_entity_ids = set(_strings(row.get("expected_entity_ids")))
        graph_entity_ids = graph_ids_by_kind.get(kind_id, set())
        expected_entity_ids = graph_entity_ids if graph_supplied else declared_expected_entity_ids
        if declared_expected_entity_ids and graph_supplied and not expected_ids_source_backed:
            unsupported_expected_entity_ids.append(kind_id)
        if not expected_entity_ids:
            findings.append(
                finding(
                    "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_MISSING",
                    "Kind Atlas/System Atlas projection rows must provide source-backed materialized entity ids.",
                    subject_id=kind_id,
                )
            )
        expected_ids_by_kind[kind_id].update(expected_entity_ids)
        required_ids.update(expected_entity_ids)
        if (
            graph_supplied
            and expected_ids_source_backed
            and declared_expected_entity_ids
            and declared_expected_entity_ids != graph_entity_ids
        ):
            expected_entity_id_mismatches[kind_id] = {
                "expected_entity_ids_missing_from_graph": sorted(
                    declared_expected_entity_ids - graph_entity_ids
                ),
                "graph_materialized_ids_missing_from_expected": sorted(
                    graph_entity_ids - declared_expected_entity_ids
                ),
            }
        live_count = _int_or_none(
            row.get("live_kind_atlas_row_count")
            if "live_kind_atlas_row_count" in row
            else row.get("kind_atlas_row_count")
        )
        if kind_id and live_count is not None:
            materialized_count = int(materialized_count_by_kind.get(kind_id, 0))
            debt_count = max(live_count - materialized_count, 0)
            live_row_count_by_kind[kind_id] = live_count
            count_debt_rows.append(
                {
                    "kind_id": kind_id,
                    "live_kind_atlas_row_count": live_count,
                    "system_atlas_materialized_entity_count": materialized_count,
                    "known_coverage_debt_count": debt_count,
                    "debt_basis": "live_kind_atlas_row_count_minus_system_atlas_materialized_entity_count",
                }
            )
            if debt_count:
                observed_debt_by_kind[kind_id] = debt_count
    if unsupported_expected_entity_ids:
        findings.append(
            finding(
                "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_NOT_SOURCE_BACKED",
                "Declared expected_entity_ids are admissible only when backed by the build_system_atlas.py graph artifact.",
                observed=sorted(unsupported_expected_entity_ids),
                expected={
                    "materialized_entity_id_source_ref": graph_materialization.get("source_ref"),
                    "system_atlas_graph_generated_by": "tools/meta/factory/build_system_atlas.py",
                },
            )
        )
    if expected_entity_id_mismatches:
        findings.append(
            finding(
                "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_MISMATCH",
                "Declared expected_entity_ids must equal entity ids derived from the System Atlas graph.",
                observed=expected_entity_id_mismatches,
            )
        )
    missing_ids = sorted(required_ids - materialized_ids)
    unexpected_ids = sorted(materialized_ids - required_ids)
    if expected_debt and set(missing_ids) != expected_debt:
        findings.append(
            finding(
                "SELF_IGNORANCE_COVERAGE_DEBT_MISMATCH",
                "Projected known coverage debt must match the fixture expectation.",
                expected=sorted(expected_debt),
                observed=missing_ids,
            )
        )
    understated_debt = {
        kind_id: {
            "minimum_expected_debt_count": expected,
            "observed_debt_count": observed_debt_by_kind.get(kind_id, 0),
        }
        for kind_id, expected in expected_debt_by_kind.items()
        if observed_debt_by_kind.get(kind_id, 0) < expected
    }
    if understated_debt:
        findings.append(
            finding(
                "SELF_IGNORANCE_COVERAGE_DEBT_MISMATCH",
                "Projected count coverage debt must not understate the fixture's declared known-debt floor.",
                expected=dict(sorted(expected_debt_by_kind.items())),
                observed=dict(sorted(observed_debt_by_kind.items())),
            )
        )
    absence_policy = kind_atlas.get("absence_policy") if isinstance(kind_atlas.get("absence_policy"), dict) else {}
    if absence_policy.get("claims_unknown_unknowns_exhaustive") is True:
        findings.append(
            finding(
                "SELF_IGNORANCE_FORBIDDEN_ABSENCE_INFERENCE",
                "Coverage debt projection may not claim unknown-unknown exhaustiveness.",
                observed=True,
            )
        )
    coverage_scope = str(
        protocol.get("coverage_scope") or "known_fixture_kind_atlas_debt_only"
    )
    total_materialized_count = sum(materialized_count_by_kind.values()) if materialized_count_by_kind else len(entities)
    total_required_count = sum(live_row_count_by_kind.values()) or len(required_ids)
    total_known_debt_count = len(missing_ids) + sum(observed_debt_by_kind.values())
    coverage_debt_recomputed = bool(graph_supplied and live_row_count_by_kind)
    realness_rank = (
        4
        if (
            coverage_debt_recomputed
            and expected_ids_source_backed
            and kind_atlas_recompute.get("used")
            and protocol_receipt.get("status") == PASS
            and (
                live_graph_materialization.get("used")
                or not _repo_root_for_live_kind_atlas(_public_root)
            )
        )
        else 3
        if graph_supplied
        else 2
    )
    return {
        "status": PASS if not findings else "blocked",
        "kind_row_count": len(rows),
        "materialized_entity_count": total_materialized_count,
        "required_entity_count": total_required_count,
        "known_coverage_debt_count": total_known_debt_count,
        "known_coverage_debt_ids": missing_ids,
        "known_coverage_debt_by_kind": dict(sorted(observed_debt_by_kind.items())),
        "known_coverage_debt_rows": count_debt_rows,
        "expected_entity_id_count_by_kind": {
            kind_id: len(ids) for kind_id, ids in sorted(expected_ids_by_kind.items())
        },
        "expected_entity_id_mismatches": expected_entity_id_mismatches,
        "system_atlas_graph_materialization": {
            key: value
            for key, value in graph_materialization.items()
            if key != "ids_by_kind"
        },
        "live_system_atlas_graph_materialization": {
            key: value
            for key, value in live_graph_materialization.items()
            if key != "ids_by_kind"
        },
        "live_system_atlas_graph_crosscheck_used": bool(
            live_graph_materialization.get("used")
        ),
        "live_system_atlas_graph_mismatches": live_graph_mismatches,
        "kind_atlas_recompute": kind_atlas_recompute,
        "live_kind_atlas_recompute_used": bool(kind_atlas_recompute.get("used")),
        "copied_build_system_atlas_bundle_evidence": _copied_build_system_atlas_evidence(
            _source_manifest
        ),
        "live_kind_atlas_row_count_by_kind": dict(sorted(live_row_count_by_kind.items())),
        "fixture_declared_known_debt_floor_by_kind": dict(sorted(expected_debt_by_kind.items())),
        "expected_entity_ids_source_backed": expected_ids_source_backed,
        "expected_entity_id_source_validation": expected_entity_source_validation,
        "unexpected_materialized_ids": unexpected_ids,
        "kind_counts": dict(sorted(kind_counts.items())),
        "realness_evidence": {
            "realness_rank": realness_rank,
            "realness_rung": f"R{realness_rank}",
            "rung_state": (
                "real_kind_atlas_vs_system_atlas_projection_recompute"
                if realness_rank >= 4
                else "partial_projection_recompute"
            ),
            "kind_atlas_recompute_bound": bool(kind_atlas_recompute.get("used")),
            "system_atlas_graph_materialization_bound": graph_supplied,
            "live_system_atlas_graph_crosscheck_bound": bool(
                live_graph_materialization.get("used")
            ),
            "source_backed_expected_entity_ids": expected_ids_source_backed,
            "coverage_debt_recomputed_from_projection_counts": coverage_debt_recomputed,
            "baked_expected_entity_ids_sufficient": False,
            "rank_basis": [
                "live System Kind Atlas row counts",
                "build_system_atlas.py graph materialized entity ids",
                "live System Atlas graph cross-check when macro repo is available",
                "source-backed expected entity id provenance",
                "count-debt recompute from projection rows",
                "projection protocol build_system_atlas.py check receipt",
            ],
        },
        "literal_unknown_unknown_omniscience_authorized": False,
        "coverage_scope": coverage_scope,
        "projection_protocol_receipt": protocol_receipt,
        "system_atlas_snapshot_generated_at": graph_materialization.get("generated_at")
        or materialized.get("system_atlas_snapshot_generated_at"),
        "system_atlas_graph_ref": graph_materialization.get("source_ref"),
        "system_atlas_graph_generated_by": graph_materialization.get("generated_by"),
        "system_atlas_refresh_blocked_by_active_source_claims": bool(
            protocol.get("system_atlas_refresh_blocked_by_active_source_claims")
        ),
        "findings": findings,
    }


def _write_json(path: Path, payload: object) -> None:
    """
    [ACTION]
    - Teleology: Implements `_write_json` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, declared filesystem outputs.
    """
    with TemporaryDirectory(prefix=f"{ORGAN_ID}-{case_id}-") as scratch:
        semantic_input = Path(scratch) / "input"
        semantic_input.mkdir(parents=True, exist_ok=True)
        for name in SPEC.required_inputs:
            if (input_dir / name).is_file():
                shutil.copy2(input_dir / name, semantic_input / name)

        rows_path = semantic_input / "kind_atlas_rows.json"
        rows = json.loads(rows_path.read_text(encoding="utf-8"))
        if case_id == "forbidden_absence_inference":
            absence_policy = rows.get("absence_policy")
            if not isinstance(absence_policy, dict):
                absence_policy = {}
            absence_policy["claims_unknown_unknowns_exhaustive"] = True
            rows["absence_policy"] = absence_policy
            _write_json(rows_path, rows)
        elif case_id == "coverage_debt_mismatch":
            graph_path = semantic_input / "system_atlas_graph.json"
            mutated = False
            if graph_path.is_file():
                graph = json.loads(graph_path.read_text(encoding="utf-8"))
                entities = graph.get("entities")
                if isinstance(entities, list) and entities:
                    entities.pop()
                    _write_json(graph_path, graph)
                    mutated = True
            else:
                materialized_path = semantic_input / "materialized_entities.json"
                materialized = json.loads(materialized_path.read_text(encoding="utf-8"))
                materialization_rows = materialized.get("materialization_rows")
                if isinstance(materialization_rows, list):
                    for row in materialization_rows:
                        if not isinstance(row, dict):
                            continue
                        count = _int_or_none(row.get("system_atlas_materialized_entity_count"))
                        if count is not None:
                            row["system_atlas_materialized_entity_count"] = count + 1
                            mutated = True
                            break
                if mutated:
                    _write_json(materialized_path, materialized)
            expected_debt = rows.get("expected_known_debt")
            if isinstance(expected_debt, list) and expected_debt:
                first = expected_debt[0]
                if isinstance(first, dict) and isinstance(first.get("expected_debt_count"), int):
                    first["expected_debt_count"] += 1
                else:
                    rows["expected_known_debt"] = expected_debt[:1]
            else:
                rows["expected_known_debt"] = []
            _write_json(rows_path, rows)
        else:
            return {
                "status": "blocked",
                "error_codes": ["SELF_IGNORANCE_NEGATIVE_CASE_UNSUPPORTED"],
                "body_in_receipt": False,
            }

        result = evaluate(semantic_input, public_root_for_path(input_dir), {})
        return {
            "status": result["status"],
            "error_codes": [
                str(row.get("error_code"))
                for row in result.get("findings", [])
                if isinstance(row, dict) and row.get("error_code")
            ],
            "body_in_receipt": False,
        }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_self_ignorance_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_self_ignorance_bundle` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=SPEC.bundle_input_mode,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.self_ignorance_coverage_ledger` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return main_for_spec(
        SPEC,
        argv,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="run-self-ignorance-bundle",
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
