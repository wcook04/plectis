"""
[PURPOSE]
- Teleology: Load the grouped standards registry and project it into a compact authority catalog so kernel and observe/apply surfaces can discover which standards govern each artifact family.
- Mechanism: Read the top-level standards registry, follow each group's `authority_index` pointer, and normalize the registry plus per-group artifact metadata into one catalog payload.
- Non-goal: Validate standard semantics or mutate standards files; this module only loads and summarizes registry/authority data.

[INTERFACE]
- Exports: `load_standards_registry`, `load_group_authority_index`, `build_standards_catalog`.
- Reads: `codex/standards/standards_registry.json` and any group authority-index JSON files referenced from it.
- Writes: None.
- Schema: `build_standards_catalog()` returns registry metadata plus normalized group cards, artifact cards, and embedded authority payloads.

[FLOW]
- Load the top-level standards registry -> resolve each group's authority index -> normalize artifact/supporting-asset metadata -> emit one grouped catalog envelope.
- When-needed: Open when routing, kernel infrastructure, or observe/apply enrichment needs a compact catalog of standards groups and their governed artifacts instead of reading the registry and authority indexes separately.
- Escalates-to: codex/standards/standards_registry.json; system/lib/observe_apply_contracts.py
- Couples: `system/lib/observe_plan_enrichment.py` and kernel infrastructure commands depend on this module's grouped catalog shape to advertise standards ownership.
- Navigation-group: kernel_lib

[DEPENDENCIES]
- json: Deserialize the registry and group authority-index payloads.
- pathlib.Path: Resolve registry and authority-index files under the supplied repo root.
- typing.Mapping: Validate mapping-shaped JSON payloads before normalization.

[CONSTRAINTS]
- Guarantee: Missing or unreadable registry/authority files degrade to empty mappings instead of raising from the public loaders.
- Orders: Group order follows the registry list order, and artifact cards follow authority-index artifact iteration order.
- Fails: None on missing or malformed JSON from the public load/build path; callers receive empty or partial catalog payloads instead.
- Non-goal: This module does not check that referenced standards actually match runtime artifacts beyond summarizing the declared metadata.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

STANDARDS_REGISTRY_PATH = "codex/standards/standards_registry.json"


def _string(value: Any) -> str:
    return str(value or "").strip()


def _read_json_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def load_standards_registry(*, repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load the top-level standards registry so callers can start from the declared standards grouping rather than direct filesystem guesses.
    - Mechanism: Resolve `STANDARDS_REGISTRY_PATH` under `repo_root` and return the parsed mapping or `{}` when unreadable.
    - Reads: `repo_root / STANDARDS_REGISTRY_PATH`.
    - Writes: None.
    - Guarantee: Returns a mapping-shaped registry payload or `{}`.
    - Fails: None.
    - When-needed: Open when a caller needs the root standards registry before resolving group authority indexes.
    - Escalates-to: system/lib/standards_registry.py::build_standards_catalog; codex/standards/standards_registry.json
    """
    return _read_json_mapping((repo_root / STANDARDS_REGISTRY_PATH).resolve())


def load_group_authority_index(*, repo_root: Path, path: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load one group authority index from the path declared in the standards registry.
    - Mechanism: Normalize the incoming relative path, short-circuit blank values to `{}`, and return the parsed authority-index mapping or `{}` when unreadable.
    - Reads: `path` and the referenced JSON file under `repo_root`.
    - Writes: None.
    - Guarantee: Returns a mapping-shaped authority payload or `{}`.
    - Fails: None.
    - When-needed: Open when one standards group has already been selected and the next step is reading its authority index.
    - Escalates-to: system/lib/standards_registry.py::build_standards_catalog; system/lib/observe_apply_contracts.py::resolve_observe_apply_standards_bundle
    """
    rel_path = _string(path)
    if not rel_path:
        return {}
    return _read_json_mapping((repo_root / rel_path).resolve())


def build_standards_catalog(*, repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the bridge- and kernel-friendly standards catalog that summarizes grouped standards ownership, artifact kinds, and supporting assets from the registry layer.
    - Mechanism: Load the standards registry, iterate each group, load its authority index, normalize artifact cards and selected registry metadata, and emit the catalog envelope.
    - Reads: `repo_root`, `load_standards_registry()`, and each group's authority-index JSON payload.
    - Writes: None.
    - Guarantee: Returns a dict containing registry metadata, kernel navigation hints, and one normalized card per standards group.
    - Fails: None for missing or malformed registry/authority files; those groups degrade to empty authority payloads or disappear if the registry itself is empty.
    - Orders: Preserves registry group ordering and the first-seen artifact ordering from each authority index.
    - When-needed: Open when kernel or observe/apply routing needs the compact grouped standards catalog instead of raw registry JSON.
    - Escalates-to: system/lib/observe_plan_enrichment.py; system/lib/kernel/commands/infrastructure.py
    - Navigation-group: kernel_lib
    """
    registry = load_standards_registry(repo_root=repo_root)
    groups_payload = registry.get("groups") if isinstance(registry.get("groups"), list) else []
    groups: list[dict[str, Any]] = []

    for item in groups_payload:
        if not isinstance(item, Mapping):
            continue
        authority_index_path = _string(item.get("authority_index"))
        authority_index = load_group_authority_index(repo_root=repo_root, path=authority_index_path)
        artifacts = authority_index.get("artifacts") if isinstance(authority_index.get("artifacts"), Mapping) else {}
        supporting_assets = (
            authority_index.get("supporting_assets")
            if isinstance(authority_index.get("supporting_assets"), Mapping)
            else {}
        )
        artifact_cards: list[dict[str, Any]] = []
        for artifact_kind, spec in artifacts.items():
            if not isinstance(spec, Mapping):
                continue
            artifact_cards.append(
                {
                    "artifact_kind": _string(artifact_kind),
                    "description": _string(spec.get("description")),
                    "json_standard": _string(spec.get("json_standard")),
                    "markdown_standard": _string(spec.get("markdown_standard")),
                    "path_globs": [
                        _string(path_glob)
                        for path_glob in (spec.get("path_globs") or [])
                        if _string(path_glob)
                    ],
                    "lifecycle": _string(spec.get("lifecycle")),
                    "authority_rule": _string(spec.get("authority_rule")),
                }
            )
        groups.append(
            {
                "group_id": _string(item.get("group_id")),
                "title": _string(item.get("title")),
                "group_root": _string(item.get("group_root")),
                "authority_index": authority_index_path,
                "summary": _string(item.get("summary")),
                "storage_status": _string(item.get("storage_status")),
                "kernel_navigation_hints": [
                    _string(hint)
                    for hint in (item.get("kernel_navigation_hints") or [])
                    if _string(hint)
                ],
                "artifact_count": len(artifact_cards),
                "supporting_asset_count": len(supporting_assets),
                "artifacts": artifact_cards,
                "authority_payload": authority_index,
            }
        )

    return {
        "registry_path": STANDARDS_REGISTRY_PATH,
        "root": _string(registry.get("root")),
        "purpose": _string(registry.get("purpose")),
        "naming_contract": registry.get("naming_contract") if isinstance(registry.get("naming_contract"), Mapping) else {},
        "folder_pattern": registry.get("folder_pattern") if isinstance(registry.get("folder_pattern"), Mapping) else {},
        "kernel_navigation_hints": [
            _string(hint)
            for hint in (registry.get("kernel_navigation_hints") or [])
            if _string(hint)
        ],
        "groups": groups,
    }
