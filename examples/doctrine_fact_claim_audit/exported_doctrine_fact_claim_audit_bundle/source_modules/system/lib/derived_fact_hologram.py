"""
[PURPOSE]
- Teleology: Generate and query the derived-fact hologram that binds volatile
  documentation claims to live repo state.
- Mechanism: Evaluate authored fact providers from `codex/doctrine/facts`,
  emit ledger/audit/navigation payloads, and audit paper-module fact assertion
  tables against the current ledger.

[CONSTRAINTS]
- The provider registry is authored; `codex/hologram/facts/*` is generated.
- Paper-module prose is never auto-rewritten from fact values.
"""
from __future__ import annotations

import json
import hashlib
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_derived_fact.json"
REGISTRY_PATH = REPO_ROOT / "codex" / "doctrine" / "facts" / "fact_registry.json"
FACT_HOLOGRAM_DIR = REPO_ROOT / "codex" / "hologram" / "facts"
LEDGER_PATH = FACT_HOLOGRAM_DIR / "ledger.json"
AUDIT_PATH = FACT_HOLOGRAM_DIR / "audit.json"
NAVIGATION_CACHE_PATH = FACT_HOLOGRAM_DIR / "navigation_cache.json"
FACT_OUTPUT_PATHS = {
    "ledger": LEDGER_PATH,
    "audit": AUDIT_PATH,
    "navigation_cache": NAVIGATION_CACHE_PATH,
}
VOLATILE_FRESHNESS_FACT_IDS = frozenset(
    {
        "task_ledger.authority.audit_event_count",
        "task_ledger.authority.authority_event_count",
        "task_ledger.events_count",
        "task_ledger.projection.authority_only_closeout_ok",
        "task_ledger.projection.delta_event_count",
        "task_ledger.projection.rebuild_priority_status",
    }
)
_VOLATILE_FRESHNESS_VALUE = "__volatile_fact_value__"
STATE_AXIS_COVERAGE_OVERRIDES = {
    "banned": {
        "coverage_posture": "proof_family_partial",
        "coverage_note": "Covers registered entry/first-contact policy facts only; not all ban-like doctrine system-wide.",
        "missing_known_source_families": [
            "standard_clause_policy_facts",
            "paper_module_policy_facts",
            "process_audit_behavior_facts",
            "dissemination_gate_state_facts",
            "skill_state_facts",
        ],
    },
    "stale": {
        "coverage_posture": "proof_family_partial",
        "coverage_note": "Covers paper-module freshness/status/repair-queue/route-attention state facts; other stale generated surfaces are not harvested yet.",
        "missing_known_source_families": [
            "generated_output_freshness_facts",
            "system_atlas_freshness_facts",
            "task_ledger_state_facts",
            "process_audit_behavior_facts",
        ],
    },
}
STATE_AXIS_COVERAGE_FAMILY_CLOSURES = {
    "dissemination_gate_state_facts": {"dissemination_gate.state_family"},
    "generated_output_freshness_facts": {"generated_output.state_family"},
    "process_audit_behavior_facts": {"process_audit.state_family"},
    "skill_state_facts": {"skill.state_family"},
    "standard_clause_policy_facts": {"standard_clause.state_family"},
    "system_atlas_freshness_facts": {"system_atlas.state_family"},
    "task_ledger_state_facts": {"task_ledger.state_family"},
}
STANDARD_POLICY_TERMS = {
    "banned": "banned",
    "debug only": "debug_only",
    "do not": "do_not",
    "forbidden": "forbidden",
    "must not": "must_not",
    "never": "never",
    "not allowed": "not_allowed",
}
STANDARD_POLICY_SCAN_EXCLUDED_FILES = {
    "std_python_scope_index.json",
}
PROCESS_AUDIT_PATH = "codex/hologram/process/audit.json"
PROCESS_AUDIT_SUMMARY_PATH = "codex/hologram/process/summary.json"
PROCESS_AUDIT_STATIC_SOURCE_PATHS = (
    "system/lib/agent_execution_trace.py",
    "system/lib/kernel/commands/navigate.py",
    "codex/standards/std_agent_execution_trace.json",
    "codex/doctrine/process/trace_rules.json",
)
PROCESS_AUDIT_BANNED_PATTERN_IDS = {
    "anti_pattern_cold_boot_missing_info",
    "anti_pattern_deep_without_ladder",
    "anti_pattern_grep_before_kernel",
    "anti_pattern_paper_module_skip",
}
SKILL_REGISTRY_PATH = "codex/doctrine/skills/skill_registry.json"
SKILL_POLICY_AGENT_SURFACE_FIELDS = ("must", "not_when", "entry")
DISSEMINATION_GATE_SOURCE_PATHS = (
    "docs/dissemination/public_toggle_readiness_gate_v0.json",
    "docs/dissemination/microcosm_release_candidate_gate_v0.json",
    "docs/dissemination/release_claim_language_gate_v0.json",
    "docs/dissemination/microcosm_public_release_boundary_controller_v0.json",
    "docs/dissemination/portability_gate_report_v0.json",
)
DISSEMINATION_PUBLIC_SAFETY_RECEIPT_GLOBS = (
    "tools/meta/microcosm_public_safety/current_findings_receipt_*.json",
    "tools/meta/microcosm_public_safety/generated_refresh_blocked_receipt_*.json",
)
DISSEMINATION_GATE_TOP_LEVEL_FIELDS = (
    "hosted_public_authorized",
    "operator_release_authorization_present",
    "publication_authorized",
    "public_toggle",
    "public_toggle_status",
    "publish_allowed",
    "release_action",
    "release_authorized",
    "status",
)
DISSEMINATION_GATE_NESTED_FIELD_PATHS = (
    ("authority_boundary", "release_authorized"),
    ("authority_boundary", "public_grounding_authorized_by_this_gate"),
    ("release_gate_decision", "overall_release_gate"),
    ("release_gate_decision", "public_toggle_status"),
    ("release_gate_decision", "verifier_public_bound_gate"),
    ("truthful_release_gate", "overall_release_gate"),
    ("truthful_release_gate", "generated_artifact_gate"),
    ("truthful_release_gate", "work_admission_gate"),
)
DISSEMINATION_BLOCKED_VALUES = {
    "absent",
    "amber",
    "block",
    "blocked",
    "blocked_pending_builder_refresh",
    "dirty",
    "fail",
    "false",
    "no_go",
    "none",
    "not_green",
    "not_green_until_portability_gate",
    "not_ready",
    "not_supplied",
    "red",
}

FACT_TABLE_COLUMNS = ("fact id", "expected", "mode", "as of", "tolerance", "why")
CURRENT_ASSERTION_MODES = {"current", "advisory", ""}
HISTORICAL_ASSERTION_MODES = {"snapshot", "historical"}
LIVE_EXPECTED_TOKENS = {"live", "current", "provider", "derived", "*"}
VOLATILE_NUMERIC_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(\d{2,6})\s+(?:[A-Za-z-]+\s+){0,2}"
    r"(annexes|modules|paper modules|patterns|rows|sources|files|docs|documents|notes|entries)\b",
    re.IGNORECASE,
)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)


@dataclass(frozen=True)
class FactAssertion:
    fact_id: str
    expected: str
    mode: str
    as_of: str
    tolerance: str
    why: str
    section: str | None = None
    module_slug: str | None = None
    module_file: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "expected": self.expected,
            "mode": self.mode or "current",
            "as_of": self.as_of,
            "tolerance": self.tolerance,
            "why": self.why,
            "section": self.section,
            "module_slug": self.module_slug,
            "module_file": self.module_file,
        }


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _relpath(path: Path, *, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_read_json(path: Path) -> Any:
    try:
        return _read_json(path)
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _json_pointer_tokens(pointer: str) -> list[str]:
    raw = str(pointer or "").strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if raw == "":
        return []
    if not raw.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer}")
    return [token.replace("~1", "/").replace("~0", "~") for token in raw.split("/")[1:]]


def _json_pointer_escape(token: Any) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def resolve_json_pointer(payload: Any, pointer: str) -> Any:
    value = payload
    for token in _json_pointer_tokens(pointer):
        if isinstance(value, list):
            try:
                value = value[int(token)]
            except (ValueError, IndexError) as exc:
                raise KeyError(token) from exc
        elif isinstance(value, Mapping):
            if token not in value:
                raise KeyError(token)
            value = value[token]
        else:
            raise KeyError(token)
    return value


def _coerce_scalar(value: Any, value_type: str | None = None) -> Any:
    kind = str(value_type or "").strip().lower()
    if kind == "integer":
        return int(value)
    if kind == "number":
        return float(value)
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    if kind == "string":
        return str(value)
    return value


def _value_repr(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _safe_id_token(value: Any) -> str:
    token = str(value or "").strip().lower().replace("-", "_")
    token = re.sub(r"[^a-z0-9_.]+", "_", token).strip("_")
    return token or "unknown"


def _dedupe_strings(items: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _state_tags(*groups: Sequence[Any]) -> list[str]:
    flattened: list[Any] = []
    for group in groups:
        flattened.extend(group)
    return _dedupe_strings(flattened)


def _git_ls_files(repo_root: Path, *pathspecs: str) -> list[str]:
    cmd = ["git", "-C", str(repo_root), "ls-files", *[item for item in pathspecs if item]]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return _dedupe_strings(line for line in result.stdout.splitlines() if line.strip())


def _tracked_file_count(repo_root: Path, *pathspecs: str, exclude_prefixes: Sequence[str] = ()) -> int:
    rows = _git_ls_files(repo_root, *pathspecs)
    prefixes = tuple(str(item) for item in exclude_prefixes)
    if prefixes:
        rows = [row for row in rows if not row.startswith(prefixes)]
    return len(rows)


def _doctrine_paper_module_markdown_count(repo_root: Path) -> int:
    rows = _git_ls_files(repo_root, "codex/doctrine/paper_modules/*.md")
    return len(
        [
            row
            for row in rows
            if "_index" not in row and "_validation" not in row and Path(row).name != "README.md"
        ]
    )


def _raw_seed_markdown_paths(repo_root: Path) -> list[Path]:
    root = repo_root / "obsidian"
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("raw_seed.md") if path.is_file())


def _raw_seed_bytes_total(repo_root: Path) -> int:
    return sum(path.stat().st_size for path in _raw_seed_markdown_paths(repo_root))


def _raw_seed_bytes_phase_09(repo_root: Path) -> int:
    path = (
        repo_root
        / "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.md"
    )
    return path.stat().st_size if path.exists() else 0


def _raw_seed_share_phase_09(repo_root: Path) -> float:
    total = _raw_seed_bytes_total(repo_root)
    if total <= 0:
        return 0.0
    return round(_raw_seed_bytes_phase_09(repo_root) / total, 3)


def _task_ledger_event_count(repo_root: Path) -> int:
    path = repo_root / "state/task_ledger/events.jsonl"
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _provider_status(fact: Mapping[str, Any]) -> str:
    return str(fact.get("provider_status") or fact.get("status") or "unknown")


def _mechanism_ref(ref: str) -> dict[str, str]:
    return {
        "ref": ref,
        "role": "doctrine_reference",
        "enforcement_status": "not_executable_rule_engine",
    }


def _state_fact(
    *,
    fact_id: str,
    title: str,
    family_id: str,
    subject_kind: str,
    subject_ref: str,
    facet: str,
    value: Any,
    tags: Sequence[Any],
    source_path: str,
    pointer: str | None,
    owner_surface: str,
    drilldown_command: str,
    mechanism_refs: Sequence[Mapping[str, Any] | str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_refs: list[Any] = []
    for item in mechanism_refs or []:
        if isinstance(item, Mapping):
            normalized_refs.append(dict(item))
        elif str(item or "").strip():
            normalized_refs.append(_mechanism_ref(str(item).strip()))
    row = {
        "id": fact_id,
        "title": title,
        "family_id": family_id,
        "provider_type": "callable_rows",
        "value_type": "string" if isinstance(value, str) else None,
        "provider_status": "ok",
        "status": "ok",
        "subject_kind": subject_kind,
        "subject_ref": subject_ref,
        "facet": facet,
        "value": value,
        "value_repr": _value_repr(value),
        "tags": _state_tags(tags),
        "source_path": source_path,
        "pointer": pointer,
        "owner_surface": owner_surface,
        "drilldown_command": drilldown_command,
        "mechanism_refs": normalized_refs,
    }
    if extra:
        for key, value in extra.items():
            if value not in (None, ""):
                row[str(key)] = value
    return row


def _indexable_value(value: Any) -> str | None:
    """Index only enum-like values; never index raw payloads or path-like strings."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or len(raw) > 64:
        return None
    if raw.isdigit():
        return None
    if len(raw) > 32 and re.fullmatch(r"[a-fA-F0-9]+", raw):
        return None
    if "/" in raw or "\\" in raw or raw.startswith("."):
        return None
    if re.fullmatch(r"[A-Za-z0-9_.:-]+", raw):
        return raw
    return None


def _stable_digest(payload: Any) -> str:
    text = json.dumps(_strip_generated_at(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _active_phase_entry(repo_root: Path) -> dict[str, Any]:
    phase_index = _safe_read_json(repo_root / "codex" / "derived" / "phase_index.json")
    entries = (phase_index or {}).get("entries") if isinstance(phase_index, Mapping) else []
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            lifecycle = entry.get("lifecycle") if isinstance(entry.get("lifecycle"), Mapping) else {}
            if lifecycle.get("state") == "active" and lifecycle.get("runtime_eligible") is True:
                return dict(entry)
    return {}


def _active_pipeline_state(repo_root: Path) -> dict[str, Any]:
    entry = _active_phase_entry(repo_root)
    phase_dir = str(entry.get("phase_dir") or "").strip()
    candidates = []
    if phase_dir:
        candidates.append(repo_root / phase_dir / "pipeline_state.json")
    candidates.append(repo_root / "pipeline_attention.json")
    for path in candidates:
        payload = _safe_read_json(path)
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def _claude_permission_allow_count(repo_root: Path) -> int:
    payload = _safe_read_json(repo_root / ".claude" / "settings.local.json") or {}
    permissions = payload.get("permissions") if isinstance(payload, Mapping) else {}
    allow = permissions.get("allow") if isinstance(permissions, Mapping) else []
    return len(allow) if isinstance(allow, list) else 0


def _scope_tree_python_runtime_coverage(repo_root: Path, field: str) -> int:
    payload = _safe_read_json(repo_root / "codex" / "hologram" / "system" / "scope_tree.json") or {}
    boundaries = payload.get("boundaries") if isinstance(payload, Mapping) else []
    if not isinstance(boundaries, list):
        return 0
    for boundary in boundaries:
        if not isinstance(boundary, Mapping) or boundary.get("id") != "python_runtime":
            continue
        coverage = boundary.get("coverage") if isinstance(boundary.get("coverage"), Mapping) else {}
        return int(coverage.get(field) or 0)
    return 0


def _reactions_config_reaction_count(repo_root: Path) -> int:
    path = repo_root / "reactions.yaml"
    if not path.exists():
        return 0
    try:
        import yaml  # local import keeps the module lightweight when YAML facts are absent
    except Exception:
        return 0
    try:
        payload = yaml.safe_load(path.read_text())
    except Exception:
        return 0
    if not isinstance(payload, Mapping):
        return 0
    reactions = payload.get("reactions")
    return len(reactions) if isinstance(reactions, list) else 0


def _raw_seed_principles(repo_root: Path) -> list[Mapping[str, Any]]:
    payload = _safe_read_json(
        repo_root
        / "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json"
    ) or {}
    principles = payload.get("principles") if isinstance(payload, Mapping) else []
    return [item for item in principles if isinstance(item, Mapping)] if isinstance(principles, list) else []


def _principle_scope_ontology_count(repo_root: Path, *, active_only: bool = False) -> int:
    total = 0
    for principle in _raw_seed_principles(repo_root):
        scope_profile = principle.get("scope_profile") if isinstance(principle.get("scope_profile"), Mapping) else {}
        if scope_profile.get("paper_module") != "principle_scope_ontology":
            continue
        if active_only and principle.get("status") != "active":
            continue
        total += 1
    return total


def _callable_value(name: str, repo_root: Path) -> Any:
    if name == "routing_hologram_situation_count":
        payload = _safe_read_json(repo_root / "codex" / "doctrine" / "routing_hologram.json") or {}
        rows = payload.get("situation_rows") if isinstance(payload, Mapping) else []
        return len(rows) if isinstance(rows, list) else 0
    if name == "explicit_active_phase_id":
        entry = _active_phase_entry(repo_root)
        return str(entry.get("phase_id") or "")
    if name == "active_pipeline_stage":
        state = _active_pipeline_state(repo_root)
        return str(state.get("stage") or "")
    if name == "active_pipeline_controller_phase":
        state = _active_pipeline_state(repo_root)
        return str(state.get("controller_phase") or "")
    if name == "claude_permission_allow_count":
        return _claude_permission_allow_count(repo_root)
    if name == "hologram_scope_tree_python_runtime_total_files":
        return _scope_tree_python_runtime_coverage(repo_root, "total_files")
    if name == "hologram_scope_tree_python_runtime_dirty_files":
        return _scope_tree_python_runtime_coverage(repo_root, "dirty_files")
    if name == "reactions_config_reaction_count":
        return _reactions_config_reaction_count(repo_root)
    if name == "principles_global_count":
        return _principle_scope_ontology_count(repo_root, active_only=False)
    if name == "principles_global_active_count":
        return _principle_scope_ontology_count(repo_root, active_only=True)
    if name == "principles_total_count":
        return len(_raw_seed_principles(repo_root))
    if name == "repo_tracked_python_count":
        return _tracked_file_count(repo_root, "*.py")
    if name == "repo_substrate_python_count":
        return _tracked_file_count(
            repo_root,
            "tools/meta/*.py",
            "tools/meta/**/*.py",
            "kernel.py",
            "system/*.py",
            "system/**/*.py",
        )
    if name == "doctrine_paper_modules_markdown_count":
        return _doctrine_paper_module_markdown_count(repo_root)
    if name == "doctrine_standards_top_level_count":
        return _tracked_file_count(repo_root, "codex/standards/*.json")
    if name == "doctrine_standards_nested_count":
        return _tracked_file_count(repo_root, "codex/standards/**/*.json")
    if name == "doctrine_concepts_count":
        return _tracked_file_count(repo_root, "codex/doctrine/concepts/*.json")
    if name == "doctrine_mechanisms_count":
        return _tracked_file_count(repo_root, "codex/doctrine/mechanisms/*.json")
    if name == "doctrine_skills_codex_count":
        return _tracked_file_count(repo_root, "codex/doctrine/skills/**/*.md")
    if name == "doctrine_skills_agents_count":
        return _tracked_file_count(repo_root, ".agents/skills/**/SKILL.md")
    if name == "frontend_tracked_files_count":
        return _tracked_file_count(repo_root, "system/server/ui/**")
    if name == "frontend_tsx_count":
        return _tracked_file_count(repo_root, "system/server/ui/**/*.tsx")
    if name == "raw_seed_bytes_total":
        return _raw_seed_bytes_total(repo_root)
    if name == "raw_seed_bytes_phase_09":
        return _raw_seed_bytes_phase_09(repo_root)
    if name == "raw_seed_share_phase_09":
        return _raw_seed_share_phase_09(repo_root)
    if name == "repo_tracked_files_total":
        return _tracked_file_count(repo_root)
    if name == "repo_tracked_files_excluding_annexes":
        return _tracked_file_count(repo_root, exclude_prefixes=("annexes/",))
    if name == "task_ledger_events_count":
        return _task_ledger_event_count(repo_root)
    raise KeyError(f"unknown callable fact provider: {name}")


def _entry_policy_facts(repo_root: Path, *, family_id: str, base_tags: Sequence[Any]) -> list[dict[str, Any]]:
    standard_path = "codex/standards/std_agent_entry_surface.json"
    bootstrap_path = "codex/doctrine/agent_bootstrap.json"
    standard = _safe_read_json(repo_root / standard_path) or {}
    bootstrap = _safe_read_json(repo_root / bootstrap_path) or {}
    routes = bootstrap.get("situation_routes") if isinstance(bootstrap, Mapping) else []
    first_move = {}
    if isinstance(standard, Mapping):
        first_move = (
            (standard.get("canonical_option_surface_routes") or {}).get("first_move_contract")
            if isinstance(standard.get("canonical_option_surface_routes"), Mapping)
            else {}
        )
    first_move = first_move if isinstance(first_move, Mapping) else {}
    route_by_id = {
        str(item.get("situation_id") or item.get("step_id") or "").strip(): item
        for item in (routes or [])
        if isinstance(item, Mapping)
    }
    replacement = str(first_move.get("first_situation_route_command_prefix") or "./repo-python kernel.py --entry").strip()
    replacement_command = f'{replacement} "<task>" --context-budget 12000'
    mechanism_refs = [_mechanism_ref("mech_031")]
    rows: list[dict[str, Any]] = []
    allowed_surfaces = [
        ("entry", "entry_control_packet", str(first_move.get("first_situation_route_command_prefix") or "./repo-python kernel.py --entry")),
        (
            "context_pack",
            "task_conditioned_context_pack_entry",
            str(first_move.get("context_pack_step_command_prefix") or "./repo-python kernel.py --context-pack"),
        ),
        (
            "navigation_metabolism",
            "navigation_metabolism",
            str(first_move.get("navigation_metabolism_step_command_prefix") or "./repo-python kernel.py --navigation-metabolism"),
        ),
        (
            "workitem_entrypoint",
            "workitem_entrypoint",
            str(first_move.get("workitem_entrypoint_command_prefix") or "./repo-python kernel.py --workitem-entrypoint"),
        ),
    ]
    for surface_ref, route_ref, command_prefix in allowed_surfaces:
        route = route_by_id.get(route_ref, {})
        source = bootstrap_path if route else standard_path
        pointer = (
            f"/situation_routes/{list(route_by_id).index(route_ref)}"
            if route_ref in route_by_id
            else "/canonical_option_surface_routes/first_move_contract"
        )
        rows.append(
            _state_fact(
                fact_id=f"entry_policy.{_safe_id_token(surface_ref)}.first_contact_policy",
                title=f"Entry policy for {surface_ref}",
                family_id=family_id,
                subject_kind="entry_surface",
                subject_ref=surface_ref,
                facet="first_contact_policy",
                value="allowed",
                tags=_state_tags(base_tags, ["allowed", "first_contact", "route_policy"]),
                source_path=source,
                pointer=pointer,
                owner_surface="std_agent_entry_surface",
                drilldown_command=f"{command_prefix} \"<task>\" --context-budget 12000",
                mechanism_refs=mechanism_refs,
            )
        )
    banned_surfaces = [
        ("kind_atlas", "--kind-atlas"),
        ("option_surface", "--option-surface"),
        ("paper_module", "--paper-module"),
        ("paper_lattice", "--paper-lattice"),
        ("skill_find", "--skill-find"),
        ("annex_inspiration", "--annex-inspiration"),
        ("docs_route", "--docs-route"),
        ("ranked_debug_internals", "ranked debug internals"),
    ]
    for item in first_move.get("demoted_bespoke_flags") or []:
        surface = _safe_id_token(str(item).lstrip("-"))
        pair = (surface, str(item))
        if pair not in banned_surfaces:
            banned_surfaces.append(pair)
    for surface_ref, display in banned_surfaces:
        rows.append(
            _state_fact(
                fact_id=f"entry_policy.{_safe_id_token(surface_ref)}.first_contact_policy",
                title=f"First-contact policy for {display}",
                family_id=family_id,
                subject_kind="entry_surface",
                subject_ref=surface_ref,
                facet="first_contact_policy",
                value="banned",
                tags=_state_tags(base_tags, ["banned", "first_contact", "route_policy"]),
                source_path=standard_path,
                pointer="/canonical_option_surface_routes/first_move_contract",
                owner_surface="std_agent_entry_surface",
                drilldown_command=replacement_command,
                mechanism_refs=mechanism_refs,
            )
        )
        rows.append(
            _state_fact(
                fact_id=f"entry_policy.{_safe_id_token(surface_ref)}.control_replacement",
                title=f"Control replacement for {display}",
                family_id=family_id,
                subject_kind="entry_surface",
                subject_ref=surface_ref,
                facet="control_replacement",
                value=replacement_command,
                tags=_state_tags(base_tags, ["replacement_route", "first_contact", "route_policy"]),
                source_path=standard_path,
                pointer="/canonical_option_surface_routes/first_move_contract",
                owner_surface="std_agent_entry_surface",
                drilldown_command=replacement_command,
                mechanism_refs=mechanism_refs,
            )
        )
    drilldown = route_by_id.get("russian_doll_option_surface_entry")
    if isinstance(drilldown, Mapping):
        rows.append(
            _state_fact(
                fact_id="entry_policy.russian_doll_option_surface_entry.surface_role",
                title="Russian-doll option surface route role",
                family_id=family_id,
                subject_kind="entry_route",
                subject_ref="russian_doll_option_surface_entry",
                facet="surface_role",
                value="atlas_projection_drilldown",
                tags=_state_tags(base_tags, ["first_contact", "route_policy", "drilldown"]),
                source_path=bootstrap_path,
                pointer=f"/situation_routes/{list(route_by_id).index('russian_doll_option_surface_entry')}",
                owner_surface="agent_bootstrap",
                drilldown_command=str(drilldown.get("route_command") or "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag"),
                mechanism_refs=mechanism_refs,
            )
        )
    return rows


def _iter_json_string_leaves(value: Any, tokens: Sequence[Any] = ()) -> list[tuple[list[Any], str]]:
    if isinstance(value, str):
        return [(list(tokens), value)]
    if isinstance(value, Mapping):
        rows: list[tuple[list[Any], str]] = []
        for key, item in value.items():
            rows.extend(_iter_json_string_leaves(item, [*tokens, key]))
        return rows
    if isinstance(value, list):
        rows = []
        for index, item in enumerate(value):
            rows.extend(_iter_json_string_leaves(item, [*tokens, index]))
        return rows
    return []


def _policy_terms(text: str) -> list[str]:
    lower = text.lower()
    return [term_id for phrase, term_id in STANDARD_POLICY_TERMS.items() if phrase in lower]


def _standard_clause_source_paths(repo_root: Path) -> list[Path]:
    root = repo_root / "codex/standards"
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.glob("std_*.json")
        if path.is_file() and path.name not in STANDARD_POLICY_SCAN_EXCLUDED_FILES
    )


def _standard_clause_policy_facts(
    repo_root: Path,
    *,
    family_id: str,
    base_tags: Sequence[Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _standard_clause_source_paths(repo_root):
        payload = _safe_read_json(path)
        if not isinstance(payload, Mapping):
            continue
        source_path = _relpath(path, repo_root=repo_root)
        standard_id = str(payload.get("id") or path.stem).strip()
        owner_surface = standard_id or path.stem
        for pointer_tokens, clause in _iter_json_string_leaves(payload):
            term_ids = _policy_terms(clause)
            if not term_ids:
                continue
            pointer = "/" + "/".join(_json_pointer_escape(token) for token in pointer_tokens)
            digest = hashlib.sha256(f"{source_path}#{pointer}".encode("utf-8")).hexdigest()[:12]
            rows.append(
                _state_fact(
                    fact_id=f"standard_clause.{_safe_id_token(owner_surface)}.{digest}.policy_status",
                    title=f"Standard {owner_surface} policy clause {pointer}",
                    family_id=family_id,
                    subject_kind="standard_clause",
                    subject_ref=owner_surface,
                    facet="policy_status",
                    value="banned",
                    tags=_state_tags(
                        base_tags,
                        ["standard_clause", "standards", "policy", "banned"],
                        term_ids,
                    ),
                    source_path=source_path,
                    pointer=pointer,
                    owner_surface=owner_surface,
                    drilldown_command=f"jq '.' {source_path}",
                    mechanism_refs=[],
                )
            )
    return rows


def _iter_skill_registry_rows(payload: Mapping[str, Any]) -> list[tuple[int, int, Mapping[str, Any], Mapping[str, Any]]]:
    rows: list[tuple[int, int, Mapping[str, Any], Mapping[str, Any]]] = []
    for family_index, family in enumerate(payload.get("families") or []):
        if not isinstance(family, Mapping):
            continue
        for skill_index, skill in enumerate(family.get("skills") or []):
            if isinstance(skill, Mapping):
                rows.append((family_index, skill_index, family, skill))
    return rows


def _skill_state_facts(
    repo_root: Path,
    *,
    family_id: str,
    base_tags: Sequence[Any],
) -> list[dict[str, Any]]:
    path = repo_root / SKILL_REGISTRY_PATH
    payload = _safe_read_json(path)
    if not isinstance(payload, Mapping):
        return []
    facts: list[dict[str, Any]] = []
    for family_index, skill_index, family, skill in _iter_skill_registry_rows(payload):
        skill_id = str(skill.get("id") or "").strip()
        if not skill_id:
            continue
        family_ref = str(family.get("family_id") or skill.get("family") or "").strip()
        agent_surface = skill.get("agent_surface")
        if not isinstance(agent_surface, Mapping):
            continue
        skill_file = str(skill.get("file") or "").strip()
        owner_surface = skill_id
        for field in SKILL_POLICY_AGENT_SURFACE_FIELDS:
            text = str(agent_surface.get(field) or "").strip()
            term_ids = _policy_terms(text)
            if not term_ids:
                continue
            pointer = f"/families/{family_index}/skills/{skill_index}/agent_surface/{_json_pointer_escape(field)}"
            digest = hashlib.sha256(f"{SKILL_REGISTRY_PATH}#{pointer}".encode("utf-8")).hexdigest()[:12]
            facts.append(
                _state_fact(
                    fact_id=f"skill.{_safe_id_token(skill_id)}.{digest}.policy_status",
                    title=f"Skill {skill_id} policy field {field}",
                    family_id=family_id,
                    subject_kind="skill",
                    subject_ref=skill_id,
                    facet="policy_status",
                    value="banned",
                    tags=_state_tags(
                        base_tags,
                        ["skill", "skills", "policy", "banned"],
                        [family_ref, field, *term_ids],
                    ),
                    source_path=SKILL_REGISTRY_PATH,
                    pointer=pointer,
                    owner_surface=owner_surface,
                    drilldown_command=f"./repo-python kernel.py --option-surface skills --band card --ids {skill_id}",
                    mechanism_refs=[],
                    extra={
                        "skill_file": skill_file or None,
                        "skill_family": family_ref or None,
                    },
                )
            )
    return facts


def _latest_existing_paths(repo_root: Path, patterns: Sequence[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(repo_root.glob(pattern))
        if matches:
            paths.append(matches[-1])
    return paths


def _dissemination_gate_source_paths(repo_root: Path) -> list[Path]:
    paths = [repo_root / rel for rel in DISSEMINATION_GATE_SOURCE_PATHS]
    paths.extend(_latest_existing_paths(repo_root, DISSEMINATION_PUBLIC_SAFETY_RECEIPT_GLOBS))
    return [path for path in paths if path.exists() and path.is_file()]


def _nested_value(payload: Mapping[str, Any], tokens: Sequence[str]) -> Any:
    value: Any = payload
    for token in tokens:
        if not isinstance(value, Mapping):
            return None
        value = value.get(token)
    return value


def _dissemination_gate_is_blocked(facet: str, value: Any) -> bool:
    if isinstance(value, bool):
        return not value and any(
            token in facet
            for token in ("authorized", "allowed", "operator_release_authorization", "public_grounding")
        )
    if isinstance(value, int) and not isinstance(value, bool):
        return value > 0 and facet in {"blocking_condition_count", "blocker_count"}
    normalized = _safe_id_token(str(value or ""))
    return normalized in DISSEMINATION_BLOCKED_VALUES or normalized.startswith("blocks_")


def _dissemination_gate_tags(facet: str, value: Any, base_tags: Sequence[Any]) -> list[str]:
    raw = str(value if value is not None else "").strip()
    normalized = _safe_id_token(raw)
    tags = ["dissemination_gate", "release_gate", "public_safety", "state", facet]
    if normalized and len(normalized) <= 80:
        tags.append(normalized)
    if _dissemination_gate_is_blocked(facet, value):
        tags.extend(["blocked", "banned"])
    elif normalized in {"clear", "green", "pass", "true"} or value is True:
        tags.append("fresh")
    return _state_tags(base_tags, tags)


def _dissemination_gate_fact(
    *,
    gate_id: str,
    family_id: str,
    base_tags: Sequence[Any],
    source_path: str,
    pointer: str,
    facet: str,
    value: Any,
) -> dict[str, Any]:
    digest = hashlib.sha256(f"{source_path}#{pointer}".encode("utf-8")).hexdigest()[:12]
    return _state_fact(
        fact_id=f"dissemination_gate.{_safe_id_token(gate_id)}.{digest}.{_safe_id_token(facet)}",
        title=f"Dissemination gate {gate_id} {facet}",
        family_id=family_id,
        subject_kind="dissemination_gate",
        subject_ref=gate_id,
        facet=facet,
        value=value,
        tags=_dissemination_gate_tags(facet, value, base_tags),
        source_path=source_path,
        pointer=pointer,
        owner_surface=gate_id,
        drilldown_command=f"jq '.' {source_path}",
        mechanism_refs=[],
    )


def _dissemination_gate_state_facts(
    repo_root: Path,
    *,
    family_id: str,
    base_tags: Sequence[Any],
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for path in _dissemination_gate_source_paths(repo_root):
        payload = _safe_read_json(path)
        if not isinstance(payload, Mapping):
            continue
        source_path = _relpath(path, repo_root=repo_root)
        gate_id = str(payload.get("receipt_id") or payload.get("policy_id") or path.stem).strip()
        gate_id = gate_id or path.stem
        for field in DISSEMINATION_GATE_TOP_LEVEL_FIELDS:
            if field in payload:
                facts.append(
                    _dissemination_gate_fact(
                        gate_id=gate_id,
                        family_id=family_id,
                        base_tags=base_tags,
                        source_path=source_path,
                        pointer=f"/{_json_pointer_escape(field)}",
                        facet=field,
                        value=payload.get(field),
                    )
                )
        summary = payload.get("summary")
        if isinstance(summary, Mapping) and "blocking_condition_count" in summary:
            facts.append(
                _dissemination_gate_fact(
                    gate_id=gate_id,
                    family_id=family_id,
                    base_tags=base_tags,
                    source_path=source_path,
                    pointer="/summary/blocking_condition_count",
                    facet="blocking_condition_count",
                    value=summary.get("blocking_condition_count"),
                )
            )
        blockers = payload.get("blocking_conditions")
        if isinstance(blockers, list):
            facts.append(
                _dissemination_gate_fact(
                    gate_id=gate_id,
                    family_id=family_id,
                    base_tags=base_tags,
                    source_path=source_path,
                    pointer="/blocking_conditions",
                    facet="blocking_condition_count",
                    value=len(blockers),
                )
            )
            for index, blocker in enumerate(blockers):
                if not isinstance(blocker, Mapping):
                    continue
                blocker_id = str(blocker.get("id") or f"blocker_{index}").strip()
                release_effect = str(blocker.get("release_effect") or "").strip()
                if release_effect:
                    facts.append(
                        _dissemination_gate_fact(
                            gate_id=gate_id,
                            family_id=family_id,
                            base_tags=base_tags,
                            source_path=source_path,
                            pointer=f"/blocking_conditions/{index}/release_effect",
                            facet=f"blocking_condition.{_safe_id_token(blocker_id)}",
                            value=release_effect,
                        )
                    )
        for tokens in DISSEMINATION_GATE_NESTED_FIELD_PATHS:
            value = _nested_value(payload, tokens)
            if value is None:
                continue
            pointer = "/" + "/".join(_json_pointer_escape(token) for token in tokens)
            facts.append(
                _dissemination_gate_fact(
                    gate_id=gate_id,
                    family_id=family_id,
                    base_tags=base_tags,
                    source_path=source_path,
                    pointer=pointer,
                    facet=".".join(tokens),
                    value=value,
                )
            )
    return facts


def _module_field_value(module: Mapping[str, Any], dotted: str) -> Any:
    value: Any = module
    for token in dotted.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(token)
    return value


def _paper_module_state_tags(facet: str, value: Any, base_tags: Sequence[Any]) -> list[str]:
    raw_value = str(value or "").strip()
    tags = ["paper_modules", "state", facet]
    if raw_value:
        tags.append(_safe_id_token(raw_value))
    if facet in {"status", "code_loci_freshness_status"}:
        tags.append("freshness")
    if raw_value.startswith("stale") or raw_value in {"source_changed", "refresh", "split"}:
        tags.append("stale")
    if raw_value in {"source_current", "up_to_date", "trust"}:
        tags.append("fresh")
    if facet == "primary_subdomain":
        tags.append("taxonomy")
    return _state_tags(base_tags, tags)


def _slug_set_from_queue(queue: Any) -> set[str]:
    out: set[str] = set()
    if not isinstance(queue, list):
        return out
    for item in queue:
        if isinstance(item, Mapping):
            slug = str(item.get("slug") or "").strip()
        else:
            slug = str(item or "").strip()
        if slug:
            out.add(slug)
    return out


def _paper_module_state_facts(repo_root: Path, *, family_id: str, base_tags: Sequence[Any]) -> list[dict[str, Any]]:
    index_path = "codex/doctrine/paper_modules/_index.json"
    route_coverage_path = "codex/doctrine/paper_modules/_route_coverage.json"
    validation_path = "codex/doctrine/paper_modules/_validation_report.json"
    index_payload = _safe_read_json(repo_root / index_path) or {}
    route_payload = _safe_read_json(repo_root / route_coverage_path) or {}
    validation_payload = _safe_read_json(repo_root / validation_path) or {}
    modules = index_payload.get("modules") if isinstance(index_payload, Mapping) else []
    if not isinstance(modules, list):
        modules = []
    route_attention = set()
    if isinstance(route_payload, Mapping):
        attention = route_payload.get("attention")
        if isinstance(attention, Mapping):
            for queue in attention.values():
                route_attention.update(_slug_set_from_queue(queue))
    validation_queues: dict[str, set[str]] = {}
    if isinstance(validation_payload, Mapping):
        for queue_name in ("refresh_queue", "split_queue", "first_author_queue", "deprecate_queue"):
            queue = validation_payload.get(queue_name)
            validation_queues[queue_name] = _slug_set_from_queue(queue)
    fields = [
        ("status", "status"),
        ("recommended_action", "recommended_action"),
        ("code_loci_freshness_status", "code_loci_freshness.status"),
        ("projection_class", "projection_class"),
    ]
    rows: list[dict[str, Any]] = []
    for index, module in enumerate(modules):
        if not isinstance(module, Mapping):
            continue
        slug = str(module.get("slug") or "").strip()
        if not slug:
            continue
        for facet, field in fields:
            value = _module_field_value(module, field)
            if value is None or value == "":
                continue
            rows.append(
                _state_fact(
                    fact_id=f"paper_module.{_safe_id_token(slug)}.{facet}",
                    title=f"Paper module {slug} {facet}",
                    family_id=family_id,
                    subject_kind="paper_module",
                    subject_ref=slug,
                    facet=facet,
                    value=value,
                    tags=_paper_module_state_tags(facet, value, base_tags),
                    source_path=index_path,
                    pointer=f"/modules/{index}/{field.replace('.', '/')}",
                    owner_surface="std_paper_module",
                    drilldown_command=f"./repo-python kernel.py --option-surface paper_modules --band card --ids {slug}",
                    mechanism_refs=[],
                )
            )
        for queue_name, queue in validation_queues.items():
            if slug in queue:
                rows.append(
                    _state_fact(
                        fact_id=f"paper_module.{_safe_id_token(slug)}.{queue_name}_membership",
                        title=f"Paper module {slug} {queue_name} membership",
                        family_id=family_id,
                        subject_kind="paper_module",
                        subject_ref=slug,
                        facet=f"{queue_name}_membership",
                        value="active",
                        tags=_state_tags(base_tags, ["paper_modules", "stale", "repair_queue", queue_name]),
                        source_path=validation_path,
                        pointer=f"/{queue_name}",
                        owner_surface="std_paper_module",
                        drilldown_command=f"./repo-python kernel.py --paper-module-facts {slug}",
                        mechanism_refs=[],
                    )
                )
        if slug in route_attention:
            rows.append(
                _state_fact(
                    fact_id=f"paper_module.{_safe_id_token(slug)}.route_health_attention",
                    title=f"Paper module {slug} route-health attention state",
                    family_id=family_id,
                    subject_kind="paper_module",
                    subject_ref=slug,
                    facet="route_health_attention",
                    value="active",
                    tags=_state_tags(base_tags, ["paper_modules", "route_coverage", "stale", "attention"]),
                    source_path=route_coverage_path,
                    pointer="/attention",
                    owner_surface="std_paper_module",
                    drilldown_command=f"./repo-python kernel.py --option-surface paper_modules --band card --ids {slug}",
                    mechanism_refs=[],
                )
            )
    return rows


def _generated_output_state_tags(facet: str, value: Any, base_tags: Sequence[Any]) -> list[str]:
    raw_value = str(value or "").strip()
    tags = ["generated_output", "generated_projection", "state", facet]
    if raw_value:
        tags.append(_safe_id_token(raw_value))
    if raw_value in {"clean", "already_landed", "none"}:
        tags.append("fresh")
    if raw_value not in {"clean", "already_landed", "none", "true"}:
        tags.append("stale")
    return _state_tags(base_tags, tags)


def _generated_output_settlement_facts(
    repo_root: Path,
    *,
    family_id: str,
    base_tags: Sequence[Any],
) -> list[dict[str, Any]]:
    from system.lib.generated_state_drainer import build_generated_projection_settlement_fast_plan

    plan = build_generated_projection_settlement_fast_plan(repo_root)
    owners = plan.get("owners") if isinstance(plan, Mapping) else []
    if not isinstance(owners, list):
        owners = []
    rows: list[dict[str, Any]] = []
    fields = [
        ("status", "status"),
        ("required_action", "required_action"),
        ("dirty_status", "dirty_status"),
        ("source_dirty_status", "source_dirty_status"),
        ("freshness_status", "freshness_status"),
        ("can_apply", "can_apply"),
        ("path_count", "path_count"),
    ]
    for index, owner in enumerate(owners):
        if not isinstance(owner, Mapping):
            continue
        owner_id = str(owner.get("owner_id") or "").strip()
        if not owner_id:
            continue
        drilldown_command = (
            "./repo-python tools/meta/control/generated_state_drainer.py "
            f"settlement-plan --owner-id {owner_id} --fast --compact"
        )
        source_path = str(owner.get("landing_manifest_path") or "system/lib/generated_state_drainer.py")
        for facet, field in fields:
            if field not in owner:
                continue
            value = owner.get(field)
            rows.append(
                _state_fact(
                    fact_id=f"generated_output.{_safe_id_token(owner_id)}.{facet}",
                    title=f"Generated output {owner_id} {facet}",
                    family_id=family_id,
                    subject_kind="generated_output_owner",
                    subject_ref=owner_id,
                    facet=facet,
                    value=value,
                    tags=_generated_output_state_tags(facet, value, base_tags),
                    source_path=source_path,
                    pointer=f"/owners/{index}/{field}",
                    owner_surface="generated_state_drainer",
                    drilldown_command=drilldown_command,
                    mechanism_refs=[],
                )
            )
    return rows


def _system_atlas_state_tags(facet: str, value: Any, base_tags: Sequence[Any]) -> list[str]:
    raw_value = str(value if value is not None else "").strip()
    tags = ["system_atlas", "state", "freshness", facet]
    if raw_value:
        tags.append(_safe_id_token(raw_value))
    stale_values = {
        "missing",
        "system_atlas_graph_missing",
        "source_inputs_changed_since_artifact_generation",
        "false",
        "blocked",
        "changed",
        "unreadable_artifact",
    }
    fresh_values = {
        "available",
        "system_atlas_graph_available",
        "source_inputs_match_artifact_generation",
        "true",
        "clean",
        "0",
    }
    normalized = _safe_id_token(raw_value)
    if normalized in stale_values:
        tags.append("stale")
    if normalized in fresh_values:
        tags.append("fresh")
    return _state_tags(base_tags, tags)


def _path_latest_mtime(paths: Sequence[Path]) -> str | None:
    latest = 0.0
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        if not path.is_file():
            continue
        latest = max(latest, stat.st_mtime)
    if latest <= 0:
        return None
    return datetime.fromtimestamp(latest, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atlas_source_paths(repo_root: Path, row: Mapping[str, Any]) -> list[Path]:
    raw_path = str(row.get("path") or "").strip()
    raw_paths = [str(item).strip() for item in row.get("paths") or [] if str(item).strip()]
    if raw_path and any(char in raw_path for char in "*?[]"):
        return sorted(path for path in repo_root.glob(raw_path) if path.is_file())
    if raw_paths:
        return [repo_root / path for path in raw_paths]
    return [repo_root / raw_path] if raw_path else []


def _system_atlas_source_change_rows(repo_root: Path, graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = graph.get("source_inputs") if isinstance(graph.get("source_inputs"), list) else []
    changed: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            continue
        current_paths = _atlas_source_paths(repo_root, row)
        current_count = sum(1 for path in current_paths if path.is_file())
        current_latest_mtime = _path_latest_mtime(current_paths)
        previous_count = int(row.get("count") or 0)
        previous_latest_mtime = str(row.get("latest_mtime") or "")
        if current_count == previous_count and str(current_latest_mtime or "") == previous_latest_mtime:
            continue
        changed.append(
            {
                "index": index,
                "source_id": str(row.get("source_id") or row.get("kind") or row.get("path") or f"source_{index}"),
                "path": str(row.get("path") or ""),
                "current_count": current_count,
                "previous_count": previous_count,
                "current_latest_mtime": current_latest_mtime,
                "previous_latest_mtime": previous_latest_mtime,
            }
        )
    return changed


def _system_atlas_currentness_facts(
    repo_root: Path,
    *,
    family_id: str,
    base_tags: Sequence[Any],
) -> list[dict[str, Any]]:
    graph_path = repo_root / "state/system_atlas/system_atlas.graph.json"
    drilldown_command = "./repo-python tools/meta/factory/build_system_atlas.py --check"
    graph = _safe_read_json(graph_path)
    if not isinstance(graph, Mapping):
        return [
            _state_fact(
                fact_id="system_atlas.projection.graph_status",
                title="System Atlas projection graph status",
                family_id=family_id,
                subject_kind="system_atlas_projection",
                subject_ref="system_atlas",
                facet="graph_status",
                value="system_atlas_graph_missing",
                tags=_system_atlas_state_tags("graph_status", "system_atlas_graph_missing", base_tags),
                source_path="state/system_atlas/system_atlas.graph.json",
                pointer="",
                owner_surface="std_system_atlas",
                drilldown_command=drilldown_command,
                mechanism_refs=[],
            )
        ]
    summary = graph.get("summary") if isinstance(graph.get("summary"), Mapping) else {}
    source_inputs = graph.get("source_inputs") if isinstance(graph.get("source_inputs"), list) else []
    changed_sources = _system_atlas_source_change_rows(repo_root, graph)
    source_coupling_status = (
        "source_inputs_changed_since_artifact_generation"
        if changed_sources
        else "source_inputs_match_artifact_generation"
    )
    safe_to_commit = not changed_sources
    rows = [
        ("graph_status", "system_atlas_graph_available", "/schema_version"),
        ("source_coupling_status", source_coupling_status, "/source_inputs"),
        ("safe_to_commit_generated_outputs_without_sources", safe_to_commit, "/source_inputs"),
        ("changed_source_count", len(changed_sources), "/source_inputs"),
        ("source_input_count", len(source_inputs), "/source_inputs"),
        ("entity_count", summary.get("entity_count"), "/summary/entity_count"),
        ("finding_count", summary.get("finding_count"), "/summary/finding_count"),
    ]
    facts: list[dict[str, Any]] = []
    for facet, value, pointer in rows:
        if value is None:
            continue
        facts.append(
            _state_fact(
                fact_id=f"system_atlas.projection.{facet}",
                title=f"System Atlas projection {facet}",
                family_id=family_id,
                subject_kind="system_atlas_projection",
                subject_ref="system_atlas",
                facet=facet,
                value=value,
                tags=_system_atlas_state_tags(facet, value, base_tags),
                source_path="state/system_atlas/system_atlas.graph.json",
                pointer=pointer,
                owner_surface="std_system_atlas",
                drilldown_command=drilldown_command,
                mechanism_refs=[],
            )
        )
    for changed in changed_sources:
        source_id = changed["source_id"]
        facts.append(
            _state_fact(
                fact_id=f"system_atlas.source.{_safe_id_token(source_id)}.source_coupling_status",
                title=f"System Atlas source {source_id} source-coupling status",
                family_id=family_id,
                subject_kind="system_atlas_source_input",
                subject_ref=source_id,
                facet="source_coupling_status",
                value="changed",
                tags=_state_tags(
                    base_tags,
                    ["system_atlas", "state", "freshness", "source_coupling", "changed", "stale"],
                ),
                source_path="state/system_atlas/system_atlas.graph.json",
                pointer=f"/source_inputs/{changed['index']}",
                owner_surface="std_system_atlas",
                drilldown_command=drilldown_command,
                mechanism_refs=[],
            )
        )
    return facts


def _task_ledger_state_tags(facet: str, value: Any, base_tags: Sequence[Any]) -> list[str]:
    raw_value = str(value if value is not None else "").strip()
    normalized = _safe_id_token(raw_value)
    tags = ["task_ledger", "state", "freshness", facet]
    volatile_facets = {
        "audit_event_count",
        "authority_event_count",
        "authority_only_closeout_ok",
        "delta_event_count",
        "rebuild_priority_status",
    }
    volatile = facet in volatile_facets
    if raw_value and len(raw_value) <= 64 and not volatile:
        tags.append(normalized)
    stale_values = {
        "attention",
        "authority_recovery_required",
        "blocked",
        "blocked_rotate_or_migrate_authority_before_append",
        "critical",
        "false",
        "high_authority_delta",
        "medium_authority_delta",
        "projection_ahead_of_authority",
        "projection_behind_authority",
        "projection_rebuild_required",
        "unknown_delta",
    }
    fresh_values = {
        "0",
        "append_allowed",
        "clean",
        "event_counts_match",
        "ok",
        "true",
    }
    if normalized in stale_values and not volatile:
        tags.append("stale")
    if normalized in fresh_values and not volatile:
        tags.append("fresh")
    return _state_tags(base_tags, tags)


def _task_ledger_state_fact(
    *,
    fact_id: str,
    title: str,
    family_id: str,
    subject_kind: str,
    subject_ref: str,
    facet: str,
    value: Any,
    base_tags: Sequence[Any],
    source_path: str,
    pointer: str,
    drilldown_command: str,
) -> dict[str, Any]:
    return _state_fact(
        fact_id=fact_id,
        title=title,
        family_id=family_id,
        subject_kind=subject_kind,
        subject_ref=subject_ref,
        facet=facet,
        value=value,
        tags=_task_ledger_state_tags(facet, value, base_tags),
        source_path=source_path,
        pointer=pointer,
        owner_surface="std_task_ledger",
        drilldown_command=drilldown_command,
        mechanism_refs=[],
    )


def _task_ledger_state_facts(
    repo_root: Path,
    *,
    family_id: str,
    base_tags: Sequence[Any],
) -> list[dict[str, Any]]:
    from system.lib import task_ledger_events

    authority = task_ledger_events.authority_health(repo_root, projection_check=True)
    storage = task_ledger_events.task_ledger_authority_storage_status(repo_root)
    projection = authority.get("projection_check") if isinstance(authority.get("projection_check"), Mapping) else {}
    comparison = (
        projection.get("event_count_comparison")
        if isinstance(projection.get("event_count_comparison"), Mapping)
        else {}
    )
    rebuild_priority = (
        projection.get("rebuild_priority") if isinstance(projection.get("rebuild_priority"), Mapping) else {}
    )
    authority_command = "./repo-python tools/meta/factory/task_ledger_apply.py authority-health --projection-check"
    projection_command = "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress"
    migration_command = "./repo-python tools/meta/factory/task_ledger_apply.py authority-migration-plan"
    facts: list[dict[str, Any]] = []
    authority_rows = [
        ("status", authority.get("status"), "/status"),
        ("ok", authority.get("ok"), "/ok"),
        ("authority_event_count", authority.get("authority_event_count"), "/authority_event_count"),
        ("audit_event_count", authority.get("audit_event_count"), "/audit_event_count"),
        ("lost_count", authority.get("lost_count"), "/lost_count"),
    ]
    for facet, value, pointer in authority_rows:
        if value is None:
            continue
        facts.append(
            _task_ledger_state_fact(
                fact_id=f"task_ledger.authority.{facet}",
                title=f"Task Ledger authority {facet}",
                family_id=family_id,
                subject_kind="task_ledger_authority",
                subject_ref="task_ledger",
                facet=facet,
                value=value,
                base_tags=base_tags,
                source_path=str(task_ledger_events.EVENTS_REL),
                pointer=pointer,
                drilldown_command=authority_command,
            )
        )
    projection_rows = [
        ("status", projection.get("status"), "/projection_check/status"),
        ("ok", projection.get("ok"), "/projection_check/ok"),
        ("mismatch_count", projection.get("mismatch_count"), "/projection_check/mismatch_count"),
        ("event_count_status", comparison.get("status"), "/projection_check/event_count_comparison/status"),
        ("delta_event_count", comparison.get("delta"), "/projection_check/event_count_comparison/delta"),
        ("rebuild_priority_status", rebuild_priority.get("status"), "/projection_check/rebuild_priority/status"),
        (
            "authority_only_closeout_ok",
            rebuild_priority.get("authority_only_closeout_ok"),
            "/projection_check/rebuild_priority/authority_only_closeout_ok",
        ),
    ]
    for facet, value, pointer in projection_rows:
        if value is None:
            continue
        facts.append(
            _task_ledger_state_fact(
                fact_id=f"task_ledger.projection.{facet}",
                title=f"Task Ledger projection {facet}",
                family_id=family_id,
                subject_kind="task_ledger_projection",
                subject_ref="task_ledger",
                facet=facet,
                value=value,
                base_tags=base_tags,
                source_path=str(task_ledger_events.LEDGER_REL),
                pointer=pointer,
                drilldown_command=projection_command,
            )
        )
    storage_rows = [
        ("status", storage.get("status"), "/authority_storage/status"),
        ("ok", storage.get("ok"), "/authority_storage/ok"),
        ("size_pressure_status", storage.get("size_pressure_status"), "/authority_storage/size_pressure_status"),
        ("write_admission", storage.get("write_admission"), "/authority_storage/write_admission"),
    ]
    for facet, value, pointer in storage_rows:
        if value is None:
            continue
        facts.append(
            _task_ledger_state_fact(
                fact_id=f"task_ledger.storage.{facet}",
                title=f"Task Ledger storage {facet}",
                family_id=family_id,
                subject_kind="task_ledger_authority_storage",
                subject_ref="task_ledger",
                facet=facet,
                value=value,
                base_tags=base_tags,
                source_path=str(task_ledger_events.EVENTS_REL),
                pointer=pointer,
                drilldown_command=migration_command,
            )
        )
    return facts


def _process_audit_cache_freshness(repo_root: Path) -> dict[str, Any]:
    cache_path = repo_root / PROCESS_AUDIT_PATH
    try:
        cache_mtime_ns = cache_path.stat().st_mtime_ns
    except OSError:
        return {
            "status": "missing",
            "static_source_status": "cache_missing",
            "stale_source_count": 0,
            "missing_source_count": 0,
        }
    stale_sources: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    for rel_path in PROCESS_AUDIT_STATIC_SOURCE_PATHS:
        source_path = repo_root / rel_path
        try:
            source_mtime_ns = source_path.stat().st_mtime_ns
        except OSError:
            missing_sources.append(rel_path)
            continue
        if source_mtime_ns > cache_mtime_ns:
            stale_sources.append({"path": rel_path, "mtime_ns": source_mtime_ns})
    if stale_sources:
        return {
            "status": "stale_static_sources",
            "static_source_status": "source_newer_than_cached_audit",
            "stale_source_count": len(stale_sources),
            "stale_sources_preview": stale_sources[:5],
            "missing_source_count": len(missing_sources),
            "patch_selection_policy": "refresh_or_force_live_before_selecting_process_audit_patch",
            "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
        }
    return {
        "status": "hit",
        "static_source_status": "cached_audit_current_for_static_trace_inputs",
        "stale_source_count": 0,
        "missing_source_count": len(missing_sources),
    }


def _process_audit_behavior_tags(
    facet: str,
    value: Any,
    base_tags: Sequence[Any],
    *,
    subject_ref: str = "",
) -> list[str]:
    raw_value = str(value if value is not None else "").strip()
    normalized = _safe_id_token(raw_value)
    tags = ["process_audit", "agent_execution_trace", "state", "freshness", facet]
    if raw_value and len(raw_value) <= 64:
        tags.append(normalized)
    if normalized in {
        "cache_missing",
        "false",
        "missing",
        "source_newer_than_cached_audit",
        "stale_static_sources",
    }:
        tags.append("stale")
    if normalized in {
        "cached_audit_current_for_static_trace_inputs",
        "clean",
        "hit",
        "ok",
        "true",
    }:
        tags.append("fresh")
    if facet in {
        "error_count",
        "finding_count",
        "missing_source_count",
        "parse_failure_count",
        "pattern_instances",
        "route_lease_warning_session_count",
        "stale_source_count",
        "warning_count",
    }:
        try:
            count = int(value)
        except (TypeError, ValueError):
            count = 0
        tags.append("fresh" if count == 0 else "stale")
        if count > 0:
            tags.append("attention")
    if facet == "average_route_compliance":
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = 0.0
        tags.append("fresh" if score >= 0.95 else "stale")
        if score < 0.95:
            tags.append("attention")
    if facet == "pattern_instances" and subject_ref in PROCESS_AUDIT_BANNED_PATTERN_IDS:
        try:
            if int(value) > 0:
                tags.append("banned")
        except (TypeError, ValueError):
            pass
    return _state_tags(base_tags, tags)


def _process_audit_state_fact(
    *,
    fact_id: str,
    title: str,
    family_id: str,
    subject_kind: str,
    subject_ref: str,
    facet: str,
    value: Any,
    base_tags: Sequence[Any],
    source_path: str,
    pointer: str | None,
    drilldown_command: str,
) -> dict[str, Any]:
    return _state_fact(
        fact_id=fact_id,
        title=title,
        family_id=family_id,
        subject_kind=subject_kind,
        subject_ref=subject_ref,
        facet=facet,
        value=value,
        tags=_process_audit_behavior_tags(facet, value, base_tags, subject_ref=subject_ref),
        source_path=source_path,
        pointer=pointer,
        owner_surface="std_agent_execution_trace",
        drilldown_command=drilldown_command,
        mechanism_refs=[],
    )


def _process_audit_behavior_facts(
    repo_root: Path,
    *,
    family_id: str,
    base_tags: Sequence[Any],
) -> list[dict[str, Any]]:
    audit = _safe_read_json(repo_root / PROCESS_AUDIT_PATH)
    if not isinstance(audit, Mapping):
        audit = {}
    summary = audit.get("summary") if isinstance(audit.get("summary"), Mapping) else {}
    if not summary:
        summary_payload = _safe_read_json(repo_root / PROCESS_AUDIT_SUMMARY_PATH)
        summary = (
            summary_payload.get("summary")
            if isinstance(summary_payload, Mapping) and isinstance(summary_payload.get("summary"), Mapping)
            else {}
        )
    freshness = _process_audit_cache_freshness(repo_root)
    drilldown_command = "./repo-python kernel.py --process-audit"
    rows: list[dict[str, Any]] = []
    cache_rows = [
        ("cache_status", freshness.get("status"), None),
        ("static_source_status", freshness.get("static_source_status"), None),
        ("stale_source_count", freshness.get("stale_source_count"), None),
        ("missing_source_count", freshness.get("missing_source_count"), None),
    ]
    for facet, value, pointer in cache_rows:
        if value is None:
            continue
        rows.append(
            _process_audit_state_fact(
                fact_id=f"process_audit.cache.{facet}",
                title=f"Process audit cache {facet}",
                family_id=family_id,
                subject_kind="process_audit_cache",
                subject_ref="process_audit",
                facet=facet,
                value=value,
                base_tags=base_tags,
                source_path=PROCESS_AUDIT_PATH,
                pointer=pointer,
                drilldown_command=drilldown_command,
            )
        )
    summary_rows = [
        ("finding_count", summary.get("finding_count"), "/summary/finding_count"),
        ("warning_count", summary.get("warning_count"), "/summary/warning_count"),
        ("error_count", summary.get("error_count"), "/summary/error_count"),
        ("parse_failure_count", summary.get("parse_failure_count"), "/summary/parse_failure_count"),
        (
            "route_lease_warning_session_count",
            summary.get("route_lease_warning_session_count"),
            "/summary/route_lease_warning_session_count",
        ),
        ("average_route_compliance", summary.get("average_route_compliance"), "/summary/average_route_compliance"),
    ]
    for facet, value, pointer in summary_rows:
        if value is None:
            continue
        rows.append(
            _process_audit_state_fact(
                fact_id=f"process_audit.summary.{facet}",
                title=f"Process audit summary {facet}",
                family_id=family_id,
                subject_kind="process_audit_summary",
                subject_ref="process_audit",
                facet=facet,
                value=value,
                base_tags=base_tags,
                source_path=PROCESS_AUDIT_PATH,
                pointer=pointer,
                drilldown_command=drilldown_command,
            )
        )
    pattern_counts = summary.get("pattern_counts") if isinstance(summary.get("pattern_counts"), Mapping) else {}
    for pattern_id, count in sorted(pattern_counts.items()):
        pattern_ref = str(pattern_id or "").strip()
        if not pattern_ref:
            continue
        rows.append(
            _process_audit_state_fact(
                fact_id=f"process_audit.pattern.{_safe_id_token(pattern_ref)}.instances",
                title=f"Process audit pattern {pattern_ref} instances",
                family_id=family_id,
                subject_kind="process_audit_pattern",
                subject_ref=pattern_ref,
                facet="pattern_instances",
                value=count,
                base_tags=base_tags,
                source_path=PROCESS_AUDIT_PATH,
                pointer=f"/summary/pattern_counts/{pattern_ref}",
                drilldown_command="./repo-python kernel.py --process-patterns",
            )
        )
    return rows


def _callable_rows(name: str, repo_root: Path, *, family_id: str, base_tags: Sequence[Any]) -> list[dict[str, Any]]:
    if name == "entry_policy_facts":
        return _entry_policy_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "standard_clause_policy_facts":
        return _standard_clause_policy_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "skill_state_facts":
        return _skill_state_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "dissemination_gate_state_facts":
        return _dissemination_gate_state_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "paper_module_state_facts":
        return _paper_module_state_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "generated_output_settlement_facts":
        return _generated_output_settlement_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "system_atlas_currentness_facts":
        return _system_atlas_currentness_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "task_ledger_state_facts":
        return _task_ledger_state_facts(repo_root, family_id=family_id, base_tags=base_tags)
    if name == "process_audit_behavior_facts":
        return _process_audit_behavior_facts(repo_root, family_id=family_id, base_tags=base_tags)
    raise KeyError(f"unknown callable_rows fact provider: {name}")


def _source_repair_command(source_path: str) -> str:
    path = str(source_path or "").strip()
    if path == "codex/hologram/system/scope_tree.json" or path.startswith("codex/hologram/system/"):
        return "./repo-python kernel.py --build --build-phases SELF"
    if path.startswith("codex/hologram/facts/"):
        return "./repo-python tools/meta/factory/build_fact_hologram.py"
    return f"restore_or_rebuild_source_path:{path}" if path else "inspect_fact_provider_source_path"


def _provider_finding(fact: Mapping[str, Any]) -> dict[str, Any]:
    source_status = str(fact.get("source_status") or "").strip()
    rule = "missing_fact_source" if source_status == "missing" else "fact_provider_error"
    finding: dict[str, Any] = {
        "severity": "error",
        "rule": rule,
        "fact_id": str(fact.get("id") or ""),
        "message": str(fact.get("error") or "provider failed"),
    }
    for key in (
        "source_path",
        "source_status",
        "error_class",
        "provider_type",
        "pointer",
        "required_next_action",
    ):
        value = fact.get(key)
        if value not in (None, ""):
            finding[key] = value
    return finding


def _evaluate_provider(row: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    fact_id = str(row.get("id") or "").strip()
    provider_type = str(row.get("provider_type") or "").strip()
    value_type = str(row.get("value_type") or "").strip() or None
    base = {
        "id": fact_id,
        "title": str(row.get("title") or fact_id).strip(),
        "provider_type": provider_type,
        "value_type": value_type,
        "tags": [str(item) for item in (row.get("tags") or []) if str(item).strip()],
        "provider_status": "ok",
        "status": "ok",
        "source_path": str(row.get("source_path") or "").strip() or None,
        "pointer": str(row.get("pointer") or "").strip() or None,
        "glob": str(row.get("glob") or "").strip() or None,
        "callable": str(row.get("callable") or "").strip() or None,
    }
    try:
        if not fact_id:
            raise ValueError("missing fact id")
        if provider_type == "json_pointer":
            source_path = str(row.get("source_path") or "").strip()
            pointer = str(row.get("pointer") or "").strip()
            if not source_path or not pointer:
                raise ValueError("json_pointer provider requires source_path and pointer")
            payload = _read_json(repo_root / source_path)
            value = resolve_json_pointer(payload, pointer)
        elif provider_type == "glob_count":
            pattern = str(row.get("glob") or "").strip()
            if not pattern:
                raise ValueError("glob_count provider requires glob")
            exclude_prefixes = [str(item).strip() for item in (row.get("exclude_prefixes") or []) if str(item).strip()]
            matches = []
            for path in (repo_root).glob(pattern):
                rel = _relpath(path, repo_root=repo_root)
                if any(rel.startswith(prefix) for prefix in exclude_prefixes):
                    continue
                matches.append(rel)
            value = len(matches)
            base["sample_matches"] = sorted(matches)[:20]
        elif provider_type == "callable":
            callable_name = str(row.get("callable") or "").strip()
            if not callable_name:
                raise ValueError("callable provider requires callable")
            value = _callable_value(callable_name, repo_root)
        else:
            raise ValueError(f"unknown provider_type: {provider_type}")
        value = _coerce_scalar(value, value_type)
        base["value"] = value
        base["value_repr"] = _value_repr(value)
    except Exception as exc:  # noqa: BLE001 - fact providers report error rows instead of crashing the ledger.
        base["status"] = "error"
        base["provider_status"] = "error"
        base["error_class"] = exc.__class__.__name__
        base["error"] = str(exc)
        base["value"] = None
        base["value_repr"] = ""
        source_path = str(row.get("source_path") or "").strip()
        if isinstance(exc, FileNotFoundError) and source_path:
            base["source_status"] = "missing"
            base["required_next_action"] = _source_repair_command(source_path)
    return base


def _evaluate_row_family(row: Mapping[str, Any], *, repo_root: Path) -> list[dict[str, Any]]:
    family_id = str(row.get("id") or "").strip()
    callable_name = str(row.get("callable") or "").strip()
    base_tags = [str(item) for item in (row.get("tags") or []) if str(item).strip()]
    try:
        if not family_id:
            raise ValueError("missing fact family id")
        if not callable_name:
            raise ValueError("callable_rows provider requires callable")
        return _callable_rows(callable_name, repo_root, family_id=family_id, base_tags=base_tags)
    except Exception as exc:  # noqa: BLE001 - family errors are represented as provider rows.
        return [
            {
                "id": family_id or "fact_family.unknown.error",
                "title": str(row.get("title") or family_id or "Unknown fact family").strip(),
                "family_id": family_id or None,
                "provider_type": "callable_rows",
                "value_type": "fact_rows",
                "tags": _state_tags(base_tags, ["fact_family", "error"]),
                "provider_status": "error",
                "status": "error",
                "source_path": str(row.get("source_path") or "").strip() or None,
                "pointer": str(row.get("pointer") or "").strip() or None,
                "callable": callable_name or None,
                "error": str(exc),
                "value": None,
                "value_repr": "",
            }
        ]


def load_fact_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    payload = _safe_read_json(path)
    return dict(payload) if isinstance(payload, Mapping) else {"facts": []}


def _fact_search_text(fact: Mapping[str, Any]) -> str:
    parts = [
        fact.get("id"),
        fact.get("title"),
        fact.get("family_id"),
        fact.get("provider_type"),
        fact.get("source_path"),
        fact.get("pointer"),
        fact.get("subject_kind"),
        fact.get("subject_ref"),
        fact.get("facet"),
        fact.get("value_repr"),
        fact.get("owner_surface"),
        " ".join(str(tag) for tag in (fact.get("tags") or [])),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def _fact_nav_row(fact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": fact.get("id"),
        "title": fact.get("title"),
        "value": fact.get("value"),
        "value_repr": fact.get("value_repr"),
        "status": fact.get("status"),
        "provider_status": _provider_status(fact),
        "provider_type": fact.get("provider_type"),
        "family_id": fact.get("family_id"),
        "subject_kind": fact.get("subject_kind"),
        "subject_ref": fact.get("subject_ref"),
        "facet": fact.get("facet"),
        "source_path": fact.get("source_path"),
        "pointer": fact.get("pointer"),
        "owner_surface": fact.get("owner_surface"),
        "drilldown_command": fact.get("drilldown_command"),
        "mechanism_refs": list(fact.get("mechanism_refs") or []),
        "tags": list(fact.get("tags") or []),
        "search_text": _fact_search_text(fact),
    }


def _sample_fact_ids(rows: Sequence[Mapping[str, Any]], *, limit: int = 8) -> list[str]:
    return [str(row.get("id") or "") for row in rows[:limit] if str(row.get("id") or "").strip()]


def _coverage_fields(axis: str, families: Sequence[str]) -> dict[str, Any]:
    family_list = _dedupe_strings(families)
    override = STATE_AXIS_COVERAGE_OVERRIDES.get(axis)
    coverage_posture = "complete_for_registered_fact_families"
    coverage_note = "Generated from currently registered fact families only."
    missing_known_source_families: list[str] = []
    if override is not None:
        coverage_posture = str(override.get("coverage_posture") or coverage_posture)
        coverage_note = str(override.get("coverage_note") or coverage_note)
        for item in override.get("missing_known_source_families") or []:
            missing_family = str(item or "").strip()
            if not missing_family:
                continue
            closure_families = STATE_AXIS_COVERAGE_FAMILY_CLOSURES.get(missing_family, set())
            if closure_families and any(family in closure_families for family in family_list):
                continue
            missing_known_source_families.append(missing_family)
    return {
        "coverage_posture": coverage_posture,
        "covered_fact_families": family_list,
        "missing_known_source_families": missing_known_source_families,
        "omission_receipt": {
            "scope": "registered_fact_families_only",
            "message": coverage_note,
            "missing_known_source_families": missing_known_source_families,
        },
    }


def _tag_index(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        for tag in row.get("tags") or []:
            tag_value = str(tag or "").strip()
            if tag_value:
                buckets.setdefault(tag_value, []).append(row)
    out = []
    for tag, bucket in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        facets = sorted({str(row.get("facet")) for row in bucket if str(row.get("facet") or "").strip()})
        subject_kinds = sorted({str(row.get("subject_kind")) for row in bucket if str(row.get("subject_kind") or "").strip()})
        families = sorted({str(row.get("family_id")) for row in bucket if str(row.get("family_id") or "").strip()})
        sources = sorted({str(row.get("source_path")) for row in bucket if str(row.get("source_path") or "").strip()})
        out.append(
            {
                "tag": tag,
                "fact_count": len(bucket),
                **_coverage_fields(tag, families),
                "facets": facets[:16],
                "subject_kinds": subject_kinds[:16],
                "fact_families": families[:16],
                "source_paths": sources[:10],
                "sample_fact_ids": _sample_fact_ids(bucket),
                "drilldown_command": f"./repo-python kernel.py --facts --facts-tag {tag} --band flag",
            }
        )
    return out


def _facet_index(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        facet = str(row.get("facet") or "").strip()
        if facet:
            buckets.setdefault(facet, []).append(row)
    out = []
    for facet, bucket in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        value_counts: Counter[str] = Counter()
        for row in bucket:
            index_value = _indexable_value(row.get("value"))
            if index_value is not None:
                value_counts[index_value] += 1
        tags = sorted({str(tag) for row in bucket for tag in (row.get("tags") or []) if str(tag).strip()})
        subject_kinds = sorted({str(row.get("subject_kind")) for row in bucket if str(row.get("subject_kind") or "").strip()})
        families = sorted({str(row.get("family_id")) for row in bucket if str(row.get("family_id") or "").strip()})
        out.append(
            {
                "facet": facet,
                "fact_count": len(bucket),
                **_coverage_fields(facet, families),
                "values": dict(sorted(value_counts.items())),
                "tags": tags[:16],
                "subject_kinds": subject_kinds[:16],
                "sample_fact_ids": _sample_fact_ids(bucket),
                "drilldown_command": f"./repo-python kernel.py --facts --facts-facet {facet} --band flag",
            }
        )
    return out


def _value_index(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        value = _indexable_value(row.get("value"))
        if value is not None:
            buckets.setdefault(value, []).append(row)
    out = []
    for value, bucket in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        facets = sorted({str(row.get("facet")) for row in bucket if str(row.get("facet") or "").strip()})
        tags = sorted({str(tag) for row in bucket for tag in (row.get("tags") or []) if str(tag).strip()})
        subject_kinds = sorted({str(row.get("subject_kind")) for row in bucket if str(row.get("subject_kind") or "").strip()})
        families = sorted({str(row.get("family_id")) for row in bucket if str(row.get("family_id") or "").strip()})
        out.append(
            {
                "value": value,
                "fact_count": len(bucket),
                **_coverage_fields(value, families),
                "facets": facets[:16],
                "tags": tags[:16],
                "subject_kinds": subject_kinds[:16],
                "sample_fact_ids": _sample_fact_ids(bucket),
                "drilldown_command": f"./repo-python kernel.py --facts --facts-value {value} --band flag",
            }
        )
    return out


def _subject_kind_index(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        subject_kind = str(row.get("subject_kind") or "").strip()
        if subject_kind:
            buckets.setdefault(subject_kind, []).append(row)
    out = []
    for subject_kind, bucket in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        facets = Counter(str(row.get("facet") or "") for row in bucket if str(row.get("facet") or "").strip())
        values = Counter(_indexable_value(row.get("value")) for row in bucket)
        values.pop(None, None)
        out.append(
            {
                "subject_kind": subject_kind,
                "fact_count": len(bucket),
                "facets": dict(sorted(facets.items())),
                "values": dict(sorted(values.items())),
                "sample_fact_ids": _sample_fact_ids(bucket),
                "drilldown_command": f"./repo-python kernel.py --facts --facts-filter subject_kind:{subject_kind} --band flag",
            }
        )
    return out


def _fact_family_index(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        family_id = str(row.get("family_id") or "").strip()
        if family_id:
            buckets.setdefault(family_id, []).append(row)
    out = []
    for family_id, bucket in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        facets = sorted({str(row.get("facet")) for row in bucket if str(row.get("facet") or "").strip()})
        tags = sorted({str(tag) for row in bucket for tag in (row.get("tags") or []) if str(tag).strip()})
        subject_kinds = sorted({str(row.get("subject_kind")) for row in bucket if str(row.get("subject_kind") or "").strip()})
        out.append(
            {
                "family_id": family_id,
                "fact_count": len(bucket),
                "coverage_posture": "complete_for_registered_family_provider",
                "coverage_note": "Complete for the callable_rows provider output generated by this registered family.",
                "facets": facets[:20],
                "tags": tags[:20],
                "subject_kinds": subject_kinds[:12],
                "sample_fact_ids": _sample_fact_ids(bucket),
                "drilldown_command": f"./repo-python kernel.py --facts --facts-filter family:{family_id} --band flag",
            }
        )
    return out


def _mechanism_ref_index(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        for ref in row.get("mechanism_refs") or []:
            if isinstance(ref, Mapping):
                ref_id = str(ref.get("ref") or "").strip()
            else:
                ref_id = str(ref or "").strip()
            if ref_id:
                buckets.setdefault(ref_id, []).append(row)
    out = []
    for ref_id, bucket in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])):
        out.append(
            {
                "mechanism_ref": ref_id,
                "fact_count": len(bucket),
                "enforcement_status": "not_executable_rule_engine",
                "sample_fact_ids": _sample_fact_ids(bucket),
                "drilldown_command": f"./repo-python kernel.py --facts --facts-filter mechanism_ref:{ref_id} --band flag",
            }
        )
    return out


def build_fact_navigation_cache(
    facts: Sequence[Mapping[str, Any]],
    *,
    summary: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    rows = [_fact_nav_row(fact) for fact in facts]
    indexes = {
        "tag_index": _tag_index(rows),
        "facet_index": _facet_index(rows),
        "value_index": _value_index(rows),
        "subject_kind_index": _subject_kind_index(rows),
        "fact_family_index": _fact_family_index(rows),
        "mechanism_ref_index": _mechanism_ref_index(rows),
    }
    cache = {
        "kind": "derived_fact_navigation_cache",
        "schema_version": "derived_fact_navigation_cache_v2",
        "generated_at": generated_at,
        "artifact_role": "generated_state_axis_artifact",
        "summary": dict(summary),
        "rows": rows,
        **indexes,
    }
    cache["source_fingerprint"] = _stable_digest(
        {
            "rows": rows,
            "indexes": indexes,
            "summary": dict(summary),
        }
    )
    return cache


def build_fact_hologram(
    *,
    repo_root: Path = REPO_ROOT,
    registry_path: Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    registry_path = registry_path or (repo_root / REGISTRY_PATH.relative_to(REPO_ROOT))
    registry = load_fact_registry(registry_path)
    rows = [dict(item) for item in (registry.get("facts") or []) if isinstance(item, Mapping)]
    facts: list[dict[str, Any]] = []
    fact_family_count = 0
    for row in rows:
        provider_type = str(row.get("provider_type") or "").strip()
        if provider_type == "callable_rows":
            fact_family_count += 1
            facts.extend(_evaluate_row_family(row, repo_root=repo_root))
        else:
            facts.append(_evaluate_provider(row, repo_root=repo_root))
    provider_counts = Counter(str(row.get("provider_type") or "unknown") for row in facts)
    status_counts = Counter(_provider_status(row) for row in facts)
    tag_count = len({tag for fact in facts for tag in (fact.get("tags") or []) if str(tag).strip()})
    facet_count = len({str(fact.get("facet")) for fact in facts if str(fact.get("facet") or "").strip()})
    generated_at = timestamp or _utc_iso()
    scalar_fact_count = sum(1 for fact in facts if str(fact.get("provider_type") or "") != "callable_rows")
    rowset_fact_count = sum(1 for fact in facts if str(fact.get("provider_type") or "") == "callable_rows")
    ledger = {
        "kind": "derived_fact_ledger",
        "schema_version": "derived_fact_ledger_v2",
        "generated_at": generated_at,
        "standard": str(STANDARD_PATH.relative_to(REPO_ROOT)),
        "registry_path": _relpath(registry_path, repo_root=repo_root),
        "summary": {
            "fact_count": len(facts),
            "scalar_fact_count": scalar_fact_count,
            "rowset_fact_count": rowset_fact_count,
            "fact_family_count": fact_family_count,
            "tag_count": tag_count,
            "facet_count": facet_count,
            "provider_type_counts": dict(sorted(provider_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "error_count": int(status_counts.get("error", 0)),
        },
        "facts": facts,
    }
    provider_findings = [
        _provider_finding(fact)
        for fact in facts
        if _provider_status(fact) == "error"
    ]
    source_findings = [
        finding for finding in provider_findings if finding.get("rule") == "missing_fact_source"
    ]
    audit = {
        "kind": "derived_fact_audit",
        "schema_version": "derived_fact_audit_v2",
        "generated_at": generated_at,
        "summary": {
            "provider_error_count": len(provider_findings),
            "source_blocker_count": len(source_findings),
            "fact_count": len(facts),
            "fact_family_count": fact_family_count,
        },
        "provider_findings": provider_findings,
        "source_findings": source_findings,
    }
    navigation_cache = build_fact_navigation_cache(facts, summary=ledger["summary"], generated_at=generated_at)
    return {"ledger": ledger, "audit": audit, "navigation_cache": navigation_cache}


def write_fact_hologram(
    *,
    repo_root: Path = REPO_ROOT,
    registry_path: Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    payload = build_fact_hologram(repo_root=repo_root, registry_path=registry_path, timestamp=timestamp)
    out_dir = repo_root / FACT_HOLOGRAM_DIR.relative_to(REPO_ROOT)
    _write_json(out_dir / LEDGER_PATH.name, payload["ledger"])
    _write_json(out_dir / AUDIT_PATH.name, payload["audit"])
    _write_json(out_dir / NAVIGATION_CACHE_PATH.name, payload["navigation_cache"])
    return {
        "kind": "derived_fact_hologram_write_receipt",
        "ledger_path": _relpath(out_dir / LEDGER_PATH.name, repo_root=repo_root),
        "audit_path": _relpath(out_dir / AUDIT_PATH.name, repo_root=repo_root),
        "navigation_cache_path": _relpath(out_dir / NAVIGATION_CACHE_PATH.name, repo_root=repo_root),
        "summary": dict(payload["ledger"].get("summary") or {}),
    }


def _strip_generated_at(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _strip_generated_at(item)
            for key, item in value.items()
            if str(key) != "generated_at"
        }
    if isinstance(value, list):
        return [_strip_generated_at(item) for item in value]
    return value


def _normalize_freshness_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        out = {
            key: _normalize_freshness_payload(item)
            for key, item in value.items()
            if str(key) not in {"generated_at", "source_fingerprint"}
        }
        if str(out.get("id") or "") in VOLATILE_FRESHNESS_FACT_IDS:
            for key in ("value", "value_repr", "search_text"):
                if key in out:
                    out[key] = _VOLATILE_FRESHNESS_VALUE
            if isinstance(out.get("tags"), list):
                out["tags"] = [_VOLATILE_FRESHNESS_VALUE]
        if "source_fingerprint" in value:
            out["source_fingerprint"] = _stable_digest(out)
        return out
    if isinstance(value, list):
        return [_normalize_freshness_payload(item) for item in value]
    return value


def check_fact_hologram_outputs(
    payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for key, rel_path in FACT_OUTPUT_PATHS.items():
        expected = payload.get(key)
        path = repo_root / rel_path.relative_to(REPO_ROOT)
        rel = _relpath(path, repo_root=repo_root)
        if expected is None:
            findings.append(
                {
                    "severity": "error",
                    "rule": "missing_expected_generated_output",
                    "output": key,
                    "path": rel,
                    "message": f"Fresh build did not produce expected output {key}.",
                }
            )
            continue
        actual = _safe_read_json(path)
        if actual is None:
            findings.append(
                {
                    "severity": "error",
                    "rule": "missing_generated_output",
                    "output": key,
                    "path": rel,
                    "message": f"Generated fact output is missing or invalid JSON: {rel}",
                }
            )
            continue
        if _normalize_freshness_payload(actual) != _normalize_freshness_payload(expected):
            findings.append(
                {
                    "severity": "error",
                    "rule": "stale_generated_output",
                    "output": key,
                    "path": rel,
                    "message": (
                        "Generated fact output differs from a fresh build after ignoring "
                        "timestamp-only generated_at drift."
                    ),
                }
            )
    return findings


def load_fact_ledger(*, repo_root: Path = REPO_ROOT, build_if_missing: bool = True) -> dict[str, Any]:
    path = repo_root / LEDGER_PATH.relative_to(REPO_ROOT)
    payload = _safe_read_json(path)
    if isinstance(payload, Mapping):
        return dict(payload)
    if build_if_missing:
        return build_fact_hologram(repo_root=repo_root)["ledger"]
    return {"facts": [], "summary": {"fact_count": 0, "error_count": 0}}


def load_fact_navigation_cache(*, repo_root: Path = REPO_ROOT, build_if_missing: bool = True) -> dict[str, Any]:
    path = repo_root / NAVIGATION_CACHE_PATH.relative_to(REPO_ROOT)
    payload = _safe_read_json(path)
    if isinstance(payload, Mapping):
        return dict(payload)
    if build_if_missing:
        return build_fact_hologram(repo_root=repo_root)["navigation_cache"]
    return {
        "kind": "derived_fact_navigation_cache",
        "schema_version": "derived_fact_navigation_cache_v2",
        "summary": {"fact_count": 0, "error_count": 0},
    }


def fact_by_id(ledger: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id") or "").strip(): dict(item)
        for item in (ledger.get("facts") or [])
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    }


def search_facts(query: str | None, *, ledger: Mapping[str, Any], limit: int | None = 25) -> list[dict[str, Any]]:
    rows = [dict(item) for item in (ledger.get("facts") or []) if isinstance(item, Mapping)]
    raw = str(query or "").strip().lower()
    if not raw:
        return rows if limit is None else rows[:limit]
    tokens = [token for token in re.split(r"[^a-z0-9_.]+", raw) if token]
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        haystack = " ".join(
            str(part)
            for part in [
                row.get("id"),
                row.get("title"),
                row.get("family_id"),
                row.get("provider_type"),
                row.get("source_path"),
                row.get("pointer"),
                row.get("subject_kind"),
                row.get("subject_ref"),
                row.get("facet"),
                row.get("value_repr"),
                row.get("owner_surface"),
                " ".join(row.get("tags") or []),
            ]
            if part
        ).lower()
        score = 0
        for token in tokens:
            if token == str(row.get("id") or "").lower():
                score += 100
            elif token in haystack:
                score += 20
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("id") or "")))
    result = [row for _score, row in scored]
    return result if limit is None else result[:limit]


def _filter_expr_parts(expr: str) -> tuple[str, str] | None:
    raw = str(expr or "").strip()
    if ":" not in raw:
        return None
    key, value = raw.split(":", 1)
    key = key.strip().lower().replace("-", "_")
    value = value.strip()
    if not key or not value:
        return None
    return key, value


def _matches_fact_filter(row: Mapping[str, Any], key: str, value: str) -> bool:
    if key == "tag":
        return value in {str(tag) for tag in (row.get("tags") or [])}
    if key == "facet":
        return str(row.get("facet") or "") == value
    if key == "value":
        return str(row.get("value") if row.get("value") is not None else "") == value
    if key in {"subject_kind", "kind"}:
        return str(row.get("subject_kind") or "") == value
    if key in {"subject_ref", "subject"}:
        return str(row.get("subject_ref") or "") == value
    if key in {"family", "family_id", "fact_family"}:
        return str(row.get("family_id") or "") == value
    if key == "provider_type":
        return str(row.get("provider_type") or "") == value
    if key in {"provider_status", "status"}:
        return _provider_status(row) == value
    if key == "source_path":
        return str(row.get("source_path") or "") == value
    if key == "mechanism_ref":
        for ref in row.get("mechanism_refs") or []:
            ref_id = str(ref.get("ref") or "").strip() if isinstance(ref, Mapping) else str(ref or "").strip()
            if ref_id == value:
                return True
        return False
    return False


def filter_facts(
    *,
    ledger: Mapping[str, Any],
    query: str | None = None,
    tag: str | None = None,
    facet: str | None = None,
    value: str | None = None,
    filters: Sequence[str] | None = None,
    limit: int | None = 40,
) -> list[dict[str, Any]]:
    rows = [dict(item) for item in (ledger.get("facts") or []) if isinstance(item, Mapping)]
    filter_exprs = []
    if tag:
        filter_exprs.append(("tag", str(tag).strip()))
    if facet:
        filter_exprs.append(("facet", str(facet).strip()))
    if value:
        filter_exprs.append(("value", str(value).strip()))
    for expr in filters or []:
        parts = _filter_expr_parts(str(expr))
        if parts is not None:
            filter_exprs.append(parts)
    for key, filter_value in filter_exprs:
        rows = [row for row in rows if _matches_fact_filter(row, key, filter_value)]
    if query:
        rows = search_facts(query, ledger={"facts": rows}, limit=limit)
    return rows if limit is None else rows[:limit]


def _table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip().strip("`").strip() for cell in stripped.strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def extract_fact_assertions(
    markdown: str,
    *,
    module_slug: str | None = None,
    module_file: str | None = None,
) -> list[FactAssertion]:
    assertions: list[FactAssertion] = []
    current_section: str | None = None
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("## "):
            current_section = line[3:].strip()
            index += 1
            continue
        cells = [cell.lower() for cell in _table_cells(line)]
        if cells and all(column in cells for column in FACT_TABLE_COLUMNS):
            column_index = {cell: cells.index(cell) for cell in FACT_TABLE_COLUMNS}
            row_index = index + 1
            if row_index < len(lines) and _is_separator_row(_table_cells(lines[row_index])):
                row_index += 1
            while row_index < len(lines):
                row_cells = _table_cells(lines[row_index])
                if not row_cells:
                    break
                fact_id = row_cells[column_index["fact id"]] if column_index["fact id"] < len(row_cells) else ""
                if not fact_id:
                    row_index += 1
                    continue
                assertions.append(
                    FactAssertion(
                        fact_id=fact_id,
                        expected=row_cells[column_index["expected"]] if column_index["expected"] < len(row_cells) else "",
                        mode=(row_cells[column_index["mode"]] if column_index["mode"] < len(row_cells) else "current").lower(),
                        as_of=row_cells[column_index["as of"]] if column_index["as of"] < len(row_cells) else "",
                        tolerance=row_cells[column_index["tolerance"]] if column_index["tolerance"] < len(row_cells) else "",
                        why=row_cells[column_index["why"]] if column_index["why"] < len(row_cells) else "",
                        section=current_section,
                        module_slug=module_slug,
                        module_file=module_file,
                    )
                )
                row_index += 1
            index = row_index
            continue
        index += 1
    return assertions


def _parse_expected(raw: str, actual: Any) -> Any:
    value = str(raw or "").strip().strip("`").strip()
    if value.lower() in LIVE_EXPECTED_TOKENS:
        return actual
    if isinstance(actual, bool):
        return value.lower() in {"true", "yes", "1", "on"}
    if isinstance(actual, int) and not isinstance(actual, bool):
        return int(value)
    if isinstance(actual, float):
        return float(value)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _parse_tolerance(raw: str) -> float:
    token = str(raw or "").strip().strip("`")
    if not token or token in {"-", "none", "n/a"}:
        return 0.0
    return float(token)


def _matches_expected(expected: Any, actual: Any, tolerance: float) -> bool:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)) and not isinstance(actual, bool):
        return abs(float(expected) - float(actual)) <= tolerance
    return str(expected) == str(actual)


def audit_fact_assertions(
    assertions: list[FactAssertion],
    *,
    ledger: Mapping[str, Any],
    strict: bool = False,
) -> dict[str, Any]:
    facts = fact_by_id(ledger)
    findings: list[dict[str, Any]] = []
    assertion_rows: list[dict[str, Any]] = []
    for assertion in assertions:
        row = assertion.as_dict()
        mode = str(assertion.mode or "current").lower()
        fact = facts.get(assertion.fact_id)
        if fact is None:
            finding = {
                "severity": "warning",
                "rule": "unknown_fact_id",
                "fact_id": assertion.fact_id,
                "message": f"Fact assertion cites unknown fact id: {assertion.fact_id}.",
                "assertion": row,
            }
            findings.append(finding)
            row["status"] = "unknown_fact_id"
            assertion_rows.append(row)
            continue
        row["actual"] = fact.get("value")
        row["actual_repr"] = fact.get("value_repr")
        row["provider_status"] = fact.get("status")
        if fact.get("status") == "error":
            findings.append(
                {
                    "severity": "warning",
                    "rule": "fact_provider_error",
                    "fact_id": assertion.fact_id,
                    "message": f"Fact provider failed for {assertion.fact_id}: {fact.get('error')}",
                    "assertion": row,
                }
            )
            row["status"] = "provider_error"
            assertion_rows.append(row)
            continue
        if mode in HISTORICAL_ASSERTION_MODES:
            row["status"] = "historical_skip"
            assertion_rows.append(row)
            continue
        try:
            expected = _parse_expected(assertion.expected, fact.get("value"))
            tolerance = _parse_tolerance(assertion.tolerance)
        except (TypeError, ValueError) as exc:
            findings.append(
                {
                    "severity": "warning",
                    "rule": "fact_assertion_parse_error",
                    "fact_id": assertion.fact_id,
                    "message": f"Could not parse expected/tolerance for {assertion.fact_id}: {exc}",
                    "assertion": row,
                }
            )
            row["status"] = "parse_error"
            assertion_rows.append(row)
            continue
        row["expected_normalized"] = expected
        row["tolerance_normalized"] = tolerance
        if str(assertion.expected or "").strip().strip("`").strip().lower() in LIVE_EXPECTED_TOKENS:
            row["expected_source"] = "live_provider"
        if not _matches_expected(expected, fact.get("value"), tolerance):
            severity = "error" if strict and mode != "advisory" else "warning"
            findings.append(
                {
                    "severity": severity,
                    "rule": "fact_assertion_mismatch",
                    "fact_id": assertion.fact_id,
                    "message": (
                        f"Fact assertion mismatch for {assertion.fact_id}: "
                        f"expected={assertion.expected!r}, actual={fact.get('value_repr')!r}."
                    ),
                    "assertion": row,
                }
            )
            row["status"] = "mismatch"
        else:
            row["status"] = "match"
        assertion_rows.append(row)
    status_counts = Counter(str(row.get("status") or "unknown") for row in assertion_rows)
    return {
        "assertions": assertion_rows,
        "findings": findings,
        "summary": {
            "assertion_count": len(assertion_rows),
            "finding_count": len(findings),
            "status_counts": dict(sorted(status_counts.items())),
        },
    }


def _section_bodies(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in markdown.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections.setdefault(current, []).append(line)
    return {heading: "\n".join(lines) for heading, lines in sections.items()}


def find_unbound_numeric_claims(markdown: str, assertions: list[FactAssertion]) -> list[dict[str, Any]]:
    asserted_sections = {assertion.section for assertion in assertions if assertion.section}
    results: list[dict[str, Any]] = []
    for heading, body in _section_bodies(markdown).items():
        if heading not in {"Current state", "Refresh contract"}:
            continue
        cleaned = CODE_FENCE_RE.sub(" ", body)
        cleaned = INLINE_CODE_RE.sub(" ", cleaned)
        for match in VOLATILE_NUMERIC_RE.finditer(cleaned):
            if heading in asserted_sections:
                continue
            snippet = cleaned[max(0, match.start() - 70): match.end() + 70]
            results.append(
                {
                    "section": heading,
                    "number": match.group(1),
                    "noun": match.group(2),
                    "snippet": " ".join(snippet.split()),
                    "message": (
                        f"Volatile numeric claim in {heading} lacks a fact assertion table: "
                        f"{match.group(0)!r}."
                    ),
                }
            )
            if len(results) >= 5:
                return results
    return results


def audit_markdown_fact_claims(
    markdown: str,
    *,
    ledger: Mapping[str, Any],
    module_slug: str | None = None,
    module_file: str | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    assertions = extract_fact_assertions(markdown, module_slug=module_slug, module_file=module_file)
    audit = audit_fact_assertions(assertions, ledger=ledger, strict=strict)
    unbound = find_unbound_numeric_claims(markdown, assertions)
    findings = list(audit["findings"])
    for item in unbound:
        findings.append(
            {
                "severity": "warning",
                "rule": "unbound_numeric_claim",
                "message": item["message"],
                "section": item["section"],
                "snippet": item["snippet"],
            }
        )
    status_counts = Counter(str(row.get("status") or "unknown") for row in audit["assertions"])
    return {
        "assertions": audit["assertions"],
        "findings": findings,
        "unbound_numeric_claims": unbound,
        "summary": {
            "assertion_count": len(audit["assertions"]),
            "finding_count": len(findings),
            "unbound_numeric_claim_count": len(unbound),
            "status_counts": dict(sorted(status_counts.items())),
        },
    }
