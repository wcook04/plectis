"""
[PURPOSE]
- Teleology: Compile reusable observe mission templates into concrete ObserveSessionPlan payloads
  without inventing a second runtime surface.
- Mechanism: Load file-based atomic group templates and mission templates, expand params/repeats,
  optionally resolve doc-registry-backed selectors, then validate the output as ObserveSessionPlan.
- Non-goal: Executing the plan. The existing observe-session runner remains the runtime.

[INTERFACE]
- list_group_atoms(repo_root)                            -> list[dict]
- list_mission_templates(repo_root)                      -> list[dict]
- load_group_atom(repo_root, atom_id)                    -> dict
- load_mission_template(repo_root, mission_id)           -> dict
- expand_mission_template(...)                           -> MissionExpansion
- emit_mission_template_schema()                         -> dict

[CONSTRAINTS]
- Pure file reads plus plan compilation; no runtime dispatch.
- Templates are JSON files rooted at codex/standards/observe/mission_templates/.
- Expansion must produce a valid ObserveSessionPlan or raise ValueError.
- When-needed: Open when authored observe mission templates or group atoms need to be listed, loaded, or expanded into a concrete ObserveSessionPlan without reading the runtime orchestrator.
- Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/observe_apply_context.py; system/lib/kernel_nav_phase.py
- Navigation-group: kernel_lib

[FLOW]
- Template inventory helpers scan the atom, mission, and meta-mission roots and expose compact cards or enriched payloads.
- Expansion resolves defaults, required params, interpolation, repeat items, doc-registry selectors, and captured labels across authored groups.
- The final expanded plan is validated through ObserveSessionPlan and returned with mission metadata in MissionExpansion.

[DEPENDENCIES]
- system.server.schemas.ObserveSessionPlan: Validates the compiled mission output against the runtime plan contract.
- system.lib.doc_registry and system.lib.substrate_citation: Resolve doc-backed selectors and @file / @doc references during expansion.
- json, copy, pathlib.Path, dataclasses: Support literal template loading, deep merge behavior, and immutable expansion results.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.controller_heartbeat import wrap_response_schema_with_heartbeat_ref
from system.lib.doc_registry import get_entry as doc_registry_get_entry
from system.lib.doc_registry import query_entries as doc_registry_query_entries
from system.lib.substrate_citation import parse_citation
from system.server.schemas import ObserveSessionPlan

MISSION_TEMPLATE_SCHEMA_VERSION = "1.0"
MISSION_TEMPLATE_ROOT_REL = "codex/standards/observe/mission_templates"
MISSION_TEMPLATE_ATOMS_REL = f"{MISSION_TEMPLATE_ROOT_REL}/atoms"
MISSION_TEMPLATE_MISSIONS_REL = f"{MISSION_TEMPLATE_ROOT_REL}/missions"
MISSION_TEMPLATE_META_MISSIONS_REL = f"{MISSION_TEMPLATE_ROOT_REL}/meta_missions"
MISSION_TEMPLATE_KIND = "observe_mission_template"
MISSION_CHAIN_KIND = "observe_mission_chain"
SUPPORTED_MISSION_KINDS = {
    MISSION_TEMPLATE_KIND,
    MISSION_CHAIN_KIND,
}

_INTERPOLATION_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_SOURCE_KEYS = {
    "$param",
    "$item",
    "$capture",
    "$doc_code_refs",
    "$doc_query_code_refs",
}


@dataclass(frozen=True)
class MissionExpansion:
    """[ROLE]
    - Teleology: Immutable handoff object for one compiled observe mission template and its validated ObserveSessionPlan payload.
    - Mechanism: Carries template identity, effective params, compiled plan JSON, captured labels, and family-context metadata returned by expand_mission_template().
    - Ownership: Created only by expand_mission_template(); consumed by mission-preview, tooling, and runtime-launch surfaces.
    - Mutability: Frozen dataclass; callers treat the compiled plan and metadata as read-only expansion output.
    - Concurrency: Thread-safe by construction because the dataclass is frozen and contains detached payload copies.
    - When-needed: Open when a caller has already expanded a mission and needs the exact shape of the compiled handoff object instead of re-reading expansion logic.
    - Escalates-to: system/lib/observe_mission_templates.py::expand_mission_template; tools/meta/apply/run_observe_plan.py
    """
    mission_id: str
    mission_template_version: str
    template_path: str
    params: dict[str, Any]
    plan: dict[str, Any]
    captures: dict[str, list[str]]
    family_context: dict[str, Any]
    continuity_metadata: dict[str, Any]
    dispatch_policy: dict[str, Any]
    skill_files: list[str]
    shared_context_files: list[str]
    injected_context_files: list[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in override.items():
        if (
            isinstance(value, Mapping)
            and isinstance(merged.get(key), Mapping)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _normalize_relpath(repo_root: Path, token: str) -> str:
    candidate = Path(token)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return candidate.resolve().as_posix()
    return Path(token).as_posix()


def _normalize_pack_relpath(repo_root: Path, mission_path: Path, token: str) -> str:
    candidate = Path(token)
    if candidate.is_absolute():
        return _normalize_relpath(repo_root, token)
    pack_relative = (mission_path.parent / candidate).resolve()
    if pack_relative.exists():
        try:
            return pack_relative.relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return pack_relative.as_posix()
    return _normalize_relpath(repo_root, token)


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _continuity_metadata(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(payload or {})
    coordinator_kind = _string(source.get("coordinator_kind")) or "ide_controller"
    if coordinator_kind not in {"ide_controller", "codex_subagent", "bridge_coordinator", "grouped_observe"}:
        coordinator_kind = "ide_controller"
    controller_heartbeat_ref = (
        dict(source.get("controller_heartbeat_ref"))
        if isinstance(source.get("controller_heartbeat_ref"), Mapping)
        else None
    )
    return {
        "path_refs": [
            _string(item)
            for item in (source.get("path_refs") or [])
            if _string(item)
        ],
        "skill_refs": [
            _string(item)
            for item in (source.get("skill_refs") or [])
            if _string(item)
        ],
        "coordinator_kind": coordinator_kind,
        "coordinator_seed_ref": _string(source.get("coordinator_seed_ref")) or None,
        "macro_operations": [
            _string(item)
            for item in (source.get("macro_operations") or [])
            if _string(item)
        ],
        "controller_heartbeat_path": _string(source.get("controller_heartbeat_path")) or None,
        "controller_heartbeat_ref": controller_heartbeat_ref,
    }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Template payload must be a JSON object: {path}")
    return payload


def _template_dirs(repo_root: Path) -> tuple[Path, Path, Path]:
    return (
        (repo_root / MISSION_TEMPLATE_ATOMS_REL).resolve(),
        (repo_root / MISSION_TEMPLATE_MISSIONS_REL).resolve(),
        (repo_root / MISSION_TEMPLATE_META_MISSIONS_REL).resolve(),
    )


def _template_id(path: Path, payload: Mapping[str, Any]) -> str:
    explicit = _string(payload.get("id")) or _string(payload.get("template_id"))
    if explicit:
        return explicit
    if path.name == "mission.json":
        return path.parent.name
    return path.stem


def _template_card(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    pack_dir = path.parent.as_posix() if path.name == "mission.json" else None
    return {
        "id": _template_id(path, payload),
        "kind": _string(payload.get("kind")),
        "schema_version": _string(payload.get("schema_version")),
        "template_version": _string(payload.get("template_version")),
        "description": _string(payload.get("description")),
        "path": path.as_posix(),
        "pack_dir": pack_dir,
        "skill_file_count": len(
            [_string(item) for item in (payload.get("skill_files") or []) if _string(item)]
        ),
        "shared_context_file_count": len(
            [_string(item) for item in (payload.get("shared_context_files") or []) if _string(item)]
        ),
        "has_dispatch_policy": bool(isinstance(payload.get("dispatch_policy"), Mapping)),
    }


def _list_templates(
    root: Path,
    *,
    expected_kind: str | set[str],
    nested_entrypoint: str | None = None,
) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    expected_kinds = {expected_kind} if isinstance(expected_kind, str) else set(expected_kind)
    results: list[dict[str, Any]] = []
    paths = list(root.glob("*.json"))
    if nested_entrypoint:
        paths.extend(root.glob(f"*/{nested_entrypoint}"))
    for path in sorted(paths):
        payload = _load_json(path)
        if _string(payload.get("kind")) not in expected_kinds:
            continue
        results.append(_template_card(path, payload))
    return results


def list_group_atoms(repo_root: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: List the authored observe group-atom cards available for mission compilation.
    - Mechanism: Resolve the atoms directory and return template cards for JSON files whose kind is `observe_group_atom`.
    - Guarantee: Returns a sorted list of template cards or an empty list when no atoms exist.
    - Fails: Propagates ValueError from malformed atom payloads encountered during listing.
    - When-needed: Open when a kernel or tooling surface needs the discoverable atom catalog before choosing or validating a mission template.
    - Escalates-to: system/lib/kernel/commands/substrate.py; tools/meta/apply/python_std_bridge_meta_mission.py
    """
    atoms_dir, _, _ = _template_dirs(repo_root)
    return _list_templates(atoms_dir, expected_kind="observe_group_atom")


def list_mission_templates(repo_root: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: List the authored observe mission templates and meta-mission packs available for expansion.
    - Mechanism: Scan both the flat missions directory and the nested meta-missions entrypoints, then sort the resulting template cards by id/path.
    - Guarantee: Returns a sorted list of mission-template cards.
    - Fails: Propagates ValueError from malformed mission payloads encountered during listing.
    - When-needed: Open when a caller needs the current mission-template inventory before selecting one to expand or expose in a kernel surface.
    - Escalates-to: system/lib/kernel/commands/substrate.py; tools/meta/apply/python_std_bridge_meta_mission.py
    """
    _, missions_dir, meta_missions_dir = _template_dirs(repo_root)
    results = [
        *_list_templates(missions_dir, expected_kind=SUPPORTED_MISSION_KINDS),
        *_list_templates(
            meta_missions_dir,
            expected_kind=SUPPORTED_MISSION_KINDS,
            nested_entrypoint="mission.json",
        ),
    ]
    return sorted(results, key=lambda item: (str(item.get("id") or ""), str(item.get("path") or "")))


def _resolve_template_path(
    root: Path,
    token: str,
    *,
    expected_kind: str | set[str],
    nested_entrypoint: str | None = None,
) -> Path:
    expected_kinds = {expected_kind} if isinstance(expected_kind, str) else set(expected_kind)

    def _validate_kind(path: Path) -> None:
        payload = _load_json(path)
        kind = _string(payload.get("kind"))
        if kind not in expected_kinds:
            expected_display = ", ".join(sorted(expected_kinds))
            raise ValueError(f"Template kind mismatch for {path}: expected one of {expected_display}")

    candidate = Path(token)
    if candidate.is_absolute() or "/" in token or token.endswith(".json"):
        path = candidate if candidate.is_absolute() else (root / candidate)
        path = path.resolve()
        _validate_kind(path)
        return path

    if nested_entrypoint:
        nested_path = (root / token / nested_entrypoint).resolve()
        if nested_path.exists():
            _validate_kind(nested_path)
            return nested_path

    path = (root / f"{token}.json").resolve()
    if path.exists():
        _validate_kind(path)
        return path
    raise ValueError(f"Template not found: {token}")


def _attach_template_location(repo_root: Path, path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    try:
        rel_path = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        rel_path = path.resolve().as_posix()
    enriched.setdefault("path", rel_path)
    if path.name == "mission.json":
        try:
            pack_dir = path.parent.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pack_dir = path.parent.resolve().as_posix()
        enriched.setdefault("pack_dir", pack_dir)
    return enriched


def load_group_atom(repo_root: Path, atom_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load one observe group atom with its repo-relative location metadata attached.
    - Mechanism: Resolve the atom token to a JSON path, read the payload, and enrich it with path metadata.
    - Guarantee: Returns a mapping for one observe_group_atom payload.
    - Fails: Raises ValueError when the atom cannot be found, parsed, or matched to the expected kind.
    - When-needed: Open when a mission authoring or tooling path needs the exact contents of one group atom before expansion.
    - Escalates-to: system/lib/kernel/commands/substrate.py; tools/meta/apply/python_std_bridge_meta_mission.py
    """
    atoms_dir, _, _ = _template_dirs(repo_root)
    path = _resolve_template_path(atoms_dir, atom_id, expected_kind="observe_group_atom")
    return _attach_template_location(repo_root, path, _load_json(path))


def _resolve_mission_template_path(repo_root: Path, mission_id: str) -> Path:
    _, missions_dir, meta_missions_dir = _template_dirs(repo_root)
    try:
        return _resolve_template_path(
            missions_dir,
            mission_id,
            expected_kind=SUPPORTED_MISSION_KINDS,
        )
    except ValueError:
        return _resolve_template_path(
            meta_missions_dir,
            mission_id,
            expected_kind=SUPPORTED_MISSION_KINDS,
            nested_entrypoint="mission.json",
        )


def load_mission_template(repo_root: Path, mission_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load one authored observe mission template or meta-mission pack with its location metadata attached.
    - Mechanism: Resolve the mission token across both mission roots, read the JSON payload, and enrich it with path metadata.
    - Guarantee: Returns a mapping for one observe_mission_template or observe_mission_chain payload.
    - Fails: Raises ValueError when the mission cannot be found, parsed, or matched to the expected kind.
    - When-needed: Open when a tooling or review path needs the exact source payload for one mission template before expansion or schema checks.
    - Escalates-to: system/lib/kernel/commands/substrate.py; tools/meta/apply/python_std_bridge_meta_mission.py
    """
    path = _resolve_mission_template_path(repo_root, mission_id)
    return _attach_template_location(repo_root, path, _load_json(path))


def _lookup_path(scope: Any, dotted_path: str) -> Any:
    token = _string(dotted_path)
    if not token:
        return None
    current: Any = scope
    for part in token.split("."):
        if isinstance(current, Mapping):
            if part not in current:
                return None
            current = current.get(part)
            continue
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            if not part.isdigit():
                return None
            index = int(part)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def _interpolate_string(text: str, scope: Mapping[str, Any]) -> Any:
    raw = str(text)
    exact = _INTERPOLATION_RE.fullmatch(raw)
    if exact:
        return _lookup_path(scope, exact.group(1))

    def _replace(match: re.Match[str]) -> str:
        value = _lookup_path(scope, match.group(1))
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return _INTERPOLATION_RE.sub(_replace, raw)


def _resolve_doc_code_refs(
    token: str,
    *,
    doc_registry_payload: Mapping[str, Any] | None,
) -> list[str]:
    if not isinstance(doc_registry_payload, Mapping):
        raise ValueError("Mission template used doc-registry selectors without a loaded doc registry.")
    ref = parse_citation(token)
    doc_id = ""
    if ref is not None and ref.kind == "doc":
        doc_id = ref.canonical_id
    else:
        doc_id = token if token.startswith("doc_") else f"doc_{token}"
    entry = doc_registry_get_entry(doc_registry_payload, doc_id)
    if entry is None:
        raise ValueError(f"Doc registry entry not found for selector: {token}")
    return [_string(item) for item in (entry.get("code_refs") or []) if _string(item)]


def _resolve_doc_query_code_refs(
    query_payload: Mapping[str, Any],
    *,
    doc_registry_payload: Mapping[str, Any] | None,
) -> list[str]:
    if not isinstance(doc_registry_payload, Mapping):
        raise ValueError("Mission template used doc-registry query selectors without a loaded doc registry.")
    results = doc_registry_query_entries(
        doc_registry_payload,
        doc_type=_string(query_payload.get("kind")) or _string(query_payload.get("doc_type")) or None,
        tag=_string(query_payload.get("tag")) or None,
        status=_string(query_payload.get("status")) or None,
        code_ref=_string(query_payload.get("code_ref")) or None,
        principle_id=_string(query_payload.get("principle_id")) or None,
        q=_string(query_payload.get("q")) or None,
    )
    code_refs: list[str] = []
    seen: set[str] = set()
    for entry in results:
        for item in entry.get("code_refs", []) or []:
            token = _string(item)
            if not token or token in seen:
                continue
            seen.add(token)
            code_refs.append(token)
    return code_refs


def _resolve_recursive(
    value: Any,
    *,
    scope: Mapping[str, Any],
    captures: Mapping[str, list[str]],
    doc_registry_payload: Mapping[str, Any] | None,
    depth: int = 0,
) -> Any:
    if value is None:
        return None

    if isinstance(value, str):
        resolved = _interpolate_string(value, scope)
        if isinstance(resolved, str) and "{{" in resolved:
            if resolved == value and _INTERPOLATION_RE.fullmatch(value):
                return None
            if depth >= 10:
                return resolved
            return _resolve_recursive(
                resolved,
                scope=scope,
                captures=captures,
                doc_registry_payload=doc_registry_payload,
                depth=depth + 1,
            )
        if isinstance(resolved, (list, dict)) and resolved is not value:
            return _resolve_recursive(
                resolved,
                scope=scope,
                captures=captures,
                doc_registry_payload=doc_registry_payload,
                depth=depth + 1,
            )
        return resolved

    if isinstance(value, list):
        return [
            _resolve_recursive(
                item,
                scope=scope,
                captures=captures,
                doc_registry_payload=doc_registry_payload,
                depth=depth + 1,
            )
            for item in value
        ]

    if isinstance(value, Mapping):
        if len(value) == 1:
            source_key = next(iter(value.keys()))
            if source_key in _SOURCE_KEYS:
                source_value = value.get(source_key)
                if source_key == "$param":
                    token = _string(source_value)
                    return _resolve_recursive(
                        scope.get(token),
                        scope=scope,
                        captures=captures,
                        doc_registry_payload=doc_registry_payload,
                        depth=depth + 1,
                    )
                if source_key == "$item":
                    token = _string(source_value)
                    item_value = scope.get("item")
                    if token in {"", ".", "self"}:
                        return _resolve_recursive(
                            item_value,
                            scope=scope,
                            captures=captures,
                            doc_registry_payload=doc_registry_payload,
                            depth=depth + 1,
                        )
                    resolved = _lookup_path(item_value, token)
                    return _resolve_recursive(
                        resolved,
                        scope=scope,
                        captures=captures,
                        doc_registry_payload=doc_registry_payload,
                        depth=depth + 1,
                    )
                if source_key == "$capture":
                    token = _string(source_value)
                    return list(captures.get(token, []))
                if source_key == "$doc_code_refs":
                    token = _string(
                        _resolve_recursive(
                            source_value,
                            scope=scope,
                            captures=captures,
                            doc_registry_payload=doc_registry_payload,
                            depth=depth + 1,
                        )
                    )
                    return _resolve_doc_code_refs(token, doc_registry_payload=doc_registry_payload)
                if source_key == "$doc_query_code_refs":
                    resolved_query = _resolve_recursive(
                        source_value,
                        scope=scope,
                        captures=captures,
                        doc_registry_payload=doc_registry_payload,
                        depth=depth + 1,
                    )
                    if not isinstance(resolved_query, Mapping):
                        raise ValueError("$doc_query_code_refs must resolve to a mapping.")
                    return _resolve_doc_query_code_refs(
                        resolved_query,
                        doc_registry_payload=doc_registry_payload,
                    )

        return {
            _string(key): _resolve_recursive(
                item,
                scope=scope,
                captures=captures,
                doc_registry_payload=doc_registry_payload,
                depth=depth + 1,
            )
            for key, item in value.items()
        }

    return copy.deepcopy(value)


def _resolve_listish(
    value: Any,
    *,
    scope: Mapping[str, Any],
    captures: Mapping[str, list[str]],
    doc_registry_payload: Mapping[str, Any] | None,
) -> list[Any]:
    raw_items = value if isinstance(value, list) else [value]
    items: list[Any] = []
    for raw in raw_items:
        resolved = _resolve_recursive(
            raw,
            scope=scope,
            captures=captures,
            doc_registry_payload=doc_registry_payload,
        )
        if resolved is None:
            continue
        if isinstance(resolved, list):
            items.extend(resolved)
        else:
            items.append(resolved)
    return items


def _resolve_string_list(
    value: Any,
    *,
    repo_root: Path,
    scope: Mapping[str, Any],
    captures: Mapping[str, list[str]],
    doc_registry_payload: Mapping[str, Any] | None,
) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for item in _resolve_listish(
        value,
        scope=scope,
        captures=captures,
        doc_registry_payload=doc_registry_payload,
    ):
        token = _string(item)
        if not token:
            continue
        ref = parse_citation(token)
        if ref is not None and ref.kind == "file":
            token = ref.canonical_id
        token = _normalize_relpath(repo_root, token)
        if token in seen:
            continue
        seen.add(token)
        results.append(token)
    return results


def _coerce_target_item(repo_root: Path, item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        token = _string(item)
        ref = parse_citation(token)
        if ref is not None:
            if ref.kind != "file":
                raise ValueError(f"Target citations must be @file:..., got {token}")
            token = ref.canonical_id
        return {"file": _normalize_relpath(repo_root, token), "scope": "full"}

    if isinstance(item, Mapping):
        if "file" not in item:
            raise ValueError(f"Target mapping missing required 'file': {item}")
        target = {str(key): copy.deepcopy(value) for key, value in item.items()}
        target["file"] = _normalize_relpath(repo_root, _string(target.get("file")))
        target["scope"] = _string(target.get("scope")) or "full"
        if not target["file"]:
            raise ValueError(f"Target mapping resolved to empty file path: {item}")
        return target

    raise ValueError(f"Unsupported target item: {item!r}")


def _resolve_target_list(
    value: Any,
    *,
    repo_root: Path,
    scope: Mapping[str, Any],
    captures: Mapping[str, list[str]],
    doc_registry_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()
    for item in _resolve_listish(
        value,
        scope=scope,
        captures=captures,
        doc_registry_payload=doc_registry_payload,
    ):
        target = _coerce_target_item(repo_root, item)
        signature = (
            _string(target.get("file")),
            _string(target.get("scope")),
            _string(target.get("name")) or None,
            _string(target.get("heading")) or None,
        )
        if signature in seen:
            continue
        seen.add(signature)
        targets.append(target)
    return targets


def _resolve_pack_context_list(
    value: Any,
    *,
    repo_root: Path,
    mission_path: Path,
    scope: Mapping[str, Any],
    doc_registry_payload: Mapping[str, Any] | None,
    owner: str,
) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for item in _resolve_listish(
        value,
        scope=scope,
        captures={},
        doc_registry_payload=doc_registry_payload,
    ):
        token = _string(item)
        if not token:
            continue
        ref = parse_citation(token)
        if ref is not None and ref.kind == "file":
            token = ref.canonical_id
        normalized = _normalize_pack_relpath(repo_root, mission_path, token)
        candidate = Path(normalized)
        resolved = candidate if candidate.is_absolute() else (repo_root / candidate)
        if not resolved.exists():
            raise ValueError(
                f"{owner} references missing context file: {token} "
                f"(resolved to {normalized})"
            )
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _resolve_mission_injected_context(
    *,
    repo_root: Path,
    mission_path: Path,
    mission_payload: Mapping[str, Any],
    scope: Mapping[str, Any],
    doc_registry_payload: Mapping[str, Any] | None,
) -> tuple[list[str], list[str], list[str]]:
    skill_files = _resolve_pack_context_list(
        mission_payload.get("skill_files"),
        repo_root=repo_root,
        mission_path=mission_path,
        scope=scope,
        doc_registry_payload=doc_registry_payload,
        owner=f"mission template '{_string(mission_payload.get('id')) or mission_path.stem}' skill_files",
    )
    shared_context_files = _resolve_pack_context_list(
        mission_payload.get("shared_context_files"),
        repo_root=repo_root,
        mission_path=mission_path,
        scope=scope,
        doc_registry_payload=doc_registry_payload,
        owner=(
            f"mission template '{_string(mission_payload.get('id')) or mission_path.stem}' "
            "shared_context_files"
        ),
    )
    injected_context_files = _dedupe_strings([*skill_files, *shared_context_files])
    return skill_files, shared_context_files, injected_context_files


def _resolve_required_params(required: Sequence[Any], params: Mapping[str, Any], *, owner: str) -> None:
    missing: list[str] = []
    for item in required:
        token = _string(item)
        value = params.get(token)
        if value is None:
            missing.append(token)
        elif isinstance(value, str) and not value.strip():
            missing.append(token)
        elif isinstance(value, list) and not value:
            missing.append(token)
    if missing:
        raise ValueError(f"{owner} missing required params: {', '.join(missing)}")


def _expand_repeat_items(
    repeat_spec: Mapping[str, Any] | None,
    *,
    scope: Mapping[str, Any],
    captures: Mapping[str, list[str]],
    doc_registry_payload: Mapping[str, Any] | None,
) -> list[Any]:
    if not isinstance(repeat_spec, Mapping):
        return [None]

    raw_from = repeat_spec.get("from")
    if isinstance(raw_from, str) and "{{" not in raw_from and raw_from in scope:
        resolved = scope.get(raw_from)
    else:
        resolved = _resolve_recursive(
            raw_from,
            scope=scope,
            captures=captures,
            doc_registry_payload=doc_registry_payload,
        )

    if isinstance(resolved, int):
        if resolved < 1:
            raise ValueError("Repeat count must be >= 1.")
        return [{"index": idx} for idx in range(1, resolved + 1)]

    if isinstance(resolved, list):
        if not resolved:
            raise ValueError("Repeat source resolved to an empty list.")
        return resolved

    raise ValueError("Repeat spec must resolve to a positive integer or a non-empty list.")


def _expand_one_group(
    *,
    repo_root: Path,
    atom_payload: Mapping[str, Any],
    group_spec: Mapping[str, Any],
    base_scope: Mapping[str, Any],
    captures: Mapping[str, list[str]],
    doc_registry_payload: Mapping[str, Any] | None,
    injected_context_files: Sequence[str] = (),
    controller_heartbeat_ref: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    atom_defaults = atom_payload.get("defaults") if isinstance(atom_payload.get("defaults"), Mapping) else {}
    atom_group = atom_payload.get("group") if isinstance(atom_payload.get("group"), Mapping) else {}
    atom_required = atom_payload.get("required_params") if isinstance(atom_payload.get("required_params"), list) else []
    with_payload = group_spec.get("with") if isinstance(group_spec.get("with"), Mapping) else {}
    capture_as = _string(group_spec.get("capture_as"))

    items = _expand_repeat_items(
        group_spec.get("repeat") if isinstance(group_spec.get("repeat"), Mapping) else None,
        scope=base_scope,
        captures=captures,
        doc_registry_payload=doc_registry_payload,
    )

    expanded_groups: list[dict[str, Any]] = []
    captured_labels: list[str] = []

    for index, item in enumerate(items, start=1):
        local_params = _deep_merge(atom_defaults, with_payload)
        local_scope = {
            **copy.deepcopy(base_scope),
            **copy.deepcopy(local_params),
            "item": copy.deepcopy(item),
            "index": index,
            "repeat_count": len(items),
        }
        _resolve_required_params(atom_required, local_scope, owner=f"group atom '{_string(atom_payload.get('id'))}'")

        group: dict[str, Any] = {}
        for field in (
            "label",
            "notes",
            "role",
            "situation",
            "question",
            "acceptance",
            "provider",
            "downstream_consumer",
        ):
            resolved = _resolve_recursive(
                atom_group.get(field),
                scope=local_scope,
                captures=captures,
                doc_registry_payload=doc_registry_payload,
            )
            token = _string(resolved)
            if token:
                group[field] = token

        for field in ("output_contract", "depends_on"):
            group[field] = _resolve_string_list(
                atom_group.get(field),
                repo_root=repo_root,
                scope=local_scope,
                captures=captures,
                doc_registry_payload=doc_registry_payload,
            )
        group["context_files"] = _dedupe_strings(
            [
                *list(injected_context_files),
                *_resolve_string_list(
                    atom_group.get("context_files"),
                    repo_root=repo_root,
                    scope=local_scope,
                    captures=captures,
                    doc_registry_payload=doc_registry_payload,
                ),
            ]
        )

        for field in ("provider_config", "response_schema", "standards"):
            resolved = _resolve_recursive(
                atom_group.get(field),
                scope=local_scope,
                captures=captures,
                doc_registry_payload=doc_registry_payload,
            )
            if isinstance(resolved, Mapping):
                group[field] = copy.deepcopy(dict(resolved))
        if controller_heartbeat_ref and isinstance(group.get("response_schema"), Mapping):
            group["response_schema"] = wrap_response_schema_with_heartbeat_ref(
                group.get("response_schema")
            )
            envelope_note = (
                "Return JSON with `heartbeat_ref` echoing the injected controller heartbeat metadata "
                "and `payload` carrying the mission-specific response body."
            )
            acceptance_text = _string(group.get("acceptance"))
            group["acceptance"] = (
                f"{acceptance_text} {envelope_note}".strip()
                if acceptance_text
                else envelope_note
            )

        resolved_json_only = _resolve_recursive(
            atom_group.get("json_only"),
            scope=local_scope,
            captures=captures,
            doc_registry_payload=doc_registry_payload,
        )
        if isinstance(resolved_json_only, bool):
            group["json_only"] = resolved_json_only
        elif _string(resolved_json_only).lower() in {"true", "false"}:
            group["json_only"] = _string(resolved_json_only).lower() == "true"

        for bool_field in ("external_research_allowed",):
            raw_val = with_payload.get(bool_field, atom_group.get(bool_field))
            resolved_bool = _resolve_recursive(
                raw_val, scope=local_scope, captures=captures,
                doc_registry_payload=doc_registry_payload,
            )
            if isinstance(resolved_bool, bool):
                group[bool_field] = resolved_bool
            elif _string(resolved_bool).lower() in {"true", "false"}:
                group[bool_field] = _string(resolved_bool).lower() == "true"

        response_surface = _resolve_recursive(
            atom_group.get("response_surface"),
            scope=local_scope,
            captures=captures,
            doc_registry_payload=doc_registry_payload,
        )
        if response_surface not in (None, "", []):
            group["response_surface"] = response_surface

        group["targets"] = _resolve_target_list(
            atom_group.get("targets"),
            repo_root=repo_root,
            scope=local_scope,
            captures=captures,
            doc_registry_payload=doc_registry_payload,
        )

        expanded_groups.append(group)
        label = _string(group.get("label"))
        if capture_as and label:
            captured_labels.append(label)

    return expanded_groups, captured_labels


def expand_mission_template(
    *,
    repo_root: Path,
    mission_id: str,
    params: Mapping[str, Any] | None = None,
    doc_registry_payload: Mapping[str, Any] | None = None,
    family_context: Mapping[str, Any] | None = None,
) -> MissionExpansion:
    """
    [ACTION]
    - Teleology: Compile one authored observe mission template into a validated ObserveSessionPlan payload plus expansion metadata.
    - Mechanism: Load the mission, merge defaults and params, expand referenced group atoms and repeats, resolve doc-registry selectors, then validate the resulting plan through ObserveSessionPlan.
    - Guarantee: Returns a MissionExpansion object containing the validated plan, captures, effective params, and template metadata.
    - Fails: Raises ValueError when required params are missing, selectors cannot resolve, or the expanded plan fails ObserveSessionPlan validation.
    - When-needed: Open when an authored mission needs to become a concrete ObserveSessionPlan for execution, preview, or meta-mission tooling.
    - Escalates-to: tools/meta/apply/python_std_bridge_meta_mission.py; tools/meta/apply/run_observe_plan.py; system/lib/observe_apply_context.py
    """
    mission_path = _resolve_mission_template_path(repo_root, mission_id)
    mission_payload = _load_json(mission_path)
    mission_kind = _string(mission_payload.get("kind"))
    if mission_kind == MISSION_CHAIN_KIND:
        raise ValueError(
            "Mission chains are control-plane contracts, not ObserveSessionPlan payloads. "
            "Load the chain template directly or execute it through a chain runtime."
        )
    mission_defaults = mission_payload.get("defaults") if isinstance(mission_payload.get("defaults"), Mapping) else {}
    effective_params = _deep_merge(mission_defaults, params or {})
    if "research_seed" in effective_params:
        from system.lib.research_seed import compile_bridge_research_probe_params
        effective_params = compile_bridge_research_probe_params(effective_params, repo_root=repo_root)
    _resolve_required_params(
        mission_payload.get("required_params") if isinstance(mission_payload.get("required_params"), list) else [],
        effective_params,
        owner=f"mission template '{_string(mission_payload.get('id')) or mission_path.stem}'",
    )

    template_version = (
        _string(mission_payload.get("template_version"))
        or MISSION_TEMPLATE_SCHEMA_VERSION
    )
    raw_plan = mission_payload.get("plan") if isinstance(mission_payload.get("plan"), Mapping) else {}
    family_payload = dict(family_context or {})
    continuity_source = family_payload.get("continuity") if isinstance(family_payload.get("continuity"), Mapping) else None
    plan_family = raw_plan.get("family") if isinstance(raw_plan.get("family"), Mapping) else {}
    if plan_family:
        resolved_plan_family = _resolve_recursive(
            plan_family,
            scope={
                **copy.deepcopy(effective_params),
                "generated_at": _utc_now_iso(),
                "mission_id": _string(mission_payload.get("id")) or mission_path.stem,
                "mission_template_version": template_version,
                "family": family_payload,
            },
            captures={},
            doc_registry_payload=doc_registry_payload,
        )
        if isinstance(resolved_plan_family, Mapping) and isinstance(resolved_plan_family.get("continuity"), Mapping):
            continuity_source = resolved_plan_family.get("continuity")
    continuity_metadata = _continuity_metadata(continuity_source if isinstance(continuity_source, Mapping) else None)
    family_payload["continuity"] = continuity_metadata
    plan_scope: dict[str, Any] = {
        **copy.deepcopy(effective_params),
        "generated_at": _utc_now_iso(),
        "mission_id": _string(mission_payload.get("id")) or mission_path.stem,
        "mission_template_version": template_version,
        "family": family_payload,
    }
    skill_files, shared_context_files, injected_context_files = _resolve_mission_injected_context(
        repo_root=repo_root,
        mission_path=mission_path,
        mission_payload=mission_payload,
        scope=plan_scope,
        doc_registry_payload=doc_registry_payload,
    )
    heartbeat_context_path = _string(continuity_metadata.get("controller_heartbeat_path"))
    if heartbeat_context_path:
        heartbeat_candidate = repo_root / heartbeat_context_path
        if heartbeat_candidate.exists():
            injected_context_files = _dedupe_strings(
                [*injected_context_files, heartbeat_context_path]
            )
    plan_scope["mission_skill_files"] = list(skill_files)
    plan_scope["mission_shared_context_files"] = list(shared_context_files)
    plan_scope["mission_injected_context_files"] = list(injected_context_files)
    plan_scope["controller_heartbeat_path"] = heartbeat_context_path or None
    plan_scope["controller_heartbeat_ref"] = continuity_metadata.get("controller_heartbeat_ref")
    resolved_dispatch_policy = _resolve_recursive(
        mission_payload.get("dispatch_policy"),
        scope=plan_scope,
        captures={},
        doc_registry_payload=doc_registry_payload,
    )
    if not isinstance(resolved_dispatch_policy, Mapping):
        resolved_dispatch_policy = {}

    captures: dict[str, list[str]] = {}
    groups: list[dict[str, Any]] = []
    atoms_dir, _, _ = _template_dirs(repo_root)
    for group_spec in mission_payload.get("groups", []) if isinstance(mission_payload.get("groups"), list) else []:
        if not isinstance(group_spec, Mapping):
            raise ValueError(f"Mission group spec must be an object: {group_spec!r}")
        atom_id = _string(group_spec.get("use"))
        if not atom_id:
            raise ValueError("Mission group spec missing required 'use' atom id.")
        atom_payload = _load_json(
            _resolve_template_path(atoms_dir, atom_id, expected_kind="observe_group_atom")
        )
        expanded_groups, captured_labels = _expand_one_group(
            repo_root=repo_root,
            atom_payload=atom_payload,
            group_spec=group_spec,
            base_scope=plan_scope,
            captures=captures,
            doc_registry_payload=doc_registry_payload,
            injected_context_files=injected_context_files,
            controller_heartbeat_ref=(
                continuity_metadata.get("controller_heartbeat_ref")
                if isinstance(continuity_metadata.get("controller_heartbeat_ref"), Mapping)
                else None
            ),
        )
        groups.extend(expanded_groups)
        capture_as = _string(group_spec.get("capture_as"))
        if capture_as:
            captures[capture_as] = captured_labels

    resolved_plan = _resolve_recursive(
        raw_plan,
        scope=plan_scope,
        captures=captures,
        doc_registry_payload=doc_registry_payload,
    )
    if not isinstance(resolved_plan, Mapping):
        raise ValueError("Mission template 'plan' must resolve to an object.")

    plan: dict[str, Any] = dict(resolved_plan)
    plan["schema_version"] = _string(plan.get("schema_version")) or "1.0"
    plan["drafted_at"] = _string(plan.get("drafted_at")) or plan_scope["generated_at"]
    plan["template_version"] = (
        _string(plan.get("template_version"))
        or f"observe_mission:{_string(mission_payload.get('id')) or mission_path.stem}@{template_version}"
    )

    for field in ("goal_question", "success_criteria", "intended_posture", "wait_notes", "wait_notes_ref", "prompt", "notes", "result_note_path", "problem_text", "dump_dir", "campaign_id", "round_id", "carry_forward_posture", "parent_observe_id"):
        token = _string(plan.get(field))
        if token:
            plan[field] = token
        elif field in plan:
            plan[field] = None

    for field in ("context_files",):
        plan[field] = _resolve_string_list(
            plan.get(field),
            repo_root=repo_root,
            scope=plan_scope,
            captures=captures,
            doc_registry_payload=doc_registry_payload,
        )

    if "round_index" in plan and not isinstance(plan.get("round_index"), int):
        round_value = plan.get("round_index")
        if round_value in (None, ""):
            plan["round_index"] = None
        else:
            try:
                plan["round_index"] = int(round_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"round_index must resolve to an integer, got {round_value!r}") from exc

    plan["groups"] = groups

    try:
        validated = ObserveSessionPlan(**plan)
    except Exception as exc:  # pragma: no cover - exercised by tests through ValueError path
        raise ValueError(f"Expanded mission template is not a valid ObserveSessionPlan: {exc}") from exc

    try:
        template_path = mission_path.relative_to(repo_root).as_posix()
    except ValueError:
        template_path = mission_path.resolve().as_posix()

    return MissionExpansion(
        mission_id=_string(mission_payload.get("id")) or mission_path.stem,
        mission_template_version=template_version,
        template_path=template_path,
        params=copy.deepcopy(effective_params),
        plan=json.loads(validated.model_dump_json(exclude_none=True)),
        captures={key: list(value) for key, value in captures.items()},
        family_context={
            "family_id": _string(family_payload.get("family_id")),
            "family_dir": _string(family_payload.get("family_dir")),
            "has_doc_registry": bool(doc_registry_payload),
            "continuity": continuity_metadata,
        },
        continuity_metadata=continuity_metadata,
        dispatch_policy=dict(resolved_dispatch_policy),
        skill_files=list(skill_files),
        shared_context_files=list(shared_context_files),
        injected_context_files=list(injected_context_files),
    )


def emit_mission_template_schema() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Emit the documented schema for observe mission-template authors and tooling surfaces.
    - Mechanism: Return a literal schema summary covering roots, atom shape, mission shape, pack shape, and supported source-object selectors.
    - Guarantee: Returns a deterministic mapping describing the current authored mission-template contract.
    - Fails: None.
    - When-needed: Open when a kernel or tooling surface needs the author-facing mission-template schema without reading the implementation details of expansion.
    - Escalates-to: system/lib/kernel/commands/substrate.py; tools/meta/apply/python_std_bridge_meta_mission.py
    """
    return {
        "kind": "observe_mission_template_schema",
        "schema_version": MISSION_TEMPLATE_SCHEMA_VERSION,
        "root": MISSION_TEMPLATE_ROOT_REL,
        "atoms_dir": MISSION_TEMPLATE_ATOMS_REL,
        "missions_dir": MISSION_TEMPLATE_MISSIONS_REL,
        "meta_missions_dir": MISSION_TEMPLATE_META_MISSIONS_REL,
        "atom_shape": {
            "kind": "observe_group_atom",
            "required": ["id", "kind", "schema_version", "group"],
            "optional": ["description", "template_version", "defaults", "required_params"],
            "group_fields": [
                "label",
                "notes",
                "role",
                "situation",
                "question",
                "acceptance",
                "output_contract",
                "response_surface",
                "downstream_consumer",
                "context_files",
                "depends_on",
                "targets",
            ],
        },
        "mission_shape": {
            "kind": "observe_mission_template",
            "required": ["id", "kind", "schema_version", "plan", "groups"],
            "optional": [
                "description",
                "template_version",
                "defaults",
                "required_params",
                "dispatch_policy",
                "skill_files",
                "shared_context_files",
            ],
            "plan_optional_fields": [
                "context_files",
                "raw_seed_family",
                "shard_packet_request",
                "standards_refs",
                "cycle_dir",
                "cycle_context_mode",
            ],
            "group_spec_fields": {
                "use": "atom id or repo-relative atom path",
                "capture_as": "optional capture bucket name for expanded labels",
                "repeat": {"from": "positive integer, param key, or list-producing source"},
                "with": "per-use local params merged over atom defaults",
            },
        },
        "mission_chain_shape": {
            "kind": "observe_mission_chain",
            "required": ["id", "kind", "schema_version", "chain_steps", "interrupt_contract"],
            "optional": [
                "description",
                "template_version",
                "intent_distillation",
                "dispatch_policy_note",
                "operator_surface",
                "open_for_codex",
            ],
            "chain_step_fields": {
                "step_id": "stable chain-local identifier",
                "ordinal": "positive_integer ordering token",
                "worker_surface": "controller_local | bridge | controller_review",
                "binding": "object; may include cli and/or child_mission_id",
                "optional": "boolean",
                "optional_condition": "string_optional",
                "interrupt_seam_after": "boolean",
                "notes": "string_optional",
            },
            "interrupt_contract_fields": {
                "seam_definition": "string",
                "stop_signal_path": "repo_relative_path",
                "stop_signal_semantics": "string",
                "graceful_partial_posture": "string",
                "resume_ledger_path": "repo_relative_path",
                "resume_ledger_entry_shape": "string_list",
                "idempotency_rule": "string",
            },
        },
        "mission_pack_shape": {
            "root": MISSION_TEMPLATE_META_MISSIONS_REL,
            "entrypoint": "meta_missions/<mission_id>/mission.json",
            "recommended_companions": ["README.md", "params.example.json"],
            "pack_context_fields": {
                "dispatch_policy": (
                    "mapping: canonical dispatch contract for bridge-backed mission packs. "
                    "Use `cohort_size` for plan backlog, `wave_width` for in-flight "
                    "dispatch concurrency, and source provider ceilings from "
                    "`tools/meta/bridge/provider_capabilities.json`."
                ),
                "skill_files": (
                    "string_list: reusable worker-skill assets auto-injected into every "
                    "expanded group context_files entry"
                ),
                "shared_context_files": (
                    "string_list: additive pack-owned context auto-injected into every "
                    "expanded group context_files entry"
                ),
            },
            "reserved_continuity_metadata": {
                "path_refs": "string_list",
                "skill_refs": "string_list",
                "coordinator_kind": "ide_controller | codex_subagent | bridge_coordinator | grouped_observe",
                "coordinator_seed_ref": "string_optional",
                "macro_operations": "string_list"
            },
            "notes": (
                "Use a folder per authored meta mission when the template needs its own docs, "
                "examples, or helper assets. Because plan-level context is not inherited by "
                "group prompts, pack-owned skill_files/shared_context_files are expanded onto "
                "every group context_files list automatically. Bridge-backed packs should also "
                "author a dispatch_policy block so operator surfaces can expose canonical "
                "cohort_size / wave_width controls without per-mission naming drift. "
                "Control-plane mission chains use kind=observe_mission_chain and own step order, "
                "interrupt seams, and resume-ledger semantics rather than ObserveSessionPlan groups."
            ),
        },
        "dispatch_policy_shape": {
            "cohort_size": {
                "semantics": "How many units of work are selected into this plan.",
                "default_for_this_mission": "positive_integer",
            },
            "wave_width": {
                "semantics": "How many selected units are in flight right now.",
                "default_for_this_mission": "positive_integer",
                "operator_soft_cap_recommendation": "string_optional",
            },
            "provider_ceiling": {
                "semantics": "Descriptive provider hard-cap metadata; runtime enforcement remains sourced from provider_capabilities.json.",
                "source": "tools/meta/bridge/provider_capabilities.json",
                "current_caps": "mapping_optional",
            },
            "contract_note": "string_optional",
            "frontend_surface_note": "string_optional",
            "operator_soft_cap_recommendation": "string_optional",
        },
        "source_objects": {
            "$param": "Read a local param by key",
            "$item": "Read the active repeat item (or one of its fields)",
            "$capture": "Read labels captured from a prior repeated group expansion",
            "$doc_code_refs": "Resolve one @doc:... selector to its code_refs list",
            "$doc_query_code_refs": "Query doc_registry entries and flatten their code_refs",
        },
        "interpolation": {
            "syntax": "{{path.to.value}}",
            "special_keys": ["item", "index", "repeat_count", "family", "generated_at", "mission_id", "mission_template_version"],
        },
        "examples": {
            "repeat": {
                "use": "probe_concept_shard",
                "capture_as": "probe_groups",
                "repeat": {"from": {"$param": "shards"}},
                "with": {
                    "label": "probe_{{item.slug}}",
                    "question": "{{item.question}}",
                    "targets": {"$item": "targets"},
                },
            },
            "captured_dependency": {
                "use": "synthesis_merge",
                "with": {
                    "label": "synthesis",
                    "depends_on": {"$capture": "probe_groups"},
                },
            },
            "shard_packet_request": {
                "plan": {
                    "shard_packet_request": {
                        "group": "{{idea_group}}",
                        "batch_size": 20,
                        "skip_concept_catalog": True,
                    }
                }
            },
        },
    }
