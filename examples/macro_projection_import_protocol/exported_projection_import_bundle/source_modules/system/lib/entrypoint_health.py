"""Entrypoint budget and stale-route scanner.

This is an input to the navigation metabolism ratchet, not a standalone audit
authority. It keeps the always-loaded instruction surfaces honest about size
and first-contact route shape.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.agent_entrypoint_audit import GENERATED_BLOCK_MARKERS
from system.lib.agent_bootstrap_projection import (
    PAPER_MODULE_MARKERS,
    PAPER_MODULE_PROJECTION_TARGET_HINTS,
    build_bootstrap_projection_context,
    load_agent_bootstrap_config,
    load_canonical_option_surface_routes,
    render_adapter_markdown,
    render_live_markdown,
    render_paper_module_index_markdown,
    stabilize_instruction_discovery_target,
)
from system.lib.routing_projection import (
    BEGIN_MARKER as ROUTING_BEGIN_MARKER,
    END_MARKER as ROUTING_END_MARKER,
    build_routing_payload,
    render_routing_markdown,
    routing_status,
)


ENTRYPOINT_PATHS = ["AGENTS.override.md", "AGENTS.md", "CLAUDE.md", "CODEX.md"]
GENERATED_ENTRYPOINT_GLOBS = [
    ".agents/skills/**/SKILL.md",
    ".codex/skills/**/SKILL.md",
    "codex/doctrine/skills/**/*.md",
]
DEFAULT_BUDGETS = {
    "AGENTS.override.md": 17600,
    "AGENTS.md": 36045,
    "CLAUDE.md": 36045,
    "CODEX.md": 36045,
}
VOLATILE_MARKDOWN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"- Factory stage: `[^`]*` — last_run `[^`]*`"),
        "- Factory stage: `<volatile-runtime-state>`",
    ),
    (
        re.compile(r"- `system_map\.json` generated_at: `[^`]*`"),
        "- `system_map.json` generated_at: `<volatile-runtime-state>`",
    ),
    (
        re.compile(r"- `doctrine_runtime\.json` mtime \(UTC\): `[^`]*`"),
        "- `doctrine_runtime.json` mtime (UTC): `<volatile-runtime-state>`",
    ),
    (
        re.compile(r"- `orchestration_state\.json`: `[^`]*` gate `[^`]*`"),
        "- `orchestration_state.json`: `<volatile-runtime-state>`",
    ),
    (
        re.compile(r"- Orchestration: driver `[^`]*`, gate `[^`]*`"),
        "- Orchestration: `<volatile-runtime-state>`",
    ),
    (
        re.compile(r"- `documentation_route_focus\.json`: `[^`]*`"),
        "- `documentation_route_focus.json`: `<volatile-runtime-state>`",
    ),
    (
        re.compile(r"- `system_view\.json`: `[^`]+` — file_count `[^`]*`"),
        "- `system_view.json`: `<volatile-runtime-state>`",
    ),
    (
        re.compile(
            r"Freshness: `[^`]+` · authored(?: modules:)? `[^`]+`"
            r"(?: · (?:checked-in sidecars: index `[^`]+` / report `[^`]+`|sidecars `[^`]+`))?"
        ),
        "Freshness: `<volatile>`",
    ),
    (re.compile(r"latest_event `[^`]+`"), "latest_event `<volatile>`"),
    (re.compile(r"Latest event: `[^`]+`"), "Latest event: `<volatile>`"),
)
ALLOW_CONTEXT_RE = re.compile(
    r"\b(drilldown|drilldowns|evidence|fallback|explicit|selected|stable id|stable slug|"
    r"not first[- ]contact|not first move|after stable|only after|demoted?|DEBUG_TRACE|"
    r"requires --debug|do not|don't|never|unsupported|before reaching|verify|verified|"
    r"refresh before citing|document what exists)\b",
    re.IGNORECASE,
)
FORBIDDEN_ROUTE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("registry_first_facade", re.compile(r"Route through the registry first", re.IGNORECASE)),
    ("raw_kernel_help", re.compile(r"(?:kernel\.py\s+--help|`--help`)")),
    ("skill_find_free_text", re.compile(r"--skill-find\s+\"<[^>]+>\"")),
    (
        "skill_find_default_search",
        re.compile(r"--skill-find(?:\s+\"[^\"]+\"|\s+<[^>]+>|\s+[A-Za-z0-9_./:-]+)(?!\s+--debug)"),
    ),
    ("paper_module_query", re.compile(r"--paper-module\s+\"<[^>]+>\"")),
    ("docs_route_query", re.compile(r"--docs-route\s+\"<[^>]+>\"")),
    (
        "paper_modules_row_flag_all",
        re.compile(r"--option-surface\s+paper_modules\s+--band\s+flag(?!\s+--ids)"),
    ),
    ("paper_lattice_free_text", re.compile(r"--paper-lattice\s+(?:\"<[^>]+>\"|<[^>]+>)")),
)

BAD_NEGATED_IMPERATIVE_RE = re.compile(
    r"\b(?:do not|don't|never)\s+(?:forget|fail|skip)\s+to\s+(?:run|use|call|open)",
    re.IGNORECASE,
)


def _allowed_stale_route_context(line: str) -> bool:
    if BAD_NEGATED_IMPERATIVE_RE.search(line):
        return False
    return bool(ALLOW_CONTEXT_RE.search(line))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(data) if isinstance(data, dict) else {}


def _budgets(repo_root: Path) -> dict[str, int]:
    out = dict(DEFAULT_BUDGETS)
    std = _load_json(repo_root / "codex/standards/std_agent_entry_surface.json")
    rows = std.get("compression_budgets") if isinstance(std.get("compression_budgets"), Mapping) else {}
    for row in rows.values() if isinstance(rows, Mapping) else []:
        if not isinstance(row, Mapping):
            continue
        path = str(row.get("path") or "").strip()
        budget = row.get("budget_bytes")
        if path and isinstance(budget, int):
            out[path] = budget
    return out


def _scan_lines(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    selected: list[tuple[int, str]] = []
    in_generated = False
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("<!-- BEGIN "):
            in_generated = True
            continue
        if stripped.startswith("<!-- END "):
            in_generated = False
            continue
        lowered = line.lower()
        if in_generated:
            if "bootstrap path" in lowered or "bootstrap sequence" in lowered:
                selected.append((index, line))
            continue
        if index <= 180:
            selected.append((index, line))
            continue
        if "bootstrap sequence" in lowered or "bootstrap path" in lowered or "bootstrap chain" in lowered:
            selected.append((index, line))
    return selected


def _stale_route_hits(text: str, *, require_entry_routes: bool = True) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for line_number, line in _scan_lines(text):
        for kind, pattern in FORBIDDEN_ROUTE_PATTERNS:
            if not pattern.search(line):
                continue
            allowed = _allowed_stale_route_context(line)
            hits.append(
                {
                    "line": line_number,
                    "kind": kind,
                    "allowed_as_drilldown": allowed,
                    "text": line.strip()[:260],
                }
            )
        lowered = line.lower()
        if (
            ("bootstrap chain" in lowered or "bootstrap path" in lowered or "bootstrap sequence" in lowered)
            and "kernel.py" in lowered
            and "--context-pack" not in line
        ):
            hits.append(
                {
                    "line": line_number,
                    "kind": "bootstrap_chain_omits_context_pack",
                    "allowed_as_drilldown": False,
                    "text": line.strip()[:260],
                }
            )
    if require_entry_routes and "--context-pack" not in text:
        hits.append(
            {
                "line": None,
                "kind": "missing_context_pack",
                "allowed_as_drilldown": False,
                "text": "Loaded entry surface does not mention --context-pack.",
            }
        )
    if require_entry_routes and "--navigation-metabolism" not in text:
        hits.append(
            {
                "line": None,
                "kind": "missing_navigation_metabolism",
                "allowed_as_drilldown": False,
                "text": "Loaded entry surface does not mention --navigation-metabolism.",
            }
        )
    return hits


def _scan_targets(repo_root: Path, *, include_generated_targets: bool = True) -> list[tuple[str, bool]]:
    targets: list[tuple[str, bool]] = [(rel, True) for rel in ENTRYPOINT_PATHS]
    if not include_generated_targets:
        return targets
    seen = {rel for rel, _ in targets}
    for pattern in GENERATED_ENTRYPOINT_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file():
                continue
            rel = str(path.relative_to(repo_root))
            if rel in seen:
                continue
            seen.add(rel)
            targets.append((rel, False))
    return targets


def build_entrypoint_health(
    repo_root: Path | str,
    *,
    include_generated_targets: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root)
    budget_by_path = _budgets(root)
    files: list[dict[str, Any]] = []
    forbidden_hits: list[dict[str, Any]] = []
    for rel, require_entry_routes in _scan_targets(
        root,
        include_generated_targets=include_generated_targets,
    ):
        path = root / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        byte_count = len(text.encode("utf-8"))
        budget = int(budget_by_path.get(rel, DEFAULT_BUDGETS.get(rel, 32768)))
        hits = _stale_route_hits(text, require_entry_routes=require_entry_routes)
        disallowed = [hit for hit in hits if not hit.get("allowed_as_drilldown")]
        posture = (
            "compact_seed" if rel == "AGENTS.override.md"
            else "shared_hub" if rel == "AGENTS.md"
            else "actor_adapter"
            if rel in {"CLAUDE.md", "CODEX.md"}
            else "generated_or_doctrine_skill"
        )
        record = {
            "path": rel,
            "bytes": byte_count,
            "budget": budget,
            "budget_status": "within_budget" if byte_count <= budget else "over_budget",
            "load_posture": posture,
            "first_contact_status": "valid" if not disallowed else "stale_route_hits",
            "stale_route_hit_count": len(hits),
            "allowed_drilldown_route_hit_count": len(hits) - len(disallowed),
            # Keep default health output compact. Full per-line route evidence
            # belongs in the dedicated entrypoint audit, while this first-contact
            # scanner needs only counts plus blocking hits.
            "stale_route_hits": disallowed[:5],
            "disallowed_stale_route_hit_count": len(disallowed),
        }
        files.append(record)
        for hit in disallowed:
            forbidden_hits.append({"path": rel, **hit})

    primary_over_budget_count = sum(
        1
        for file in files
        if file["budget_status"] == "over_budget" and file["load_posture"] != "generated_or_doctrine_skill"
    )
    generated_over_budget_count = sum(
        1
        for file in files
        if file["budget_status"] == "over_budget" and file["load_posture"] == "generated_or_doctrine_skill"
    )
    reported_files = [
        file
        for file in files
        if file["load_posture"] != "generated_or_doctrine_skill"
        or file["budget_status"] == "over_budget"
        or int(file.get("disallowed_stale_route_hit_count") or 0) > 0
    ]
    suppressed_files = [file for file in files if file not in reported_files]
    suppressed_by_posture: dict[str, int] = {}
    for file in suppressed_files:
        posture = str(file.get("load_posture") or "unknown")
        suppressed_by_posture[posture] = suppressed_by_posture.get(posture, 0) + 1
    stale_route_hit_count = sum(int(file.get("stale_route_hit_count") or 0) for file in files)
    allowed_drilldown_route_hit_count = sum(
        int(file.get("allowed_drilldown_route_hit_count") or 0)
        for file in files
    )
    summary = {
        "file_count": len(files),
        "reported_file_count": len(reported_files),
        "suppressed_file_count": len(suppressed_files),
        "suppressed_by_posture": suppressed_by_posture,
        "over_budget_count": primary_over_budget_count,
        "generated_or_doctrine_over_budget_count": generated_over_budget_count,
        "generated_target_scan_status": (
            "available" if include_generated_targets else "deferred_by_caller"
        ),
        "stale_route_hit_count": stale_route_hit_count,
        "allowed_drilldown_route_hit_count": allowed_drilldown_route_hit_count,
        "disallowed_stale_route_hit_count": len(forbidden_hits),
        "contract_status": "valid"
        if not forbidden_hits and primary_over_budget_count == 0
        else "entrypoint_debt",
    }
    return {
        "kind": "entrypoint_health",
        "schema_version": "entrypoint_health_v0",
        "first_contact_contract": {
            "normal_task": "--context-pack",
            "navigation_complaint": "--navigation-metabolism",
            "paper_lattice": "stable-slug drilldown only",
            "legacy_routes": "skill-find, paper-module, docs-route, raw help, and paper-lattice free text are drilldowns only",
        },
        "instruction_files": reported_files,
        "forbidden_first_contact_hits": forbidden_hits,
        "summary": summary,
    }


def _check_generated_region_markers(
    repo_root: Path, paths: list[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Lightweight marker-balance check on entrypoint files.

    A full content-vs-renderer drift check lives in
    system/lib/agent_entrypoint_audit.py::_detect_generated_block_drift; that
    requires loading expected_regions and running the bootstrap projection
    builder, which is too heavy for per-packet diagnostic surfacing. This
    helper checks the cheaper invariant: does each file expose balanced
    marker pairs for any region whose BEGIN appears? Empty body or unbalanced
    markers are a real diagnostic signal even when the deeper drift check is
    deferred.
    """
    findings: list[dict[str, Any]] = []
    seen = 0
    balanced = 0
    empty_body = 0
    for raw in paths:
        path = repo_root / raw
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for begin, end in GENERATED_BLOCK_MARKERS:
            begin_idx = text.find(begin)
            end_idx = text.find(end)
            if begin_idx == -1 and end_idx == -1:
                continue
            seen += 1
            if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
                findings.append({
                    "rule": "generated_block_markers_unbalanced",
                    "path": raw,
                    "marker": begin,
                    "severity": "error",
                })
                continue
            body = text[begin_idx + len(begin): end_idx].strip()
            if not body:
                findings.append({
                    "rule": "generated_block_empty_body",
                    "path": raw,
                    "marker": begin,
                    "severity": "warning",
                })
                empty_body += 1
                continue
            balanced += 1
    return findings, {
        "marker_pairs_seen": seen,
        "marker_pairs_balanced_with_body": balanced,
        "marker_pairs_empty_body": empty_body,
        "marker_pairs_unbalanced": len([f for f in findings if f["rule"] == "generated_block_markers_unbalanced"]),
    }


def _normalize_managed_region(text: str) -> str:
    out = str(text or "")
    for pattern, replacement in VOLATILE_MARKDOWN_PATTERNS:
        out = pattern.sub(replacement, out)
    lines = [
        line.rstrip()
        for line in out.strip().splitlines()
        if not line.startswith("_Shared paper-module sidecars are stale or incomplete;")
        and not line.startswith("_Sidecars stale;")
    ]
    return "\n".join(lines)


def _expected_managed_regions(repo_root: Path) -> tuple[dict[tuple[str, str, str], str], dict[str, Any]]:
    """Render expected managed entry regions without mutating disk."""
    try:
        cfg = load_agent_bootstrap_config(repo_root)
        context = build_bootstrap_projection_context(repo_root, config=cfg, refresh_orchestration=False)
        markers = cfg.get("markers") if isinstance(cfg.get("markers"), Mapping) else {}
        md_targets = cfg.get("markdown_targets") if isinstance(cfg.get("markdown_targets"), Mapping) else {}
        adapter_markers = markers.get("adapters") if isinstance(markers.get("adapters"), Mapping) else {}
        adapter_actor_map = cfg.get("adapter_actor_map") if isinstance(cfg.get("adapter_actor_map"), Mapping) else {}
        actor_lookup = {
            str(row.get("actor_id") or ""): row
            for row in (context.get("actor_context_surfaces") or [])
            if isinstance(row, Mapping) and str(row.get("actor_id") or "")
        }

        expected: dict[tuple[str, str, str], str] = {}
        agents_rel = str(md_targets.get("agents_md") or "AGENTS.md")
        begin = str(markers.get("begin") or "<!-- BEGIN agent_bootstrap_live -->")
        end = str(markers.get("end") or "<!-- END agent_bootstrap_live -->")
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
            md_rel = str(md_targets.get(adapter_key) or "").strip()
            a_begin = str(marker_pair.get("begin") or "").strip()
            a_end = str(marker_pair.get("end") or "").strip()
            if not md_rel or not a_begin or not a_end:
                continue
            actor_id = str(adapter_actor_map.get(adapter_key) or "").strip()
            adapter_role = (
                "claude_adapter" if adapter_key == "claude_md"
                else "codex_adapter" if adapter_key == "codex_md"
                else f"{adapter_key}_adapter"
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

        instruction = context.get("instruction_discovery") if isinstance(context.get("instruction_discovery"), Mapping) else {}
        if instruction:
            target = str(instruction.get("markdown_target") or "").strip()
            i_begin = str(instruction.get("begin_marker") or "").strip()
            i_end = str(instruction.get("end_marker") or "").strip()
            if target and i_begin and i_end and (repo_root / target).exists():
                seed_text = (repo_root / target).read_text(encoding="utf-8")
                _, rendered_instruction, _ = stabilize_instruction_discovery_target(
                    seed_text,
                    context.get("instruction_discovery_facts") or {},
                    context["bindings"],
                    bootstrap_sequence=context["bootstrap_sequence"] or None,
                    situation_routes=context["situation_routes"] or None,
                    system_facts_at_a_glance=context.get("system_facts_at_a_glance") or None,
                    agent_operating_packet=(
                        context.get("agent_operating_packet")
                        if isinstance(context.get("agent_operating_packet"), Mapping)
                        else None
                    ),
                )
                expected[(target, i_begin, i_end)] = rendered_instruction

        pm_begin, pm_end = PAPER_MODULE_MARKERS
        paper_module_markdown = render_paper_module_index_markdown(repo_root)
        pm_targets: list[str] = [agents_rel]
        for hint in PAPER_MODULE_PROJECTION_TARGET_HINTS:
            if hint == "agents_md":
                continue
            candidate = md_targets.get(hint)
            if candidate:
                pm_targets.append(str(candidate))
        pm_targets.extend(["CLAUDE.md", "CODEX.md"])
        seen_pm_targets: set[str] = set()
        for target in pm_targets:
            if not target or target in seen_pm_targets:
                continue
            seen_pm_targets.add(target)
            expected[(target, pm_begin, pm_end)] = paper_module_markdown

        expected[("AGENTS.md", ROUTING_BEGIN_MARKER, ROUTING_END_MARKER)] = render_routing_markdown(
            build_routing_payload(repo_root)
        )
        return expected, {"status": "available", "expected_region_count": len(expected)}
    except Exception as exc:  # pragma: no cover - defensive fallback for diagnostic surfacing
        return {}, {
            "status": "unavailable",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _check_generated_region_content_sync(
    repo_root: Path,
    paths: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_regions, expected_status = _expected_managed_regions(repo_root)
    if not expected_regions:
        return [], {
            "renderer_content_sync": "expected_regions_unavailable",
            **expected_status,
            "checked_region_count": 0,
            "matched_region_count": 0,
            "drift_region_count": 0,
            "missing_region_count": 0,
        }

    allowed_paths = set(paths)
    findings: list[dict[str, Any]] = []
    checked = 0
    matched = 0
    missing = 0
    drift = 0
    unbalanced = 0
    empty = 0
    for (rel, begin, end), expected in sorted(expected_regions.items()):
        if allowed_paths and rel not in allowed_paths:
            continue
        path = repo_root / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        checked += 1
        begin_idx = text.find(begin)
        end_idx = text.find(end)
        if begin_idx == -1 or end_idx == -1:
            missing += 1
            findings.append({
                "rule": "generated_region_missing",
                "path": rel,
                "marker": begin,
                "severity": "visible_debt",
            })
            continue
        if end_idx < begin_idx:
            unbalanced += 1
            findings.append({
                "rule": "generated_region_unbalanced",
                "path": rel,
                "marker": begin,
                "severity": "visible_debt",
            })
            continue
        body = text[begin_idx + len(begin): end_idx].strip()
        if not body:
            empty += 1
            findings.append({
                "rule": "generated_region_empty",
                "path": rel,
                "marker": begin,
                "severity": "visible_debt",
            })
            continue
        if _normalize_managed_region(body) != _normalize_managed_region(expected):
            drift += 1
            findings.append({
                "rule": "generated_region_renderer_drift",
                "path": rel,
                "marker": begin,
                "severity": "visible_debt",
            })
            continue
        matched += 1

    status = "matched" if checked > 0 and not findings else "drift"
    try:
        routing_projection_status = routing_status(repo_root)
    except Exception as exc:  # pragma: no cover - defensive diagnostic fallback
        routing_projection_status = {
            "status": "unavailable",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return findings, {
        "renderer_content_sync": status,
        **expected_status,
        "checked_region_count": checked,
        "matched_region_count": matched,
        "drift_region_count": drift,
        "missing_region_count": missing,
        "unbalanced_region_count": unbalanced,
        "empty_region_count": empty,
        "routing_source_coupling": routing_projection_status.get("source_coupling"),
        "routing_source_worktree_state": routing_projection_status.get("source_worktree_state"),
    }


def _check_generated_region_source_coupling_receipt(repo_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fast structural receipt for routine first-contact packets.

    Full renderer-vs-markdown diffing renders bootstrap, paper-module, and routing
    projections. That is appropriate for explicit diagnostic queries, but too
    expensive as a routine side effect of selected structural lanes. This receipt
    keeps the landing-critical routing source-coupling state visible and points
    at the full checker for renderer drift evidence.
    """
    try:
        from system.lib.routing_projection import routing_fast_source_coupling_status

        routing_projection_status = routing_fast_source_coupling_status(repo_root)
    except Exception as exc:  # pragma: no cover - defensive diagnostic fallback
        routing_projection_status = {
            "status": "unavailable",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return [], {
        "renderer_content_sync": "deferred_structural_context",
        "status": "routing_source_coupling_only",
        "checked_region_count": 0,
        "matched_region_count": 0,
        "drift_region_count": 0,
        "missing_region_count": 0,
        "unbalanced_region_count": 0,
        "empty_region_count": 0,
        "full_renderer_check_deferred": True,
        "full_renderer_check_reason": (
            "Structural-only entry/context triggers carry marker balance and routing source-coupling "
            "without rendering all managed regions inside the routine first-contact packet."
        ),
        "full_renderer_check_command": (
            "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py; "
            "./repo-python tools/meta/factory/build_routing_projection.py --check"
        ),
        "routing_source_coupling": routing_projection_status.get("source_coupling")
        if isinstance(routing_projection_status, Mapping)
        else None,
        "routing_source_worktree_state": routing_projection_status.get("source_worktree_state")
        if isinstance(routing_projection_status, Mapping)
        else None,
    }


_ENTRY_SURFACE_DIAGNOSTIC_TRIGGERS = (
    "agents.md",
    "claude.md",
    "codex.md",
    "agents.override.md",
    "entry budget",
    "entry-budget",
    "entrypoint",
    "entry surface",
    "entry-surface",
    "generated region",
    "generated-region",
    "generated projection",
    "generated-projection",
    "projection source",
    "source projection",
    "source coupling",
    "source-coupling",
    "source-worktree",
    "source inputs",
    "dirty source",
    "instruction file",
    "instruction-file",
    "compression policy",
    "compression-policy",
    "commit policy",
    "commit-policy",
    "startup hook",
    "first contact",
    "first-contact",
    "route health",
    "stale route",
)

_ENTRY_SURFACE_FULL_CONTENT_SYNC_TRIGGERS = (
    "generated region",
    "generated-region",
    "generated projection",
    "generated-projection",
    "projection source",
    "source projection",
    "source coupling",
    "source-coupling",
    "source-worktree",
    "source inputs",
    "dirty source",
)


# Action-autonomy phrases — when the operator's task carries one of these, the
# runtime entry packet must surface the **active** governing standard rule
# (std_agent_entry_surface.json::common_sense_helpfulness_floor::action_over_pointless_inaction)
# as operational pressure, not only the provisional axiom-candidate pressure
# emitted by `system.lib.standard_option_surface.candidate_runtime_pressure_rows`.
# Candidate pressure carries authority_posture=candidate_not_active_doctrine;
# without an active-standard diagnostic, Type A reading the entry packet sees
# only "provisional candidate" framing for what is in fact a settled rule of
# the entry-surface standard. The phrase list mirrors the matcher whitelist in
# `_RUNTIME_PRESSURE_AUTONOMY_PHRASES` so doctrine→adapter→runtime stays in
# sync; both sources should change together.
_ACTION_AUTONOMY_DIAGNOSTIC_TRIGGERS = (
    "permission gate",
    "permission gates",
    "permission-gated",
    "permission-gating",
    "permission ceremony",
    "approval gate",
    "approval gating",
    "approval fatigue",
    "authorize next",
    "authorize the next",
    "your call",
    "redirect or proceed",
    "micro slice",
    "micro slices",
    "micro-slice",
    "micro-slices",
    "micro-sliced",
    "micro-slicing",
    "largest coherent",
    "coherent wave",
    "coherent verified wave",
    "safe wave",
    "autonomous seed",
    "seed should work",
    "work for anything",
    "twiddling thumbs",
    "twiddle thumbs",
    "action autonomy",
    "agent autonomy",
)


def _structural_trigger_rows(triggers: Sequence[Mapping[str, Any] | str] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trigger in triggers or []:
        if isinstance(trigger, Mapping):
            trigger_id = str(trigger.get("trigger_id") or trigger.get("id") or "").strip()
            if not trigger_id:
                continue
            row = {"trigger_id": trigger_id}
            for key in (
                "recognized_situation",
                "selected_lane_id",
                "selected_kind_ids",
                "selected_row_ids",
                "source",
                "reason",
            ):
                value = trigger.get(key)
                if value not in (None, "", [], {}):
                    row[key] = value
            rows.append(row)
        else:
            trigger_id = str(trigger or "").strip()
            if trigger_id:
                rows.append({"trigger_id": trigger_id})
    return rows


def project_entry_surface_diagnostics(
    repo_root: Path,
    query: str,
    *,
    structural_triggers: Sequence[Mapping[str, Any] | str] | None = None,
    content_sync_mode: str = "auto",
) -> dict[str, Any]:
    """Project entrypoint_health into a soft-pressure diagnostic packet section.

    First proof case for the entry-surface diagnostic projection family per
    cap_quick_type_a_skill_candidate_per_kind_diagnost_ae2605ea5c9d. Triggers when
    the task query mentions entry-surface concerns (AGENTS.md, CLAUDE.md, entry
    budget, generated regions, instruction files, compression/commit policy,
    first contact, stale routes), or when a caller supplies an already-selected
    structural route context such as a navigation/projection control lane.
    Returns an empty triggered=False payload when neither applies.

    Severity is `soft_pressure` / `visible_debt` by default — these diagnostics are
    not hard gates unless a governing standard explicitly says otherwise. The
    projection consumes existing checker output (`build_entrypoint_health`) rather
    than reinventing budget/route logic, per the diagnostic-projection pattern of
    extending compliance/observability ledgers instead of greenfielding a parallel
    source of truth.
    """
    query_str = str(query or "")
    structural_rows = _structural_trigger_rows(structural_triggers)
    if not query_str.strip() and not structural_rows:
        return {"rows": [], "count": 0, "triggered": False}
    q_lower = query_str.lower()
    matched_triggers = [t for t in _ENTRY_SURFACE_DIAGNOSTIC_TRIGGERS if t in q_lower]
    matched_autonomy_phrases = [
        t for t in _ACTION_AUTONOMY_DIAGNOSTIC_TRIGGERS if t in q_lower
    ]
    if not matched_triggers and not structural_rows and not matched_autonomy_phrases:
        return {"rows": [], "count": 0, "triggered": False}
    normalized_content_sync_mode = str(content_sync_mode or "auto").strip().lower()
    if normalized_content_sync_mode not in {"auto", "full", "source_coupling_only"}:
        normalized_content_sync_mode = "auto"
    matched_full_content_sync_triggers = [
        t for t in _ENTRY_SURFACE_FULL_CONTENT_SYNC_TRIGGERS if t in q_lower
    ]
    use_full_content_sync = (
        normalized_content_sync_mode == "full"
        or (
            normalized_content_sync_mode == "auto"
            and bool(matched_full_content_sync_triggers)
        )
    )
    health: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    files: list[Any] = []
    if matched_triggers:
        health = build_entrypoint_health(repo_root)
        summary = health.get("summary") or {}
        files = health.get("instruction_files") or []
    rows: list[dict[str, Any]] = []
    over_budget = int(summary.get("over_budget_count") or 0)
    if over_budget > 0:
        target_surfaces = sorted(
            str(f.get("path") or "")
            for f in files
            if f.get("budget_status") == "over_budget"
            and f.get("load_posture") != "generated_or_doctrine_skill"
        )
        rows.append({
            "diagnostic_id": "entry_surface_budget_pressure",
            "target_surfaces": target_surfaces,
            "severity": "soft_pressure",
            "observed_state": {
                "over_budget_count": over_budget,
                "contract_status": summary.get("contract_status"),
                "generated_or_doctrine_over_budget_count": summary.get("generated_or_doctrine_over_budget_count"),
            },
            "recommended_action": "Compress new prose into existing entry surfaces; avoid expanding load-bearing instruction files unless doctrine-critical.",
            "governing_standard_ref": "codex/standards/std_agent_entry_surface.json::compression_budgets",
            "checker_module_ref": "system/lib/entrypoint_health.py::build_entrypoint_health",
            "is_hard_gate": False,
        })
    forbidden_count = int(summary.get("disallowed_stale_route_hit_count") or 0)
    if forbidden_count > 0:
        forbidden_paths = sorted({
            str(h.get("path") or "")
            for h in (health.get("forbidden_first_contact_hits") or [])
            if isinstance(h, dict)
        })
        rows.append({
            "diagnostic_id": "entry_surface_forbidden_first_contact_routes",
            "target_surfaces": forbidden_paths,
            "severity": "visible_debt",
            "observed_state": {
                "disallowed_stale_route_hit_count": forbidden_count,
                "first_contact_contract": health.get("first_contact_contract"),
            },
            "recommended_action": "Replace forbidden first-contact routes with the contracted drilldowns or mark as explicit drilldown-only context.",
            "governing_standard_ref": "codex/standards/std_agent_entry_surface.json::entry_affordance_contract",
            "checker_module_ref": "system/lib/entrypoint_health.py::build_entrypoint_health",
            "is_hard_gate": False,
        })
    marker_findings, marker_stats = _check_generated_region_markers(repo_root, ENTRYPOINT_PATHS)
    if use_full_content_sync:
        content_findings, content_stats = _check_generated_region_content_sync(repo_root, ENTRYPOINT_PATHS)
    else:
        content_findings, content_stats = _check_generated_region_source_coupling_receipt(repo_root)
    if marker_stats["marker_pairs_seen"] > 0:
        marker_balance_ok = marker_stats["marker_pairs_unbalanced"] == 0 and marker_stats["marker_pairs_empty_body"] == 0
        content_sync_status = str(content_stats.get("renderer_content_sync") or "unknown")
        content_sync_ok = content_sync_status == "matched"
        content_sync_deferred = bool(content_stats.get("full_renderer_check_deferred")) or content_sync_status.startswith("deferred")
        routing_source_coupling = content_stats.get("routing_source_coupling")
        routing_source_coupling_ok = (
            not isinstance(routing_source_coupling, Mapping)
            or routing_source_coupling.get("status") == "clean_source_inputs_and_artifacts"
        )
        routing_source_coupling_status = (
            str(routing_source_coupling.get("status") or "")
            if isinstance(routing_source_coupling, Mapping)
            else ""
        )
        routing_source_dirty = (
            isinstance(routing_source_coupling, Mapping)
            and (
                bool(routing_source_coupling.get("dirty_source_paths") or [])
                or routing_source_coupling_status
                in {
                    "artifact_matches_dirty_source_inputs",
                    "dirty_source_inputs_and_artifact_drift",
                }
            )
        )
        generated_regions_match: bool | None = None if content_sync_deferred else marker_balance_ok and content_sync_ok
        generated_region_landing_safe: bool | None = (
            None
            if content_sync_deferred
            else marker_balance_ok and content_sync_ok and routing_source_coupling_ok
        )
        if content_sync_deferred and routing_source_dirty:
            generated_region_action = (
                "Structural context surfaced marker balance and routing source-coupling without a full renderer diff, "
                "and routing projection source inputs are dirty; commit the source inputs with generated routing targets, "
                "or leave generated targets out of the scoped landing."
            )
        elif content_sync_deferred and not routing_source_coupling_ok:
            generated_region_action = (
                "Structural context surfaced marker balance and routing source-coupling without a full renderer diff, "
                "and routing projection artifacts are stale against clean source inputs; run the owning projection "
                "builder/check before trusting generated routing targets."
            )
        elif content_sync_deferred:
            generated_region_action = (
                "Structural context surfaced marker balance and routing source-coupling without a full renderer diff; "
                "run the deeper checker before making generated entry docs authoritative."
            )
        elif marker_balance_ok and content_sync_ok and not routing_source_coupling_ok and routing_source_dirty:
            generated_region_action = (
                "Generated regions match current renderers, but routing projection source inputs are dirty; "
                "commit the source inputs with generated routing targets, or leave generated targets out of the scoped landing."
            )
        elif marker_balance_ok and content_sync_ok and not routing_source_coupling_ok:
            generated_region_action = (
                "Generated regions match current renderers, but routing projection artifacts are stale against clean source inputs; "
                "run the owning projection builder/check before trusting generated routing targets."
            )
        elif marker_balance_ok and content_sync_ok:
            generated_region_action = (
                "Generated regions are structurally intact and match their current renderers; compress only new prose outside managed blocks."
            )
        elif routing_source_dirty:
            generated_region_action = (
                "Generated regions are missing, structurally invalid, or differ from renderer output, and routing projection source inputs are dirty; "
                "commit the source inputs with generated routing targets, or leave generated targets out of the scoped landing."
            )
        elif routing_source_coupling_status == "artifact_drift_from_clean_sources":
            generated_region_action = (
                "Generated regions are missing, structurally invalid, or differ from renderer output while routing source inputs are clean; "
                "run ./repo-python tools/meta/factory/build_agent_bootstrap_projection.py and ./repo-python tools/meta/factory/build_routing_projection.py "
                "before trusting compressed entry docs."
            )
        else:
            generated_region_action = (
                "Generated regions are missing, structurally invalid, or differ from renderer output; run ./repo-python "
                "tools/meta/factory/build_agent_bootstrap_projection.py and ./repo-python tools/meta/factory/build_routing_projection.py "
                "before trusting compressed entry docs."
            )
        rows.append({
            "diagnostic_id": "entry_surface_generated_region_sync",
            "target_surfaces": ENTRYPOINT_PATHS,
            "severity": "informational" if generated_region_landing_safe is True else "visible_debt",
            "observed_state": {
                "generated_region_marker_balance_ok": marker_balance_ok,
                "marker_balance_check": marker_stats,
                "marker_findings": marker_findings,
                "generated_regions_match": generated_regions_match,
                "generated_regions_match_status": "deferred" if content_sync_deferred else "matched" if generated_regions_match else "drift",
                "generated_region_landing_safe": generated_region_landing_safe,
                "generated_region_landing_safe_status": (
                    "deferred"
                    if content_sync_deferred
                    else "safe"
                    if generated_region_landing_safe
                    else "unsafe"
                ),
                "renderer_content_sync": content_sync_status,
                "renderer_content_sync_deferred": content_sync_deferred,
                "content_sync_mode": "full" if use_full_content_sync else "source_coupling_only",
                "full_content_sync_triggered_by": matched_full_content_sync_triggers,
                "renderer_content_check": content_stats,
                "renderer_content_findings": content_findings[:8],
                "renderer_content_sync_checker": "system/lib/entrypoint_health.py::_check_generated_region_content_sync",
            },
            "recommended_action": generated_region_action,
            "governing_standard_ref": "codex/standards/std_agent_entry_surface.json::compression_via_projection_contract",
            "checker_module_ref": "system/lib/entrypoint_health.py::_check_generated_region_markers",
            "deeper_checker_ref": "tools/meta/factory/check_agent_bootstrap_projection.py + tools/meta/factory/build_routing_projection.py --check",
            "is_hard_gate": False,
        })
    if matched_autonomy_phrases:
        rows.append({
            "diagnostic_id": "action_autonomy_runtime_pressure",
            "target_surfaces": list(ENTRYPOINT_PATHS),
            "severity": "operational_pressure",
            "observed_state": {
                "matched_autonomy_phrases": matched_autonomy_phrases[:6],
                "operator_voice_2026_05_07": (
                    "do not get trapped in tiny 'authorize next wave?' loops; "
                    "safety boundaries route action, they do not collapse the agent "
                    "into permission-gated micro-slices."
                ),
            },
            "one_line_rule": (
                "Take the largest coherent verified action inside the trust envelope "
                "before permission-gating; only ask when a real blast-radius boundary is hit."
            ),
            "anti_pattern": (
                "Ending safe read-only / path-scoped waves with 'authorize next wave?' / "
                "'your call' / 'redirect or proceed' / 'should I scope a cap_quick?'."
            ),
            "allowed_stop_conditions": [
                "destructive or irreversible action",
                "secret-handling or private disclosure",
                "publication / remote sync boundary",
                "non-isolatable concurrent-owner conflict",
                "unsafe generated-projection ownership",
                "safety-changing validation failure",
            ],
            "recommended_action": (
                "Name the largest coherent useful wave available now; if it is safe and "
                "in-scope, run it; if a smaller slice is chosen, state the blocker that "
                "made the larger wave unsafe."
            ),
            "governing_standard_ref": (
                "codex/standards/std_agent_entry_surface.json::common_sense_helpfulness_floor::action_over_pointless_inaction"
            ),
            "candidate_pressure_complement": (
                "system/lib/standard_option_surface.py::candidate_runtime_pressure_rows "
                "elevates whitelisted axiom candidates (operator_autonomy_pressure_phrase) "
                "as supplemental shape pressure; this row carries the active governing "
                "rule itself."
            ),
            "checker_module_ref": "system/lib/entrypoint_health.py::project_entry_surface_diagnostics",
            "is_hard_gate": False,
        })
    if matched_autonomy_phrases and matched_triggers:
        trigger_source = "query_and_autonomy_phrase_and_structural_context" if structural_rows else "query_and_autonomy_phrase"
    elif matched_autonomy_phrases and structural_rows:
        trigger_source = "autonomy_phrase_and_structural_context"
    elif matched_autonomy_phrases:
        trigger_source = "autonomy_phrase"
    elif matched_triggers and structural_rows:
        trigger_source = "query_and_structural_context"
    elif matched_triggers:
        trigger_source = "query"
    else:
        trigger_source = "structural_context"
    return {
        "rows": rows,
        "count": len(rows),
        "triggered": True,
        "matched_triggers": matched_triggers,
        "matched_autonomy_phrases": matched_autonomy_phrases,
        "structural_triggers": structural_rows,
        "trigger_source": trigger_source,
        "severity_default": "soft_pressure",
        "non_blocking": True,
        "non_blocking_warning": "Entry-surface diagnostics are soft pressure / visible debt; they do not hard-gate edits unless a governing standard says otherwise.",
        "source_module": "system/lib/entrypoint_health.py::project_entry_surface_diagnostics",
        "underlying_checker": "system/lib/entrypoint_health.py::build_entrypoint_health",
        "diagnostic_family": "entry_surface_diagnostics",
        "diagnostic_family_owner_cap": "cap_quick_type_a_skill_candidate_per_kind_diagnost_ae2605ea5c9d",
        "candidate_pressure_refs": [
            "axiom_candidate_cybernetic_projection_feedback",
        ],
        "candidate_pressure_relationship": "This diagnostic family is one operational instance of the candidate axiom currently surfaced in candidate_runtime_pressure: action-bearing surfaces (entry-surface instruction files) project their state for cross-surface human/agent agreement; budget pressure + generated-region sync are the substrate-level facts that make the projection trustworthy.",
    }
