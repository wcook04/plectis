"""
[PURPOSE]
- Teleology: Resolve the repo's live bootstrap state from disk and project it into AGENTS markdown blocks plus JSON sidecars that other agents can consume without rediscovery.
- Teleology: Resolve the repo's live bootstrap state from disk and project it into AGENTS / adapter / discovery-seed markdown plus JSON sidecars that other agents can consume without rediscovery.
- Mechanism: Loads agent_bootstrap.json defaults, reads current pipeline/control-plane artifacts, normalizes bootstrap route tables, renders the live markdown blocks, and writes the JSON projection pair when requested.

[INTERFACE]
- Exports: normalize_minimum_read_sets, normalize_bootstrap_sequence, normalize_situation_routes, normalize_actor_context_surfaces, normalize_type_a_convergence_contract, normalize_runtime_control_plane, normalize_instruction_discovery, resolve_instruction_discovery_facts, find_pipeline_state_path, load_agent_bootstrap_config, resolve_live_bindings, render_live_markdown, render_instruction_discovery_markdown, build_live_payload, build_injection_strip, replace_marked_region, extract_marked_region, run_projection, try_refresh_after_controller_write.
- Reads: codex/doctrine/agent_bootstrap.json plus pipeline, factory, system-map, doctrine-runtime, orchestration, and documentation-route-focus artifacts under the repo root.
- Writes: run_projection() writes JSON sidecars and refreshes managed regions in AGENTS.md, adapters, and the compact instruction-discovery seed when configured.

[FLOW]
- Orders: load_agent_bootstrap_config() defines defaults -> resolve_live_bindings() snapshots runtime state from disk -> render_live_markdown()/render_instruction_discovery_markdown()/build_live_payload()/build_injection_strip() materialize projection variants -> run_projection() writes files and refreshes marked regions.
- When-needed: Open when the AGENTS live bootstrap projection needs to be regenerated or when an agent must trace which disk artifacts feed the current bootstrap block.
- Escalates-to: codex/doctrine/agent_bootstrap.json; tools/meta/factory/build_agent_bootstrap_projection.py; system/lib/phase_activation.py::load_explicit_active_phase
- Navigation-group: kernel_lib

[DEPENDENCIES]
- json + pathlib + datetime: Load and write projection artifacts with UTC timestamps.
- system.lib.phase_activation: Resolve the explicitly active phase before falling back to pipeline-state discovery.

[CONSTRAINTS]
- Guarantee: Projection helpers degrade to default config or missing-value placeholders instead of raising on absent optional artifacts.
- Non-goal: This module does not decide bootstrap policy; it projects the policy and runtime state already defined elsewhere.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.agent_operating_packet import (
    DEFAULT_TARGET_REL as AGENT_OPERATING_PACKET_REL,
    build_agent_operating_packet,
    build_agent_operating_packet_strip,
    render_agent_operating_packet_markdown,
)
from system.lib.paper_modules import load_paper_module_runtime

DEFAULT_MARKERS = (
    "<!-- BEGIN agent_bootstrap_live -->",
    "<!-- END agent_bootstrap_live -->",
)

PAPER_MODULE_MARKERS = (
    "<!-- BEGIN paper_module_index -->",
    "<!-- END paper_module_index -->",
)

PAPER_MODULE_INDEX_REL = "codex/doctrine/paper_modules/_index.json"
PAPER_MODULE_STANDARD_REL = "codex/standards/std_paper_module.json"
PAPER_MODULE_PROJECTION_TARGET_HINTS = ("agents_md", "claude_md", "codex_md")
PAPER_MODULE_DEFAULT_TLDR_BUDGET_CHARS = 96
PAPER_MODULE_DEFAULT_REGION_BUDGET_CHARS = 2400
PAPER_MODULE_DEFAULT_MAX_ROWS = 8
FACTORY_STATE_LIVE_TTL_DAYS = 7
PAPER_MODULE_DEFAULT_PINNED_SLUGS = (
    "raw_seed_substrate",
    "raw_seed_metabolism",
    "system_constitution_seed",
)
AGENTS_SITUATION_ROUTE_RENDER_LIMIT = 8
AGENTS_HIDDEN_ACTOR_DELIVERY_ANCHOR_LIMIT: int | None = None
SYSTEM_FACTS_AT_A_GLANCE_REL = "state/system_atlas/system_facts_at_a_glance.json"
SYSTEM_FACTS_AT_A_GLANCE_MD_REL = "docs/system_atlas/generated_system_facts_at_a_glance.md"
ROUTE_TARGET_CONTACT_RELATIONS = frozenset({"audits", "routes_to", "validates"})
ROUTE_TARGET_OPERATIONAL_RELATIONS = frozenset(
    {"audits", "implements", "projects", "routes_to", "validates"}
)


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _factory_event_times(factory_state: Mapping[str, Any] | None) -> list[datetime]:
    if not isinstance(factory_state, Mapping):
        return []
    candidates: list[Any] = [
        factory_state.get("last_run"),
        factory_state.get("last_materialize"),
        factory_state.get("last_stage_apply"),
        factory_state.get("last_merge"),
    ]
    for job in factory_state.get("jobs_completed") or []:
        if isinstance(job, Mapping):
            candidates.append(job.get("finished_at"))
    for err in factory_state.get("errors") or []:
        if isinstance(err, Mapping):
            candidates.append(err.get("time"))
    return [dt for dt in (_parse_iso_datetime(item) for item in candidates) if dt is not None]


def _factory_state_projection(
    repo_root: Path,
    factory_state: Mapping[str, Any] | None,
    factory_state_path: Path | None,
) -> dict[str, Any]:
    if not isinstance(factory_state, Mapping) or not factory_state:
        return {
            "factory_state_rel": _rel(repo_root, factory_state_path) if factory_state_path else None,
            "factory_stage": None,
            "factory_last_run": None,
            "factory_state_freshness": "missing",
            "factory_state_role": "missing",
            "factory_state_live": False,
        }
    times = _factory_event_times(factory_state)
    newest = max(times) if times else None
    stage_observed_at = _parse_iso_datetime(factory_state.get("last_run")) or newest
    age_days: int | None = None
    if stage_observed_at is not None:
        age_days = max(0, int((datetime.now(timezone.utc) - stage_observed_at).total_seconds() // 86400))
    if age_days is None:
        freshness = "undated_snapshot"
        role = "historical_snapshot"
        live = False
    elif age_days > FACTORY_STATE_LIVE_TTL_DAYS:
        freshness = "stale_historical_snapshot"
        role = "historical_snapshot"
        live = False
    else:
        freshness = "recent_runtime_snapshot"
        role = "runtime_signal"
        live = True
    return {
        "factory_state_rel": _rel(repo_root, factory_state_path) if factory_state_path else None,
        "factory_stage": factory_state.get("stage"),
        "factory_last_run": factory_state.get("last_run"),
        "factory_last_event_at": newest.isoformat() if newest is not None else None,
        "factory_stage_observed_at": stage_observed_at.isoformat() if stage_observed_at is not None else None,
        "factory_state_age_days": age_days,
        "factory_state_freshness": freshness,
        "factory_state_role": role,
        "factory_state_live": live,
        "factory_stage_is_current": live,
    }


def _factory_state_markdown_line(bindings: Mapping[str, Any], *, adapter: bool = False) -> str | None:
    stage = bindings.get("factory_stage")
    rel = bindings.get("factory_state_rel") or "tools/meta/factory/factory_state.json"
    if not stage:
        return f"- Factory state: `{bindings.get('factory_state_freshness') or 'missing'}`" if adapter else f"- `{rel}` — factory state unavailable"
    freshness = bindings.get("factory_state_freshness") or "unknown_freshness"
    role = bindings.get("factory_state_role") or "unknown_role"
    last_run = bindings.get("factory_last_run") or "unknown"
    age = bindings.get("factory_state_age_days")
    age_text = f", age `{age}d`" if isinstance(age, int) else ""
    if adapter:
        return (
            f"- Factory state: `{role}` / `{freshness}` — stage `{stage}`, "
            f"last_run `{last_run}`{age_text}"
        )
    return (
        f"- `{rel}` — `{role}` / `{freshness}`; stage `{stage}`, "
        f"last_run `{last_run}`{age_text}"
    )

DEFAULT_COMPACT_COMMAND_SURFACE = {
    "max_flags_per_group": 6,
    "group_entrypoints": {
        "navigate": {
            "command": "python3 kernel.py --orient-task \"<topic>\"",
            "why": "Turn a vague task into a bounded working set before opening raw files.",
        },
        "planning": {
            "command": "python3 kernel.py --phase [<phase>]",
            "why": "Recover the active phase packet and current wave contract.",
        },
        "observe": {
            "command": "python3 kernel.py --launch-observe --plan <plan.json> --bridge --provider chatgpt --bridge-workers 3 --detach",
            "why": "Launch a detached grouped observe run after the controller has already chosen the groups.",
        },
        "apply": {
            "command": "python3 kernel.py --apply <ops.json> [--live]",
            "why": "Route bounded mutations through the governed apply surface instead of ad hoc edits.",
        },
        "infrastructure": {
            "command": "python3 kernel.py --build status",
            "why": "Inspect generated-surface staleness before trusting derived artifacts.",
        },
    },
}

DEFAULT_INSTRUCTION_DISCOVERY = {
    "provider": "codex",
    "markdown_target": "AGENTS.override.md",
    "begin_marker": "<!-- BEGIN instruction_discovery_live -->",
    "end_marker": "<!-- END instruction_discovery_live -->",
    "seed_path": "AGENTS.override.md",
    "deep_hub_path": "AGENTS.md",
    "adapter_paths": ["CODEX.md", "CLAUDE.md"],
    "size_watch_paths": ["AGENTS.override.md", "AGENTS.md", "CODEX.md", "CLAUDE.md"],
    "project_doc_max_bytes_default": 36045,
    "compact_seed_budget_bytes": 17600,
    "official_source": "https://developers.openai.com/codex/guides/agents-md#how-codex-discovers-guidance",
}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _hidden_actor_delivery_anchor_rows(
    situations: list[Mapping[str, Any]],
    rendered_situations: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Preserve actor-delivery receipts for delivered routes that fall outside the compact route row budget.
    - Mechanism: Emits only the minimal required-token Rosetta anchors for hidden deliver_to_cold_start rows.
    - Guarantee: Excludes the state-axis route because it has a dedicated compact projection elsewhere.
    """
    rendered_ids = {str(row.get("situation_id") or "").strip() for row in rendered_situations}
    out: list[Mapping[str, Any]] = []
    for row in situations:
        situation_id = str(row.get("situation_id") or "").strip()
        if (
            not situation_id
            or situation_id in rendered_ids
            or situation_id == "system_state_axis_overview"
        ):
            continue
        delivery = row.get("actor_delivery") if isinstance(row.get("actor_delivery"), Mapping) else {}
        if delivery.get("decision") != "deliver_to_cold_start":
            continue
        required_tokens = [
            str(token).strip()
            for token in (delivery.get("required_tokens") or [])
            if str(token).strip()
        ]
        if required_tokens:
            out.append(row)
    if AGENTS_HIDDEN_ACTOR_DELIVERY_ANCHOR_LIMIT is None:
        return out
    return out[:AGENTS_HIDDEN_ACTOR_DELIVERY_ANCHOR_LIMIT]


def load_system_facts_at_a_glance(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load the generated System Atlas facts card that compact agent-entry and prompt surfaces reuse.
    - Mechanism: Reads state/system_atlas/system_facts_at_a_glance.json and returns an explicit unavailable packet when the projection has not been built.
    - Guarantee: Does not raise on missing or malformed generated state.
    """
    path = repo_root / SYSTEM_FACTS_AT_A_GLANCE_REL
    data = _safe_load_json(path)
    if not data:
        return {
            "kind": "system_facts_at_a_glance",
            "schema_version": "system_facts_at_a_glance_v1",
            "status": "missing",
            "source_refs": [
                SYSTEM_FACTS_AT_A_GLANCE_REL,
                SYSTEM_FACTS_AT_A_GLANCE_MD_REL,
                "tools/meta/factory/build_system_atlas.py",
            ],
            "summary": {},
            "facts": [],
            "prompt_insert": {
                "title": "System facts at-a-glance",
                "source_json": SYSTEM_FACTS_AT_A_GLANCE_REL,
                "source_markdown": SYSTEM_FACTS_AT_A_GLANCE_MD_REL,
                "text": (
                    "System facts projection missing. Ask Type A to run "
                    "./repo-python tools/meta/factory/build_system_atlas.py before relying on atlas-backed facts."
                ),
            },
        }
    return data


def render_system_facts_at_a_glance(
    facts: Mapping[str, Any] | None,
    *,
    max_rows: int = 5,
    heading: str = "**System facts at a glance:**",
    compact: bool = False,
) -> list[str]:
    """
    [ACTION]
    - Teleology: Render the compact facts card into bootstrap markdown without copying the whole System Atlas.
    - Mechanism: Emits one source line plus the first few fact rows; JSON/Markdown sidecars remain the expansion surface.
    - Guarantee: Returns an empty list only when no facts payload is supplied.
    """
    if not isinstance(facts, Mapping) or not facts:
        return []
    rows = [row for row in list(facts.get("facts") or []) if isinstance(row, Mapping)]
    prompt_insert = facts.get("prompt_insert") if isinstance(facts.get("prompt_insert"), Mapping) else {}
    source_json = str(prompt_insert.get("source_json") or SYSTEM_FACTS_AT_A_GLANCE_REL)
    source_markdown = str(prompt_insert.get("source_markdown") or SYSTEM_FACTS_AT_A_GLANCE_MD_REL)
    if compact:
        return [
            "",
            heading,
            f"- Source: `{source_markdown}`; JSON `{source_json}`. Projection, not authority.",
            "- Defaults: A/B=substrate authority; availability ladder; Type A verifies dynamic/private state; residuals via WorkItems, Prompt Ledger, or up-prop.",
        ]
    out = [
        "",
        heading,
        f"- Source: `{source_markdown}` / `{source_json}`; authority posture `{facts.get('authority_posture') or 'generated projection'}`.",
    ]
    if not rows:
        out.append("- Projection unavailable; run `./repo-python tools/meta/factory/build_system_atlas.py`.")
        return out
    for row in rows[: max(1, max_rows)]:
        label = str(row.get("label") or row.get("id") or "").strip()
        summary = str(row.get("summary") or "").strip()
        if len(summary) > 170:
            summary = summary[:167].rstrip() + "..."
        out.append(f"- `{row.get('id')}` — {label}: {summary}")
    return out


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _existing_rel_from_binding(repo_root: Path, raw_path: Any) -> str | None:
    rel = str(raw_path or "").strip()
    if not rel:
        return None
    path = Path(rel)
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        return None
    return _rel(repo_root, path)


def _normalize_string_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text and text not in values:
            values.append(text)
    return values


def _route_target_chip(target: Mapping[str, Any]) -> str | None:
    kind = str(target.get("kind") or "").strip()
    ref = str(target.get("ref") or "").strip()
    if not kind or not ref:
        return None
    chip = f"`{kind}:{ref}`"
    relation = str(target.get("relation") or "").strip()
    if relation:
        chip += f"[{relation}]"
    return chip


def _route_target_projection_bits(route_targets: list[Any]) -> tuple[list[str], int]:
    valid_targets = [target for target in route_targets if isinstance(target, Mapping)]
    if not valid_targets:
        return [], 0
    selected: list[Mapping[str, Any]] = [valid_targets[0]]
    contact_target = next(
        (
            target
            for target in valid_targets[1:]
            if str(target.get("relation") or "").strip() in ROUTE_TARGET_CONTACT_RELATIONS
        ),
        None,
    )
    operational_target = contact_target or next(
        (
            target
            for target in valid_targets[1:]
            if str(target.get("relation") or "").strip() in ROUTE_TARGET_OPERATIONAL_RELATIONS
        ),
        None,
    )
    if operational_target is not None:
        selected.append(operational_target)
    target_bits = [chip for target in selected if (chip := _route_target_chip(target))]
    return target_bits, max(0, len(valid_targets) - len(selected))


def _load_paper_module_projection_shape(repo_root: Path) -> dict[str, Any]:
    std = _safe_load_json(repo_root / PAPER_MODULE_STANDARD_REL) or {}
    contract = (
        std.get("bootstrap_projection_contract")
        if isinstance(std.get("bootstrap_projection_contract"), Mapping)
        else {}
    )
    shape = contract.get("projection_shape") if isinstance(contract.get("projection_shape"), Mapping) else {}

    def _shape_int(key: str, default: int) -> int:
        try:
            return int(shape.get(key) or default)
        except (TypeError, ValueError):
            return default

    pinned = _normalize_string_list(shape.get("pinned_slugs")) or list(PAPER_MODULE_DEFAULT_PINNED_SLUGS)
    return {
        "tldr_excerpt_budget_chars": _shape_int(
            "tldr_excerpt_budget_chars",
            PAPER_MODULE_DEFAULT_TLDR_BUDGET_CHARS,
        ),
        "total_region_budget_chars": _shape_int(
            "total_region_budget_chars",
            PAPER_MODULE_DEFAULT_REGION_BUDGET_CHARS,
        ),
        "max_rows": _shape_int("max_rows", PAPER_MODULE_DEFAULT_MAX_ROWS),
        "pinned_slugs": pinned,
    }


def _family_number_from_dir(family_dir: str | None) -> str | None:
    text = str(family_dir or "").strip()
    if not text:
        return None
    name = Path(text).name
    if " - " not in name:
        return None
    token = name.split(" - ", 1)[0].strip()
    return token or None


def _apply_active_family_bootstrap_overrides(
    bindings: Mapping[str, Any],
    *,
    minimum_read_sets: Mapping[str, Any] | None = None,
    situation_routes: list[Mapping[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    from system.lib.raw_seed_registry import (
        raw_seed_meta_path_for_family,
        raw_seed_principles_path_for_family,
    )

    mrs = normalize_minimum_read_sets(minimum_read_sets)
    active_family_dir = str(bindings.get("active_family_dir") or bindings.get("family_dir") or "").strip()
    active_family_number = str(bindings.get("active_family_number") or "").strip() or _family_number_from_dir(active_family_dir) or ""
    if active_family_dir:
        raw_seed_meta = raw_seed_meta_path_for_family(active_family_dir)
        raw_seed_principles = raw_seed_principles_path_for_family(active_family_dir)
        if "mrs_artifact_raw_seed_substrate" in mrs:
            mrs["mrs_artifact_raw_seed_substrate"] = {
                **mrs["mrs_artifact_raw_seed_substrate"],
                "paths": [raw_seed_meta, "docs/raw_seed_doctrine_derivation.md"],
            }
        if "mrs_filetype_raw_seed_family" in mrs:
            mrs["mrs_filetype_raw_seed_family"] = {
                **mrs["mrs_filetype_raw_seed_family"],
                "paths": [raw_seed_meta, raw_seed_principles],
            }
        if "mrs_artifact_principles_graph" in mrs:
            mrs["mrs_artifact_principles_graph"] = {
                **mrs["mrs_artifact_principles_graph"],
                "paths": ["docs/raw_seed_principles_curation.md", raw_seed_principles],
            }

    routes = normalize_situation_routes(situation_routes, minimum_read_sets=mrs or None)
    if active_family_dir and active_family_number:
        raw_seed_meta = raw_seed_meta_path_for_family(active_family_dir)
        for row in routes:
            if str(row.get("situation_id") or "").strip() != "raw_seed_substrate":
                continue
            row["canonical_next_read"] = raw_seed_meta
            row["fallback_command"] = f"python3 kernel.py --sync-raw-seed {active_family_number} --live"
            row["minimum_read_paths"] = [raw_seed_meta, "docs/raw_seed_doctrine_derivation.md"]
            break
    return mrs, routes


def normalize_minimum_read_sets(raw: Any) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Canonicalize minimum_read_sets config into the stable shape used by projection rendering and payload emission.
    - Mechanism: Keeps mapping-shaped entries only, trims set ids and path strings, and preserves purpose when present.
    - Guarantee: Returns `{set_id: {paths: [...], purpose?}}` with only non-empty ids and paths.
    - Fails: None.
    - When-needed: Open when agent_bootstrap minimum-read-set config needs normalization before route rendering or payload emission.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::render_live_markdown
    """
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        set_id = str(key).strip()
        if not set_id or not isinstance(value, Mapping):
            continue
        paths_raw = value.get("paths")
        paths = [
            str(p).strip()
            for p in (paths_raw if isinstance(paths_raw, list) else [])
            if str(p).strip()
        ]
        purpose = str(value.get("purpose") or "").strip() or None
        entry: dict[str, Any] = {"paths": paths}
        if purpose:
            entry["purpose"] = purpose
        out[set_id] = entry
    return out


def normalize_bootstrap_sequence(raw: Any) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Canonicalize bootstrap-sequence rows before they are rendered into the live bootstrap surfaces.
    - Mechanism: Keeps list items that are mappings with non-empty step_id and command fields, trimming optional why text when present.
    - Guarantee: Returns an ordered list of normalized bootstrap-step mappings.
    - Fails: None.
    - When-needed: Open when bootstrap-sequence config needs the exact filtering rules used before markdown or JSON projection.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::render_live_markdown
    """
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        step_id = str(item.get("step_id") or "").strip()
        command = str(item.get("command") or "").strip()
        if not step_id or not command:
            continue
        row: dict[str, Any] = {"step_id": step_id, "command": command}
        why = str(item.get("why") or "").strip()
        if why:
            row["why"] = why
        out.append(row)
    return out


def _bootstrap_command_by_step_id(
    bootstrap_sequence: list[Mapping[str, Any]] | None,
) -> dict[str, str]:
    sequence = normalize_bootstrap_sequence(bootstrap_sequence)
    commands: dict[str, str] = {}
    for step in sequence:
        step_id = str(step.get("step_id") or "").strip()
        command = str(step.get("command") or "").strip()
        if step_id and command and step_id not in commands:
            commands[step_id] = command
    return commands


def _compact_kernel_command(command: str) -> str:
    for prefix in ("./repo-python kernel.py ", "python3 kernel.py "):
        if command.startswith(prefix):
            return command[len(prefix):]
    return command


def render_compact_bootstrap_handshake(
    bootstrap_sequence: list[Mapping[str, Any]] | None,
) -> str | None:
    """
    [ACTION]
    - Teleology: Project the configured bootstrap sequence as one live-state prelude plus one task-routing control packet instead of hand-maintained prose.
    - Mechanism: Reads the normalized `bootstrap_sequence` rows and emits the compact sentence used by adapter live blocks.
    - Guarantee: Returns None when no prelude or entry command can be resolved; does not invent commands missing from the config.
    """
    commands = _bootstrap_command_by_step_id(bootstrap_sequence)
    prelude = [
        commands[step_id]
        for step_id in ("kernel_info", "kernel_preflight", "kernel_pulse")
        if commands.get(step_id)
    ]
    entry = commands.get("entry")
    if not prelude and not entry:
        return None

    parts: list[str] = []
    if prelude:
        parts.append("Prelude: " + " -> ".join(f"`{_compact_kernel_command(cmd)}`" for cmd in prelude))
    if entry:
        parts.append(f"task lane: `{_compact_kernel_command(entry)}`")

    drilldowns = [
        commands[step_id]
        for step_id in ("context_pack", "navigation_metabolism", "kind_atlas")
        if commands.get(step_id)
    ]
    if drilldowns:
        parts.append(
            "drilldowns after lane selection: "
            + ", ".join(f"`{_compact_kernel_command(cmd)}`" for cmd in drilldowns[:3])
        )
    return "- " + "; ".join(parts) + "."


def normalize_situation_routes(
    raw: Any,
    *,
    minimum_read_sets: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Normalize situation-route rows into the bounded projection shape agents read from the live bootstrap.
    - Mechanism: Filters to mapping rows with situation_id and route_command, resolves minimum-read-set references, and fills canonical_next_read from the set when missing.
    - Guarantee: Returns only routable situation rows with trimmed scalar fields and optional minimum_read_paths.
    - Fails: None.
    - When-needed: Open when situation routes from agent_bootstrap.json need to be projected into markdown or JSON without carrying invalid rows.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::normalize_minimum_read_sets
    """
    if not isinstance(raw, list):
        return []
    mrs = normalize_minimum_read_sets(minimum_read_sets)
    out: list[dict[str, Any]] = []

    def _normalize_route_targets(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, Mapping):
            candidates = [value]
        elif isinstance(value, list):
            candidates = [item for item in value if isinstance(item, Mapping)]
        else:
            return []

        targets: list[dict[str, Any]] = []
        for candidate in candidates:
            kind = str(candidate.get("kind") or candidate.get("target_kind") or "").strip()
            ref = str(candidate.get("ref") or candidate.get("target_ref") or candidate.get("id") or "").strip()
            if not kind or not ref:
                continue
            target: dict[str, Any] = {"kind": kind, "ref": ref}
            for key in (
                "role",
                "relation",
                "authority",
                "label",
                "command",
                "freshness_command",
            ):
                raw_value = str(candidate.get(key) or "").strip()
                if raw_value:
                    target[key] = raw_value
            match_tokens = [
                str(token).strip()
                for token in (candidate.get("match_tokens") or [])
                if str(token).strip()
            ]
            if match_tokens:
                target["match_tokens"] = match_tokens
            targets.append(target)
        return targets

    for item in raw:
        if not isinstance(item, Mapping):
            continue
        situation_id = str(item.get("situation_id") or "").strip()
        route_command = str(item.get("route_command") or "").strip()
        if not situation_id or not route_command:
            continue
        minimum_read_set_id = str(item.get("minimum_read_set_id") or "").strip() or None
        minimum_read_entry = mrs.get(minimum_read_set_id or "") or {}
        minimum_read_paths = [
            str(path).strip()
            for path in (minimum_read_entry.get("paths") or [])
            if str(path).strip()
        ]
        canonical_next_read = str(item.get("canonical_next_read") or "").strip()
        if not canonical_next_read and minimum_read_paths:
            canonical_next_read = minimum_read_paths[0]
        row: dict[str, Any] = {
            "situation_id": situation_id,
            "route_command": route_command,
        }
        for key in (
            "label",
            "use_when",
            "route_id",
            "fallback_command",
            "freshness_command",
            "principle_anchor",
            "standard_anchor",
        ):
            value = str(item.get(key) or "").strip()
            if value:
                row[key] = value
        drilldown_chain = item.get("drilldown_chain")
        if isinstance(drilldown_chain, list):
            cleaned = [str(step).strip() for step in drilldown_chain if str(step).strip()]
            if cleaned:
                row["drilldown_chain"] = cleaned
        match_tokens = item.get("match_tokens")
        if isinstance(match_tokens, list):
            cleaned = [str(token).strip() for token in match_tokens if str(token).strip()]
            if cleaned:
                row["match_tokens"] = cleaned
        route_targets = _normalize_route_targets(item.get("route_targets") or item.get("route_target"))
        if route_targets:
            row["route_targets"] = route_targets
        actor_delivery = item.get("actor_delivery")
        if isinstance(actor_delivery, Mapping):
            delivery_row: dict[str, Any] = {}
            for key in ("decision", "reason", "source", "workitem_ref"):
                value = str(actor_delivery.get(key) or "").strip()
                if value:
                    delivery_row[key] = value
            for key in (
                "required_actor_ids",
                "required_tokens",
                "smoke_command",
                "smoke_expected_tokens",
                "smoke_negative_command",
                "smoke_forbidden_tokens",
            ):
                values = [
                    str(value).strip()
                    for value in (actor_delivery.get(key) or [])
                    if str(value).strip()
                ]
                if values:
                    delivery_row[key] = values
            if delivery_row:
                row["actor_delivery"] = delivery_row
        if minimum_read_set_id:
            row["minimum_read_set_id"] = minimum_read_set_id
        if canonical_next_read:
            row["canonical_next_read"] = canonical_next_read
        if minimum_read_paths:
            row["minimum_read_paths"] = minimum_read_paths
        out.append(row)
    return out


def normalize_actor_context_surfaces(
    raw: Any,
    *,
    minimum_read_sets: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Normalize actor context-surface rows for projection into live bootstrap artifacts.
    - Mechanism: Filters to mapping rows with actor_id and label, trims read_order and primary_commands entries, and attaches resolved minimum_read_paths when available.
    - Guarantee: Returns only valid actor rows with stable list fields and optional runtime_surface_id.
    - Fails: None.
    - When-needed: Open when actor-context entries from agent_bootstrap.json need the exact normalization rules before projection.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::normalize_minimum_read_sets
    """
    if not isinstance(raw, list):
        return []
    mrs = normalize_minimum_read_sets(minimum_read_sets)
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        actor_id = str(item.get("actor_id") or "").strip()
        label = str(item.get("label") or "").strip()
        if not actor_id or not label:
            continue
        minimum_read_set_id = str(item.get("minimum_read_set_id") or "").strip() or None
        minimum_read_entry = mrs.get(minimum_read_set_id or "") or {}
        row: dict[str, Any] = {
            "actor_id": actor_id,
            "label": label,
            "read_order": [
                str(value).strip()
                for value in (item.get("read_order") or [])
                if str(value).strip()
            ],
            "primary_commands": [
                str(value).strip()
                for value in (item.get("primary_commands") or [])
                if str(value).strip()
            ],
        }
        if minimum_read_set_id:
            row["minimum_read_set_id"] = minimum_read_set_id
        fallback_minimum_read_paths = (
            item.get("minimum_read_paths")
            if isinstance(item.get("minimum_read_paths"), list)
            else []
        )
        minimum_read_source = (
            minimum_read_entry.get("paths")
            if isinstance(minimum_read_entry.get("paths"), list)
            else fallback_minimum_read_paths
        )
        minimum_read_paths = [
            str(path).strip()
            for path in (minimum_read_source or [])
            if str(path).strip()
        ]
        if minimum_read_paths:
            row["minimum_read_paths"] = minimum_read_paths
        runtime_surface_id = str(item.get("runtime_surface_id") or "").strip()
        if runtime_surface_id:
            row["runtime_surface_id"] = runtime_surface_id
        out.append(row)
    return out


def build_actor_bootstrap_packets(
    raw: Any,
    *,
    minimum_read_sets: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Derive ordered flat-file bootstrap packets for each actor so context identity is explicit instead of re-derived from scattered adapter prose.
    - Mechanism: Normalizes actor_context_surfaces, merges read_order with resolved minimum-read paths while preserving first-read order, and emits one compact packet per actor.
    - Guarantee: Returns deterministic actor packets with deduplicated context_files and the first readable file highlighted as first_read.
    - Fails: None.
    - When-needed: Open when a host or bridge surface needs the actor's ordered bootstrap file packet rather than the raw config row.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::build_live_payload
    """
    actors = normalize_actor_context_surfaces(raw, minimum_read_sets=minimum_read_sets)
    packets: list[dict[str, Any]] = []
    for row in actors:
        context_files: list[dict[str, Any]] = []
        seen: set[str] = set()

        def _add_file(path: str, source: str) -> None:
            rel = str(path or "").strip()
            if not rel or rel in seen:
                return
            seen.add(rel)
            context_files.append(
                {
                    "order": len(context_files) + 1,
                    "path": rel,
                    "source": source,
                }
            )

        for path in row.get("read_order") or []:
            _add_file(str(path), "read_order")
        for path in row.get("minimum_read_paths") or []:
            _add_file(str(path), "minimum_read_set")

        packet: dict[str, Any] = {
            "actor_id": row["actor_id"],
            "label": row["label"],
            "identity_source": "flat_file_bootstrap",
            "context_files": context_files,
            "primary_commands": list(row.get("primary_commands") or []),
        }
        if context_files:
            packet["first_read"] = context_files[0]["path"]
        if row.get("minimum_read_set_id"):
            packet["minimum_read_set_id"] = row["minimum_read_set_id"]
        if row.get("runtime_surface_id"):
            packet["runtime_surface_id"] = row["runtime_surface_id"]
        if packet["primary_commands"]:
            packet["entry_command"] = packet["primary_commands"][0]
        packets.append(packet)
    return packets


def normalize_runtime_control_plane(raw: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Filter the runtime-control-plane config down to the named fields exposed in the bootstrap projection.
    - Mechanism: Copies only the recognized keys and trims them to non-empty strings.
    - Guarantee: Returns a dict containing only known runtime-control-plane projection keys.
    - Fails: None.
    - When-needed: Open when runtime control-plane config needs the exact field whitelist used by the bootstrap projection.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::render_live_markdown
    """
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key in (
        "snapshot_path",
        "event_log_path",
        "brief_json_path",
        "brief_markdown_path",
        "control_room_command",
        "overnight_status_command",
        "overnight_write_command",
        "pulse_command",
        "docs_route_command",
        "docs_route_focus_path",
    ):
        value = str(raw.get(key) or "").strip()
        if value:
            out[key] = value
    return out


def normalize_compact_command_surface(raw: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Canonicalize the compact startup command surface config used by the AGENTS bootstrap projection.
    - Mechanism: Merge any provided overrides onto the repo defaults, preserving only mapping-shaped group entrypoints with command text.
    - Guarantee: Returns a dict with max_flags_per_group and group_entrypoints ready for markdown/JSON projection.
    - Fails: None.
    - When-needed: Open when the managed AGENTS command surface needs the exact normalization rules behind its entrypoint table.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::render_compact_command_surface
    """
    base = {
        "max_flags_per_group": int(DEFAULT_COMPACT_COMMAND_SURFACE["max_flags_per_group"]),
        "group_entrypoints": {
            key: dict(value)
            for key, value in DEFAULT_COMPACT_COMMAND_SURFACE["group_entrypoints"].items()
        },
    }
    if not isinstance(raw, Mapping):
        return base
    max_flags = raw.get("max_flags_per_group")
    if isinstance(max_flags, int) and max_flags > 0:
        base["max_flags_per_group"] = max_flags
    group_entrypoints = raw.get("group_entrypoints")
    if not isinstance(group_entrypoints, Mapping):
        return base
    normalized_groups: dict[str, dict[str, Any]] = {
        key: dict(value)
        for key, value in base["group_entrypoints"].items()
    }
    for group, item in group_entrypoints.items():
        group_id = str(group or "").strip()
        if not group_id or not isinstance(item, Mapping):
            continue
        command = str(item.get("command") or "").strip()
        if not command:
            continue
        row = {"command": command}
        why = str(item.get("why") or "").strip()
        if why:
            row["why"] = why
        normalized_groups[group_id] = row
    base["group_entrypoints"] = normalized_groups
    return base


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def normalize_instruction_discovery(raw: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Canonicalize the compact Codex instruction-discovery seed config so official discovery constraints and local file-size facts stay in one projected surface.
    - Mechanism: Merges configured values onto DEFAULT_INSTRUCTION_DISCOVERY, trimming paths, markers, and byte budgets while preserving a stable list of watched instruction files.
    - Guarantee: Returns a dict with seed/deep-hub paths, marker pair, watch paths, and positive byte budgets.
    - Fails: None.
    - When-needed: Open when changing how AGENTS.override.md or another compact seed is generated for Codex project-doc discovery.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::resolve_instruction_discovery_facts
    """
    cfg = dict(DEFAULT_INSTRUCTION_DISCOVERY)
    if isinstance(raw, Mapping):
        for key in (
            "provider",
            "markdown_target",
            "begin_marker",
            "end_marker",
            "seed_path",
            "deep_hub_path",
            "official_source",
        ):
            value = str(raw.get(key) or "").strip()
            if value:
                cfg[key] = value
        adapter_paths = _normalize_string_list(raw.get("adapter_paths"))
        if adapter_paths:
            cfg["adapter_paths"] = adapter_paths
        watch_paths = _normalize_string_list(raw.get("size_watch_paths"))
        if watch_paths:
            cfg["size_watch_paths"] = watch_paths
        cfg["project_doc_max_bytes_default"] = _positive_int(
            raw.get("project_doc_max_bytes_default"),
            int(DEFAULT_INSTRUCTION_DISCOVERY["project_doc_max_bytes_default"]),
        )
        cfg["compact_seed_budget_bytes"] = _positive_int(
            raw.get("compact_seed_budget_bytes"),
            int(DEFAULT_INSTRUCTION_DISCOVERY["compact_seed_budget_bytes"]),
        )
    seed_path = str(cfg.get("seed_path") or "").strip()
    deep_hub = str(cfg.get("deep_hub_path") or "").strip()
    watch_paths = _normalize_string_list(cfg.get("size_watch_paths"))
    for path in (seed_path, deep_hub, *cfg.get("adapter_paths", [])):
        text = str(path or "").strip()
        if text and text not in watch_paths:
            watch_paths.append(text)
    cfg["size_watch_paths"] = watch_paths
    return cfg


def _file_size_record(repo_root: Path, rel_path: str, *, default_budget: int, seed_budget: int, seed_path: str) -> dict[str, Any]:
    path = repo_root / rel_path
    exists = path.is_file()
    byte_count: int | None = None
    non_empty = False
    if exists:
        try:
            raw = path.read_bytes()
            byte_count = len(raw)
            non_empty = bool(raw.strip())
        except OSError:
            byte_count = None
    budget = seed_budget if rel_path == seed_path else default_budget
    status = "missing"
    if exists and byte_count is not None:
        if not non_empty:
            status = "empty"
        elif byte_count > budget:
            status = "over_budget"
        else:
            status = "within_budget"
    return {
        "path": rel_path,
        "exists": exists,
        "non_empty": non_empty,
        "bytes": byte_count,
        "budget_bytes": budget,
        "budget_status": status,
    }


def resolve_instruction_discovery_facts(repo_root: Path, raw: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Snapshot local Codex instruction-discovery facts from disk so the compact root seed carries current, non-hand-maintained evidence.
    - Mechanism: Reads configured instruction files, computes byte counts and budget posture, and resolves the effective root instruction path under the `AGENTS.override.md` before `AGENTS.md` rule.
    - Guarantee: Returns deterministic file-size and effective-root facts for markdown and JSON projections; absent files degrade to explicit missing rows.
    - Fails: None.
    - When-needed: Open when the root Codex discovery seed needs live facts about entrypoint size, override presence, or hub/adapters crossing discovery budgets.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::render_instruction_discovery_markdown; codex/doctrine/paper_modules/codex_markdown_doctrine.md
    """
    cfg = normalize_instruction_discovery(raw)
    default_budget = int(cfg["project_doc_max_bytes_default"])
    seed_budget = int(cfg["compact_seed_budget_bytes"])
    seed_path = str(cfg["seed_path"])
    deep_hub = str(cfg["deep_hub_path"])
    records = [
        _file_size_record(
            repo_root,
            rel_path,
            default_budget=default_budget,
            seed_budget=seed_budget,
            seed_path=seed_path,
        )
        for rel_path in cfg["size_watch_paths"]
    ]
    by_path = {record["path"]: record for record in records}
    seed_record = by_path.get(seed_path) or _file_size_record(
        repo_root,
        seed_path,
        default_budget=default_budget,
        seed_budget=seed_budget,
        seed_path=seed_path,
    )
    hub_record = by_path.get(deep_hub) or _file_size_record(
        repo_root,
        deep_hub,
        default_budget=default_budget,
        seed_budget=seed_budget,
        seed_path=seed_path,
    )
    effective_root = seed_path if seed_record.get("non_empty") else (deep_hub if hub_record.get("non_empty") else None)
    oversized = [
        record["path"]
        for record in records
        if record.get("budget_status") == "over_budget"
    ]
    return {
        "provider": cfg["provider"],
        "official_source": cfg.get("official_source"),
        "markdown_target": cfg["markdown_target"],
        "seed_path": seed_path,
        "deep_hub_path": deep_hub,
        "adapter_paths": list(cfg.get("adapter_paths") or []),
        "project_doc_max_bytes_default": default_budget,
        "compact_seed_budget_bytes": seed_budget,
        "effective_root_instruction_path": effective_root,
        "override_active": effective_root == seed_path,
        "files": records,
        "oversized_paths": oversized,
        "begin_marker": cfg["begin_marker"],
        "end_marker": cfg["end_marker"],
    }


def _normalize_keyed_rows(raw: Any, *, key_field: str) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        row: dict[str, str] = {}
        for key, value in item.items():
            text = str(value or "").strip()
            if text:
                row[str(key)] = text
        if row.get(key_field):
            rows.append(row)
    return rows


def normalize_type_a_convergence_contract(raw: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Canonicalize the Type A convergence contract that keeps Codex and Claude entry surfaces aligned with observed host-agent behavior.
    - Mechanism: Filters the optional config block to short scalar fields plus bounded lists for source surfaces, probe commands, feedback loop, and invariants.
    - Guarantee: Returns a stable mapping suitable for markdown and JSON projection, or an empty dict when no valid contract is configured.
    - Fails: None.
    - When-needed: Open when extending how AGENTS/CODEX/CLAUDE surface cross-agent convergence, external host telemetry, or closeout feedback loops.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; docs/agent_telemetry.md; codex/doctrine/paper_modules/host_agent_external_surfaces.md
    """
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key in ("summary", "route_command", "canonical_next_read", "coverage_command"):
        value = str(raw.get(key) or "").strip()
        if value:
            out[key] = value
    source_surfaces = _normalize_keyed_rows(raw.get("source_surfaces"), key_field="id")
    if source_surfaces:
        out["source_surfaces"] = source_surfaces
    probe_commands = _normalize_keyed_rows(raw.get("probe_commands"), key_field="id")
    if probe_commands:
        out["probe_commands"] = probe_commands
    gate = raw.get("comprehension_gate")
    if isinstance(gate, Mapping):
        normalized_gate: dict[str, Any] = {}
        for key in ("summary", "route_command", "failure_mode"):
            value = str(gate.get(key) or "").strip()
            if value:
                normalized_gate[key] = value
        buckets = _normalize_keyed_rows(gate.get("required_evidence_buckets"), key_field="id")
        if buckets:
            normalized_gate["required_evidence_buckets"] = buckets
        if normalized_gate:
            out["comprehension_gate"] = normalized_gate
    feedback_loop = [
        str(value).strip()
        for value in (raw.get("feedback_loop") if isinstance(raw.get("feedback_loop"), list) else [])
        if str(value).strip()
    ]
    if feedback_loop:
        out["feedback_loop"] = feedback_loop
    invariants = [
        str(value).strip()
        for value in (raw.get("invariants") if isinstance(raw.get("invariants"), list) else [])
        if str(value).strip()
    ]
    if invariants:
        out["invariants"] = invariants
    return out


def render_type_a_convergence_contract(raw: Any) -> list[str]:
    """
    [ACTION]
    - Teleology: Render the Type A convergence contract into the managed AGENTS bootstrap block.
    - Mechanism: Emits a compact markdown section naming the shared route, source surfaces, safe probes, feedback loop, and invariants.
    - Guarantee: Returns an empty list when the contract is absent and a bounded markdown line list when present.
    - Fails: None.
    - When-needed: Open when changing how cold Type A agents learn to reconcile Codex/Claude behavior through observed host records.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::render_live_markdown
    """
    contract = normalize_type_a_convergence_contract(raw)
    if not contract:
        return []
    lines: list[str] = ["", "**Type A convergence contract:**", ""]
    if contract.get("summary"):
        lines.append(f"- {contract['summary']}")
    route_bits: list[str] = []
    if contract.get("route_command"):
        route_bits.append(f"route `{contract['route_command']}`")
    if contract.get("canonical_next_read"):
        route_bits.append(f"next `{contract['canonical_next_read']}`")
    if contract.get("coverage_command"):
        route_bits.append(f"coverage `{contract['coverage_command']}`")
    if route_bits:
        lines.append(f"- {'; '.join(route_bits)}")
    # Compressed per pri_121: collapse source_surfaces / probe_commands / feedback_loop / invariants
    # into compact single-line projections; full glosses live in agent_bootstrap_live.json.
    if contract.get("source_surfaces"):
        path_bits: list[str] = []
        for row in contract["source_surfaces"]:
            path = row.get("path")
            if path:
                path_bits.append(f"`{path}`")
        if path_bits:
            lines.append(
                f"- Source surfaces: {'; '.join(path_bits)} (roles/authority in `codex/doctrine/agent_bootstrap_live.json`)."
            )
    if contract.get("probe_commands"):
        cmd_bits: list[str] = []
        for row in contract["probe_commands"]:
            command = row.get("command")
            if command:
                cmd_bits.append(f"`{command}`")
        if cmd_bits:
            lines.append(
                f"- Safe probes: {'; '.join(cmd_bits)} (purposes in `codex/doctrine/agent_bootstrap_live.json`)."
            )
    gate = contract.get("comprehension_gate")
    if isinstance(gate, Mapping):
        summary = str(gate.get("summary") or "").strip()
        route = str(gate.get("route_command") or "").strip()
        failure = str(gate.get("failure_mode") or "").strip()
        if summary:
            lines.append(f"- Comprehension gate: {summary}")
        if route:
            lines.append(f"  - Gate route: `{route}`")
        bucket_rows = [
            row for row in (gate.get("required_evidence_buckets") or [])
            if isinstance(row, Mapping)
        ]
        if bucket_rows:
            bucket_ids: list[str] = []
            bucket_routes: list[str] = []
            for row in bucket_rows:
                bucket_id = str(row.get("id") or "").strip()
                if bucket_id:
                    bucket_ids.append(f"`{bucket_id}`")
                must_cite = str(row.get("must_cite") or "")
                parts = must_cite.split("`")
                snippets = [parts[i].strip() for i in range(1, len(parts), 2) if parts[i].strip()]
                if snippets and bucket_id:
                    short = " | ".join(f"`{s}`" for s in snippets[:3])
                    bucket_routes.append(f"  - `{bucket_id}`: {short}")
            if bucket_ids:
                lines.append(
                    f"  - Required evidence buckets ({len(bucket_ids)}): "
                    + "; ".join(bucket_ids)
                    + " (per pri_121; full glosses in `codex/doctrine/agent_bootstrap_live.json`)."
                )
            lines.extend(bucket_routes)
        if failure:
            lines.append(f"  - Failure mode: {failure}")
    if contract.get("feedback_loop"):
        # Compressed per pri_121: emit lead verb of each step; full prose in sidecar.
        loop = contract["feedback_loop"]
        verbs = [str(item).split()[0] for item in loop if str(item).strip()]
        if verbs:
            lines.append(
                f"- Feedback loop: {' → '.join(verbs)} (full prose in `codex/doctrine/agent_bootstrap_live.json`)."
            )
    if contract.get("invariants"):
        # Compressed per pri_121: emit count + sidecar pointer.
        n = len(contract["invariants"])
        lines.append(
            f"- Invariants: {n} (text in `codex/doctrine/agent_bootstrap_live.json::type_a_convergence_contract.invariants`)."
        )
    return lines


def render_compact_command_surface(
    compact_command_surface: Mapping[str, Any] | None,
    *,
    bootstrap_sequence: list[Mapping[str, Any]] | None = None,
) -> list[str]:
    """
    [ACTION]
    - Teleology: Render the compact startup command surface from the shared kernel command taxonomy plus bootstrap-config entrypoints.
    - Mechanism: Read normalized entrypoint rows, pair them with `state.STABLE_COMMANDS`, and emit a bounded markdown table with the bootstrap sequence nearby.
    - Guarantee: Returns a list of markdown lines ready to splice into the AGENTS live bootstrap region.
    - Fails: None.
    - When-needed: Open when the AGENTS startup command surface needs to be regenerated from machine authority instead of prose duplication.
    - Escalates-to: system.lib.kernel.state::STABLE_COMMANDS; codex/doctrine/agent_bootstrap.json
    """
    from system.lib.kernel import state as kernel_state

    config = normalize_compact_command_surface(compact_command_surface)
    entrypoints = config.get("group_entrypoints") if isinstance(config.get("group_entrypoints"), Mapping) else {}
    lines: list[str] = ["", "**Compact startup command surface:**", ""]
    if bootstrap_sequence:
        # Compact form: drop the redundant `./repo-python kernel.py ` prefix
        # repeated across every step (was ~200 bytes of duplication for the
        # 8-step russian-doll chain), keep the flag-only ordered chain so cold
        # agents see the canonical first-move sequence.
        seq_steps = normalize_bootstrap_sequence(bootstrap_sequence)
        flag_chain: list[str] = []
        for step in seq_steps:
            cmd = str(step.get("command") or "").strip()
            stripped = cmd.replace("./repo-python kernel.py ", "").replace("python3 kernel.py ", "")
            if stripped:
                flag_chain.append(f"`{stripped}`")
        if flag_chain:
            lines.append(f"- Bootstrap path (kernel.py): " + " → ".join(flag_chain))
    # Lane registry compressed per pri_121: full lane × command × flags
    # taxonomy lives in agent_bootstrap_live.json::compact_command_surface
    # plus `./repo-python kernel.py --info`. The hub carries the route
    # pointer; the registry stays in the JSON sidecar.
    lane_groups = sorted(
        g for g, spec in entrypoints.items()
        if g in kernel_state.STABLE_COMMANDS and isinstance(spec, Mapping) and (spec.get("command") or "").strip()
    )
    if lane_groups:
        lines.append(
            f"- Lane registry ({len(lane_groups)} lanes: {', '.join('`' + g + '`' for g in lane_groups)}): "
            f"`./repo-python kernel.py --info` for full lane × command × flags taxonomy "
            f"(also in `codex/doctrine/agent_bootstrap_live.json::compact_command_surface`)."
        )
    return lines


def _file_mtime_iso(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except OSError:
        return None


def find_pipeline_state_path(repo_root: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Resolve the pipeline_state.json that should anchor the live bootstrap snapshot.
    - Mechanism: Delegates to the shared phase-lifecycle runtime selector so only non-deprecated, runtime-eligible phase lineage can anchor the live bootstrap snapshot.
    - Guarantee: Returns the best runtime-eligible pipeline-state path or None when no such candidate exists.
    - Fails: None.
    - When-needed: Open when a bootstrap refresh needs the exact precedence rule for choosing the active pipeline-state file.
    - Escalates-to: system/lib/phase_activation.py::load_explicit_active_phase; system/lib/agent_bootstrap_projection.py::resolve_live_bindings
    """
    from system.lib.phase_lifecycle import resolve_latest_runtime_state

    return resolve_latest_runtime_state(repo_root)


def load_agent_bootstrap_config(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load the bootstrap projection config or synthesize the default config when the on-disk artifact is missing.
    - Mechanism: Reads codex/doctrine/agent_bootstrap.json through _safe_load_json() and returns a hard-coded fallback document when the file is absent or invalid.
    - Guarantee: Returns a bootstrap-config mapping with markers, generated-file targets, markdown targets, and source-path defaults.
    - Fails: None.
    - When-needed: Open when a bootstrap projection run needs to know the exact default config that replaces a missing or invalid agent_bootstrap.json.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::run_projection
    """
    path = repo_root / "codex" / "doctrine" / "agent_bootstrap.json"
    data = _safe_load_json(path)
    if not data:
        return {
            "kind": "agent_bootstrap",
            "schema_version": "agent_bootstrap_v0",
            "markers": {"begin": DEFAULT_MARKERS[0], "end": DEFAULT_MARKERS[1]},
            "generated_file_targets": {
                "live_json": "codex/doctrine/agent_bootstrap_live.json",
                "injection_strip": "codex/doctrine/agent_bootstrap_injection_strip.json",
                "agent_operating_packet": AGENT_OPERATING_PACKET_REL,
            },
            "markdown_targets": {"agents_md": "AGENTS.md"},
            "injection_strip_max_bytes": 8192,
            "source_paths": {
                "system_map": "codex/doctrine/system_map.json",
                "doctrine_runtime": "codex/doctrine/doctrine_runtime.json",
                "factory_state": "tools/meta/factory/factory_state.json",
                "orchestration_state": "tools/meta/control/orchestration_state.json",
                "default_extracted_shards": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/extracted_shards.json",
            },
            "compact_command_surface": DEFAULT_COMPACT_COMMAND_SURFACE,
            "instruction_discovery": DEFAULT_INSTRUCTION_DISCOVERY,
        }
    return data


def normalize_bootstrap_projection_sections(config: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Normalize the agent-bootstrap config once so builder, checker, and writer lanes cannot drift by forgetting a section.
    - Mechanism: Applies every section normalizer in dependency order: minimum read sets first, then routes/actors that depend on them, plus runtime, command, and Type A convergence surfaces.
    - Guarantee: Returns the complete normalized section mapping consumed by markdown, JSON, and drift-check projections.
    - Fails: None.
    - When-needed: Open when adding a new agent-bootstrap section or debugging a mismatch between build_agent_bootstrap_projection.py and check_agent_bootstrap_projection.py.
    - Escalates-to: codex/doctrine/agent_bootstrap.json; system/lib/agent_bootstrap_projection.py::build_bootstrap_projection_context
    """
    cfg = dict(config or {})
    rows = cfg.get("per_agent_rows") if isinstance(cfg.get("per_agent_rows"), list) else []
    mrs = normalize_minimum_read_sets(cfg.get("minimum_read_sets"))
    sequence = normalize_bootstrap_sequence(cfg.get("bootstrap_sequence"))
    situations = normalize_situation_routes(cfg.get("situation_routes"), minimum_read_sets=mrs or None)
    actor_context_surfaces = normalize_actor_context_surfaces(
        cfg.get("actor_context_surfaces"),
        minimum_read_sets=mrs or None,
    )
    return {
        "per_agent_rows": rows,
        "minimum_read_sets": mrs,
        "bootstrap_sequence": sequence,
        "situation_routes": situations,
        "actor_context_surfaces": actor_context_surfaces,
        "actor_bootstrap_packets": build_actor_bootstrap_packets(
            actor_context_surfaces,
            minimum_read_sets=mrs or None,
        ),
        "runtime_control_plane": normalize_runtime_control_plane(cfg.get("runtime_control_plane")),
        "compact_command_surface": normalize_compact_command_surface(cfg.get("compact_command_surface")),
        "instruction_discovery": normalize_instruction_discovery(cfg.get("instruction_discovery")),
        "type_a_convergence_contract": normalize_type_a_convergence_contract(
            cfg.get("type_a_convergence_contract")
        ),
    }


def build_bootstrap_projection_context(
    repo_root: Path,
    *,
    config: Mapping[str, Any] | None = None,
    refresh_orchestration: bool = True,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the shared parser/model context for all bootstrap projection consumers before any markdown or file writer runs.
    - Mechanism: Loads or accepts the bootstrap config, normalizes all config sections through normalize_bootstrap_projection_sections(), and resolves live disk bindings with the requested orchestration refresh posture.
    - Guarantee: Builder CLIs, drift checkers, and write paths can consume the same complete section set instead of re-implementing partial normalization.
    - Fails: Propagates resolve_live_bindings failures from the underlying runtime loader.
    - When-needed: Open when aligning AGENTS/CODEX/CLAUDE projection generation with checker expectations, or when adding a new generated bootstrap section.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::resolve_live_bindings; system/lib/agent_bootstrap_projection.py::render_live_markdown
    """
    cfg = dict(config or load_agent_bootstrap_config(repo_root))
    sections = normalize_bootstrap_projection_sections(cfg)
    return {
        "config": cfg,
        "bindings": resolve_live_bindings(
            repo_root,
            config=cfg,
            refresh_orchestration=refresh_orchestration,
        ),
        "instruction_discovery_facts": resolve_instruction_discovery_facts(
            repo_root,
            cfg.get("instruction_discovery"),
        ),
        "system_facts_at_a_glance": load_system_facts_at_a_glance(repo_root),
        "agent_operating_packet": build_agent_operating_packet(
            repo_root,
            config=cfg.get("agent_operating_packet")
            if isinstance(cfg.get("agent_operating_packet"), Mapping)
            else None,
        ),
        **sections,
    }


def resolve_live_bindings(
    repo_root: Path,
    *,
    config: Mapping[str, Any] | None = None,
    pipeline_state_path: Path | None = None,
    factory_state_path: Path | None = None,
    refresh_orchestration: bool = True,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Snapshot the current bootstrap-relevant runtime bindings from disk into one mapping.
    - Mechanism: Loads configured source artifacts, derives timestamps and counts, resolves active directive/system-view metadata from orchestration state, and returns one normalized bindings dict. Callers that only compare existing projections can disable orchestration refresh to avoid self-invalidating the check.
    - Guarantee: Returns a dict with stable bootstrap binding keys even when optional artifacts are missing.
    - Fails: None.
    - When-needed: Open when a projection refresh or debugging pass needs to see exactly which disk artifacts feed the live bootstrap block.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::find_pipeline_state_path; system/lib/agent_bootstrap_projection.py::load_agent_bootstrap_config
    - Navigation-group: kernel_lib
    """
    from system.control.orchestration import load_orchestration_state
    from system.lib.phase_activation import load_explicit_active_phase

    cfg = dict(config or load_agent_bootstrap_config(repo_root))
    src = cfg.get("source_paths") or {}
    if not isinstance(src, dict):
        src = {}

    explicit_activation = load_explicit_active_phase(repo_root) or {}

    ps_path = pipeline_state_path or find_pipeline_state_path(repo_root)
    ps: dict[str, Any] | None = None
    if ps_path and ps_path.is_file():
        ps = _safe_load_json(ps_path)

    fs_path = factory_state_path
    if fs_path is None:
        fs_rel = str(src.get("factory_state") or "tools/meta/factory/factory_state.json").strip()
        fs_path = repo_root / fs_rel
    fs = _safe_load_json(fs_path) if fs_path and fs_path.is_file() else None

    sm_rel = str(src.get("system_map") or "codex/doctrine/system_map.json").strip()
    sm_path = repo_root / sm_rel
    sm = _safe_load_json(sm_path) if sm_path.is_file() else None
    sm_gen = None
    if sm:
        sm_gen = sm.get("generated_at")
    if not sm_gen:
        sm_gen = _file_mtime_iso(sm_path)

    dr_rel = str(src.get("doctrine_runtime") or "codex/doctrine/doctrine_runtime.json").strip()
    dr_path = repo_root / dr_rel
    dr_mtime = _file_mtime_iso(dr_path)

    orch_rel = str(src.get("orchestration_state") or "tools/meta/control/orchestration_state.json").strip()
    orch_path = repo_root / orch_rel
    try:
        orch = load_orchestration_state(repo_root=repo_root, refresh=refresh_orchestration)
    except Exception:
        orch = _safe_load_json(orch_path) if orch_path.is_file() else None
    orch_event_log = (orch or {}).get("event_log") if isinstance((orch or {}).get("event_log"), Mapping) else {}
    orch_coordination = (orch or {}).get("coordination") if isinstance((orch or {}).get("coordination"), Mapping) else {}
    orch_directive = orch_coordination.get("active_directive") if isinstance(orch_coordination.get("active_directive"), Mapping) else {}
    orch_system_view = orch_coordination.get("system_view") if isinstance(orch_coordination.get("system_view"), Mapping) else {}
    orch_current_owner = orch_coordination.get("current_owner") if isinstance(orch_coordination.get("current_owner"), Mapping) else {}
    orch_next_handoff = orch_coordination.get("next_handoff") if isinstance(orch_coordination.get("next_handoff"), Mapping) else {}
    orch_event_log_rel = str(
        (orch_event_log or {}).get("path")
        or src.get("orchestration_event_log")
        or ""
    ).strip() or None

    focus_rel = str(src.get("documentation_route_focus") or "tools/meta/control/documentation_route_focus.json").strip()
    focus_path = repo_root / focus_rel
    focus = _safe_load_json(focus_path) if focus_path.is_file() else None

    shards_rel: str | None = None
    shard_count: int | None = None
    explicit_family_dir = str(explicit_activation.get("family_dir") or "").strip() or None
    explicit_family_number = str(explicit_activation.get("phase_number") or "").strip()
    if explicit_family_number:
        explicit_family_number = explicit_family_number.split(".", 1)[0].strip()
    explicit_family_number = explicit_family_number or _family_number_from_dir(explicit_family_dir)
    if ps:
        sp = str(ps.get("shards_path") or "").strip()
        if sp:
            shards_rel = sp
        elif str(ps.get("phase_dir") or "").strip():
            shards_rel = f"{str(ps['phase_dir']).strip()}/extracted_shards.json"
    if not shards_rel:
        if explicit_family_dir:
            shards_rel = f"{explicit_family_dir}/extracted_shards.json"
        else:
            d = str(src.get("default_extracted_shards") or "").strip()
            shards_rel = d or None
    if shards_rel:
        shard_path = repo_root / shards_rel
        sd = _safe_load_json(shard_path)
        if sd and isinstance(sd.get("shards"), list):
            shard_count = len(sd["shards"])

    active_directive_path = _existing_rel_from_binding(
        repo_root,
        (orch_directive or {}).get("path") if orch_directive else None,
    )

    factory_projection = _factory_state_projection(repo_root, fs, fs_path)

    bindings: dict[str, Any] = {
        "pipeline_state_rel": _rel(repo_root, ps_path) if ps_path and ps_path.is_file() else None,
        "pipeline_stage": (ps or {}).get("stage"),
        "controller_phase": (ps or {}).get("phase"),
        "phase_dir": (ps or {}).get("phase_dir"),
        "family_dir": (ps or {}).get("family_dir"),
        "active_family_dir": explicit_family_dir,
        "active_family_number": explicit_family_number,
        "active_phase_id": explicit_activation.get("phase_id"),
        "active_phase_number": explicit_activation.get("phase_number"),
        "active_phase_title": explicit_activation.get("phase_title"),
        "active_phase_dir": explicit_activation.get("phase_dir"),
        "cycle": (ps or {}).get("cycle"),
        "orchestration_state_rel": orch_rel if orch_path.is_file() else None,
        "orchestration_active_driver": (orch or {}).get("active_driver") if orch else None,
        "orchestration_gate_reason": ((orch or {}).get("gate") or {}).get("gate_reason") if orch else None,
        "orchestration_event_log_rel": orch_event_log_rel,
        "orchestration_latest_event_id": (orch_event_log or {}).get("latest_event_id") if orch_event_log else None,
        "orchestration_current_owner": (orch_current_owner or {}).get("actor_id") if orch_current_owner else None,
        "orchestration_next_handoff": (orch_next_handoff or {}).get("actor_id") if orch_next_handoff else None,
        "active_directive_path": active_directive_path,
        "active_directive_summary": (orch_directive or {}).get("summary") if active_directive_path else None,
        "system_view_rel": (orch_system_view or {}).get("path") if orch_system_view else None,
        "system_view_file_count": (orch_system_view or {}).get("file_count") if orch_system_view else None,
        "documentation_route_focus_rel": focus_rel if focus_path.is_file() else None,
        "documentation_route_focus_active_preset": (focus or {}).get("active_preset_id") if focus else None,
        "system_map_generated_at": sm_gen,
        "doctrine_runtime_mtime_iso": dr_mtime,
        "extracted_shards_rel": shards_rel,
        "extracted_shard_count": shard_count,
    }
    bindings.update(factory_projection)
    return bindings


def render_live_markdown(
    bindings: Mapping[str, Any],
    *,
    per_agent_rows: list[Mapping[str, Any]] | None = None,
    system_facts_at_a_glance: Mapping[str, Any] | None = None,
    agent_operating_packet: Mapping[str, Any] | None = None,
    minimum_read_sets: Mapping[str, Any] | None = None,
    bootstrap_sequence: list[Mapping[str, Any]] | None = None,
    situation_routes: list[Mapping[str, Any]] | None = None,
    actor_context_surfaces: list[Mapping[str, Any]] | None = None,
    runtime_control_plane: Mapping[str, Any] | None = None,
    compact_command_surface: Mapping[str, Any] | None = None,
    type_a_convergence_contract: Mapping[str, Any] | None = None,
) -> str:
    """
    [ACTION]
    - Teleology: Render the markdown block injected into AGENTS.md from normalized bootstrap data.
    - Mechanism: Formats the live bindings, per-agent rows, bootstrap sequence, runtime-control-plane data, situation routes, actor surfaces, and minimum-read-set registry into one markdown string.
    - Guarantee: Returns markdown ending with a trailing newline, suitable for replace_marked_region().
    - Fails: None.
    - When-needed: Open when the AGENTS live block content itself needs to be traced or regenerated from already-normalized inputs.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::run_projection; system/lib/agent_bootstrap_projection.py::replace_marked_region
    """
    lines: list[str] = [
        "### Live context (from disk)",
        "",
        "_This block is regenerated by the builder; do not edit by hand._",
        "",
        "**Refresh:**",
        "",
        "```bash",
        "./repo-python tools/meta/factory/build_agent_bootstrap_projection.py",
        "```",
        "",
        "**Pipeline (runtime-eligible active state):**",
    ]
    mrs, situations = _apply_active_family_bootstrap_overrides(
        bindings,
        minimum_read_sets=minimum_read_sets,
        situation_routes=situation_routes,
    )
    if bindings.get("pipeline_state_rel"):
        lines.append(
            f"- State: `{bindings['pipeline_state_rel']}` — stage `{bindings.get('pipeline_stage')}`, "
            f"controller phase `{bindings.get('controller_phase')}`, cycle `{bindings.get('cycle')}`"
        )
        if bindings.get("phase_dir"):
            lines.append(f"- Phase dir: `{bindings['phase_dir']}`")
    else:
        lines.append("- No `pipeline_state.json` resolved (no explicit active phase or no file under `obsidian/`).")
    if bindings.get("active_phase_number") or bindings.get("active_phase_id"):
        lines.append(
            f"- Explicit active phase: `{bindings.get('active_phase_id') or bindings.get('active_phase_number')}`"
            f" — `{bindings.get('active_phase_title') or 'untitled phase'}`"
        )
        if bindings.get("active_phase_dir"):
            lines.append(f"- Explicit active dir: `{bindings.get('active_phase_dir')}`")

    lines.extend(
        [
            "",
            "**Factory runner:**",
            _factory_state_markdown_line(bindings) or "- `tools/meta/factory/factory_state.json` — factory state unavailable",
            "",
            "**Holographic / control plane:**",
            f"- `system_map.json` generated_at: `{bindings.get('system_map_generated_at')}`",
            f"- `doctrine_runtime.json` mtime (UTC): `{bindings.get('doctrine_runtime_mtime_iso')}`",
            f"- `orchestration_state.json`: `{bindings.get('orchestration_active_driver')}` gate `{bindings.get('orchestration_gate_reason') or 'none'}`",
        ]
    )
    if bindings.get("orchestration_event_log_rel"):
        lines.append(
            f"- `orchestration_events.jsonl`: `{bindings.get('orchestration_event_log_rel')}`"
        )
    if bindings.get("documentation_route_focus_rel"):
        lines.append(
            f"- `documentation_route_focus.json`: `{bindings.get('documentation_route_focus_active_preset') or 'n/a'}`"
        )
    if bindings.get("active_directive_path"):
        lines.append(
            f"- `focus_directive.json`: `{bindings.get('active_directive_path')}` — `{bindings.get('active_directive_summary') or 'active directive'}`"
        )
    if bindings.get("system_view_rel"):
        lines.append(
            f"- `system_view.json`: `{bindings.get('system_view_rel')}` — file_count `{bindings.get('system_view_file_count')}`"
        )

    lines.extend(["", "**Extracted shards (factory lane backlog):**"])
    if bindings.get("extracted_shards_rel"):
        cnt = bindings.get("extracted_shard_count")
        lines.append(f"- `{bindings['extracted_shards_rel']}` — shard count: {cnt if cnt is not None else 'n/a'}")
    else:
        lines.append("- Not resolved from pipeline state or defaults.")

    if per_agent_rows:
        lines.extend(["", "**Multi-agent entry points (stable):**", ""])
        lines.append("| Agent | Read first | Primary delta |")
        lines.append("|-------|------------|---------------|")
        for row in per_agent_rows:
            agent = str(row.get("agent") or "").replace("|", "\\|")
            rf = str(row.get("read_first") or "").replace("|", "\\|")
            pd = str(row.get("primary_delta") or "").replace("|", "\\|")
            lines.append(f"| **{agent}** | {rf} | {pd} |")

    lines.extend(
        render_system_facts_at_a_glance(
            system_facts_at_a_glance,
            max_rows=6,
        )
    )
    sequence = normalize_bootstrap_sequence(bootstrap_sequence)
    # Bootstrap sequence is rendered ONLY via render_compact_command_surface
    # ("Bootstrap path: `cmd1`, `cmd2`, ...") per pri_121 / pri_131. The
    # previously-rendered "Bootstrap sequence (canonical):" verbose block was
    # ~1615 bytes of redundant per-step `why` prose; full step rationale lives
    # in agent_bootstrap_live.json::bootstrap_sequence (sidecar route).
    lines.extend(
        render_compact_command_surface(
            compact_command_surface,
            bootstrap_sequence=sequence or None,
        )
    )

    runtime_plane = normalize_runtime_control_plane(runtime_control_plane)
    if runtime_plane:
        lines.extend(["", "**Runtime control plane:**", ""])
        if runtime_plane.get("snapshot_path"):
            lines.append(f"- Snapshot: `{runtime_plane['snapshot_path']}`")
        if runtime_plane.get("event_log_path"):
            lines.append(f"- Event log: `{runtime_plane['event_log_path']}`")
        if runtime_plane.get("control_room_command"):
            lines.append(f"- Control room: `{runtime_plane['control_room_command']}`")
        if runtime_plane.get("overnight_write_command"):
            lines.append(f"- Refresh write: `{runtime_plane['overnight_write_command']}`")
        if runtime_plane.get("docs_route_command"):
            lines.append(f"- Docs route: `{runtime_plane['docs_route_command']}`")

    if situations:
        lines.extend([
            "",
            "**Situation routes (canonical next read):**",
            "",
            "_Compressed per pri_121 / std_agent_entry_surface.json::compression_via_projection_contract. `set` (MRS id) and `fallback` live in `codex/doctrine/agent_bootstrap_live.json::situation_routes`; expand a row via `./repo-python kernel.py --docs-route <query>` or follow `next`._",
            "",
        ])
        rendered_situations = situations[:AGENTS_SITUATION_ROUTE_RENDER_LIMIT]
        for row in rendered_situations:
            label = str(row.get("label") or row["situation_id"]).strip()
            use_when = str(row.get("use_when") or "").strip()
            if len(use_when) > 70:
                cut = use_when[:70].rsplit(" ", 1)[0]
                use_when = cut + "…"
            principle = str(row.get("principle_anchor") or "").strip()
            id_part = f"`{row['situation_id']}`"
            if principle:
                id_part += f" ({principle})"
            headline = f"- {id_part} — {label}"
            if use_when:
                headline += f". {use_when}"
            lines.append(headline)
            details: list[str] = [f"route `{row['route_command']}`"]
            if row.get("canonical_next_read"):
                details.append(f"→ `{row['canonical_next_read']}`")
            delivery = row.get("actor_delivery") if isinstance(row.get("actor_delivery"), Mapping) else {}
            deliver_to_cold_start = delivery.get("decision") == "deliver_to_cold_start"
            if deliver_to_cold_start and row.get("fallback_command"):
                details.append(f"fallback `{row['fallback_command']}`")
            route_targets = row.get("route_targets")
            if deliver_to_cold_start and row.get("standard_anchor") and not route_targets:
                details.append(f"standard `{row['standard_anchor']}`")
            if isinstance(route_targets, list) and route_targets:
                target_bits, more_targets = _route_target_projection_bits(route_targets)
                if target_bits:
                    suffix = f" (+{more_targets})" if more_targets > 0 else ""
                    details.append(f"targets {', '.join(target_bits)}{suffix}")
            if row.get("freshness_command"):
                details.append(f"freshness `{row['freshness_command']}`")
            lines.append(f"  - {'; '.join(details)}")
        hidden_count = max(0, len(situations) - len(rendered_situations))
        if hidden_count:
            lines.append(
                f"- _… +{hidden_count} more routes in "
                "`codex/doctrine/agent_bootstrap_live.json::situation_routes`; "
                "browse via `./repo-python kernel.py --docs-route <query>`._"
            )
        hidden_delivery = _hidden_actor_delivery_anchor_rows(situations, rendered_situations)
        if hidden_delivery:
            anchor_bits: list[str] = []
            for row in hidden_delivery:
                delivery = row.get("actor_delivery") if isinstance(row.get("actor_delivery"), Mapping) else {}
                tokens = [
                    str(token).strip()
                    for token in (delivery.get("required_tokens") or [])
                    if str(token).strip()
                ]
                if tokens:
                    anchor_bits.append(" · ".join(f"`{token}`" for token in tokens[:3]))
            if anchor_bits:
                lines.append(f"- Delivery anchors: {'; '.join(anchor_bits)}.")

    actors = normalize_actor_context_surfaces(actor_context_surfaces, minimum_read_sets=mrs or None)
    actor_packets = build_actor_bootstrap_packets(actors, minimum_read_sets=mrs or None)
    packet_by_actor = {
        str(packet.get("actor_id")): packet
        for packet in actor_packets
        if packet.get("actor_id")
    }
    if actors:
        lines.extend([
            "",
            "**Actor context surfaces:**",
            "",
            "_Compressed per pri_121. `set` (MRS id) and `surface` (runtime surface id) live in `agent_bootstrap_live.json::actor_context_surfaces`; the headline + first command + first read is the Rosetta Stone seed._",
            "",
        ])
        for row in actors:
            lines.append(f"- `{row['actor_id']}` — {row['label']}")
            details: list[str] = []
            if row.get("primary_commands"):
                details.append(f"cmd `{row['primary_commands'][0]}`")
            if row.get("read_order"):
                details.append(f"read `{row['read_order'][0]}`")
            if details:
                lines.append(f"  - {'; '.join(details)}")

    lines.extend(render_type_a_convergence_contract(type_a_convergence_contract))

    if mrs:
        lines.extend(
            [
                "",
                "**Minimum read set registry:**",
                "",
            ]
        )
        lines.append(
            f"- Total available sets: {len(mrs)}. Full id list lives in "
            f"`codex/doctrine/agent_bootstrap_live.json::minimum_read_sets` "
            f"(builder-projected sidecar) and `codex/doctrine/agent_bootstrap.json::minimum_read_sets` (source)."
        )
        lines.append("- Resolve the actual bounded path set with `./repo-python kernel.py --docs-route <query-or-path>` (path list returned in `payload.minimum_read_set.paths`).")

    return "\n".join(lines).rstrip() + "\n"


def build_live_payload(
    bindings: Mapping[str, Any],
    *,
    generated_at: str,
    source_event: str | None,
    per_agent_rows: list[Mapping[str, Any]] | None,
    system_facts_at_a_glance: Mapping[str, Any] | None = None,
    agent_operating_packet: Mapping[str, Any] | None = None,
    minimum_read_sets: Mapping[str, Any] | None = None,
    bootstrap_sequence: list[Mapping[str, Any]] | None = None,
    situation_routes: list[Mapping[str, Any]] | None = None,
    actor_context_surfaces: list[Mapping[str, Any]] | None = None,
    runtime_control_plane: Mapping[str, Any] | None = None,
    compact_command_surface: Mapping[str, Any] | None = None,
    instruction_discovery_facts: Mapping[str, Any] | None = None,
    type_a_convergence_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the JSON sidecar that preserves the full live bootstrap snapshot for machine consumers.
    - Mechanism: Packages live bindings plus normalized optional sections into an `agent_bootstrap_live` payload.
    - Guarantee: Returns a dict ready to serialize as codex/doctrine/agent_bootstrap_live.json.
    - Fails: None.
    - When-needed: Open when machine consumers need the exact JSON projection emitted alongside the markdown bootstrap block.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::run_projection; codex/doctrine/agent_bootstrap.json
    """
    payload: dict[str, Any] = {
        "kind": "agent_bootstrap_live",
        "schema_version": "agent_bootstrap_live_v0",
        "generated_at": generated_at,
        "source_event": source_event,
        "live_bindings": dict(bindings),
        "per_agent_rows": list(per_agent_rows or []),
    }
    mrs, situations = _apply_active_family_bootstrap_overrides(
        bindings,
        minimum_read_sets=minimum_read_sets,
        situation_routes=situation_routes,
    )
    if mrs:
        payload["minimum_read_sets"] = mrs
    sequence = normalize_bootstrap_sequence(bootstrap_sequence)
    if sequence:
        payload["bootstrap_sequence"] = sequence
    if situations:
        payload["situation_routes"] = situations
    actors = normalize_actor_context_surfaces(actor_context_surfaces, minimum_read_sets=mrs or None)
    if actors:
        payload["actor_context_surfaces"] = actors
        payload["actor_bootstrap_packets"] = build_actor_bootstrap_packets(
            actors,
            minimum_read_sets=mrs or None,
        )
    runtime_plane = normalize_runtime_control_plane(runtime_control_plane)
    if runtime_plane:
        payload["runtime_control_plane"] = runtime_plane
    compact_commands = normalize_compact_command_surface(compact_command_surface)
    if compact_commands:
        payload["compact_command_surface"] = compact_commands
    if isinstance(instruction_discovery_facts, Mapping) and instruction_discovery_facts:
        payload["instruction_discovery"] = dict(instruction_discovery_facts)
    if isinstance(system_facts_at_a_glance, Mapping) and system_facts_at_a_glance:
        payload["system_facts_at_a_glance"] = dict(system_facts_at_a_glance)
    if isinstance(agent_operating_packet, Mapping) and agent_operating_packet:
        payload["agent_operating_packet"] = build_agent_operating_packet_strip(agent_operating_packet)
    convergence = normalize_type_a_convergence_contract(type_a_convergence_contract)
    if convergence:
        payload["type_a_convergence_contract"] = convergence
    return payload


def _display_bytes(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "n/a"


def render_instruction_discovery_markdown(
    facts: Mapping[str, Any],
    bindings: Mapping[str, Any],
    *,
    bootstrap_sequence: list[Mapping[str, Any]] | None = None,
    situation_routes: list[Mapping[str, Any]] | None = None,
    system_facts_at_a_glance: Mapping[str, Any] | None = None,
    agent_operating_packet: Mapping[str, Any] | None = None,
) -> str:
    """
    [ACTION]
    - Teleology: Render the managed live-facts block inside the compact root instruction seed that Codex actually discovers first.
    - Mechanism: Formats effective root instruction path, watched entrypoint byte counts, budget posture, active phase, and bootstrap command chain from resolved disk facts.
    - Guarantee: Returns markdown ending with a trailing newline, suitable for replace_marked_region().
    - Fails: None.
    - When-needed: Open when AGENTS.override.md needs dynamic facts refreshed without hand-maintaining volatile counts or active runtime state.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::resolve_instruction_discovery_facts; codex/doctrine/agent_bootstrap.json::instruction_discovery
    """
    effective = facts.get("effective_root_instruction_path") or "none"
    seed_path = facts.get("seed_path") or "AGENTS.override.md"
    deep_hub = facts.get("deep_hub_path") or "AGENTS.md"
    default_budget = facts.get("project_doc_max_bytes_default")
    seed_budget = facts.get("compact_seed_budget_bytes")
    lines: list[str] = [
        "### Instruction Discovery - Live Facts",
        "",
        "_This block is regenerated from `codex/doctrine/agent_bootstrap.json` plus disk state. Do not edit by hand._",
        "",
        f"- Provider lane: `{facts.get('provider') or 'codex'}`",
        f"- Effective root instruction: `{effective}`",
        f"- Compact seed: `{seed_path}` (budget `{_display_bytes(seed_budget)}` bytes)",
        f"- Deep hub: `{deep_hub}` (watch budget `{_display_bytes(default_budget)}` bytes)",
        f"- Override active: `{bool(facts.get('override_active'))}`",
    ]
    if facts.get("official_source"):
        lines.append(f"- Upstream rule reference: `{facts['official_source']}`")
    if bindings.get("active_phase_id") or bindings.get("active_phase_number"):
        phase_id = bindings.get("active_phase_id") or bindings.get("active_phase_number")
        lines.append(
            f"- Active phase: `{phase_id}` - `{bindings.get('active_phase_title') or 'untitled phase'}`"
        )
    elif bindings.get("pipeline_state_rel"):
        lines.append(
            f"- Pipeline state: `{bindings['pipeline_state_rel']}` - stage `{bindings.get('pipeline_stage')}`"
        )
    if bindings.get("orchestration_gate_reason") or bindings.get("orchestration_active_driver"):
        lines.append(
            f"- Orchestration: driver `{bindings.get('orchestration_active_driver') or 'none'}`, "
            f"gate `{bindings.get('orchestration_gate_reason') or 'none'}`"
        )
    if bindings.get("documentation_route_focus_active_preset"):
        lines.append(f"- Docs focus: `{bindings.get('documentation_route_focus_active_preset')}`")

    lines.extend(["", "| Instruction file | Bytes | Budget | Status |", "|---|---:|---:|---|"])
    for record in facts.get("files") or []:
        if not isinstance(record, Mapping):
            continue
        path = record.get("path") or ""
        lines.append(
            f"| `{path}` | {_display_bytes(record.get('bytes'))} | "
            f"{_display_bytes(record.get('budget_bytes'))} | `{record.get('budget_status') or 'unknown'}` |"
        )

    oversized = [str(path) for path in (facts.get("oversized_paths") or []) if str(path)]
    if oversized:
        joined = ", ".join(f"`{path}`" for path in oversized)
        lines.append("")
        lines.append(f"- Over-budget watched files: {joined}")
    system_fact_rows = render_system_facts_at_a_glance(
        system_facts_at_a_glance,
        max_rows=4,
        heading="**System facts at a glance:**",
    )
    if system_fact_rows:
        lines.extend(system_fact_rows)
    agent_packet_rows = render_agent_operating_packet_markdown(
        agent_operating_packet,
        heading="**Agent operating packet:**",
        compact=True,
    )
    if agent_packet_rows:
        lines.extend(agent_packet_rows)
    sequence = normalize_bootstrap_sequence(bootstrap_sequence)
    if sequence:
        chain = " -> ".join(f"`{step['command']}`" for step in sequence[:4])
        lines.append(f"- Bootstrap chain: {chain}")
        lines.append(
            "- Bootstrap owner/freshness: owner "
            "[agent_bootstrap_live.json](codex/doctrine/agent_bootstrap_live.json) / "
            "[std_agent_entry_surface.json](codex/standards/std_agent_entry_surface.json); "
            "check `./repo-python tools/meta/factory/check_agent_bootstrap_projection.py`."
        )
    state_axis_route = _state_axis_rosetta_route(situation_routes)
    if state_axis_route:
        route_command = str(
            state_axis_route.get("route_command")
            or "./repo-python kernel.py --facts --band cluster_flag"
        )
        lines.append(
            "- State-axis route: State adjectives route through facts; overview "
            f"`{route_command}`; exact axes `--facts --facts-tag <tag>` / "
            "`--facts --facts-facet <facet>`; private/public use context-pack/System Atlas; "
            "projection gaps use `--navigation-metabolism`."
        )
        lines.append(
            "- State-axis owner/freshness: owner "
            "[std_derived_fact.json](codex/standards/std_derived_fact.json) / "
            "[system facts projection](state/system_atlas/system_facts_at_a_glance.json); "
            "freshness `./repo-python tools/meta/factory/build_fact_hologram.py --check`."
        )
    lines.append(
        "- Projection freshness: owner "
        "[agent_bootstrap_projection.py](system/lib/agent_bootstrap_projection.py); "
        "check `./repo-python tools/meta/factory/check_agent_bootstrap_projection.py`; "
        "refresh `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py`."
    )
    return "\n".join(lines).rstrip() + "\n"


def stabilize_instruction_discovery_target(
    seed_text: str,
    facts: Mapping[str, Any],
    bindings: Mapping[str, Any],
    *,
    bootstrap_sequence: list[Mapping[str, Any]] | None = None,
    situation_routes: list[Mapping[str, Any]] | None = None,
    system_facts_at_a_glance: Mapping[str, Any] | None = None,
    agent_operating_packet: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], str, str]:
    """
    [ACTION]
    - Teleology: Make the instruction seed's self-size fact describe the post-projection file, not the stale pre-replacement file.
    - Mechanism: Renders the live block, splices it into the current seed text, updates the seed file-size row from the projected text byte count, and repeats until the rendered text stabilizes.
    - Guarantee: Returns updated facts, rendered inner markdown, and complete projected seed text.
    - Fails: Propagates marker errors from replace_marked_region when the configured target lacks markers.
    - When-needed: Open when AGENTS.override.md carries dynamic facts about itself and must not report a pre-refresh byte count.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::render_instruction_discovery_markdown
    """
    current = dict(facts)
    begin = str(current.get("begin_marker") or DEFAULT_INSTRUCTION_DISCOVERY["begin_marker"])
    end = str(current.get("end_marker") or DEFAULT_INSTRUCTION_DISCOVERY["end_marker"])
    seed_path = str(current.get("seed_path") or current.get("markdown_target") or "AGENTS.override.md")
    seed_budget = _positive_int(current.get("compact_seed_budget_bytes"), int(DEFAULT_INSTRUCTION_DISCOVERY["compact_seed_budget_bytes"]))
    default_budget = _positive_int(current.get("project_doc_max_bytes_default"), int(DEFAULT_INSTRUCTION_DISCOVERY["project_doc_max_bytes_default"]))
    rendered = ""
    projected = seed_text
    previous_size: int | None = None
    for _ in range(5):
        rendered = render_instruction_discovery_markdown(
            current,
            bindings,
            bootstrap_sequence=bootstrap_sequence,
            situation_routes=situation_routes,
            system_facts_at_a_glance=system_facts_at_a_glance,
            agent_operating_packet=agent_operating_packet,
        )
        projected = replace_marked_region(seed_text, rendered, begin, end)
        projected_size = len(projected.encode("utf-8"))
        files: list[dict[str, Any]] = []
        seed_seen = False
        for record_raw in current.get("files") or []:
            if not isinstance(record_raw, Mapping):
                continue
            record = dict(record_raw)
            if record.get("path") == seed_path:
                seed_seen = True
                record["exists"] = True
                record["non_empty"] = projected_size > 0
                record["bytes"] = projected_size
                record["budget_bytes"] = seed_budget
                record["budget_status"] = "over_budget" if projected_size > seed_budget else "within_budget"
            files.append(record)
        if not seed_seen:
            files.insert(
                0,
                {
                    "path": seed_path,
                    "exists": True,
                    "non_empty": projected_size > 0,
                    "bytes": projected_size,
                    "budget_bytes": seed_budget,
                    "budget_status": "over_budget" if projected_size > seed_budget else "within_budget",
                },
            )
        current["files"] = files
        current["oversized_paths"] = [
            str(record.get("path"))
            for record in files
            if record.get("budget_status") == "over_budget"
        ]
        current["project_doc_max_bytes_default"] = default_budget
        current["compact_seed_budget_bytes"] = seed_budget
        if previous_size == projected_size:
            break
        previous_size = projected_size
    rendered = render_instruction_discovery_markdown(
        current,
        bindings,
        bootstrap_sequence=bootstrap_sequence,
        situation_routes=situation_routes,
        system_facts_at_a_glance=system_facts_at_a_glance,
        agent_operating_packet=agent_operating_packet,
    )
    projected = replace_marked_region(seed_text, rendered, begin, end)
    return current, rendered, projected


def build_injection_strip(
    bindings: Mapping[str, Any],
    *,
    max_bytes: int,
    agent_operating_packet: Mapping[str, Any] | None = None,
    minimum_read_set_ids: list[str] | None = None,
    situation_route_ids: list[str] | None = None,
    actor_context_surface_ids: list[str] | None = None,
    type_a_convergence: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the size-bounded bootstrap injection strip used for compact context handoff.
    - Mechanism: Starts from a slim binding subset, optionally adds section ids, then drops lower-priority keys until the JSON encoding fits within max_bytes.
    - Guarantee: Returns a JSON-serializable dict whose UTF-8 encoding is no larger than max_bytes, or a final truncated note payload if necessary.
    - Fails: None.
    - When-needed: Open when a bridge or agent handoff needs the exact truncation policy for the bootstrap injection strip.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::build_live_payload; system/lib/agent_bootstrap_projection.py::run_projection
    """
    slim: dict[str, Any] = {
        "kind": "agent_bootstrap_injection_strip",
        "pipeline_stage": bindings.get("pipeline_stage"),
        "controller_phase": bindings.get("controller_phase"),
        "phase_dir": bindings.get("phase_dir"),
        "factory_state_freshness": bindings.get("factory_state_freshness"),
        "factory_state_role": bindings.get("factory_state_role"),
        "factory_state_live": bindings.get("factory_state_live"),
        "orchestration_active_driver": bindings.get("orchestration_active_driver"),
        "orchestration_gate_reason": bindings.get("orchestration_gate_reason"),
        "orchestration_latest_event_id": bindings.get("orchestration_latest_event_id"),
        "documentation_route_focus_active_preset": bindings.get("documentation_route_focus_active_preset"),
        "active_directive_path": bindings.get("active_directive_path"),
        "system_view_rel": bindings.get("system_view_rel"),
        "system_map_generated_at": bindings.get("system_map_generated_at"),
        "extracted_shards_rel": bindings.get("extracted_shards_rel"),
        "extracted_shard_count": bindings.get("extracted_shard_count"),
    }
    if minimum_read_set_ids:
        slim["minimum_read_set_ids"] = list(minimum_read_set_ids)
    if situation_route_ids:
        slim["situation_route_ids"] = list(situation_route_ids)
    if actor_context_surface_ids:
        slim["actor_context_surface_ids"] = list(actor_context_surface_ids)
    if type_a_convergence:
        slim["type_a_convergence"] = str(type_a_convergence)
    if isinstance(agent_operating_packet, Mapping) and agent_operating_packet:
        slim["agent_operating_packet"] = build_agent_operating_packet_strip(agent_operating_packet)
    text = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
    if len(text.encode("utf-8")) <= max_bytes:
        return slim
    # Truncate by re-serializing smaller dict
    for drop in (
        "minimum_read_set_ids",
        "situation_route_ids",
        "actor_context_surface_ids",
        "type_a_convergence",
        "documentation_route_focus_active_preset",
        "active_directive_path",
        "system_view_rel",
        "factory_state_live",
        "factory_state_role",
        "factory_state_freshness",
        "extracted_shard_count",
        "extracted_shards_rel",
        "system_map_generated_at",
        "agent_operating_packet",
    ):
        slim.pop(drop, None)
        text = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
        if len(text.encode("utf-8")) <= max_bytes:
            return slim
    return {"kind": "agent_bootstrap_injection_strip", "note": "truncated"}


def replace_marked_region(
    content: str,
    inner: str,
    begin: str,
    end: str,
) -> str:
    """
    [ACTION]
    - Teleology: Replace one marked region in a markdown document with freshly rendered bootstrap content.
    - Mechanism: Splits on begin and end markers and splices the new inner payload between them.
    - Guarantee: Returns the updated content string when both markers are present.
    - Fails: Raises ValueError("marker_missing") when either marker is absent.
    - When-needed: Open when a projection write needs the exact splice rule for the managed AGENTS marked region.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::run_projection
    """
    if begin not in content or end not in content:
        raise ValueError("marker_missing")
    pre, rest = content.split(begin, 1)
    _, post = rest.split(end, 1)
    return pre + begin + "\n" + inner + end + post


def _state_axis_rosetta_route(situation_routes: list[Mapping[str, Any]] | None) -> Mapping[str, Any] | None:
    for row in situation_routes or []:
        if not isinstance(row, Mapping):
            continue
        if row.get("situation_id") == "system_state_axis_overview":
            return row
    return None


def render_adapter_markdown(
    bindings: Mapping[str, Any],
    *,
    adapter_role: str,
    actor_id: str,
    actor_row: Mapping[str, Any] | None = None,
    system_facts_at_a_glance: Mapping[str, Any] | None = None,
    bootstrap_sequence: list[Mapping[str, Any]] | None = None,
    situation_routes: list[Mapping[str, Any]] | None = None,
    type_a_convergence_contract: Mapping[str, Any] | None = None,
    canonical_option_surface_routes: Mapping[str, Any] | None = None,
    hub_path: str = "AGENTS.md",
) -> str:
    """
    [ACTION]
    - Teleology: Render the compact adapter-specific live block hosted inside CLAUDE.md or CODEX.md so agent-specific bootstrap hints do not drift as hand-authored prose.
    - Mechanism: Pulls the live pipeline snapshot, the one actor_context_surfaces row for this adapter's actor, a one-line compact bootstrap sequence, and a handoff pointer to the shared hub into a small markdown block.
    - Guarantee: Returns markdown ending with a trailing newline, suitable for replace_marked_region() against the adapter-specific marker pair.
    - Fails: None.
    - When-needed: Open when the CLAUDE.md or CODEX.md managed region needs to be refreshed; or when extending the adapter block shape.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::run_projection; system/lib/agent_bootstrap_projection.py::render_live_markdown
    - Navigation-group: kernel_lib
    """
    role_label = {
        "claude_adapter": "Claude Code adapter",
        "codex_adapter": "Codex adapter",
    }.get(adapter_role, "Agent adapter")

    lines: list[str] = [
        f"### {role_label} — live context (from disk)",
        "",
        "_This block is regenerated by the builder from `codex/doctrine/agent_bootstrap.json`; do not edit by hand._",
        "",
        "**Refresh:** `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py`",
        "",
        "**Live pipeline snapshot:**",
    ]
    if bindings.get("active_phase_id") or bindings.get("active_phase_number"):
        phase_id = bindings.get("active_phase_id") or bindings.get("active_phase_number")
        phase_title = bindings.get("active_phase_title") or "untitled phase"
        lines.append(f"- Active phase: `{phase_id}` — `{phase_title}`")
    elif bindings.get("pipeline_state_rel"):
        lines.append(
            f"- Pipeline state: `{bindings['pipeline_state_rel']}` — stage `{bindings.get('pipeline_stage')}`, "
            f"controller phase `{bindings.get('controller_phase')}`"
        )
    else:
        lines.append("- No explicit active phase resolved.")

    factory_line = _factory_state_markdown_line(bindings, adapter=True)
    if factory_line:
        lines.append(factory_line)
    if bindings.get("orchestration_gate_reason") or bindings.get("orchestration_active_driver"):
        lines.append(
            f"- Orchestration: driver `{bindings.get('orchestration_active_driver') or 'none'}`, "
            f"gate `{bindings.get('orchestration_gate_reason') or 'none'}`"
        )
    if bindings.get("active_directive_path"):
        lines.append(
            f"- Active directive: `{bindings.get('active_directive_path')}` — "
            f"`{bindings.get('active_directive_summary') or 'active directive'}`"
        )

    if actor_row:
        lines.extend(["", f"**Actor context — `{actor_id}`:**"])
        label = actor_row.get("label")
        if label:
            lines.append(f"- {label}")
        mrs_id = actor_row.get("minimum_read_set_id")
        if mrs_id:
            lines.append(f"- Minimum read set: `{mrs_id}`")
        surface_id = actor_row.get("runtime_surface_id")
        if surface_id:
            lines.append(f"- Runtime surface: `{surface_id}`")
        primary_cmds = actor_row.get("primary_commands") or []
        if primary_cmds:
            joined = ", ".join(f"`{cmd}`" for cmd in primary_cmds)
            lines.append(f"- Entry commands: {joined}")
        read_order = actor_row.get("read_order") or []
        if read_order:
            joined = ", ".join(f"`{doc}`" for doc in read_order)
            lines.append(f"- Read order: {joined}")

    lines.extend(
        render_system_facts_at_a_glance(
            system_facts_at_a_glance,
            max_rows=2,
            heading="**System facts at a glance:**",
            compact=True,
        )
    )

    sequence = normalize_bootstrap_sequence(bootstrap_sequence)
    if sequence:
        lines.extend(["", "**Bootstrap sequence (compact):**"])
        compact_handshake = render_compact_bootstrap_handshake(sequence)
        if compact_handshake:
            lines.append(compact_handshake)

    state_axis_route = _state_axis_rosetta_route(situation_routes)
    if state_axis_route:
        route_command = str(
            state_axis_route.get("route_command")
            or "./repo-python kernel.py --facts --band cluster_flag"
        )
        fallback_command = str(
            state_axis_route.get("fallback_command")
            or "./repo-python kernel.py --fact-audit"
        )
        lines.extend(
            [
                "",
                "**State-axis Rosetta:**",
                "- State adjectives route through facts: ask via `--entry` first; "
                f"overview is `{route_command}`; exact axes use "
                "`--facts --facts-tag <tag>` or `--facts --facts-facet <facet>`; "
                "private/public uses context-pack/System Atlas until disclosure facts exist; "
                f"projection gaps use `--navigation-metabolism`; freshness fallback `{fallback_command}`.",
            ]
        )

    if isinstance(canonical_option_surface_routes, Mapping):
        tokens = canonical_option_surface_routes.get("required_tokens") or []
        principle = (
            canonical_option_surface_routes.get("principle_anchor")
            or "pri_128"
        )
        if tokens:
            chain_tokens = [str(tok) for tok in tokens if isinstance(tok, str)]
            entry_cmd = "./repo-python kernel.py --entry \"<task>\""
            kind_atlas_cmd = "./repo-python kernel.py --kind-atlas"
            option_cluster_cmd = (
                "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag"
            )
            option_flag_cmd = (
                "./repo-python kernel.py --option-surface <kind_id> --band flag"
            )
            option_card_cmd = (
                "./repo-python kernel.py --option-surface <kind_id> --band card --ids <id>"
            )
            freshness_cmd = "./repo-python kernel.py --navigation-context-rosetta"
            lines.extend(
                [
                    "",
                    f"**Russian-doll route is a drilldown, not cold-start first move "
                    f"(per {principle} + std_agent_entry_surface.json::first_move_contract):**",
                    f"- Cold-start first move: `{entry_cmd}`. The entry packet's "
                    f"`banned_routes` lists `atlas_as_control_entry` with replacement `--entry`.",
                    f"- After entry selects a kind (or operator browses) — cluster-first for "
                    f"breadth, flag/card for row selection: `{kind_atlas_cmd}` → "
                    f"`{option_cluster_cmd}` → `{option_flag_cmd}` (when narrowing inside the "
                    f"selected cluster) → `{option_card_cmd}`",
                    f"- Freshness: `{freshness_cmd}`",
                    f"- Rule: bespoke trigger flags (`--paper-module`, `--skill-find`, "
                    f"`--annex-inspiration`, `--docs-route`) are lower drilldowns below this lane. "
                    f"Tokens audited: {', '.join(f'`{t}`' for t in chain_tokens)}.",
                ]
            )

    convergence = normalize_type_a_convergence_contract(type_a_convergence_contract)
    if convergence:
        lines.extend(["", "**Type A convergence:**"])
        if convergence.get("summary"):
            lines.append(f"- {convergence['summary']}")
        route = convergence.get("route_command")
        next_read = convergence.get("canonical_next_read")
        if route or next_read:
            bits: list[str] = []
            if route:
                bits.append(f"`{route}`")
            if next_read:
                bits.append(f"`{next_read}`")
            lines.append(f"- Shared route: {' → '.join(bits)}")

    lines.extend([
        "",
        f"**Full hub:** read `{hub_path}` next for the complete routing hologram, skill catalog, "
        "situation routes, and the 7 shared principles.",
        "",
    ])
    return "\n".join(lines) + "\n"


def render_paper_module_index_markdown(repo_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Render the paper-module discoverability block projected into AGENTS.md, CLAUDE.md, and CODEX.md per std_paper_module.json::bootstrap_projection_contract so cold agents see every paper module from the primary bootstrap surfaces without scanning the paper-modules directory.
    - Mechanism: Loads the shared paper-module runtime so the projection resolves from authored markdown while also surfacing sidecar freshness. Pins the configured slug set first, fills the remaining rows by (fan_in_inbound desc, authored asc, slug asc), and emits a compact markdown table bounded by the configured row and region budgets.
    - Guarantee: Returns a trailing-newline markdown block. If the shared runtime cannot load or no modules exist, returns a short fallback block that names the refresh command rather than failing the bootstrap projection.
    - Fails: None.
    - When-needed: Open when the paper-module bootstrap projection needs to be regenerated after a new paper module ships or after build_paper_module_index.py has refreshed the sidecar.
    - Escalates-to: tools/meta/factory/build_paper_module_index.py; codex/standards/std_paper_module.json::bootstrap_projection_contract
    - Navigation-group: kernel_lib
    """
    fallback = (
        "### Paper modules — subsystem ontology (auto-projected)\n"
        "\n"
        "_Paper-module runtime not available. Run_ `./repo-python tools/meta/factory/build_paper_module_index.py` _to regenerate the paper-module surfaces, then rerun this projection._\n"
    )
    try:
        runtime = load_paper_module_runtime(repo_root=repo_root, compare_existing=True)
    except Exception:
        return fallback

    data = runtime.index
    freshness = runtime.current_freshness if isinstance(runtime.current_freshness, Mapping) else {}
    modules = data.get("modules") or []
    if not isinstance(modules, list) or not modules:
        return fallback
    shape = _load_paper_module_projection_shape(repo_root)
    excerpt_budget = int(shape["tldr_excerpt_budget_chars"])
    region_budget = int(shape["total_region_budget_chars"])
    max_rows = max(1, int(shape["max_rows"]))
    pinned_slugs = [slug for slug in shape["pinned_slugs"] if isinstance(slug, str) and slug.strip()]

    def _row_sort_key(m: Mapping[str, Any]) -> tuple[int, str, str]:
        try:
            fan_in = int(m.get("fan_in_inbound") or 0)
        except (TypeError, ValueError):
            fan_in = 0
        return (-fan_in, str(m.get("authored") or ""), str(m.get("slug") or ""))

    modules_sorted = sorted(
        (m for m in modules if isinstance(m, Mapping) and m.get("slug")),
        key=_row_sort_key,
    )
    module_by_slug = {
        str(m.get("slug")).strip(): m
        for m in modules_sorted
        if str(m.get("slug") or "").strip()
    }
    selected: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    pinned_present_count = 0
    for slug in pinned_slugs:
        mod = module_by_slug.get(slug)
        if mod is None:
            continue
        selected.append(mod)
        seen.add(slug)
        pinned_present_count += 1
    for mod in modules_sorted:
        slug = str(mod.get("slug") or "").strip()
        if not slug or slug in seen:
            continue
        selected.append(mod)
        seen.add(slug)
        if len(selected) >= max_rows:
            break

    module_count = len(modules_sorted)
    pinned_label = ", ".join(f"`{slug}`" for slug in pinned_slugs) if pinned_slugs else "none"
    sync_status = str(freshness.get("sync_status") or "unknown")
    sidecar_index_count = freshness.get("index_generated_module_count")
    sidecar_report_count = freshness.get("report_generated_module_count")
    freshness_line = (
        f"Freshness: `in_sync` · authored modules: `{module_count}`"
        if sync_status == "in_sync"
        else (
            f"Freshness: `{sync_status}` · authored `{module_count}`"
            + (
                f" · sidecars `{sidecar_index_count}/{sidecar_report_count}`"
                if sidecar_index_count is not None or sidecar_report_count is not None
                else ""
            )
        )
    )
    lines: list[str] = [
        "### Paper modules — subsystem ontology (auto-projected)",
        "",
        "_Builder-owned discoverability slice. Full inventory: `codex/doctrine/paper_modules/README.md`, `_index.json`, `_validation_report.json`._",
        "",
        f"Pins: {pinned_label} · tail: fan-in desc",
        freshness_line,
    ]
    lines.extend(["", "| Slug | Open this when | Status |", "|---|---|---|"])
    rows: list[str] = []
    for mod in selected:
        slug = str(mod.get("slug") or "").strip()
        previews = mod.get("previews") if isinstance(mod.get("previews"), Mapping) else {}
        preview = str(
            (previews.get("tldr") if previews else "")
            or mod.get("tldr_excerpt")
            or mod.get("title")
            or ""
        ).replace("|", "\\|")
        preview = " ".join(preview.split())
        if len(preview) > excerpt_budget:
            preview = preview[: excerpt_budget - 1].rstrip() + "…"
        status = str(mod.get("status") or "").strip()
        rows.append(f"| `{slug}` | {preview} | `{status}` |")

    footer = [
        "",
        "**Read:** module TLDR, then one `Code loci` row. **Refresh:** `./repo-python tools/meta/factory/build_paper_module_index.py && ./repo-python tools/meta/factory/build_agent_bootstrap_projection.py`.",
    ]

    omitted_count = module_count - len(rows)
    while True:
        overflow = [f"| _… +{omitted_count} more_ | _See_ `README.md` / `_index.json` for the full inventory._ | |"] if omitted_count > 0 else []
        rendered = "\n".join(lines + rows + overflow + footer) + "\n"
        if len(rendered) <= region_budget or len(rows) <= pinned_present_count:
            return rendered
        rows.pop()
        omitted_count += 1


def extract_marked_region(content: str, begin: str, end: str) -> str | None:
    """
    [ACTION]
    - Teleology: Read back the currently projected marked region from a markdown document.
    - Mechanism: Splits on the begin and end markers and trims surrounding blank lines from the inner block.
    - Guarantee: Returns the extracted inner text when both markers exist, otherwise None.
    - Fails: None.
    - When-needed: Open when a caller needs to inspect the current live bootstrap block without rewriting the document.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::replace_marked_region
    """
    if begin not in content or end not in content:
        return None
    rest = content.split(begin, 1)[1]
    inner, _ = rest.split(end, 1)
    return inner.strip("\n")


def _write_text_if_changed(path: Path, text: str) -> bool:
    try:
        old = path.read_text(encoding="utf-8")
    except OSError:
        old = None
    if old == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def load_canonical_option_surface_routes(repo_root: Path) -> Mapping[str, Any] | None:
    """
    [ACTION]
    - Teleology: Load the canonical_option_surface_routes contract from std_agent_entry_surface.json so adapter and live renderers can project the russian-doll route declared by pri_128.
    - Mechanism: Reads the standard JSON, returns the canonical_option_surface_routes mapping if present.
    - Guarantee: Returns a Mapping when the standard exists and declares the contract; otherwise None. Never raises on a missing file.
    - Fails: Returns None for malformed JSON or missing contract; logs nothing.
    """
    std_path = repo_root / "codex" / "standards" / "std_agent_entry_surface.json"
    if not std_path.exists():
        return None
    try:
        import json as _json
        data = _json.loads(std_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    contract = data.get("canonical_option_surface_routes")
    if isinstance(contract, Mapping):
        return contract
    return None


def run_projection(
    repo_root: Path,
    *,
    dry_run: bool = False,
    write_agents: bool = True,
    source_event: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Execute a full bootstrap projection pass from config load through optional file writes.
    - Mechanism: Loads config, normalizes optional sections, resolves live bindings, renders markdown/JSON payloads, and writes sidecars plus marked-region updates unless dry_run is enabled.
    - Guarantee: Returns a result dict describing the bindings, markdown size, and any written targets.
    - Fails: Raises filesystem or marker errors when live writes cannot complete.
    - When-needed: Open when the repo needs a full AGENTS bootstrap refresh or when a caller must inspect the end-to-end projection pipeline.
    - Escalates-to: tools/meta/factory/build_agent_bootstrap_projection.py; codex/doctrine/agent_bootstrap.json
    - Navigation-group: kernel_lib
    """
    cfg = load_agent_bootstrap_config(repo_root)
    markers = cfg.get("markers") or {}
    begin = str(markers.get("begin") or DEFAULT_MARKERS[0])
    end = str(markers.get("end") or DEFAULT_MARKERS[1])
    max_bytes = int(cfg.get("injection_strip_max_bytes") or 8192)
    targets = cfg.get("generated_file_targets") or {}
    md_targets = cfg.get("markdown_targets") or {}
    agents_rel = str(md_targets.get("agents_md") or "AGENTS.md")

    context = build_bootstrap_projection_context(repo_root, config=cfg)
    rows = context["per_agent_rows"]
    mrs = context["minimum_read_sets"]
    sequence = context["bootstrap_sequence"]
    situations = context["situation_routes"]
    runtime_plane = context["runtime_control_plane"]
    compact_commands = context["compact_command_surface"]
    instruction_discovery = context["instruction_discovery"]
    instruction_facts = context["instruction_discovery_facts"]
    system_facts = context["system_facts_at_a_glance"]
    agent_packet = context["agent_operating_packet"]
    type_a_convergence = context["type_a_convergence_contract"]
    actor_context_surfaces = context["actor_context_surfaces"]
    bindings = context["bindings"]
    generated_at = _utc_iso()
    instruction_seed_inner: str | None = None
    instruction_seed_projected_text: str | None = None
    if instruction_discovery:
        instruction_target = str(instruction_discovery.get("markdown_target") or "").strip()
        instruction_begin = str(instruction_discovery.get("begin_marker") or "").strip()
        instruction_end = str(instruction_discovery.get("end_marker") or "").strip()
        if instruction_target and instruction_begin and instruction_end:
            instruction_path = repo_root / instruction_target
            if instruction_path.exists():
                try:
                    current_seed_text = instruction_path.read_text(encoding="utf-8")
                    if instruction_begin in current_seed_text and instruction_end in current_seed_text:
                        (
                            instruction_facts,
                            instruction_seed_inner,
                            instruction_seed_projected_text,
                        ) = stabilize_instruction_discovery_target(
                            current_seed_text,
                            instruction_facts,
                            bindings,
                            bootstrap_sequence=sequence or None,
                            situation_routes=situations or None,
                            system_facts_at_a_glance=system_facts,
                            agent_operating_packet=agent_packet,
                        )
                except OSError:
                    pass
    md = render_live_markdown(
        bindings,
        per_agent_rows=rows,
        system_facts_at_a_glance=system_facts,
        minimum_read_sets=mrs or None,
        bootstrap_sequence=sequence or None,
        situation_routes=situations or None,
        actor_context_surfaces=actor_context_surfaces or None,
        runtime_control_plane=runtime_plane or None,
        compact_command_surface=compact_commands or None,
        type_a_convergence_contract=type_a_convergence or None,
    )
    live_payload = build_live_payload(
        bindings,
        generated_at=generated_at,
        source_event=source_event,
        per_agent_rows=rows,
        system_facts_at_a_glance=system_facts,
        agent_operating_packet=agent_packet,
        minimum_read_sets=mrs or None,
        bootstrap_sequence=sequence or None,
        situation_routes=situations or None,
        actor_context_surfaces=actor_context_surfaces or None,
        runtime_control_plane=runtime_plane or None,
        compact_command_surface=compact_commands or None,
        instruction_discovery_facts=instruction_facts or None,
        type_a_convergence_contract=type_a_convergence or None,
    )
    strip = build_injection_strip(
        bindings,
        max_bytes=max_bytes,
        agent_operating_packet=agent_packet,
        minimum_read_set_ids=sorted(mrs.keys()) if mrs else None,
        situation_route_ids=[row["situation_id"] for row in situations] if situations else None,
        actor_context_surface_ids=[row["actor_id"] for row in actor_context_surfaces] if actor_context_surfaces else None,
        type_a_convergence=str(type_a_convergence.get("route_command") or "") if type_a_convergence else None,
    )

    result: dict[str, Any] = {
        "dry_run": dry_run,
        "live_bindings": bindings,
        "markdown_chars": len(md),
        "wrote": [],
        "unchanged": [],
    }

    if not dry_run:
        live_rel = str(targets.get("live_json") or "codex/doctrine/agent_bootstrap_live.json")
        inj_rel = str(targets.get("injection_strip") or "codex/doctrine/agent_bootstrap_injection_strip.json")
        op_rel = str(targets.get("agent_operating_packet") or AGENT_OPERATING_PACKET_REL)
        live_path = repo_root / live_rel
        inj_path = repo_root / inj_rel
        op_path = repo_root / op_rel
        op_path.parent.mkdir(parents=True, exist_ok=True)
        op_text = json.dumps(agent_packet, indent=2, ensure_ascii=False) + "\n"
        if _write_text_if_changed(op_path, op_text):
            result["wrote"].append(op_rel)
        else:
            result["unchanged"].append(op_rel)
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_text = json.dumps(live_payload, indent=2, ensure_ascii=False) + "\n"
        if _write_text_if_changed(live_path, live_text):
            result["wrote"].append(live_rel)
        else:
            result["unchanged"].append(live_rel)
        inj_path.parent.mkdir(parents=True, exist_ok=True)
        inj_text = json.dumps(strip, indent=2, ensure_ascii=False) + "\n"
        if _write_text_if_changed(inj_path, inj_text):
            result["wrote"].append(inj_rel)
        else:
            result["unchanged"].append(inj_rel)

        if write_agents:
            ap = repo_root / agents_rel
            text = ap.read_text(encoding="utf-8")
            new_text = replace_marked_region(text, md, begin, end)
            if _write_text_if_changed(ap, new_text):
                result["wrote"].append(agents_rel)
            else:
                result["unchanged"].append(agents_rel)

            adapter_markers = markers.get("adapters") if isinstance(markers.get("adapters"), dict) else {}
            adapter_actor_map = cfg.get("adapter_actor_map") if isinstance(cfg.get("adapter_actor_map"), dict) else {}
            actor_lookup = {row.get("actor_id"): row for row in (actor_context_surfaces or []) if isinstance(row, Mapping)}
            skipped_adapters: list[str] = []
            for adapter_key, adapter_marker_pair in adapter_markers.items():
                if not isinstance(adapter_marker_pair, Mapping):
                    continue
                a_begin = adapter_marker_pair.get("begin")
                a_end = adapter_marker_pair.get("end")
                md_rel = md_targets.get(adapter_key)
                if not (a_begin and a_end and md_rel):
                    continue
                md_path = repo_root / str(md_rel)
                if not md_path.exists():
                    skipped_adapters.append(f"{adapter_key}:missing_file")
                    continue
                file_text = md_path.read_text(encoding="utf-8")
                if a_begin not in file_text or a_end not in file_text:
                    skipped_adapters.append(f"{adapter_key}:missing_markers")
                    continue
                actor_id = adapter_actor_map.get(adapter_key) or ""
                actor_row = actor_lookup.get(actor_id) if actor_id else None
                adapter_role = "claude_adapter" if adapter_key == "claude_md" else (
                    "codex_adapter" if adapter_key == "codex_md" else f"{adapter_key}_adapter"
                )
                adapter_md = render_adapter_markdown(
                    bindings,
                    adapter_role=adapter_role,
                    actor_id=actor_id,
                    actor_row=actor_row,
                    system_facts_at_a_glance=system_facts,
                    bootstrap_sequence=sequence or None,
                    situation_routes=situations or None,
                    type_a_convergence_contract=type_a_convergence or None,
                    canonical_option_surface_routes=load_canonical_option_surface_routes(repo_root),
                    hub_path=agents_rel,
                )
                new_adapter_text = replace_marked_region(file_text, adapter_md, str(a_begin), str(a_end))
                if _write_text_if_changed(md_path, new_adapter_text):
                    result["wrote"].append(str(md_rel))
                else:
                    result["unchanged"].append(str(md_rel))
            if skipped_adapters:
                result["skipped_adapters"] = skipped_adapters

            if instruction_discovery:
                instruction_target = str(instruction_discovery.get("markdown_target") or "").strip()
                instruction_begin = str(instruction_discovery.get("begin_marker") or "").strip()
                instruction_end = str(instruction_discovery.get("end_marker") or "").strip()
                if instruction_target and instruction_begin and instruction_end:
                    seed_path = repo_root / instruction_target
                    if seed_path.exists():
                        seed_text = seed_path.read_text(encoding="utf-8")
                        if instruction_begin in seed_text and instruction_end in seed_text:
                            if instruction_seed_projected_text is not None:
                                new_seed_text = instruction_seed_projected_text
                            else:
                                instruction_md = render_instruction_discovery_markdown(
                                    instruction_facts,
                                    bindings,
                                    bootstrap_sequence=sequence or None,
                                    situation_routes=situations or None,
                                    system_facts_at_a_glance=system_facts,
                                    agent_operating_packet=agent_packet,
                                )
                                new_seed_text = replace_marked_region(
                                    seed_text,
                                    instruction_md,
                                    instruction_begin,
                                    instruction_end,
                                )
                            if _write_text_if_changed(seed_path, new_seed_text):
                                result["wrote"].append(instruction_target)
                            else:
                                result["unchanged"].append(instruction_target)
                        else:
                            result.setdefault("skipped_instruction_discovery", []).append(
                                f"{instruction_target}:missing_markers"
                            )
                    else:
                        result.setdefault("skipped_instruction_discovery", []).append(
                            f"{instruction_target}:missing_file"
                        )

            pm_begin, pm_end = PAPER_MODULE_MARKERS
            pm_md = render_paper_module_index_markdown(repo_root)
            pm_targets: list[str] = [agents_rel]
            for hint in PAPER_MODULE_PROJECTION_TARGET_HINTS:
                if hint == "agents_md":
                    continue
                candidate = md_targets.get(hint)
                if candidate:
                    pm_targets.append(str(candidate))
            pm_targets.extend(["CLAUDE.md", "CODEX.md"])
            pm_written: list[str] = []
            pm_skipped: list[str] = []
            seen: set[str] = set()
            for rel in pm_targets:
                if not rel or rel in seen:
                    continue
                seen.add(rel)
                path = repo_root / rel
                if not path.exists():
                    pm_skipped.append(f"{rel}:missing_file")
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    pm_skipped.append(f"{rel}:unreadable")
                    continue
                if pm_begin not in text or pm_end not in text:
                    pm_skipped.append(f"{rel}:missing_markers")
                    continue
                try:
                    new_text = replace_marked_region(text, pm_md, pm_begin, pm_end)
                except ValueError:
                    pm_skipped.append(f"{rel}:marker_error")
                    continue
                if _write_text_if_changed(path, new_text):
                    pm_written.append(rel)
                    if rel not in result["wrote"]:
                        result["wrote"].append(rel)
                else:
                    result["unchanged"].append(rel)
            result["paper_module_projection"] = {
                "wrote": pm_written,
                "skipped": pm_skipped,
                "region_chars": len(pm_md),
            }

            if instruction_discovery:
                instruction_target = str(instruction_discovery.get("markdown_target") or "").strip()
                instruction_begin = str(instruction_discovery.get("begin_marker") or "").strip()
                instruction_end = str(instruction_discovery.get("end_marker") or "").strip()
                if instruction_target and instruction_begin and instruction_end:
                    seed_path = repo_root / instruction_target
                    if seed_path.exists():
                        seed_text = seed_path.read_text(encoding="utf-8")
                        if instruction_begin in seed_text and instruction_end in seed_text:
                            final_instruction_facts = resolve_instruction_discovery_facts(
                                repo_root,
                                instruction_discovery,
                            )
                            (
                                final_instruction_facts,
                                _final_instruction_inner,
                                final_seed_text,
                            ) = stabilize_instruction_discovery_target(
                                seed_text,
                                final_instruction_facts,
                                bindings,
                                bootstrap_sequence=sequence or None,
                                situation_routes=situations or None,
                                system_facts_at_a_glance=system_facts,
                                agent_operating_packet=agent_packet,
                            )
                            if _write_text_if_changed(seed_path, final_seed_text):
                                if instruction_target not in result["wrote"]:
                                    result["wrote"].append(instruction_target)
                            elif (
                                instruction_target not in result["wrote"]
                                and instruction_target not in result["unchanged"]
                            ):
                                result["unchanged"].append(instruction_target)
                            if live_payload.get("instruction_discovery") != final_instruction_facts:
                                live_payload["instruction_discovery"] = final_instruction_facts
                                live_text = json.dumps(live_payload, indent=2, ensure_ascii=False) + "\n"
                                if _write_text_if_changed(live_path, live_text):
                                    if live_rel not in result["wrote"]:
                                        result["wrote"].append(live_rel)
                                elif live_rel not in result["wrote"] and live_rel not in result["unchanged"]:
                                    result["unchanged"].append(live_rel)
                        elif f"{instruction_target}:missing_markers" not in result.get(
                            "skipped_instruction_discovery",
                            [],
                        ):
                            result.setdefault("skipped_instruction_discovery", []).append(
                                f"{instruction_target}:missing_markers"
                            )
                    elif f"{instruction_target}:missing_file" not in result.get(
                        "skipped_instruction_discovery",
                        [],
                    ):
                        result.setdefault("skipped_instruction_discovery", []).append(
                            f"{instruction_target}:missing_file"
                        )

    return result


def try_refresh_after_controller_write(repo_root: Path | None = None) -> None:
    """
    [ACTION]
    - Teleology: Opportunistically refresh bootstrap projections after controller writes when the environment flag opts into it.
    - Mechanism: Checks AI_WORKFLOW_REFRESH_AGENT_BOOTSTRAP, derives the repo root when needed, and swallows any exception from run_projection().
    - Guarantee: Never raises to the caller.
    - Fails: None.
    - When-needed: Open when controller-side writes may need to trigger a best-effort bootstrap refresh without risking the caller.
    - Escalates-to: system/lib/agent_bootstrap_projection.py::run_projection
    """
    if os.environ.get("AI_WORKFLOW_REFRESH_AGENT_BOOTSTRAP") != "1":
        return
    root = repo_root or Path(__file__).resolve().parents[2]
    try:
        run_projection(root, dry_run=False, write_agents=True, source_event="controller_artifacts_written")
    except Exception:
        pass
