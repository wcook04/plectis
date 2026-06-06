"""
[PURPOSE]
- Teleology: Project one deterministic routing hologram from the skill registry, synth contract, wave-delegation doctrine, and live routing telemetry so entry docs stop hand-maintaining drifting routing prose.
- Mechanism: Load named authority sources, blend structural and observed routing signals into a compact situation-to-skill table, fuse execution modes with persistence sinks, render a bounded markdown block, and optionally refresh the injected regions plus JSON artifact.

[INTERFACE]
- Exports: DEFAULT_OUTPUT_REL, BEGIN_MARKER, END_MARKER, build_routing_payload, render_routing_markdown, check_drift, routing_status, run_projection.
- Reads: codex/doctrine/skills/skill_registry.json, codex/standards/observe_apply/std_synth_seed.json, codex/doctrine/skills/kernel/wave_conductor.md, codex/doctrine/skills/kernel/delegation_protocol.md, codex/doctrine/routing_anti_patterns.json, state/agent_telemetry/latest_full/{routing_candidates.json|grep_targets.json}, and selected markdown targets.
- Writes: codex/doctrine/routing_hologram.json and the managed routing region in AGENTS.md when run_projection() is invoked.

[FLOW]
- Orders: Load authority sources -> derive compact routing payload -> render markdown block -> compare or write selected targets.
- When-needed: Open when routing guidance in entry docs should be regenerated, audited for drift, or surfaced as a compact machine-readable artifact.
- Escalates-to: tools/meta/factory/build_routing_projection.py; codex/doctrine/skills/skill_registry.json; codex/standards/observe_apply/std_synth_seed.json

[DEPENDENCIES]
- hashlib + json + pathlib + re: deterministic source hashing, payload assembly, and bounded markdown parsing.
- system.lib.agent_bootstrap_projection: reuse marked-region helpers so injected projections follow the existing repo pattern.
- tools.meta.agent_telemetry.common: share token normalization and candidate aggregation logic with telemetry extraction and coverage.

[CONSTRAINTS]
- The rendered block is intentionally capped: 3 entry steps, 10 situation rows, 6 execution modes, 5 anti-patterns.
- Sources named in the footer are the only authority inputs; any new section belongs in code and source config, not by hand in CLAUDE.md or AGENTS.md.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from system.lib.agent_bootstrap_projection import extract_marked_region, replace_marked_region
from tools.meta.agent_telemetry.common import (
    build_routing_candidates,
    candidate_aliases,
    classify_token,
    extract_symbol_tokens,
    normalize_token,
)

DEFAULT_OUTPUT_REL = "codex/doctrine/routing_hologram.json"
FAST_SOURCE_COUPLING_CACHE_NODE_ID = "routing_projection.fast_source_coupling"
AGENTS_MD_REL = "AGENTS.md"
SKILL_REGISTRY_REL = "codex/doctrine/skills/skill_registry.json"
STD_SYNTH_SEED_REL = "codex/standards/observe_apply/std_synth_seed.json"
WAVE_CONDUCTOR_REL = "codex/doctrine/skills/kernel/wave_conductor.md"
DELEGATION_PROTOCOL_REL = "codex/doctrine/skills/kernel/delegation_protocol.md"
ANTI_PATTERNS_REL = "codex/doctrine/routing_anti_patterns.json"
TELEMETRY_ROUTING_CANDIDATES_REL = "state/agent_telemetry/latest_full/routing_candidates.json"
TELEMETRY_GREP_TARGETS_REL = "state/agent_telemetry/latest_full/grep_targets.json"

BEGIN_MARKER = "<!-- BEGIN generated_routing -->"
END_MARKER = "<!-- END generated_routing -->"

ENTRY_PROTOCOL = [
    "`./repo-python kernel.py --info` -> `--preflight` -> `--pulse` for the live-state prelude.",
    "`./repo-python kernel.py --entry \"<task>\" --context-budget 12000`; add `--phase` when wave-scoped.",
    "Open a skill only after entry, a route row, or coverage selects it.",
]

MAX_SITUATION_ROWS = 10
MAX_MODE_ROWS = 6
MAX_ANTI_PATTERNS = 5
MAX_DELEGATION_CONTRACT_ROWS = 3
PINNED_ROUTING_PRIORITY = 95


def _safe_load_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _static_source_paths(repo_root: Path) -> list[Path]:
    return [
        repo_root / SKILL_REGISTRY_REL,
        repo_root / STD_SYNTH_SEED_REL,
        repo_root / WAVE_CONDUCTOR_REL,
        repo_root / DELEGATION_PROTOCOL_REL,
        repo_root / ANTI_PATTERNS_REL,
    ]


def _projection_source_paths(repo_root: Path, telemetry_source_rel: str | None) -> list[Path]:
    paths = _static_source_paths(repo_root)
    if telemetry_source_rel:
        paths.append(repo_root / telemetry_source_rel)
    return paths


def _source_rel_path(repo_root: Path, path_or_rel: Path | str) -> str:
    path = Path(path_or_rel)
    if path.is_absolute():
        return _rel(repo_root, path)
    return str(path)


def _porcelain_path(line: str) -> str:
    path = line[3:].strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[-1]
    return path.strip('"')


def source_worktree_state(repo_root: Path, source_paths: list[Path | str]) -> dict[str, Any]:
    rel_paths = sorted({_source_rel_path(repo_root, path) for path in source_paths if str(path).strip()})
    if not rel_paths:
        return {
            "status": "available",
            "source_dirty": False,
            "dirty_source_count": 0,
            "dirty_source_paths": [],
            "source_paths_checked": [],
            "dirty_rows": [],
        }

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", *rel_paths],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {
            "status": "unavailable",
            "reason": "git_status_failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "source_dirty": None,
            "dirty_source_count": None,
            "dirty_source_paths": [],
            "source_paths_checked": rel_paths,
            "dirty_rows": [],
        }

    if result.returncode != 0:
        return {
            "status": "unavailable",
            "reason": "git_status_nonzero",
            "returncode": result.returncode,
            "stderr": result.stderr.strip()[:500],
            "source_dirty": None,
            "dirty_source_count": None,
            "dirty_source_paths": [],
            "source_paths_checked": rel_paths,
            "dirty_rows": [],
        }

    dirty_rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        rel = _porcelain_path(line)
        if not rel:
            continue
        dirty_rows.append(
            {
                "path": rel,
                "index_status": "?" if line.startswith("??") else line[0],
                "worktree_status": "?" if line.startswith("??") else line[1],
                "porcelain": line[:2],
            }
        )

    dirty_paths = sorted({row["path"] for row in dirty_rows})
    return {
        "status": "available",
        "source_dirty": bool(dirty_paths),
        "dirty_source_count": len(dirty_paths),
        "dirty_source_paths": dirty_paths,
        "source_paths_checked": rel_paths,
        "dirty_rows": dirty_rows,
    }


def routing_source_worktree_state(repo_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return source_worktree_state(repo_root, [str(path) for path in payload.get("source_paths") or []])


def routing_source_coupling_receipt(
    *,
    artifact_matches_current_worktree: bool,
    source_state: dict[str, Any],
) -> dict[str, Any]:
    state_available = source_state.get("status") == "available"
    source_dirty = bool(source_state.get("source_dirty")) if state_available else None
    if not state_available:
        return {
            "status": "source_state_unavailable",
            "artifact_matches_current_worktree": artifact_matches_current_worktree,
            "safe_to_commit_generated_outputs_without_sources": False,
            "reason": "Git source-state receipt is unavailable, so generated projection commit coupling cannot be proven.",
        }
    if source_dirty:
        status = (
            "artifact_matches_dirty_source_inputs"
            if artifact_matches_current_worktree
            else "dirty_source_inputs_and_artifact_drift"
        )
        return {
            "status": status,
            "artifact_matches_current_worktree": artifact_matches_current_worktree,
            "safe_to_commit_generated_outputs_without_sources": False,
            "dirty_source_paths": source_state.get("dirty_source_paths") or [],
            "reason": (
                "Routing projection inputs are dirty. The artifact hash/render is computed from worktree "
                "source contents, so committing generated targets without the dirty source paths can make "
                "the committed projection non-reproducible."
            ),
        }
    if not artifact_matches_current_worktree:
        return {
            "status": "artifact_drift_from_clean_sources",
            "artifact_matches_current_worktree": False,
            "safe_to_commit_generated_outputs_without_sources": False,
            "dirty_source_paths": [],
            "reason": "Routing source inputs are clean, but generated targets do not match the current renderer.",
        }
    return {
        "status": "clean_source_inputs_and_artifacts",
        "artifact_matches_current_worktree": True,
        "safe_to_commit_generated_outputs_without_sources": True,
        "dirty_source_paths": [],
        "reason": "Routing generated targets match the renderer and the projection source inputs are clean.",
    }


def _input_sha256(repo_root: Path, source_paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in source_paths:
        hasher.update(str(_rel(repo_root, path)).encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    start_idx: int | None = None
    start_level: int | None = None
    for idx, line in enumerate(lines):
        match = re.match(r"^(#+)\s+(.*)$", line.strip())
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if start_idx is None:
            if title == heading:
                start_idx = idx + 1
                start_level = level
            continue
        if level <= int(start_level or 0):
            return lines[start_idx:idx]
    return lines[start_idx:] if start_idx is not None else []


def _parse_mode_descriptions(wave_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in _section_lines(wave_text, "Decision rule"):
        match = re.match(r"^- `([^`]+)`: (.+)$", line.strip())
        if match:
            out[match.group(1).strip()] = match.group(2).strip()
    return out


def _truncate(text: str, limit: int = 120) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _strip_skill_prefix(path: str) -> str:
    prefix = "codex/doctrine/skills/"
    return path[len(prefix):] if path.startswith(prefix) else path


def _combo_counts(registry: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for combo in registry.get("alchemy_combinations") or []:
        if not isinstance(combo, dict):
            continue
        for skill_id in combo.get("skills") or []:
            sid = str(skill_id or "").strip()
            if sid:
                counts[sid] = counts.get(sid, 0) + 1
    return counts


def _active_skills(registry: dict[str, Any]) -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    order = 0
    for family in registry.get("families") or []:
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("family_id") or "").strip()
        for skill in family.get("skills") or []:
            if not isinstance(skill, dict) or str(skill.get("status") or "").strip() != "active":
                continue
            row = dict(skill)
            row["_family_id"] = family_id
            row["_order"] = order
            skills.append(row)
            order += 1
    return skills


def _routing_candidate_skills(registry: dict[str, Any]) -> list[dict[str, Any]]:
    skills = _active_skills(registry)
    prioritized = [skill for skill in skills if int(skill.get("routing_priority") or 0) > 0]
    return prioritized or skills


def _load_telemetry_candidates(repo_root: Path) -> tuple[list[dict[str, Any]], str | None, str]:
    routing_candidates_path = repo_root / TELEMETRY_ROUTING_CANDIDATES_REL
    if routing_candidates_path.is_file():
        payload = _safe_load_json(routing_candidates_path)
        if isinstance(payload, list):
            return payload, TELEMETRY_ROUTING_CANDIDATES_REL, "routing_candidates"

    grep_targets_path = repo_root / TELEMETRY_GREP_TARGETS_REL
    if grep_targets_path.is_file():
        payload = _safe_load_json(grep_targets_path)
        if isinstance(payload, dict):
            return build_routing_candidates(payload, min_count=1), TELEMETRY_GREP_TARGETS_REL, "grep_targets"

    return [], None, "missing"


def _skill_situation_key(skill: dict[str, Any]) -> str:
    surface = skill.get("agent_surface") or {}
    holographic = skill.get("holographic") or {}
    raw = (
        str(holographic.get("situation_signature") or "").strip()
        or str(surface.get("use_when") or "").strip()
        or str(skill.get("id") or "").strip()
    )
    return re.sub(r"\s+", " ", raw).strip().lower()


def _skill_match_tokens(skill: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()

    def _add_alias(value: str) -> None:
        norm = normalize_token(value)
        if not norm or classify_token(norm) == "generic":
            return
        for alias in candidate_aliases(norm):
            if classify_token(alias) != "generic":
                tokens.add(alias.lower())

    def _add_path_alias(path_value: str) -> None:
        norm = normalize_token(path_value)
        if not norm:
            return
        path = Path(norm)
        for candidate in (norm, path.name, path.stem):
            normalized = normalize_token(candidate)
            if normalized and classify_token(normalized) != "generic":
                tokens.add(normalized.lower())

    def _add_text(text: str) -> None:
        if not text:
            return
        for token in extract_symbol_tokens(text):
            classification = classify_token(token)
            if classification in {"concept_id", "module_path", "camel_symbol"}:
                tokens.add(token)
                continue
            if classification == "snake_symbol" and "_" in token:
                tokens.add(token)

    surface = skill.get("agent_surface") or {}
    holographic = skill.get("holographic") or {}

    _add_alias(str(skill.get("id") or ""))
    _add_path_alias(str(skill.get("file") or ""))
    _add_text(str(skill.get("title") or ""))
    _add_text(str(holographic.get("situation_signature") or ""))
    _add_text(str(surface.get("use_when") or ""))
    for trigger in skill.get("triggers") or []:
        _add_text(str(trigger or ""))
    return tokens


def _skill_telemetry_stats(
    skills: list[dict[str, Any]],
    routing_candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    skill_tokens = {
        str(skill.get("id") or ""): _skill_match_tokens(skill)
        for skill in skills
    }
    stats: dict[str, dict[str, Any]] = {
        str(skill.get("id") or ""): {
            "telemetry_shared_hits": 0.0,
            "telemetry_match_count": 0,
            "telemetry_top_tokens": {},
        }
        for skill in skills
    }

    for row in routing_candidates:
        token = normalize_token(str(row.get("token") or ""))
        count = int(row.get("count") or 0)
        classification = str(row.get("classification") or classify_token(token))
        if not token or count <= 0 or classification == "generic":
            continue
        aliases = {
            alias.lower()
            for alias in candidate_aliases(token)
            if classify_token(alias) != "generic"
        }
        if not aliases:
            continue

        matched_skill_ids = [
            skill_id
            for skill_id, tokens in skill_tokens.items()
            if skill_id and tokens.intersection(aliases)
        ]
        if not matched_skill_ids:
            continue

        shared_hits = count / len(matched_skill_ids)
        for skill_id in matched_skill_ids:
            bucket = stats[skill_id]
            bucket["telemetry_shared_hits"] = float(bucket["telemetry_shared_hits"]) + shared_hits
            bucket["telemetry_match_count"] = int(bucket["telemetry_match_count"]) + 1
            top_tokens = bucket["telemetry_top_tokens"]
            top_tokens[token] = float(top_tokens.get(token, 0.0)) + shared_hits

    for bucket in stats.values():
        top_tokens = bucket.pop("telemetry_top_tokens")
        bucket["telemetry_shared_hits"] = round(float(bucket["telemetry_shared_hits"]), 3)
        bucket["telemetry_top_tokens"] = [
            token
            for token, _ in sorted(
                top_tokens.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        ]
    return stats


def _telemetry_score(shared_hits: float, match_count: int) -> float:
    return round(min(shared_hits, 40.0) / 10.0 + min(match_count, 6) * 0.75, 4)


def _routing_score(
    skill: dict[str, Any],
    combo_counts: dict[str, int],
    telemetry_stats: dict[str, dict[str, Any]],
) -> tuple[float, float, int, int, int, int, int]:
    skill_id = str(skill.get("id") or "").strip()
    triggers = len(skill.get("triggers") or [])
    governing = len(skill.get("governing_principles") or [])
    composes = len(skill.get("composes_with") or [])
    combos = combo_counts.get(skill_id, 0)
    explicit = int(skill.get("routing_priority") or 0)
    family_bonus = 2 if str(skill.get("_family_id") or "") == "kernel" else 0
    use_when = str((skill.get("agent_surface") or {}).get("use_when") or "").lower()
    mode_bonus = 2 if any(token in use_when for token in ("subagent_cohort", "bridge_graph", "continuous_conductor")) else 0
    telemetry = telemetry_stats.get(skill_id) or {}
    shared_hits = float(telemetry.get("telemetry_shared_hits") or 0.0)
    match_count = int(telemetry.get("telemetry_match_count") or 0)
    derived_score = combos * 3 + triggers * 2 + governing + composes + family_bonus + mode_bonus
    total_score = round(derived_score + _telemetry_score(shared_hits, match_count), 4)
    return (
        total_score,
        shared_hits,
        match_count,
        explicit,
        combos,
        triggers,
        -int(skill.get("_order") or 0),
    )


def _combo_counts_for_skills(registry: dict[str, Any], skills: list[dict[str, Any]]) -> dict[str, int]:
    skill_ids = {str(skill.get("id") or "").strip() for skill in skills}
    return {
        skill_id: count
        for skill_id, count in _combo_counts(registry).items()
        if skill_id in skill_ids
    }


def _build_situation_rows(
    registry: dict[str, Any],
    skills: list[dict[str, Any]],
    telemetry_stats: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    combo_counts = _combo_counts_for_skills(registry, skills)
    ranked = sorted(
        skills,
        key=lambda skill: _routing_score(skill, combo_counts, telemetry_stats),
        reverse=True,
    )
    rows: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    seen_signatures: set[str] = set()

    def _append(skill: dict[str, Any]) -> None:
        surface = skill.get("agent_surface") or {}
        skill_id = str(skill.get("id") or "").strip()
        combos = combo_counts.get(skill_id, 0)
        triggers = len(skill.get("triggers") or [])
        governing = len(skill.get("governing_principles") or [])
        composes = len(skill.get("composes_with") or [])
        family_bonus = 2 if str(skill.get("_family_id") or "") == "kernel" else 0
        use_when = str(surface.get("use_when") or "").lower()
        mode_bonus = 2 if any(token in use_when for token in ("subagent_cohort", "bridge_graph", "continuous_conductor")) else 0
        telemetry = telemetry_stats.get(skill_id) or {}
        shared_hits = float(telemetry.get("telemetry_shared_hits") or 0.0)
        match_count = int(telemetry.get("telemetry_match_count") or 0)
        derived_score = combos * 3 + triggers * 2 + governing + composes + family_bonus + mode_bonus
        total_score = round(derived_score + _telemetry_score(shared_hits, match_count), 4)
        situation_key = _skill_situation_key(skill)
        rows.append(
            {
                "skill_id": skill_id,
                "skill_path": _strip_skill_prefix(str(skill.get("file") or "").strip()),
                "family_id": str(skill.get("_family_id") or "").strip(),
                "situation_key": situation_key,
                "situation": _truncate(
                    str(surface.get("use_when") or "")
                    or str((skill.get("holographic") or {}).get("situation_signature") or "")
                    or str(next(iter(skill.get("triggers") or []), "") or ""),
                    112,
                ),
                "score": {
                    "total": total_score,
                    "derived": derived_score,
                    "explicit_priority": int(skill.get("routing_priority") or 0),
                    "alchemy_combo_count": combos,
                    "trigger_count": triggers,
                    "governing_principle_count": governing,
                    "telemetry_shared_hits": shared_hits,
                    "telemetry_match_count": match_count,
                    "telemetry_top_tokens": telemetry.get("telemetry_top_tokens") or [],
                },
            }
        )
        selected_ids.add(skill_id)

    pinned = [
        skill
        for skill in ranked
        if int(skill.get("routing_priority") or 0) >= PINNED_ROUTING_PRIORITY
    ]
    for skill in pinned:
        if len(rows) >= MAX_SITUATION_ROWS:
            break
        situation_key = _skill_situation_key(skill)
        if situation_key in seen_signatures:
            continue
        seen_signatures.add(situation_key)
        _append(skill)

    for skill in ranked:
        if len(rows) >= MAX_SITUATION_ROWS:
            break
        skill_id = str(skill.get("id") or "").strip()
        if skill_id in selected_ids:
            continue
        situation_key = _skill_situation_key(skill)
        if situation_key in seen_signatures:
            continue
        seen_signatures.add(situation_key)
        _append(skill)

    if len(rows) < MAX_SITUATION_ROWS:
        for skill in ranked:
            if len(rows) >= MAX_SITUATION_ROWS:
                break
            skill_id = str(skill.get("id") or "").strip()
            if skill_id in selected_ids:
                continue
            _append(skill)

    return rows


def _mode_list(std_synth_seed: dict[str, Any]) -> list[str]:
    current_wave_shape = std_synth_seed.get("current_wave_shape") or {}
    raw = str(current_wave_shape.get("mode") or "")
    return [part.strip() for part in raw.split("|") if part.strip()][:MAX_MODE_ROWS]


def _build_mode_rows(
    std_synth_seed: dict[str, Any],
    wave_text: str,
    delegation_text: str,
) -> list[dict[str, str]]:
    mode_descriptions = _parse_mode_descriptions(wave_text)
    assimilation = std_synth_seed.get("assimilation_targets_shape") or {}

    archive_root = "archive_root"
    ledger_path = "ledger_path"
    delta_path = "delta_path"
    continuation_summary_path = "continuation_summary_path"
    observe_plan_path = "observe_plan_path" if "observe_plan_path" in assimilation else "observe_plan_path"
    resume_contract_path = "resume_contract_path" if "resume_contract_path" in assimilation else "resume_contract_path"

    zero_write_hint = (
        "synth_seed.json:synthesis_memory + "
        f"`{delta_path}` + `{archive_root}/cohort_wave_<wave_id>_bundles/` + `{ledger_path}`"
    )
    bridge_hint = f"`{observe_plan_path}` + `{resume_contract_path}` + bridge receipts"
    conductor_hint = f"`{observe_plan_path}` + `{resume_contract_path}` + `{continuation_summary_path}` + bridge receipts"
    mission_hint = (
        "`observe_plan_path` + `resume_contract.json` (for detached observe wake) + "
        "`_mission_controller_state.json` + mission-local `pipeline_resume.json` / `pipeline_attention.json`"
    )

    rows: list[dict[str, str]] = []
    for mode in _mode_list(std_synth_seed):
        if mode == "direct_local":
            rows.append(
                {
                    "mode": mode,
                    "worker_surface": "controller",
                    "use_when": mode_descriptions.get(mode, "Bounded local edits with no meaningful delegation seam."),
                    "persistence": "`synth_seed.json` + `ledger_path` via `--phase-assimilate`",
                }
            )
        elif mode == "hybrid":
            rows.append(
                {
                    "mode": mode,
                    "worker_surface": "controller + delegated seam",
                    "use_when": mode_descriptions.get(mode, "Local wiring plus one or more bounded delegated seams."),
                    "persistence": "`synth_seed.json` + `ledger_path`; delegated lane inherits the bridge or cohort contract",
                }
            )
        elif mode == "bridge_graph":
            rows.append(
                {
                    "mode": mode,
                    "worker_surface": "bridge",
                    "use_when": mode_descriptions.get(mode, "Injected-context bridge fan-out is the primary execution engine."),
                    "persistence": bridge_hint,
                }
            )
        elif mode == "continuous_conductor":
            rows.append(
                {
                    "mode": mode,
                    "worker_surface": "bridge",
                    "use_when": mode_descriptions.get(mode, "Long-running bounded campaign with explicit wake barriers."),
                    "persistence": conductor_hint,
                }
            )
        elif mode == "subagent_cohort":
            rows.append(
                {
                    "mode": mode,
                    "worker_surface": "subagent",
                    "use_when": mode_descriptions.get(mode, "Multiple scoped tool-using workers with explicit write boundaries and a single assimilation sink."),
                    "persistence": zero_write_hint,
                }
            )
        elif mode == "mission_launch":
            rows.append(
                {
                    "mode": mode,
                    "worker_surface": "observe runtime + controller",
                    "use_when": mode_descriptions.get(mode, "Mission expansion launches observe work and hands closure back to the controller through a mission-scoped state file."),
                    "persistence": mission_hint,
                }
            )

    bridge_phrase = "observe-plan artifacts, receipts, and resume contracts" in delegation_text
    zero_write_phrase = "Workers return bundles in the tool-return message" in delegation_text
    for row in rows:
        row["source_provenance"] = "wave_conductor + delegation_protocol" if (bridge_phrase or zero_write_phrase) else "wave_conductor"
    return rows


def _has_all(text: str, phrases: tuple[str, ...]) -> bool:
    return all(phrase.lower() in text for phrase in phrases)


def _build_delegation_contract_rows(delegation_text: str) -> list[dict[str, str]]:
    normalized = " ".join(delegation_text.split()).lower()
    rows: list[dict[str, str]] = []

    if _has_all(normalized, ("stateless", "self-contained prompt", "returns one bundle")):
        rows.append(
            {
                "surface": "subagent_cohort",
                "contract": (
                    "Workers are stateless, self-contained single-return calls; each prompt carries target "
                    "paths, scope, expected artifacts, handoff requirements, and forbidden writes."
                ),
            }
        )

    if _has_all(normalized, ("workers return bundles in the tool-return message", "synth_seed.json:synthesis_memory")):
        rows.append(
            {
                "surface": "zero-write cohort",
                "contract": (
                    "Evidence workers return typed bundles in-tool; the controller alone writes synthesis "
                    "memory, optional delta/archive artifacts, and the ledger."
                ),
            }
        )

    if _has_all(normalized, ("end the turn after detached dispatch", "resume_contract")):
        rows.append(
            {
                "surface": "bridge_graph / continuous_conductor",
                "contract": (
                    "Detached bridge work is resumed from the observe plan, resume contract, and stored "
                    "receipts before controller assimilation."
                ),
            }
        )

    return rows[:MAX_DELEGATION_CONTRACT_ROWS]


def _load_anti_patterns(repo_root: Path) -> list[dict[str, str]]:
    payload = _safe_load_json(repo_root / ANTI_PATTERNS_REL)
    rows = payload.get("anti_patterns") if isinstance(payload, dict) else []
    out: list[dict[str, str]] = []
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            out.append(
                {
                    "id": str(item.get("id") or "").strip() or f"anti_pattern_{len(out)+1}",
                    "text": _truncate(text, 140),
                }
            )
    return out[:MAX_ANTI_PATTERNS]


def _validate_payload(
    payload: dict[str, Any],
    *,
    expected_mode_names: list[str],
    active_skill_count: int,
) -> None:
    entry_protocol = payload.get("entry_protocol") or []
    if len(entry_protocol) != len(ENTRY_PROTOCOL):
        raise ValueError(f"Routing projection expected {len(ENTRY_PROTOCOL)} entry steps, got {len(entry_protocol)}.")

    situation_rows = payload.get("situation_rows") or []
    expected_situation_count = min(MAX_SITUATION_ROWS, active_skill_count)
    if len(situation_rows) != expected_situation_count:
        raise ValueError(
            f"Routing projection expected {expected_situation_count} situation rows, got {len(situation_rows)}."
        )

    situation_keys = [str(row.get("situation_key") or "").strip().lower() for row in situation_rows]
    if "" in situation_keys or len(set(situation_keys)) != len(situation_keys):
        raise ValueError("Routing projection produced duplicate or empty situation keys in the top situation rows.")

    mode_rows = payload.get("mode_rows") or []
    mode_names = [str(row.get("mode") or "") for row in mode_rows]
    if len(mode_rows) != len(expected_mode_names):
        raise ValueError(
            f"Routing projection expected {len(expected_mode_names)} mode rows, got {len(mode_rows)}."
        )
    if mode_names != expected_mode_names:
        raise ValueError(
            f"Routing projection mode rows drifted from std_synth_seed order: expected {expected_mode_names}, got {mode_names}."
        )

    anti_patterns = payload.get("anti_patterns") or []
    if len(anti_patterns) > MAX_ANTI_PATTERNS:
        raise ValueError(
            f"Routing projection expected at most {MAX_ANTI_PATTERNS} anti-patterns, got {len(anti_patterns)}."
        )

    delegation_contract_rows = payload.get("delegation_contract_rows") or []
    if len(delegation_contract_rows) > MAX_DELEGATION_CONTRACT_ROWS:
        raise ValueError(
            "Routing projection expected at most "
            f"{MAX_DELEGATION_CONTRACT_ROWS} delegated contract rows, got {len(delegation_contract_rows)}."
        )
    for row in delegation_contract_rows:
        if not str(row.get("surface") or "").strip() or not str(row.get("contract") or "").strip():
            raise ValueError("Routing projection produced an empty delegated worker contract row.")


def build_routing_payload(repo_root: Path) -> dict[str, Any]:
    registry = _safe_load_json(repo_root / SKILL_REGISTRY_REL)
    std_synth_seed = _safe_load_json(repo_root / STD_SYNTH_SEED_REL)
    wave_text = (repo_root / WAVE_CONDUCTOR_REL).read_text(encoding="utf-8")
    delegation_text = (repo_root / DELEGATION_PROTOCOL_REL).read_text(encoding="utf-8")
    routing_candidates, telemetry_source_rel, telemetry_source_kind = _load_telemetry_candidates(repo_root)

    if not isinstance(registry, dict) or not isinstance(std_synth_seed, dict):
        raise ValueError("Routing projection authorities could not be loaded.")

    routing_skills = _routing_candidate_skills(registry)
    telemetry_stats = _skill_telemetry_stats(routing_skills, routing_candidates)
    source_paths = _projection_source_paths(repo_root, telemetry_source_rel)
    mode_names = _mode_list(std_synth_seed)

    payload = {
        "kind": "routing_hologram",
        "generated_from": "deterministic_projection",
        "input_sha256": _input_sha256(repo_root, source_paths),
        "source_paths": [_rel(repo_root, path) for path in source_paths],
        "artifact_path": DEFAULT_OUTPUT_REL,
        "entry_protocol": ENTRY_PROTOCOL,
        "section_caps": {
            "entry_protocol": len(ENTRY_PROTOCOL),
            "situation_rows": MAX_SITUATION_ROWS,
            "mode_rows": MAX_MODE_ROWS,
            "anti_patterns": MAX_ANTI_PATTERNS,
            "delegation_contract_rows": MAX_DELEGATION_CONTRACT_ROWS,
        },
        "skill_map_path": "codex/doctrine/skills/skill_map.md",
        "telemetry": {
            "source_kind": telemetry_source_kind,
            "source_path": telemetry_source_rel,
            "candidate_count": len(routing_candidates),
            "matched_skill_count": sum(
                1 for stats in telemetry_stats.values() if int(stats.get("telemetry_match_count") or 0) > 0
            ),
        },
        "situation_rows": _build_situation_rows(registry, routing_skills, telemetry_stats),
        "mode_rows": _build_mode_rows(std_synth_seed, wave_text, delegation_text),
        "delegation_contract_rows": _build_delegation_contract_rows(delegation_text),
        "anti_patterns": _load_anti_patterns(repo_root),
    }
    _validate_payload(payload, expected_mode_names=mode_names, active_skill_count=len(routing_skills))
    return payload


def render_routing_markdown(payload: dict[str, Any]) -> str:
    telemetry = payload.get("telemetry") or {}
    telemetry_note = ""
    if telemetry.get("source_path"):
        telemetry_note = f" + `{telemetry.get('source_path')}`"
    lines = [
        "_Auto-generated from `skill_registry.json`, `std_synth_seed.json`, `wave_conductor.md`, `delegation_protocol.md`, `routing_anti_patterns.json`"
        f"{telemetry_note}. Do not edit by hand._",
        "_Full browse: [codex/doctrine/skills/skill_map.md](codex/doctrine/skills/skill_map.md) | Refresh: `./repo-python tools/meta/factory/build_routing_projection.py`_",
        "",
        "**Entry Protocol**",
    ]
    for idx, step in enumerate(payload.get("entry_protocol") or [], start=1):
        lines.append(f"{idx}. {step}")

    lines.extend(
        [
            "",
            "**Situation -> Skill**",
            f"_Top {len(payload.get('situation_rows') or [])} rows by routing score. Full browse stays in `skill_map.md`._",
            "| Situation | Open first |",
            "|---|---|",
        ]
    )
    for row in payload.get("situation_rows") or []:
        lines.append(f"| {row.get('situation')} | `{row.get('skill_path')}` |")

    lines.extend(
        [
            "",
            "**Modes + Persistence**",
            "| Mode | Worker surface | Use when | Persistence |",
            "|---|---|---|---|",
        ]
    )
    for row in payload.get("mode_rows") or []:
        lines.append(
            "| "
            f"`{row.get('mode')}` | {row.get('worker_surface')} | {row.get('use_when')} | {row.get('persistence')} |"
        )

    contract_rows = payload.get("delegation_contract_rows") or []
    if contract_rows:
        lines.extend(
            [
                "",
                "**Delegated Worker Contract**",
                "| Surface | Contract |",
                "|---|---|",
            ]
        )
        for row in contract_rows:
            lines.append(f"| `{row.get('surface')}` | {row.get('contract')} |")

    lines.extend(["", "**Anti-patterns**"])
    for row in payload.get("anti_patterns") or []:
        lines.append(f"- {row.get('text')}")

    digest = str(payload.get("input_sha256") or "")[:16]
    lines.extend(
        [
            "",
            f"_Artifact: `{payload.get('artifact_path')}` | Sources sha256[:16]: `{digest}`_",
        ]
    )
    return "\n".join(lines)


def _selected_targets(target: str) -> list[str]:
    if target == "agents":
        return [AGENTS_MD_REL]
    if target == "json":
        return [DEFAULT_OUTPUT_REL]
    return [AGENTS_MD_REL, DEFAULT_OUTPUT_REL]


def check_drift(
    repo_root: Path,
    *,
    targets: list[str] | None = None,
    output_rel: str = DEFAULT_OUTPUT_REL,
) -> tuple[bool, list[dict[str, Any]], dict[str, Any], str]:
    payload = build_routing_payload(repo_root)
    markdown = render_routing_markdown(payload)
    clean = True
    results: list[dict[str, Any]] = []

    for rel in targets or _selected_targets("all"):
        path = repo_root / (output_rel if rel == DEFAULT_OUTPUT_REL else rel)
        if rel.endswith(".json"):
            if not path.is_file():
                clean = False
                results.append({"target": rel, "clean": False, "reason": "missing"})
                continue
            expected = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
            is_clean = path.read_text(encoding="utf-8") == expected
            clean = clean and is_clean
            results.append({"target": rel, "clean": is_clean, "reason": "match" if is_clean else "artifact drift"})
            continue
        if not path.is_file():
            clean = False
            results.append({"target": rel, "clean": False, "reason": "missing"})
            continue
        current_text = path.read_text(encoding="utf-8")
        current_block = extract_marked_region(current_text, BEGIN_MARKER, END_MARKER)
        if current_block is None:
            clean = False
            results.append({"target": rel, "clean": False, "reason": "markers not found"})
            continue
        is_clean = current_block.strip() == markdown.strip()
        clean = clean and is_clean
        results.append({"target": rel, "clean": is_clean, "reason": "match" if is_clean else "block drift"})

    return clean, results, payload, markdown


def routing_status(repo_root: Path, *, output_rel: str = DEFAULT_OUTPUT_REL) -> dict[str, Any]:
    out_path = repo_root / output_rel
    clean, checks, payload, _ = check_drift(
        repo_root,
        targets=[AGENTS_MD_REL, DEFAULT_OUTPUT_REL],
        output_rel=output_rel,
    )
    source_state = routing_source_worktree_state(repo_root, payload)
    source_coupling = routing_source_coupling_receipt(
        artifact_matches_current_worktree=clean,
        source_state=source_state,
    )
    return {
        "artifact_path": _rel(repo_root, out_path),
        "exists": out_path.is_file(),
        "stale": not clean,
        "drift_targets": [item["target"] for item in checks if not item.get("clean")],
        "input_sha256": payload.get("input_sha256"),
        "check_command": "python3 kernel.py --routing-check",
        "refresh_command": "./repo-python tools/meta/factory/build_routing_projection.py",
        "source_paths": payload.get("source_paths") or [],
        "source_worktree_state": source_state,
        "source_coupling": source_coupling,
    }


def _routing_fast_source_coupling_status_uncached(
    repo_root: Path,
    *,
    output_rel: str = DEFAULT_OUTPUT_REL,
) -> dict[str, Any]:
    """Return routing source-coupling without rebuilding the routing projection.

    Routine entry packets need to know whether source inputs are dirty, but
    building the whole routing payload is a multi-second diagnostic. The saved
    projection already records its source path set and input hash, so this fast
    receipt can compare those source files directly and leave renderer drift to
    the explicit checker.
    """
    out_path = repo_root / output_rel
    try:
        payload = _safe_load_json(out_path)
    except Exception:
        payload = {}
    artifact_payload = payload if isinstance(payload, dict) else {}
    raw_source_paths = [
        str(path)
        for path in list(artifact_payload.get("source_paths") or [])
        if str(path or "").strip()
    ]
    source_paths = [repo_root / rel for rel in raw_source_paths]
    source_state = source_worktree_state(repo_root, raw_source_paths)
    expected_hash = str(artifact_payload.get("input_sha256") or "").strip()
    current_hash = ""
    hash_status = "unavailable"
    if source_paths and all(path.is_file() for path in source_paths):
        try:
            current_hash = _input_sha256(repo_root, source_paths)
            hash_status = "matched" if expected_hash and current_hash == expected_hash else "drift"
        except OSError:
            hash_status = "unavailable"
    artifact_matches_current_worktree = bool(expected_hash and current_hash == expected_hash)
    source_coupling = routing_source_coupling_receipt(
        artifact_matches_current_worktree=artifact_matches_current_worktree,
        source_state=source_state,
    )
    source_coupling["receipt_mode"] = "fast_saved_projection_source_hash"
    return {
        "artifact_path": _rel(repo_root, out_path),
        "exists": out_path.is_file(),
        "stale": None if hash_status == "unavailable" else not artifact_matches_current_worktree,
        "drift_targets": [],
        "input_sha256": expected_hash or None,
        "current_input_sha256": current_hash or None,
        "input_hash_status": hash_status,
        "check_command": "python3 kernel.py --routing-check",
        "refresh_command": "./repo-python tools/meta/factory/build_routing_projection.py",
        "source_paths": raw_source_paths,
        "source_worktree_state": source_state,
        "source_coupling": source_coupling,
        "full_renderer_check_deferred": True,
    }


def routing_fast_source_coupling_status(repo_root: Path, *, output_rel: str = DEFAULT_OUTPUT_REL) -> dict[str, Any]:
    out_path = repo_root / output_rel
    try:
        payload = _safe_load_json(out_path)
    except Exception:
        payload = {}
    artifact_payload = payload if isinstance(payload, dict) else {}
    source_paths = [
        str(path)
        for path in list(artifact_payload.get("source_paths") or [])
        if str(path or "").strip()
    ]

    from system.lib.command_node_cache import cached_command_node

    def build() -> dict[str, Any]:
        return _routing_fast_source_coupling_status_uncached(repo_root, output_rel=output_rel)

    cached_payload, cache_status = cached_command_node(
        repo_root,
        node_id=FAST_SOURCE_COUPLING_CACHE_NODE_ID,
        key={
            "kind": "routing_fast_source_coupling_status",
            "schema": "routing_source_coupling_receipt_v1",
            "output_rel": output_rel,
        },
        input_paths=[output_rel, *source_paths],
        ttl_s=300.0,
        builder=build,
        freshness_policy="short_ttl_plus_routing_source_manifest",
        dynamic_inputs_manifested=True,
    )
    result = dict(cached_payload) if isinstance(cached_payload, dict) else {}
    result["cache"] = cache_status
    return result


def run_projection(
    repo_root: Path,
    *,
    targets: list[str] | None = None,
    output_rel: str = DEFAULT_OUTPUT_REL,
) -> dict[str, Any]:
    payload = build_routing_payload(repo_root)
    markdown = render_routing_markdown(payload)
    wrote: list[str] = []

    for rel in targets or _selected_targets("all"):
        path = repo_root / (output_rel if rel == DEFAULT_OUTPUT_REL else rel)
        if rel.endswith(".json"):
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            wrote.append(_rel(repo_root, path))
            continue
        existing = path.read_text(encoding="utf-8")
        if BEGIN_MARKER in existing and END_MARKER in existing:
            updated = replace_marked_region(existing, markdown, BEGIN_MARKER, END_MARKER)
        else:
            # Cross-builder ownership contract: when a peer builder (e.g. agent_bootstrap_projection)
            # regenerates the host file without preserving the routing marker pair, append a fresh
            # block at the end. This keeps the routing block self-healing without requiring the
            # peer builder to know about every other builder's markers.
            block = f"\n\n{BEGIN_MARKER}\n{markdown}{END_MARKER}\n"
            updated = existing.rstrip() + block
        path.write_text(updated, encoding="utf-8")
        wrote.append(_rel(repo_root, path))

    return {
        "ok": True,
        "wrote": wrote,
        "input_sha256": payload.get("input_sha256"),
        "situation_row_count": len(payload.get("situation_rows") or []),
        "mode_row_count": len(payload.get("mode_rows") or []),
    }
