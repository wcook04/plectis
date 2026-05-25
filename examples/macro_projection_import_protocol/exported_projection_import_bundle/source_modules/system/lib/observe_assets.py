"""
[PURPOSE]
- Teleology: Centralize canonical path resolution for observe-related docs, standards,
  generated navigation outputs, and runtime workspace state.
- Mechanism: Expose stable repo-relative constants plus a single `observe_asset_paths(root)`
  constructor that returns the canonical codex/runtime locations.
- Non-goal: This module does not read, validate, or mutate observe plans or history payloads.

[INTERFACE]
- Exports:
  - observe_asset_paths(root)
  - ObserveAssetPaths
  - repo-relative constants for canonical and runtime observe assets

[CONSTRAINTS]
- Canonical authored markdown lives under `codex/doctrine/`.
- Canonical reusable observe standards live under `codex/standards/observe/`.
- Canonical generated observe navigation lives under `codex/derived/observe/`.
- Runtime observe state remains under `tools/meta/apply/`.
- When-needed: Open when a caller needs the canonical observe/apply path registry instead of reconstructing runtime and doctrine locations from multiple kernel or server surfaces.
- Escalates-to: system/lib/kernel/state.py; tools/meta/apply/observe_session.py; system/lib/kernel/commands/navigate.py
- Navigation-group: kernel_lib
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

APPLY_DIR_REL = "tools/meta/apply"
OBSERVE_PLAN_REL = f"{APPLY_DIR_REL}/observe_plan.json"
OBSERVE_RESULT_REL = f"{APPLY_DIR_REL}/observe_result.json"
OBSERVE_DUMPS_REL = f"{APPLY_DIR_REL}/observe_dumps"
OBSERVE_HISTORY_DIR_REL = f"{APPLY_DIR_REL}/observe_history"
OBSERVE_HISTORY_JSON_REL = f"{OBSERVE_HISTORY_DIR_REL}/history_index.json"
OBSERVE_HISTORY_MD_REL = f"{OBSERVE_HISTORY_DIR_REL}/history_index.md"
APPLY_PLAN_REL = f"{APPLY_DIR_REL}/apply_plan.json"
APPLY_RESULT_REL = f"{APPLY_DIR_REL}/apply_result.json"
APPLY_HISTORY_REL = f"{APPLY_DIR_REL}/apply_history"
SCRATCHPAD_PROMPT_REL = f"{APPLY_DIR_REL}/scratchpad.md"
OBSERVE_PLAN_SUGGESTION_REL = f"{OBSERVE_DUMPS_REL}/_observe_plan_suggestion.json"

CORE_STD_OBSERVE_SESSION_REL = "codex/standards/std_observe_session.json"
CANONICAL_STANDARDS_DIR_REL = "codex/standards/observe"
CANONICAL_STD_GENERAL_REL = f"{CANONICAL_STANDARDS_DIR_REL}/std_observe_general.json"
CANONICAL_STD_SEARCH_REL = f"{CANONICAL_STANDARDS_DIR_REL}/std_observe_search.json"
CANONICAL_PROMPTS_MD_REL = f"{CANONICAL_STANDARDS_DIR_REL}/observe_plan_prompts.md"
CANONICAL_PROMPTS_JSON_REL = f"{CANONICAL_STANDARDS_DIR_REL}/observe_prompts.json"
CANONICAL_TEMPLATES_REL = f"{CANONICAL_STANDARDS_DIR_REL}/templates"

CANONICAL_DERIVED_OBSERVE_DIR_REL = "codex/derived/observe"
CANONICAL_TREE_MD_REL = f"{CANONICAL_DERIVED_OBSERVE_DIR_REL}/tree.md"
CANONICAL_TREE_MANIFEST_REL = f"{CANONICAL_DERIVED_OBSERVE_DIR_REL}/tree_manifest.json"

CANONICAL_OBSERVE_GUIDE_REL = "codex/doctrine/skills/kernel/observe.md"
CANONICAL_OBSERVE_PATTERNS_GUIDE_REL = "codex/doctrine/skills/kernel/observe_patterns.md"
CANONICAL_OBSERVE_AUTHORING_REL = "codex/doctrine/skills/kernel/observe_plan_authoring.md"
CANONICAL_IMPLEMENT_GUIDE_REL = "codex/doctrine/skills/kernel/implement.md"
CANONICAL_RUNTIME_CHANGE_PROTOCOL_REL = "codex/doctrine/operations/runtime_change_protocol.md"
CANONICAL_ETF_REFERENCE_REL = "codex/doctrine/references/etf_universe.md"
OBSERVE_SESSIONS_DIR_REL = "obsidian/meta/observe_sessions"

OBSERVE_TREE_RUNTIME_RELS = (
    "tools/meta/apply.py",
    "tools/meta/apply/run_observe_plan.py",
    "tools/meta/builder.py",
    "tools/meta/config_lint.py",
    "tools/meta/miner.py",
    "tools/meta/patcher.py",
    APPLY_DIR_REL,
    OBSERVE_PLAN_REL,
    OBSERVE_RESULT_REL,
    OBSERVE_HISTORY_JSON_REL,
    OBSERVE_HISTORY_MD_REL,
    f"{OBSERVE_HISTORY_DIR_REL}/entries",
    f"{OBSERVE_HISTORY_DIR_REL}/prompts",
    OBSERVE_DUMPS_REL,
)

OBSERVE_TREE_CANONICAL_DOC_RELS = (
    CANONICAL_STD_GENERAL_REL,
    CANONICAL_STD_SEARCH_REL,
    CANONICAL_PROMPTS_MD_REL,
    CANONICAL_PROMPTS_JSON_REL,
    CANONICAL_TEMPLATES_REL,
    CANONICAL_OBSERVE_GUIDE_REL,
    CANONICAL_OBSERVE_PATTERNS_GUIDE_REL,
    CANONICAL_OBSERVE_AUTHORING_REL,
    CANONICAL_IMPLEMENT_GUIDE_REL,
    CANONICAL_RUNTIME_CHANGE_PROTOCOL_REL,
    CANONICAL_ETF_REFERENCE_REL,
    CANONICAL_TREE_MD_REL,
    CANONICAL_TREE_MANIFEST_REL,
)


@dataclass(frozen=True)
class ObserveAssetPaths:
    """[ROLE]
    - Teleology: Carry all resolved observe/apply filesystem paths for one repository root as a single immutable bundle.
    - Ownership: Owns resolved Path fields for every canonical runtime, standards, derived, and doctrine observe/apply asset location.
    - Mutability: Immutable — frozen dataclass; all fields set at construction.
    - Concurrency: Safe for concurrent reads; no mutable state.
    """
    root: Path
    apply_dir: Path
    observe_plan: Path
    observe_result: Path
    observe_dumps: Path
    observe_history_dir: Path
    observe_history_json: Path
    observe_history_md: Path
    apply_plan: Path
    apply_result: Path
    apply_history: Path
    scratchpad_prompt: Path
    observe_plan_suggestion: Path
    observe_sessions_dir: Path
    std_observe_session: Path
    standards_dir: Path
    std_general: Path
    std_search: Path
    prompts_md: Path
    prompts_json: Path
    templates_dir: Path
    derived_dir: Path
    tree_md: Path
    tree_manifest: Path
    observe_guide: Path
    observe_patterns_guide: Path
    observe_authoring_guide: Path
    implement_guide: Path
    runtime_change_protocol: Path
    etf_reference: Path


def observe_asset_paths(root: Path) -> ObserveAssetPaths:
    """
    [ACTION]
    - Teleology: Materialize the canonical observe/apply path registry for one repository root.
    - Mechanism: Resolve the supplied root once and populate an immutable ObserveAssetPaths dataclass from the module's repo-relative constants.
    - Guarantee: Returns an ObserveAssetPaths instance whose fields all point under the resolved repository root.
    - Fails: None.
    - When-needed: Open when kernel, server, or session code needs the exact resolved observe/apply asset locations for one repo root.
    - Escalates-to: system/lib/kernel/state.py; system/lib/observe_session_contracts.py; tools/meta/apply/observe_session.py
    """
    root = Path(root).resolve()
    return ObserveAssetPaths(
        root=root,
        apply_dir=root / APPLY_DIR_REL,
        observe_plan=root / OBSERVE_PLAN_REL,
        observe_result=root / OBSERVE_RESULT_REL,
        observe_dumps=root / OBSERVE_DUMPS_REL,
        observe_history_dir=root / OBSERVE_HISTORY_DIR_REL,
        observe_history_json=root / OBSERVE_HISTORY_JSON_REL,
        observe_history_md=root / OBSERVE_HISTORY_MD_REL,
        apply_plan=root / APPLY_PLAN_REL,
        apply_result=root / APPLY_RESULT_REL,
        apply_history=root / APPLY_HISTORY_REL,
        scratchpad_prompt=root / SCRATCHPAD_PROMPT_REL,
        observe_plan_suggestion=root / OBSERVE_PLAN_SUGGESTION_REL,
        observe_sessions_dir=root / OBSERVE_SESSIONS_DIR_REL,
        std_observe_session=root / CORE_STD_OBSERVE_SESSION_REL,
        standards_dir=root / CANONICAL_STANDARDS_DIR_REL,
        std_general=root / CANONICAL_STD_GENERAL_REL,
        std_search=root / CANONICAL_STD_SEARCH_REL,
        prompts_md=root / CANONICAL_PROMPTS_MD_REL,
        prompts_json=root / CANONICAL_PROMPTS_JSON_REL,
        templates_dir=root / CANONICAL_TEMPLATES_REL,
        derived_dir=root / CANONICAL_DERIVED_OBSERVE_DIR_REL,
        tree_md=root / CANONICAL_TREE_MD_REL,
        tree_manifest=root / CANONICAL_TREE_MANIFEST_REL,
        observe_guide=root / CANONICAL_OBSERVE_GUIDE_REL,
        observe_patterns_guide=root / CANONICAL_OBSERVE_PATTERNS_GUIDE_REL,
        observe_authoring_guide=root / CANONICAL_OBSERVE_AUTHORING_REL,
        implement_guide=root / CANONICAL_IMPLEMENT_GUIDE_REL,
        runtime_change_protocol=root / CANONICAL_RUNTIME_CHANGE_PROTOCOL_REL,
        etf_reference=root / CANONICAL_ETF_REFERENCE_REL,
    )
