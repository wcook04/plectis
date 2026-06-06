#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Given a set of changed paths (or a mutation receipt), produce a
  conservative, explainable selection of validators + exact pytest nodeids
  that should run. Per std_test_impact_map.json. Mutation class M0E.
- Mechanism: Stage A determine changed paths. Stage B map paths to lattice
  graph artifact_kinds. Stage C consult declared selectors and expand via
  graph freshness edges. Stage D mark validators (run before tests). Stage E
  add fallback bundle if nothing else matched. Never returns empty: empty
  selection always triggers a fallback bundle.

[INTERFACE]
- Reads: state/lattice/lattice_graph_latest.json,
  state/testing/test_inventory.json,
  codex/testing/test_impact_map.json (declared selector POLICY — authority class),
  codex/standards/lattice_registry.json (fallback bundles).
- LEGACY: state/testing/test_impact_map.json is FORBIDDEN (state/** is evidence,
  not policy). The selector fails fast if that path exists.
- Writes: state/testing/test_impact_expanded_latest.json (when --write).

[CLI]
  select_impacted_tests.py --changed <path> [--changed <path> ...]
  select_impacted_tests.py --json                # JSON to stdout
  select_impacted_tests.py --write               # persist expanded projection
  select_impacted_tests.py --receipt <file>      # read changed_artifacts from a mutation receipt JSON
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
GRAPH_PATH = REPO_ROOT / "state" / "lattice" / "lattice_graph_latest.json"
INVENTORY_PATH = REPO_ROOT / "state" / "testing" / "test_inventory.json"
# Declared selector policy lives under codex/** (authority class), NOT state/**
# (evidence/projection class). M0E/M1 writers must NEVER mutate this file.
IMPACT_MAP_PATH = REPO_ROOT / "codex" / "testing" / "test_impact_map.json"
REGISTRY_PATH = REPO_ROOT / "codex" / "standards" / "lattice_registry.json"
# Generated expansion projection of the declared policy + current inventory + graph.
EXPANDED_PATH = REPO_ROOT / "state" / "testing" / "test_impact_expanded_latest.json"
# Legacy path that must NEVER be resurrected. state/** is evidence-only; declared
# policy lives only under codex/**. The selector refuses to run if this exists.
FORBIDDEN_LEGACY_IMPACT_MAP = REPO_ROOT / "state" / "testing" / "test_impact_map.json"


class LegacyImpactMapForbidden(RuntimeError):
    """Raised when the forbidden legacy declared-policy path exists at runtime."""


def _enforce_legacy_guard() -> None:
    if FORBIDDEN_LEGACY_IMPACT_MAP.exists():
        try:
            forbidden_display = str(FORBIDDEN_LEGACY_IMPACT_MAP.relative_to(REPO_ROOT))
        except ValueError:
            forbidden_display = str(FORBIDDEN_LEGACY_IMPACT_MAP)
        raise LegacyImpactMapForbidden(
            "declared test impact policy must live under codex/testing/test_impact_map.json; "
            f"{forbidden_display} is forbidden because state/** is evidence/projection "
            "territory. Move the file back to codex/testing/ and delete the state/** copy."
        )

if __package__ in (None, ""):
    sys.path.insert(0, str(REPO_ROOT / "tools" / "meta" / "factory"))

import append_lattice_event as ev_helper  # noqa: E402
import test_inventory as inventory_owner  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def _glob_match(path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(path, pattern):
        return True
    if "**" in pattern:
        # fnmatch doesn't honour ** as recursive; broaden manually.
        flat = pattern.replace("**/", "").replace("**", "*")
        return fnmatch.fnmatch(path, flat) or fnmatch.fnmatch(path.split("/")[-1], flat)
    if "/" not in pattern and "/" in path:
        return fnmatch.fnmatch(path.split("/")[-1], pattern)
    return False


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _inventory_freshness(inventory: dict[str, Any]) -> dict[str, Any]:
    base = {
        "owner_tool": "tools/meta/testing/test_inventory.py",
        "check_command": "tools/meta/testing/test_inventory.py --check",
        "refresh_command": "tools/meta/testing/test_inventory.py --write",
    }
    existing = inventory.get("source_fingerprint") if isinstance(inventory, dict) else None
    if not isinstance(existing, dict):
        return {
            **base,
            "status": "missing_source_fingerprint",
            "trusted_for_selector": False,
        }
    try:
        current = inventory_owner.build_source_fingerprint()
    except Exception as exc:  # pragma: no cover - defensive read-model boundary
        return {
            **base,
            "status": "freshness_check_unavailable",
            "trusted_for_selector": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    fresh = inventory_owner.source_fingerprints_match(existing, current)
    return {
        **base,
        "status": "fresh" if fresh else "stale",
        "trusted_for_selector": fresh,
        "existing_digest": existing.get("digest"),
        "current_digest": current.get("digest"),
        "existing_path_count": existing.get("path_count"),
        "current_path_count": current.get("path_count"),
    }


def _resolve_changed_paths(args) -> list[str]:
    paths: list[str] = []
    if args.receipt:
        receipt = _load_json(Path(args.receipt))
        if receipt:
            for r in receipt.get("changed_artifacts", []) or []:
                if isinstance(r, str):
                    paths.append(r)
                elif isinstance(r, dict) and "path" in r:
                    paths.append(r["path"])
    if args.changed:
        paths.extend(args.changed)
    norm: list[str] = []
    for p in paths:
        try:
            norm.append(str(Path(p).resolve().relative_to(REPO_ROOT)))
        except ValueError:
            norm.append(p)
    seen: set[str] = set()
    out: list[str] = []
    for p in norm:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _classify_change(path: str) -> str:
    """Coarse classification used for the fallback bundle when nothing matches."""
    if path.startswith("codex/doctrine/paper_modules/") or path.startswith("codex/doctrine/skills/") or path.startswith("codex/doctrine/concepts/") or path.startswith("codex/doctrine/mechanisms/"):
        return "unknown_doctrine_change"
    if path.startswith("codex/standards/std_"):
        return "unknown_standard_change"
    if path in ("reactions.yaml",) or path.startswith("system/lib/launchable") or path.startswith("tools/meta/control/"):
        return "unknown_runtime_change"
    if path.startswith("system/server/ui/"):
        return "unknown_server_or_ui_change"
    if path.startswith("tools/meta/testing/"):
        return "selector_code_change"
    if path.startswith("codex/standards/lattice_") or path.startswith("tools/meta/factory/append_lattice_") or path.startswith("tools/meta/factory/build_lattice_") or path.startswith("tools/meta/factory/lattice_"):
        return "lattice_substrate_change"
    return "unknown_doctrine_change"


def _artifact_kind_for(path: str, graph: dict) -> str | None:
    for node in graph.get("nodes", []):
        if node.get("kind") == "artifact" and node.get("path") == path:
            return node.get("artifact_kind")
    return None


def _changed_test_file_nodeids(changed_paths: list[str], item_index: dict[str, dict]) -> dict[str, list[str]]:
    """Return exact inventory nodeids for changed pytest files.

    The declared impact map handles source artifacts. A changed test file is
    already its own focused proof route, so it should not fall through to a
    broad fallback bundle when the inventory can resolve exact nodeids.
    """
    by_path: dict[str, list[str]] = {}
    for nodeid, row in item_index.items():
        path = str(row.get("path") or nodeid.split("::", 1)[0])
        by_path.setdefault(path, []).append(nodeid)

    matches: dict[str, list[str]] = {}
    for raw_path in changed_paths:
        path = raw_path.split("::", 1)[0]
        if not (path.startswith("system/server/tests/") and path.endswith(".py")):
            continue
        nodeids = sorted(dict.fromkeys(by_path.get(path, [])))
        if nodeids:
            matches[path] = nodeids
    return matches


def select(changed_paths: list[str]) -> dict[str, Any]:
    _enforce_legacy_guard()
    graph = _load_json(GRAPH_PATH) or {"nodes": [], "edges": [], "graph_digest": None}
    inventory = _load_json(INVENTORY_PATH) or {"test_items": [], "summary": {"inventory_digest": None}}
    inventory_freshness = _inventory_freshness(inventory)
    impact_map = _load_json(IMPACT_MAP_PATH) or {"selectors": []}
    registry = _load_json(REGISTRY_PATH) or {"fallback_test_bundles": {}}

    item_index: dict[str, dict] = {it["nodeid"]: it for it in inventory.get("test_items", [])}

    classifications: list[dict] = []
    if not changed_paths:
        classifications.append({"path": None, "artifact_kind": "unknown", "fallback_bundle": "unknown_doctrine_change"})
    for path in changed_paths:
        ak = _artifact_kind_for(path, graph)
        classifications.append({
            "path": path,
            "artifact_kind": ak or "unknown",
            "fallback_bundle": _classify_change(path),
        })

    matched_selectors: list[dict] = []
    selection_reason_global: list[str] = []
    selected_test_items: dict[str, list[str]] = {}
    selected_validators: list[dict] = []

    for sel in impact_map.get("selectors", []):
        sel_id = sel["selector_id"]
        sel_kinds = set(sel.get("artifact_kinds", []))
        sel_globs = sel.get("artifact_globs", [])
        matched_artifacts: list[str] = []
        reasons: list[str] = []
        for c in classifications:
            p = c.get("path")
            kind = c.get("artifact_kind")
            if p is None:
                continue
            kind_match = bool(kind and kind in sel_kinds)
            glob_match = any(_glob_match(p, g) for g in sel_globs)
            if kind_match or glob_match:
                matched_artifacts.append(p)
                if kind_match:
                    reasons.append(f"changed artifact_kind={kind} matched selector {sel_id}")
                if glob_match:
                    reasons.append(f"changed path {p} matched glob in selector {sel_id}")
        if not matched_artifacts:
            continue
        # Resolve test nodeid prefixes against current inventory.
        matched_test_items: list[str] = []
        unresolved_test_prefixes: list[str] = []
        for trow in sel.get("tests", []):
            prefix = trow["nodeid_prefix"]
            before_count = len(matched_test_items)
            for nodeid in item_index:
                if nodeid.startswith(prefix):
                    matched_test_items.append(nodeid)
                    reasons.append(f"selector {sel_id} -> {nodeid} ({trow.get('reason', '')})")
            if len(matched_test_items) == before_count:
                unresolved_test_prefixes.append(prefix)
        for vpath in sel.get("validators", []):
            selected_validators.append({"selector_id": sel_id, "command": vpath})
        matched_selectors.append({
            "selector_id": sel_id,
            "matched_artifacts": sorted(set(matched_artifacts)),
            "matched_test_items": sorted(set(matched_test_items)),
            "matched_validators": sel.get("validators", []),
            "unresolved_test_prefixes": sorted(set(unresolved_test_prefixes)),
            "selection_reason": list(dict.fromkeys(reasons)),
        })
        selected_test_items[sel_id] = matched_test_items
        selection_reason_global.extend(reasons)

    direct_test_file_matches = _changed_test_file_nodeids(changed_paths, item_index)
    if direct_test_file_matches:
        direct_nodeids: list[str] = []
        direct_reasons: list[str] = []
        for path, nodeids in sorted(direct_test_file_matches.items()):
            direct_nodeids.extend(nodeids)
            direct_reasons.append(
                f"changed test file {path} selected its own {len(nodeids)} inventory nodeid(s)"
            )
        direct_nodeids = sorted(dict.fromkeys(direct_nodeids))
        matched_selectors.append(
            {
                "selector_id": "direct_changed_test_file",
                "matched_artifacts": sorted(direct_test_file_matches),
                "matched_test_items": direct_nodeids,
                "matched_validators": [],
                "unresolved_test_prefixes": [],
                "selection_reason": direct_reasons,
            }
        )
        selected_test_items["direct_changed_test_file"] = direct_nodeids
        selection_reason_global.extend(direct_reasons)

    flat_tests: list[str] = []
    for ids in selected_test_items.values():
        for n in ids:
            if n not in flat_tests:
                flat_tests.append(n)

    fallback_used = False
    fallback_bundle_name: str | None = None
    fallback_tests: list[str] = []
    if not flat_tests:
        bundles = registry.get("fallback_test_bundles", {}) or {}
        # Pick the most relevant fallback bundle from classifications. If multiple
        # different classifications appear, pick the broadest one in this priority order.
        priority = [
            "lattice_substrate_change",
            "selector_code_change",
            "unknown_runtime_change",
            "unknown_standard_change",
            "unknown_server_or_ui_change",
            "unknown_doctrine_change",
        ]
        seen_bundles = [c["fallback_bundle"] for c in classifications]
        for name in priority:
            if name in seen_bundles and name in bundles:
                fallback_bundle_name = name
                fallback_tests = list(bundles[name])
                break
        if fallback_bundle_name is None and bundles:
            fallback_bundle_name = next(iter(bundles))
            fallback_tests = list(bundles[fallback_bundle_name])
        fallback_used = bool(fallback_tests)
        if fallback_used:
            selection_reason_global.append(
                f"no declared selector matched; fallback bundle '{fallback_bundle_name}' selected"
            )

    expanded = {
        "schema_version": 1,
        "generated_at": _now(),
        "changed_paths": changed_paths,
        "classifications": classifications,
        "matched_selectors": matched_selectors,
        "selected_test_items": flat_tests,
        "selected_validators": selected_validators,
        "fallback_used": fallback_used,
        "fallback_bundle": fallback_bundle_name,
        "fallback_tests": fallback_tests,
        "inventory_freshness": inventory_freshness,
        "selector_diagnostics": {
            "inventory_freshness_status": inventory_freshness["status"],
            "inventory_trusted_for_selector": inventory_freshness["trusted_for_selector"],
            "unresolved_test_prefixes": [
                {
                    "selector_id": s["selector_id"],
                    "nodeid_prefix": prefix,
                }
                for s in matched_selectors
                for prefix in s.get("unresolved_test_prefixes", [])
            ],
        },
        "selection_reason": list(dict.fromkeys(selection_reason_global)),
        "provenance": {
            "graph_digest": graph.get("graph_digest"),
            "inventory_digest": (inventory.get("summary") or {}).get("inventory_digest"),
            "inventory_freshness_status": inventory_freshness["status"],
            "impact_map_digest": _sha256_text(json.dumps(impact_map, sort_keys=True)),
            "selector_version": "v1",
        },
    }
    return expanded


def write_expanded(expanded: dict[str, Any]) -> Path:
    EXPANDED_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPANDED_PATH.write_text(
        json.dumps(expanded, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return EXPANDED_PATH


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", action="append", default=[], help="Repo-relative changed path (repeatable).")
    ap.add_argument("--receipt", type=str, default=None, help="Path to a mutation-receipt JSON with changed_artifacts.")
    ap.add_argument("--write", action="store_true", help="Persist expanded projection.")
    ap.add_argument("--json", action="store_true", help="Print JSON to stdout (default).")
    args = ap.parse_args()

    paths = _resolve_changed_paths(args)
    expanded = select(paths)
    if args.write:
        wrote = write_expanded(expanded)
        expanded = dict(expanded)
        expanded["wrote"] = str(wrote.relative_to(REPO_ROOT))
    print(json.dumps(expanded, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
