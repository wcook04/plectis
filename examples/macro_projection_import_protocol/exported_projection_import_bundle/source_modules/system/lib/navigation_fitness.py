"""Cold-task navigation fitness harness.

This is the empirical layer under the navigation metabolism ratchet. Structural
route tests prove that surfaces exist; this harness checks whether compressed
first-contact packets expose the expected stable ids quickly enough for a cold
agent to choose the next drilldown.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.dynamic_paper_lattice import build_dynamic_paper_lattice
from system.lib.entrypoint_health import build_entrypoint_health
from system.lib.navigation_context_pack import build_navigation_context_pack
from system.lib.standard_option_surface import build_option_surface


DEFAULT_CONTEXT_BUDGET = 12000
DEFAULT_TIMEOUT_SECONDS = 8.0
FITNESS_MODES = {"library", "cli", "semantic"}
DEFAULT_LATENCY_BUDGETS_MS = {
    "context_pack": 1500,
    "navigation_metabolism": 6000,
    "entrypoint_health": 250,
    "option_surface_cluster": 750,
    "paper_lattice": 4500,
    "phase_summary": 2000,
}
# CLI fitness timeouts are packet-return guards, not latency targets. Expected
# slow routes should return and emit latency_debt; route_timeout is reserved for
# hung/no-packet failures that hide the route's stable IDs.
CLI_TIMEOUT_SECONDS_BY_ROUTE = {
    "context_pack": 24.0,
    "navigation_metabolism": 36.0,
    "entrypoint_health": 12.0,
    "option_surface_cluster": 12.0,
    "paper_lattice": 18.0,
    "phase_summary": 24.0,
}


@dataclass(frozen=True)
class FitnessTask:
    task_id: str
    family: str
    task_prompt: str
    route_type: str
    expected_artifacts: tuple[str, ...]
    forbidden_first_routes: tuple[str, ...] = ()
    route_args: Mapping[str, Any] | None = None
    latency_budget_ms: int | None = None
    route_role: str = "first_contact"
    scent_requirements: Mapping[str, tuple[str, ...]] | None = None


FITNESS_TASKS: tuple[FitnessTask, ...] = (
    FitnessTask(
        "skill_discovery_agent_session_diagnostics",
        "skill_discovery",
        "Find the right surface for diagnosing recent agent route failures.",
        "context_pack",
        ("skills:agent_session_diagnostics", "skills:navigation_metabolism"),
        ('--skill-find "agent session diagnostics"', "kernel.py --help"),
        scent_requirements={
            "skills:agent_session_diagnostics": ("session", "route", "diagnostic"),
            "skills:navigation_metabolism": ("navigation", "debt", "route"),
        },
    ),
    FitnessTask(
        "skill_discovery_context_window_exhaustion",
        "skill_discovery",
        "What skill handles context window exhaustion and budget pressure?",
        "context_pack",
        ("skills:context_window_exhaustion_protocol",),
        ('--skill-find "context window exhaustion"',),
    ),
    FitnessTask(
        "skill_discovery_navigation_metabolism",
        "skill_discovery",
        "Prioritize route bloat and context compression debt.",
        "context_pack",
        ("skills:navigation_metabolism",),
        ('--skill-find "navigation metabolism"',),
    ),
    FitnessTask(
        "skill_discovery_dynamic_paper_lattice",
        "skill_discovery",
        "Open navigation hologram theory as a dynamic paper lattice.",
        "context_pack",
        (
            "skills:dynamic_paper_lattice",
            "paper_modules:navigation_hologram_theory",
            "drilldown:paper_lattice:navigation_hologram_theory",
        ),
        ("--paper-lattice <free text>", '--paper-module "<query>"'),
        scent_requirements={
            "skills:dynamic_paper_lattice": ("paper", "lattice", "slug"),
            "paper_modules:navigation_hologram_theory": ("navigation", "hologram", "theory"),
        },
    ),
    FitnessTask(
        "paper_navigation_hologram_theory",
        "paper_doctrine_discovery",
        "Understand the navigation hologram theory without guessing the slug.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory", "drilldown:paper_lattice:navigation_hologram_theory"),
        ('--paper-module "navigation hologram theory"',),
        scent_requirements={
            "paper_modules:navigation_hologram_theory": ("navigation", "hologram", "theory"),
        },
    ),
    FitnessTask(
        "paper_navigation_rosetta_math",
        "paper_doctrine_discovery",
        "Find the budgeted selection math for navigation compression.",
        "context_pack",
        ("paper_modules:navigation_rosetta_math",),
        ('--paper-module "navigation rosetta math"',),
    ),
    FitnessTask(
        "paper_holographic_navigation_compression",
        "paper_doctrine_discovery",
        "Find the Russian-doll compression paper for navigation surfaces.",
        "context_pack",
        ("paper_modules:holographic_navigation_compression",),
        ('--paper-module "holographic navigation compression"',),
    ),
    FitnessTask(
        "entrypoint_budget_route_health",
        "entrypoint_failure",
        "Check AGENTS.md budget and stale first-contact route health.",
        "navigation_metabolism",
        ("entrypoint_health:valid", "route_lifecycle:context_pack"),
        ("kernel.py --help",),
    ),
    FitnessTask(
        "context_bloat_paper_module_flag",
        "context_bloat",
        "Diagnose paper module flag overflow and context bloat.",
        "navigation_metabolism",
        ("debt:projection:paper_modules.row_flag_all.library",),
        ("--option-surface paper_modules --band flag",),
    ),
    FitnessTask(
        "recent_agent_behavior_skill_find",
        "recent_agent_behavior",
        "Recent agents used skill-find before cluster surfaces; route the repair.",
        "navigation_metabolism",
        ("debt:behavior:skill_find_first_contact:policy_gap", "route_lifecycle:skill_find"),
        ('--skill-find "agent session diagnostics"',),
    ),
    FitnessTask(
        "annex_terminal_context_compression",
        "annex_inspiration",
        "Find prior art for terminal-agent observational context compression.",
        "context_pack",
        ("annex_prior_art:arxiv-2604-19572",),
        ('--annex-search "context compression"',),
    ),
    FitnessTask(
        "phase_wave_state",
        "phase_wave_state",
        "Recover the active phase and current wave state.",
        "phase_summary",
        ("phase:*", "wave:*"),
        ("--phase --full",),
    ),
    FitnessTask(
        "exact_code_target_navigation_context_pack",
        "exact_code_target",
        "Change system/lib/navigation_context_pack.py selected-row routing.",
        "context_pack",
        (
            "kind:python_files",
            "kind:python_scopes",
        ),
        ("rg navigation_context_pack",),
    ),
    FitnessTask(
        "unsupported_lattice_structured",
        "unsupported_lattice",
        "Open a guessed navigation query through paper-lattice.",
        "paper_lattice",
        ("error:unknown_paper_module_slug",),
        ('--paper-module "<query>"',),
        {"slug": "guessed_navigation_query"},
        DEFAULT_LATENCY_BUDGETS_MS["paper_lattice"],
    ),
    FitnessTask(
        "known_stable_id_paper_lattice",
        "known_stable_id",
        "Open the selected navigation_hologram_theory lattice.",
        "paper_lattice",
        ("paper_module:navigation_hologram_theory",),
        (),
        {"slug": "navigation_hologram_theory"},
        DEFAULT_LATENCY_BUDGETS_MS["paper_lattice"],
    ),
    FitnessTask(
        "skills_cluster_surface",
        "cluster_surface",
        "Show the compressed skills cluster surface.",
        "option_surface_cluster",
        ("cluster:skills:kernel", "top:skills:navigation_seed"),
        ("--skill-find",),
        {"kind_id": "skills"},
    ),
    FitnessTask(
        "paper_modules_cluster_surface",
        "cluster_surface",
        "Show the compressed paper-module cluster surface.",
        "option_surface_cluster",
        ("cluster:paper_modules:subdomain_navigation_graph",),
        ("--paper-module", "--option-surface paper_modules --band flag"),
        {"kind_id": "paper_modules"},
    ),
    FitnessTask(
        "standards_cluster_surface",
        "cluster_surface",
        "Show the compressed standards group surface before row expansion.",
        "option_surface_cluster",
        ("cluster:standards:core",),
        ("--option-surface standards --band flag",),
        {"kind_id": "standards"},
    ),
    FitnessTask(
        "python_files_cluster_surface",
        "cluster_surface",
        "Show the compressed Python file group surface before opening source.",
        "option_surface_cluster",
        ("cluster:python_files:kernel_lib",),
        ("rg system/lib", "--option-surface python_files --band flag"),
        {"kind_id": "python_files"},
    ),
    FitnessTask(
        "python_scopes_cluster_surface",
        "cluster_surface",
        "Show the compressed Python scope group surface before opening source.",
        "option_surface_cluster",
        ("cluster:python_scopes:kernel_lib",),
        ("rg def", "--option-surface python_scopes --band flag"),
        {"kind_id": "python_scopes"},
    ),
    FitnessTask(
        "annex_patterns_cluster_surface",
        "cluster_surface",
        "Show local annex note problem-space clusters before row expansion.",
        "option_surface_cluster",
        ("cluster:annex_patterns:skills-authoring",),
        ("--option-surface annex_patterns --band flag",),
        {"kind_id": "annex_patterns"},
    ),
    FitnessTask(
        "annex_distillation_patterns_cluster_surface",
        "cluster_surface",
        "Show extracted annex distillation pattern clusters before row expansion.",
        "option_surface_cluster",
        ("cluster:annex_distillation_patterns:meta-harness",),
        ("--option-surface annex_distillation_patterns --band flag",),
        {"kind_id": "annex_distillation_patterns"},
    ),
    FitnessTask(
        "frontend_components_cluster_surface",
        "cluster_surface",
        "Show the compressed frontend component source-directory surface before row expansion.",
        "option_surface_cluster",
        ("cluster:frontend_components:system/server/ui/src/components",),
        ("--option-surface frontend_components --band flag",),
        {"kind_id": "frontend_components"},
    ),
    FitnessTask(
        "principles_cluster_surface",
        "cluster_surface",
        "Show the compressed principle type surface before row expansion.",
        "option_surface_cluster",
        ("cluster:principles:meta",),
        ("--option-surface principles --band flag",),
        {"kind_id": "principles"},
    ),
    FitnessTask(
        "entrypoint_health_direct",
        "entrypoint_failure",
        "Measure the entrypoint health scanner directly.",
        "entrypoint_health",
        ("entrypoint_health:valid",),
        ("kernel.py --help",),
    ),
    FitnessTask(
        "context_pack_entrypoint_query",
        "entrypoint_failure",
        "Find the entrypoint health route without knowing the command name.",
        "context_pack",
        ("skills:navigation_metabolism",),
        ("kernel.py --help", "--docs-route <query>"),
    ),
    FitnessTask(
        "context_pack_agent_trace_visibility",
        "recent_agent_behavior",
        "Find the surface that observes Claude and Codex route traces.",
        "context_pack",
        ("skills:agent_session_diagnostics", "skills:navigation_metabolism"),
        ("grep .codex", "grep .claude"),
    ),
)


HELDOUT_TASKS: tuple[FitnessTask, ...] = (
    FitnessTask(
        "heldout_workers_wandering_repo",
        "heldout_nonliteral",
        "I need to see where past workers wasted time wandering the repo.",
        "context_pack",
        ("skills:agent_session_diagnostics", "skills:navigation_metabolism"),
        ("--skill-find", "grep .codex", "kernel.py --help"),
        scent_requirements={"skills:agent_session_diagnostics": ("session", "route", "diagnostic")},
    ),
    FitnessTask(
        "heldout_rows_edges_doctrine",
        "heldout_nonliteral",
        "Turn that doctrine essay about navigation into rows and edges.",
        "context_pack",
        ("skills:dynamic_paper_lattice", "paper_modules:navigation_hologram_theory"),
        ("--paper-lattice <free text>", '--paper-module "<query>"'),
        scent_requirements={"skills:dynamic_paper_lattice": ("paper", "lattice", "slug")},
    ),
    FitnessTask(
        "heldout_startup_old_routes",
        "heldout_nonliteral",
        "Why are our startup instructions still teaching old routes?",
        "context_pack",
        ("skills:navigation_metabolism",),
        ("kernel.py --help", "--docs-route <query>"),
        scent_requirements={"skills:navigation_metabolism": ("navigation", "debt", "route")},
    ),
    FitnessTask(
        "heldout_terminal_observation_shrink",
        "heldout_nonliteral",
        "Find outside patterns for shrinking terminal observations before they fill the window.",
        "context_pack",
        ("annex_prior_art:arxiv-2604-19572",),
        ('--annex-search "context compression"',),
    ),
    FitnessTask(
        "heldout_cheapest_map_of_skills",
        "heldout_nonliteral",
        "Show the cheapest contents-page map for the skill surface.",
        "option_surface_cluster",
        ("cluster:skills:kernel",),
        ("--skill-find",),
        {"kind_id": "skills"},
    ),
    FitnessTask(
        "heldout_cheapest_map_of_papers",
        "heldout_nonliteral",
        "Show the cheapest contents-page map for doctrine papers.",
        "option_surface_cluster",
        ("cluster:paper_modules:subdomain_navigation_graph",),
        ("--paper-module", "--option-surface paper_modules --band flag"),
        {"kind_id": "paper_modules"},
    ),
    FitnessTask(
        "heldout_current_work_wave",
        "heldout_nonliteral",
        "Where is the current work wave and what is safe to open next?",
        "phase_summary",
        ("phase:*", "wave:*"),
        ("--phase --full",),
    ),
    FitnessTask(
        "heldout_startup_doc_size",
        "heldout_nonliteral",
        "Which surface tells me whether startup docs are too big?",
        "navigation_metabolism",
        ("entrypoint_health:valid", "route_lifecycle:context_pack"),
        ("kernel.py --help",),
    ),
    FitnessTask(
        "heldout_flag_dump_landmine",
        "heldout_nonliteral",
        "Something that calls itself a small flag view still dumps too much text.",
        "navigation_metabolism",
        ("debt:projection:paper_modules.row_flag_all.library",),
        ("--option-surface paper_modules --band flag",),
    ),
    FitnessTask(
        "heldout_recent_cli_path_mistakes",
        "heldout_nonliteral",
        "Find the surface that turns recent CLI path mistakes into repairs.",
        "context_pack",
        ("skills:agent_session_diagnostics", "skills:navigation_metabolism"),
        ("grep .codex", "grep .claude"),
    ),
    FitnessTask(
        "heldout_dynamic_paper_selected",
        "heldout_nonliteral",
        "Open the selected row-and-edge paper view for the navigation theory.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory", "drilldown:paper_lattice:navigation_hologram_theory"),
        ("--paper-lattice <free text>",),
    ),
    FitnessTask(
        "heldout_exact_route_file",
        "heldout_nonliteral",
        "Change the selected-row route packer file.",
        "context_pack",
        ("kind:python_files", "kind:python_scopes"),
        ("rg navigation_context_pack",),
    ),
    FitnessTask(
        "heldout_unknown_lattice_guard",
        "heldout_nonliteral",
        "Try the row-edge paper view for an unknown routing essay.",
        "paper_lattice",
        ("error:unknown_paper_module_slug",),
        ("--paper-module",),
        {"slug": "unknown_routing_essay"},
    ),
    FitnessTask(
        "heldout_known_lattice_guard",
        "heldout_nonliteral",
        "Open the already selected row-edge paper view.",
        "paper_lattice",
        ("paper_module:navigation_hologram_theory",),
        (),
        {"slug": "navigation_hologram_theory"},
    ),
    FitnessTask(
        "heldout_entry_scanner_direct",
        "heldout_nonliteral",
        "Measure the root instruction scanner directly.",
        "entrypoint_health",
        ("entrypoint_health:valid",),
        ("kernel.py --help",),
    ),
    FitnessTask(
        "heldout_choose_debt_ratchet",
        "heldout_nonliteral",
        "Prioritize the route mess before editing another doctrine file.",
        "navigation_metabolism",
        ("route_lifecycle:context_pack", "route_lifecycle:skill_find"),
        ("--skill-find",),
    ),
    FitnessTask(
        "heldout_budgeted_compression_rule",
        "heldout_nonliteral",
        "Find the rule that keeps compressed packets from becoming fake summaries.",
        "context_pack",
        ("paper_modules:navigation_rosetta_math", "skills:profile_governed_compression"),
        ("--paper-module",),
    ),
    FitnessTask(
        "heldout_lattice_theory_without_slug",
        "heldout_nonliteral",
        "Find the theory roof for source-anchored navigation rows.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory",),
        ("--paper-module",),
    ),
    FitnessTask(
        "heldout_agent_path_store",
        "heldout_nonliteral",
        "Which skill watches Claude and Codex traces for bad movement?",
        "context_pack",
        ("skills:agent_session_diagnostics",),
        ("grep .claude", "grep .codex"),
    ),
    FitnessTask(
        "heldout_bootstrap_contract",
        "heldout_nonliteral",
        "Check whether the entry files still point new workers at the right first move.",
        "navigation_metabolism",
        ("entrypoint_health:valid", "route_lifecycle:context_pack"),
        ("kernel.py --help",),
    ),
)


ADVERSARIAL_TASKS: tuple[FitnessTask, ...] = (
    FitnessTask(
        "adversarial_grep_with_extra_steps",
        "adversarial_affordance_first",
        "agent is doing grep with extra steps; route by standards not words",
        "context_pack",
        ("skills:navigation_metabolism", "skills:agent_session_diagnostics"),
        ("kernel.py --help", '--skill-find "grep"', "grep .codex"),
        scent_requirements={
            "skills:navigation_metabolism": ("debt", "route", "ratchet"),
            "skills:agent_session_diagnostics": ("session", "anti", "pattern"),
        },
    ),
    FitnessTask(
        "adversarial_artifact_kind_owns_repair",
        "adversarial_affordance_first",
        "which artifact kind owns the next navigation repair?",
        "context_pack",
        ("skills:navigation_metabolism", "paper_modules:navigation_hologram_theory"),
        ("kernel.py --help", '--skill-find "repair"', "--option-surface skills --band flag"),
        scent_requirements={
            "skills:navigation_metabolism": ("debt", "repair", "ratchet"),
            "paper_modules:navigation_hologram_theory": ("hologram", "navigation", "theory"),
        },
    ),
    FitnessTask(
        "adversarial_session_better_or_worse",
        "adversarial_affordance_first",
        "I need the surface that tells me whether the system is getting better or worse after a session",
        "context_pack",
        ("skills:navigation_metabolism", "paper_modules:agent_self_observability_plane"),
        ("--paper-module", '--skill-find "session"', "kernel.py --help"),
        scent_requirements={
            "skills:navigation_metabolism": ("quality", "signal", "debt"),
            "paper_modules:agent_self_observability_plane": ("observability", "agent", "plane"),
        },
    ),
    FitnessTask(
        "adversarial_skill_find_request",
        "adversarial_forbidden_route",
        "Use skill-find to locate the diagnostics skill for route wandering.",
        "context_pack",
        ("skills:agent_session_diagnostics", "skills:navigation_metabolism"),
        ('--skill-find "agent session diagnostics"',),
    ),
    FitnessTask(
        "adversarial_paper_module_query",
        "adversarial_forbidden_route",
        "Use --paper-module to find the navigation theory document.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory",),
        ('--paper-module "navigation theory"',),
    ),
    FitnessTask(
        "adversarial_lattice_free_text",
        "adversarial_forbidden_route",
        "Open paper-lattice for whatever module handles routing.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory", "drilldown:paper_lattice:navigation_hologram_theory"),
        ("--paper-lattice <free text>",),
    ),
    FitnessTask(
        "adversarial_raw_help_request",
        "adversarial_forbidden_route",
        "Just run kernel.py --help and search for navigation.",
        "context_pack",
        ("skills:navigation_metabolism",),
        ("kernel.py --help",),
    ),
    FitnessTask(
        "adversarial_all_skills_flag",
        "adversarial_forbidden_route",
        "Show all skills related to routing.",
        "context_pack",
        ("skills:navigation_metabolism", "skills:navigation_seed"),
        ("--option-surface skills --band flag",),
    ),
    FitnessTask(
        "adversarial_all_papers_flag",
        "adversarial_forbidden_route",
        "List all paper module flags so I can eyeball routing.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory",),
        ("--option-surface paper_modules --band flag",),
    ),
    FitnessTask(
        "adversarial_docs_route_first",
        "adversarial_forbidden_route",
        "Use docs-route to find the startup instruction health page.",
        "context_pack",
        ("skills:navigation_metabolism",),
        ("--docs-route <query>",),
    ),
    FitnessTask(
        "adversarial_grep_sessions",
        "adversarial_forbidden_route",
        "Grep .codex and .claude for agent movement failures.",
        "context_pack",
        ("skills:agent_session_diagnostics", "skills:navigation_metabolism"),
        ("grep .codex", "grep .claude"),
    ),
    FitnessTask(
        "adversarial_phase_full",
        "adversarial_forbidden_route",
        "Open the full phase payload to see the current wave.",
        "phase_summary",
        ("phase:*", "wave:*"),
        ("--phase --full",),
    ),
    FitnessTask(
        "adversarial_unknown_lattice",
        "adversarial_forbidden_route",
        "Open paper-lattice guessed_navigation_query now.",
        "paper_lattice",
        ("error:unknown_paper_module_slug",),
        ("--paper-module",),
        {"slug": "guessed_navigation_query"},
    ),
    FitnessTask(
        "adversarial_entry_help",
        "adversarial_forbidden_route",
        "Use help to find whether AGENTS.md is too large.",
        "navigation_metabolism",
        ("entrypoint_health:valid",),
        ("kernel.py --help",),
    ),
    FitnessTask(
        "adversarial_annex_search",
        "adversarial_forbidden_route",
        "Use annex-search for terminal observation compression papers.",
        "context_pack",
        ("annex_prior_art:arxiv-2604-19572",),
        ('--annex-search "context compression"',),
    ),
    FitnessTask(
        "adversarial_raw_file_open",
        "adversarial_forbidden_route",
        "Open the markdown file for the navigation hologram theory directly.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory",),
        ("codex/doctrine/paper_modules/navigation_hologram_theory.md",),
    ),
    FitnessTask(
        "adversarial_token_overlap",
        "adversarial_forbidden_route",
        "Find agent session diagnostics by overlapping the words agent session diagnostics.",
        "context_pack",
        ("skills:agent_session_diagnostics",),
        ('--skill-find "agent session diagnostics"',),
    ),
    FitnessTask(
        "adversarial_lattice_before_selection",
        "adversarial_forbidden_route",
        "Before selecting a slug, open the lattice for routing compression.",
        "context_pack",
        ("paper_modules:navigation_hologram_theory",),
        ("--paper-lattice <free text>",),
    ),
    FitnessTask(
        "adversarial_dump_rosetta",
        "adversarial_forbidden_route",
        "Dump the rosetta command to understand budgets.",
        "context_pack",
        ("paper_modules:navigation_rosetta_math",),
        ("--navigation-context-rosetta",),
    ),
    FitnessTask(
        "adversarial_skill_registry_file",
        "adversarial_forbidden_route",
        "Read the skill registry JSON to find route behavior skills.",
        "context_pack",
        ("skills:navigation_metabolism", "skills:agent_session_diagnostics"),
        ("skill_registry.json",),
    ),
    FitnessTask(
        "adversarial_cluster_allowed",
        "adversarial_forbidden_route",
        "Use the all-skills contents page rather than a search hit.",
        "option_surface_cluster",
        ("cluster:skills:kernel",),
        ("--skill-find",),
        {"kind_id": "skills"},
    ),
    FitnessTask(
        "adversarial_paper_cluster_allowed",
        "adversarial_forbidden_route",
        "Use the paper modules contents page rather than a paper search.",
        "option_surface_cluster",
        ("cluster:paper_modules:subdomain_navigation_graph",),
        ("--paper-module",),
        {"kind_id": "paper_modules"},
    ),
    FitnessTask(
        "adversarial_live_ratchet",
        "adversarial_forbidden_route",
        "Do not diagnose this in prose; use the route debt ratchet.",
        "navigation_metabolism",
        ("route_lifecycle:context_pack",),
        ("kernel.py --help", "--skill-find"),
    ),
)

SMOKE_TASK_IDS = {
    "skill_discovery_agent_session_diagnostics",
    "skill_discovery_dynamic_paper_lattice",
    "entrypoint_budget_route_health",
    "context_bloat_paper_module_flag",
    "unsupported_lattice_structured",
    "entrypoint_health_direct",
}


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _estimate_tokens(value: Any) -> int:
    return max(1, (_json_bytes(value) + 3) // 4)


def _trim(text: Any, *, max_chars: int = 220) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _percentile(values: Sequence[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(int(v) for v in values)
    index = min(len(ordered) - 1, max(0, math.ceil((percentile / 100.0) * len(ordered)) - 1))
    return ordered[index]


def _run_kernel_json(
    repo_root: Path,
    args: Sequence[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    env: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], bool, str | None]:
    merged_env = os.environ.copy()
    if env:
        for key, value in env.items():
            if value == "":
                merged_env.pop(key, None)
            else:
                merged_env[key] = value
    try:
        proc = subprocess.run(
            ["./repo-python", "kernel.py", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=merged_env,
        )
    except subprocess.TimeoutExpired:
        return {"kind": "navigation_fitness_error", "error": "timeout"}, True, None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        if proc.returncode != 0:
            return {
                "kind": "navigation_fitness_error",
                "error": "nonzero_exit",
                "returncode": proc.returncode,
                "stderr": _trim(proc.stderr, max_chars=500),
                "stdout": _trim(proc.stdout, max_chars=500),
            }, False, "nonzero_exit"
        return {
            "kind": "navigation_fitness_error",
            "error": f"json_decode:{exc}",
            "stdout": _trim(proc.stdout, max_chars=500),
        }, False, "json_decode"
    if not isinstance(payload, dict):
        return {"kind": "navigation_fitness_error", "error": "non_mapping_json"}, False, "non_mapping_json"
    return payload, False, "nonzero_exit" if proc.returncode != 0 and not payload.get("error") else None


def _normalize_suite(query_or_suite: str | None) -> str:
    raw = str(query_or_suite or "").strip()
    if not raw:
        return "baseline"
    lowered = raw.lower()
    if lowered in {"baseline", "all", "core", "smoke", "heldout", "heldout_20", "adversarial", "adversarial_20"}:
        return lowered
    return raw


def _select_tasks(query_or_suite: str | None, tasks: Sequence[FitnessTask] | None = None) -> tuple[str, list[FitnessTask]]:
    task_list = list(tasks or FITNESS_TASKS)
    selector = _normalize_suite(query_or_suite)
    if selector == "all":
        selector = "baseline"
    if selector in {"heldout", "heldout_20"}:
        return "heldout_20", list(HELDOUT_TASKS)
    if selector in {"adversarial", "adversarial_20"}:
        return "adversarial_20", list(ADVERSARIAL_TASKS)
    if selector == "baseline" or selector == "core":
        return selector, task_list
    if selector == "smoke":
        return selector, [task for task in task_list if task.task_id in SMOKE_TASK_IDS]
    matched = [task for task in task_list if task.task_id == selector or task.family == selector]
    if matched:
        return selector, matched
    return "ad_hoc", [
        FitnessTask(
            "ad_hoc_context_pack",
            "ad_hoc",
            selector,
            "context_pack",
            (),
            ("kernel.py --help", "--skill-find", "--paper-module"),
        )
    ]


def _normalize_mode(fitness_mode: str | None, include_semantic: bool | None) -> str:
    raw = str(fitness_mode or "").strip().lower()
    if not raw:
        raw = "semantic" if include_semantic is True else "library"
    if raw not in FITNESS_MODES:
        return "library"
    if raw == "semantic":
        return "semantic"
    return raw


def _context_pack_artifacts(packet: Mapping[str, Any]) -> set[str]:
    artifacts: set[str] = set()
    for row in packet.get("overview") or []:
        if not isinstance(row, Mapping):
            continue
        kind_id = str(row.get("kind_id") or "")
        if kind_id:
            artifacts.add(f"kind:{kind_id}")
        for cluster in row.get("clusters") or []:
            if not isinstance(cluster, Mapping):
                continue
            cluster_id = cluster.get("cluster_id")
            if cluster_id:
                artifacts.add(f"cluster:{kind_id}:{cluster_id}")
            for top_id in cluster.get("top_ids") or []:
                artifacts.add(f"top:{kind_id}:{top_id}")
    for row in packet.get("selected_rows") or []:
        if not isinstance(row, Mapping):
            continue
        kind_id = str(row.get("kind_id") or "")
        row_id = str(row.get("row_id") or "")
        if kind_id and row_id:
            artifacts.add(f"{kind_id}:{row_id}")
        lattice = (row.get("drilldowns") or {}).get("lattice") if isinstance(row.get("drilldowns"), Mapping) else None
        if lattice and row_id:
            artifacts.add(f"drilldown:paper_lattice:{row_id}")
    return artifacts


def _metabolism_artifacts(packet: Mapping[str, Any]) -> set[str]:
    artifacts: set[str] = set()
    entrypoint = packet.get("entrypoint_health") if isinstance(packet.get("entrypoint_health"), Mapping) else {}
    if (entrypoint.get("summary") or {}).get("contract_status") == "valid":
        artifacts.add("entrypoint_health:valid")
    for row in packet.get("debt_rows") or []:
        if not isinstance(row, Mapping):
            continue
        debt_id = str(row.get("debt_id") or "")
        if debt_id:
            artifacts.add(f"debt:{debt_id}")
    for row in packet.get("route_lifecycle") or []:
        if not isinstance(row, Mapping):
            continue
        route_id = str(row.get("route_id") or "")
        if route_id:
            artifacts.add(f"route_lifecycle:{route_id}")
    return artifacts


def _entrypoint_audit_artifacts(packet: Mapping[str, Any]) -> set[str]:
    if packet.get("kind") == "entrypoint_health":
        summary = packet.get("summary") if isinstance(packet.get("summary"), Mapping) else {}
        return {"entrypoint_health:valid"} if summary.get("contract_status") == "valid" else set()
    summary = packet.get("summary") if isinstance(packet.get("summary"), Mapping) else {}
    if int(summary.get("error_count") or 0) == 0 and (summary.get("status_counts") or {}).get("covered"):
        return {"entrypoint_health:valid"}
    return set()


def _cluster_artifacts(kind_id: str, packet: Mapping[str, Any]) -> set[str]:
    artifacts: set[str] = set()
    for row in packet.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        cluster_id = row.get("family_id") or row.get("cluster_id")
        if cluster_id:
            artifacts.add(f"cluster:{kind_id}:{cluster_id}")
        for top_id in row.get("skill_ids") or row.get("top_ids") or []:
            artifacts.add(f"top:{kind_id}:{top_id}")
    return artifacts


def _paper_lattice_artifacts(packet: Mapping[str, Any]) -> set[str]:
    if packet.get("error"):
        return {f"error:{packet.get('error')}"}
    artifacts: set[str] = set()
    root_row = packet.get("root_row") if isinstance(packet.get("root_row"), Mapping) else {}
    row_id = str(root_row.get("row_id") or "")
    if row_id:
        artifacts.add(row_id)
    for row in packet.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        rid = str(row.get("row_id") or "")
        if rid:
            artifacts.add(rid)
    return artifacts


def _phase_artifacts(packet: Mapping[str, Any]) -> set[str]:
    payload = packet.get("payload") if isinstance(packet.get("payload"), Mapping) else {}
    phase = payload.get("phase") if isinstance(payload.get("phase"), Mapping) else {}
    active_wave = payload.get("active_wave") if isinstance(payload.get("active_wave"), Mapping) else {}
    artifacts = set()
    if phase.get("phase_id"):
        artifacts.add(f"phase:{phase.get('phase_id')}")
    if active_wave.get("wave_id"):
        artifacts.add(f"wave:{active_wave.get('wave_id')}")
    return artifacts


def _context_pack_scent_sources(packet: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for row in packet.get("selected_rows") or []:
        if not isinstance(row, Mapping):
            continue
        kind_id = str(row.get("kind_id") or "")
        row_id = str(row.get("row_id") or "")
        if not kind_id or not row_id:
            continue
        artifact_id = f"{kind_id}:{row_id}"
        passport = row.get("affordance_passport") if isinstance(row.get("affordance_passport"), Mapping) else {}
        fields = {
            "title": row.get("title"),
            "summary": row.get("summary"),
            "reason": row.get("reason"),
            "claim": row.get("claim"),
            "atom": row.get("atom"),
            "flag": row.get("flag"),
            "cluster_keys": " ".join(str(item) for item in row.get("cluster_keys") or []),
            "passport_cluster_keys": " ".join(str(item) for item in passport.get("cluster_keys") or []),
            "passport_when_to_open": passport.get("when_to_open"),
            "passport_when_not_to_open": passport.get("when_not_to_open"),
            "passport_landmines": " ".join(str(item) for item in passport.get("landmines") or []),
            "passport_sufficiency_claims": " ".join(str(item) for item in passport.get("sufficiency_claims") or []),
        }
        text = " ".join(str(value or "") for value in fields.values()).lower()
        sources[artifact_id] = {
            "row_id": artifact_id,
            "fields_checked": [key for key, value in fields.items() if value],
            "text": text,
        }
    return sources


def _scent_checks(task: FitnessTask, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    requirements = task.scent_requirements or {}
    if not requirements:
        return []
    if task.route_type != "context_pack":
        return []
    sources = _context_pack_scent_sources(payload)
    checks: list[dict[str, Any]] = []
    for artifact_id, terms in requirements.items():
        source = sources.get(artifact_id, {})
        text = str(source.get("text") or "")
        missing_terms = [term for term in terms if str(term).lower() not in text]
        checks.append(
            {
                "row_id": artifact_id,
                "fields_checked": source.get("fields_checked") or [],
                "required_scent": list(terms),
                "missing_scent": missing_terms,
                "scent_status": "pass" if source and not missing_terms else "fail",
            }
        )
    return checks


def _run_phase_summary(repo_root: Path, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    proc = subprocess.run(
        ["./repo-python", "kernel.py", "--phase"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "kind": "phase_summary_error",
            "error": "nonzero_exit",
            "returncode": proc.returncode,
            "stderr": _trim(proc.stderr, max_chars=500),
        }
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"kind": "phase_summary_error", "error": f"json_decode:{exc}", "stdout": _trim(proc.stdout)}


def _cli_timeout_seconds(task: FitnessTask, *, fitness_mode: str) -> float:
    route_timeout = max(
        DEFAULT_TIMEOUT_SECONDS,
        float(CLI_TIMEOUT_SECONDS_BY_ROUTE.get(task.route_type, DEFAULT_TIMEOUT_SECONDS)),
    )
    if task.route_type == "context_pack" and fitness_mode == "semantic":
        return max(route_timeout, DEFAULT_TIMEOUT_SECONDS * 2)
    return route_timeout


def _evaluate_task(
    repo_root: Path,
    task: FitnessTask,
    *,
    context_budget: int,
    include_semantic: bool,
    fitness_mode: str,
) -> dict[str, Any]:
    route_args = dict(task.route_args or {})
    route_role = str(task.route_role or "first_contact")
    if route_role == "first_contact" and task.route_type == "navigation_metabolism":
        route_role = "diagnostic"
    elif route_role == "first_contact" and task.route_type == "paper_lattice":
        route_role = "evidence"
    command_used = ""
    first_contact_command = ""
    timed_out = False
    error: str | None = None
    payload: Mapping[str, Any] = {}
    selected: set[str] = set()
    timeout_seconds = _cli_timeout_seconds(task, fitness_mode=fitness_mode)
    start = time.perf_counter()
    try:
        if task.route_type == "context_pack":
            first_contact_command = "./repo-python kernel.py --context-pack"
            command_used = (
                f'./repo-python kernel.py --context-pack {json.dumps(task.task_prompt)} '
                f"--context-budget {context_budget}"
            )
            if fitness_mode in {"cli", "semantic"}:
                env = {
                    "AIW_NAV_FITNESS_ENABLE_SEMANTIC": "1" if fitness_mode == "semantic" else "0",
                    "AIW_CONTEXT_PACK_DISABLE_SEMANTIC": "" if fitness_mode == "semantic" else "1",
                }
                payload, timed_out, cli_error = _run_kernel_json(
                    repo_root,
                    ["--context-pack", task.task_prompt, "--context-budget", str(context_budget)],
                    timeout=timeout_seconds,
                    env=env,
                )
                error = cli_error
            else:
                payload = build_navigation_context_pack(
                    repo_root,
                    task.task_prompt,
                    context_budget=context_budget,
                    include_semantic=include_semantic,
                )
            selected = _context_pack_artifacts(payload)
        elif task.route_type == "navigation_metabolism":
            first_contact_command = "./repo-python kernel.py --navigation-metabolism"
            command_used = (
                f'./repo-python kernel.py --navigation-metabolism {json.dumps(task.task_prompt)} '
                f"--metabolism-profile quick --context-budget {context_budget}"
            )
            if fitness_mode == "cli":
                payload, timed_out, cli_error = _run_kernel_json(
                    repo_root,
                    [
                        "--navigation-metabolism",
                        task.task_prompt,
                        "--metabolism-profile",
                        "quick",
                        "--context-budget",
                        str(context_budget),
                    ],
                    timeout=timeout_seconds,
                )
                error = cli_error
            else:
                from system.lib.navigation_metabolism_ledger import build_navigation_metabolism_ledger

                payload = build_navigation_metabolism_ledger(
                    repo_root,
                    query=task.task_prompt,
                    context_budget=context_budget,
                    include_session_summary=False,
                    include_fitness=False,
                    metabolism_profile="quick",
                )
            selected = _metabolism_artifacts(payload)
        elif task.route_type == "entrypoint_health":
            first_contact_command = "entrypoint_health"
            if fitness_mode == "cli":
                command_used = "./repo-python kernel.py --entrypoint-health"
                payload, timed_out, cli_error = _run_kernel_json(
                    repo_root,
                    ["--entrypoint-health"],
                    timeout=timeout_seconds,
                )
                error = cli_error
                selected = _entrypoint_audit_artifacts(payload)
            else:
                command_used = "entrypoint_health.build_entrypoint_health"
                payload = build_entrypoint_health(repo_root)
                selected = (
                    {"entrypoint_health:valid"}
                    if (payload.get("summary") or {}).get("contract_status") == "valid"
                    else set()
                )
        elif task.route_type == "option_surface_cluster":
            kind_id = str(route_args.get("kind_id") or "skills")
            first_contact_command = f"./repo-python kernel.py --option-surface {kind_id} --band cluster_flag"
            command_used = f"./repo-python kernel.py --option-surface {kind_id} --band cluster_flag"
            if fitness_mode == "cli":
                payload, timed_out, cli_error = _run_kernel_json(
                    repo_root,
                    ["--option-surface", kind_id, "--band", "cluster_flag"],
                    timeout=timeout_seconds,
                )
                error = cli_error
            else:
                payload = build_option_surface(repo_root, kind_id, band="cluster_flag")
            selected = _cluster_artifacts(kind_id, payload)
        elif task.route_type == "paper_lattice":
            slug = str(route_args.get("slug") or "navigation_hologram_theory")
            first_contact_command = f"./repo-python kernel.py --paper-lattice {slug}"
            command_used = f"./repo-python kernel.py --paper-lattice {slug} --band card --context-budget {context_budget}"
            if fitness_mode == "cli":
                payload, timed_out, cli_error = _run_kernel_json(
                    repo_root,
                    ["--paper-lattice", slug, "--band", "card", "--context-budget", str(context_budget)],
                    timeout=timeout_seconds,
                )
                error = cli_error
            else:
                payload = build_dynamic_paper_lattice(repo_root, slug=slug, band="card", context_budget=context_budget)
            selected = _paper_lattice_artifacts(payload)
        elif task.route_type == "phase_summary":
            first_contact_command = "./repo-python kernel.py --phase"
            command_used = "./repo-python kernel.py --phase"
            payload = _run_phase_summary(repo_root, timeout=timeout_seconds)
            selected = _phase_artifacts(payload)
        else:
            first_contact_command = f"unsupported:{task.route_type}"
            command_used = f"unsupported:{task.route_type}"
            payload = {"kind": "navigation_fitness_error", "error": f"unsupported_route_type:{task.route_type}"}
            selected = set()
    except subprocess.TimeoutExpired:
        timed_out = True
        selected = set()
        payload = {"kind": "navigation_fitness_error", "error": "timeout"}
    except Exception as exc:  # noqa: BLE001 - fitness must report failures, not crash the ledger
        error = f"{type(exc).__name__}: {exc}"
        selected = set()
        payload = {"kind": "navigation_fitness_error", "error": error}
    wall_ms = int(round((time.perf_counter() - start) * 1000))
    output_bytes = _json_bytes(payload)
    expected = set(task.expected_artifacts)
    found, missing = _match_expected(expected, selected)
    recall = 1.0 if not expected else len(found) / len(expected)
    precision = 1.0 if not selected else len(found) / max(1, len(selected))
    latency_budget = int(task.latency_budget_ms or DEFAULT_LATENCY_BUDGETS_MS.get(task.route_type, 2500))
    forbidden_hits = [route for route in task.forbidden_first_routes if route and route in first_contact_command]
    next_drilldown_available = _next_drilldown_available(task.route_type, payload)
    scent_checks = _scent_checks(task, payload)
    scent_failures = [check for check in scent_checks if check.get("scent_status") == "fail"]
    scent_status = "unscored" if not scent_checks else "pass" if not scent_failures else "fail"
    if not expected:
        sufficiency_status = "unscored"
        sufficiency_failure_kind = None
    elif timed_out:
        sufficiency_status = "fail"
        sufficiency_failure_kind = "route_timeout"
    elif error is not None:
        sufficiency_status = "fail"
        sufficiency_failure_kind = "route_error"
    elif missing:
        sufficiency_status = "fail"
        sufficiency_failure_kind = "missing_id"
    elif scent_failures:
        sufficiency_status = "fail"
        sufficiency_failure_kind = "weak_scent"
    elif not next_drilldown_available:
        sufficiency_status = "fail"
        sufficiency_failure_kind = "missing_drilldown"
    elif forbidden_hits:
        sufficiency_status = "fail"
        sufficiency_failure_kind = "forbidden_route"
    else:
        sufficiency_status = "pass"
        sufficiency_failure_kind = None
    latency_status = "timeout" if timed_out else "pass" if wall_ms <= latency_budget else "fail"
    selected_artifacts = _selected_artifact_display(selected, expected)
    stage_timings_ms = {}
    semantic_status = {}
    if task.route_type == "context_pack":
        strategy = payload.get("strategy") if isinstance(payload.get("strategy"), Mapping) else {}
        stage_timings_ms = dict(strategy.get("stage_timings_ms") or {}) if isinstance(strategy.get("stage_timings_ms"), Mapping) else {}
        semantic_status = dict(strategy.get("semantic_status") or {}) if isinstance(strategy.get("semantic_status"), Mapping) else {}
        if semantic_status.get("status") == "disabled":
            semantic_status = {
                "status": "disabled",
                "reason": semantic_status.get("reason"),
                "wall_ms": semantic_status.get("wall_ms"),
            }
    slow_stage = None
    if stage_timings_ms:
        slow_stage = max(stage_timings_ms.items(), key=lambda item: int(item[1] or 0))[0]
    return {
        "task_id": task.task_id,
        "family": task.family,
        "task_prompt": task.task_prompt,
        "fitness_mode": fitness_mode,
        "route_type": task.route_type,
        "route_role": route_role,
        "command_used": command_used,
        "first_contact_command": first_contact_command,
        "output_bytes": output_bytes,
        "estimated_tokens": max(1, (output_bytes + 3) // 4),
        "wall_ms": wall_ms,
        "latency_budget_ms": latency_budget,
        "timeout_seconds": timeout_seconds if fitness_mode in {"cli", "semantic"} else None,
        "stage_timings_ms": stage_timings_ms,
        "semantic_status": semantic_status,
        "slow_stage": slow_stage,
        "selected_artifacts": selected_artifacts,
        "selected_artifact_count": len(selected),
        "expected_artifacts": sorted(expected),
        "found_expected_artifacts": found,
        "missing_expected_artifacts": missing,
        "recall_at_packet": round(recall, 4),
        "precision_at_packet": round(precision, 4),
        "next_drilldown_available": next_drilldown_available,
        "forbidden_first_route_hits": forbidden_hits,
        "scent_status": scent_status,
        "scent_checks": scent_checks,
        "sufficiency_status": sufficiency_status,
        "sufficiency_failure_kind": sufficiency_failure_kind,
        "latency_status": latency_status,
        "error": error,
        "timed_out": timed_out,
    }


def _match_expected(expected: set[str], selected: set[str]) -> tuple[list[str], list[str]]:
    found: list[str] = []
    missing: list[str] = []
    for item in sorted(expected):
        if item.endswith("*"):
            prefix = item[:-1]
            match = next((candidate for candidate in sorted(selected) if candidate.startswith(prefix)), None)
            if match:
                found.append(item)
            else:
                missing.append(item)
        elif item in selected:
            found.append(item)
        else:
            missing.append(item)
    return found, missing


def _selected_artifact_display(selected: set[str], expected: set[str], *, limit: int = 24) -> list[str]:
    ordered = sorted(selected)
    display = ordered[:limit]
    for item in sorted(expected):
        selected_item = None
        if item.endswith("*"):
            prefix = item[:-1]
            selected_item = next((candidate for candidate in ordered if candidate.startswith(prefix)), None)
        elif item in selected:
            selected_item = item
        if selected_item and selected_item not in display:
            display.append(selected_item)
    return display


def _route_type_metrics(results: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for result in results:
        grouped.setdefault(str(result.get("route_type") or "unknown"), []).append(result)
    metrics: dict[str, dict[str, Any]] = {}
    for route_type, rows in sorted(grouped.items()):
        wall_values = [int(row.get("wall_ms") or 0) for row in rows]
        metrics[route_type] = {
            "count": len(rows),
            "p50_wall_ms": _percentile(wall_values, 50),
            "p95_wall_ms": _percentile(wall_values, 95),
            "max_wall_ms": max(wall_values) if wall_values else None,
            "latency_fail_count": sum(1 for row in rows if row.get("latency_status") in {"fail", "timeout"}),
        }
    return metrics


def _latency_repair_class(route_type: str, slow_stage: str | None, fitness_mode: str | None) -> str:
    if fitness_mode == "semantic":
        if slow_stage == "semantic_candidates":
            return "defer_or_cache_semantic_expansion"
        return "live_semantic_latency_profile"
    if route_type == "context_pack":
        stage_map = {
            "kind_atlas": "cache_kind_atlas",
            "semantic_candidates": "defer_or_cache_semantic_expansion",
            "selected_rows": "precompute_selected_option_rows",
            "overview": "cache_option_surface_cluster",
            "budget_trim": "optimize_budget_trim",
        }
        return stage_map.get(str(slow_stage or ""), "cache_or_precompute_context_pack_selector")
    if route_type == "navigation_metabolism":
        return "split_metabolism_summary_from_full"
    if route_type == "paper_lattice":
        return "memoize_paper_lattice_exemplar"
    if route_type == "option_surface_cluster":
        return "cache_option_surface_cluster"
    return "cache_or_precompute_selector"


def _sufficiency_repair_class(
    failure_kind: str | None,
    *,
    route_type: str = "",
    slow_stage: str | None = None,
    fitness_mode: str | None = None,
) -> str:
    if failure_kind == "route_timeout":
        if route_type == "navigation_metabolism":
            return "split_metabolism_summary_from_full"
        if route_type == "entrypoint_health":
            return "use_cheap_entrypoint_health_cli"
        if route_type == "context_pack" and fitness_mode == "semantic":
            return "defer_or_cache_semantic_expansion"
        if slow_stage == "semantic_candidates":
            return "defer_or_cache_semantic_expansion"
        return "route_timeout_profile_repair"
    if failure_kind == "route_error":
        return "route_error_contract_repair"
    if failure_kind == "weak_scent":
        return "compression_passport_or_claim_rewrite"
    if failure_kind == "missing_drilldown":
        return "drilldown_projection_repair"
    if failure_kind == "forbidden_route":
        return "first_contact_route_steering_repair"
    return "compression_passport_or_selector_repair"


def _next_drilldown_available(route_type: str, payload: Mapping[str, Any]) -> bool:
    if route_type == "context_pack":
        if payload.get("next_commands"):
            return True
        return any(
            isinstance(row, Mapping)
            and (row.get("drilldown_command") or row.get("drilldowns") or row.get("evidence_command"))
            for row in payload.get("selected_rows") or []
        )
    if route_type == "navigation_metabolism":
        return bool(payload.get("top_repairs") or payload.get("next_commands"))
    if route_type == "entrypoint_health":
        return True
    if route_type == "option_surface_cluster":
        if payload.get("next"):
            return True
        return any(
            isinstance(row, Mapping)
            and (row.get("drilldown_command") or row.get("top_ids"))
            for row in payload.get("rows") or []
        )
    if route_type == "paper_lattice":
        return bool(payload.get("next_commands") or payload.get("error"))
    if route_type == "phase_summary":
        return bool((payload.get("payload") or {}).get("full_payload_hint") or payload.get("next"))
    return False


_TIMEOUT_REPAIR_OWNERS: dict[str, tuple[str, ...]] = {
    "split_metabolism_summary_from_full": (
        "system/lib/navigation_metabolism_ledger.py",
        "system/lib/navigation_fitness.py",
    ),
    "use_cheap_entrypoint_health_cli": (
        "system/lib/entrypoint_health.py",
        "system/lib/navigation_fitness.py",
    ),
    "defer_or_cache_semantic_expansion": (
        "system/lib/navigation_context_pack.py",
        "system/lib/semantic_routing.py",
    ),
    "route_timeout_profile_repair": (
        "system/lib/navigation_fitness.py",
        "system/lib/navigation_context_pack.py",
    ),
}


def _timeout_target_files(repair_class: str) -> list[str]:
    return list(_TIMEOUT_REPAIR_OWNERS.get(repair_class, _TIMEOUT_REPAIR_OWNERS["route_timeout_profile_repair"]))


_LATENCY_REPAIR_OWNERS: dict[str, tuple[str, ...]] = {
    "cache_kind_atlas": (
        "system/lib/navigation_context_pack.py",
        "system/lib/kind_atlas.py",
        "system/lib/navigation_fitness.py",
    ),
    "precompute_selected_option_rows": (
        "system/lib/navigation_context_pack.py",
        "system/lib/standard_option_surface.py",
        "system/lib/navigation_fitness.py",
    ),
    "cache_option_surface_cluster": (
        "system/lib/standard_option_surface.py",
        "system/lib/navigation_fitness.py",
    ),
    "split_metabolism_summary_from_full": (
        "system/lib/navigation_metabolism_ledger.py",
        "system/lib/command_node_cache.py",
        "system/lib/navigation_fitness.py",
    ),
    "memoize_paper_lattice_exemplar": (
        "system/lib/dynamic_paper_lattice.py",
        "system/lib/navigation_fitness.py",
    ),
    "cache_or_precompute_selector": (
        "system/lib/navigation_context_pack.py",
        "system/lib/navigation_fitness.py",
    ),
    "cache_or_precompute_context_pack_selector": (
        "system/lib/navigation_context_pack.py",
        "system/lib/navigation_fitness.py",
    ),
    "defer_or_cache_semantic_expansion": (
        "system/lib/navigation_context_pack.py",
        "system/lib/semantic_routing.py",
        "system/lib/navigation_fitness.py",
    ),
    "live_semantic_latency_profile": (
        "system/lib/navigation_context_pack.py",
        "system/lib/semantic_routing.py",
        "system/lib/navigation_fitness.py",
    ),
    "optimize_budget_trim": (
        "system/lib/navigation_context_pack.py",
        "system/lib/navigation_fitness.py",
    ),
}


def _latency_target_files(repair_class: str) -> list[str]:
    return list(_LATENCY_REPAIR_OWNERS.get(repair_class, _LATENCY_REPAIR_OWNERS["cache_or_precompute_selector"]))


def _debt_candidates(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        task_id = str(result.get("task_id") or "unknown")
        if result.get("sufficiency_status") == "fail":
            route_type = str(result.get("route_type") or "unknown")
            failure_kind = str(result.get("sufficiency_failure_kind") or "unknown")
            slow_stage = result.get("slow_stage")
            fitness_mode = result.get("fitness_mode")
            if failure_kind == "route_timeout":
                hidden_ids = list(result.get("missing_expected_artifacts") or [])
                repair_class = _sufficiency_repair_class(
                    failure_kind,
                    route_type=route_type,
                    slow_stage=str(slow_stage or "") or None,
                    fitness_mode=str(fitness_mode or "") or None,
                )
                target_files = _timeout_target_files(repair_class)
                preview_ids = hidden_ids[:3]
                title = (
                    "Navigation route timed out before producing a packet; "
                    f"repair_owner={target_files[0]}; "
                    f"hidden_expected_ids={preview_ids}"
                )
                rows.append(
                    {
                        "debt_id": f"timeout:{route_type}:{task_id}",
                        "debt_class": "timeout_debt",
                        "priority": 88,
                        "title": title,
                        "evidence": (
                            f"failure_kind=route_timeout; "
                            f"hidden_expected_artifacts={hidden_ids}; "
                            f"wall_ms={result.get('wall_ms')}; "
                            f"latency_budget_ms={result.get('latency_budget_ms')}; "
                            f"command={result.get('command_used')}"
                        ),
                        "repair_class": repair_class,
                        "target_files": target_files,
                        "tests": [
                            "navigation-fitness timeout debt names hidden expected ids and repair owner",
                            "navigation-fitness sufficiency debt does not absorb route_timeout cases",
                        ],
                        "task_id": task_id,
                        "route_type": route_type,
                        "route_role": result.get("route_role"),
                        "failure_kind": failure_kind,
                        "fitness_mode": fitness_mode,
                        "slow_stage": slow_stage,
                        "hidden_expected_artifacts": hidden_ids,
                    }
                )
            else:
                rows.append(
                    {
                        "debt_id": f"sufficiency:{route_type}:{task_id}",
                        "debt_class": "sufficiency_debt",
                        "priority": 87,
                        "title": "Compressed navigation packet did not expose the expected next drilldown",
                        "evidence": (
                            f"failure_kind={failure_kind}; missing={result.get('missing_expected_artifacts')}; "
                            f"scent={result.get('scent_checks')}; "
                            f"recall={result.get('recall_at_packet')}; command={result.get('command_used')}"
                        ),
                        "repair_class": _sufficiency_repair_class(
                            failure_kind,
                            route_type=route_type,
                            slow_stage=str(slow_stage or "") or None,
                            fitness_mode=str(fitness_mode or "") or None,
                        ),
                        "target_files": [
                            "system/lib/navigation_context_pack.py",
                            "codex/doctrine/skills/skill_registry.json",
                            "system/lib/standard_option_surface.py",
                        ],
                        "tests": [
                            "navigation-fitness fixture finds the expected stable ids",
                            "selected compressed row exposes a next drilldown without legacy keyword search",
                        ],
                        "task_id": task_id,
                        "route_type": route_type,
                        "route_role": result.get("route_role"),
                        "failure_kind": failure_kind,
                        "fitness_mode": fitness_mode,
                        "slow_stage": slow_stage,
                    }
                )
        if result.get("latency_status") in {"fail", "timeout"}:
            route_type = str(result.get("route_type") or "unknown")
            slow_stage = result.get("slow_stage")
            fitness_mode = result.get("fitness_mode")
            route_role = str(result.get("route_role") or "first_contact")
            latency_priority = 86 if route_role == "first_contact" else 78 if route_role == "diagnostic" else 64
            repair_class = _latency_repair_class(
                route_type,
                str(slow_stage or "") or None,
                str(fitness_mode or ""),
            )
            rows.append(
                {
                    "debt_id": f"latency:{route_type}:{task_id}",
                    "debt_class": "latency_debt",
                    "priority": latency_priority,
                    "title": "Navigation first-contact route exceeded its latency budget",
                    "evidence": (
                        f"wall_ms={result.get('wall_ms')}; budget_ms={result.get('latency_budget_ms')}; "
                        f"status={result.get('latency_status')}; slow_stage={slow_stage}; "
                        f"mode={fitness_mode}; command={result.get('command_used')}"
                    ),
                    "repair_class": repair_class,
                    "target_files": _latency_target_files(repair_class),
                    "tests": [
                        "navigation-fitness latency status passes for this fixture or records explicit diagnostic-only classification",
                    ],
                    "task_id": task_id,
                    "route_type": route_type,
                    "route_role": result.get("route_role"),
                    "slow_stage": slow_stage,
                    "fitness_mode": fitness_mode,
                }
            )
    return rows


def build_navigation_fitness(
    repo_root: Path | str,
    query_or_suite: str | None = None,
    *,
    context_budget: int = DEFAULT_CONTEXT_BUDGET,
    tasks: Sequence[FitnessTask] | None = None,
    include_semantic: bool | None = None,
    fitness_mode: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    budget = max(1000, int(context_budget or DEFAULT_CONTEXT_BUDGET))
    suite, selected_tasks = _select_tasks(query_or_suite, tasks=tasks)
    mode = _normalize_mode(fitness_mode, include_semantic)
    semantic_enabled = (
        True
        if mode == "semantic"
        else False
        if mode in {"library", "cli"}
        else (
        include_semantic
        if include_semantic is not None
        else os.environ.get("AIW_NAV_FITNESS_ENABLE_SEMANTIC") == "1"
        )
    )
    results = [
        _evaluate_task(
            root,
            task,
            context_budget=budget,
            include_semantic=bool(semantic_enabled),
            fitness_mode=mode,
        )
        for task in selected_tasks
    ]
    wall_values = [int(result.get("wall_ms") or 0) for result in results]
    suff_failures = [result for result in results if result.get("sufficiency_status") == "fail"]
    latency_failures = [result for result in results if result.get("latency_status") in {"fail", "timeout"}]
    debt_candidates = _debt_candidates(results)
    packet: dict[str, Any] = {
        "kind": "navigation_fitness",
        "schema_version": "navigation_fitness_v0",
        "query_or_suite": query_or_suite or "baseline",
        "suite": suite,
        "budget": {
            "context_budget_tokens": budget,
            "estimated_tokens": 0,
            "hard_ceiling": True,
        },
        "strategy": {
            "cold_task_fitness": True,
            "measures_sufficiency_and_latency": True,
            "fitness_mode": mode,
            "available_modes": sorted(FITNESS_MODES),
            "available_suites": ["smoke", "baseline", "heldout_20", "adversarial_20"],
            "library_mode": "in-process deterministic builders",
            "cli_mode": "actual ./repo-python kernel.py command paths for route tasks",
            "semantic_mode": "live context-pack semantic expansion through the CLI with timeout protection",
            "semantic_context_pack_enabled": bool(semantic_enabled),
            "semantic_note": (
                "Use --fitness-mode semantic or AIW_NAV_FITNESS_ENABLE_SEMANTIC=1 to include live semantic route expansion; "
                "library mode keeps the harness deterministic and fast enough for the ratchet."
            ),
        },
        "summary": {
            "task_count": len(results),
            "sufficiency_pass_count": sum(1 for result in results if result.get("sufficiency_status") == "pass"),
            "sufficiency_fail_count": len(suff_failures),
            "latency_pass_count": sum(1 for result in results if result.get("latency_status") == "pass"),
            "latency_fail_count": len(latency_failures),
            "p50_wall_ms": _percentile(wall_values, 50),
            "p95_wall_ms": _percentile(wall_values, 95),
            "max_wall_ms": max(wall_values) if wall_values else None,
            "debt_candidate_count": len(debt_candidates),
        },
        "route_type_metrics": _route_type_metrics(results),
        "latency_budgets_ms": dict(DEFAULT_LATENCY_BUDGETS_MS),
        "task_results": results,
        "debt_candidates": debt_candidates,
        "next_commands": [
            "./repo-python kernel.py --navigation-fitness smoke --fitness-mode library --context-budget 12000",
            "./repo-python kernel.py --navigation-fitness smoke --fitness-mode cli --context-budget 12000",
            "./repo-python kernel.py --navigation-fitness smoke --fitness-mode semantic --context-budget 12000",
            "./repo-python kernel.py --navigation-fitness heldout_20 --context-budget 12000",
            "./repo-python kernel.py --navigation-fitness adversarial_20 --context-budget 12000",
            "./repo-python kernel.py --navigation-metabolism \"navigation fitness\" --metabolism-profile quick --context-budget 12000",
        ],
    }
    packet["budget"]["estimated_tokens"] = _estimate_tokens(packet)
    if packet["budget"]["estimated_tokens"] > budget:
        packet["task_results"] = packet["task_results"][:12]
        packet["debt_candidates"] = packet["debt_candidates"][:12]
        packet["budget"]["trimmed_for_budget"] = True
        packet["budget"]["estimated_tokens"] = _estimate_tokens(packet)
    else:
        packet["budget"]["trimmed_for_budget"] = False
    return packet
