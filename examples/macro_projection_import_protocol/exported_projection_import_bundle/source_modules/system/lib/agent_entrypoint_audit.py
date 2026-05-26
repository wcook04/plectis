"""
- When-needed: Open when you need to audit agent entrypoints for anti-drift and comprehension, verifying coverage of kernel command, docs-route, paper-module slug, projection file, or literal tokens against authored axis registries.
- Escalates-to: system/lib/agent_bootstrap_projection.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_agent_entrypoint_audit.json"
AXIS_REGISTRY_PATH = REPO_ROOT / "codex" / "doctrine" / "agent_entrypoints" / "axis_registry.json"
ENTRYPOINT_REGISTRY_PATH = REPO_ROOT / "codex" / "doctrine" / "agent_entrypoints" / "entrypoint_registry.json"
AGENT_BOOTSTRAP_PATH = REPO_ROOT / "codex" / "doctrine" / "agent_bootstrap.json"
PAPER_MODULE_INDEX_PATH = REPO_ROOT / "codex" / "doctrine" / "paper_modules" / "_index.json"

HOLOGRAM_DIR = REPO_ROOT / "codex" / "hologram" / "agent_entrypoints"
AUDIT_PATH = HOLOGRAM_DIR / "audit.json"
SUMMARY_PATH = HOLOGRAM_DIR / "summary.json"
PER_ENTRYPOINT_PATH = HOLOGRAM_DIR / "per_entrypoint.json"

AUDIT_SCHEMA_VERSION = "agent_entrypoint_audit_v1"
SUMMARY_SCHEMA_VERSION = "agent_entrypoint_audit_summary_v1"
PER_ENTRYPOINT_SCHEMA_VERSION = "agent_entrypoint_audit_per_entrypoint_v1"

GENERATED_BLOCK_MARKERS = (
    ("<!-- BEGIN agent_bootstrap_live -->", "<!-- END agent_bootstrap_live -->"),
    ("<!-- BEGIN claude_adapter_live -->", "<!-- END claude_adapter_live -->"),
    ("<!-- BEGIN codex_adapter_live -->", "<!-- END codex_adapter_live -->"),
    ("<!-- BEGIN generated_routing -->", "<!-- END generated_routing -->"),
)

STRONG_RESOLUTION_METHODS = {"kernel_command", "docs_route", "paper_module_slug", "projection_file"}
AMBIENT_RESOLUTION_METHODS = {"any_of_tokens", "explicit_token"}

_SLUG_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class AxisResolution:
    method: str
    value: str | None
    values: tuple[str, ...]
    why: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "AxisResolution":
        method = str(row.get("method") or "").strip()
        value = row.get("value")
        values_raw = row.get("values") or []
        values = tuple(str(item).strip() for item in values_raw if str(item).strip())
        why = row.get("why")
        return cls(
            method=method,
            value=str(value).strip() if isinstance(value, str) else None,
            values=values,
            why=str(why).strip() if isinstance(why, str) else None,
        )

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"method": self.method}
        if self.value is not None:
            payload["value"] = self.value
        if self.values:
            payload["values"] = list(self.values)
        if self.why is not None:
            payload["why"] = self.why
        return payload


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _relpath(path: Path, *, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _normalize_slug(raw: str) -> str:
    lowered = str(raw or "").strip().lower()
    return _SLUG_NORMALIZE_RE.sub("_", lowered).strip("_")


def _paper_module_slugs(repo_root: Path) -> set[str]:
    index_path = repo_root / PAPER_MODULE_INDEX_PATH.relative_to(REPO_ROOT)
    payload = _safe_read_json(index_path)
    if not isinstance(payload, Mapping):
        return set()
    manifest = payload.get("source_manifest") if isinstance(payload.get("source_manifest"), Mapping) else {}
    modules = manifest.get("modules") if isinstance(manifest.get("modules"), list) else []
    return {
        str(item.get("slug") or "").strip()
        for item in modules
        if isinstance(item, Mapping) and str(item.get("slug") or "").strip()
    }


def load_axis_registry(path: Path | None = None) -> dict[str, Any]:
    registry = _safe_read_json(path or AXIS_REGISTRY_PATH)
    return dict(registry) if isinstance(registry, Mapping) else {"axes": []}


def load_entrypoint_registry(path: Path | None = None) -> dict[str, Any]:
    registry = _safe_read_json(path or ENTRYPOINT_REGISTRY_PATH)
    return dict(registry) if isinstance(registry, Mapping) else {"entrypoints": [], "dotfile_tree_inventory": {}}


def load_bootstrap_actor_context(path: Path | None = None) -> list[dict[str, Any]]:
    payload = _safe_read_json(path or AGENT_BOOTSTRAP_PATH)
    if not isinstance(payload, Mapping):
        return []
    surfaces = payload.get("actor_context_surfaces")
    return [dict(item) for item in (surfaces or []) if isinstance(item, Mapping)]


def load_bootstrap_config(path: Path | None = None) -> dict[str, Any]:
    payload = _safe_read_json(path or AGENT_BOOTSTRAP_PATH)
    return dict(payload) if isinstance(payload, Mapping) else {}


def _dedupe_strings(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _entrypoint_overlays_by_id(registry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    overlays: dict[str, dict[str, Any]] = {}
    for raw in registry.get("entrypoints") or []:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        entry_id = str(row.get("id") or "").strip()
        actor_id = str(row.get("actor_id") or "").strip()
        if entry_id:
            overlays[entry_id] = row
        if actor_id and actor_id not in overlays:
            overlays[actor_id] = row
    return overlays


def _apply_entrypoint_overlay(base: dict[str, Any], overlay: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(overlay, Mapping):
        return base
    for key in ("label", "companion_paths", "dotfile_tree", "line_budget", "required_axes", "notes"):
        if key in overlay:
            base[key] = overlay[key]
    return base


def _derive_entrypoints_from_bootstrap(
    registry: Mapping[str, Any],
    bootstrap_config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Derive entrypoint identity/read-order from agent_bootstrap.json, then apply audit-only overlays."""
    markdown_targets = bootstrap_config.get("markdown_targets") if isinstance(bootstrap_config.get("markdown_targets"), Mapping) else {}
    adapter_actor_map = bootstrap_config.get("adapter_actor_map") if isinstance(bootstrap_config.get("adapter_actor_map"), Mapping) else {}
    actor_rows = [
        dict(item)
        for item in (bootstrap_config.get("actor_context_surfaces") or [])
        if isinstance(item, Mapping)
    ]
    actors_by_id = {str(row.get("actor_id") or "").strip(): row for row in actor_rows if str(row.get("actor_id") or "").strip()}
    overlays = _entrypoint_overlays_by_id(registry)

    # Fixture/back-compat path: older tests and callers may provide only the audit registry.
    if not markdown_targets and not adapter_actor_map:
        return [dict(item) for item in (registry.get("entrypoints") or []) if isinstance(item, Mapping)]

    derived: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    agents_md = str(markdown_targets.get("agents_md") or "").strip()
    if agents_md:
        overlay = overlays.get("shared")
        shared = {
            "id": "shared",
            "role": "shared_hub",
            "actor_id": None,
            "label": "Shared agent hub (AGENTS.md)",
            "primary_paths": [agents_md],
            "read_scope_paths": [agents_md],
            "companion_paths": [],
            "dotfile_tree": None,
            "line_budget": None,
            "required_axes": [],
            "notes": "Vendor-neutral hub derived from agent_bootstrap.json::markdown_targets.agents_md.",
        }
        derived.append(_apply_entrypoint_overlay(shared, overlay))
        seen_ids.add("shared")

    for adapter_key, actor_raw in adapter_actor_map.items():
        actor_id = str(actor_raw or "").strip()
        md_rel = str(markdown_targets.get(adapter_key) or "").strip()
        if not actor_id or not md_rel:
            continue
        actor_row = actors_by_id.get(actor_id, {})
        overlay = overlays.get(actor_id) or overlays.get(str(adapter_key))
        read_order = _dedupe_strings([md_rel, *(actor_row.get("read_order") or [])])
        adapter = {
            "id": actor_id,
            "role": "adapter",
            "actor_id": actor_id,
            "label": str(actor_row.get("label") or actor_id),
            "primary_paths": [md_rel],
            "read_scope_paths": read_order or [md_rel],
            "companion_paths": [],
            "dotfile_tree": None,
            "line_budget": None,
            "required_axes": [],
            "notes": (
                f"Adapter identity/read scope derived from agent_bootstrap.json::{adapter_key} "
                "and actor_context_surfaces; audit registry only overlays obligations."
            ),
        }
        derived.append(_apply_entrypoint_overlay(adapter, overlay))
        seen_ids.add(actor_id)

    # Preserve any explicitly declared non-bootstrap entrypoint rows as overlays/fallbacks.
    for raw in registry.get("entrypoints") or []:
        if not isinstance(raw, Mapping):
            continue
        entry_id = str(raw.get("id") or "").strip()
        if not entry_id or entry_id in seen_ids:
            continue
        if not raw.get("primary_paths"):
            continue
        row = dict(raw)
        row.setdefault("read_scope_paths", list(row.get("primary_paths") or []))
        derived.append(row)
        seen_ids.add(entry_id)
    return derived


def _read_entrypoint_content(
    entrypoint: Mapping[str, Any], *, repo_root: Path
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Return (combined_lowercase_haystack, per_path_records, missing_paths)."""
    primary = [str(item) for item in (entrypoint.get("primary_paths") or [])]
    read_scope = [str(item) for item in (entrypoint.get("read_scope_paths") or [])] or primary
    companion = [str(item) for item in (entrypoint.get("companion_paths") or [])]
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    parts: list[str] = []

    path_rows: list[tuple[str, str]] = []
    for raw in primary:
        path_rows.append(("primary", raw))
    for raw in read_scope:
        if raw not in primary:
            path_rows.append(("read_scope", raw))
    for raw in companion:
        if raw not in primary and raw not in read_scope:
            path_rows.append(("companion", raw))

    for role, raw in path_rows:
        path = repo_root / raw
        text = _read_text_safe(path)
        if not text:
            if not path.exists():
                missing.append(raw)
            records.append({"path": raw, "role": role, "present": path.exists(), "line_count": 0, "char_count": 0})
            continue
        line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
        records.append({"path": raw, "role": role, "present": True, "line_count": line_count, "char_count": len(text)})
        parts.append(text)
    haystack = "\n".join(parts).lower()
    return haystack, records, missing


def _axis_token_hits(haystack: str, value: str) -> bool:
    token = str(value or "").strip().lower()
    return bool(token) and token in haystack


def _axis_kernel_command_hits(haystack: str, flag_value: str) -> bool:
    """A kernel command hit matches either the full `kernel.py --flag` citation or the bare `--flag` token."""
    value = str(flag_value or "").strip().lower()
    if not value:
        return False
    if value in haystack:
        return True
    if value.startswith("kernel.py "):
        flag = value.split(" ", 1)[1].strip()
        if flag and flag in haystack:
            return True
    if value.startswith("--"):
        return value in haystack
    return False


def _axis_docs_route_hits(haystack: str, alias: str) -> bool:
    normalized = str(alias or "").strip().lower()
    if not normalized:
        return False
    if f"--docs-route \"{normalized}\"" in haystack:
        return True
    if f"--docs-route {normalized}" in haystack:
        return True
    if f"docs-route \"{normalized}\"" in haystack:
        return True
    return False


def _axis_paper_module_hits(haystack: str, slug: str, *, known_slugs: set[str]) -> tuple[bool, str | None]:
    normalized = _normalize_slug(slug)
    if not normalized:
        return False, "empty paper-module slug"
    if normalized not in known_slugs:
        return False, f"unknown paper-module slug (not in _index.json): {normalized}"
    if normalized in haystack:
        return True, None
    file_token = f"paper_modules/{normalized}.md".lower()
    if file_token in haystack:
        return True, None
    return False, None


def _axis_projection_file_hits(haystack: str, path: str) -> bool:
    value = str(path or "").strip().lower()
    return bool(value) and value in haystack


def _probe_axis(
    axis: Mapping[str, Any],
    haystack: str,
    *,
    known_paper_module_slugs: set[str],
) -> dict[str, Any]:
    resolutions = [AxisResolution.from_row(row) for row in (axis.get("resolution_methods") or []) if isinstance(row, Mapping)]
    results: list[dict[str, Any]] = []
    notes: list[str] = []
    for resolution in resolutions:
        method = resolution.method
        outcome = {"method": method, "matched": False, "matched_on": None, "raw": resolution.as_dict()}
        if method == "kernel_command" and resolution.value:
            if _axis_kernel_command_hits(haystack, resolution.value):
                outcome["matched"] = True
                outcome["matched_on"] = resolution.value
        elif method == "docs_route" and resolution.value:
            if _axis_docs_route_hits(haystack, resolution.value):
                outcome["matched"] = True
                outcome["matched_on"] = resolution.value
        elif method == "paper_module_slug" and resolution.value:
            hit, note = _axis_paper_module_hits(haystack, resolution.value, known_slugs=known_paper_module_slugs)
            if hit:
                outcome["matched"] = True
                outcome["matched_on"] = _normalize_slug(resolution.value)
            elif note:
                notes.append(note)
        elif method == "projection_file" and resolution.value:
            if _axis_projection_file_hits(haystack, resolution.value):
                outcome["matched"] = True
                outcome["matched_on"] = resolution.value
        elif method == "explicit_token" and resolution.value:
            if _axis_token_hits(haystack, resolution.value):
                outcome["matched"] = True
                outcome["matched_on"] = resolution.value
        elif method == "any_of_tokens" and resolution.values:
            for token in resolution.values:
                if _axis_token_hits(haystack, token):
                    outcome["matched"] = True
                    outcome["matched_on"] = token
                    break
        else:
            notes.append(f"resolution method '{method}' has no usable value payload")
        results.append(outcome)
    covered = any(item["matched"] for item in results)
    matched_methods = [item["method"] for item in results if item["matched"]]
    return {
        "axis_id": str(axis.get("id") or ""),
        "covered": covered,
        "probe_results": results,
        "matched_methods": matched_methods,
        "notes": notes,
    }


def _extract_marked_region(content: str, begin: str, end: str) -> str | None:
    begin_idx = content.find(begin)
    end_idx = content.find(end)
    if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
        return None
    return content[begin_idx + len(begin): end_idx]


def _normalize_generated_region(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in str(text or "").strip().splitlines())
    try:
        from tools.meta.factory.check_agent_bootstrap_projection import (
            _normalize_volatile_markdown,
        )
    except Exception:
        return normalized
    return _normalize_volatile_markdown(normalized)


def _expected_generated_regions(repo_root: Path) -> dict[tuple[str, str, str], str]:
    """Render the current bootstrap projection in memory for generated-block comparison."""
    try:
        from system.lib.agent_bootstrap_projection import (
            build_bootstrap_projection_context,
            load_agent_bootstrap_config,
            load_canonical_option_surface_routes,
            render_adapter_markdown,
            render_live_markdown,
        )

        cfg = load_agent_bootstrap_config(repo_root)
        context = build_bootstrap_projection_context(
            repo_root,
            config=cfg,
            refresh_orchestration=False,
        )
        markers = cfg.get("markers") if isinstance(cfg.get("markers"), Mapping) else {}
        markdown_targets = cfg.get("markdown_targets") if isinstance(cfg.get("markdown_targets"), Mapping) else {}
        adapter_markers = markers.get("adapters") if isinstance(markers.get("adapters"), Mapping) else {}
        adapter_actor_map = cfg.get("adapter_actor_map") if isinstance(cfg.get("adapter_actor_map"), Mapping) else {}
        actor_lookup = {
            str(row.get("actor_id") or ""): row
            for row in (context.get("actor_context_surfaces") or [])
            if isinstance(row, Mapping) and str(row.get("actor_id") or "")
        }

        expected: dict[tuple[str, str, str], str] = {}
        agents_rel = str(markdown_targets.get("agents_md") or "AGENTS.md")
        begin = str(markers.get("begin") or GENERATED_BLOCK_MARKERS[0][0])
        end = str(markers.get("end") or GENERATED_BLOCK_MARKERS[0][1])
        expected[(agents_rel, begin, end)] = render_live_markdown(
            context["bindings"],
            per_agent_rows=context["per_agent_rows"],
            system_facts_at_a_glance=context.get("system_facts_at_a_glance") or None,
            minimum_read_sets=context["minimum_read_sets"] or None,
            bootstrap_sequence=context["bootstrap_sequence"] or None,
            situation_routes=context["situation_routes"] or None,
            actor_context_surfaces=context["actor_context_surfaces"] or None,
            runtime_control_plane=context["runtime_control_plane"] or None,
            compact_command_surface=context["compact_command_surface"] or None,
            type_a_convergence_contract=context["type_a_convergence_contract"] or None,
        )

        for adapter_key, marker_pair in adapter_markers.items():
            if not isinstance(marker_pair, Mapping):
                continue
            md_rel = str(markdown_targets.get(adapter_key) or "").strip()
            a_begin = str(marker_pair.get("begin") or "").strip()
            a_end = str(marker_pair.get("end") or "").strip()
            if not md_rel or not a_begin or not a_end:
                continue
            actor_id = str(adapter_actor_map.get(adapter_key) or "").strip()
            adapter_role = "claude_adapter" if adapter_key == "claude_md" else (
                "codex_adapter" if adapter_key == "codex_md" else f"{adapter_key}_adapter"
            )
            expected[(md_rel, a_begin, a_end)] = render_adapter_markdown(
                context["bindings"],
                adapter_role=adapter_role,
                actor_id=actor_id,
                actor_row=actor_lookup.get(actor_id),
                system_facts_at_a_glance=context.get("system_facts_at_a_glance") or None,
                bootstrap_sequence=context["bootstrap_sequence"] or None,
                situation_routes=context["situation_routes"] or None,
                type_a_convergence_contract=context["type_a_convergence_contract"] or None,
                canonical_option_surface_routes=load_canonical_option_surface_routes(repo_root),
                hub_path=agents_rel,
            )
        return expected
    except Exception:
        return {}


def _detect_generated_block_drift(
    entrypoint: Mapping[str, Any],
    *,
    repo_root: Path,
    expected_regions: Mapping[tuple[str, str, str], str] | None = None,
) -> list[dict[str, Any]]:
    """Compare managed regions against the current bootstrap renderer when possible."""
    findings: list[dict[str, Any]] = []
    for raw in entrypoint.get("primary_paths") or []:
        path = repo_root / str(raw)
        text = _read_text_safe(path)
        if not text:
            continue
        for begin, end in GENERATED_BLOCK_MARKERS:
            begin_idx = text.find(begin)
            end_idx = text.find(end)
            if begin_idx == -1 and end_idx == -1:
                continue
            if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
                findings.append(
                    {
                        "severity": "error",
                        "rule": "generated_block_drift",
                        "entrypoint_id": str(entrypoint.get("id") or ""),
                        "path": str(raw),
                        "message": (
                            f"Generated region markers for {begin!r}..{end!r} are unbalanced in {raw}; "
                            "the builder output is either missing, reordered, or hand-edited."
                        ),
                    }
                )
                continue
            body = text[begin_idx + len(begin): end_idx].strip()
            if not body:
                findings.append(
                    {
                        "severity": "warning",
                        "rule": "stale_projection",
                        "entrypoint_id": str(entrypoint.get("id") or ""),
                        "path": str(raw),
                        "message": (
                            f"Generated region {begin!r}..{end!r} in {raw} is empty; "
                            "run the agent_bootstrap projection builder to refresh."
                        ),
                    }
                )
                continue
            expected = (expected_regions or {}).get((str(raw), begin, end))
            if expected is not None and _normalize_generated_region(body) != _normalize_generated_region(expected):
                findings.append(
                    {
                        "severity": "error",
                        "rule": "generated_block_drift",
                        "entrypoint_id": str(entrypoint.get("id") or ""),
                        "path": str(raw),
                        "message": (
                            f"Generated region {begin!r}..{end!r} in {raw} differs from the current "
                            "agent_bootstrap_projection renderer; run the projection builder instead of "
                            "hand-editing the managed region."
                        ),
                    }
                )
    return findings


def _build_entry_surface_budget_ledger(*, repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Derive a budget ledger over entry surfaces (AGENTS.md /
      AGENTS.override.md / CLAUDE.md / CODEX.md) so reserve / route-density /
      principle-anchor metrics become operator-visible alongside the hard
      byte-budget check. Per pri_131 (Entry-Surface Byte Budgets Protect
      First-Read Fidelity) and pri_130 (Architectural Decisions Require
      Principle-Anchored Justification).
    - Mechanism: Read compression_budgets from std_agent_entry_surface.json,
      stat each entry surface on disk, compute reserve_bytes = hard_cap -
      bytes, derive reserve_floor as max(5% of hard_cap, observed concurrent
      growth burst), classify reserve_status as `over_budget` / `critical` /
      `comfortable`, record whether the budget row carries the structured
      ADR fields per pri_130's architectural_constraint_rationale_contract.
    - Guarantee: Returns an empty dict if std_agent_entry_surface.json is
      missing or compression_budgets is absent; otherwise returns a structured
      ledger with `rows` and `reserve_floor_basis` keys.
    - Fails: None.
    - When-needed: Open when extending the ledger to additional surfaces, or
      when computing the reserve_floor from concurrent-growth telemetry rather
      than the 5% heuristic.
    """
    std_path = repo_root / "codex" / "standards" / "std_agent_entry_surface.json"
    if not std_path.exists():
        return {}
    try:
        std_data = json.loads(std_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    budgets = std_data.get("compression_budgets") or {}
    if not isinstance(budgets, Mapping):
        return {}
    rows: list[dict[str, Any]] = []
    for surface_id, row in budgets.items():
        if surface_id == "comment" or not isinstance(row, Mapping):
            continue
        rel_path = str(row.get("path") or "").strip()
        hard_cap = row.get("budget_bytes")
        if not rel_path or not isinstance(hard_cap, int):
            continue
        target = repo_root / rel_path
        if not target.exists():
            rows.append({
                "surface_id": str(surface_id),
                "path": rel_path,
                "status": "missing",
                "hard_cap": hard_cap,
            })
            continue
        size_bytes = target.stat().st_size
        reserve_bytes = max(0, hard_cap - size_bytes)
        reserve_floor = max(int(hard_cap * 0.05), 0)
        if size_bytes > hard_cap:
            reserve_status = "over_budget"
        elif reserve_bytes < reserve_floor:
            reserve_status = "critical"
        else:
            reserve_status = "comfortable"
        justifying_principle = str(row.get("justifying_principle") or "").strip() or None
        has_decision_record = all(
            row.get(field)
            for field in (
                "justifying_principle",
                "failure_prevented",
                "change_protocol",
                "review_command",
                "repair_path",
            )
        )
        rows.append({
            "surface_id": str(surface_id),
            "path": rel_path,
            "bytes": size_bytes,
            "hard_cap": hard_cap,
            "reserve_bytes": reserve_bytes,
            "reserve_floor": reserve_floor,
            "reserve_pct": round((reserve_bytes / hard_cap) * 100, 1) if hard_cap else 0.0,
            "reserve_status": reserve_status,
            "justifying_principle": justifying_principle,
            "has_decision_record": has_decision_record,
        })
    return {
        "rows": rows,
        "reserve_floor_basis": "max(5% of hard_cap, observed concurrent-growth burst); initial heuristic uses 5% only and should be refined when concurrent-growth telemetry is available. Reference: this thread observed ~3680-byte AGENTS.md growth from a single concurrent doc commit, so reserve_floor for AGENTS.md should eventually move from 3276 (5%) toward ~4096 once telemetry is wired.",
        "principle_anchor": "pri_131",
        "schema_version": "entry_surface_budget_ledger_v1",
    }


def _check_entry_surface_reserve(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for row in (ledger.get("rows") or []):
        if not isinstance(row, Mapping):
            continue
        if row.get("reserve_status") != "critical":
            continue
        bytes_ = int(row.get("bytes") or 0)
        hard_cap = int(row.get("hard_cap") or 0)
        reserve_bytes = int(row.get("reserve_bytes") or 0)
        reserve_floor = int(row.get("reserve_floor") or 0)
        findings.append({
            "severity": "warning",
            "rule": "entry_surface_reserve_critical",
            "path": str(row.get("path") or ""),
            "surface_id": str(row.get("surface_id") or ""),
            "bytes": bytes_,
            "hard_cap": hard_cap,
            "reserve_bytes": reserve_bytes,
            "reserve_floor": reserve_floor,
            "message": (
                f"Entry surface {row.get('path')!r} is within the hard cap "
                f"({bytes_}/{hard_cap}) but reserve {reserve_bytes} bytes is below the "
                f"floor {reserve_floor} ({row.get('reserve_pct', 0)}% headroom). "
                f"Concurrent-agent commits can blow the cap with the next addition; "
                f"apply pri_121 compression to routed substrate before adding more "
                f"entry-surface prose. (Per pri_131 change_protocol: do NOT raise "
                f"budget_bytes as the first move.)"
            ),
        })
    return findings


def _check_architectural_constraint_principle_anchor(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for row in (ledger.get("rows") or []):
        if not isinstance(row, Mapping):
            continue
        if row.get("status") == "missing":
            continue
        if row.get("has_decision_record"):
            continue
        findings.append({
            "severity": "warning",
            "rule": "architectural_constraint_lacks_principle_anchor",
            "path": str(row.get("path") or ""),
            "surface_id": str(row.get("surface_id") or ""),
            "justifying_principle": row.get("justifying_principle"),
            "message": (
                f"compression_budgets row for {row.get('surface_id')!r} ({row.get('path')}) "
                f"lacks the full structured decision-record shape pri_130's "
                f"architectural_constraint_rationale_contract requires "
                f"(justifying_principle / failure_prevented / change_protocol / "
                f"review_command / repair_path). See compression_budgets.agents_md "
                f"for the reference template; pri_131 is the canonical principle for "
                f"entry-surface byte budgets. Migration is non-breaking; existing "
                f"prose `rationale` stays valid until each row is migrated."
            ),
        })
    return findings


def _classify_topology_ref_scope(ref_kind: str, ref: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Classify a topology doctrine ref as `shared` (all actors should
      reach it), `actor_local` (only the intended actor should reach it; symmetric
      missing-from-other-actor is NOT a defect), or `unknown` (needs operator/owner
      metadata to decide). Per pri_130 + the operator's same-turn triage of the 9
      measured asymmetric refs.
    - Mechanism: Two layers. Explicit triage table from the operator's prior turn
      classifies known-by-name refs first. Heuristic fallback uses path naming
      (`claude_*` / Claude-prefixed filenames → claude actor_local; `codex_*`
      filenames → codex actor_local; `voice_archaeology*` substrate → shared).
      Default is `unknown` so the audit keeps emitting warnings for refs the
      classifier hasn't been taught yet, rather than silently passing them.
    - Guarantee: Always returns a dict with the three required keys; never raises.
    - Fails: None.
    """
    ref_lower = (ref or "").lower()
    stem = ref_lower.rsplit("/", 1)[-1]
    # Operator triage from prior turn: explicit initial classifications.
    EXPLICIT_CLAUDE_LOCAL = frozenset({
        "codex/doctrine/paper_modules/claude_agents_materialization.md",
        "codex/doctrine/paper_modules/station_render_engine.md",
        "codex/doctrine/skills/frontend/frontend_visual_verification.md",
    })
    EXPLICIT_SHARED = frozenset({
        "codex/doctrine/paper_modules/voice_archaeology.md",
        "codex/doctrine/skills/raw_seed/archaeological_voice_mining.md",
        "codex/doctrine/skills/doctrine/concept_mechanism_curation.md",
        "codex/doctrine/skills/doctrine/principles_curation.md",
        "codex/doctrine/skills/doctrine/meta_mission_authoring.md",
    })
    if ref in EXPLICIT_CLAUDE_LOCAL:
        return {
            "scope_class": "actor_local",
            "actor_scope": "claude",
            "scope_reason": "Operator-triaged 2026-04-28: Claude-specific doctrine (subagents / UI render-engine / frontend visual verification).",
        }
    if ref in EXPLICIT_SHARED:
        return {
            "scope_class": "shared",
            "actor_scope": "all",
            "scope_reason": "Operator-triaged 2026-04-28: shared substrate (voice-archaeology corpus mining / doctrine curation skills) applies to any agent.",
        }
    # Standard for voice_archaeology — operator confirmed shared.
    if ref_kind == "standard" and "voice_archaeology" in ref_lower:
        return {
            "scope_class": "shared",
            "actor_scope": "all",
            "scope_reason": "Voice-archaeology substrate contract; applies to any agent doing pre-system voice mining.",
        }
    # Heuristic fallback by filename naming.
    if stem.startswith("claude_") or stem.startswith("claude.") or stem == "claude":
        return {
            "scope_class": "actor_local",
            "actor_scope": "claude",
            "scope_reason": f"Filename {stem!r} starts with 'claude_'; heuristic classifies as Claude-actor-local doctrine.",
        }
    if stem.startswith("codex_") or stem.startswith("codex.") or stem == "codex":
        return {
            "scope_class": "actor_local",
            "actor_scope": "codex",
            "scope_reason": f"Filename {stem!r} starts with 'codex_'; heuristic classifies as Codex-actor-local doctrine.",
        }
    # meta_mission_authoring is explicitly unknown per operator triage.
    return {
        "scope_class": "unknown",
        "actor_scope": None,
        "scope_reason": "No explicit triage entry and no naming heuristic matches; defaults to unknown so audit keeps emitting until operator classifies.",
    }


_TOPOLOGY_REGION_RE = re.compile(r"<!--\s*BEGIN\s+(\S+?)\s*-->(.*?)<!--\s*END\s+\1\s*-->", re.DOTALL)
_TOPOLOGY_ROUTE_RE = re.compile(r"`((?:\./repo-python|python3?)\s+(?:kernel\.py|tools/meta/[^\s`]+)[^`]*)`")
_TOPOLOGY_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_TOPOLOGY_PRI_RE = re.compile(r"\bpri_\d{3,4}\b")
_TOPOLOGY_STD_RE = re.compile(r"\bstd_[a-z][a-z0-9_]+\b")
_TOPOLOGY_SKILL_PATH_RE = re.compile(r"`?(codex/doctrine/skills/[a-z0-9_/.-]+\.md)`?")
_TOPOLOGY_PAPER_PATH_RE = re.compile(r"`?(codex/doctrine/paper_modules/[a-z0-9_.-]+\.md)`?")
_TOPOLOGY_STANDARD_PATH_RE = re.compile(r"`?(codex/standards/[a-z0-9_/.-]+\.json)`?")
_TOPOLOGY_SOURCE_PATH_RE = re.compile(
    r"`?("
    r"(?:system/lib|tools/meta|docs|state|codex/doctrine|codex/hologram)/"
    r"[a-z0-9_/.-]+\.(?:py|md|json|jsonl)"
    r")`?"
)
_TOPOLOGY_FRESHNESS_RE = re.compile(
    r"(check_[a-z0-9_]+\.py|--check\b|freshness\b|refresh(?: command)?\b)",
    re.IGNORECASE,
)
_TOPOLOGY_SURFACES = (
    ("agents_override_md", "AGENTS.override.md", "codex_compact_discovery_seed", "codex"),
    ("agents_md", "AGENTS.md", "shared_hub", "shared"),
    ("claude_md", "CLAUDE.md", "claude_adapter", "claude"),
    ("codex_md", "CODEX.md", "codex_adapter", "codex"),
)


def _build_entry_surface_topology(*, repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Derive a navigation topology graph over the four entry
      surfaces (AGENTS.override.md / AGENTS.md / CLAUDE.md / CODEX.md) so the
      shape that operator boot files actually carry — marker regions, route
      commands, markdown links, principle/standard/skill refs — becomes
      auditable rather than implicit. First half of the operator's
      'navigation derivable from AGENTS.md / CLAUDE.md / CODEX.md structure
      itself' framework; the second half (shared_doctrine_adapter_asymmetry)
      depends on this topology being present.
    - Mechanism: For each surface, read its bytes, extract marker regions
      (BEGIN/END pairs), route commands (`./repo-python kernel.py ...` /
      `python3 kernel.py ...`), markdown links, pri_/std_ refs, skill and
      paper-module paths. Compute per-surface coverage metrics
      (route_count / owner_coverage / freshness_coverage). Build the graph
      with `surfaces` (nodes) and `edges` (contains / routes_to / cites).
    - Guarantee: Returns a dict with `schema_version: entry_surface_topology_v1`
      and a list of surfaces; missing files become an empty-node row rather
      than a hard failure.
    - Fails: None (defensive parsing).
    """
    surfaces: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for surface_id, rel_path, role, actor in _TOPOLOGY_SURFACES:
        target = repo_root / rel_path
        if not target.exists():
            surfaces.append({
                "surface_id": surface_id,
                "path": rel_path,
                "role": role,
                "actor": actor,
                "status": "missing",
            })
            continue
        text = target.read_text(encoding="utf-8")
        size_bytes = len(text.encode("utf-8"))
        regions: list[dict[str, Any]] = []
        for m in _TOPOLOGY_REGION_RE.finditer(text):
            name = m.group(1)
            body = m.group(2)
            regions.append({
                "region_id": name,
                "bytes": len(body.encode("utf-8")),
                "byte_start": m.start(),
                "byte_end": m.end(),
            })
            edges.append({
                "source": rel_path,
                "target": name,
                "edge_type": "contains",
                "evidence": "marker_region",
            })
        route_commands = sorted(set(_TOPOLOGY_ROUTE_RE.findall(text)))
        link_pairs = [(label, href) for label, href in _TOPOLOGY_LINK_RE.findall(text)
                      if not href.startswith(("http://", "https://", "mailto:"))]
        principle_refs = sorted(set(_TOPOLOGY_PRI_RE.findall(text)))
        standard_refs = sorted(set(_TOPOLOGY_STD_RE.findall(text)))
        skill_refs = sorted(set(_TOPOLOGY_SKILL_PATH_RE.findall(text)))
        paper_refs = sorted(set(_TOPOLOGY_PAPER_PATH_RE.findall(text)))
        for label, href in link_pairs:
            edges.append({
                "source": rel_path,
                "target": href,
                "edge_type": "routes_to",
                "evidence": "markdown_link",
                "label": label,
            })
        for pri in principle_refs:
            edges.append({"source": rel_path, "target": pri, "edge_type": "cites", "evidence": "principle_ref"})
        for std in standard_refs:
            edges.append({"source": rel_path, "target": std, "edge_type": "cites", "evidence": "standard_ref"})
        # Route-pointer quality: a route_command is "owner-supported" if any
        # markdown link, standard/skill/paper path, or generated/source sidecar
        # appears in the previous two lines, same line, or following two lines;
        # "freshness-supported" if a check/refresh command, `--check`, or the
        # literal token `freshness` appears similarly. The symmetric window
        # matches Rosetta rows that put owner/freshness before the command.
        lines = text.splitlines()
        owner_supported = 0
        freshness_supported = 0
        if route_commands:
            line_offsets = []
            for idx, line in enumerate(lines):
                if any(rc in line for rc in route_commands):
                    line_offsets.append(idx)
            for idx in line_offsets:
                window = "\n".join(lines[max(0, idx - 2): min(idx + 3, len(lines))])
                if (
                    _TOPOLOGY_LINK_RE.search(window)
                    or _TOPOLOGY_SKILL_PATH_RE.search(window)
                    or _TOPOLOGY_PAPER_PATH_RE.search(window)
                    or _TOPOLOGY_STANDARD_PATH_RE.search(window)
                    or _TOPOLOGY_SOURCE_PATH_RE.search(window)
                    or _TOPOLOGY_STD_RE.search(window)
                ):
                    owner_supported += 1
                if _TOPOLOGY_FRESHNESS_RE.search(window):
                    freshness_supported += 1
            owner_coverage = round(owner_supported / max(1, len(line_offsets)), 3)
            freshness_coverage = round(freshness_supported / max(1, len(line_offsets)), 3)
        else:
            owner_coverage = 1.0
            freshness_coverage = 1.0
        surfaces.append({
            "surface_id": surface_id,
            "path": rel_path,
            "role": role,
            "actor": actor,
            "bytes": size_bytes,
            "region_count": len(regions),
            "regions": regions,
            "route_command_count": len(route_commands),
            "route_commands": route_commands[:30],
            "internal_link_count": len(link_pairs),
            "principle_ref_count": len(principle_refs),
            "principle_refs": principle_refs,
            "standard_ref_count": len(standard_refs),
            "standard_refs": standard_refs,
            "skill_ref_count": len(skill_refs),
            "skill_refs": skill_refs,
            "paper_module_ref_count": len(paper_refs),
            "paper_module_refs": paper_refs,
            "owner_coverage": owner_coverage,
            "freshness_coverage": freshness_coverage,
        })
    # adapter_reachability: detect adapter routes to the shared hub and
    # classify each doctrine ref's reachability per actor.
    shared_hub_path = "AGENTS.md"
    SHARED_HUB_TOKENS = ("AGENTS.md", "agents.md")
    adapter_routes_to_hub: dict[str, bool] = {}
    surface_index = {s["surface_id"]: s for s in surfaces if isinstance(s.get("surface_id"), str)}
    for surface_id, rel_path, role, actor in _TOPOLOGY_SURFACES:
        if rel_path == shared_hub_path:
            continue
        target = repo_root / rel_path
        if not target.exists():
            adapter_routes_to_hub[surface_id] = False
            continue
        body = target.read_text(encoding="utf-8")
        adapter_routes_to_hub[surface_id] = any(tok in body for tok in SHARED_HUB_TOKENS)
    # Build the per-actor reachability map keyed by ref kind+id.
    actors = ("codex", "claude")
    actor_to_surface = {"codex": ("agents_override_md", "codex_md"), "claude": ("claude_md",)}
    surfaces_by_actor: dict[str, list[dict[str, Any]]] = {a: [] for a in actors}
    shared_surface = surface_index.get("agents_md")
    for actor, surface_ids in actor_to_surface.items():
        for sid in surface_ids:
            s = surface_index.get(sid)
            if s and s.get("status") != "missing":
                surfaces_by_actor[actor].append(s)
    REF_KINDS = (
        ("principle", "principle_refs"),
        ("standard", "standard_refs"),
        ("skill", "skill_refs"),
        ("paper_module", "paper_module_refs"),
    )
    seen_refs: dict[tuple[str, str], dict[str, Any]] = {}
    def _record_ref(ref_kind: str, ref_id: str, surface_id: str) -> None:
        key = (ref_kind, ref_id)
        row = seen_refs.setdefault(key, {
            "ref_kind": ref_kind,
            "ref": ref_id,
            "direct_surfaces": [],
            "reachable_actors": {},
        })
        if surface_id not in row["direct_surfaces"]:
            row["direct_surfaces"].append(surface_id)
    for s in surfaces:
        if s.get("status") == "missing":
            continue
        sid = s.get("surface_id")
        for ref_kind, field in REF_KINDS:
            for ref_id in (s.get(field) or []):
                _record_ref(ref_kind, ref_id, sid)
    # Walk one hop deeper into shared owners cited by AGENTS.md (paper modules
    # and skills). A ref appearing in any such owner is reachable by any actor
    # whose adapter routes to AGENTS.md, classified as
    # `transitive_via_routed_owner`. This honors pri_130's "shared owner"
    # semantic: AGENTS.md need not duplicate every shared ref inline; routing
    # to a paper module / skill that contains the ref is sufficient.
    routed_owners_from_hub: set[str] = set()
    if shared_surface and shared_surface.get("status") != "missing":
        for href in (shared_surface.get("paper_module_refs") or []):
            routed_owners_from_hub.add(href)
        for href in (shared_surface.get("skill_refs") or []):
            routed_owners_from_hub.add(href)
    refs_in_routed_owners: set[tuple[str, str]] = set()
    for owner_rel in routed_owners_from_hub:
        owner_path = repo_root / owner_rel
        if not owner_path.exists():
            continue
        try:
            owner_text = owner_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for pri in _TOPOLOGY_PRI_RE.findall(owner_text):
            refs_in_routed_owners.add(("principle", pri))
        for std in _TOPOLOGY_STD_RE.findall(owner_text):
            refs_in_routed_owners.add(("standard", std))
        for skill in _TOPOLOGY_SKILL_PATH_RE.findall(owner_text):
            refs_in_routed_owners.add(("skill", skill))
        for pm in _TOPOLOGY_PAPER_PATH_RE.findall(owner_text):
            refs_in_routed_owners.add(("paper_module", pm))
    for row in seen_refs.values():
        direct = set(row["direct_surfaces"])
        for actor in actors:
            actor_surface_ids = {s.get("surface_id") for s in surfaces_by_actor[actor]}
            if direct & actor_surface_ids:
                row["reachable_actors"][actor] = "direct"
                continue
            routed_to_hub = any(
                adapter_routes_to_hub.get(sid)
                for sid in (s.get("surface_id") for s in surfaces_by_actor[actor])
            )
            if "agents_md" in direct and routed_to_hub:
                row["reachable_actors"][actor] = "transitive_via_agents_md"
                continue
            ref_key = (row["ref_kind"], row["ref"])
            if routed_to_hub and ref_key in refs_in_routed_owners:
                row["reachable_actors"][actor] = "transitive_via_routed_owner"
                continue
            row["reachable_actors"][actor] = "missing"
    # Annotate each ref with scope classification (shared / actor_local /
    # unknown) so downstream asymmetry checks can suppress actor-local refs
    # whose intended actor can reach them.
    scope_counts: dict[str, int] = {"shared": 0, "actor_local": 0, "unknown": 0}
    for row in seen_refs.values():
        scope = _classify_topology_ref_scope(row["ref_kind"], row["ref"])
        row["scope_class"] = scope["scope_class"]
        row["actor_scope"] = scope["actor_scope"]
        row["scope_reason"] = scope["scope_reason"]
        scope_counts[scope["scope_class"]] = scope_counts.get(scope["scope_class"], 0) + 1
    adapter_reachability = {
        "actors": list(actors),
        "shared_hub": shared_hub_path,
        "adapter_routes_to_shared_hub": adapter_routes_to_hub,
        "ref_count": len(seen_refs),
        "scope_counts": scope_counts,
        "refs": sorted(seen_refs.values(), key=lambda r: (r["ref_kind"], r["ref"])),
    }
    return {
        "schema_version": "entry_surface_topology_v3",
        "principle_anchor": "pri_131",
        "surfaces": surfaces,
        "edges": edges,
        "edge_count": len(edges),
        "node_types": ["entry_surface", "generated_region", "principle", "standard", "skill", "paper_module", "external_path"],
        "edge_types": ["contains", "routes_to", "cites"],
        "adapter_reachability": adapter_reachability,
        "coverage_threshold": {
            "owner_coverage": 0.6,
            "freshness_coverage": 0.4,
            "basis": "Initial heuristics. owner_coverage threshold reflects the Rosetta Stone shape — most route commands should sit near an owning artifact pointer (markdown link, standard/skill/paper path, generated sidecar, or source file). freshness_coverage is lower because not every route command needs a paired freshness check; only those operating against build-projected substrate do.",
        },
        "asymmetry_policy": {
            "rewards_transitive_routing": True,
            "rule": "A ref is reachable by an actor whose adapter routes to AGENTS.md if the ref is (a) directly present in any of the actor's adapter surfaces, OR (b) directly present in AGENTS.md (transitive_via_agents_md), OR (c) present in any paper module / skill that AGENTS.md cites (transitive_via_routed_owner). Adapters are not required to duplicate shared refs; the warning fires only when an actor cannot reach a shared ref through ANY of these paths.",
            "reachability_classifications": ["direct", "transitive_via_agents_md", "transitive_via_routed_owner", "missing"],
            "warning_kind": "shared_doctrine_adapter_asymmetry",
            "v3_change_note": "v2 only walked one hop (entry surface -> AGENTS.md). v3 adds one more hop: walks into paper modules and skills cited from AGENTS.md, recognizing refs in those routed owners as reachable. This honors pri_130's 'shared owner' semantic and corrects v2's false-positive findings caused by the audit's heuristic limitation rather than by real asymmetry.",
        },
    }


def _check_shared_doctrine_adapter_asymmetry(topology: Mapping[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Detect cases where shared doctrine refs (pri_/std_/skill/
      paper_module) are reachable from one actor's adapter reading path but
      not the other. Per pri_130's named follow-on (asymmetric AGENTS.md /
      CLAUDE.md adapter reading topology) and the operator's same-turn flag.
    - Mechanism: Read entry_surface_topology.adapter_reachability.refs;
      emit one warning per ref whose `reachable_actors` contains `missing`
      for at least one actor. Rewards transitive routing — a ref directly
      present in AGENTS.md AND reached by an adapter that routes to
      AGENTS.md is classified `transitive_via_agents_md` and does NOT fire.
    - Guarantee: Returns an empty list when topology lacks
      adapter_reachability (e.g. v1 schema) or no asymmetric refs exist.
    - Fails: None.
    """
    reachability = (topology.get("adapter_reachability") or {}) if isinstance(topology, Mapping) else {}
    findings: list[dict[str, Any]] = []
    for row in (reachability.get("refs") or []):
        if not isinstance(row, Mapping):
            continue
        actors_status = row.get("reachable_actors") or {}
        missing_actors = sorted(
            actor for actor, status in actors_status.items()
            if status == "missing"
        )
        if not missing_actors:
            continue
        ref_kind = str(row.get("ref_kind") or "")
        ref_id = str(row.get("ref") or "")
        direct = list(row.get("direct_surfaces") or [])
        scope_class = str(row.get("scope_class") or "unknown")
        actor_scope = row.get("actor_scope")
        scope_reason = str(row.get("scope_reason") or "")
        # Suppress actor_local refs whose intended actor CAN reach them
        # (presence in their own adapter is the success state for actor-local
        # doctrine; symmetric missing-from-other-actor is NOT a defect).
        if scope_class == "actor_local" and actor_scope:
            intended_status = actors_status.get(actor_scope)
            if intended_status in ("direct", "transitive_via_agents_md", "transitive_via_routed_owner"):
                continue
        # For shared refs, fire the standard shared_doctrine_adapter_asymmetry rule.
        # For unknown refs, fire a different rule (scope_unknown_adapter_asymmetry)
        # so they remain operator-triage targets without polluting the shared rule.
        if scope_class == "shared":
            rule = "shared_doctrine_adapter_asymmetry"
            message = (
                f"Shared doctrine ref {ref_id!r} ({ref_kind}) is directly present in "
                f"surfaces {direct or '<none>'} but is missing from actor reading "
                f"path(s) {missing_actors}. Scope reason: {scope_reason} Repair: route "
                f"via AGENTS.md or another shared owner artifact AGENTS.md cites; do "
                f"NOT duplicate into adapters. Adapters are not required to mirror "
                f"shared refs; the warning fires only when no direct OR transitive "
                f"reachability path exists for at least one actor."
            )
        elif scope_class == "actor_local":
            rule = "actor_local_doctrine_misrouted"
            message = (
                f"Actor-local doctrine ref {ref_id!r} ({ref_kind}, intended actor: "
                f"{actor_scope!r}) is directly present in surfaces {direct or '<none>'} "
                f"but is missing from its INTENDED actor's reading path. Scope reason: "
                f"{scope_reason} Repair: route the intended actor's adapter to the "
                f"surface that contains this ref, or relocate the ref into the "
                f"intended actor's adapter."
            )
        else:
            rule = "scope_unknown_adapter_asymmetry"
            message = (
                f"Doctrine ref {ref_id!r} ({ref_kind}) has scope_class=unknown and is "
                f"missing from actor reading path(s) {missing_actors}. Scope reason: "
                f"{scope_reason} Repair: classify as shared or actor_local in "
                f"_classify_topology_ref_scope (see system/lib/agent_entrypoint_audit.py); "
                f"the audit will then fire the correct narrower warning."
            )
        findings.append({
            "severity": "warning",
            "rule": rule,
            "doctrine_ref": ref_id,
            "ref_kind": ref_kind,
            "direct_surfaces": direct,
            "reachable_actors": dict(actors_status),
            "missing_actors": missing_actors,
            "scope_class": scope_class,
            "actor_scope": actor_scope,
            "scope_reason": scope_reason,
            "message": message,
        })
    return findings


def _check_route_pointer_quality(topology: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    thresholds = topology.get("coverage_threshold") or {}
    owner_floor = float(thresholds.get("owner_coverage") or 0.6)
    freshness_floor = float(thresholds.get("freshness_coverage") or 0.4)
    for surface in (topology.get("surfaces") or []):
        if not isinstance(surface, Mapping) or surface.get("status") == "missing":
            continue
        if not surface.get("route_command_count"):
            continue
        rc = int(surface.get("route_command_count") or 0)
        owner_cov = float(surface.get("owner_coverage") or 0)
        fresh_cov = float(surface.get("freshness_coverage") or 0)
        if owner_cov < owner_floor:
            findings.append({
                "severity": "warning",
                "rule": "route_pointer_missing_owner",
                "path": str(surface.get("path") or ""),
                "surface_id": str(surface.get("surface_id") or ""),
                "route_command_count": rc,
                "owner_coverage": owner_cov,
                "owner_coverage_floor": owner_floor,
                "message": (
                    f"Entry surface {surface.get('path')!r} carries {rc} route commands "
                    f"but only {owner_cov*100:.0f}% sit near an owning artifact "
                    f"(markdown link, standard/skill/paper path, generated sidecar, or source file) in their immediate "
                    f"context (floor: {owner_floor*100:.0f}%). Per the Rosetta Stone shape "
                    f"in std_agent_entry_surface.json::compression_via_projection_contract, "
                    f"every route command should pair with an owning_artifact pointer so "
                    f"cold agents can expand the seed. Repair: add markdown links to the "
                    f"routed owner artifacts, or relocate orphan route commands to a routed skill."
                ),
            })
        if fresh_cov < freshness_floor:
            findings.append({
                "severity": "warning",
                "rule": "route_pointer_missing_freshness_command",
                "path": str(surface.get("path") or ""),
                "surface_id": str(surface.get("surface_id") or ""),
                "route_command_count": rc,
                "freshness_coverage": fresh_cov,
                "freshness_coverage_floor": freshness_floor,
                "message": (
                    f"Entry surface {surface.get('path')!r} carries {rc} route commands "
                    f"but only {fresh_cov*100:.0f}% sit near a freshness signal "
                    f"(check_*.py, --check flag, refresh command, or 'freshness' keyword) in their immediate "
                    f"context (floor: {freshness_floor*100:.0f}%). Cold agents need a way to "
                    f"verify a routed surface is current; the Rosetta Stone shape requires "
                    f"a freshness_command alongside the route_command. Repair: pair each "
                    f"hub route command with the appropriate `check_*.py` or `--check` invocation."
                ),
            })
    return findings


def _check_navigation_integration_debt(*, repo_root: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Surface `integration_debt` self-diagnosis fields that navigation primitives emit
      inside raw JSON output where no cold agent ever sees them, per pri_128 test #3.
    - Mechanism: Subprocess the canonical russian-doll first-move command
      (`./repo-python kernel.py --option-surface paper_modules --band flag`), parse the JSON
      payload, and look for any top-level mapping field whose `status` is `integration_debt`.
      Each such field becomes one operator-visible audit finding carrying the source command,
      observed message, and a repair pointer.
    - Guarantee: Returns an empty list when no integration_debt signal is emitted, the kernel
      command fails, or the JSON cannot be parsed; never raises.
    - Fails: None (subprocess failure is reported as an empty list, not a finding, so the audit
      never fails closed on a missing kernel binary).
    - When-needed: Open when extending the integration-debt surface to new emitter commands or
      to additional kinds beyond paper_modules.
    """
    import subprocess as _subprocess

    PROBE_COMMAND = (
        "./repo-python", "kernel.py",
        "--option-surface", "paper_modules", "--band", "flag",
    )
    try:
        proc = _subprocess.run(
            list(PROBE_COMMAND),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception:
        return []
    if proc.returncode != 0 or not proc.stdout:
        return []
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return []
    if not isinstance(payload, Mapping):
        return []

    findings: list[dict[str, Any]] = []
    probe_command_str = " ".join(PROBE_COMMAND)
    for field_name, field_value in payload.items():
        if not isinstance(field_value, Mapping):
            continue
        status = str(field_value.get("status") or "").strip()
        if status != "integration_debt":
            continue
        observed = str(field_value.get("observed") or "").strip()
        emitter_command = str(field_value.get("command") or "").strip()
        message = (
            f"Agent-entrypoint audit surfaced unresolved navigation integration debt: "
            f"`{field_name}.status='integration_debt'` is reported by "
            f"`{emitter_command or probe_command_str}` and observed in the JSON output of "
            f"`{probe_command_str}`. The debt is now operator-visible through this audit; "
            f"the remaining repair is upstream in the primitive/projection that reported the "
            f"debt. Observed: {observed or '<no observed message>'}."
        )
        findings.append({
            "severity": "warning",
            "rule": "navigation_integration_debt_unresolved",
            "legacy_rule": "navigation_integration_debt_not_operator_visible",
            "path": str(field_name),
            "probe_command": probe_command_str,
            "emitter_command": emitter_command or probe_command_str,
            "debt_field": field_name,
            "debt_status": status,
            "observed": observed,
            "message": message,
        })
    return findings


def _check_oversized(entrypoint: Mapping[str, Any], path_records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    line_budget = entrypoint.get("line_budget")
    if not isinstance(line_budget, int) or line_budget <= 0:
        return []
    findings: list[dict[str, Any]] = []
    primary_paths = {str(item) for item in (entrypoint.get("primary_paths") or [])}
    for record in path_records:
        if str(record.get("path") or "") not in primary_paths:
            continue
        line_count = int(record.get("line_count") or 0)
        if line_count > line_budget:
            findings.append(
                {
                    "severity": "warning",
                    "rule": "oversized_entrypoint",
                    "entrypoint_id": str(entrypoint.get("id") or ""),
                    "path": str(record.get("path") or ""),
                    "message": (
                        f"Entrypoint {entrypoint.get('id')!r} primary path {record.get('path')!r} is "
                        f"{line_count} lines, over budget {line_budget}; route depth into paper modules / skills."
                    ),
                }
            )
    return findings


def _check_hidden_adapter_surfaces(
    registry: Mapping[str, Any], *, repo_root: Path
) -> list[dict[str, Any]]:
    inventory = registry.get("dotfile_tree_inventory")
    if not isinstance(inventory, Mapping):
        return []
    coverage_files = [str(item) for item in inventory.get("coverage_surfaces", []) if str(item).strip()]
    coverage_text = "\n".join(_read_text_safe(repo_root / item) for item in coverage_files).lower()
    findings: list[dict[str, Any]] = []
    entrypoint_texts: dict[str, str] = {}
    for ep in registry.get("entrypoints", []):
        if not isinstance(ep, Mapping):
            continue
        combined = "\n".join(
            _read_text_safe(repo_root / str(item))
            for item in [
                *(ep.get("primary_paths") or []),
                *(ep.get("read_scope_paths") or []),
                *(ep.get("companion_paths") or []),
            ]
        )
        entrypoint_texts[str(ep.get("id") or "")] = combined.lower()
    for tree_key, expected_paths in inventory.items():
        if tree_key in {"purpose", "coverage_surfaces"}:
            continue
        if not isinstance(expected_paths, list):
            continue
        for raw in expected_paths:
            path = repo_root / str(raw)
            if not path.exists():
                findings.append(
                    {
                        "severity": "warning",
                        "rule": "hidden_adapter_surface",
                        "path": str(raw),
                        "message": (
                            f"Adapter file {raw!r} declared in dotfile_tree_inventory[{tree_key!r}] "
                            "is missing on disk; either author it or drop it from the registry."
                        ),
                    }
                )
                continue
            token = str(raw).strip().lower()
            tree_token = str(tree_key).strip().lower()
            if token in coverage_text:
                continue
            if any(token in text for text in entrypoint_texts.values()):
                continue
            broad_tree_covered = bool(tree_token) and (
                tree_token in coverage_text or any(tree_token in text for text in entrypoint_texts.values())
            )
            if broad_tree_covered:
                findings.append(
                    {
                        "severity": "warning",
                        "rule": "hidden_adapter_surface",
                        "path": str(raw),
                        "coverage_quality": "broad_tree_reference",
                        "message": (
                            f"Adapter file {raw!r} exists on disk and its tree {tree_key!r} is mentioned, "
                            "but no declared entrypoint or coverage paper module names the file exactly."
                        ),
                    }
                )
                continue
            findings.append(
                {
                    "severity": "error",
                    "rule": "hidden_adapter_surface",
                    "path": str(raw),
                    "coverage_quality": "absent",
                    "message": (
                        f"Adapter file {raw!r} exists on disk but no declared entrypoint primary/companion path "
                        "and no coverage paper module references it; adapter substrate is invisible to navigation."
                    ),
                }
            )
    return findings


def _check_bootstrap_coherence(
    registry: Mapping[str, Any], bootstrap_actors: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Cross-check: every adapter entrypoint's actor_id must appear in actor_context_surfaces."""
    known_actor_ids = {str(item.get("actor_id") or "") for item in bootstrap_actors if isinstance(item, Mapping)}
    findings: list[dict[str, Any]] = []
    for ep in registry.get("entrypoints", []):
        if not isinstance(ep, Mapping):
            continue
        if str(ep.get("role") or "") != "adapter":
            continue
        actor_id = str(ep.get("actor_id") or "").strip()
        if not actor_id:
            continue
        if actor_id not in known_actor_ids:
            findings.append(
                {
                    "severity": "error",
                    "rule": "missing_axis",
                    "entrypoint_id": str(ep.get("id") or ""),
                    "axis_id": "adapter_surfaces",
                    "message": (
                        f"Entrypoint {ep.get('id')!r} declares actor_id={actor_id!r} which is not in "
                        "codex/doctrine/agent_bootstrap.json::actor_context_surfaces; the audit truth "
                        "and the bootstrap truth have forked."
                    ),
                }
            )
    return findings


def _check_unknown_axes(
    registry: Mapping[str, Any], axes: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    known_axis_ids = {str(item.get("id") or "") for item in axes if isinstance(item, Mapping)}
    findings: list[dict[str, Any]] = []
    for ep in registry.get("entrypoints", []):
        if not isinstance(ep, Mapping):
            continue
        for axis_id in ep.get("required_axes", []) or []:
            if str(axis_id) not in known_axis_ids:
                findings.append(
                    {
                        "severity": "warning",
                        "rule": "unknown_axis_reference",
                        "entrypoint_id": str(ep.get("id") or ""),
                        "axis_id": str(axis_id),
                        "message": f"Entrypoint {ep.get('id')!r} cites unknown axis {axis_id!r}.",
                    }
                )
    return findings


_INCOHERENT_DOCTRINE_PATTERNS = (
    {
        "pattern": re.compile(r"\bpri_\*\.json\b", re.IGNORECASE),
        "token": "pri_*.json",
        "authority": "obsidian/**/raw_seed/raw_seed_principles.json::principles[]",
        "projection": "obsidian/doctrine/principles/pri_*.md",
    },
)


def _check_doctrine_file_pattern_coherence(
    entrypoint: Mapping[str, Any], *, repo_root: Path
) -> list[dict[str, Any]]:
    """Flag entrypoint rules that cite doctrine file patterns that are not real authorities."""
    findings: list[dict[str, Any]] = []
    paths = _dedupe_strings(
        [
            *(entrypoint.get("primary_paths") or []),
            *(entrypoint.get("read_scope_paths") or []),
            *(entrypoint.get("companion_paths") or []),
        ]
    )
    for raw in paths:
        text = _read_text_safe(repo_root / raw)
        if not text:
            continue
        for spec in _INCOHERENT_DOCTRINE_PATTERNS:
            pattern = spec["pattern"]
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                snippet_start = max(0, match.start() - 80)
                snippet_end = min(len(text), match.end() + 80)
                snippet = " ".join(text[snippet_start:snippet_end].split())
                findings.append(
                    {
                        "severity": "error",
                        "rule": "incoherent_doctrine_file_pattern",
                        "entrypoint_id": str(entrypoint.get("id") or ""),
                        "path": str(raw),
                        "line": line,
                        "pattern": spec["token"],
                        "authority": spec["authority"],
                        "projection": spec["projection"],
                        "snippet": snippet,
                        "message": (
                            f"Entrypoint {entrypoint.get('id')!r} cites {spec['token']!r}, but that is not "
                            f"a live doctrine authority pattern. Principles are rows in {spec['authority']} "
                            f"and may project to {spec['projection']}; rewrite the instruction to name the "
                            "real authority surface and apply lane."
                        ),
                    }
                )
    return findings


def _entrypoint_fix_scope(entrypoint_id: str) -> str:
    if entrypoint_id == "claude_code":
        return "claude_only"
    if entrypoint_id == "codex":
        return "codex_only"
    if entrypoint_id == "shared":
        return "shared"
    return f"{entrypoint_id}_only" if entrypoint_id else "shared"


def _repair_metadata_for_finding(
    finding: Mapping[str, Any],
    *,
    missing_axis_counts: Mapping[str, int],
    required_axis_counts: Mapping[str, int],
    entrypoint_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    rule = str(finding.get("rule") or "")
    entrypoint_id = str(finding.get("entrypoint_id") or "")
    axis_id = str(finding.get("axis_id") or "")
    entrypoint = entrypoint_by_id.get(entrypoint_id) or {}
    primary_paths = [str(item) for item in (entrypoint.get("primary_paths") or []) if str(item).strip()]

    if rule == "missing_axis":
        missing_count = int(missing_axis_counts.get(axis_id) or 0)
        required_count = int(required_axis_counts.get(axis_id) or 0)
        if axis_id and required_count > 1 and missing_count == required_count:
            surface = "codex/doctrine/agent_bootstrap.json::type_a_convergence_contract.comprehension_gate"
            metadata: dict[str, Any] = {
                "fix_scope": "shared",
                "repair_kind": "shared_projection_fix",
                "repair_surface": surface,
                "repair_reason": (
                    f"Axis {axis_id!r} is missing from every entrypoint that requires it; repair the "
                    "shared bootstrap/projection source instead of patching adapter prose one file at a time."
                ),
            }
            if axis_id == "derived_facts_anti_drift":
                metadata["shared_fix_candidate"] = {
                    "surface": surface,
                    "commands": [
                        "python3 kernel.py --facts",
                        "python3 kernel.py --fact-audit",
                        "python3 kernel.py --paper-module-facts <slug>",
                    ],
                }
            return metadata
        return {
            "fix_scope": _entrypoint_fix_scope(entrypoint_id),
            "repair_kind": "adapter_entrypoint_fix",
            "repair_surface": primary_paths[0] if primary_paths else "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
            "repair_reason": (
                f"Only entrypoint {entrypoint_id!r} is missing axis {axis_id!r}; fix that actor's "
                "adapter/read-order surface or its audit overlay."
            ),
        }

    if rule == "weak_route":
        return {
            "fix_scope": _entrypoint_fix_scope(entrypoint_id),
            "repair_kind": "strengthen_route_citation",
            "repair_surface": primary_paths[0] if primary_paths else "codex/doctrine/agent_bootstrap.json",
            "repair_reason": (
                "The axis is only covered by ambient prose or a literal token. Add an explicit kernel "
                "command, docs-route, paper-module slug, or projection-file citation."
            ),
        }

    if rule in {"generated_block_drift", "stale_projection"}:
        return {
            "fix_scope": "projection_builder",
            "repair_kind": "regenerate_projection",
            "repair_surface": "tools/meta/factory/build_agent_bootstrap_projection.py",
            "repair_reason": "Managed markdown differs from the current bootstrap renderer; regenerate, do not edit the marked region by hand.",
        }

    if rule == "hidden_adapter_surface":
        path = str(finding.get("path") or "")
        if "missing on disk" in str(finding.get("message") or ""):
            return {
                "fix_scope": "dotfile_plane",
                "repair_kind": "registry_or_file_fix",
                "repair_surface": "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
                "repair_reason": f"Declared adapter path {path!r} is absent; either author the file or remove the inventory row.",
            }
        return {
            "fix_scope": "dotfile_plane",
            "repair_kind": "document_adapter_surface",
            "repair_surface": "codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md",
            "repair_reason": f"Adapter path {path!r} exists but is not exactly covered by the host-agent dotfile plane.",
        }

    if rule == "oversized_entrypoint":
        return {
            "fix_scope": _entrypoint_fix_scope(entrypoint_id),
            "repair_kind": "entrypoint_budget_rebalance",
            "repair_surface": str(finding.get("path") or (primary_paths[0] if primary_paths else "")),
            "repair_reason": "The entrypoint exceeds its line budget; route depth into paper modules or companion surfaces.",
        }

    if rule == "unknown_axis_reference":
        return {
            "fix_scope": "entrypoint_registry",
            "repair_kind": "registry_consistency_fix",
            "repair_surface": "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
            "repair_reason": "The entrypoint overlay references an axis id that is not declared in the axis registry.",
        }

    if rule == "incoherent_doctrine_file_pattern":
        path = str(finding.get("path") or "")
        return {
            "fix_scope": _entrypoint_fix_scope(entrypoint_id),
            "repair_kind": "entrypoint_authority_pattern_fix",
            "repair_surface": path or (primary_paths[0] if primary_paths else "codex/doctrine/agent_entrypoints/entrypoint_registry.json"),
            "repair_reason": (
                "The entrypoint names a doctrine file pattern that is not a real authority. Replace it with "
                "the actual authority surface (`raw_seed_principles.json` rows, `con_*.json`, or `mech_*.json`) "
                "and cite the apply lane that mutates it."
            ),
        }

    return {
        "fix_scope": "shared",
        "repair_kind": "manual_review",
        "repair_surface": "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        "repair_reason": "No rule-specific repair mapping exists; inspect the finding and update the audit standard if this recurs.",
    }


def _attach_repair_metadata(
    findings: Sequence[Mapping[str, Any]],
    *,
    entrypoint_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    missing_axis_counts = Counter(
        str(item.get("axis_id") or "")
        for item in findings
        if str(item.get("rule") or "") == "missing_axis" and str(item.get("axis_id") or "")
    )
    required_axis_counts: Counter[str] = Counter()
    for record in entrypoint_records:
        for axis_id in record.get("required_axes") or []:
            required_axis_counts[str(axis_id)] += 1
    entrypoint_by_id = {
        str(record.get("id") or ""): record
        for record in entrypoint_records
        if str(record.get("id") or "")
    }
    enriched: list[dict[str, Any]] = []
    for raw in findings:
        finding = dict(raw)
        finding.update(
            _repair_metadata_for_finding(
                finding,
                missing_axis_counts=missing_axis_counts,
                required_axis_counts=required_axis_counts,
                entrypoint_by_id=entrypoint_by_id,
            )
        )
        enriched.append(finding)
    return enriched


def _build_repair_plan(findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for finding in findings:
        surface = str(finding.get("repair_surface") or "manual_review")
        kind = str(finding.get("repair_kind") or "manual_review")
        scope = str(finding.get("fix_scope") or "shared")
        key = (scope, surface, kind)
        row = grouped.setdefault(
            key,
            {
                "fix_scope": scope,
                "repair_surface": surface,
                "repair_kind": kind,
                "finding_count": 0,
                "rules": set(),
                "entrypoint_ids": set(),
                "axis_ids": set(),
                "repair_reason": str(finding.get("repair_reason") or ""),
            },
        )
        row["finding_count"] += 1
        if finding.get("rule"):
            row["rules"].add(str(finding.get("rule")))
        if finding.get("entrypoint_id"):
            row["entrypoint_ids"].add(str(finding.get("entrypoint_id")))
        if finding.get("axis_id"):
            row["axis_ids"].add(str(finding.get("axis_id")))
        if finding.get("shared_fix_candidate") and "shared_fix_candidate" not in row:
            row["shared_fix_candidate"] = finding.get("shared_fix_candidate")
    items: list[dict[str, Any]] = []
    for row in grouped.values():
        items.append(
            {
                **{key: value for key, value in row.items() if key not in {"rules", "entrypoint_ids", "axis_ids"}},
                "rules": sorted(row["rules"]),
                "entrypoint_ids": sorted(row["entrypoint_ids"]),
                "axis_ids": sorted(row["axis_ids"]),
            }
        )
    items.sort(key=lambda row: (str(row["fix_scope"]), str(row["repair_surface"]), str(row["repair_kind"])))
    return {
        "summary": {
            "repair_item_count": len(items),
            "finding_count": len(findings),
        },
        "items": items,
    }


def build_agent_entrypoint_audit(
    *,
    repo_root: Path = REPO_ROOT,
    axis_registry_path: Path | None = None,
    entrypoint_registry_path: Path | None = None,
    bootstrap_path: Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    axis_payload = load_axis_registry(axis_registry_path or (repo_root / AXIS_REGISTRY_PATH.relative_to(REPO_ROOT)))
    entrypoint_payload = load_entrypoint_registry(
        entrypoint_registry_path or (repo_root / ENTRYPOINT_REGISTRY_PATH.relative_to(REPO_ROOT))
    )
    bootstrap_config = load_bootstrap_config(bootstrap_path or (repo_root / AGENT_BOOTSTRAP_PATH.relative_to(REPO_ROOT)))
    bootstrap_actors = [
        dict(item)
        for item in (bootstrap_config.get("actor_context_surfaces") or [])
        if isinstance(item, Mapping)
    ]

    axes = [dict(item) for item in (axis_payload.get("axes") or []) if isinstance(item, Mapping)]
    axis_by_id = {str(item.get("id") or ""): item for item in axes}
    entrypoints = _derive_entrypoints_from_bootstrap(entrypoint_payload, bootstrap_config)
    known_paper_module_slugs = _paper_module_slugs(repo_root)
    expected_regions = _expected_generated_regions(repo_root)

    generated_at = timestamp or _utc_iso()
    findings: list[dict[str, Any]] = []
    entrypoint_records: list[dict[str, Any]] = []

    for entrypoint in entrypoints:
        haystack, path_records, missing_paths = _read_entrypoint_content(entrypoint, repo_root=repo_root)
        axis_matrix: list[dict[str, Any]] = []
        uncovered_ids: list[str] = []
        required_axes = [str(item) for item in (entrypoint.get("required_axes") or [])]
        for axis_id in required_axes:
            axis = axis_by_id.get(axis_id)
            if axis is None:
                axis_matrix.append(
                    {
                        "axis_id": axis_id,
                        "covered": False,
                        "probe_results": [],
                        "matched_methods": [],
                        "notes": ["axis missing from axis_registry.json"],
                    }
                )
                uncovered_ids.append(axis_id)
                continue
            result = _probe_axis(axis, haystack, known_paper_module_slugs=known_paper_module_slugs)
            axis_matrix.append(result)
            if not result["covered"]:
                uncovered_ids.append(axis_id)
                severity = str(axis.get("severity_if_missing") or "error").strip() or "error"
                findings.append(
                    {
                        "severity": severity,
                        "rule": "missing_axis",
                        "entrypoint_id": str(entrypoint.get("id") or ""),
                        "axis_id": axis_id,
                        "message": (
                            f"Entrypoint {entrypoint.get('id')!r} has no reachable surface for required axis "
                            f"{axis_id!r} ({axis.get('title')!r}). Cold agent cannot verify this comprehension "
                            "obligation without guessing."
                        ),
                    }
                )
            else:
                matched_methods = {str(method) for method in (result.get("matched_methods") or [])}
                declared_methods = {
                    str(row.get("method") or "")
                    for row in (axis.get("resolution_methods") or [])
                    if isinstance(row, Mapping)
                }
                if matched_methods and not (matched_methods & STRONG_RESOLUTION_METHODS) and (declared_methods & STRONG_RESOLUTION_METHODS):
                    findings.append(
                        {
                            "severity": "warning",
                            "rule": "weak_route",
                            "entrypoint_id": str(entrypoint.get("id") or ""),
                            "axis_id": axis_id,
                            "message": (
                                f"Entrypoint {entrypoint.get('id')!r} covers axis {axis_id!r} only through "
                                f"ambient method(s) {sorted(matched_methods)}. Prefer an explicit kernel/docs/"
                                "paper-module/projection citation."
                            ),
                        }
                    )

        findings.extend(_detect_generated_block_drift(entrypoint, repo_root=repo_root, expected_regions=expected_regions))
        findings.extend(_check_oversized(entrypoint, path_records))
        findings.extend(_check_doctrine_file_pattern_coherence(entrypoint, repo_root=repo_root))

        if missing_paths:
            for missing in missing_paths:
                findings.append(
                    {
                        "severity": "warning",
                        "rule": "hidden_adapter_surface",
                        "entrypoint_id": str(entrypoint.get("id") or ""),
                        "path": missing,
                        "message": (
                            f"Declared {'primary' if missing in (entrypoint.get('primary_paths') or []) else 'companion'} path "
                            f"{missing!r} is missing on disk for entrypoint {entrypoint.get('id')!r}."
                        ),
                    }
                )

        covered_count = sum(1 for row in axis_matrix if row["covered"])
        status = "covered" if covered_count == len(required_axes) else "incomplete"
        entrypoint_records.append(
            {
                "id": str(entrypoint.get("id") or ""),
                "role": str(entrypoint.get("role") or ""),
                "actor_id": entrypoint.get("actor_id"),
                "label": str(entrypoint.get("label") or ""),
                "primary_paths": list(entrypoint.get("primary_paths") or []),
                "read_scope_paths": list(entrypoint.get("read_scope_paths") or entrypoint.get("primary_paths") or []),
                "companion_paths": list(entrypoint.get("companion_paths") or []),
                "dotfile_tree": entrypoint.get("dotfile_tree"),
                "line_budget": entrypoint.get("line_budget"),
                "path_records": path_records,
                "required_axes": required_axes,
                "axis_matrix": axis_matrix,
                "covered_axis_count": covered_count,
                "required_axis_count": len(required_axes),
                "uncovered_axes": uncovered_ids,
                "status": status,
                "notes": str(entrypoint.get("notes") or ""),
            }
        )

    derived_entrypoint_payload = {**entrypoint_payload, "entrypoints": entrypoints}
    findings.extend(_check_hidden_adapter_surfaces(derived_entrypoint_payload, repo_root=repo_root))
    findings.extend(_check_bootstrap_coherence(derived_entrypoint_payload, bootstrap_actors))
    findings.extend(_check_unknown_axes(entrypoint_payload, axes))
    findings.extend(_check_navigation_integration_debt(repo_root=repo_root))
    entry_surface_budget_ledger = _build_entry_surface_budget_ledger(repo_root=repo_root)
    findings.extend(_check_entry_surface_reserve(entry_surface_budget_ledger))
    findings.extend(_check_architectural_constraint_principle_anchor(entry_surface_budget_ledger))
    entry_surface_topology = _build_entry_surface_topology(repo_root=repo_root)
    findings.extend(_check_route_pointer_quality(entry_surface_topology))
    findings.extend(_check_shared_doctrine_adapter_asymmetry(entry_surface_topology))
    findings = _attach_repair_metadata(findings, entrypoint_records=entrypoint_records)
    repair_plan = _build_repair_plan(findings)

    severity_counts = Counter(str(item.get("severity") or "") for item in findings)
    rule_counts = Counter(str(item.get("rule") or "") for item in findings)
    status_counts = Counter(str(item.get("status") or "") for item in entrypoint_records)

    summary = {
        "entrypoint_count": len(entrypoint_records),
        "axis_count": len(axes),
        "finding_count": len(findings),
        "error_count": int(severity_counts.get("error", 0)),
        "warning_count": int(severity_counts.get("warning", 0)),
        "status_counts": dict(sorted(status_counts.items())),
        "rule_counts": dict(sorted(rule_counts.items())),
        "entrypoint_status": [
            {
                "id": record["id"],
                "role": record["role"],
                "actor_id": record.get("actor_id"),
                "status": record["status"],
                "covered_axis_count": record["covered_axis_count"],
                "required_axis_count": record["required_axis_count"],
                "uncovered_axes": record["uncovered_axes"],
            }
            for record in entrypoint_records
        ],
    }
    if summary["error_count"] > 0:
        recommended_action = "refresh"
    elif summary["warning_count"] > 0:
        recommended_action = "review_warnings"
    else:
        recommended_action = "trust"
    summary["recommended_action"] = recommended_action

    sources = {
        "live": [
            _relpath(repo_root / STANDARD_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / AXIS_REGISTRY_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / ENTRYPOINT_REGISTRY_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / AGENT_BOOTSTRAP_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / PAPER_MODULE_INDEX_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        ],
        "derived": [
            _relpath(repo_root / AUDIT_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / SUMMARY_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / PER_ENTRYPOINT_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        ],
    }

    audit = {
        "kind": "agent_entrypoint_audit",
        "schema_version": AUDIT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "standard": _relpath(repo_root / STANDARD_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        "registries": {
            "axes": _relpath(repo_root / AXIS_REGISTRY_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            "entrypoints": _relpath(repo_root / ENTRYPOINT_REGISTRY_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        },
        "summary": summary,
        "repair_plan": repair_plan,
        "axes": [
            {
                "id": str(axis.get("id") or ""),
                "title": str(axis.get("title") or ""),
                "why": str(axis.get("why") or ""),
                "required_for_actors": list(axis.get("required_for_actors") or []),
                "severity_if_missing": str(axis.get("severity_if_missing") or "error"),
                "resolution_methods": [
                    AxisResolution.from_row(row).as_dict()
                    for row in (axis.get("resolution_methods") or [])
                    if isinstance(row, Mapping)
                ],
                "tags": list(axis.get("tags") or []),
            }
            for axis in axes
        ],
        "entrypoints": entrypoint_records,
        "findings": findings,
        "dotfile_tree_inventory": dict(entrypoint_payload.get("dotfile_tree_inventory") or {}),
        "entry_surface_budget_ledger": entry_surface_budget_ledger,
        "entry_surface_topology": entry_surface_topology,
        "sources": sources,
    }

    summary_payload = {
        "kind": "agent_entrypoint_audit_summary",
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_at": generated_at,
        "summary": summary,
        "repair_plan": repair_plan,
        "sources": sources,
    }

    per_entrypoint_payload = {
        "kind": "agent_entrypoint_audit_per_entrypoint",
        "schema_version": PER_ENTRYPOINT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "entrypoints": [
            {
                "id": record["id"],
                "role": record["role"],
                "actor_id": record.get("actor_id"),
                "label": record["label"],
                "primary_paths": record["primary_paths"],
                "read_scope_paths": record["read_scope_paths"],
                "companion_paths": record["companion_paths"],
                "axis_matrix": record["axis_matrix"],
                "covered_axis_count": record["covered_axis_count"],
                "required_axis_count": record["required_axis_count"],
                "uncovered_axes": record["uncovered_axes"],
                "status": record["status"],
            }
            for record in entrypoint_records
        ],
        "sources": sources,
    }

    return {"audit": audit, "summary": summary_payload, "per_entrypoint": per_entrypoint_payload}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_agent_entrypoint_audit(
    *,
    repo_root: Path = REPO_ROOT,
    axis_registry_path: Path | None = None,
    entrypoint_registry_path: Path | None = None,
    bootstrap_path: Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    payload = build_agent_entrypoint_audit(
        repo_root=repo_root,
        axis_registry_path=axis_registry_path,
        entrypoint_registry_path=entrypoint_registry_path,
        bootstrap_path=bootstrap_path,
        timestamp=timestamp,
    )
    out_dir = repo_root / HOLOGRAM_DIR.relative_to(REPO_ROOT)
    _write_json(out_dir / AUDIT_PATH.name, payload["audit"])
    _write_json(out_dir / SUMMARY_PATH.name, payload["summary"])
    _write_json(out_dir / PER_ENTRYPOINT_PATH.name, payload["per_entrypoint"])
    return {
        "kind": "agent_entrypoint_audit_write_receipt",
        "audit_path": _relpath(out_dir / AUDIT_PATH.name, repo_root=repo_root),
        "summary_path": _relpath(out_dir / SUMMARY_PATH.name, repo_root=repo_root),
        "per_entrypoint_path": _relpath(out_dir / PER_ENTRYPOINT_PATH.name, repo_root=repo_root),
        "summary": dict(payload["audit"].get("summary") or {}),
    }


def load_agent_entrypoint_audit(
    *, repo_root: Path = REPO_ROOT, build_if_missing: bool = True
) -> dict[str, Any]:
    path = repo_root / AUDIT_PATH.relative_to(REPO_ROOT)
    payload = _safe_read_json(path)
    if isinstance(payload, Mapping):
        return dict(payload)
    if build_if_missing:
        return build_agent_entrypoint_audit(repo_root=repo_root)["audit"]
    return {
        "kind": "agent_entrypoint_audit",
        "schema_version": AUDIT_SCHEMA_VERSION,
        "summary": {"entrypoint_count": 0, "finding_count": 0, "error_count": 0, "warning_count": 0},
        "entrypoints": [],
        "findings": [],
    }


_ENTRYPOINT_ALIASES = {
    "claude": "claude_code",
    "claude-code": "claude_code",
    "claudecode": "claude_code",
    "agents": "shared",
    "hub": "shared",
}


def select_entrypoint(
    audit: Mapping[str, Any], request: str
) -> dict[str, Any] | None:
    raw = str(request or "").strip().lower()
    if not raw:
        return None
    normalized = _ENTRYPOINT_ALIASES.get(raw, raw)
    for record in audit.get("entrypoints") or []:
        if not isinstance(record, Mapping):
            continue
        rid = str(record.get("id") or "").lower()
        actor = str(record.get("actor_id") or "").lower()
        role = str(record.get("role") or "").lower()
        if normalized == rid or normalized == actor or (normalized == "shared" and role == "shared_hub"):
            return dict(record)
    return None


def summarize_entrypoints(audit: Mapping[str, Any]) -> dict[str, Any]:
    summary = dict(audit.get("summary") or {})
    rows = []
    for record in audit.get("entrypoints") or []:
        if not isinstance(record, Mapping):
            continue
        axis_tiles = [
            {
                "axis_id": axis.get("axis_id"),
                "covered": bool(axis.get("covered")),
                "matched_methods": list(axis.get("matched_methods") or []),
            }
            for axis in record.get("axis_matrix") or []
            if isinstance(axis, Mapping)
        ]
        rows.append(
            {
                "id": record.get("id"),
                "role": record.get("role"),
                "actor_id": record.get("actor_id"),
                "label": record.get("label"),
                "status": record.get("status"),
                "covered_axis_count": record.get("covered_axis_count"),
                "required_axis_count": record.get("required_axis_count"),
                "uncovered_axes": list(record.get("uncovered_axes") or []),
                "axis_tiles": axis_tiles,
            }
        )
    return {"summary": summary, "entrypoints": rows}
