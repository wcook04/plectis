from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from system.lib.raw_seed_atomization import REPO_ROOT


REGISTRY_REL_PATH = Path("codex/derived/config_authority_registry.json")
STANDARD_REL_PATH = Path("codex/standards/std_config_authority_registry.json")
PAPER_MODULE_REL_PATH = Path("codex/doctrine/paper_modules/federated_config_plane.md")
REGISTRY_REBUILD_COMMAND = "./repo-python tools/meta/factory/build_config_authority_registry.py"

SUPPORTED_BANDS = {"cluster_flag", "flag", "card"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _rel(path: Path, *, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _path_id(prefix: str, rel_path: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", rel_path).strip("_").lower()
    return f"{prefix}.{slug}"


def _exists_status(path: Path) -> str:
    if path.exists():
        return "available"
    return "missing"


def _json_summary(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return {
            "shape": "object",
            "key_count": len(payload),
            "top_keys": sorted(str(key) for key in payload.keys())[:12],
        }
    if isinstance(payload, list):
        return {"shape": "array", "item_count": len(payload)}
    if payload is None:
        return {"shape": "missing_or_unreadable"}
    return {"shape": type(payload).__name__}


def _file_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    payload = _load_json(path) if path.suffix == ".json" else None
    summary = {
        "exists": True,
        "byte_count": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "content_sha256": _file_sha256(path),
    }
    if payload is not None:
        summary["json"] = _json_summary(payload)
    return summary


def _effective_trace(
    *,
    authority_path: str,
    summary: Any,
    consumers: list[str],
    validator: str,
    mutation_allowed: bool,
    mutation_blocked_reason: str,
    rollback_route: str | None,
    refresh_route: str | None,
    override_chain: list[str] | None = None,
    context_used: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "effective_value_or_redacted_summary": summary,
        "winning_source": authority_path,
        "authority_path": authority_path,
        "override_chain": override_chain or [authority_path],
        "context_used": context_used or ["repo_root"],
        "validator": validator,
        "consumers": consumers,
        "mutation_allowed": mutation_allowed,
        "mutation_blocked_reason": mutation_blocked_reason,
        "rollback_route": rollback_route,
        "refresh_or_rebuild_route": refresh_route,
    }


def _row(
    *,
    config_id: str,
    canonical_label: str,
    row_class: str,
    authority_owner: str,
    authority_path: str,
    loader: str,
    writer: str,
    governing_standard: str,
    schema_or_validator: str,
    value_semantics: str,
    context_dimensions: list[str],
    override_precedence: list[str],
    mutability_class: str,
    safe_edit_gate: str,
    rollback_or_restore: str | None,
    refresh_or_rebuild: str | None,
    consumer_edges: list[str],
    dependency_edges: list[str],
    projection_surfaces: list[str],
    frontend_routes: list[str],
    agent_entry_routes: list[str],
    diagnostics: list[dict[str, Any]],
    redaction_policy: str,
    exemption_reason: str | None,
    last_verified: str,
    effective_summary: Any,
    config_ref_aliases: list[str] | None = None,
) -> dict[str, Any]:
    mutation_allowed = mutability_class in {"compatibility_edit_endpoint", "guarded_compatibility_writer"}
    mutation_blocked_reason = (
        "mutation is owned by an existing compatibility endpoint, not by /api/config/surface"
        if mutation_allowed
        else "read_only_registry_v1_requires_writer_validator_preview_rollback_and_redaction"
    )
    field_manager = _derive_field_manager(
        row_class=row_class,
        mutability_class=mutability_class,
        authority_owner=authority_owner,
        authority_path=authority_path,
        writer=writer,
    )
    typed_consumer_edges = _derive_typed_edges(
        source_config_id=config_id,
        source_authority_path=authority_path,
        target_refs=consumer_edges,
        edge_kind="consumer",
        last_verified=last_verified,
    )
    typed_dependency_edges = _derive_typed_edges(
        source_config_id=config_id,
        source_authority_path=authority_path,
        target_refs=dependency_edges,
        edge_kind="dependency",
        last_verified=last_verified,
    )
    effective = _effective_trace(
        authority_path=authority_path,
        summary=effective_summary,
        consumers=consumer_edges,
        validator=schema_or_validator,
        mutation_allowed=mutation_allowed,
        mutation_blocked_reason=mutation_blocked_reason,
        rollback_route=rollback_or_restore,
        refresh_route=refresh_or_rebuild,
        override_chain=override_precedence,
        context_used=context_dimensions,
    )
    band_descriptions = _derive_band_descriptions(
        canonical_label=canonical_label,
        row_class=row_class,
        authority_owner=authority_owner,
        authority_path=authority_path,
        loader=loader,
        writer=writer,
        governing_standard=governing_standard,
        schema_or_validator=schema_or_validator,
        value_semantics=value_semantics,
        mutability_class=mutability_class,
        safe_edit_gate=safe_edit_gate,
        rollback_or_restore=rollback_or_restore,
        refresh_or_rebuild=refresh_or_rebuild,
        consumer_edges=consumer_edges,
        dependency_edges=dependency_edges,
        diagnostics=diagnostics,
        redaction_policy=redaction_policy,
        exemption_reason=exemption_reason,
        field_manager=field_manager,
        typed_consumer_edges=typed_consumer_edges,
        typed_dependency_edges=typed_dependency_edges,
        effective_trace=effective,
    )
    search_parts = [
        config_id,
        canonical_label,
        row_class,
        authority_owner,
        authority_path,
        loader,
        writer,
        governing_standard,
        schema_or_validator,
        value_semantics,
        mutability_class,
        safe_edit_gate,
        rollback_or_restore,
        refresh_or_rebuild,
        *consumer_edges,
        *dependency_edges,
        *projection_surfaces,
        *frontend_routes,
        *agent_entry_routes,
        *(config_ref_aliases or []),
    ]
    return {
        "config_id": config_id,
        "canonical_label": canonical_label,
        "class": row_class,
        "authority_owner": authority_owner,
        "authority_path": authority_path,
        "loader": loader,
        "writer": writer,
        "governing_standard": governing_standard,
        "schema_or_validator": schema_or_validator,
        "stored_default_current_effective_semantics": value_semantics,
        "context_dimensions": context_dimensions,
        "override_precedence": override_precedence,
        "mutability_class": mutability_class,
        "safe_edit_gate": safe_edit_gate,
        "rollback_or_restore": rollback_or_restore,
        "refresh_or_rebuild": refresh_or_rebuild,
        "consumer_edges": consumer_edges,
        "dependency_edges": dependency_edges,
        "projection_surfaces": projection_surfaces,
        "frontend_routes": frontend_routes,
        "agent_entry_routes": agent_entry_routes,
        "diagnostics": diagnostics,
        "redaction_policy": redaction_policy,
        "exemption_reason": exemption_reason,
        "last_verified": last_verified,
        "effective_trace": effective,
        "config_ref_aliases": config_ref_aliases or [],
        "field_manager": field_manager,
        "typed_consumer_edges": typed_consumer_edges,
        "typed_dependency_edges": typed_dependency_edges,
        "band_descriptions": band_descriptions,
        "search_text": " \n ".join(str(part) for part in search_parts if part),
    }


def _derive_band_descriptions(
    *,
    canonical_label: str,
    row_class: str,
    authority_owner: str,
    authority_path: str,
    loader: str,
    writer: str,
    governing_standard: str,
    schema_or_validator: str,
    value_semantics: str,
    mutability_class: str,
    safe_edit_gate: str,
    rollback_or_restore: str | None,
    refresh_or_rebuild: str | None,
    consumer_edges: list[str],
    dependency_edges: list[str],
    diagnostics: list[dict[str, Any]],
    redaction_policy: str,
    exemption_reason: str | None,
    field_manager: dict[str, Any],
    typed_consumer_edges: list[dict[str, Any]],
    typed_dependency_edges: list[dict[str, Any]],
    effective_trace: dict[str, Any],
) -> dict[str, str]:
    """[ACTION]
    - Teleology: Project compact navigation bands (atom / flag / card / deep) from the row contract so cold agents browse the registry at four depths without re-deriving structure from raw row JSON.
    - Mechanism: Compose each band from existing row fields plus derived sibling fields (effective_trace, field_manager, typed-edge counts). Per pri_001 (JSON is contract, markdown is projection): deep is generated, never hand-authored prose.
    - Reads: every row field plus three derived sibling structures.
    - Writes: None.
    - Guarantee: Returns a dict with atom/flag/card/deep keys, each a non-empty string.
    - Fails: None.
    - When-needed: Open when a row needs band_descriptions populated for the knob-depth projection slice.
    - Escalates-to: codex/standards/std_config_authority_registry.json::band_descriptions_contract
    """
    atom = canonical_label
    flag = f"{row_class} | {canonical_label} | mutability={mutability_class}"
    diagnostic_summary = (
        "no diagnostics" if not diagnostics else f"{len(diagnostics)} diagnostic(s) recorded"
    )
    card_lines = [
        f"authority: {authority_owner} @ {authority_path}",
        f"writer: {writer} (safe_edit_gate: {safe_edit_gate})",
        f"validator: {schema_or_validator}",
        f"redaction: {redaction_policy}",
        f"status: {diagnostic_summary}",
    ]
    card = "\n".join(card_lines)
    rollback_text = rollback_or_restore or "no rollback route declared"
    refresh_text = refresh_or_rebuild or "no refresh/rebuild route declared"
    exemption_text = exemption_reason or "none"
    deep_lines = [
        f"# {canonical_label}",
        f"class: {row_class}",
        f"authority_owner: {authority_owner}",
        f"authority_path: {authority_path}",
        f"loader: {loader}",
        f"writer: {writer}",
        f"governing_standard: {governing_standard}",
        f"schema_or_validator: {schema_or_validator}",
        f"value_semantics: {value_semantics}",
        f"mutability_class: {mutability_class}",
        f"safe_edit_gate: {safe_edit_gate}",
        f"rollback_or_restore: {rollback_text}",
        f"refresh_or_rebuild: {refresh_text}",
        f"redaction_policy: {redaction_policy}",
        f"exemption_reason: {exemption_text}",
        "",
        "# field_manager",
        f"  field_owner: {field_manager['field_owner']}",
        f"  writer_owner: {field_manager['writer_owner']}",
        f"  field_manager_class: {field_manager['field_manager_class']}",
        f"  allowed_operation_class: {field_manager['allowed_operation_class']}",
        f"  conflict_posture: {field_manager['conflict_posture']}",
        f"  compatibility_writer: {field_manager['compatibility_writer']}",
        "",
        "# edges",
        f"  consumer_edges: {len(consumer_edges)} (typed siblings: {len(typed_consumer_edges)})",
        f"  dependency_edges: {len(dependency_edges)} (typed siblings: {len(typed_dependency_edges)})",
        "",
        "# effective_trace summary",
        f"  winning_source: {effective_trace.get('winning_source')}",
        f"  mutation_allowed: {effective_trace.get('mutation_allowed')}",
        f"  mutation_blocked_reason: {effective_trace.get('mutation_blocked_reason')}",
        f"  rollback_route: {effective_trace.get('rollback_route')}",
        f"  refresh_or_rebuild_route: {effective_trace.get('refresh_or_rebuild_route')}",
        "",
        f"# diagnostics: {diagnostic_summary}",
    ]
    deep = "\n".join(deep_lines)
    return {
        "atom": atom,
        "flag": flag,
        "card": card,
        "deep": deep,
    }


_FIELD_MANAGER_CLASS_BY_MUTABILITY: dict[str, str] = {
    "compatibility_edit_endpoint": "compatibility_edit",
    "guarded_compatibility_writer": "compatibility_edit",
    "legacy_preview_apply_for_domain_files": "compatibility_edit",
    "domain_owner_writer_required": "domain_owner_edit",
    "standard_discipline_required": "domain_owner_edit",
    "generated_read_only": "generated_rebuild",
    "projection_owner_writer_required": "generated_rebuild",
    "runtime_writer_owned": "runtime_owned",
    "process_env_runtime_override": "runtime_owned",
    "host_local_read_only_metadata": "read_only",
    "read_only_projection": "read_only",
    "secret_metadata_only": "secret_metadata_only",
}

_ALLOWED_OPERATION_BY_FIELD_MANAGER_CLASS: dict[str, str] = {
    "read_only": "read",
    "compatibility_edit": "patch_compat",
    "domain_owner_edit": "patch_owner",
    "generated_rebuild": "rebuild_only",
    "runtime_owned": "runtime_writer_only",
    "secret_metadata_only": "metadata_only",
}


_TYPED_EDGE_VERB_DEFAULTS: dict[str, dict[str, str]] = {
    # Maps the legacy string-array edge_kind to a default base verb from
    # std_navigation_rosetta_grammar. Vocabulary additions (owns / consumes /
    # projects_into / derives_from / enforces / depends_on) are explicitly out
    # of scope for this slice — defaults must use existing base verbs.
    "consumer": {
        "verb_id": "feeds",
        "reverse_verb": "evidences",
        "forward_read": "this row feeds the target consumer",
        "reverse_read": "the target consumer evidences this row's authority",
        "authority_flow": "source_to_target",
        "reason": "default mapping: consumer_edge -> feeds (existing rosetta base verb)",
    },
    "dependency": {
        "verb_id": "routes_to",
        "reverse_verb": "evidences",
        "forward_read": "this row routes to the named dependency",
        "reverse_read": "the dependency evidences this row's reference",
        "authority_flow": "source_to_target",
        "reason": "default mapping: dependency_edge -> routes_to (conservative; no clean depends_on base verb in current rosetta vocabulary)",
    },
}

_TYPED_EDGE_LIMITATION_NOTE = (
    "v2 default mapping is conservative: consumer string entries route to verb_id=feeds and "
    "dependency string entries route to verb_id=routes_to. The rosetta grammar's base verbs do not "
    "include a 'depends_on' verb; future slices may add a complex_relation phrase if mapping "
    "fidelity matters more than the current sibling-projection coverage."
)


def _derive_typed_edges(
    *,
    source_config_id: str,
    source_authority_path: str,
    target_refs: list[str],
    edge_kind: str,
    last_verified: str,
) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Derive an edge_instance_shape-conformant sibling list of typed edges from a string-array edge field, preserving the legacy field for compatibility while exposing typed projections to consumers that need verb_id, authority_flow, validity, and bidirectional reads.
    - Mechanism: Map each target_ref string to one typed edge dict using the static verb-default table for edge_kind; populate impact_vector / confidence as draft-status defaults; mark validity.currentness_posture as candidate.
    - Reads: source_config_id, source_authority_path, target_refs, edge_kind, last_verified.
    - Writes: None.
    - Guarantee: Returns a list with one typed edge dict per target_ref; len matches len(target_refs); every edge has the 16 edge_instance_shape required keys plus a validity sub-shape with 4 keys.
    - Fails: Raises if edge_kind is not in _TYPED_EDGE_VERB_DEFAULTS (programming error).
    - When-needed: Open when the registry row contract gains typed sibling edges and a row needs typed_consumer_edges or typed_dependency_edges populated.
    - Escalates-to: codex/standards/std_navigation_rosetta_grammar.json::edge_instance_shape
    """
    if edge_kind not in _TYPED_EDGE_VERB_DEFAULTS:
        raise ValueError(f"unknown typed-edge kind: {edge_kind}")
    defaults = _TYPED_EDGE_VERB_DEFAULTS[edge_kind]
    edges: list[dict[str, Any]] = []
    for target_ref in target_refs:
        verb_id = defaults["verb_id"]
        edges.append({
            "edge_id": f"{source_config_id}::{verb_id}::{target_ref}",
            "source_atom_ref": source_config_id,
            "target_atom_ref": target_ref,
            "verb_id": verb_id,
            "reverse_verb": defaults["reverse_verb"],
            "forward_read": defaults["forward_read"],
            "reverse_read": defaults["reverse_read"],
            "impact_vector": {
                "semantic_flow": "medium",
                "authority_flow": "medium" if edge_kind == "dependency" else "low",
                "freshness_risk": "low",
                "mutation_risk": "low",
                "coverage_value": "medium",
                "scorer_status": "draft",
            },
            "confidence": {
                "score": 0.7,
                "tier": "medium",
                "reason": defaults["reason"],
                "scorer_status": "draft",
            },
            "reason": defaults["reason"],
            "extraction_mode": "authored",
            "authority_flow": defaults["authority_flow"],
            "validity": {
                "valid_from": last_verified,
                "valid_until": None,
                "invalidated_by": None,
                "currentness_posture": "candidate",
            },
            "evidence_ref": source_authority_path,
            "drilldown_ref": (
                f"./repo-python kernel.py --option-surface config_authorities --band card --ids {source_config_id}"
            ),
            "same_graph_contract": (
                "config_authority_registry typed-edge emission v0; sibling projection over legacy "
                "string-array consumer_edges/dependency_edges; v2 default verb mapping per "
                "_TYPED_EDGE_VERB_DEFAULTS; vocabulary additions deferred to future slice."
            ),
        })
    return edges


def _derive_field_manager(
    *,
    row_class: str,
    mutability_class: str,
    authority_owner: str,
    authority_path: str,
    writer: str,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Derive the field_manager block for one registry row from existing row inputs so v2 backfills 76 rows without per-row hand-edits.
    - Mechanism: Map mutability_class through a static table to field_manager_class; map field_manager_class to allowed_operation_class; default field_owner/writer_owner/field_path from existing row fields.
    - Reads: row_class, mutability_class, authority_owner, authority_path, writer.
    - Writes: None.
    - Guarantee: Returns a dict with all seven field_manager_contract fields populated; unknown mutability_class falls back to read_only/read with conflict_posture=none_known.
    - Fails: None.
    - When-needed: Open when a row populates field_manager metadata that future compatibility-writer warning or mutation-policy slices will consume.
    - Escalates-to: codex/standards/std_config_authority_registry.json::field_manager_contract
    """
    field_manager_class = _FIELD_MANAGER_CLASS_BY_MUTABILITY.get(mutability_class, "read_only")
    allowed_operation_class = _ALLOWED_OPERATION_BY_FIELD_MANAGER_CLASS.get(
        field_manager_class, "read"
    )
    return {
        "field_owner": authority_owner,
        "writer_owner": writer,
        "compatibility_writer": field_manager_class == "compatibility_edit",
        "field_path": authority_path,
        "field_manager_class": field_manager_class,
        "conflict_posture": "none_known",
        "allowed_operation_class": allowed_operation_class,
    }


def _diagnostic_for_path(repo_root: Path, rel_path: str) -> list[dict[str, Any]]:
    path = repo_root / rel_path
    if path.exists():
        return []
    return [
        {
            "severity": "warn",
            "code": "authority_path_missing",
            "message": f"Authority path {rel_path} is not present in this checkout.",
        }
    ]


def _master_config_rows(repo_root: Path, *, generated_at: str) -> list[dict[str, Any]]:
    path = repo_root / "master_config.json"
    payload = _load_json(path)
    if not isinstance(payload, Mapping):
        payload = {}
    rows: list[dict[str, Any]] = []
    for section in ("bridge", "execution", "observe", "pipeline", "paths", "ui"):
        section_payload = payload.get(section)
        rows.append(
            _row(
                config_id=f"master_config.{section}",
                canonical_label=f"master_config.json {section}",
                row_class="root_effective_config" if section != "ui" else "frontend_or_station_config",
                authority_owner="kernel/server config",
                authority_path="master_config.json",
                loader=(
                    "system/lib/kernel/config.py::load_master_config (canonical, no args) + "
                    "system/server/main.py::_read_master_config (server reader, line 846) + "
                    "system/lib/observe_runtime.py::load_master_config (observe runtime, repo_root arg, line 231) + "
                    "pipeline_control.load_master_config (repo-root file, used at system/lib/seed_pipeline_controller.py:37) + "
                    "tools/meta/apply/run_observe_plan.py::_load_master_config (apply tooling private, line 3420)"
                ),
                writer="/api/config/system" if section != "ui" else "/api/config/ui",
                governing_standard=STANDARD_REL_PATH.as_posix(),
                schema_or_validator="master_config JSON parse + existing route model validation",
                value_semantics="stored section participates in effective runtime config; compatibility endpoints own scoped edits",
                context_dimensions=["repo_root", "server_runtime", "ui_scope" if section == "ui" else "kernel_scope"],
                override_precedence=["master_config.json", "domain/runtime overrides where loaders explicitly merge them"],
                mutability_class="guarded_compatibility_writer" if section != "ui" else "compatibility_edit_endpoint",
                safe_edit_gate="/api/config/system" if section != "ui" else "/api/config/ui",
                rollback_or_restore="master_config.json.bak / master_config.base.json",
                refresh_or_rebuild=None,
                consumer_edges=[
                    "system/lib/kernel/config.py",
                    "system/server/main.py",
                    "/api/config/system",
                    "/api/config/ui" if section == "ui" else "/api/bridge/status",
                    "/settings",
                ],
                dependency_edges=[],
                projection_surfaces=["codex/derived/config_authority_registry.json", "system_surface_registry link"],
                frontend_routes=["/settings"],
                agent_entry_routes=["kernel option-surface config_authorities", "docs-route config plane"],
                diagnostics=_diagnostic_for_path(repo_root, "master_config.json"),
                redaction_policy="show structured section summary; redact fields only if later marked secret",
                exemption_reason=None,
                last_verified=generated_at,
                effective_summary=_json_summary(section_payload),
            )
        )
    return rows


def _config_file_row(
    repo_root: Path,
    rel_path: str,
    *,
    generated_at: str,
    row_class: str,
    authority_owner: str,
    governing_standard: str,
    loader: str,
    writer: str,
    mutability_class: str,
    consumer_edges: list[str],
    projection_surfaces: list[str] | None = None,
    frontend_routes: list[str] | None = None,
    agent_entry_routes: list[str] | None = None,
    redaction_policy: str = "metadata_and_shape_visible",
    exemption_reason: str | None = None,
) -> dict[str, Any]:
    aliases = [rel_path]
    if rel_path.startswith("codex/"):
        aliases.append(rel_path.removeprefix("codex/"))
    return _row(
        config_id=_path_id("config_path", rel_path),
        canonical_label=rel_path,
        row_class=row_class,
        authority_owner=authority_owner,
        authority_path=rel_path,
        loader=loader,
        writer=writer,
        governing_standard=governing_standard,
        schema_or_validator="JSON parse" if rel_path.endswith(".json") else "owning-domain parser",
        value_semantics="domain-owned stored config; registry records authority and effective trace summary",
        context_dimensions=["repo_root"],
        override_precedence=[rel_path, "owning domain loader/runtime context"],
        mutability_class=mutability_class,
        safe_edit_gate="owning domain writer; /api/config/surface is read-only in v1",
        rollback_or_restore="git history or owning domain backup",
        refresh_or_rebuild=None,
        consumer_edges=consumer_edges,
        dependency_edges=[],
        projection_surfaces=projection_surfaces or ["codex/derived/config_authority_registry.json"],
        frontend_routes=frontend_routes or [],
        agent_entry_routes=agent_entry_routes or ["kernel option-surface config_authorities", "docs-route config plane"],
        diagnostics=_diagnostic_for_path(repo_root, rel_path),
        redaction_policy=redaction_policy,
        exemption_reason=exemption_reason,
        last_verified=generated_at,
        effective_summary=_file_summary(repo_root / rel_path),
        config_ref_aliases=aliases,
    )


def _glob_rows(repo_root: Path, pattern: str, *, generated_at: str, **kwargs: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(repo_root.glob(pattern)):
        if not path.is_file():
            continue
        rows.append(_config_file_row(repo_root, _rel(path, repo_root=repo_root), generated_at=generated_at, **kwargs))
    return rows


def _host_adapter_row(repo_root: Path, rel_path: str, *, generated_at: str) -> dict[str, Any]:
    path = repo_root / rel_path
    children = []
    if path.exists() and path.is_dir():
        children = sorted(child.name for child in path.iterdir() if child.name != ".DS_Store")[:12]
    return _row(
        config_id=_path_id("host_adapter", rel_path),
        canonical_label=f"{rel_path} host adapter config",
        row_class="host_local_adapter_config",
        authority_owner="host adapter",
        authority_path=rel_path,
        loader="host-specific agent runtime",
        writer="host-specific adapter tools",
        governing_standard=STANDARD_REL_PATH.as_posix(),
        schema_or_validator="host adapter contract; metadata only in registry",
        value_semantics="host-local config can affect agent entry behavior but remains outside repo-root centralization",
        context_dimensions=["host", "agent_provider", "repo_root"],
        override_precedence=[rel_path, "provider runtime defaults"],
        mutability_class="host_local_read_only_metadata",
        safe_edit_gate="host adapter owner; never raw-edit through config surface",
        rollback_or_restore="host backup or git history when tracked",
        refresh_or_rebuild=None,
        consumer_edges=["agent entry surfaces", "host agent runtime"],
        dependency_edges=[],
        projection_surfaces=["codex/derived/config_authority_registry.json"],
        frontend_routes=[],
        agent_entry_routes=["host_agent_dotfile_surfaces paper module", "docs-route config plane"],
        diagnostics=_diagnostic_for_path(repo_root, rel_path),
        redaction_policy="metadata_only_no_raw_values",
        exemption_reason="host-local adapter config is indexed for discovery but not centralized or exposed as editable raw JSON",
        last_verified=generated_at,
        effective_summary={"exists": path.exists(), "entry_count": len(children), "sample_names": children},
    )


def _api_route_row(config_id: str, route: str, *, generated_at: str) -> dict[str, Any]:
    return _row(
        config_id=config_id,
        canonical_label=route,
        row_class="frontend_or_station_config",
        authority_owner="system/server/main.py",
        authority_path=route,
        loader="FastAPI route",
        writer="route handler" if route in {"/api/config/system", "/api/config/ui"} else "read-only route",
        governing_standard=STANDARD_REL_PATH.as_posix(),
        schema_or_validator="FastAPI response/request model",
        value_semantics="API surface over config state; not the source authority for domain-owned config",
        context_dimensions=["server_runtime", "http_api"],
        override_precedence=["route handler", "underlying authority path"],
        mutability_class="compatibility_edit_endpoint" if route in {"/api/config/system", "/api/config/ui"} else "read_only_projection",
        safe_edit_gate=route if route in {"/api/config/system", "/api/config/ui"} else "read-only",
        rollback_or_restore="underlying authority rollback",
        refresh_or_rebuild=None,
        consumer_edges=["system/server/ui/src/api.ts", "/settings"],
        dependency_edges=["master_config.json"] if route.startswith("/api/config/") else ["codex/derived/system_surface_registry.json"],
        projection_surfaces=["codex/derived/config_authority_registry.json", "codex/derived/system_surface_registry.json"],
        frontend_routes=["/settings"],
        agent_entry_routes=["docs-route config plane", "kernel option-surface config_authorities"],
        diagnostics=[],
        redaction_policy="route model controls returned payload",
        exemption_reason=None,
        last_verified=generated_at,
        effective_summary={"route": route, "method": "GET/PUT" if route in {"/api/config/system", "/api/config/ui"} else "GET"},
    )


def _mission_preflight_timeout_env_row(generated_at: str) -> dict[str, Any]:
    return _row(
        config_id="env.aiw_mission_preflight_git_timeout_seconds",
        canonical_label="AIW_MISSION_PREFLIGHT_GIT_TIMEOUT_SECONDS",
        row_class="runtime_coordination_state",
        authority_owner="mission transaction preflight",
        authority_path="environment:AIW_MISSION_PREFLIGHT_GIT_TIMEOUT_SECONDS",
        loader="system/lib/mission_transaction_landing_preflight.py::_git_command_timeout_seconds",
        writer="caller process environment",
        governing_standard=STANDARD_REL_PATH.as_posix(),
        schema_or_validator="float seconds; invalid or missing value falls back to DEFAULT_GIT_COMMAND_TIMEOUT_SECONDS=15.0; minimum 0.1",
        value_semantics=(
            "process-local runtime override for mission preflight Git subprocess timeout; "
            "registry records the contract and default, not the live per-shell value"
        ),
        context_dimensions=["process_environment", "repo_root", "mission_transaction_preflight_cli"],
        override_precedence=[
            "AIW_MISSION_PREFLIGHT_GIT_TIMEOUT_SECONDS",
            "system/lib/mission_transaction_landing_preflight.py::DEFAULT_GIT_COMMAND_TIMEOUT_SECONDS",
        ],
        mutability_class="process_env_runtime_override",
        safe_edit_gate="set per-process environment for the calling command; /api/config/surface remains read-only",
        rollback_or_restore="unset AIW_MISSION_PREFLIGHT_GIT_TIMEOUT_SECONDS",
        refresh_or_rebuild=None,
        consumer_edges=[
            "system/lib/mission_transaction_landing_preflight.py::_run_git",
            "tools/meta/control/mission_transaction_preflight.py --control-summary",
            "mission transaction preflight Git command diagnostics",
        ],
        dependency_edges=["system/lib/mission_transaction_landing_preflight.py::DEFAULT_GIT_COMMAND_TIMEOUT_SECONDS"],
        projection_surfaces=["codex/derived/config_authority_registry.json", "kernel option-surface config_authorities"],
        frontend_routes=[],
        agent_entry_routes=[
            "kernel option-surface config_authorities",
            "docs-route config plane",
            "mission_transaction_preflight.py --control-summary",
        ],
        diagnostics=[],
        redaction_policy="metadata_and_default_visible_live_env_value_not_recorded",
        exemption_reason="process-local environment override; the registry records authority and validation semantics rather than live values",
        last_verified=generated_at,
        effective_summary={
            "env_var": "AIW_MISSION_PREFLIGHT_GIT_TIMEOUT_SECONDS",
            "default_seconds": 15.0,
            "minimum_seconds": 0.1,
            "live_value_recorded": False,
            "invalid_value_behavior": "falls back to default",
        },
        config_ref_aliases=[
            "AIW_MISSION_PREFLIGHT_GIT_TIMEOUT_SECONDS",
            "mission_preflight_git_timeout",
            "mission_transaction_preflight.git_timeout_seconds",
        ],
    )


def _configs_board_row(generated_at: str) -> dict[str, Any]:
    return _row(
        config_id="frontend.configs_board.config_ref",
        canonical_label="ConfigsBoard config_ref resolver",
        row_class="frontend_or_station_config",
        authority_owner="Control Room frontend",
        authority_path="system/server/ui/src/components/views/ConfigsBoard.tsx",
        loader="graphSnapshot.nodes[].provenance.config_ref + config authority registry",
        writer="api.meta.previewApply / api.meta.commitApply for legacy domain config files",
        governing_standard=STANDARD_REL_PATH.as_posix(),
        schema_or_validator="config_ref authority_path match",
        value_semantics="frontend projection resolves config_ref to registry row before filename fallback",
        context_dimensions=["frontend_runtime", "mission_graph_snapshot"],
        override_precedence=["config_ref registry row", "codex file tree fallback diagnostic"],
        mutability_class="legacy_preview_apply_for_domain_files",
        safe_edit_gate="meta preview/apply flow only for domain-owned codex/configs files",
        rollback_or_restore="meta apply diff/commit history",
        refresh_or_rebuild="POST /api/config/surface/rebuild",
        consumer_edges=["Control Room ConfigsBoard", "mission graph provenance"],
        dependency_edges=["codex/configs/*.json", "codex/derived/config_authority_registry.json"],
        projection_surfaces=["/api/config/surface/search", "/api/config/surface/node/{config_id}"],
        frontend_routes=["/control/:mission configs tab"],
        agent_entry_routes=["docs-route config_ref"],
        diagnostics=[],
        redaction_policy="show registry metadata and selected domain file content only through existing file viewer",
        exemption_reason=None,
        last_verified=generated_at,
        effective_summary={"resolver": "registry-backed config_ref rows with filename fallback diagnostic"},
    )


def _settings_authority_bridge_row(repo_root: Path, *, generated_at: str) -> dict[str, Any]:
    return _row(
        config_id="frontend.settings_authority_bridge",
        canonical_label="Settings authority bridge read model",
        row_class="frontend_or_station_config",
        authority_owner="Settings frontend",
        authority_path="system/server/ui/src/lib/configSettingsAuthority.ts",
        loader="/settings consumes /api/config/surface before enabling scoped editors",
        writer="frontend read-model compiler; no config source writes",
        governing_standard=STANDARD_REL_PATH.as_posix(),
        schema_or_validator="system/server/ui/src/lib/__tests__/configSettingsAuthority.test.ts + system/server/ui/src/pages/__tests__/Settings.test.tsx",
        value_semantics="Settings and SettingsTuner preserve config authority rows, effective traces, and compatibility write gates without creating a parallel settings registry",
        context_dimensions=["frontend_runtime", "config_authority_projection", "ui_scope"],
        override_precedence=[
            "codex/derived/config_authority_registry.json via /api/config/surface",
            "master_config.json compatibility writer rows",
            "UI display attributes",
        ],
        mutability_class="read_only_projection",
        safe_edit_gate="read-only",
        rollback_or_restore="revert frontend source or rebuild bundle",
        refresh_or_rebuild="cd system/server/ui && npm test -- src/lib/__tests__/configSettingsAuthority.test.ts src/pages/__tests__/Settings.test.tsx",
        consumer_edges=[
            "system/server/ui/src/pages/Settings.tsx",
            "system/server/ui/src/components/SettingsTuner.tsx",
            "/settings",
        ],
        dependency_edges=[
            "master_config.bridge",
            "master_config.execution",
            "master_config.observe",
            "master_config.paths",
            "master_config.ui",
            "api.config.system",
            "api.config.ui",
            "codex/derived/config_authority_registry.json",
        ],
        projection_surfaces=[
            "frontend DOM data-config-authority-* attributes",
            "Settings diagnostics authority bridge panel",
        ],
        frontend_routes=["/settings"],
        agent_entry_routes=["kernel option-surface config_authorities", "docs-route config plane"],
        diagnostics=_diagnostic_for_path(repo_root, "system/server/ui/src/lib/configSettingsAuthority.ts"),
        redaction_policy="metadata_only_no_raw_values",
        exemption_reason=None,
        last_verified=generated_at,
        effective_summary={
            "source_route": "/api/config/surface",
            "source_artifact": REGISTRY_REL_PATH.as_posix(),
            "parallel_settings_registry_authorized": False,
            "system_write_gate": "/api/config/system",
            "ui_write_gate": "/api/config/ui",
        },
    )


def build_config_authority_registry(*, repo_root: Path = REPO_ROOT, generated_at: str | None = None) -> dict[str, Any]:
    root = Path(repo_root)
    stamp = generated_at or _utc_now()
    rows: list[dict[str, Any]] = []
    rows.extend(_master_config_rows(root, generated_at=stamp))
    rows.extend(
        _glob_rows(
            root,
            "codex/configs/*.json",
            generated_at=stamp,
            row_class="domain_authority_config",
            authority_owner="codex tool config domain",
            governing_standard="codex/standards/std_tool_config.json",
            loader="domain tool config loader",
            writer="domain apply lane or ConfigsBoard legacy preview/apply",
            mutability_class="domain_owner_writer_required",
            consumer_edges=["ConfigsBoard config_ref", "tool config consumers"],
            frontend_routes=["/control/:mission configs tab"],
        )
    )
    rows.extend(
        _glob_rows(
            root,
            "codex/substrate/configs/*.json",
            generated_at=stamp,
            row_class="domain_authority_config",
            authority_owner="substrate config domain",
            governing_standard="codex/standards/std_tool_config.json",
            loader="substrate config readers",
            writer="substrate owner lane",
            mutability_class="domain_owner_writer_required",
            consumer_edges=["substrate config consumers"],
        )
    )
    for rel_path, row_class, owner, loader, writer, mutability, consumers in (
        ("reactions.yaml", "domain_authority_config", "reactions engine", "tools/meta/control/reactions_engine.py", "reactions owner lane", "domain_owner_writer_required", ["reactions engine", "orchestration control plane"]),
        ("codex/doctrine/agent_bootstrap.json", "domain_authority_config", "agent entry substrate", "system/lib/agent_bootstrap_projection.py", "build_agent_bootstrap_projection.py", "domain_owner_writer_required", ["AGENTS.md", "CLAUDE.md", "CODEX.md", "kernel docs-route"]),
        ("codex/doctrine/compute/provider_registry.json", "domain_authority_config", "compute provider registry", "system/lib/model_profile_registry.py", "provider registry owner lane", "domain_owner_writer_required", ["model profile registry", "observe runtime"]),
        ("tools/meta/control/orchestration_state.json", "runtime_coordination_state", "orchestration control plane", "runtime control readers", "orchestration writer", "runtime_writer_owned", ["kernel pulse", "docs-route focus", "control room"]),
        ("tools/meta/observability/station_views.json", "frontend_or_station_config", "Station observability", "Station navigation projection", "Station view owner lane", "projection_owner_writer_required", ["Station navigation", "frontend navigation"]),
    ):
        rows.append(
            _config_file_row(
                root,
                rel_path,
                generated_at=stamp,
                row_class=row_class,
                authority_owner=owner,
                governing_standard=STANDARD_REL_PATH.as_posix(),
                loader=loader,
                writer=writer,
                mutability_class=mutability,
                consumer_edges=consumers,
                projection_surfaces=["codex/derived/config_authority_registry.json"],
                frontend_routes=["/settings"] if rel_path == "tools/meta/observability/station_views.json" else [],
            )
        )
    for rel_path, row_class, owner, loader, writer, mutability, consumers in (
        (
            "codex/doctrine/compression_profiles.json",
            "domain_authority_config",
            "render profile registry / compression profiles",
            "system/lib/raw_seed_compressed_projection.py + system/lib/agent_bootstrap_projection.py",
            "compression profiles owner lane",
            "domain_owner_writer_required",
            ["raw_seed_compressed_projection", "Type B grounding packet builder", "system packet builder"],
        ),
        (
            "codex/doctrine/routing_hologram.json",
            "domain_authority_config",
            "routing hologram doctrine",
            "system/lib/agent_bootstrap_projection.py + system/lib/kind_atlas.py",
            "routing hologram owner lane",
            "domain_owner_writer_required",
            ["AGENTS.md", "CLAUDE.md", "CODEX.md", "kernel agent_operating_packet", "kernel option-surface routing"],
        ),
        (
            "codex/doctrine/documentation_theory_index.json",
            "domain_authority_config",
            "documentation theory index",
            "system/lib/kernel/commands/docs.py + system/lib/agent_bootstrap_projection.py",
            "documentation theory owner lane",
            "domain_owner_writer_required",
            ["kernel docs-route", "kernel context-pack", "AGENTS.md routing"],
        ),
        (
            "codex/doctrine/skills/skill_registry.json",
            "domain_authority_config",
            "skill registry",
            "tools/meta/factory/build_skill_catalog_projection.py + system/lib/skill_catalog.py",
            "skill registry owner lane",
            "domain_owner_writer_required",
            ["kernel option-surface skills", ".agents/skills/", "codex/doctrine/skills/skill_map.md", "AGENTS.md skills section"],
        ),
        (
            "codex/doctrine/agent_bootstrap_live.json",
            "generated_projection_or_cache",
            "agent bootstrap projection builder",
            "system/lib/agent_bootstrap_projection.py readers",
            "tools/meta/factory/build_agent_bootstrap_projection.py",
            "generated_read_only",
            ["AGENTS.md live block", "CLAUDE.md live block", "CODEX.md live block", "kernel pulse"],
        ),
        (
            "codex/doctrine/agent_bootstrap_injection_strip.json",
            "generated_projection_or_cache",
            "agent bootstrap projection builder",
            "session bootstrap injection paths",
            "tools/meta/factory/build_agent_bootstrap_projection.py",
            "generated_read_only",
            ["session bootstrap injection", ".claude/hooks/runtime_hook.py"],
        ),
        (
            "codex/doctrine/agent_operating_packet.json",
            "generated_projection_or_cache",
            "agent operating packet builder",
            "system/lib/agent_operating_packet.py::load_agent_operating_packet_strip + system/lib/agent_bootstrap_projection.py",
            "system/lib/agent_operating_packet.py::build_agent_operating_packet",
            "generated_read_only",
            ["kernel --agent-operating-packet", "kernel context-pack", "kernel entry packet"],
        ),
    ):
        rows.append(
            _config_file_row(
                root,
                rel_path,
                generated_at=stamp,
                row_class=row_class,
                authority_owner=owner,
                governing_standard=STANDARD_REL_PATH.as_posix(),
                loader=loader,
                writer=writer,
                mutability_class=mutability,
                consumer_edges=consumers,
                projection_surfaces=["codex/derived/config_authority_registry.json"],
                exemption_reason=("generated projection; never source authority" if row_class == "generated_projection_or_cache" else None),
            )
        )
    rows.append(
        _config_file_row(
            root,
            "codex/doctrine/cognitive_operators.json",
            generated_at=stamp,
            row_class="domain_authority_config",
            authority_owner="cognitive operator registry",
            governing_standard="codex/standards/std_cognitive_operator.json",
            loader=(
                "system/lib/cognitive_operator_registry.py + "
                "system/lib/kernel/commands/generated_artifact_surfaces.py"
            ),
            writer="cognitive operator registry owner lane + tools/meta/factory/validate_cognitive_operator_registry.py",
            mutability_class="domain_owner_writer_required",
            consumer_edges=[
                "kernel option-surface cognitive_operators",
                "navigation_index_spine cognitive operator opening",
                "cognitive operator validator",
                "Kind Atlas cognitive_operators rows",
            ],
            projection_surfaces=[
                "codex/derived/config_authority_registry.json",
                "kernel option-surface cognitive_operators",
            ],
            agent_entry_routes=[
                "kernel option-surface cognitive_operators",
                "docs-route cognitive operator registry",
                "validate_cognitive_operator_registry.py --json",
            ],
        )
    )
    rows.extend(
        _glob_rows(
            root,
            "state/frontend_navigation/*.json",
            generated_at=stamp,
            row_class="generated_projection_or_cache",
            authority_owner="frontend navigation builder",
            governing_standard="codex/standards/std_frontend_component_index.json",
            loader="frontend navigation readers",
            writer="frontend navigation builder",
            mutability_class="generated_read_only",
            consumer_edges=["Station navigation", "Settings navigation"],
            projection_surfaces=["state/frontend_navigation/*.json"],
            redaction_policy="metadata_and_shape_visible",
            exemption_reason="generated projection; never source authority",
        )
    )
    rows.extend(
        _glob_rows(
            root,
            "state/system_atlas/*.json",
            generated_at=stamp,
            row_class="generated_projection_or_cache",
            authority_owner="system atlas builder",
            governing_standard=STANDARD_REL_PATH.as_posix(),
            loader="system atlas readers",
            writer="tools/meta/factory/build_system_atlas.py",
            mutability_class="generated_read_only",
            consumer_edges=["system atlas docs", "system_self_comprehension_root", "Type B grounding packet"],
            projection_surfaces=["state/system_atlas/*.json"],
            redaction_policy="metadata_and_shape_visible",
            exemption_reason="generated projection; never source authority",
        )
    )
    rows.append(
        _config_file_row(
            root,
            "state/bridge_preflight_cache.json",
            generated_at=stamp,
            row_class="runtime_coordination_state",
            authority_owner="bridge preflight runtime",
            governing_standard=STANDARD_REL_PATH.as_posix(),
            loader="system/lib/kernel/preflight_cache.py",
            writer="bridge preflight runtime",
            mutability_class="runtime_writer_owned",
            consumer_edges=["bridge preflight", "kernel pulse", "kernel observe"],
            projection_surfaces=["codex/derived/config_authority_registry.json"],
            redaction_policy="metadata_and_shape_visible",
            exemption_reason="runtime coordination state; not source authority for stored config",
        )
    )
    for rel_path, row_class, owner, loader, writer, mutability, consumers, exemption in (
        (
            "codex/doctrine/doctrine_compiler_ir.json",
            "generated_projection_or_cache",
            "doctrine compiler IR builder",
            "doctrine IR readers",
            "tools/meta/factory/emit_doctrine_ir_proposals.py + tools/meta/factory/review_doctrine_ir_proposals.py",
            "generated_read_only",
            ["doctrine IR review pipeline", "lattice_status diagnostics"],
            "generated projection; never source authority",
        ),
        (
            "codex/doctrine/doctrine_graph.json",
            "generated_projection_or_cache",
            "doctrine graph builder",
            "doctrine graph readers",
            "tools/meta/factory/build_doctrine_subdomain_index.py family",
            "generated_read_only",
            ["doctrine navigation", "kernel doctrine routes"],
            "generated projection; never source authority",
        ),
        (
            "codex/doctrine/doctrine_index.json",
            "generated_projection_or_cache",
            "doctrine subdomain index builder",
            "doctrine index readers",
            "tools/meta/factory/build_doctrine_subdomain_index.py",
            "generated_read_only",
            ["doctrine navigation", "kernel docs-route"],
            "generated projection; never source authority",
        ),
        (
            "codex/doctrine/doctrine_section_units.json",
            "generated_projection_or_cache",
            "doctrine section unit builder",
            "doctrine section readers",
            "doctrine section unit projector",
            "generated_read_only",
            ["doctrine navigation", "doctrine compiler IR"],
            "generated projection; never source authority",
        ),
        (
            "codex/doctrine/doctrine_surface.json",
            "generated_projection_or_cache",
            "doctrine surface builder",
            "doctrine surface readers",
            "doctrine surface projector",
            "generated_read_only",
            ["doctrine navigation", "kernel option-surface doctrine"],
            "generated projection; never source authority",
        ),
        (
            "codex/doctrine/system_map.json",
            "generated_projection_or_cache",
            "system map builder",
            "system map readers",
            "tools/meta/factory/generate_system_map.py",
            "generated_read_only",
            ["system atlas", "kernel docs-route", "Type B grounding packet"],
            "generated projection; never source authority",
        ),
        (
            "codex/doctrine/doctrine_runtime.json",
            "runtime_coordination_state",
            "doctrine runtime",
            "doctrine runtime readers",
            "doctrine runtime owner lane",
            "runtime_writer_owned",
            ["kernel pulse", "doctrine review pipeline"],
            "runtime coordination state; not source authority for stored config",
        ),
        (
            "codex/doctrine/doctrine_approved_overlay.json",
            "domain_authority_config",
            "doctrine approval overlay owner",
            "doctrine review readers",
            "doctrine review owner lane",
            "domain_owner_writer_required",
            ["doctrine review pipeline", "doctrine compiler IR"],
            None,
        ),
        (
            "codex/doctrine/doctrine_registry.json",
            "domain_authority_config",
            "doctrine registry owner",
            "doctrine registry readers",
            "doctrine registry owner lane",
            "domain_owner_writer_required",
            ["doctrine navigation", "doctrine_index", "kernel docs-route"],
            None,
        ),
        (
            "codex/doctrine/doctrine_routing.json",
            "domain_authority_config",
            "doctrine routing owner",
            "doctrine routing readers",
            "doctrine routing owner lane",
            "domain_owner_writer_required",
            ["doctrine navigation", "kernel docs-route"],
            None,
        ),
        (
            "codex/doctrine/concept_mechanism_candidate_curation.json",
            "domain_authority_config",
            "concept/mechanism curation owner",
            "concept/mechanism curation readers",
            "concept/mechanism curation owner lane",
            "domain_owner_writer_required",
            ["doctrine review pipeline", "concept_mechanism_candidates"],
            None,
        ),
        (
            "codex/doctrine/concept_mechanism_candidates.json",
            "domain_authority_config",
            "concept/mechanism candidate owner",
            "concept/mechanism candidate readers",
            "concept/mechanism owner lane",
            "domain_owner_writer_required",
            ["doctrine review pipeline", "concept_mechanism_candidate_curation"],
            None,
        ),
        (
            "codex/doctrine/pipeline_step_routing.json",
            "domain_authority_config",
            "pipeline step routing owner",
            "pipeline step routing readers",
            "pipeline step routing owner lane",
            "domain_owner_writer_required",
            ["pipeline orchestration", "kernel pulse"],
            None,
        ),
        (
            "codex/doctrine/principle_refinement_plan.json",
            "domain_authority_config",
            "principle refinement plan owner",
            "principle refinement readers",
            "principle refinement owner lane",
            "domain_owner_writer_required",
            ["doctrine review pipeline", "principle authoring"],
            None,
        ),
        (
            "codex/doctrine/routing_anti_patterns.json",
            "domain_authority_config",
            "routing anti-pattern doctrine",
            "routing anti-pattern readers",
            "routing anti-pattern owner lane",
            "domain_owner_writer_required",
            ["agent navigation hooks", "session diagnostics"],
            None,
        ),
        (
            "codex/doctrine/teleology_nodes.json",
            "domain_authority_config",
            "teleology node owner",
            "teleology node readers",
            "teleology node owner lane",
            "domain_owner_writer_required",
            ["doctrine teleology", "kernel docs-route"],
            None,
        ),
        (
            "codex/doctrine/github_import_targets.json",
            "domain_authority_config",
            "github import target owner",
            "github import readers",
            "github import owner lane",
            "domain_owner_writer_required",
            ["github sync", "annex import"],
            None,
        ),
    ):
        rows.append(
            _config_file_row(
                root,
                rel_path,
                generated_at=stamp,
                row_class=row_class,
                authority_owner=owner,
                governing_standard=STANDARD_REL_PATH.as_posix(),
                loader=loader,
                writer=writer,
                mutability_class=mutability,
                consumer_edges=consumers,
                projection_surfaces=["codex/derived/config_authority_registry.json"],
                exemption_reason=exemption,
            )
        )
    for rel_path in (".claude", ".codex", ".cursor"):
        rows.append(_host_adapter_row(root, rel_path, generated_at=stamp))
    rows.extend(
        [
            _api_route_row("api.config.system", "/api/config/system", generated_at=stamp),
            _api_route_row("api.config.ui", "/api/config/ui", generated_at=stamp),
            _api_route_row("api.system.registry", "/api/system/registry", generated_at=stamp),
            _mission_preflight_timeout_env_row(stamp),
            _configs_board_row(stamp),
            _settings_authority_bridge_row(root, generated_at=stamp),
            _config_file_row(
                root,
                "codex/standards/std_tool_config.json",
                generated_at=stamp,
                row_class="schema_or_standard_config",
                authority_owner="standards substrate",
                governing_standard="codex/standards/std_standards_registry.json",
                loader="standards readers",
                writer="standards owner lane",
                mutability_class="standard_discipline_required",
                consumer_edges=["codex/configs/*.json", "codex/substrate/configs/*.json"],
            ),
            _config_file_row(
                root,
                "codex/standards/std_plan_manifest.json",
                generated_at=stamp,
                row_class="schema_or_standard_config",
                authority_owner="plan manifest standard",
                governing_standard="codex/standards/std_standards_registry.json",
                loader="plan manifest readers",
                writer="standards owner lane",
                mutability_class="standard_discipline_required",
                consumer_edges=["config_authority_and_visibility plan group"],
            ),
            _row(
                config_id="secret_or_private_config.metadata_policy",
                canonical_label="Secret/private config metadata policy",
                row_class="secret_or_private_config",
                authority_owner="security/redaction policy",
                authority_path="secret/private config roots",
                loader="metadata-only registry policy",
                writer="owning secret manager or host adapter",
                governing_standard=STANDARD_REL_PATH.as_posix(),
                schema_or_validator="redaction policy",
                value_semantics="private or secret-bearing config is queryable only as owner/freshness/redaction metadata unless a later security model allows more",
                context_dimensions=["host", "privacy_boundary", "redaction_policy"],
                override_precedence=["secret manager", "host adapter", "repo metadata row"],
                mutability_class="secret_metadata_only",
                safe_edit_gate="never raw-edit through config surface",
                rollback_or_restore=None,
                refresh_or_rebuild=None,
                consumer_edges=["config authority diagnostics"],
                dependency_edges=[],
                projection_surfaces=["codex/derived/config_authority_registry.json"],
                frontend_routes=["/settings diagnostics"],
                agent_entry_routes=["docs-route config plane"],
                diagnostics=[],
                redaction_policy="metadata_only_no_raw_values",
                exemption_reason="secret-bearing values are explicitly outside read/write exposure for v1",
                last_verified=stamp,
                effective_summary={"policy": "metadata only; raw values not surfaced"},
            ),
        ]
    )
    rows_by_id = {row["config_id"]: row for row in rows}
    rows = [rows_by_id[key] for key in sorted(rows_by_id)]
    class_counts = Counter(str(row.get("class")) for row in rows)
    mutability_counts = Counter(str(row.get("mutability_class")) for row in rows)
    diagnostics = [
        {"config_id": row["config_id"], **diag}
        for row in rows
        for diag in row.get("diagnostics", [])
        if isinstance(diag, Mapping)
    ]
    config_ref_index: dict[str, str] = {}
    for row in rows:
        for alias in row.get("config_ref_aliases") or []:
            config_ref_index[str(alias)] = str(row["config_id"])
    return {
        "kind": "config_authority_registry",
        "schema_version": "config_authority_registry_v1",
        "generated_at": stamp,
        "artifact_path": REGISTRY_REL_PATH.as_posix(),
        "authority_posture": "federated_registry_not_value_authority",
        "governing_standard": STANDARD_REL_PATH.as_posix(),
        "paper_module": PAPER_MODULE_REL_PATH.as_posix(),
        "row_count": len(rows),
        "class_counts": dict(sorted(class_counts.items())),
        "mutability_counts": dict(sorted(mutability_counts.items())),
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics,
        "config_ref_index": dict(sorted(config_ref_index.items())),
        "api_routes": [
            "GET /api/config/surface",
            "GET /api/config/surface/search",
            "GET /api/config/surface/node/{config_id}",
            "GET /api/config/surface/effective/{config_id}",
            "GET /api/config/surface/diagnostics",
            "POST /api/config/surface/rebuild",
        ],
        "agent_entry_routes": [
            "./repo-python kernel.py --option-surface config_authorities --band cluster_flag",
            "./repo-python kernel.py --docs-route \"master_config settings config authority registry config_ref effective config\"",
            "./repo-python kernel.py --context-pack \"federated master config plane settings api agent entry config authority registry effective resolver\" --context-budget 12000",
        ],
        "rows": rows,
    }


def _load_standard_contract(repo_root: Path) -> dict[str, Any]:
    standard = _load_json(Path(repo_root) / STANDARD_REL_PATH)
    if not isinstance(standard, Mapping):
        return {
            "row_classes": [],
            "row_contract_required": [],
            "effective_trace_required": [],
        }
    return {
        "row_classes": list(standard.get("row_classes") or []),
        "row_contract_required": list(standard.get("row_contract_required") or []),
        "effective_trace_required": list(standard.get("effective_trace_required") or []),
    }


def validate_config_authority_registry(
    payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    contract = _load_standard_contract(Path(repo_root))
    allowed_classes = {str(item) for item in contract.get("row_classes") or []}
    row_required = [str(item) for item in contract.get("row_contract_required") or []]
    trace_required = [str(item) for item in contract.get("effective_trace_required") or []]
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def add_error(code: str, message: str, *, config_id: str | None = None) -> None:
        entry: dict[str, Any] = {"code": code, "message": message}
        if config_id:
            entry["config_id"] = config_id
        errors.append(entry)

    def add_warning(code: str, message: str, *, config_id: str | None = None) -> None:
        entry: dict[str, Any] = {"code": code, "message": message}
        if config_id:
            entry["config_id"] = config_id
        warnings.append(entry)

    if payload.get("kind") != "config_authority_registry":
        add_error("invalid_kind", "registry kind must be config_authority_registry")
    if payload.get("schema_version") != "config_authority_registry_v1":
        add_error("invalid_schema_version", "registry schema_version must be config_authority_registry_v1")

    rows = payload.get("rows")
    if not isinstance(rows, list):
        add_error("rows_not_list", "registry rows must be a list")
        rows = []
    if payload.get("row_count") != len(rows):
        add_error("row_count_mismatch", f"row_count {payload.get('row_count')} does not match {len(rows)} rows")

    seen_ids: set[str] = set()
    flattened_diagnostics: list[Mapping[str, Any]] = []
    list_fields = {
        "context_dimensions",
        "override_precedence",
        "consumer_edges",
        "dependency_edges",
        "projection_surfaces",
        "frontend_routes",
        "agent_entry_routes",
        "diagnostics",
    }
    non_empty_string_fields = {
        "config_id",
        "canonical_label",
        "class",
        "authority_owner",
        "authority_path",
        "loader",
        "writer",
        "governing_standard",
        "schema_or_validator",
        "stored_default_current_effective_semantics",
        "mutability_class",
        "safe_edit_gate",
        "redaction_policy",
        "last_verified",
    }
    read_only_mutability = {
        "generated_read_only",
        "host_local_read_only_metadata",
        "read_only_projection",
        "secret_metadata_only",
    }
    metadata_only_classes = {"host_local_adapter_config", "secret_or_private_config"}

    for index, row_value in enumerate(rows):
        if not isinstance(row_value, Mapping):
            add_error("row_not_object", f"row at index {index} must be an object")
            continue
        row = dict(row_value)
        config_id = str(row.get("config_id") or "").strip()
        location = config_id or f"rows[{index}]"

        if not config_id:
            add_error("missing_config_id", "row config_id must be non-empty", config_id=location)
        elif config_id in seen_ids:
            add_error("duplicate_config_id", f"duplicate config_id {config_id}", config_id=config_id)
        seen_ids.add(config_id)

        for field in row_required:
            if field not in row:
                add_error("missing_required_field", f"missing required row field {field}", config_id=location)
        for field in non_empty_string_fields:
            if field in row and not str(row.get(field) or "").strip():
                add_error("empty_required_string", f"row field {field} must be non-empty", config_id=location)
        for field in list_fields:
            if field in row and not isinstance(row.get(field), list):
                add_error("required_list_field_not_list", f"row field {field} must be a list", config_id=location)

        row_class = str(row.get("class") or "")
        if allowed_classes and row_class not in allowed_classes:
            add_error("invalid_row_class", f"class {row_class} is not declared by the standard", config_id=location)

        trace = row.get("effective_trace")
        if not isinstance(trace, Mapping):
            add_error("missing_effective_trace", "effective_trace must be an object", config_id=location)
            trace = {}
        for field in trace_required:
            if field not in trace:
                add_error("missing_effective_trace_field", f"missing effective_trace field {field}", config_id=location)
        if "mutation_allowed" in trace and not isinstance(trace.get("mutation_allowed"), bool):
            add_error("mutation_allowed_not_bool", "effective_trace.mutation_allowed must be boolean", config_id=location)
        if "consumers" in trace and not isinstance(trace.get("consumers"), list):
            add_error("trace_consumers_not_list", "effective_trace.consumers must be a list", config_id=location)
        for field in ("winning_source", "authority_path", "validator"):
            if field in trace and not str(trace.get(field) or "").strip():
                add_error("empty_effective_trace_string", f"effective_trace.{field} must be non-empty", config_id=location)

        mutation_allowed = bool(trace.get("mutation_allowed"))
        mutability_class = str(row.get("mutability_class") or "")
        if row_class == "generated_projection_or_cache" and mutation_allowed:
            add_error("generated_projection_mutable", "generated projection/cache rows must not allow mutation", config_id=location)
        if mutability_class in read_only_mutability and mutation_allowed:
            add_error("read_only_mutability_allows_mutation", f"{mutability_class} rows must not allow mutation", config_id=location)
        if row_class in metadata_only_classes and row.get("redaction_policy") != "metadata_only_no_raw_values":
            add_error("metadata_only_redaction_required", f"{row_class} rows must use metadata_only_no_raw_values", config_id=location)

        for diagnostic in row.get("diagnostics") or []:
            if isinstance(diagnostic, Mapping):
                flattened_diagnostics.append(diagnostic)
            else:
                add_warning("diagnostic_not_object", "diagnostic entries should be objects", config_id=location)

    if payload.get("diagnostic_count") != len(flattened_diagnostics):
        add_error(
            "diagnostic_count_mismatch",
            f"diagnostic_count {payload.get('diagnostic_count')} does not match {len(flattened_diagnostics)} row diagnostics",
        )

    for route in payload.get("api_routes") or []:
        route_text = str(route)
        method = route_text.split(" ", 1)[0].strip().upper()
        if method in {"PATCH", "PUT", "DELETE"}:
            add_error("config_surface_value_mutation_route", f"{route_text} exposes value mutation on the config surface")
        if method == "POST" and not route_text.endswith("/rebuild"):
            add_error("config_surface_unexpected_post_route", f"{route_text} is not the projection rebuild route")

    if not allowed_classes:
        add_warning("standard_contract_missing", f"{STANDARD_REL_PATH.as_posix()} could not provide row_classes")

    return {
        "kind": "config_authority_registry_validation",
        "valid": not errors,
        "row_count": len(rows),
        "error_count": len(errors),
        "errors": errors,
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def normalized_config_authority_registry(payload: Any) -> Any:
    # valid_from added when typed_consumer_edges/typed_dependency_edges
    # started carrying validity.valid_from per std_navigation_rosetta_grammar
    # edge_instance_shape.validity_shape (slice 4 typed-edge emission).
    volatile_keys = {"generated_at", "last_verified", "mtime", "valid_from"}

    def normalize(value: Any, *, key: str | None = None) -> Any:
        if key in volatile_keys:
            return "<normalized>"
        if isinstance(value, Mapping):
            return {str(item_key): normalize(item_value, key=str(item_key)) for item_key, item_value in sorted(value.items())}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    return normalize(payload)


def _normalized_row_lookup(payload: Any) -> dict[str, Any]:
    normalized = normalized_config_authority_registry(payload)
    if not isinstance(normalized, Mapping):
        return {}
    rows = normalized.get("rows")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("config_id")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("config_id")
    }


def _config_registry_stale_findings(
    *,
    built: Mapping[str, Any],
    stored: Any,
) -> list[dict[str, Any]]:
    if not isinstance(stored, Mapping):
        return [
            {
                "severity": "error",
                "rule": "derived_projection_missing",
                "artifact_path": REGISTRY_REL_PATH.as_posix(),
                "drift_class": "missing_or_unreadable_projection",
                "message": f"{REGISTRY_REL_PATH.as_posix()} is missing or unreadable",
                "required_next_action": REGISTRY_REBUILD_COMMAND,
                "owner_repair_command": REGISTRY_REBUILD_COMMAND,
            }
        ]

    normalized_built = normalized_config_authority_registry(built)
    normalized_stored = normalized_config_authority_registry(stored)
    if normalized_built == normalized_stored:
        return []

    built_rows = _normalized_row_lookup(built)
    stored_rows = _normalized_row_lookup(stored)
    added_ids = sorted(set(built_rows) - set(stored_rows))
    removed_ids = sorted(set(stored_rows) - set(built_rows))
    changed_ids = sorted(
        row_id
        for row_id in set(built_rows).intersection(stored_rows)
        if built_rows.get(row_id) != stored_rows.get(row_id)
    )
    changed_top_level_keys = sorted(
        key
        for key in set(normalized_built).union(normalized_stored)
        if key != "rows"
        and isinstance(normalized_built, Mapping)
        and isinstance(normalized_stored, Mapping)
        and normalized_built.get(key) != normalized_stored.get(key)
    )
    if added_ids or removed_ids:
        drift_class = "row_identity_drift"
    elif changed_ids:
        drift_class = "row_content_drift"
    elif changed_top_level_keys:
        drift_class = "registry_metadata_drift"
    else:
        drift_class = "normalized_payload_drift"
    return [
        {
            "severity": "error",
            "rule": "derived_projection_stale",
            "artifact_path": REGISTRY_REL_PATH.as_posix(),
            "drift_class": drift_class,
            "message": f"{REGISTRY_REL_PATH.as_posix()} does not match a freshly built normalized registry",
            "added_config_ids": added_ids,
            "removed_config_ids": removed_ids,
            "changed_config_ids": changed_ids,
            "changed_config_id_count": len(changed_ids),
            "changed_config_ids_preview": changed_ids[:25],
            "changed_top_level_keys": changed_top_level_keys,
            "required_next_action": REGISTRY_REBUILD_COMMAND,
            "owner_repair_command": REGISTRY_REBUILD_COMMAND,
        }
    ]


# v2 child slice 7: warn-stage enforcement scan families.
# Each (glob, suggested_class) names a family the registry is expected to
# cover. Files matching the glob whose path is NOT a registered authority_path
# AND not explicitly exempted are surfaced as warnings — never errors.
_WARN_STAGE_SCAN_FAMILIES: tuple[tuple[str, str], ...] = (
    ("codex/doctrine/*.json", "domain_authority_config"),
    ("codex/configs/*.json", "domain_authority_config"),
    ("codex/substrate/configs/*.json", "domain_authority_config"),
    ("codex/doctrine/skills/*.json", "domain_authority_config"),
    ("state/system_atlas/*.json", "generated_projection_or_cache"),
    ("state/frontend_navigation/*.json", "generated_projection_or_cache"),
)


def _unregistered_root_findings(
    *,
    built: Mapping[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Surface a warn-stage signal when a config-family root exists
      on disk but no registry row claims it. Step 3 of the standard's
      enforcement_ladder (warn). Never flips --check exit code.
    - Mechanism: For each scan family glob, enumerate files; cross-reference
      against built registry authority_path values; emit one warning finding
      per unmatched file with candidate_path, suggested_class, scan_family.
    - Reads: built (live registry), repo_root.
    - Writes: None.
    - Guarantee: Returns a list of warning dicts; never raises on missing
      directories.
    - When-needed: Open when the registry --check should detect new
      behavior-affecting roots that landed on disk without a row.
    """
    rows = built.get("rows") or []
    registered_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        path = row.get("authority_path")
        if isinstance(path, str):
            registered_paths.add(path)
    findings: list[dict[str, Any]] = []
    for glob, suggested_class in _WARN_STAGE_SCAN_FAMILIES:
        for candidate in sorted(repo_root.glob(glob)):
            if not candidate.is_file():
                continue
            rel = str(candidate.relative_to(repo_root))
            if rel in registered_paths:
                continue
            findings.append({
                "code": "unregistered_behavior_affecting_root",
                "severity": "warning",
                "candidate_path": rel,
                "suggested_class": suggested_class,
                "scan_family": glob,
                "message": (
                    f"{rel} matched scan family {glob} but is not a registered "
                    f"authority_path; suggested class {suggested_class}. "
                    f"Register it with system/lib/config_authority_registry.py "
                    f"or record an explicit exemption_reason."
                ),
            })
    return findings


def check_config_authority_registry(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root)
    built = build_config_authority_registry(repo_root=root)
    stored = _load_json(root / REGISTRY_REL_PATH)
    validation = validate_config_authority_registry(built, repo_root=root)
    stored_validation = (
        validate_config_authority_registry(stored, repo_root=root)
        if isinstance(stored, Mapping)
        else {
            "valid": False,
            "error_count": 1,
            "errors": [{"code": "derived_projection_missing", "message": f"{REGISTRY_REL_PATH.as_posix()} is missing or unreadable"}],
            "warning_count": 0,
            "warnings": [],
        }
    )
    fresh = isinstance(stored, Mapping) and normalized_config_authority_registry(stored) == normalized_config_authority_registry(built)
    built_ids = {
        str(row.get("config_id"))
        for row in built.get("rows") or []
        if isinstance(row, Mapping) and row.get("config_id")
    }
    stored_ids = {
        str(row.get("config_id"))
        for row in (stored or {}).get("rows", []) if isinstance(row, Mapping) and row.get("config_id")
    } if isinstance(stored, Mapping) else set()
    errors = list(validation.get("errors") or [])
    errors.extend({"code": f"stored_{error.get('code')}", "message": error.get("message")} for error in stored_validation.get("errors") or [])
    stale_findings = _config_registry_stale_findings(built=built, stored=stored)
    if not fresh:
        for finding in stale_findings:
            errors.append(
                {
                    "code": str(finding.get("rule") or "derived_projection_stale"),
                    "message": finding.get("message"),
                    "artifact_path": finding.get("artifact_path"),
                    "drift_class": finding.get("drift_class"),
                    "required_next_action": finding.get("required_next_action"),
                    "owner_repair_command": finding.get("owner_repair_command"),
                }
            )
    changed_config_ids = [
        row_id
        for finding in stale_findings
        for row_id in finding.get("changed_config_ids", [])
        if isinstance(row_id, str)
    ]
    required_next_action = (
        stale_findings[0].get("required_next_action")
        if stale_findings
        else None
    )
    unregistered_root_warnings = _unregistered_root_findings(built=built, repo_root=root)
    return {
        "kind": "config_authority_registry_check",
        "ok": fresh and not errors,
        "fresh": fresh,
        "contract_valid": bool(validation.get("valid")) and bool(stored_validation.get("valid")),
        "artifact_path": REGISTRY_REL_PATH.as_posix(),
        "required_next_action": required_next_action,
        "owner_repair_command": required_next_action,
        "row_count": built.get("row_count"),
        "stored_row_count": stored.get("row_count") if isinstance(stored, Mapping) else None,
        "class_counts": built.get("class_counts"),
        "diagnostic_count": built.get("diagnostic_count"),
        "stored_diagnostic_count": stored.get("diagnostic_count") if isinstance(stored, Mapping) else None,
        "added_config_ids": sorted(built_ids - stored_ids),
        "removed_config_ids": sorted(stored_ids - built_ids),
        "changed_config_ids": changed_config_ids,
        "changed_config_id_count": len(changed_config_ids),
        "stale_finding_count": len(stale_findings),
        "stale_findings": stale_findings,
        "error_count": len(errors),
        "errors": errors,
        "warning_count": int(validation.get("warning_count") or 0) + int(stored_validation.get("warning_count") or 0),
        "warnings": list(validation.get("warnings") or []) + list(stored_validation.get("warnings") or []),
        "unregistered_root_warning_count": len(unregistered_root_warnings),
        "unregistered_root_warnings": unregistered_root_warnings,
    }


def load_config_authority_registry(*, repo_root: Path = REPO_ROOT, build_if_missing: bool = True) -> dict[str, Any]:
    root = Path(repo_root)
    payload = _load_json(root / REGISTRY_REL_PATH)
    if isinstance(payload, Mapping) and payload.get("kind") == "config_authority_registry":
        return dict(payload)
    if build_if_missing:
        return build_config_authority_registry(repo_root=root)
    return {
        "kind": "config_authority_registry",
        "schema_version": "config_authority_registry_v1",
        "available": False,
        "artifact_path": REGISTRY_REL_PATH.as_posix(),
        "authority_posture": "projection_missing_not_synthesized",
        "governing_standard": STANDARD_REL_PATH.as_posix(),
        "paper_module": PAPER_MODULE_REL_PATH.as_posix(),
        "row_count": 0,
        "class_counts": {},
        "mutability_counts": {},
        "diagnostic_count": 1,
        "diagnostics": [
            {
                "severity": "error",
                "code": "derived_projection_missing",
                "message": (
                    f"{REGISTRY_REL_PATH.as_posix()} is missing or unreadable and "
                    "build_if_missing is false."
                ),
                "required_next_action": REGISTRY_REBUILD_COMMAND,
                "owner_repair_command": REGISTRY_REBUILD_COMMAND,
            }
        ],
        "config_ref_index": {},
        "api_routes": [],
        "agent_entry_routes": [
            "./repo-python tools/meta/factory/build_config_authority_registry.py",
            "./repo-python tools/meta/factory/build_config_authority_registry.py --check",
        ],
        "rows": [],
    }


def write_config_authority_registry(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    payload = build_config_authority_registry(repo_root=repo_root)
    _write_json(Path(repo_root) / REGISTRY_REL_PATH, payload)
    return {
        "kind": "config_authority_registry_rebuild_receipt",
        "generated_at": payload.get("generated_at"),
        "artifact_path": REGISTRY_REL_PATH.as_posix(),
        "row_count": payload.get("row_count"),
        "diagnostic_count": payload.get("diagnostic_count"),
    }


def _row_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    label = row.get("canonical_label") or row.get("config_id")
    row_class = row.get("class")
    owner = row.get("authority_owner")
    path = row.get("authority_path")
    return {
        "config_id": row.get("config_id"),
        "canonical_label": row.get("canonical_label"),
        "claim": f"{label} is a {row_class} owned by {owner} at {path}.",
        "class": row_class,
        "authority_owner": owner,
        "authority_path": path,
        "mutability_class": row.get("mutability_class"),
        "redaction_policy": row.get("redaction_policy"),
        "diagnostics": row.get("diagnostics") or [],
        "frontend_routes": row.get("frontend_routes") or [],
        "agent_entry_routes": row.get("agent_entry_routes") or [],
    }


def search_config_authority_registry(
    *,
    query: str,
    repo_root: Path = REPO_ROOT,
    limit: int = 40,
) -> dict[str, Any]:
    payload = load_config_authority_registry(repo_root=repo_root)
    query_text = str(query or "").strip().lower()
    query_tokens = {token for token in re.findall(r"[a-z0-9_./:-]{2,}", query_text)}
    results: list[dict[str, Any]] = []
    for row in payload.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        haystack = str(row.get("search_text") or "").lower()
        overlap = sorted(token for token in query_tokens if token in haystack)
        if query_text and query_text not in haystack and not overlap:
            continue
        score = len(overlap) * 10
        if query_text and query_text in haystack:
            score += 20
        if query_text and query_text == str(row.get("authority_path") or "").lower():
            score += 30
        results.append({"score": score, "row": _row_summary(row), "matched_terms": overlap})
    results.sort(key=lambda item: (-int(item.get("score") or 0), str((item.get("row") or {}).get("config_id") or "")))
    return {
        "kind": "config_authority_registry_search_results",
        "query": query,
        "matched": len(results),
        "results": results[:limit],
    }


def _row_lookup(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("config_id")): dict(row)
        for row in payload.get("rows") or []
        if isinstance(row, Mapping) and row.get("config_id")
    }


def resolve_config_authority_node(*, config_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    payload = load_config_authority_registry(repo_root=repo_root)
    rows = _row_lookup(payload)
    row = rows.get(config_id)
    if row is None:
        ref_index = payload.get("config_ref_index") if isinstance(payload.get("config_ref_index"), Mapping) else {}
        target_id = str(ref_index.get(config_id) or "")
        row = rows.get(target_id)
    if row is None:
        return None
    row_id = str(row.get("config_id"))
    authority_path = str(row.get("authority_path") or "")
    related = [
        _row_summary(other)
        for other_id, other in rows.items()
        if other_id != row_id
        and (
            authority_path in (other.get("dependency_edges") or [])
            or authority_path in (other.get("consumer_edges") or [])
            or row_id in (other.get("dependency_edges") or [])
            or row_id in (other.get("consumer_edges") or [])
        )
    ]
    return {
        "kind": "config_authority_registry_node_detail",
        "node": row,
        "related_rows": related,
    }


def resolve_config_authority_effective(*, config_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    detail = resolve_config_authority_node(config_id=config_id, repo_root=repo_root)
    if detail is None:
        return None
    row = detail["node"]
    return {
        "kind": "config_authority_effective_trace",
        "config_id": row.get("config_id"),
        "canonical_label": row.get("canonical_label"),
        "authority_path": row.get("authority_path"),
        "mutability_class": row.get("mutability_class"),
        "redaction_policy": row.get("redaction_policy"),
        "effective_trace": row.get("effective_trace") or {},
    }


def config_authority_diagnostics(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    payload = load_config_authority_registry(repo_root=repo_root)
    return {
        "kind": "config_authority_registry_diagnostics",
        "generated_at": payload.get("generated_at"),
        "diagnostic_count": payload.get("diagnostic_count", 0),
        "class_counts": payload.get("class_counts", {}),
        "mutability_counts": payload.get("mutability_counts", {}),
        "diagnostics": payload.get("diagnostics", []),
    }


def build_config_authority_option_surface(
    repo_root: Path | str = REPO_ROOT,
    *,
    band: str = "flag",
    ids: str | list[str] | tuple[str, ...] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    normalized_band = str(band or "flag").strip().lower()
    if normalized_band not in SUPPORTED_BANDS:
        normalized_band = "flag"
    selected_ids: list[str] = []
    if isinstance(ids, str):
        selected_ids = [part for part in ids.replace(",", " ").split() if part]
    elif ids:
        selected_ids = [str(item).strip() for item in ids if str(item).strip()]
    payload = load_config_authority_registry(repo_root=root)
    rows = [row for row in payload.get("rows") or [] if isinstance(row, Mapping)]
    if normalized_band == "cluster_flag":
        class_counts = payload.get("class_counts") if isinstance(payload.get("class_counts"), Mapping) else {}
        surface_rows = [
            {
                "row_id": f"config_authority_class:{row_class}::cluster_flag",
                "artifact_kind": "config_authority_class",
                "class": row_class,
                "count": count,
                "claim": f"{count} config authority row(s) classified as {row_class}.",
                "drilldown_command": f"./repo-python kernel.py --option-surface config_authorities --band flag --ids {row_class}",
            }
            for row_class, count in sorted(class_counts.items())
        ]
    else:
        if selected_ids:
            selected = [
                row
                for row in rows
                if str(row.get("config_id")) in selected_ids
                or str(row.get("class")) in selected_ids
                or str(row.get("authority_path")) in selected_ids
            ]
        else:
            selected = rows
        if normalized_band == "card":
            surface_rows = [dict(row) for row in selected]
        else:
            surface_rows = [_row_summary(row) for row in selected]
    return {
        "kind": "standard_owned_option_surface",
        "schema_version": "standard_owned_option_surface_v0",
        "generated_at": generated_at or _utc_now(),
        "artifact_kind": "config_authorities",
        "band": normalized_band,
        "profile_status": "supported",
        "authority_posture": "federated_registry_projection_not_value_authority",
        "governing_standard": {"ref": STANDARD_REL_PATH.as_posix(), "owned_bands": sorted(SUPPORTED_BANDS)},
        "source_refs": [STANDARD_REL_PATH.as_posix(), REGISTRY_REL_PATH.as_posix(), PAPER_MODULE_REL_PATH.as_posix()],
        "selection": {"mode": "ids" if selected_ids else "all", "ids": selected_ids},
        "rows": surface_rows,
        "summary": {
            "row_count": len(surface_rows),
            "total_authority_rows": payload.get("row_count", 0),
            "diagnostic_count": payload.get("diagnostic_count", 0),
        },
        "navigation": {
            "cluster_first_for_high_cardinality": True,
            "option_surface_command": "./repo-python kernel.py --option-surface config_authorities --band cluster_flag",
            "card_command": "./repo-python kernel.py --option-surface config_authorities --band card --ids <config_id>",
            "api_surface": "/api/config/surface",
        },
    }
