"""
[PURPOSE]
- Teleology: Single source of truth for kernel-wide shared state (repo root, resolved paths, constants).
- Mechanism: Lazy initialization via init(repo_root) called once by kernel.py during bootstrap.
  All path constants are derived from repo_root and observe_asset_paths. Command modules import
  from here instead of referencing kernel.py directly, breaking the monolith dependency.

[INTERFACE]
- Exports: init(), REPO_ROOT, all OBSERVE_*/APPLY_*/CODEX_* path constants, configuration constants.
- Guarantee: After init() returns, every module-level Path is resolved and usable.
- Fails: Calling any path before init() → AttributeError.

[FLOW]
- kernel.py calls _bootstrap() to locate the repo root.
- kernel.py calls init(repo_root) once.
- Command and helper modules import paths directly: `from system.lib.kernel.state import REPO_ROOT, OBSERVE_PLAN`.

[DEPENDENCIES]
- system.lib.observe_assets: observe_asset_paths (path registry for observe infrastructure)
- system.lib.standards_registry: STANDARDS_REGISTRY_PATH

[CONSTRAINTS]
- Determinism: All paths are pure derivations from repo_root — no filesystem probing.
- Atomicity: init() is idempotent; second call is a no-op.
- Non-goal: This module does NOT import kernel_navigation, bridge, or any heavy subsystem.
- When-needed: Open when kernel modules need the authoritative shared path/constants surface or the bootstrap-time path derivation contract instead of reading kernel.py globals.
- Escalates-to: system/lib/observe_assets.py; system/lib/kernel_navigation.py; system/lib/contracts.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Stable kernel contract constants
# ---------------------------------------------------------------------------
KERNEL_VERSION = "1.0.0"
KERNEL_ENTRYPOINT = "kernel.py"
FOCUS_STATUS_CHOICES = ("active", "blocked", "parked", "completed", "reference")

STABLE_COMMANDS = {
    "navigate": (
        "--pulse", "--full", "--info", "--frontier", "--recent-obsidian",
        "--working-set", "--bootstrap-task", "--extract-note-structure",
        "--extract-note-mode", "--extract-note", "--obsidian-family",
        "--set-focus", "--focus-status", "--focus-label", "--focus-handoff",
        "--focus-scope", "--clear-focus-status", "--clear-focus-label",
        "--clear-focus-handoff", "--execution-map", "--map", "--stale",
        "--doc-gaps", "--anchor", "--paths", "--atlas", "--orient",
        "--docs-route", "--paper-module", "--paper-module-coverage",
        "--kind-atlas", "--kind-band-contract-audit", "--option-surface", "--band", "--ids",
        "--navigation-context-rosetta", "--context-pack", "--navigation-surface-audit", "--surface-authoring-audit", "--entrypoint-health", "--annex-movement-pressure-map", "--annex-navigation-dogfood", "--navigation-metabolism", "--surface-ratchet", "--metabolism-profile", "--navigation-fitness", "--fitness-mode", "--paper-lattice", "--dynamic-paper", "--lattice-scope", "--lattice-facet", "--edge-neighborhood", "--context-budget",
        "--latency-seed-digest", "--latency-seed-top", "--latency-seed-no-git", "--latency-seed-format",
        "--nav-hologram", "--compression-band",
        "--paper-module-route-coverage", "--paper-module-route", "--facts", "--fact", "--fact-audit",
        "--paper-module-facts", "--list-docs-route-focus", "--set-docs-route-focus",
        "--organisation-control-plane", "--organization-control-plane", "--organisation-next-slice", "--organization-next-slice",
        "--skill-find", "--command-card", "--validate-seed-continuity", "--validate-seed-heartbeat", "--session-diagnostics",
        "--orient-task", "--context", "--trace", "--direction", "--doctrine",
        "--doctrine-runtime", "--locate", "--run-context", "--lens", "--compile",
        "--standards-companion-drift", "--metabolism-row-jobs", "--provider-plane-liveness",
        "--provider-plane-application-catalog",
        "--kernel-surface-currentness", "--kernel-surface-currentness-waves", "--waves",
        "--relational-context", "--relational-context-band", "--relational-context-radius",
    ),
    "planning": (
        "--phase", "--phase-harbor", "--phase-deposit", "--phase-begin",
        "--phase-dock", "--ingest-phase-deposit", "--phase-observe",
        "--plan-phase", "--plan-batch", "--compile-batch", "--plan-sync",
        "--impact", "--verify", "--add-workstream", "--add-phase",
        "--new-family", "--new-phase", "--parent", "--number", "--title",
        "--write-packet",
    ),
    "observe": (
        "--plan", "--set-plan", "--validate", "--quick", "--files",
        "--situation", "--summary", "--launch-observe", "--bridge-status",
        "--bridge-preflight", "--bridge", "--provider", "--bridge-provider",
        "--bridge-workers", "--bridge-timeout-s", "--bridge-max-chars",
        "--resume-observe", "--retry-label", "--run-kind", "--launch-dispatch",
        "--no-sticky-dump-dir", "--detach", "--log-file", "--draft-observe",
        "--draft-session", "--draft-next-pass", "--validate-session",
        "--writeback-session", "--boundary", "--source-paths", "--write-plan",
        "--continue-from", "--synthesize", "--digest-observe", "--questions",
        "--review", "--miner", "--miner-emit-manifest", "--remediate",
    ),
    "apply": (
        "--apply", "--apply-session", "--apply-session-loop", "--apply-loop",
        "--live", "--no-auto-rollback", "--target-family", "--apply-validate",
        "--quick-apply", "--target", "--metabolize", "--from-observe",
        "--source-artifact", "--section",
    ),
    "check": ("--check", "--code-files"),
    "validate": ("--scratchpad", "--show-pass", "--json"),
    "infrastructure": (
        "--runs", "--data-roots", "--run-artifacts", "--run-artifact",
        "--run-state", "--run-debug", "--run-predictions", "--run-compare",
        "--run-grade-predictions", "--run-evidence", "--run-timeline",
        "--run-lineage", "--prune", "--build", "--build-phases", "--dry-run",
        "--graph", "--hologram", "--inspect", "--tree-modes",
    ),
    "common": (
        "--tree", "--history", "--contents", "--list-dumps", "--read-dump",
        "--list-observes", "--read-observe", "--open", "--friction",
        "--friction-report", "--list-sessions", "--read-session",
        "--draft-next-pass", "--writeback-session", "--standards",
        "--prompt", "--list-prompts", "--doctrine-runtime",
    ),
}

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
MARKDOWN_FRONTIER_DEFAULT_LIMIT = 5
PRUNE_MIN_AGE_HOURS = 48.0
PRUNE_TELEMETRY_FILE = "_prune_telemetry.jsonl"
DEFAULT_BRIDGE_TIMEOUT_S = 1500.0
DEFAULT_DETACHED_OBSERVE_RECEIPT_TIMEOUT_S = 8.0
DEFAULT_DETACHED_OBSERVE_RECEIPT_POLL_S = 0.1
DEFAULT_DETACHED_OBSERVE_LOG_TAIL_LINES = 40
METABOLIZE_MARKDOWN_SKIP_DIRS = {
    ".git", ".hg", ".obsidian", ".pytest_cache", ".ruff_cache",
    ".svn", ".venv", "__pycache__", "build", "dist", "node_modules", "venv",
}

AUTO_DEFAULT_PHASE_LABEL: str = "ACTIVE"
AUTO_DEFAULT_PHASE_HANDOFF: str = ""

# ---------------------------------------------------------------------------
# Module-level path state — populated by init()
# ---------------------------------------------------------------------------
_initialized = False

REPO_ROOT: Path
APPLY_DIR: Path

# Observe infrastructure
OBSERVE_PLAN: Path
OBSERVE_RESULT: Path
OBSERVE_DUMPS: Path
OBSERVE_HISTORY: Path
OBSERVE_HISTORY_MD: Path
OBSERVE_HISTORY_DIR: Path
OBSERVE_PROMPT: Path
OBSERVE_PATTERN_GUIDE: Path
TREE_MD: Path
TREE_MANIFEST: Path
OBSERVE_PLAN_SUGGESTION: Path
OBSERVE_PLANS_DIR: Path
OBSERVE_SESSION_ROOT: Path
OBSERVE_HISTORY_ENTRIES_DIR: Path
OBSERVE_HISTORY_DIGESTS_DIR: Path
OBSERVE_HISTORY_PROMPTS_DIR: Path
OBSERVE_HISTORY_RUNTIME_DIR: Path
OBSERVE_STICKY_DUMP_MARKER: Path
OBSERVE_RUNNER: Path
OBSERVE_SESSION_RUNNER: Path
FRICTION_LOG: Path

# Apply infrastructure
APPLY_PLAN: Path
APPLY_METABOLIZE_PLAN: Path
APPLY_METABOLIZE_RESULT: Path
APPLY_METABOLIZE_PATCH_MAP_PLAN: Path
APPLY_METABOLIZE_PATCH_MAP_RESULT: Path
APPLY_RESULT: Path
APPLY_LOOP_RESULT: Path
APPLY_HISTORY: Path
APPLY_SNAPSHOTS: Path

# Codex/standards
CODEX_STANDARDS_DIR: Path
STANDARDS_REGISTRY: Path
CODEX_RESOURCES_DIR: Path
STD_MARKDOWN_DOC: Path
STD_PLAN_NOTE: Path
STD_WORK_NOTE: Path
STD_NODE_REASONING: Path
STD_NODE_TOOL: Path
STD_APPLY: Path
APPLY_GUIDE: Path
KERNEL_PRINCIPLES_DOC: Path
PLAN_DIR: Path
SCRATCHPAD_PY: Path
SCRATCHPAD_PROMPT: Path

# Builder / derived
BUILDER_PY: Path
MAP_FILE: Path
COMPILED_DIR: Path
MASTER_CONFIG: Path

# Standards shortcuts
STANDARDS_DIR: Path
STD_GENERAL: Path
STD_OBSERVE_SESSION: Path
STD_OBSERVE_CYCLE: Path
STD_SESSION_DIGEST: Path
STD_SEARCH: Path
STD_FRAMEWORK: Path
STD_PROMPTS_MD: Path
STD_PROMPTS_JSON: Path
STD_TEMPLATES: Path
KERNEL_SKILLS_SCHEMA: Path
DOCTRINE_RUNTIME_SPEC: Path

# Navigation output mode
NAVIGATION_FULL_OUTPUT: bool = False


def init(repo_root: Path) -> None:
    """
    [ACTION]
    - Teleology: Bootstrap the kernel's shared state surface exactly once so command and helper modules can import stable paths and defaults without depending on kernel.py globals.
    - Mechanism: Short-circuit on repeat calls, derive observe/apply/standards paths from repo_root plus observe_asset_paths(), and assign the resulting Paths into module-level globals.
    - Reads: repo_root, system.lib.observe_assets.observe_asset_paths(), and system.lib.standards_registry.STANDARDS_REGISTRY_PATH.
    - Writes: Module-level path and config globals in this module.
    - Guarantee: After return, every exported path constant is a resolved Path and later init() calls are no-ops.
    - Fails: None (all derivations are pure).
    - When-needed: Open when diagnosing kernel bootstrap order or any shared-path mismatch across command modules.
    - Escalates-to: system/lib/observe_assets.py; system/lib/kernel_navigation.py
    - Navigation-group: kernel_lib
    """
    global _initialized, REPO_ROOT, APPLY_DIR, NAVIGATION_FULL_OUTPUT
    global OBSERVE_PLAN, OBSERVE_RESULT, OBSERVE_DUMPS, OBSERVE_HISTORY
    global OBSERVE_HISTORY_MD, OBSERVE_HISTORY_DIR, OBSERVE_PROMPT
    global OBSERVE_PATTERN_GUIDE, TREE_MD, TREE_MANIFEST, OBSERVE_PLAN_SUGGESTION
    global OBSERVE_PLANS_DIR, OBSERVE_SESSION_ROOT
    global OBSERVE_HISTORY_ENTRIES_DIR, OBSERVE_HISTORY_DIGESTS_DIR
    global OBSERVE_HISTORY_PROMPTS_DIR, OBSERVE_HISTORY_RUNTIME_DIR
    global OBSERVE_STICKY_DUMP_MARKER, OBSERVE_RUNNER, OBSERVE_SESSION_RUNNER
    global FRICTION_LOG
    global APPLY_PLAN, APPLY_METABOLIZE_PLAN, APPLY_METABOLIZE_RESULT
    global APPLY_METABOLIZE_PATCH_MAP_PLAN, APPLY_METABOLIZE_PATCH_MAP_RESULT
    global APPLY_RESULT, APPLY_LOOP_RESULT, APPLY_HISTORY, APPLY_SNAPSHOTS
    global CODEX_STANDARDS_DIR, STANDARDS_REGISTRY, CODEX_RESOURCES_DIR
    global STD_MARKDOWN_DOC, STD_PLAN_NOTE, STD_WORK_NOTE
    global STD_NODE_REASONING, STD_NODE_TOOL, STD_APPLY, APPLY_GUIDE
    global KERNEL_PRINCIPLES_DOC, PLAN_DIR, SCRATCHPAD_PY, SCRATCHPAD_PROMPT
    global BUILDER_PY, MAP_FILE, COMPILED_DIR, MASTER_CONFIG
    global STANDARDS_DIR, STD_GENERAL, STD_OBSERVE_SESSION, STD_OBSERVE_CYCLE
    global STD_SESSION_DIGEST, STD_SEARCH, STD_FRAMEWORK
    global STD_PROMPTS_MD, STD_PROMPTS_JSON, STD_TEMPLATES
    global KERNEL_SKILLS_SCHEMA, DOCTRINE_RUNTIME_SPEC

    if _initialized:
        return
    _initialized = True

    from system.lib.observe_assets import observe_asset_paths
    from system.lib.standards_registry import STANDARDS_REGISTRY_PATH

    REPO_ROOT = repo_root
    APPLY_DIR = repo_root / "tools" / "meta" / "apply"

    assets = observe_asset_paths(repo_root)
    OBSERVE_PLAN = assets.observe_plan
    OBSERVE_RESULT = assets.observe_result
    OBSERVE_DUMPS = assets.observe_dumps
    OBSERVE_HISTORY = assets.observe_history_json
    OBSERVE_HISTORY_MD = assets.observe_history_md
    OBSERVE_HISTORY_DIR = assets.observe_history_dir
    OBSERVE_PROMPT = assets.observe_authoring_guide
    OBSERVE_PATTERN_GUIDE = assets.observe_patterns_guide
    TREE_MD = assets.tree_md
    TREE_MANIFEST = assets.tree_manifest
    OBSERVE_PLAN_SUGGESTION = assets.observe_plan_suggestion
    OBSERVE_PLANS_DIR = APPLY_DIR / "observe_plans"
    OBSERVE_SESSION_ROOT = assets.observe_sessions_dir
    OBSERVE_HISTORY_ENTRIES_DIR = OBSERVE_HISTORY_DIR / "entries"
    OBSERVE_HISTORY_DIGESTS_DIR = OBSERVE_HISTORY_DIR / "digests"
    OBSERVE_HISTORY_PROMPTS_DIR = OBSERVE_HISTORY_DIR / "prompts"
    OBSERVE_HISTORY_RUNTIME_DIR = OBSERVE_HISTORY_DIR / "runtime"
    OBSERVE_STICKY_DUMP_MARKER = OBSERVE_HISTORY_DIR / "sticky_dump_dir.txt"
    OBSERVE_RUNNER = repo_root / "tools" / "meta" / "apply" / "run_observe_plan.py"
    OBSERVE_SESSION_RUNNER = repo_root / "tools" / "meta" / "apply" / "observe_session_runner.py"
    FRICTION_LOG = repo_root / "state" / "friction.jsonl"

    APPLY_PLAN = APPLY_DIR / "apply_plan.json"
    APPLY_METABOLIZE_PLAN = APPLY_DIR / "_metabolize_plan.json"
    APPLY_METABOLIZE_RESULT = APPLY_DIR / "_metabolize_apply_result.json"
    APPLY_METABOLIZE_PATCH_MAP_PLAN = APPLY_DIR / "_metabolize_patch_map_plan.json"
    APPLY_METABOLIZE_PATCH_MAP_RESULT = APPLY_DIR / "_metabolize_patch_map_result.json"
    APPLY_RESULT = APPLY_DIR / "apply_result.json"
    APPLY_LOOP_RESULT = APPLY_DIR / "apply_loop_result.json"
    APPLY_HISTORY = APPLY_DIR / "apply_history"
    APPLY_SNAPSHOTS = APPLY_DIR / "snapshots"

    CODEX_STANDARDS_DIR = repo_root / "codex" / "standards"
    STANDARDS_REGISTRY = repo_root / STANDARDS_REGISTRY_PATH
    CODEX_RESOURCES_DIR = repo_root / "codex" / "resources"
    STD_MARKDOWN_DOC = CODEX_STANDARDS_DIR / "std_markdown_doc.json"
    STD_PLAN_NOTE = CODEX_STANDARDS_DIR / "std_plan_note.json"
    STD_WORK_NOTE = CODEX_STANDARDS_DIR / "std_work_note.json"
    STD_NODE_REASONING = CODEX_STANDARDS_DIR / "std_node_reasoning.json"
    STD_NODE_TOOL = CODEX_STANDARDS_DIR / "std_node_tool.json"
    STD_APPLY = repo_root / "codex" / "standards" / "std_apply.json"
    APPLY_GUIDE = repo_root / "codex" / "doctrine" / "skills" / "kernel" / "apply.md"
    KERNEL_PRINCIPLES_DOC = repo_root / "codex" / "doctrine" / "references" / "kernel_principles.md"
    PLAN_DIR = repo_root / "codex" / "substrate" / "plan"
    SCRATCHPAD_PY = repo_root / "tools" / "dev" / "scratchpad.py"
    SCRATCHPAD_PROMPT = APPLY_DIR / "scratchpad.md"

    BUILDER_PY = repo_root / "tools" / "meta" / "builder.py"
    MAP_FILE = repo_root / "codex" / "derived" / "map.json"
    COMPILED_DIR = repo_root / "codex" / "derived" / "compiled"
    MASTER_CONFIG = repo_root / "master_config.json"

    STANDARDS_DIR = assets.standards_dir
    STD_GENERAL = assets.std_general
    STD_OBSERVE_SESSION = assets.std_observe_session
    STD_OBSERVE_CYCLE = CODEX_STANDARDS_DIR / "std_observe_cycle.json"
    STD_SESSION_DIGEST = CODEX_STANDARDS_DIR / "std_session_digest.json"
    STD_SEARCH = assets.std_search
    STD_FRAMEWORK = assets.observe_guide
    STD_PROMPTS_MD = assets.prompts_md
    STD_PROMPTS_JSON = assets.prompts_json
    STD_TEMPLATES = assets.templates_dir
    KERNEL_SKILLS_SCHEMA = repo_root / "codex" / "doctrine" / "skills" / "kernel" / "_schema.json"
    DOCTRINE_RUNTIME_SPEC = repo_root / "codex" / "doctrine" / "doctrine_runtime.json"


# ---------------------------------------------------------------------------
# Convenience accessors (used across many command modules)
# ---------------------------------------------------------------------------

def repo_root_resolved() -> Path:
    """[ACTION] Return the resolved repo root."""
    return REPO_ROOT.resolve()


def rel(p: Path) -> str:
    """[ACTION] Return repo-relative path string."""
    try:
        return str(p.resolve().relative_to(repo_root_resolved()))
    except ValueError:
        return str(p)
