"""
Forward-integration runtime policy for WorkItem/Type A agents.

The policy is intentionally not a clean-tree gate. It classifies dirty local
reality, blocks only information-loss or authority-corruption risks, and lets
coherent scoped work continue in a shared dirty checkout.
"""
from __future__ import annotations

from functools import lru_cache
import os
import shlex
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib import generated_projection_registry, shared_worktree_guard


SCHEMA_VERSION = "forward_integration_policy_v1"

MODE_FORWARD_INTEGRATION = "forward_integration"
MODE_STRICT_VALIDATION = "strict_validation"
MODE_INSPECTION_REQUIRED = "inspection_required"
MODE_DESTRUCTIVE_OVERRIDE_REQUIRED = "destructive_override_required"
MODE_OPERATOR_ACCELERATION = "operator_acceleration"

DIRTY_PROMPT_TRACE = "dirty_prompt_trace"
DIRTY_GENERATED_PROJECTION = "dirty_generated_projection"
DIRTY_RAW_SEED_PROJECTION = "dirty_raw_seed_projection"
DIRTY_WORK_LEDGER_PROJECTION = "dirty_work_ledger_projection"
DIRTY_FRONTEND_WORK = "dirty_frontend_work"
DIRTY_PHASE_RUNTIME = "dirty_phase_runtime"
DIRTY_RUN_ARTIFACT = "dirty_run_artifact"
DIRTY_AUTHORITY_FILE = "dirty_authority_file"
DIRTY_PROVIDER_PROVENANCE = "dirty_provider_provenance"
DIRTY_UNKNOWN = "dirty_unknown"
DIRTY_LARGE_OR_BINARY_UNKNOWN = "dirty_large_or_binary_unknown"

LARGE_UNKNOWN_BYTES = 1_000_000
DIRTY_PATH_SAMPLE_LIMIT = 80

DERIVED_PROJECTION_SLICE_CONTRACT: dict[str, Any] = {
    "schema_version": "derived_projection_slice_contract_v1",
    "purpose": (
        "Allow a narrow derived-view target to land during broader source drift without "
        "baking a half-edited source snapshot into generated artifacts."
    ),
    "allowed_when": [
        "the target is a registered generated projection or owner-tool target",
        "the slice is rebuilt from a clean committed kernel or an immutable source snapshot",
        "dirty or concurrently owned source inputs are not reread by the slice",
        "the diff is proven to touch only the intended derived fields or records",
        "canonical kernel fingerprints remain unchanged, or any change is justified by an owned kernel update",
        "the closeout distinguishes owned derived-view drift from wider source-coupling drift reported by full checks",
    ],
    "required_receipt_fields": [
        "projection_owner_id",
        "target_paths",
        "canonical_kernel_path",
        "canonical_kernel_ref",
        "source_coupling_status",
        "dirty_source_inputs_excluded",
        "diff_invariant",
        "fingerprint_status",
        "validation_commands",
        "full_rebuild_or_check_status",
        "foreign_or_blocked_drift_boundary",
    ],
    "forbidden_when": [
        "the target itself is source authority",
        "the derived view must incorporate another owner's uncommitted edits",
        "full regeneration would rewrite source-coupled artifacts from dirty inputs",
        "the diff contains unproven non-slice changes",
    ],
    "closeout_rule": (
        "Report the landed target as a derived slice, not as a clean full projection rebuild. "
        "Any wider drift remains with the source owner, builder owner, or a captured re-entry condition."
    ),
}


def _projection_owner_repair_command(owner_id: str) -> str:
    owner = generated_projection_registry.get_projection_owner(owner_id)
    return " ".join(owner.repair_command)


CLASS_POLICIES: dict[str, dict[str, Any]] = {
    DIRTY_PROMPT_TRACE: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "preserve_trace_continue",
        "description": "Prompt-shelf and operator-facing prompt traces are nonblocking provenance until adopted into authority.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": False,
    },
    DIRTY_GENERATED_PROJECTION: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "projection_owner_tool_only",
        "description": "Generated projection dirt is normal; do not hand-edit or regenerate over it without owner-tool intent.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": False,
        "owner_tool_only": True,
    },
    DIRTY_RAW_SEED_PROJECTION: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "preserve_raw_seed_continue",
        "description": "Raw-seed family projection dirt is live system state; preserve it unless explicitly using its owner lane.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": True,
    },
    DIRTY_WORK_LEDGER_PROJECTION: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "preserve_work_ledger_projection_continue",
        "description": "Work Ledger indexes/projections are nonblocking; Work Ledger append/runtime authority remains strict.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": False,
    },
    DIRTY_FRONTEND_WORK: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "avoid_unless_claimed",
        "description": "Frontend and screenshot work is often parallel exploratory state; avoid unless claimed.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": False,
    },
    DIRTY_PHASE_RUNTIME: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "adopt_or_preserve_runtime_state",
        "description": "Phase/subphase runtime files are live state; classify and continue unless the target action would overwrite them.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": False,
    },
    DIRTY_RUN_ARTIFACT: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "preserve_or_claim_run_artifact",
        "description": "state/runs artifacts are runtime receipts, not generated projections; preserve unrelated dirt and validate if adopted.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": True,
    },
    DIRTY_AUTHORITY_FILE: {
        "mode": MODE_STRICT_VALIDATION,
        "default_action": "strict_validation_if_touched",
        "description": "Authority-bearing files require strict validation when touched, but unrelated dirty authority does not stop scoped work.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": True,
    },
    DIRTY_PROVIDER_PROVENANCE: {
        "mode": MODE_FORWARD_INTEGRATION,
        "default_action": "preserve_provider_receipt_continue",
        "description": "Provider outputs are nonblocking provenance until adopted into validated receipt/event authority.",
        "hard_blocker_if_target": False,
        "strict_validation_if_touched": True,
    },
    DIRTY_UNKNOWN: {
        "mode": MODE_INSPECTION_REQUIRED,
        "default_action": "inspect_before_target_mutation",
        "description": "Unknown dirty targets may hide operator/agent work; inspect before mutating them.",
        "hard_blocker_if_target": True,
        "strict_validation_if_touched": False,
    },
    DIRTY_LARGE_OR_BINARY_UNKNOWN: {
        "mode": MODE_INSPECTION_REQUIRED,
        "default_action": "inspect_before_target_mutation",
        "description": "Large or binary unknown targets are hard to diff and can hide lossy replacement risk.",
        "hard_blocker_if_target": True,
        "strict_validation_if_touched": False,
    },
}

AUTHORITY_SURFACE_PATTERNS = (
    "kernel.py",
    "AGENTS.md",
    "AGENTS.override.md",
    "CODEX.md",
    "CLAUDE.md",
    "state/task_ledger/events.jsonl",
    "state/task_ledger/ledger.json",
    "state/task_ledger/sign_offs.json",
    "state/task_ledger/discovery_receipts/",
    "state/work_ledger/events.jsonl",
    "state/work_ledger/runtime_status.json",
    "state/prompt_ledger/events.jsonl",
    "state/provider_receipts/",
    "codex/standards/",
    "codex/doctrine/agent_bootstrap.json",
    "system/lib/",
    "tools/meta/",
)

GENERATED_PROJECTION_PREFIXES = (
    "codex/doctrine/paper_modules/_",
    "codex/derived/",
    "codex/navigation_hologram/",
    "codex/hologram/",
    "state/task_ledger/views/",
    "state/prompt_ledger/views/",
    "state/architectural_projection/",
    "system/server/ui/src/api/generated/",
)

WORK_LEDGER_PROJECTION_PREFIXES = (
    "codex/ledger/",
    "state/work_ledger/views/",
    "state/work_ledger/index",
)

PROMPT_TRACE_PREFIXES = (
    "obsidian/prompt_shelf/usage/",
    "obsidian/prompt_shelf/items/",
    "state/prompt_shelf/",
)

RAW_SEED_PREFIXES = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed",
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed",
)

PHASE_RUNTIME_TOKENS = (
    "/pipeline_",
    "/continuation_packet",
    "/autonomous_seed",
    "/phase_memory",
    "/phase_harbor",
)

FRONTEND_PREFIXES = (
    "system/server/ui/",
    "frontend/",
    "screenshots/",
    "state/screenshots/",
)

PROVIDER_PREFIXES = (
    "state/provider_receipts/",
    "state/provider_outputs/",
    "state/model_receipts/",
)

RUN_ARTIFACT_PREFIXES = (
    "state/runs/",
)

OWNER_TOOL_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "pattern": "codex/doctrine/paper_modules/_*.json",
        "owner_tool": "./repo-python tools/meta/factory/build_paper_module_index.py",
        "authority": "codex/doctrine/paper_modules/*.md",
        "projection": True,
    },
    {
        "pattern": "codex/doctrine/paper_modules/README.md",
        "owner_tool": "./repo-python tools/meta/factory/build_paper_module_index.py",
        "authority": "codex/doctrine/paper_modules/*.md",
        "projection": True,
    },
    {
        "pattern": "state/task_ledger/views/*.json",
        "owner_tool": _projection_owner_repair_command("task_ledger_projection"),
        "authority": "state/task_ledger/events.jsonl",
        "projection": True,
    },
    {
        "pattern": "state/task_ledger/ledger.json",
        "owner_tool": _projection_owner_repair_command("task_ledger_projection"),
        "authority": "state/task_ledger/events.jsonl",
        "projection": True,
    },
    {
        "pattern": "state/task_ledger/sign_offs.json",
        "owner_tool": _projection_owner_repair_command("task_ledger_projection"),
        "authority": "state/task_ledger/events.jsonl",
        "projection": True,
    },
    {
        "pattern": "state/prompt_ledger/ledger.json",
        "owner_tool": "./repo-python tools/meta/observability/prompt_ledger.py rebuild",
        "authority": "state/prompt_ledger/events.jsonl",
        "projection": True,
    },
    {
        "pattern": "state/prompt_ledger/views/*.json",
        "owner_tool": "./repo-python tools/meta/observability/prompt_ledger.py rebuild",
        "authority": "state/prompt_ledger/events.jsonl",
        "projection": True,
    },
    {
        "pattern": "codex/ledger/*/work_ledger_index.json",
        "owner_tool": _projection_owner_repair_command("work_ledger_index_projection"),
        "authority": "codex/ledger/*/work_ledger.jsonl",
        "projection": True,
    },
    {
        "pattern": "system/server/ui/src/api/generated/*",
        "owner_tool": "OpenAPI client generator for Station API",
        "authority": "system/server/main.py OpenAPI schema",
        "projection": True,
    },
    {
        "pattern": "AGENTS.md",
        "owner_tool": "./repo-python tools/meta/factory/build_agent_bootstrap_projection.py",
        "authority": "codex/doctrine/agent_bootstrap.json",
        "projection": True,
    },
    {
        "pattern": "CODEX.md",
        "owner_tool": "./repo-python tools/meta/factory/build_agent_bootstrap_projection.py",
        "authority": "codex/doctrine/agent_bootstrap.json",
        "projection": True,
    },
    {
        "pattern": "CLAUDE.md",
        "owner_tool": "./repo-python tools/meta/factory/build_agent_bootstrap_projection.py",
        "authority": "codex/doctrine/agent_bootstrap.json",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/content-graph.json",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "microcosm-substrate/ plus tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/content-manifest.json",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "sites/microcosm/content-graph.json",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/projection-status.json",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "sites/microcosm/content-graph.json",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/assets/search-index.js",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "sites/microcosm/content-graph.json",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/assets/site-packet.js",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "sites/microcosm/content-graph.json",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/docs/*.html",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "sites/microcosm/content-graph.json",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/docs/architecture-graph-scene.json",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "microcosm-substrate/core/architecture_kernel.json",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/_headers",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/_redirects",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/robots.txt",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/security.txt",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/404.html",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/.well-known/security.txt",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
    {
        "pattern": "sites/microcosm/sitemap.xml",
        "owner_tool": _projection_owner_repair_command("microcosm_public_site_projection"),
        "authority": "tools/meta/dissemination/build_microcosm_public_site.py",
        "projection": True,
    },
)


def normalize_repo_path(repo_root: Path, path: str | os.PathLike[str]) -> str:
    """Return a repo-relative POSIX path when possible."""
    raw = str(path or "").strip()
    if not raw:
        return ""
    if raw.startswith('"') and raw.endswith('"'):
        try:
            parts = shlex.split(raw)
            if parts:
                raw = parts[0]
        except ValueError:
            raw = raw[1:-1]
    raw = raw.replace("\\", "/")
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            raw = candidate.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            raw = candidate.as_posix()
    if raw.startswith("./"):
        raw = raw[2:]
    return raw.strip("/")


def owner_tool_entries_for_path(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    rel = str(path or "").strip("/")
    return [
        dict(entry)
        for entry in OWNER_TOOL_REGISTRY
        if fnmatch(rel, str(entry.get("pattern") or ""))
    ]


def _has_registered_projection_owner(path: str) -> bool:
    return any(entry.get("projection") for entry in owner_tool_entries_for_path(path))


@lru_cache(maxsize=32768)
def _scope_parts(value: str) -> tuple[str, ...]:
    token = str(value or "").strip("/")
    if not token:
        return ()
    return tuple(part for part in token.split("/") if part)


def path_scope_overlaps(left: str, right: str) -> bool:
    left_parts = _scope_parts(str(left or ""))
    right_parts = _scope_parts(str(right or ""))
    if not left_parts or not right_parts:
        return False
    if left_parts == right_parts:
        return True
    if len(left_parts) < len(right_parts):
        return right_parts[: len(left_parts)] == left_parts
    return left_parts[: len(right_parts)] == right_parts


def is_authority_surface(path: str) -> bool:
    rel = str(path or "").strip("/")
    if not rel:
        return False
    if rel.endswith(".py") and rel.startswith(("system/", "tools/")):
        return True
    if rel.endswith(".json") and rel.startswith("codex/standards/"):
        return True
    if rel.endswith(".jsonl") and (
        rel.startswith("state/task_ledger/")
        or rel.startswith("state/prompt_ledger/")
        or rel.startswith("state/provider_receipts/")
    ):
        return True
    if rel.endswith(("raw_seed.json", "raw_seed.md", "agent_seed.json", "agent_seed.md")):
        return True
    return any(rel == pattern.rstrip("/") or rel.startswith(pattern) for pattern in AUTHORITY_SURFACE_PATTERNS)


def _path_exists_large_or_binary(repo_root: Path, rel_path: str) -> bool:
    path = repo_root / rel_path
    if not path.exists() or path.is_dir():
        return False
    try:
        if path.stat().st_size > LARGE_UNKNOWN_BYTES:
            return True
        with path.open("rb") as handle:
            chunk = handle.read(4096)
    except OSError:
        return False
    return b"\0" in chunk


def _class_for_path(rel_path: str, *, repo_root: Path | None = None) -> str:
    rel = str(rel_path or "").strip("/")
    if not rel:
        return DIRTY_UNKNOWN
    if is_authority_surface(rel):
        return DIRTY_AUTHORITY_FILE
    if rel.startswith(PROVIDER_PREFIXES):
        return DIRTY_PROVIDER_PROVENANCE
    if rel == "state/prompt_ledger/.prompt_ledger.lock":
        return DIRTY_PHASE_RUNTIME
    if rel == "state/prompt_ledger/ledger.json":
        return DIRTY_GENERATED_PROJECTION
    if rel.startswith(PROMPT_TRACE_PREFIXES) or "prompt_shelf" in rel or "uppropagation" in rel:
        return DIRTY_PROMPT_TRACE
    if rel.startswith(RAW_SEED_PREFIXES):
        return DIRTY_RAW_SEED_PROJECTION
    if rel.startswith(WORK_LEDGER_PROJECTION_PREFIXES) or rel.endswith("work_ledger_index.json"):
        return DIRTY_WORK_LEDGER_PROJECTION
    if rel.startswith(RUN_ARTIFACT_PREFIXES):
        return DIRTY_RUN_ARTIFACT
    if _has_registered_projection_owner(rel):
        return DIRTY_GENERATED_PROJECTION
    if rel.startswith(GENERATED_PROJECTION_PREFIXES) or rel.endswith(("_index.json", "_validation_report.json")):
        return DIRTY_GENERATED_PROJECTION
    if rel.startswith(FRONTEND_PREFIXES) or rel.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return DIRTY_FRONTEND_WORK
    if rel.startswith("obsidian/") and any(token in rel for token in PHASE_RUNTIME_TOKENS):
        return DIRTY_PHASE_RUNTIME
    if repo_root is not None and _path_exists_large_or_binary(repo_root, rel):
        return DIRTY_LARGE_OR_BINARY_UNKNOWN
    return DIRTY_UNKNOWN


def classify_dirty_path(path: str | os.PathLike[str], *, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path.cwd()
    rel = normalize_repo_path(root, path)
    surface_class = _class_for_path(rel, repo_root=root)
    policy = dict(CLASS_POLICIES[surface_class])
    return {
        "path": rel,
        "surface_class": surface_class,
        "mode": policy.get("mode"),
        "default_action": policy.get("default_action"),
        "description": policy.get("description"),
        "hard_blocker_if_target": bool(policy.get("hard_blocker_if_target")),
        "strict_validation_if_touched": bool(policy.get("strict_validation_if_touched"))
        or is_authority_surface(rel),
        "owner_tool_only": bool(policy.get("owner_tool_only")),
        "owner_tools": owner_tool_entries_for_path(rel),
    }


def _dirty_paths(repo_root: Path, override: Sequence[str] | None) -> list[str]:
    if override is not None:
        return [normalize_repo_path(repo_root, path) for path in override if str(path or "").strip()]
    return [
        normalize_repo_path(repo_root, path)
        for path in shared_worktree_guard.read_dirty_paths(repo_root)
        if str(path or "").strip()
    ]


def _override_accepts_loss_risk(receipt: Mapping[str, Any] | None) -> bool:
    if not receipt:
        return False
    return bool(receipt.get("operator_acceptance") or receipt.get("accept_overwrite_risk"))


def build_forward_integration_policy(
    repo_root: Path,
    *,
    target_paths: Sequence[str] | None = None,
    owner_tool_paths: Sequence[str] | None = None,
    dirty_paths: Sequence[str] | None = None,
    attempted_action: str | None = None,
    destructive_override_receipt: Mapping[str, Any] | None = None,
    claim_collisions: Sequence[Mapping[str, Any]] | None = None,
    require_exclusive: bool = False,
) -> dict[str, Any]:
    """Classify dirty state and decide whether scoped work may continue."""
    root = repo_root.resolve()
    dirty = _dirty_paths(root, dirty_paths)
    normalized_targets = [
        normalize_repo_path(root, path)
        for path in (target_paths or [])
        if str(path or "").strip()
    ]
    owner_tool_target_paths = {
        normalize_repo_path(root, path)
        for path in (owner_tool_paths or [])
        if str(path or "").strip()
    }
    dirty_set = set(dirty)

    classified = [classify_dirty_path(path, repo_root=root) for path in dirty]
    class_counts: dict[str, int] = {}
    for row in classified:
        cls = str(row["surface_class"])
        class_counts[cls] = class_counts.get(cls, 0) + 1

    target_policies: dict[str, dict[str, Any]] = {}
    blockers: list[dict[str, Any]] = []
    strict_validation_paths: list[str] = []
    inspection_required_paths: list[str] = []
    warnings: list[str] = []

    for target in normalized_targets:
        target_classification = classify_dirty_path(target, repo_root=root)
        is_dirty_target = target in dirty_set or any(path_scope_overlaps(target, dirty_path) for dirty_path in dirty)
        owner_tool_or_adoption_receipt = any(
            path_scope_overlaps(owner_path, target) or path_scope_overlaps(target, owner_path)
            for owner_path in owner_tool_target_paths
        )
        target_classification["is_dirty_target"] = is_dirty_target
        target_classification["owner_tool_or_adoption_receipt"] = owner_tool_or_adoption_receipt
        target_classification["owner_tool_or_adoption_receipt_required"] = bool(
            is_dirty_target and target_classification.get("owner_tool_only") and not owner_tool_or_adoption_receipt
        )
        target_policies[target] = target_classification
        if target_classification.get("strict_validation_if_touched"):
            strict_validation_paths.append(target)
        if is_dirty_target and target_classification.get("hard_blocker_if_target"):
            inspection_required_paths.append(target)
            blockers.append(
                {
                    "kind": "dirty_unknown_target"
                    if target_classification["surface_class"] == DIRTY_UNKNOWN
                    else "dirty_large_or_binary_unknown_target",
                    "path": target,
                    "mode": MODE_INSPECTION_REQUIRED,
                    "reason": target_classification.get("description"),
                }
            )
        if target_classification["owner_tool_or_adoption_receipt_required"]:
            owner_tools = target_classification.get("owner_tools") or []
            inspection_required_paths.append(target)
            blockers.append(
                {
                    "kind": "generated_projection_target_requires_owner_tool_or_adoption_receipt",
                    "path": target,
                    "mode": MODE_INSPECTION_REQUIRED,
                    "owner_tools": owner_tools,
                    "reason": "dirty generated projections may only be replaced through their owner tool or an explicit adoption receipt",
                }
            )
        elif is_dirty_target and target_classification.get("owner_tool_only"):
            warnings.append(f"{target}: generated projection target covered by owner-tool/adoption receipt")

    destructive_git_risks = (
        shared_worktree_guard.detect_git_risks_in_text(attempted_action)
        if attempted_action
        else []
    )
    if destructive_git_risks and dirty and not _override_accepts_loss_risk(destructive_override_receipt):
        blockers.append(
            {
                "kind": "destructive_overwrite_risk",
                "mode": MODE_DESTRUCTIVE_OVERRIDE_REQUIRED,
                "risk_count": len(destructive_git_risks),
                "risks": destructive_git_risks,
                "reason": "destructive git/file actions are blocked in a dirty tree without an explicit loss-risk receipt",
            }
        )

    collisions = [dict(item) for item in (claim_collisions or []) if isinstance(item, Mapping)]
    if require_exclusive and collisions:
        blockers.append(
            {
                "kind": "exclusive_claim_collision",
                "mode": MODE_STRICT_VALIDATION,
                "collision_count": len(collisions),
                "collisions": collisions,
                "reason": "--require-exclusive was requested and overlapping Work Ledger claims are active",
            }
        )

    if dirty and not blockers:
        warnings.append(
            f"{len(dirty)} dirty paths classified; unrelated dirty files are not blockers in forward_integration mode"
        )

    blocked_kinds = [str(item.get("kind") or "unknown_blocker") for item in blockers]
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": MODE_FORWARD_INTEGRATION,
        "dirty_tree_allowed": True,
        "destructive_overwrite_allowed": False,
        "safe_to_continue": not blockers,
        "blocked_only_by": blocked_kinds,
        "blockers": blockers,
        "warnings": warnings,
        "dirty_path_count": len(dirty),
        "dirty_surface_classes": dict(sorted(class_counts.items())),
        "dirty_paths_sample": classified[:DIRTY_PATH_SAMPLE_LIMIT],
        "target_paths": normalized_targets,
        "target_path_policy": target_policies,
        "strict_validation_required_paths": sorted(set(strict_validation_paths)),
        "inspection_required_paths": sorted(set(inspection_required_paths)),
        "owner_tool_registry": list(OWNER_TOOL_REGISTRY),
        "destructive_git_risks": destructive_git_risks,
        "claim_collisions": collisions,
        "rules": {
            "default": "forward_integration",
            "dirty_tree": "allowed_after_classification",
            "hard_stop": "potential_information_loss_or_authority_corruption",
            "strict_validation": "authority_bearing_surfaces_if_touched",
            "recovery_model": "forward_repair_not_rollback",
            "derived_projection_slice": "allowed_only_with_slice_contract_receipt",
        },
        "derived_projection_slice_contract": DERIVED_PROJECTION_SLICE_CONTRACT,
    }
