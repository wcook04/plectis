"""Plan the next concrete closeout action from the git closeout packet."""

from __future__ import annotations

import ast
import json
import hashlib
import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from system.lib import work_ledger_runtime
from system.lib.git_state_snapshot import (
    build_closeout_git_state_conditions,
    compact_closeout_git_state_conditions,
)
from tools.meta.control import mission_closeout_verdict
from tools.meta.control.gate_spender import (
    GateContext as _GateSpenderContext,
    OwnerStatus as _GateSpenderOwnerStatus,
    select_route as _select_gate_spender_route,
)


SCHEMA = "closeout_executor_plan_v0"
RUN_ONE_SCHEMA = "closeout_executor_run_one_receipt_v0"
RUN_BURST_SCHEMA = "closeout_executor_run_burst_receipt_v0"
HYGIENE_SCHEMA = "closeout_executor_hygiene_receipt_v0"
STOP_INTEGRITY_SCHEMA = "closeout_stop_state_integrity_v0"
MISSION_TRACE_CONTEXT_SCHEMA = "mission_trace_context_v0"
UI_EFFECT_BLOCKER_REFS = (
    "cap_quick_ui_effect_receipt_blocked_by_existing_ty_92842ca8ed82",
)
UI_EFFECT_BLOCKER_TAGS = ("closeout_executor", "ui_effect_receipt", "build_blocker")
TS_ERROR_PATH_RE = re.compile(r"^(src/[^(:]+?\.(?:ts|tsx|js|jsx))\(\d+,\d+\): error ", re.MULTILINE)

GENERATED_PREFIXES = (
    "codex/ledger/",
    "docs/dissemination/generated/",
    "sites/",
    "state/",
)
SYSTEM_ATLAS_GENERATED_DOC_PREFIX = "docs/system_atlas/"
SOURCE_PREFIXES = (
    ".claude/follow_on/",
    ".claude/hooks/",
    ".codex/follow_on/",
    "codex/doctrine/",
    "codex/standards/",
    "docs/",
    "system/lib/",
    "system/server/tests/",
    "system/server/ui/src/",
    "microcosm-substrate/src/",
    "microcosm-substrate/tests/",
    "self-indexing-cognitive-substrate/src/",
    "self-indexing-cognitive-substrate/tests/",
    "tools/meta/",
)
SOURCE_EXACT_PATHS = (
    "AGENTS.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    "CODEX.md",
    "checkpoint",
    "kernel.py",
    "reactions.yaml",
    "run_git.py",
)
TEST_PREFIXES = (
    "system/server/tests/",
    "microcosm-substrate/tests/",
    "self-indexing-cognitive-substrate/tests/",
)
AMBIENT_WORKSPACE_PREFIXES = (
    "obsidian/.obsidian/",
)
AUTONOMOUS_SEED_STATE_PREFIX = "state/meta_missions/type_a_autonomous_seed_loop/seeds/"
ROOT_AUTONOMOUS_SEED_PREFIX = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, "
    "and Fresh Execution Spine/autonomous_seed."
)
ROOT_AUTONOMOUS_SEED_JSON = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, "
    "and Fresh Execution Spine/autonomous_seed.json"
)
OBSERVABILITY_RUNTIME_STATE_PREFIX = "state/observability/"
RUNTIME_ARTIFACT_LIFECYCLE_PREFIXES = (
    "state/runs/",
)
PHASE_PIPELINE_RUNTIME_FILENAMES = {
    "continuation_packet.json",
    "meta_ledger.json",
    "pipeline_attention.json",
    "pipeline_attention.md",
    "pipeline_resume.json",
    "pipeline_resume.md",
    "pipeline_state.json",
    "raw_seed_digest.json",
    "system_view.json",
    "task_backlog.json",
}
MICROCOSM_RUNTIME_RECEIPT_PREFIX = "microcosm-substrate/receipts/runtime_shell/"
RECEIPT_ARTIFACT_PREFIX = "receipts/"
ANNEX_SYNC_DIGEST_FILENAMES = {
    "annex_sync_digest.json",
    "annex_sync_digest.md",
    "annex_sync_digest_run_state.json",
}
RUNTIME_ARTIFACT_LIFECYCLE_COMMAND = (
    "./repo-python tools/meta/control/mission_transaction_preflight.py --runtime-artifact-lifecycle"
)
ANNEX_SYNC_DIGEST_COMMAND = "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 8"
PHASE_PIPELINE_RUNTIME_COMMAND = (
    "./repo-python tools/meta/control/phase_convergence_doctor.py --compact"
)
MICROCOSM_RUNTIME_RECEIPT_COMMAND = (
    "cd microcosm-substrate && PYTHONPATH=src .venv/bin/python -m microcosm_core.runtime_shell --help"
)
GENERATED_DIRT_OWNER_REVIEW_COMMAND = (
    "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact"
)
TASK_LEDGER_SOURCE_AUTHORITY_PATHS = (
    "state/task_ledger/events.jsonl",
    "state/task_ledger/events_audit.jsonl",
    "state/mission_blackboard/board.json",
)
TASK_LEDGER_SOURCE_AUTHORITY_GLOBS = (
    "codex/ledger/*/work_ledger.jsonl",
    "codex/ledger/*/work_ledger_index.json",
    "codex/ledger/*/work_ledger_index.*.json",
)
TASK_LEDGER_WRITER_TOKENS = (
    "quick-capture",
    "rebuild",
    "sign-off",
    "claim",
    "promote",
    "note",
    "triage",
    "retire",
    "execution-receipt",
)
MISSION_TRACE_ENV_ALIASES = {
    "mission_trace_id": ("AIW_MISSION_TRACE_ID", "MISSION_TRACE_ID", "TRACE_ID"),
    "mission_id": ("AIW_MISSION_ID", "MISSION_ID"),
    "subject_id": ("AIW_SUBJECT_ID", "TASK_LEDGER_SUBJECT_ID", "SUBJECT_ID"),
    "episode_id": ("AIW_EPISODE_ID", "EPISODE_ID"),
    "phase_id": ("AIW_PHASE_ID", "PHASE_ID"),
    "wave_id": ("AIW_WAVE_ID", "WAVE_ID"),
    "parent_step_id": ("AIW_PARENT_STEP_ID", "MISSION_PARENT_STEP_ID", "PARENT_STEP_ID"),
    "prompt_run_id": ("AIW_PROMPT_RUN_ID", "TYPE_B_PROMPT_RUN_ID", "PROMPT_RUN_ID"),
    "prompt_trace_id": ("AIW_PROMPT_TRACE_ID", "PROMPT_TRACE_ID"),
    "outbox_row_id": ("AIW_OUTBOX_ROW_ID", "OUTBOX_ROW_ID"),
    "provider_thread_id": ("AIW_PROVIDER_THREAD_ID", "PROVIDER_THREAD_ID"),
    "agent_run_id": ("AIW_AGENT_RUN_ID", "AGENT_RUN_ID", "CODEX_SESSION_ID"),
}


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _env_context_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for field, aliases in MISSION_TRACE_ENV_ALIASES.items():
        value = _first_text(*(os.environ.get(alias) for alias in aliases))
        if value:
            values[field] = value
    return values


def _cluster_id_from_action(action: Mapping[str, Any]) -> str | None:
    cluster = action.get("cluster") if isinstance(action.get("cluster"), Mapping) else {}
    return _first_text(cluster.get("cluster_id"), action.get("cluster_id"))


def _uniq_text(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            rows.append(text)
            seen.add(text)
    return rows


def _receipt_affected_paths(receipt: Mapping[str, Any]) -> list[str]:
    values: list[Any] = []
    for key in ("paths", "path", "generated_paths", "untracked_paths"):
        value = receipt.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            values.extend(value)
        else:
            values.append(value)
    blocked = receipt.get("blocked_worktree")
    if isinstance(blocked, Mapping):
        values.append(blocked.get("path"))
    for row in receipt.get("staged_external_paths") or []:
        if isinstance(row, Mapping):
            values.append(row.get("path"))
    integrity = receipt.get("closeout_stop_integrity")
    if isinstance(integrity, Mapping):
        for row in integrity.get("initial_staged_residue_paths") or []:
            if isinstance(row, Mapping):
                values.append(row.get("path"))
        for path in integrity.get("staged_paths_introduced_during_action") or []:
            values.append(path)
    return _uniq_text(values)


def _receipt_commits(receipt: Mapping[str, Any]) -> list[str]:
    values: list[Any] = []
    if isinstance(receipt.get("commits"), Sequence) and not isinstance(receipt.get("commits"), (str, bytes, bytearray)):
        values.extend(receipt.get("commits") or [])
    values.append(receipt.get("commit"))
    return _uniq_text(values)


def _receipt_nested_blocker(receipt: Mapping[str, Any]) -> dict[str, Any]:
    children = receipt.get("receipts")
    if not isinstance(children, Sequence) or isinstance(children, (str, bytes, bytearray)):
        return {}
    for child in reversed(children):
        if not isinstance(child, Mapping):
            continue
        context = child.get("mission_trace_context")
        context_out = (
            context.get("mission_context_out")
            if isinstance(context, Mapping) and isinstance(context.get("mission_context_out"), Mapping)
            else {}
        )
        blockers = context_out.get("blockers") if isinstance(context_out, Mapping) else []
        if isinstance(blockers, Sequence) and not isinstance(blockers, (str, bytes, bytearray)):
            for blocker in blockers:
                if not isinstance(blocker, Mapping):
                    continue
                if _first_text(blocker.get("reason"), blocker.get("message"), blocker.get("required_next_command")):
                    return dict(blocker)
        if child.get("status") == "blocked":
            blocker = {
                "reason": child.get("reason"),
                "message": child.get("message"),
                "required_next_command": child.get("required_next_command"),
            }
            if _first_text(*blocker.values()):
                return blocker
    return {}


def _compact_commands(commands: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(commands, Sequence) or isinstance(commands, (str, bytes, bytearray)):
        return []
    return [str(command) for command in commands[:limit] if str(command).strip()]


def _mission_trace_step_id(plan: Mapping[str, Any], action: Mapping[str, Any], receipt: Mapping[str, Any]) -> str:
    seed = "|".join(
        str(value or "")
        for value in (
            plan.get("plan_id"),
            action.get("action_id"),
            action.get("lane"),
            receipt.get("reason"),
            receipt.get("status"),
        )
    )
    return "closeout_executor:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _build_mission_trace_context(
    *,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    env = _env_context_values()
    lane = _first_text(receipt.get("lane"), action.get("lane"))
    cluster_id = _cluster_id_from_action(action)
    nested_blocker = _receipt_nested_blocker(receipt)
    reason = _first_text(
        receipt.get("reason"),
        nested_blocker.get("reason"),
        receipt.get("stop_reason"),
    )
    status = _first_text(receipt.get("status"))
    handles_present = any(
        env.get(key)
        for key in (
            "mission_trace_id",
            "mission_id",
            "subject_id",
            "prompt_run_id",
            "prompt_trace_id",
            "outbox_row_id",
            "provider_thread_id",
        )
    )
    prompt_refs = {
        key: env[key]
        for key in ("prompt_run_id", "prompt_trace_id", "outbox_row_id", "provider_thread_id")
        if env.get(key)
    }
    affected_paths = _receipt_affected_paths(receipt)
    commits = _receipt_commits(receipt)
    blocker = (
        {
            "reason": reason,
            "message": _first_text(receipt.get("message"), nested_blocker.get("message")),
            "required_next_command": _first_text(
                receipt.get("required_next_command"),
                nested_blocker.get("required_next_command"),
            ),
        }
        if status == "blocked"
        else None
    )
    context: dict[str, Any] = {
        "schema": MISSION_TRACE_CONTEXT_SCHEMA,
        "authority_boundary": "trace_envelope_only_not_authority_store",
        "mission_context_status": "available" if handles_present else "missing",
        "surface": "closeout_executor",
        "actor_class": "controller",
        "step_id": env.get("step_id") or _mission_trace_step_id(plan, action, receipt),
        "parent_step_id": env.get("parent_step_id"),
        "mission_trace_id": env.get("mission_trace_id"),
        "mission_id": env.get("mission_id"),
        "subject_id": env.get("subject_id"),
        "episode_id": env.get("episode_id"),
        "phase_id": env.get("phase_id"),
        "wave_id": env.get("wave_id"),
        "agent_run_id": env.get("agent_run_id"),
        "fallback_subject": cluster_id or lane or _first_text(plan.get("plan_id")),
        "plan_id": plan.get("plan_id"),
        "action_id": action.get("action_id") or receipt.get("action_id"),
        "lane": lane,
        "cluster_id": cluster_id,
        "reason": reason,
        "decision_state": status,
        "prompt_refs": prompt_refs,
        "mission_context_in": {
            "planned_lane": action.get("lane"),
            "planned_cluster_id": cluster_id,
            "owner_commands": _compact_commands(action.get("commands") or receipt.get("owner_commands") or []),
        },
        "mission_context_out": {
            "status": status,
            "reason": reason,
            "affected_paths": affected_paths,
            "commits": commits,
            "remote_verified": receipt.get("remote_verified"),
            "blockers": [blocker] if blocker else [],
            "validation_refs": receipt.get("validation_refs") or [],
            "next_step": receipt.get("next_step"),
            "required_next_command": _first_text(
                receipt.get("required_next_command"),
                nested_blocker.get("required_next_command"),
            ),
        },
        "receipt_ref": f"closeout_executor:{plan.get('plan_id')}:{action.get('action_id') or receipt.get('action_id')}:{reason}",
    }
    return {key: value for key, value in context.items() if value not in (None, [], {})}


def _attach_mission_trace_context(
    receipt: Mapping[str, Any],
    *,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(receipt)
    payload.setdefault(
        "mission_trace_context",
        _build_mission_trace_context(plan=plan, action=action, receipt=payload),
    )
    return payload


def _parse_status_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        if not raw:
            continue
        status = raw[:2]
        path = raw[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = _decode_status_path(path)
        rows.append({"xy": status, "path": path})
    return rows


def _decode_status_path(path: str) -> str:
    text = str(path or "").strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        try:
            decoded = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            decoded = None
        if isinstance(decoded, str):
            return decoded
        try:
            parts = shlex.split(text)
        except ValueError:
            parts = []
        if parts:
            return parts[0]
    return text


def _git_status_rows(repo_root: Path) -> list[dict[str, str]]:
    result = subprocess.run(
        ["git", "status", "--short", "--porcelain=v1", "-uall"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return _parse_status_rows(result.stdout)


def _run_push_audit(repo_root: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["./repo-python", "run_git.py", "audit", "push", "--json"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if result.returncode != 0:
        payload.setdefault("status", "unknown")
        payload.setdefault("blocked_reasons", [])
        payload["error"] = result.stderr.strip() or result.stdout.strip() or "push audit failed"
    return payload


def _is_generated_path(path: str) -> bool:
    if _is_runtime_artifact_lifecycle_path(path):
        return False
    name = Path(path).name
    return (
        path.startswith(GENERATED_PREFIXES)
        or (
            path.startswith(SYSTEM_ATLAS_GENERATED_DOC_PREFIX)
            and (name.startswith("generated_") or name.endswith(".generated.md"))
        )
        or "/views/" in path
        or "/dist/" in path
    )


def _is_source_candidate(path: str) -> bool:
    if _is_generated_path(path):
        return False
    return (path in SOURCE_EXACT_PATHS or path.startswith(SOURCE_PREFIXES)) and Path(path).suffix in {
        "",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".json",
        ".md",
        ".yaml",
        ".yml",
    }


def _is_test_path(path: str) -> bool:
    return path.startswith(TEST_PREFIXES)


def _is_ambient_workspace_path(path: str) -> bool:
    return path.startswith(AMBIENT_WORKSPACE_PREFIXES)


def _is_autonomous_seed_state_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized.startswith(ROOT_AUTONOMOUS_SEED_PREFIX)
        or (
            normalized.startswith(AUTONOMOUS_SEED_STATE_PREFIX)
            and normalized.endswith(".json")
        )
    )


def _is_annex_sync_digest_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith("annexes/") and normalized.rsplit("/", 1)[-1] in ANNEX_SYNC_DIGEST_FILENAMES


def _is_runtime_state_path(path: str) -> bool:
    return path.startswith(OBSERVABILITY_RUNTIME_STATE_PREFIX)


def _is_runtime_artifact_lifecycle_path(path: str) -> bool:
    return (
        _is_runtime_state_path(path)
        or path.startswith(RUNTIME_ARTIFACT_LIFECYCLE_PREFIXES)
        or _is_phase_pipeline_runtime_path(path)
        or _is_microcosm_runtime_receipt_path(path)
        or _is_receipt_artifact_path(path)
    )


def _is_phase_pipeline_runtime_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if not normalized.startswith("obsidian/okay lets do this/"):
        return False
    name = normalized.rsplit("/", 1)[-1]
    return (
        name in PHASE_PIPELINE_RUNTIME_FILENAMES
        or "/.pipeline_recovery/" in normalized
        or "/cycle_" in normalized
    )


def _is_microcosm_runtime_receipt_path(path: str) -> bool:
    return path.replace("\\", "/").startswith(MICROCOSM_RUNTIME_RECEIPT_PREFIX)


def _is_receipt_artifact_path(path: str) -> bool:
    return path.replace("\\", "/").startswith(RECEIPT_ARTIFACT_PREFIX)


def _is_owner_routed_dirty_state_path(path: str) -> bool:
    return (
        _is_ambient_workspace_path(path)
        or _is_annex_sync_digest_path(path)
        or _is_autonomous_seed_state_path(path)
        or _is_runtime_artifact_lifecycle_path(path)
    )


def _dirty_status_paths(rows: Sequence[Mapping[str, str]]) -> list[str]:
    paths: list[str] = []
    for row in rows:
        path = str(row.get("path") or "")
        if path:
            paths.append(path)
    return paths


def _worktree_status_probe_command(path_text: str) -> str:
    return f"git -C {shlex.quote(path_text)} status --short --porcelain=v1 -uall"


def _worktree_owner_commands(worktrees: Mapping[str, Any]) -> list[str]:
    return _uniq_text(
        [
            "git worktree list --porcelain",
            "git worktree list --verbose",
            *(worktrees.get("status_probe_commands") or []),
        ]
    )


def _owner_routed_dirty_state_commands(paths: Sequence[str]) -> list[str]:
    commands: list[str] = []
    if any(_is_runtime_artifact_lifecycle_path(path) for path in paths):
        commands.append(RUNTIME_ARTIFACT_LIFECYCLE_COMMAND)
    if any(_is_runtime_state_path(path) for path in paths):
        commands.append("./repo-python -m tools.meta.observability.station_render timings --json --limit 20")
    if any(_is_phase_pipeline_runtime_path(path) for path in paths):
        commands.append(PHASE_PIPELINE_RUNTIME_COMMAND)
    if any(_is_microcosm_runtime_receipt_path(path) for path in paths):
        commands.append(MICROCOSM_RUNTIME_RECEIPT_COMMAND)
    if any(_is_annex_sync_digest_path(path) for path in paths):
        commands.append(ANNEX_SYNC_DIGEST_COMMAND)
    for path in paths:
        if _is_autonomous_seed_state_path(path):
            target = ROOT_AUTONOMOUS_SEED_JSON if path.startswith(ROOT_AUTONOMOUS_SEED_PREFIX) else path
            commands.append(
                f"./repo-python kernel.py --validate-seed-continuity {shlex.quote(target)}"
            )
    commands.append("./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact")
    return _uniq_text(commands)


def _module_stem(path: str) -> str:
    stem = Path(path).stem
    if _is_test_path(path) and stem.startswith("test_"):
        stem = stem.removeprefix("test_")
        for suffix in ("_cli_compact", "_cached_summary", "_runtime_claim_snapshot"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
    return stem


def _cluster_paths_for(stem: str, rows: Sequence[Mapping[str, str]]) -> list[str]:
    paths: list[str] = []
    for row in rows:
        path = str(row.get("path") or "")
        if not _is_source_candidate(path):
            continue
        candidate_stem = _module_stem(path)
        test_match = _is_test_path(path) and (
            stem in candidate_stem
            or path.startswith("self-indexing-cognitive-substrate/tests/")
        )
        source_match = candidate_stem == stem
        if source_match or test_match:
            paths.append(path)
    return sorted(dict.fromkeys(paths))


def _validation_commands(paths: Sequence[str]) -> list[str]:
    commands: list[str] = []
    py_sources = [
        path
        for path in paths
        if path.endswith(".py") and not _is_test_path(path)
    ]
    json_sources = [
        path
        for path in paths
        if path.endswith(".json") and not _is_generated_path(path)
    ]
    tests = [path for path in paths if _is_test_path(path) and path.endswith(".py")]
    ui_paths = [path for path in paths if path.startswith("system/server/ui/src/")]
    if py_sources:
        commands.append("python3 -m py_compile " + " ".join(py_sources))
    for path in json_sources:
        commands.append("python3 -m json.tool " + path)
    if tests:
        commands.append("./repo-pytest " + " ".join(tests) + " -q")
    if ui_paths:
        rels = [str(Path(path).relative_to("system/server/ui")) for path in ui_paths]
        commands.append("cd system/server/ui && npx eslint " + " ".join(rels))
    return commands


def _targeted_ui_effect_commands(paths: Sequence[str]) -> list[str]:
    commands: list[str] = []
    path_set = set(paths)
    if "system/server/ui/src/pages/ControlRoom.tsx" in path_set:
        commands.append(
            "cd system/server/ui && npx vitest run src/pages/__tests__/ControlRoom.navigation.test.tsx"
        )
    if "system/server/ui/src/components/Exoskeleton.tsx" in path_set:
        commands.append("cd system/server/ui && npx vitest run src/components/__tests__/Exoskeleton.test.tsx")
    if "system/server/ui/src/api.ts" in path_set:
        commands.append("cd system/server/ui && npx vitest run src/__tests__/api.config.test.ts")
    return commands


def _effect_receipt(paths: Sequence[str]) -> dict[str, Any] | None:
    ui_paths = [path for path in paths if path.startswith("system/server/ui/src/")]
    if not ui_paths:
        return None
    build_commands = [
        "cd system/server/ui && npm run build --if-present",
    ]
    proof_modes: list[dict[str, Any]] = [
        {
            "mode": "production_build",
            "commands": build_commands,
        }
    ]
    targeted_commands = _targeted_ui_effect_commands(ui_paths)
    if targeted_commands:
        proof_modes.append(
            {
                "mode": "targeted_component_smoke",
                "commands": targeted_commands,
                "acceptable_when": "production_build_blocked_by_external_type_baseline",
            }
        )
    return {
        "required": True,
        "reason": "UIOperatorVisibleSourceCluster",
        "commands": build_commands,
        "proof_modes": proof_modes,
        "acceptable_evidence": [
            "build/lint/test passed for the UI source cluster",
            "served route or component smoke observed expected selector/text/action",
            "bundle or asset hash changed after rebuild",
            "explicit blocker names why served-surface effect cannot be verified",
        ],
    }


def _cluster_requires_effect_receipt(cluster: Mapping[str, Any]) -> bool:
    receipt = cluster.get("effect_receipt") if isinstance(cluster.get("effect_receipt"), Mapping) else {}
    return bool(receipt.get("required"))


def _active_ui_effect_blocker_ref(repo_root: Path) -> str | None:
    ledger_path = repo_root / "state" / "task_ledger" / "ledger.json"
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    items = data.get("work_items") if isinstance(data, Mapping) else None
    if not isinstance(items, list):
        return None
    terminal_states = {"done", "closed", "retired", "merged", "accepted", "satisfied"}
    active_items: list[Mapping[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        state = str(item.get("state") or item.get("status") or "").lower()
        if state in terminal_states:
            continue
        active_items.append(item)
        tags = {str(tag) for tag in item.get("tags") or []}
        if all(tag in tags for tag in UI_EFFECT_BLOCKER_TAGS):
            return str(item.get("id") or item.get("subject_id") or "")
    for item in active_items:
        item_id = str(item.get("id") or item.get("subject_id") or "")
        if item_id in UI_EFFECT_BLOCKER_REFS:
            return item_id
    return None


def _deferred_ui_effect_actions(clusters: Sequence[Mapping[str, Any]], blocker_ref: str | None) -> list[dict[str, Any]]:
    if not blocker_ref:
        return []
    deferred: list[dict[str, Any]] = []
    for cluster in clusters:
        if not _cluster_requires_effect_receipt(cluster):
            continue
        deferred.append(
            {
                "lane": "drain_source_cluster",
                "cluster_id": cluster.get("cluster_id"),
                "paths": list(cluster.get("paths") or []),
                "reason": "UiEffectValidationBlockedByExternalTypeScriptErrors",
                "blocker_ref": blocker_ref,
                "retry_override": "./repo-python tools/meta/control/closeout_executor.py run-one --include-ui-effect-blocked --json",
            }
        )
    return deferred


def _active_claim_deferred_actions(
    repo_root: Path,
    clusters: Sequence[Mapping[str, Any]],
    *,
    current_session_id: str | None = None,
) -> list[dict[str, Any]]:
    deferred: list[dict[str, Any]] = []
    for cluster in clusters:
        paths = [str(path) for path in cluster.get("paths") or [] if str(path)]
        if not paths:
            continue
        try:
            # Pass current_session_id so the CURRENT actor's own scope-claims are excluded
            # (work_ledger_runtime.active_claim_collisions_for_paths self-excludes only when a
            # session_id is supplied). Without it a disciplined claim_scope_then_mutate actor's
            # own dirty paths collide with its own claim and get misrouted to owner_finalizer.
            collisions = work_ledger_runtime.active_claim_collisions_for_paths(
                repo_root, paths, session_id=current_session_id
            )
        except Exception as exc:  # pragma: no cover - defensive read-only planner fallback
            collisions = []
            error = str(exc)
        else:
            error = ""
        if not collisions:
            continue
        claim_ids = _uniq_text([row.get("claim_id") for row in collisions if isinstance(row, Mapping)])
        owner_session_ids = _uniq_text([row.get("session_id") for row in collisions if isinstance(row, Mapping)])
        deferred.append(
            {
                "lane": "drain_source_cluster",
                "cluster_id": cluster.get("cluster_id"),
                "paths": paths,
                "reason": "WorkLedgerActiveClaimOverlap",
                "active_claim_collisions": collisions,
                "claim_ids": claim_ids,
                "owner_session_ids": owner_session_ids,
                "lease_status": "active",
                "commit_attempted": False,
                "safety_authority": "work_ledger_mutation_check + scoped_commit guard",
                "scheduler_action": "defer_and_continue_to_next_independent_cluster",
                "required_next_command": (
                    "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 30"
                ),
                "retry_policy": "owner_session_lands_or_releases_claim_then_replan",
                "owner_session_commands": [
                    (
                        "./repo-python tools/meta/factory/work_ledger.py session-status "
                        f"--session-id {session_id} --full"
                    )
                    for session_id in owner_session_ids
                ],
            }
        )
        if error:
            deferred[-1]["collision_lookup_error"] = error
    return deferred


def _collision_matches_path(row: Mapping[str, Any], path: str) -> bool:
    requested = str(row.get("requested_path") or "").strip()
    if requested == path:
        return True
    for key in ("claim_path", "path", "scope_id"):
        claim_path = str(row.get(key) or "").strip().rstrip("/")
        if not claim_path:
            continue
        if path == claim_path or path.startswith(claim_path + "/"):
            return True
    return False


def _path_matches_prefix(path: str, prefixes: Sequence[str]) -> bool:
    clean_path = str(path or "").strip().strip("/")
    if not clean_path:
        return False
    for raw_prefix in prefixes:
        prefix = str(raw_prefix or "").strip().strip("/")
        if not prefix:
            continue
        if clean_path == prefix or clean_path.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def _cluster_matches_prefixes(cluster: Mapping[str, Any], prefixes: Sequence[str]) -> bool:
    return any(
        _path_matches_prefix(str(path or ""), prefixes)
        for path in cluster.get("paths") or []
    )


def _actor_transaction_scope(
    repo_root: Path,
    current_session_id: str | None,
    *,
    explicit_owned_path_prefixes: Sequence[str] | None = None,
    explicit_subject_id: str | None = None,
) -> dict[str, Any]:
    session_id = str(current_session_id or "").strip()
    explicit_prefixes = _uniq_text(
        [str(path).strip() for path in explicit_owned_path_prefixes or [] if str(path).strip()]
    )
    if explicit_prefixes:
        subject_id = str(explicit_subject_id or "").strip()
        return {
            "schema": "actor_transaction_scope_v0",
            "status": "resolved",
            "provider_session_id": session_id or None,
            "work_ledger_session_ids": [session_id] if session_id else [],
            "owned_path_prefixes": explicit_prefixes,
            "claimed_paths": explicit_prefixes,
            "claimed_td_ids": [],
            "claimed_work_item_ids": [subject_id] if subject_id else [],
            "active_claim_ids": [],
            "finalized_claim_ids": [],
            "finalized_sessions": [],
            "scope_source": "explicit_owned_path_prefixes",
            "scope_confidence": "operator_supplied_path_prefixes",
        }
    if not session_id:
        return {
            "schema": "actor_transaction_scope_v0",
            "status": "identity_unresolved",
            "provider_session_id": None,
            "work_ledger_session_ids": [],
            "owned_path_prefixes": [],
            "claimed_paths": [],
            "claimed_td_ids": [],
            "claimed_work_item_ids": [],
            "active_claim_ids": [],
            "finalized_claim_ids": [],
            "finalized_sessions": [],
            "scope_source": "none",
            "scope_confidence": "none",
        }
    try:
        status = work_ledger_runtime.load_runtime_status(repo_root)
    except Exception as exc:  # pragma: no cover - defensive closeout projection fallback
        return {
            "schema": "actor_transaction_scope_v0",
            "status": "runtime_status_unavailable",
            "provider_session_id": session_id,
            "work_ledger_session_ids": [session_id],
            "owned_path_prefixes": [],
            "claimed_paths": [],
            "claimed_td_ids": [],
            "claimed_work_item_ids": [],
            "active_claim_ids": [],
            "finalized_claim_ids": [],
            "finalized_sessions": [],
            "scope_source": "work_ledger_runtime",
            "scope_confidence": "none",
            "error": str(exc),
        }
    sessions = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    session = sessions.get(session_id) if isinstance(sessions, Mapping) else None
    if not isinstance(session, Mapping):
        return {
            "schema": "actor_transaction_scope_v0",
            "status": "session_not_found",
            "provider_session_id": session_id,
            "work_ledger_session_ids": [session_id],
            "owned_path_prefixes": [],
            "claimed_paths": [],
            "claimed_td_ids": [],
            "claimed_work_item_ids": [],
            "active_claim_ids": [],
            "finalized_claim_ids": [],
            "finalized_sessions": [],
            "scope_source": "work_ledger_runtime",
            "scope_confidence": "none",
        }

    claimed_paths: list[str] = []
    claimed_td_ids: list[str] = []
    claimed_work_item_ids: list[str] = []
    active_claim_ids: list[str] = []
    finalized_claim_ids: list[str] = []
    for claim in session.get("claims") or []:
        if not isinstance(claim, Mapping):
            continue
        claim_id = str(claim.get("claim_id") or "").strip()
        is_finalized = bool(claim.get("released_at") or claim.get("expired_at"))
        if claim_id:
            if is_finalized:
                finalized_claim_ids.append(claim_id)
            else:
                active_claim_ids.append(claim_id)
        scope_kind = str(claim.get("scope_kind") or "").strip()
        path = str(claim.get("path") or "").strip()
        scope_id = str(claim.get("scope_id") or "").strip()
        if (scope_kind == "path" or path) and (path or scope_id):
            claimed_paths.append(path or scope_id)
        td_id = str(claim.get("td_id") or "").strip()
        if scope_kind == "td_id" and not td_id:
            td_id = scope_id
        if td_id:
            claimed_td_ids.append(td_id)
        work_item_id = str(claim.get("work_item_id") or "").strip()
        if scope_kind == "work_item_id" and not work_item_id:
            work_item_id = scope_id
        if work_item_id:
            claimed_work_item_ids.append(work_item_id)

    owned_path_prefixes = _uniq_text(claimed_paths)
    session_ended = bool(session.get("ended_at"))
    return {
        "schema": "actor_transaction_scope_v0",
        "status": "resolved" if owned_path_prefixes else "resolved_without_path_claims",
        "provider_session_id": session_id,
        "work_ledger_session_ids": [session_id],
        "owned_path_prefixes": owned_path_prefixes,
        "claimed_paths": owned_path_prefixes,
        "claimed_td_ids": _uniq_text(claimed_td_ids),
        "claimed_work_item_ids": _uniq_text(claimed_work_item_ids),
        "active_claim_ids": _uniq_text(active_claim_ids),
        "finalized_claim_ids": _uniq_text(finalized_claim_ids),
        "finalized_sessions": [session_id] if session_ended else [],
        "session_ended": session_ended,
        "claim_count": len([claim for claim in session.get("claims") or [] if isinstance(claim, Mapping)]),
        "scope_source": "work_ledger_session_claim_history",
        "scope_confidence": "path_claim_history" if owned_path_prefixes else "session_without_path_claims",
    }


def _mission_verdict_from_actor_scope(
    repo_root: Path,
    *,
    actor_scope: Mapping[str, Any],
    closeout_summary: Mapping[str, Any],
    dirty_paths: Sequence[str],
) -> dict[str, Any]:
    prefixes = [str(path) for path in actor_scope.get("owned_path_prefixes") or [] if str(path)]
    verdict = mission_closeout_verdict.build_verdict(
        repo_root=repo_root,
        owned_path_prefixes=prefixes,
        subject_id=str((actor_scope.get("claimed_work_item_ids") or [None])[0] or ""),
        paths_override=list(dirty_paths),
        ahead_behind_override=(
            _int_value(closeout_summary.get("ahead")),
            _int_value(closeout_summary.get("behind")),
        ),
    )
    verdict["actor_scope_status"] = actor_scope.get("status")
    verdict["actor_scope_source"] = actor_scope.get("scope_source")
    verdict["machine_classification_trust"] = bool(prefixes and actor_scope.get("status") == "resolved")
    return verdict


def _active_claim_dirty_path_action(
    repo_root: Path,
    paths: Sequence[str],
    *,
    current_session_id: str | None = None,
) -> dict[str, Any] | None:
    dirty_paths = _uniq_text(paths)
    if not dirty_paths:
        return None
    try:
        collisions = work_ledger_runtime.active_claim_collisions_for_paths(
            repo_root, dirty_paths, session_id=current_session_id
        )
    except Exception as exc:  # pragma: no cover - defensive read-only planner fallback
        collisions = []
        error = str(exc)
    else:
        error = ""
    if not collisions:
        return None

    typed_collisions = [row for row in collisions if isinstance(row, Mapping)]
    claimed_paths = [
        path
        for path in dirty_paths
        if any(_collision_matches_path(row, path) for row in typed_collisions)
    ]
    unclaimed_paths = [path for path in dirty_paths if path not in set(claimed_paths)]
    owner_session_ids = _uniq_text([row.get("session_id") for row in typed_collisions])
    owner_commands = [
        (
            "./repo-python tools/meta/factory/work_ledger.py session-status "
            f"--session-id {session_id} --full"
        )
        for session_id in owner_session_ids
    ]
    if not owner_commands:
        owner_commands = ["./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 30"]
    action: dict[str, Any] = {
        "lane": "active_claim_blocked",
        "reason": "WorkLedgerActiveClaimOverlap",
        "commands": owner_commands,
        "paths": dirty_paths[:50],
        "path_count": len(dirty_paths),
        "active_claim_paths": claimed_paths[:50],
        "active_claim_path_count": len(claimed_paths),
        "unclaimed_paths": unclaimed_paths[:50],
        "unclaimed_path_count": len(unclaimed_paths),
        "active_claim_collisions": [dict(row) for row in typed_collisions],
        "claim_ids": _uniq_text([row.get("claim_id") for row in typed_collisions]),
        "owner_session_ids": owner_session_ids,
        "lease_status": "active",
        "commit_attempted": False,
        "scheduler_action": "owner_finalizer_required",
        "required_next_command": owner_commands[0],
        "retry_policy": "owner_session_lands_or_releases_claim_then_replan",
        "safety_authority": "work_ledger_mutation_check + scoped_commit guard",
        "dirty_state_boundary": "non_source_dirty_paths_checked_against_active_claims",
    }
    if error:
        action["collision_lookup_error"] = error
    return action


def _deferred_action_ids(actions: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(action.get("cluster_id") or "") for action in actions if str(action.get("cluster_id") or "")}


def _source_deferred_reason_suffix(actions: Sequence[Mapping[str, Any]]) -> str:
    reasons = {str(action.get("reason") or "") for action in actions}
    if "WorkLedgerActiveClaimOverlap" in reasons and "UiEffectValidationBlockedByExternalTypeScriptErrors" in reasons:
        return "AfterDeferredOwnerBlockers"
    if "WorkLedgerActiveClaimOverlap" in reasons:
        return "AfterDeferredActiveClaimBlocker"
    if "UiEffectValidationBlockedByExternalTypeScriptErrors" in reasons:
        return "AfterDeferredUiEffectBlocker"
    return ""


def _active_claim_blocked_action(deferred_actions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    active_deferred = [
        action for action in deferred_actions if str(action.get("reason") or "") == "WorkLedgerActiveClaimOverlap"
    ]
    collisions: list[Mapping[str, Any]] = []
    for action in active_deferred:
        for row in action.get("active_claim_collisions") or []:
            if isinstance(row, Mapping):
                collisions.append(row)
    owner_commands = _uniq_text(
        command
        for action in active_deferred
        for command in action.get("owner_session_commands") or []
    )
    if not owner_commands:
        owner_commands = ["./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 30"]
    return {
        "lane": "active_claim_blocked",
        "reason": "WorkLedgerActiveClaimOverlap",
        "commands": owner_commands,
        "blocked_cluster_ids": [action.get("cluster_id") for action in active_deferred],
        "active_claim_deferred_actions": [dict(action) for action in active_deferred],
        "active_claim_collisions": [dict(row) for row in collisions],
        "claim_ids": _uniq_text([row.get("claim_id") for row in collisions]),
        "owner_session_ids": _uniq_text([row.get("session_id") for row in collisions]),
        "lease_status": "active",
        "commit_attempted": False,
        "scheduler_action": "owner_finalizer_required",
        "required_next_command": owner_commands[0],
        "retry_policy": "owner_session_lands_or_releases_claim_then_replan",
        "safety_authority": "work_ledger_mutation_check + scoped_commit guard",
    }


def _mission_verdict_command(prefixes: Sequence[str], *, subject_id: str = "") -> str:
    parts = [
        "./repo-python",
        "tools/meta/control/closeout_executor.py",
        "mission-verdict",
        "--json",
    ]
    for prefix in prefixes:
        parts.extend(["--owned-path-prefix", str(prefix)])
    if subject_id:
        parts.extend(["--subject-id", subject_id])
    return " ".join(shlex.quote(part) for part in parts)


def _mission_closeout_terminal_action(
    *,
    actor_owned_prefixes: Sequence[str],
    mission_verdict: Mapping[str, Any],
    actor_foreign_clusters: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    status = str(mission_verdict.get("status") or "mission_closeout_blocked")
    reason_by_status = {
        "held_foreign_dirty": "MissionVerdictHeldForeignDirty",
        "held_publication_foreign_dirty": "MissionVerdictHeldPublicationForeignDirty",
        "blocked_behind": "MissionVerdictBlockedBehind",
        "blocked_publication": "MissionVerdictBlockedPublication",
    }
    scheduler_by_status = {
        "held_foreign_dirty": "typed_held_foreign_closeout",
        "held_publication_foreign_dirty": "typed_held_publication_foreign_closeout",
        "blocked_behind": "typed_mission_closeout_blocked",
        "blocked_publication": "typed_mission_closeout_blocked",
    }
    commands = [
        _mission_verdict_command(
            actor_owned_prefixes,
            subject_id=str(mission_verdict.get("subject_id") or ""),
        )
    ]
    if status in {"blocked_publication", "held_publication_foreign_dirty"}:
        commands.append("./repo-python run_git.py audit push --json")
    return {
        "lane": status,
        "reason": reason_by_status.get(status, "MissionVerdictBlocked"),
        "commands": _uniq_text(commands),
        "mission_closeout_verdict_status": status,
        "mission_closeout_verdict": dict(mission_verdict),
        "machine_classification_trust": bool(mission_verdict.get("machine_classification_trust")),
        "caller_must_carry_local_landing_evidence": not bool(
            mission_verdict.get("machine_classification_trust")
        ),
        "foreign_source_cluster_candidates": [dict(cluster) for cluster in actor_foreign_clusters],
        "scheduler_action": scheduler_by_status.get(status, "typed_mission_closeout_blocked"),
        "closeout_ready_after_local_landing": status in {
            "held_foreign_dirty",
            "held_publication_foreign_dirty",
        },
        "commit_attempted": False,
        "required_next_command": commands[0],
        "safety_authority": "mission_closeout_verdict + actor_owned_path_prefixes",
    }


def _mission_closeout_terminal_receipt(
    *,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    status = str(action.get("mission_closeout_verdict_status") or action.get("lane") or "")
    is_held = status in MISSION_HELD_CLOSEOUT_STATUSES
    receipt_status = status if is_held else "blocked"
    return {
        "schema": RUN_ONE_SCHEMA,
        "kind": "closeout_executor_run_one_receipt",
        "status": receipt_status,
        "reason": str(action.get("reason") or "MissionCloseoutHeldOrBlocked"),
        "message": (
            "mission-owned scope is clean enough for this verdict; the remaining "
            f"closeout condition is {status} and must not be drained as current-session work"
        ),
        "plan_id": plan.get("plan_id"),
        "action_id": action.get("action_id"),
        "lane": action.get("lane"),
        "mission_closeout_verdict": plan.get("mission_closeout_verdict"),
        "foreign_source_cluster_candidates": action.get("foreign_source_cluster_candidates") or [],
        "owner_commands": list(action.get("commands") or []),
        "required_next_command": action.get("required_next_command"),
        "scheduler_action": action.get("scheduler_action"),
        "closeout_ready_after_local_landing": action.get("closeout_ready_after_local_landing"),
        "machine_classification_trust": bool(action.get("machine_classification_trust")),
        "caller_must_carry_local_landing_evidence": bool(
            action.get("caller_must_carry_local_landing_evidence")
        ),
        "terminal_for_current_mission": bool(is_held),
        "safety_authority": action.get("safety_authority"),
    }


def _commit_command(
    paths: Sequence[str],
    message: str,
    *,
    expected_parent: str | None = None,
    allow_untracked: bool = False,
) -> str:
    path_args = " ".join(f"--path {path}" for path in paths)
    allow_untracked_arg = (
        " --allow-untracked"
        if allow_untracked or any(_is_test_path(path) for path in paths)
        else ""
    )
    parent = expected_parent or "$(git rev-parse HEAD)"
    return (
        "./repo-python tools/meta/control/scoped_commit.py full-paths "
        f"{path_args}{allow_untracked_arg} --allow-multi-hunk-full-paths "
        f"--remote-fallback-on-metadata-block --expected-parent {parent} "
        f"--message {json.dumps(message)}"
    )


def _stable_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _observed_state(
    closeout_summary: Mapping[str, Any],
    status_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    observed = closeout_summary.get("observed")
    if not isinstance(observed, Mapping):
        observed = {}
    worktrees = closeout_summary.get("worktrees")
    if not isinstance(worktrees, Mapping):
        worktrees = {}
    status_projection = [
        {"xy": str(row.get("xy") or ""), "path": str(row.get("path") or "")}
        for row in status_rows
    ]
    return {
        "head": observed.get("head"),
        "upstream": observed.get("upstream"),
        "remote_ref": observed.get("remote_ref"),
        "status_hash": observed.get("status_hash"),
        "dirty_total": _int_value(closeout_summary.get("dirty_total")),
        "staged_total": _int_value(closeout_summary.get("staged_total")),
        "ahead": _int_value(closeout_summary.get("ahead")),
        "behind": _int_value(closeout_summary.get("behind")),
        "worktree_count": _int_value(worktrees.get("linked_count")),
        "worktree_status": worktrees.get("status"),
        "status_rows_hash": _stable_digest({"rows": status_projection}),
    }


def _worktree_drain_required(worktrees: Mapping[str, Any]) -> bool:
    status = str(worktrees.get("status") or "").strip()
    if status in {"", "clear", "deferred", "not_checked"}:
        return False
    if worktrees.get("cleanup_required") is False:
        return False
    linked_count = _int_value(worktrees.get("linked_count"))
    return linked_count > 0 or bool(worktrees.get("cleanup_required"))


def _action_fingerprint(action: Mapping[str, Any]) -> dict[str, Any]:
    cluster = action.get("cluster") if isinstance(action.get("cluster"), Mapping) else {}
    push_audit = action.get("push_audit") if isinstance(action.get("push_audit"), Mapping) else {}
    return {
        "lane": action.get("lane"),
        "reason": action.get("reason"),
        "commands": action.get("commands") or [],
        "cluster_id": cluster.get("cluster_id"),
        "cluster_paths": cluster.get("paths") or [],
        "push_audit_status": push_audit.get("status"),
        "push_blockers": push_audit.get("blocked_reasons") or [],
    }


def _source_clusters(
    rows: Sequence[Mapping[str, str]],
    *,
    limit: int = 5,
    expected_parent: str | None = None,
    preferred_prefixes: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    candidates = [str(row.get("path") or "") for row in rows if _is_source_candidate(str(row.get("path") or ""))]
    preferred = [str(prefix) for prefix in preferred_prefixes or [] if str(prefix)]
    clusters: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in candidates:
        if _is_test_path(path):
            continue
        stem = _module_stem(path)
        if not stem or stem in seen:
            continue
        seen.add(stem)
        paths = _cluster_paths_for(stem, rows)
        tests = [item for item in paths if _is_test_path(item)]
        source_paths = [item for item in paths if item not in tests]
        if not source_paths:
            continue
        untracked_paths = sorted(
            {
                str(row.get("path") or "")
                for row in rows
                if str(row.get("path") or "") in paths and str(row.get("xy") or "") == "??"
            }
        )
        cluster = {
            "cluster_id": f"source_test:{stem}",
            "stem": stem,
            "paths": paths,
            "source_paths": source_paths,
            "test_paths": tests,
            "untracked_paths": untracked_paths,
            "allow_untracked": bool(untracked_paths),
            "validation_commands": _validation_commands(paths),
            "commit_command": _commit_command(
                paths,
                f"Drain {stem} source cluster",
                expected_parent=expected_parent,
                allow_untracked=bool(untracked_paths),
            ),
        }
        receipt = _effect_receipt(paths)
        if receipt:
            cluster["effect_receipt"] = receipt
        clusters.append(cluster)
    clusters.sort(
        key=lambda row: (
            0 if preferred and _cluster_matches_prefixes(row, preferred) else 1,
            0 if row.get("test_paths") else 1,
            len(row.get("paths") or []),
            str(row.get("cluster_id")),
        )
    )
    return clusters[:limit]


def _wip_capsule_route(
    *,
    action: Mapping[str, Any],
    observed: Mapping[str, Any],
    dirty_paths: Sequence[str],
    actor_scope: Mapping[str, Any],
    mission_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    lane = str(action.get("lane") or "")
    non_landable_lanes = {
        "active_claim_blocked",
        "held_foreign_dirty",
        "held_publication_foreign_dirty",
        "inspect_diff_review",
        "owner_routed_dirty_state",
        "ui_effect_blocked",
    }
    required = lane in non_landable_lanes or str(action.get("scheduler_action") or "") == "owner_finalizer_required"
    item_id = "wip_" + _stable_digest(
        {
            "head": observed.get("head"),
            "lane": lane,
            "dirty_paths": list(dirty_paths)[:100],
            "session_id": actor_scope.get("provider_session_id"),
            "verdict": mission_verdict.get("status"),
        }
    )
    if not required:
        return {
            "schema": "wip_capsule_route_v1",
            "status": "not_required",
            "reason": "local_landing_or_publication_action_available",
            "wip_capsule_id": item_id,
        }
    preservation_command = (
        "./checkpoint --rescue-ref --dry-run --message "
        + json.dumps(f"rescue: {item_id} {lane or 'closeout'}")
    )
    return {
        "schema": "wip_capsule_route_v1",
        "status": "available",
        "wip_capsule_id": item_id,
        "base_head": observed.get("head"),
        "actor_session_id": actor_scope.get("provider_session_id"),
        "owned_path_prefixes": list(actor_scope.get("owned_path_prefixes") or []),
        "dirty_paths_preview": list(dirty_paths)[:50],
        "dirty_path_count": len(dirty_paths),
        "non_landable_reason": action.get("reason") or lane,
        "mission_closeout_status": mission_verdict.get("status"),
        "preservation_command": preservation_command,
        "settlement_item": {
            "schema": "workspace_settlement_item_v1",
            "item_id": "settle_" + item_id[4:],
            "item_class": "wip_capsule_required",
            "blocked_by": _uniq_text(
                [
                    str(action.get("reason") or ""),
                    str(mission_verdict.get("status") or ""),
                ]
            ),
            "reentry_command": "./repo-python tools/meta/control/mission_transaction_preflight.py --control-summary",
            "retirement_condition": "wip capsule is landed, superseded by scoped commit, or retired with evidence",
            "closeout_relevance": True,
        },
    }


def _settlement_group_projection(
    *,
    action: Mapping[str, Any],
    actor_scope: Mapping[str, Any],
    mission_verdict: Mapping[str, Any],
    deferred_actions: Sequence[Mapping[str, Any]],
    wip_capsule_route: Mapping[str, Any],
) -> dict[str, Any]:
    owner_session_ids = _uniq_text(
        [
            *[session for session in action.get("owner_session_ids") or []],
            *[
                session
                for deferred in deferred_actions
                for session in (deferred.get("owner_session_ids") or [])
            ],
        ]
    )
    local_session_id = str(actor_scope.get("provider_session_id") or "")
    participant_session_ids = _uniq_text([local_session_id, *owner_session_ids])
    settlement_items: list[dict[str, Any]] = []
    item = wip_capsule_route.get("settlement_item")
    if isinstance(item, Mapping):
        settlement_items.append(dict(item))
    status = "coordination_required" if owner_session_ids else "single_session_projection"
    if mission_verdict.get("status") in {"held_foreign_dirty", "held_publication_foreign_dirty"}:
        status = "held_foreign_ready"
    return {
        "schema": "settlement_group_v0",
        "group_id": "sg_" + _stable_digest(
            {
                "local_session_id": local_session_id,
                "owner_session_ids": owner_session_ids,
                "lane": action.get("lane"),
                "verdict": mission_verdict.get("status"),
                "items": settlement_items,
            }
        ),
        "status": status,
        "local_session_id": local_session_id or None,
        "participant_session_ids": participant_session_ids,
        "owner_session_ids": owner_session_ids,
        "primary_action_lane": action.get("lane"),
        "primary_action_reason": action.get("reason"),
        "mission_closeout_status": mission_verdict.get("status"),
        "settlement_items": settlement_items,
        "hud_visible": True,
        "query_commands": [
            (
                "./repo-python tools/meta/factory/work_ledger.py session-status "
                f"--session-id {session_id} --full"
            )
            for session_id in participant_session_ids
            if session_id
        ],
        "retirement_condition": (
            "all participant claims are released or represented by scoped commits, "
            "execution receipts, projection settlement rows, or WIP capsule retirement evidence"
        ),
    }


def _compact_closeout(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "dirty_total": packet.get("dirty_total"),
        "staged_total": packet.get("staged_total"),
        "ahead": packet.get("ahead"),
        "behind": packet.get("behind"),
        "observed": packet.get("observed"),
        "closeout_ready": packet.get("closeout_ready"),
        "publication": packet.get("publication"),
        "worktrees": packet.get("worktrees"),
        "reason": packet.get("reason"),
    }


def build_closeout_executor_plan(
    repo_root: Path | str,
    *,
    closeout_summary: Mapping[str, Any] | None = None,
    status_rows: Sequence[Mapping[str, str]] | None = None,
    push_audit: Mapping[str, Any] | None = None,
    run_push_audit: bool = True,
    include_ui_effect_blocked: bool = False,
    defer_active_claim_blocked: bool = True,
    current_session_id: str | None = None,
    owned_path_prefixes: Sequence[str] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    if closeout_summary is None:
        closeout_summary = compact_closeout_git_state_conditions(
            build_closeout_git_state_conditions(repo, path_limit=10, recent_limit=2)
        )
    if status_rows is None:
        status_rows = _git_status_rows(repo)

    ahead = int(closeout_summary.get("ahead") or 0)
    worktrees = closeout_summary.get("worktrees") if isinstance(closeout_summary.get("worktrees"), Mapping) else {}
    worktree_drain_required = _worktree_drain_required(worktrees)
    observed = _observed_state(closeout_summary, status_rows)
    observed_head = str(observed.get("head") or "").strip() or None
    dirty_paths = _dirty_status_paths(status_rows)
    actor_scope = _actor_transaction_scope(
        repo,
        current_session_id,
        explicit_owned_path_prefixes=owned_path_prefixes,
        explicit_subject_id=subject_id,
    )
    actor_owned_prefixes = [
        str(path) for path in actor_scope.get("owned_path_prefixes") or [] if str(path)
    ]
    actor_scope_filter_enabled = bool(
        actor_scope.get("status") == "resolved" and actor_owned_prefixes
    )
    mission_verdict = _mission_verdict_from_actor_scope(
        repo,
        actor_scope=actor_scope,
        closeout_summary=closeout_summary,
        dirty_paths=dirty_paths,
    )
    ui_effect_blocker_ref = None if include_ui_effect_blocked else _active_ui_effect_blocker_ref(repo)
    clusters = _source_clusters(
        status_rows,
        limit=10 if ui_effect_blocker_ref else 5,
        expected_parent=observed_head,
        preferred_prefixes=actor_owned_prefixes,
    )
    actor_owned_clusters = [
        cluster for cluster in clusters if _cluster_matches_prefixes(cluster, actor_owned_prefixes)
    ]
    actor_foreign_clusters = [
        cluster for cluster in clusters if cluster not in actor_owned_clusters
    ]
    closeout_source_clusters = actor_owned_clusters if actor_scope_filter_enabled else clusters
    ui_deferred_actions = _deferred_ui_effect_actions(closeout_source_clusters, ui_effect_blocker_ref)
    source_claim_lookup_allowed = (
        closeout_summary.get("closeout_ready") is not True
        and not worktree_drain_required
    )
    active_claim_deferred_actions = (
        _active_claim_deferred_actions(repo, closeout_source_clusters, current_session_id=current_session_id)
        if defer_active_claim_blocked and source_claim_lookup_allowed
        else []
    )
    deferred_actions = [*ui_deferred_actions, *active_claim_deferred_actions]
    deferred_cluster_ids = _deferred_action_ids(deferred_actions)
    runnable_clusters = [
        cluster
        for cluster in closeout_source_clusters
        if str(cluster.get("cluster_id") or "") not in deferred_cluster_ids
    ]
    generated_dirty_paths = [path for path in dirty_paths if _is_generated_path(path)]
    owner_routed_dirty_paths = [
        path for path in dirty_paths if _is_owner_routed_dirty_state_path(path)
    ]
    unclassified_dirty_paths = [
        path
        for path in dirty_paths
        if not _is_generated_path(path) and not _is_owner_routed_dirty_state_path(path)
    ]
    non_source_unclassified_dirty_paths = [
        path for path in unclassified_dirty_paths if not _is_source_candidate(path)
    ]
    generated_only_dirty = bool(generated_dirty_paths) and len(generated_dirty_paths) == len(dirty_paths)
    ambient_only_dirty = bool(dirty_paths) and all(_is_ambient_workspace_path(path) for path in dirty_paths)
    owner_routed_dirty_only = bool(dirty_paths) and all(
        _is_owner_routed_dirty_state_path(path) for path in dirty_paths
    )
    generated_and_owner_routed_only = (
        bool(dirty_paths)
        and bool(generated_dirty_paths)
        and bool(owner_routed_dirty_paths)
        and not unclassified_dirty_paths
    )
    active_claim_dirty_action = (
        _active_claim_dirty_path_action(repo, non_source_unclassified_dirty_paths, current_session_id=current_session_id)
        if defer_active_claim_blocked and source_claim_lookup_allowed and non_source_unclassified_dirty_paths
        else None
    )
    active_claim_unclassified_dirty_only = (
        bool(active_claim_dirty_action)
        and int(active_claim_dirty_action.get("unclaimed_path_count") or 0) == 0
    )

    action: dict[str, Any]
    if closeout_summary.get("closeout_ready") is True:
        action = {
            "lane": "no_action",
            "reason": "CloseoutReady",
            "commands": [],
        }
    elif worktree_drain_required:
        action = {
            "lane": "drain_worktrees",
            "reason": worktrees.get("reason") or "LinkedWorktreesObserved",
            "commands": _worktree_owner_commands(worktrees),
        }
    elif (
        mission_verdict.get("status")
        in {
            "held_foreign_dirty",
            "held_publication_foreign_dirty",
            "blocked_behind",
            "blocked_publication",
        }
        and not runnable_clusters
        and not active_claim_deferred_actions
        and (
            actor_scope_filter_enabled
            or (
                bool(str(current_session_id or "").strip())
                and mission_verdict.get("status") in MISSION_HELD_CLOSEOUT_STATUSES
                and not generated_only_dirty
                and not owner_routed_dirty_only
                and not generated_and_owner_routed_only
            )
        )
    ):
        action = _mission_closeout_terminal_action(
            actor_owned_prefixes=actor_owned_prefixes,
            mission_verdict=mission_verdict,
            actor_foreign_clusters=actor_foreign_clusters,
        )
    elif runnable_clusters:
        first = runnable_clusters[0]
        deferred_reason_suffix = _source_deferred_reason_suffix(deferred_actions)
        action = {
            "lane": "drain_source_cluster",
            "reason": "SourceTestDirtyClusterObserved" + deferred_reason_suffix,
            "cluster": first,
            "commands": [
                "git diff -- " + " ".join(first["paths"]),
                *first["validation_commands"],
                first["commit_command"],
                "./repo-python run_git.py audit push --json",
                "./repo-python run_git.py push guarded --json",
                "git ls-remote origin refs/heads/main",
            ],
        }
        if deferred_actions:
            action["deferred_cluster_ids"] = [item.get("cluster_id") for item in deferred_actions]
            action["scheduler_action"] = "defer_and_continue_to_next_independent_cluster"
    elif ambient_only_dirty:
        action = {
            "lane": "ambient_workspace_state",
            "reason": "AmbientWorkspaceOnlyDirtyState",
            "paths": dirty_paths,
            "commands": [
                "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
            ],
        }
    elif owner_routed_dirty_only:
        action = {
            "lane": "owner_routed_dirty_state",
            "reason": "OwnerRoutedDirtyStateDetected",
            "paths": dirty_paths,
            "commands": _owner_routed_dirty_state_commands(dirty_paths),
        }
    elif generated_and_owner_routed_only:
        action = {
            "lane": "owner_routed_dirty_state",
            "reason": "GeneratedAndOwnerRoutedDirtyStateDetected",
            "paths": dirty_paths,
            "generated_paths": generated_dirty_paths[:50],
            "generated_path_count": len(generated_dirty_paths),
            "owner_routed_paths": owner_routed_dirty_paths[:50],
            "owner_routed_path_count": len(owner_routed_dirty_paths),
            "commands": _uniq_text(
                [
                    "./repo-python tools/meta/control/generated_state_drainer.py status --compact",
                    "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --fast",
                    *_owner_routed_dirty_state_commands(owner_routed_dirty_paths),
                ]
            ),
        }
    elif active_claim_unclassified_dirty_only:
        action = dict(active_claim_dirty_action or {})
        if generated_dirty_paths:
            action["generated_paths"] = generated_dirty_paths[:50]
            action["generated_path_count"] = len(generated_dirty_paths)
        if owner_routed_dirty_paths:
            action["owner_routed_paths"] = owner_routed_dirty_paths[:50]
            action["owner_routed_path_count"] = len(owner_routed_dirty_paths)
    elif active_claim_deferred_actions:
        action = _active_claim_blocked_action(deferred_actions)
    elif deferred_actions:
        action = {
            "lane": "ui_effect_blocked",
            "reason": "UiEffectValidationBlockedByExternalTypeScriptErrors",
            "commands": [
                "cd system/server/ui && npm run build --if-present",
                "./repo-python tools/meta/control/closeout_executor.py run-one --include-ui-effect-blocked --json",
            ],
            "blocked_cluster_ids": [item.get("cluster_id") for item in deferred_actions],
            "blocker_ref": ui_effect_blocker_ref,
        }
    elif generated_only_dirty:
        action = {
            "lane": "settle_generated_state",
            "reason": "OnlyGeneratedOrProjectionDirtDetected",
            "commands": [
                "./repo-python tools/meta/control/generated_state_drainer.py status --compact",
                "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --fast",
            ],
        }
    elif generated_dirty_paths:
        action = {
            "lane": "inspect_diff_review",
            "reason": "MixedGeneratedAndUnclassifiedDirtyPaths",
            "generated_paths": generated_dirty_paths[:50],
            "generated_path_count": len(generated_dirty_paths),
            "owner_routed_paths": owner_routed_dirty_paths[:50],
            "owner_routed_path_count": len(owner_routed_dirty_paths),
            "unclassified_paths": unclassified_dirty_paths[:50],
            "unclassified_path_count": len(unclassified_dirty_paths),
            "commands": [
                "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
                "./repo-python tools/meta/control/generated_state_drainer.py status --compact",
            ],
        }
    elif ahead > 0 and not dirty_paths:
        audit = dict(push_audit or (_run_push_audit(repo) if run_push_audit else {}))
        audit_clear = (
            audit.get("status") == "clear"
            and bool(audit.get("direct_push_allowed", True))
            and not audit.get("blocked_reasons")
        )
        guarded_push_command = str(
            audit.get("next_safe_command")
            or "./repo-python run_git.py push guarded --json"
        )
        action = {
            "lane": "publish_if_clear" if audit_clear else "publication_gate",
            "reason": "LocalAheadOfOrigin" if audit_clear else "PushAuditNotClear",
            "push_audit": audit or None,
            "commands": [
                "./repo-python run_git.py audit push --json",
                guarded_push_command if audit_clear else "./repo-python tools/meta/control/publication_lane.py plan --repo-root .",
                "git ls-remote origin refs/heads/main" if audit_clear else "./repo-python tools/meta/control/mission_transaction_preflight.py --github-push-bloat-gate",
                "git rev-parse HEAD" if audit_clear else "",
            ],
        }
        action["commands"] = [command for command in action["commands"] if command]
    else:
        action = {
            "lane": "inspect_diff_review",
            "reason": closeout_summary.get("reason") or "DirtyPathsUnclassified",
            "commands": [
                "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
            ],
        }
    action["action_id"] = "cea_" + _stable_digest(
        {
            "observed": observed,
            "action": _action_fingerprint(action),
        }
    )
    plan_id = "cep_" + _stable_digest(
        {
            "observed": observed,
            "primary_action": _action_fingerprint(action),
            "action_id": action.get("action_id"),
        }
    )
    wip_capsule_route = _wip_capsule_route(
        action=action,
        observed=observed,
        dirty_paths=dirty_paths,
        actor_scope=actor_scope,
        mission_verdict=mission_verdict,
    )
    settlement_group = _settlement_group_projection(
        action=action,
        actor_scope=actor_scope,
        mission_verdict=mission_verdict,
        deferred_actions=deferred_actions,
        wip_capsule_route=wip_capsule_route,
    )

    return {
        "schema": SCHEMA,
        "kind": "closeout_executor_plan",
        "repo_root": str(repo),
        "plan_id": plan_id,
        "freshness": "fresh",
        # Identity transparency for self-exclusion: True when no current_session_id was
        # supplied, so active-claim self-exclusion could not run and any active claim
        # (possibly the actor's own) was treated as a collision. Consumers MUST NOT treat
        # this as a reason to suppress closeout; it only records that ownership self-exclusion
        # was not applied. Clusters are unaffected — the plan is identical apart from this flag.
        "session_identity_unresolved": current_session_id is None,
        "current_session_id": current_session_id,
        "actor_transaction_scope": actor_scope,
        "mission_closeout_verdict": mission_verdict,
        "wip_capsule_route": wip_capsule_route,
        "settlement_group": settlement_group,
        "observed": observed,
        "status": "ready" if action["lane"] == "no_action" else "action_required",
        "closeout": _compact_closeout(closeout_summary),
        "primary_action": action,
        "source_cluster_candidates": clusters,
        "actor_owned_source_cluster_candidates": actor_owned_clusters,
        "foreign_source_cluster_candidates": actor_foreign_clusters if actor_scope_filter_enabled else [],
        "actor_scope_filter_enabled": actor_scope_filter_enabled,
        "runnable_source_cluster_candidates": runnable_clusters,
        "blocked_source_cluster_candidates": [
            dict(action)
            for action in active_claim_deferred_actions
        ],
        "deferred_actions": deferred_actions,
        "active_claim_blocker_lookup": {
            "strategy": "work_ledger_active_claim_collisions_for_source_cluster_paths",
            "enabled": bool(defer_active_claim_blocked),
            "deferred_cluster_count": len(active_claim_deferred_actions),
            "blocked_cluster_ids": [action.get("cluster_id") for action in active_claim_deferred_actions],
            "safety_authority": "work_ledger_mutation_check + scoped_commit guard",
        },
        "dirty_path_active_claim_lookup": {
            "strategy": "work_ledger_active_claim_collisions_for_unclassified_dirty_paths",
            "enabled": bool(defer_active_claim_blocked),
            "unclassified_path_count": len(unclassified_dirty_paths),
            "non_source_unclassified_path_count": len(non_source_unclassified_dirty_paths),
            "active_claim_path_count": (
                int(active_claim_dirty_action.get("active_claim_path_count") or 0)
                if active_claim_dirty_action
                else 0
            ),
            "unclaimed_path_count": (
                int(active_claim_dirty_action.get("unclaimed_path_count") or 0)
                if active_claim_dirty_action
                else len(unclassified_dirty_paths)
            ),
            "safety_authority": "work_ledger_mutation_check + scoped_commit guard",
        },
        "ui_effect_blocker_lookup": {
            "strategy": "task_ledger_tags_with_episode_fallback",
            "required_tags": list(UI_EFFECT_BLOCKER_TAGS),
            "fallback_refs": list(UI_EFFECT_BLOCKER_REFS),
            "matched_ref": ui_effect_blocker_ref,
        },
        "rules": [
            "red closeout state must route to publish, worktree drain, source scoped commit, generated-state settlement, or a concrete blocker",
            "generated projection settlement comes after source/test clusters unless no source cluster is present",
            "executor plan is read-only; commit/push/remove actuation stays with scoped tools and git",
        ],
    }


Command = Sequence[str] | str
CommandRunner = Callable[[Path, Command], Mapping[str, Any]]


def _command_string(command: Command) -> str:
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


def _truncate_output(value: Any, *, limit: int = 4000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _run_command(
    repo_root: Path,
    command: Command,
    *,
    shell: bool = False,
    timeout: int = 300,
    output_limit: int = 4000,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            shell=shell,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "command": _command_string(command),
            "returncode": completed.returncode,
            "stdout": _truncate_output(completed.stdout, limit=output_limit),
            "stderr": _truncate_output(completed.stderr, limit=output_limit),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": _command_string(command),
            "returncode": 124,
            "stdout": _truncate_output(exc.stdout, limit=output_limit),
            "stderr": _truncate_output(exc.stderr, limit=output_limit)
            or f"command timed out after {timeout}s",
        }


def _invoke_runner(
    runner: Callable[..., Mapping[str, Any]] | None,
    repo_root: Path,
    command: Command,
    *,
    shell: bool = False,
    timeout: int = 300,
    output_limit: int = 4000,
) -> dict[str, Any]:
    if runner is None:
        return _run_command(
            repo_root,
            command,
            shell=shell,
            timeout=timeout,
            output_limit=output_limit,
        )
    result = runner(repo_root, command, shell=shell, timeout=timeout)
    return {
        "command": str(result.get("command") or _command_string(command)),
        "returncode": int(result.get("returncode") or 0),
        "stdout": _truncate_output(result.get("stdout"), limit=output_limit),
        "stderr": _truncate_output(result.get("stderr"), limit=output_limit),
    }


def _json_stdout(result: Mapping[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(str(result.get("stdout") or "{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _command_ok(result: Mapping[str, Any]) -> bool:
    return int(result.get("returncode") or 0) == 0


def _json_objects_from_text(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in str(value or "").splitlines():
        text = line.strip()
        if not (text.startswith("{") and text.endswith("}")):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _queued_validation_pressure_receipt(evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for result in reversed(evidence):
        if int(result.get("returncode") or 0) != 75:
            continue
        command = str(result.get("command") or "")
        if "repo-pytest" not in command:
            continue
        gate_rows = [
            row
            for row in (
                _json_objects_from_text(result.get("stderr"))
                + _json_objects_from_text(result.get("stdout"))
            )
            if row.get("schema")
            in {"repo_pytest_host_pressure_gate_v0", "repo_pytest_disk_pressure_gate_v0"}
            and row.get("status") == "blocked"
        ]
        if not gate_rows:
            continue
        gate = gate_rows[-1]
        schema = str(gate.get("schema") or "")
        pressure_kind = "disk_pressure" if "disk" in schema else "host_pressure"
        return {
            "queued_validation": {
                "schema": "closeout_executor_queued_validation_v0",
                "pressure_kind": pressure_kind,
                "gate_schema": schema,
                "gate": gate,
                "command": command,
                "tempfail_returncode": 75,
                "queue_id": gate.get("resource_work_queue_id"),
                "queue_status": gate.get("resource_work_queue_status"),
                "recheck_command": gate.get("host_pressure_recheck_command")
                or gate.get("quote_command")
                or gate.get("storage_doctor_command")
                or gate.get("process_gate_command"),
            },
            "required_next_command": gate.get("host_pressure_recheck_command")
            or gate.get("quote_command")
            or gate.get("storage_doctor_command")
            or gate.get("process_gate_command")
            or command,
            "scheduler_action": "retry_validation_after_pressure_clears",
            "retry_policy": "retry_after_pressure_recheck_allows_test_build",
            "pressure_kind": pressure_kind,
        }
    return None


def _blocker(
    *,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
    reason: str,
    message: str,
    evidence: Sequence[Mapping[str, Any]] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": RUN_ONE_SCHEMA,
        "kind": "closeout_executor_run_one_receipt",
        "status": "blocked",
        "reason": reason,
        "message": message,
        "plan_id": plan.get("plan_id"),
        "action_id": action.get("action_id"),
        "lane": action.get("lane"),
        "evidence": list(evidence or []),
    }
    if extra:
        payload.update(dict(extra))
    return payload


def _unsupported_lane_handoff(action: Mapping[str, Any]) -> dict[str, Any]:
    commands = [str(command) for command in action.get("commands") or [] if str(command)]
    payload: dict[str, Any] = {
        "primary_action": dict(action),
        "owner_commands": commands,
        "required_next_command": commands[0] if commands else None,
    }
    if str(action.get("lane") or "") in {"inspect_diff_review", "publication_gate"}:
        payload.update(
            {
                "manual_review_required": True,
                "review_owner": "current_actor_or_closeout_owner",
                "review_receipt_required": True,
                "typed_closeout_states_after_review": [
                    "landed_local_publication_blocked",
                    "held_foreign_dirty",
                    "held_publication_foreign_dirty",
                    "manual_review_blocked",
                ],
                "review_closeout_contract": {
                    "schema": "closeout_executor_manual_review_contract_v0",
                    "rule": (
                        "Unsupported review lanes are not operator assignments by default. "
                        "Run the safe owner commands when in scope, then close with a typed "
                        "state backed by local landing, dirty-path ownership, and publication "
                        "boundary evidence."
                    ),
                    "required_fields": [
                        "review_command_receipt",
                        "local_landing_or_no_owned_paths_receipt",
                        "remaining_dirty_path_classification",
                        "publication_boundary_status",
                        "reentry_condition",
                    ],
                },
            }
        )
    return payload


def _owner_routed_dirty_state_handoff(action: Mapping[str, Any]) -> dict[str, Any]:
    payload = _unsupported_lane_handoff(action)
    payload["owner_handoff_class"] = str(action.get("reason") or "owner_routed_dirty_state")
    return payload


def _command_like(value: str) -> bool:
    text = value.strip()
    return text.startswith(("./", "git ", "npm ", "npx ", "python", "pytest", "uv "))


def _settlement_owner_commands(payload: Mapping[str, Any]) -> list[str]:
    commands: list[str] = []
    plans: list[Mapping[str, Any]] = [payload]
    before_plan = payload.get("before_plan")
    if isinstance(before_plan, Mapping):
        plans.append(before_plan)
    for plan in plans:
        for owner in plan.get("owners") or []:
            if not isinstance(owner, Mapping):
                continue
            required_action = str(owner.get("required_action") or "").strip()
            command = str(owner.get("owner_required_next_command") or owner.get("required_next_command") or "").strip()
            if (
                required_action
                and required_action != "none"
                and command
                and command != "none"
                and _command_like(command)
                and command not in commands
            ):
                commands.append(command)
        command = str(plan.get("required_next_command") or "").strip()
        if command and command != "none" and _command_like(command) and command not in commands:
            commands.append(command)
    return commands


def _parse_worktree_porcelain_z(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for token in text.split("\0"):
        token = token.strip()
        if not token:
            if current:
                rows.append(current)
                current = {}
            continue
        if token.startswith("worktree "):
            if current:
                rows.append(current)
            current = {"path": token.removeprefix("worktree ").strip()}
            continue
        if token.startswith("HEAD "):
            current["head"] = token.removeprefix("HEAD ").strip()
        elif token.startswith("branch "):
            current["branch"] = token.removeprefix("branch ").strip()
        elif token == "detached":
            current["detached"] = True
        elif token.startswith("locked"):
            current["locked"] = True
            reason = token.removeprefix("locked").strip()
            if reason:
                current["lock_reason"] = reason
        elif token.startswith("prunable"):
            current["prunable"] = True
            reason = token.removeprefix("prunable").strip()
            if reason:
                current["prunable_reason"] = reason
    if current:
        rows.append(current)
    return rows


def _worktree_owner_family(path_text: str) -> str:
    name = Path(path_text).name
    if name.startswith("ai-workflow-portability-clean-"):
        return "portability_clean"
    if name.startswith(("ai_workflow_pub_", "aiw-publication-")):
        return "publication_scratch"
    return "unknown"


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _worktree_path_trust_class(path_text: str, owner_family: str) -> str:
    if owner_family not in {"portability_clean", "publication_scratch"}:
        return "unknown"
    try:
        path = Path(path_text).expanduser().resolve(strict=False)
    except OSError:
        return "unknown"
    temp_roots = [
        Path(tempfile.gettempdir()).resolve(strict=False),
        Path("/tmp").resolve(strict=False),
        Path("/private/tmp").resolve(strict=False),
        Path("/var/tmp").resolve(strict=False),
        Path("/private/var/tmp").resolve(strict=False),
    ]
    for root in temp_roots:
        if _path_is_relative_to(path, root):
            return "trusted_temp_path"
    return "untrusted_path"


def _compact_process_refs(ps_text: str, path_text: str, *, limit: int = 8) -> list[str]:
    name = Path(path_text).name
    refs: list[str] = []
    for line in ps_text.splitlines():
        if not line.strip():
            continue
        if path_text in line or (name and name in line):
            refs.append(re.sub(r"\s+", " ", line).strip())
        if len(refs) >= limit:
            break
    return refs


def _owner_process_refs(ps_text: str, owner_family: str, *, limit: int = 8) -> list[str]:
    tokens_by_family = {
        "portability_clean": (
            "tools/meta/dissemination/portability_gate.py",
            "render_public_projection.py",
            "ai_workflow_public_projection_after_",
        ),
        "publication_scratch": (
            "tools/meta/control/publication_lane.py",
            "ai_workflow_pub_",
            "aiw-publication-",
        ),
    }
    tokens = tokens_by_family.get(owner_family)
    if not tokens:
        return []
    refs: list[str] = []
    for line in ps_text.splitlines():
        if any(token in line for token in tokens):
            refs.append(re.sub(r"\s+", " ", line).strip())
        if len(refs) >= limit:
            break
    return refs


def _worktree_summary_for_receipt(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": row.get("path"),
        "head": row.get("head"),
        "main_head": row.get("main_head"),
        "head_relation": row.get("head_relation"),
        "branch": row.get("branch"),
        "detached": bool(row.get("detached")) or not bool(row.get("branch")),
        "locked": bool(row.get("locked")),
        "lock_reason": row.get("lock_reason"),
        "prunable": bool(row.get("prunable")),
        "prunable_reason": row.get("prunable_reason"),
        "owner_family": row.get("owner_family"),
        "path_trust_class": row.get("path_trust_class"),
        "path_exists": row.get("path_exists"),
        "same_head_as_main": row.get("same_head_as_main"),
        "dirty": row.get("dirty"),
        "status_command": row.get("status_command"),
        "head_relation_error": row.get("head_relation_error"),
        "active_process_refs": row.get("active_process_refs") or [],
        "recommended_action": row.get("recommended_action"),
    }


def _classify_linked_worktrees(
    repo_root: Path,
    *,
    action: Mapping[str, Any],
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    list_result = _invoke_runner(
        runner,
        repo_root,
        ["git", "worktree", "list", "--porcelain", "-z"],
        timeout=30,
        output_limit=20000,
    )
    evidence.append(list_result)
    if not _command_ok(list_result):
        return (
            [],
            evidence,
            [
                {
                    "reason": "WorktreeListFailed",
                    "message": "git worktree list --porcelain -z failed",
                    "recommended_action": "block_unknown",
                }
            ],
        )

    rows = _parse_worktree_porcelain_z(str(list_result.get("stdout") or ""))
    main_head = str((action.get("observed") if isinstance(action.get("observed"), Mapping) else {}) or "")
    observed = action.get("observed") if isinstance(action.get("observed"), Mapping) else {}
    main_head = str(observed.get("head") or "").strip()
    if not main_head:
        plan_head = str(action.get("head") or "").strip()
        main_head = plan_head
    if not main_head:
        rev_result = _invoke_runner(
            runner,
            repo_root,
            ["git", "rev-parse", "HEAD"],
            timeout=30,
            output_limit=2000,
        )
        evidence.append(rev_result)
        main_head = str(rev_result.get("stdout") or "").strip() if _command_ok(rev_result) else ""

    ps_result = _invoke_runner(
        runner,
        repo_root,
        ["ps", "-axo", "pid,ppid,stat,etime,command"],
        timeout=30,
        output_limit=20000,
    )
    evidence.append(ps_result)
    ps_ok = _command_ok(ps_result)
    ps_text = str(ps_result.get("stdout") or "") if ps_ok else ""

    classified: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        path_text = str(raw.get("path") or "")
        if not path_text:
            continue
        path = Path(path_text)
        try:
            is_main = path.resolve() == repo_root
        except OSError:
            is_main = index == 0
        if is_main:
            continue

        owner_family = _worktree_owner_family(path_text)
        path_trust_class = _worktree_path_trust_class(path_text, owner_family)
        active_refs = list(
            dict.fromkeys(
                [
                    *_compact_process_refs(ps_text, path_text),
                    *_owner_process_refs(ps_text, owner_family),
                ]
            )
        )
        path_exists = path.exists()
        detached = bool(raw.get("detached")) or not bool(raw.get("branch"))
        head = str(raw.get("head") or "").strip()
        same_head = bool(main_head and head == main_head)
        row = dict(raw)
        row.update(
            {
                "role": "linked",
                "owner_family": owner_family,
                "path_trust_class": path_trust_class,
                "path_exists": path_exists,
                "detached": detached,
                "same_head_as_main": same_head,
                "main_head": main_head,
                "head_relation": "same_as_main" if same_head else "unchecked",
                "active_process_refs": active_refs,
                "dirty": None,
                "status_command": _worktree_status_probe_command(path_text),
            }
        )

        if not ps_ok:
            row["recommended_action"] = "block_active_process_scan_unknown"
            blockers.append(row)
            classified.append(row)
            continue
        if bool(row.get("locked")):
            row["recommended_action"] = "block_locked"
            blockers.append(row)
            classified.append(row)
            continue
        if active_refs:
            row["recommended_action"] = "wait_active_owner"
            blockers.append(row)
            classified.append(row)
            continue
        if bool(row.get("prunable")) or not path_exists:
            row["recommended_action"] = "prune_missing_admin"
            classified.append(row)
            continue
        if owner_family == "unknown":
            row["recommended_action"] = "block_unknown"
            blockers.append(row)
            classified.append(row)
            continue
        if path_trust_class != "trusted_temp_path":
            row["recommended_action"] = "block_untrusted_path"
            blockers.append(row)
            classified.append(row)
            continue
        if not detached:
            row["recommended_action"] = "block_branch_owned"
            blockers.append(row)
            classified.append(row)
            continue

        status_result = _invoke_runner(
            runner,
            repo_root,
            ["git", "-C", path_text, "status", "--short", "--porcelain=v1", "-uall"],
            timeout=60,
            output_limit=12000,
        )
        evidence.append(status_result)
        if not _command_ok(status_result):
            row["recommended_action"] = "block_status_unknown"
            blockers.append(row)
            classified.append(row)
            continue
        status_rows = [line for line in str(status_result.get("stdout") or "").splitlines() if line.strip()]
        row["dirty"] = bool(status_rows)
        row["status_rows"] = status_rows[:20]
        if status_rows:
            row["recommended_action"] = "block_dirty"
            blockers.append(row)
            classified.append(row)
            continue

        super_result = _invoke_runner(
            runner,
            repo_root,
            ["git", "-C", path_text, "rev-parse", "--show-superproject-working-tree"],
            timeout=30,
            output_limit=4000,
        )
        evidence.append(super_result)
        if _command_ok(super_result) and str(super_result.get("stdout") or "").strip():
            row["recommended_action"] = "block_submodule"
            row["superproject"] = str(super_result.get("stdout") or "").strip()
            blockers.append(row)
            classified.append(row)
            continue

        if same_head:
            row["recommended_action"] = "remove_clean_temp"
            classified.append(row)
            continue

        if not head or not main_head:
            row["head_relation"] = "unknown"
            row["recommended_action"] = "block_head_relation_unknown"
            blockers.append(row)
            classified.append(row)
            continue

        ancestor_result = _invoke_runner(
            runner,
            repo_root,
            ["git", "merge-base", "--is-ancestor", head, main_head],
            timeout=30,
            output_limit=4000,
        )
        evidence.append(ancestor_result)
        ancestor_returncode = int(ancestor_result.get("returncode") or 0)
        if ancestor_returncode == 0:
            row["head_relation"] = "ancestor_of_main"
            row["recommended_action"] = "remove_stale_clean_temp"
            classified.append(row)
            continue
        if ancestor_returncode == 1:
            row["head_relation"] = "not_ancestor_of_main"
            row["recommended_action"] = "block_unexpected_head"
            blockers.append(row)
            classified.append(row)
            continue

        row["head_relation"] = "unknown"
        row["recommended_action"] = "block_head_relation_unknown"
        row["head_relation_error"] = str(ancestor_result.get("stderr") or ancestor_result.get("stdout") or "").strip()
        blockers.append(row)
        classified.append(row)
        continue

    return classified, evidence, blockers


def _worktree_blocker_reason(row: Mapping[str, Any]) -> tuple[str, str]:
    action = str(row.get("recommended_action") or "")
    if action == "wait_active_owner":
        return "WorktreeActiveOwner", "linked worktree has active owner processes; retry after they exit"
    if action == "block_locked":
        return "WorktreeLocked", "linked worktree is locked; owner must unlock or remove it"
    if action == "block_dirty":
        return "WorktreeDirty", "linked worktree has dirty or untracked paths"
    if action == "block_unknown":
        return "WorktreeUnknownOwner", "linked worktree owner family is unknown"
    if action == "block_branch_owned":
        return "WorktreeBranchOwned", "linked worktree is branch-owned rather than detached disposable work"
    if action == "block_unexpected_head":
        return "WorktreeUnexpectedHead", "linked worktree HEAD does not match the main checkout HEAD"
    if action == "block_head_relation_unknown":
        return "WorktreeHeadRelationUnknown", "linked worktree HEAD relationship to main could not be verified"
    if action == "block_status_unknown":
        return "WorktreeStatusUnknown", "linked worktree status could not be read"
    if action == "block_submodule":
        return "WorktreeSubmodule", "linked worktree appears to be inside a superproject/submodule context"
    if action == "block_active_process_scan_unknown":
        return "WorktreeActiveProcessScanUnknown", "active process scan failed; worktree removal is not safe"
    if action == "block_untrusted_path":
        return "WorktreeUntrustedPath", "linked worktree basename matches a known family but path is not under a trusted temp root"
    return "WorktreeUnknownState", "linked worktree actionability is unknown"


def _worktree_blocker_required_command(row: Mapping[str, Any], reason: str, action: Mapping[str, Any]) -> str | None:
    status_command = str(row.get("status_command") or "").strip()
    path_text = str(row.get("path") or "").strip()
    if reason in {"WorktreeDirty", "WorktreeStatusUnknown"} and status_command:
        return status_command
    if reason == "WorktreeActiveOwner":
        return "ps -axo pid,ppid,stat,etime,command"
    if reason == "WorktreeLocked":
        return "git worktree list --verbose"
    if reason == "WorktreeBranchOwned" and path_text:
        return f"git -C {shlex.quote(path_text)} branch --show-current"
    commands = [str(command) for command in action.get("commands") or [] if str(command).strip()]
    return commands[0] if commands else None


def _run_drain_worktrees(
    repo_root: Path,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    classified, evidence, blockers = _classify_linked_worktrees(
        repo_root,
        action={"observed": plan.get("observed") if isinstance(plan.get("observed"), Mapping) else {}, **dict(action)},
        runner=runner,
    )
    linked = [_worktree_summary_for_receipt(row) for row in classified]
    if not classified:
        return {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "no_action",
            "reason": "NoLinkedWorktrees",
            "message": "no linked worktrees remain",
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "evidence": evidence,
            "linked_worktrees": [],
            "next_step": "replan",
        }

    if blockers:
        first = blockers[0]
        reason, message = _worktree_blocker_reason(first)
        required_next_command = _worktree_blocker_required_command(first, reason, action)
        return _blocker(
            plan=plan,
            action=action,
            reason=reason,
            message=message,
            evidence=evidence,
            extra={
                "linked_worktrees": linked,
                "blocked_worktree": _worktree_summary_for_receipt(first),
                "owner_commands": _uniq_text([*(action.get("commands") or []), required_next_command]),
                "required_next_command": required_next_command,
                "retry_policy": "retry_after_owner_process_exits_then_replan"
                if reason == "WorktreeActiveOwner"
                else None,
            },
        )

    prunable = [row for row in classified if row.get("recommended_action") == "prune_missing_admin"]
    if prunable:
        prune_result = _invoke_runner(
            runner,
            repo_root,
            ["./repo-git", "worktree", "prune"],
            timeout=300,
            output_limit=12000,
        )
        evidence.append(prune_result)
        if not _command_ok(prune_result):
            return _blocker(
                plan=plan,
                action=action,
                reason="WorktreePruneFailed",
                message="repo-git worktree prune failed for prunable linked worktree metadata",
                evidence=evidence,
                extra={"linked_worktrees": linked},
            )
        post = _invoke_runner(
            runner,
            repo_root,
            ["git", "worktree", "list", "--porcelain", "-z"],
            timeout=30,
            output_limit=20000,
        )
        evidence.append(post)
        if not _command_ok(post):
            return _blocker(
                plan=plan,
                action=action,
                reason="WorktreePostcheckFailed",
                message="git worktree list failed after pruning linked worktree metadata",
                evidence=evidence,
                extra={"linked_worktrees": linked},
            )
        post_paths = {str(row.get("path") or "") for row in _parse_worktree_porcelain_z(str(post.get("stdout") or ""))}
        remaining = [str(row.get("path")) for row in prunable if str(row.get("path")) in post_paths]
        if remaining:
            return _blocker(
                plan=plan,
                action=action,
                reason="WorktreePrunePostcheckFailed",
                message="one or more prunable linked worktree entries remained after prune",
                evidence=evidence,
                extra={"linked_worktrees": linked, "remaining_paths": remaining},
            )
        return {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "executed",
            "reason": "WorktreePruned",
            "message": "pruned stale linked worktree administrative metadata",
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "linked_worktrees": linked,
            "paths": [str(row.get("path")) for row in prunable],
            "evidence": evidence,
            "next_step": "replan",
        }

    removable = [
        row
        for row in classified
        if row.get("recommended_action") in {"remove_clean_temp", "remove_stale_clean_temp"}
    ]
    if removable:
        row = removable[0]
        path_text = str(row.get("path") or "")
        remove_result = _invoke_runner(
            runner,
            repo_root,
            ["./repo-git", "worktree", "remove", path_text],
            timeout=300,
            output_limit=12000,
        )
        evidence.append(remove_result)
        if not _command_ok(remove_result):
            return _blocker(
                plan=plan,
                action=action,
                reason="WorktreeRemoveFailed",
                message="repo-git worktree remove failed for clean detached temp worktree",
                evidence=evidence,
                extra={"linked_worktrees": linked, "path": path_text},
            )
        post = _invoke_runner(
            runner,
            repo_root,
            ["git", "worktree", "list", "--porcelain", "-z"],
            timeout=30,
            output_limit=20000,
        )
        evidence.append(post)
        if not _command_ok(post):
            return _blocker(
                plan=plan,
                action=action,
                reason="WorktreePostcheckFailed",
                message="git worktree list failed after removing linked worktree",
                evidence=evidence,
                extra={"linked_worktrees": linked, "path": path_text},
            )
        post_paths = {str(row.get("path") or "") for row in _parse_worktree_porcelain_z(str(post.get("stdout") or ""))}
        if path_text in post_paths:
            return _blocker(
                plan=plan,
                action=action,
                reason="WorktreeRemovePostcheckFailed",
                message="linked worktree remained in git worktree list after remove",
                evidence=evidence,
                extra={"linked_worktrees": linked, "path": path_text},
            )
        return {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "executed",
            "reason": "WorktreeStaleCleanTempRemoved"
            if row.get("recommended_action") == "remove_stale_clean_temp"
            else "WorktreeRemoved",
            "message": "removed clean detached trusted temp linked worktree whose HEAD is an ancestor of main HEAD"
            if row.get("recommended_action") == "remove_stale_clean_temp"
            else "removed clean detached temp linked worktree",
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "linked_worktrees": linked,
            "path": path_text,
            "head": row.get("head"),
            "main_head": row.get("main_head"),
            "head_relation": row.get("head_relation"),
            "path_trust_class": row.get("path_trust_class"),
            "owner_family": row.get("owner_family"),
            "evidence": evidence,
            "next_step": "replan",
        }

    return _blocker(
        plan=plan,
        action=action,
        reason="WorktreeNoSafeAction",
        message="linked worktrees were observed but no safe remove/prune action was available",
        evidence=evidence,
        extra={"linked_worktrees": linked, "owner_commands": action.get("commands") or []},
    )


def _stale_reverse_index_rows(quarantine: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = quarantine.get("rows")
    if not isinstance(rows, Sequence):
        return []
    stale: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        path = str(row.get("path") or "").strip("/")
        state = row.get("index_entry_state") if isinstance(row.get("index_entry_state"), Mapping) else {}
        if not path or str(state.get("status") or "") != "stale_reverse_index_entry":
            continue
        if _is_generated_path(path):
            continue
        if not (state.get("worktree_matches_head") and not state.get("index_matches_head")):
            continue
        if state.get("worktree_matches_index"):
            continue
        stale.append(dict(row))
    return stale


def _stale_reverse_index_paths(quarantine: Mapping[str, Any]) -> list[str]:
    return list(dict.fromkeys(str(row.get("path") or "") for row in _stale_reverse_index_rows(quarantine)))


def _staged_paths_from_quarantine(quarantine: Mapping[str, Any]) -> list[str]:
    rows = quarantine.get("rows")
    if not isinstance(rows, Sequence):
        return []
    return [
        str(row.get("path") or "")
        for row in rows
        if isinstance(row, Mapping) and str(row.get("path") or "")
    ]


def _staged_index_quarantine(
    repo_root: Path,
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = _invoke_runner(
        runner,
        repo_root,
        [
            "./repo-python",
            "tools/meta/control/mission_transaction_preflight.py",
            "--repo-root",
            str(repo_root),
            "--staged-index-quarantine",
        ],
        timeout=300,
        output_limit=12000,
    )
    payload = _json_stdout(result)
    return (payload if payload else {}, result)


def _hygiene_receipt(
    *,
    status: str,
    reason: str,
    message: str,
    evidence: Sequence[Mapping[str, Any]] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": HYGIENE_SCHEMA,
        "kind": "closeout_executor_hygiene_receipt",
        "status": status,
        "reason": reason,
        "message": message,
        "evidence": list(evidence or []),
    }
    if extra:
        payload.update(dict(extra))
    return payload


def _run_stale_reverse_index_hygiene(
    repo_root: Path,
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
    max_repairs: int = 20,
) -> dict[str, Any]:
    if max_repairs <= 0:
        return _hygiene_receipt(
            status="no_action",
            reason="StaleReverseIndexHygieneBudgetExhausted",
            message="stale reverse index hygiene budget is exhausted",
        )
    preflight, preflight_result = _staged_index_quarantine(repo_root, runner=runner)
    evidence: list[dict[str, Any]] = [preflight_result]
    if not _command_ok(preflight_result):
        return _hygiene_receipt(
            status="blocked",
            reason="StagedIndexQuarantineFailed",
            message="mission_transaction_preflight staged-index quarantine failed",
            evidence=evidence,
        )
    stale_paths = _stale_reverse_index_paths(preflight)
    if not stale_paths:
        return _hygiene_receipt(
            status="no_action",
            reason="NoStaleReverseIndexEntries",
            message="no exact stale reverse index entries were classified",
            evidence=evidence,
        )

    repair_paths = stale_paths[:max_repairs]
    reset_result = _invoke_runner(
        runner,
        repo_root,
        ["./repo-git", "reset", "--", *repair_paths],
        timeout=300,
        output_limit=12000,
    )
    evidence.append(reset_result)
    if not _command_ok(reset_result):
        return _hygiene_receipt(
            status="blocked",
            reason="StaleReverseIndexResetFailed",
            message="repo-git reset failed for exact stale reverse index entries",
            evidence=evidence,
            extra={"paths": repair_paths},
        )

    postflight, postflight_result = _staged_index_quarantine(repo_root, runner=runner)
    evidence.append(postflight_result)
    remaining_repaired = [path for path in repair_paths if path in _stale_reverse_index_paths(postflight)]
    if remaining_repaired:
        return _hygiene_receipt(
            status="blocked",
            reason="StaleReverseIndexPostcheckFailed",
            message="one or more exact stale reverse index entries remained after reset",
            evidence=evidence,
            extra={"paths": repair_paths, "remaining_paths": remaining_repaired},
        )

    post_staged = _staged_paths_from_quarantine(postflight)
    return _hygiene_receipt(
        status="executed",
        reason="StaleReverseIndexEntriesCleared",
        message="cleared exact stale reverse index entries using mission preflight classification",
        evidence=evidence,
        extra={
            "paths": repair_paths,
            "path_count": len(repair_paths),
            "paths_truncated": len(stale_paths) > len(repair_paths),
            "preserved_staged_paths": [path for path in post_staged if path not in set(repair_paths)],
            "next_step": "replan",
            "evidence_summary": {
                "classifier": "mission_transaction_preflight.shared_index_quarantine_v0",
                "head_equals_worktree": True,
                "index_differs": True,
                "head_worktree_diff_empty": True,
            },
        },
    )


def _typescript_error_paths(text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for match in TS_ERROR_PATH_RE.finditer(text):
        path = "system/server/ui/" + match.group(1)
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def _ui_effect_blocker_analysis(
    *,
    blocked_cluster: Mapping[str, Any],
    command_result: Mapping[str, Any],
    ui_status_rows: Sequence[Mapping[str, str]],
    blocker_ref: str | None = None,
) -> dict[str, Any]:
    cluster_paths = {str(path) for path in blocked_cluster.get("paths") or []}
    dirty_by_path = {str(row.get("path") or ""): str(row.get("xy") or "") for row in ui_status_rows}
    error_paths = _typescript_error_paths(
        "\n".join(
            [
                str(command_result.get("stdout") or ""),
                str(command_result.get("stderr") or ""),
            ]
        )
    )
    files: list[dict[str, Any]] = []
    for path in error_paths:
        dirty_status = dirty_by_path.get(path)
        inside_cluster = path in cluster_paths
        if inside_cluster:
            fix_lane = "direct_fix"
            cluster_candidate = blocked_cluster.get("cluster_id")
        elif dirty_status and _is_source_candidate(path):
            fix_lane = "dependency_cluster"
            cluster_candidate = f"source_test:{_module_stem(path)}"
        elif path.startswith("system/server/ui/src/"):
            fix_lane = "baseline_debt"
            cluster_candidate = f"source_test:{_module_stem(path)}"
        else:
            fix_lane = "unknown"
            cluster_candidate = None
        files.append(
            {
                "path": path,
                "dirty_status": dirty_status,
                "inside_blocked_cluster": inside_cluster,
                "cluster_candidate": cluster_candidate,
                "fix_lane": fix_lane,
            }
        )
    if not files:
        selected_next_action = "effect_command_failed_without_parseable_type_errors"
    elif any(item["fix_lane"] == "direct_fix" for item in files):
        selected_next_action = "fix_blocked_ui_cluster"
    elif any(item["fix_lane"] == "dependency_cluster" for item in files):
        selected_next_action = "drain_dependency_cluster"
    elif all(item["fix_lane"] == "baseline_debt" for item in files):
        selected_next_action = "defer_blocked_ui_cluster_continue_non_ui_drain"
    else:
        selected_next_action = "classify_ui_effect_blocker_manually"
    return {
        "blocked_cluster": blocked_cluster.get("cluster_id"),
        "build_command": command_result.get("command"),
        "error_files": files,
        "selected_next_action": selected_next_action,
        "blocker_ref": blocker_ref or UI_EFFECT_BLOCKER_REFS[0],
    }


def _targeted_effect_modes(effect: Mapping[str, Any]) -> list[dict[str, Any]]:
    modes = effect.get("proof_modes") if isinstance(effect.get("proof_modes"), Sequence) else []
    targeted: list[dict[str, Any]] = []
    for mode in modes:
        if not isinstance(mode, Mapping):
            continue
        if str(mode.get("mode") or "") == "production_build":
            continue
        commands = [str(command) for command in mode.get("commands") or []]
        if commands:
            targeted.append({"mode": str(mode.get("mode") or "targeted_effect"), "commands": commands})
    return targeted


def _targeted_effect_allowed(blocker_analysis: Mapping[str, Any]) -> bool:
    error_files = blocker_analysis.get("error_files")
    if not isinstance(error_files, Sequence) or not error_files:
        return False
    for item in error_files:
        if not isinstance(item, Mapping):
            return False
        if item.get("inside_blocked_cluster"):
            return False
        if str(item.get("fix_lane") or "") != "baseline_debt":
            return False
    return True


def _current_head(
    repo_root: Path,
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]]:
    result = _invoke_runner(runner, repo_root, ["git", "rev-parse", "HEAD"], timeout=60)
    return str(result.get("stdout") or "").strip(), result


def _task_ledger_source_digest(repo_root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    rel_paths = list(TASK_LEDGER_SOURCE_AUTHORITY_PATHS)
    for pattern in TASK_LEDGER_SOURCE_AUTHORITY_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file():
                continue
            rel_path = path.relative_to(repo_root).as_posix()
            if rel_path not in seen:
                rel_paths.append(rel_path)
                seen.add(rel_path)
    for rel_path in rel_paths:
        path = repo_root / rel_path
        try:
            data = path.read_bytes()
            exists = True
        except OSError:
            data = b""
            exists = False
        path_digest = hashlib.sha256(data).hexdigest() if exists else None
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(b"1" if exists else b"0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        rows.append(
            {
                "path": rel_path,
                "exists": exists,
                "size": len(data),
                "sha256": f"sha256:{path_digest}" if path_digest else None,
            }
        )
    return {
        "schema": "task_ledger_source_digest_v0",
        "digest": f"sha256:{digest.hexdigest()}",
        "paths": rows,
    }


def _active_task_ledger_writer_processes(
    repo_root: Path,
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = _invoke_runner(
        runner,
        repo_root,
        ["ps", "-axo", "pid,ppid,stat,etime,command"],
        timeout=60,
        output_limit=20000,
    )
    rows: list[dict[str, Any]] = []
    for raw in str(result.get("stdout") or "").splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("pid "):
            continue
        if "rg " in line:
            continue
        is_task_ledger_writer = "task_ledger_apply.py" in line and any(
            token in line for token in TASK_LEDGER_WRITER_TOKENS
        )
        is_generated_settle = (
            "generated_state_drainer.py" in line
            and "settle" in line
            and "--dry-run" not in line
            and "settlement-plan" not in line
        )
        if not is_task_ledger_writer and not is_generated_settle:
            continue
        parts = line.split(None, 4)
        if len(parts) == 5:
            pid, ppid, stat, elapsed, command = parts
        else:
            pid = ppid = stat = elapsed = ""
            command = line
        rows.append(
            {
                "pid": pid,
                "ppid": ppid,
                "stat": stat,
                "elapsed": elapsed,
                "command": command,
            }
        )
    return rows[:10], result


def _staged_index_rows(
    repo_root: Path,
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    result = _invoke_runner(
        runner,
        repo_root,
        ["git", "diff", "--cached", "--name-status"],
        timeout=60,
        output_limit=20000,
    )
    rows: list[dict[str, str]] = []
    for raw in str(result.get("stdout") or "").splitlines():
        parts = raw.split("\t")
        if len(parts) >= 2:
            rows.append({"status": parts[0], "path": parts[-1]})
    return rows, result


def _staged_index_paths(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    paths: set[str] = set()
    for row in rows:
        path = str(row.get("path") or "").strip()
        if path:
            paths.add(path)
    return paths


def _index_rows_for_paths(rows: Sequence[Mapping[str, Any]], paths: set[str]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for row in rows:
        path = str(row.get("path") or "").strip()
        if path in paths:
            selected.append({"status": str(row.get("status") or ""), "path": path})
    return selected


def _closeout_stop_state_integrity(
    repo_root: Path,
    *,
    reason: str,
    pre_staged_rows: Sequence[Mapping[str, Any]],
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    initial_rows, initial_result = _staged_index_rows(repo_root, runner=runner)
    evidence: list[dict[str, Any]] = [initial_result]
    pre_paths = _staged_index_paths(pre_staged_rows)
    initial_paths = _staged_index_paths(initial_rows)
    introduced_paths = sorted(initial_paths - pre_paths)
    cleanup_attempted = False
    cleanup_succeeded: bool | None = None
    cleanup_result: dict[str, Any] | None = None
    final_rows = list(initial_rows)

    if introduced_paths:
        cleanup_attempted = True
        cleanup_result = _invoke_runner(
            runner,
            repo_root,
            ["./repo-git", "reset", "--", *introduced_paths],
            timeout=300,
            output_limit=12000,
        )
        evidence.append(cleanup_result)
        cleanup_succeeded = _command_ok(cleanup_result)
        if cleanup_succeeded:
            final_rows, final_result = _staged_index_rows(repo_root, runner=runner)
            evidence.append(final_result)

    final_paths = _staged_index_paths(final_rows)
    if final_rows:
        status = "cleanup_failed" if cleanup_attempted and not cleanup_succeeded else "residue_reported"
    elif cleanup_attempted:
        status = "cleaned"
    else:
        status = "passed"
    return (
        {
            "schema": STOP_INTEGRITY_SCHEMA,
            "status": status,
            "reason": reason,
            "pre_index_clean": not bool(pre_staged_rows),
            "pre_staged_path_count": len(pre_paths),
            "post_index_clean": not bool(final_rows),
            "post_staged_path_count": len(final_paths),
            "initial_post_index_clean": not bool(initial_rows),
            "initial_post_staged_path_count": len(initial_paths),
            "initial_staged_residue_paths": list(initial_rows),
            "staged_paths_introduced_during_action": introduced_paths,
            "staged_residue_paths": list(final_rows),
            "external_staged_paths": _index_rows_for_paths(final_rows, pre_paths),
            "index_cleanup": {
                "attempted": cleanup_attempted,
                "policy": "unstage_only_paths_introduced_after_closeout_pre_index_snapshot",
                "paths": introduced_paths,
                "succeeded": cleanup_succeeded,
                "worktree_content_preserved": True,
                "command": cleanup_result.get("command") if cleanup_result else None,
            },
        },
        evidence,
    )


def _path_status(
    repo_root: Path,
    paths: Sequence[str],
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    command = ["git", "status", "--short", "--porcelain=v1", "-uall", "--", *paths]
    return _invoke_runner(runner, repo_root, command, timeout=60)


def _status_rows_with_evidence(
    repo_root: Path,
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    result = _invoke_runner(
        runner,
        repo_root,
        ["git", "status", "--short", "--porcelain=v1", "-uall"],
        timeout=60,
        output_limit=60000,
    )
    if not _command_ok(result):
        return [], result
    return _parse_status_rows(str(result.get("stdout") or "")), result


def _staged_rows_from_status(status_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _parse_status_rows(status_text):
        xy = str(row.get("xy") or "")
        path = str(row.get("path") or "")
        index_status = xy[:1]
        if index_status and index_status not in {" ", "?"}:
            rows.append({"xy": xy, "path": path})
    return rows


def _work_ledger_mutation_check(
    repo_root: Path,
    paths: Sequence[str],
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    command = [
        "./repo-python",
        "tools/meta/factory/work_ledger.py",
        "mutation-check",
        "--require-exclusive",
    ]
    for path in paths:
        command.extend(["--path", str(path)])
    result = _invoke_runner(runner, repo_root, command, timeout=120, output_limit=12000)
    payload = _json_stdout(result)
    return (payload if payload else {}, result)


def _mutation_check_commands(paths: Sequence[str]) -> list[str]:
    path_args = " ".join(f"--path {path}" for path in paths)
    return [
        f"./repo-python tools/meta/factory/work_ledger.py mutation-check {path_args} --require-exclusive",
        "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 30",
    ]


def _run_validation_commands(
    repo_root: Path,
    commands: Sequence[str],
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    for command in commands:
        result = _invoke_runner(runner, repo_root, command, shell=True, timeout=900)
        evidence.append(result)
        if not _command_ok(result):
            return False, evidence
    return True, evidence


def _scoped_commit_command(
    paths: Sequence[str],
    message: str,
    expected_parent: str,
    *,
    allow_untracked: bool = False,
) -> list[str]:
    command = [
        "./repo-python",
        "tools/meta/control/scoped_commit.py",
        "full-paths",
    ]
    for path in paths:
        command.extend(["--path", path])
    if allow_untracked or any(_is_test_path(path) for path in paths):
        command.append("--allow-untracked")
    command.extend(
        [
            "--allow-multi-hunk-full-paths",
            "--remote-fallback-on-metadata-block",
            "--expected-parent",
            expected_parent,
            "--message",
            message,
        ]
    )
    return command


def _verify_remote_ref(
    repo_root: Path,
    expected_head: str,
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    remote_result = _invoke_runner(
        runner,
        repo_root,
        ["git", "ls-remote", "origin", "refs/heads/main"],
        timeout=120,
    )
    evidence = [remote_result]
    remote_stdout = str(remote_result.get("stdout") or "").strip()
    remote_oid = remote_stdout.split()[0] if remote_stdout else ""
    return bool(remote_oid and remote_oid == expected_head), evidence


def _guarded_push_command_from_audit(
    audit: Mapping[str, Any],
    *,
    expected_source: str | None = None,
) -> tuple[list[str] | None, dict[str, Any] | None]:
    source_sha = str(expected_source or audit.get("head") or "").strip()
    remote_sha = str(audit.get("remote_oid") or "").strip()
    target_ref = str(audit.get("target_ref") or "refs/heads/main").strip()
    remote_name = str(audit.get("remote_name") or "origin").strip()
    missing = [
        name
        for name, value in (
            ("expected_source", source_sha),
            ("expected_remote", remote_sha),
            ("target_ref", target_ref),
            ("remote_name", remote_name),
        )
        if not value
    ]
    identity = {
        "expected_source": source_sha or None,
        "expected_remote": remote_sha or None,
        "target_ref": target_ref or None,
        "remote_name": remote_name or None,
    }
    if missing:
        return None, {"missing": missing, **identity}
    return [
        "./repo-python",
        "run_git.py",
        "push",
        "guarded",
        "--remote-name",
        remote_name,
        "--source-ref",
        "HEAD",
        "--target-ref",
        target_ref,
        "--expected-source",
        source_sha,
        "--expected-remote",
        remote_sha,
        "--json",
    ], identity


def _run_guarded_push_from_audit(
    repo_root: Path,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
    audit: Mapping[str, Any],
    *,
    expected_source: str,
    runner: Callable[..., Mapping[str, Any]] | None = None,
    evidence: list[dict[str, Any]],
    blocker_reason: str,
    blocker_message: str,
    extra: Mapping[str, Any] | None = None,
) -> tuple[bool, dict[str, Any] | None, dict[str, Any] | None]:
    command, identity = _guarded_push_command_from_audit(audit, expected_source=expected_source)
    if command is None:
        blocked_extra = {"guarded_push_identity": identity}
        if extra:
            blocked_extra.update(dict(extra))
        return False, _blocker(
            plan=plan,
            action=action,
            reason="GuardedPushIdentityMissing",
            message="push audit did not provide the source and remote identities required for guarded publication",
            evidence=evidence,
            extra=blocked_extra,
        ), None
    push_result = _invoke_runner(runner, repo_root, command, timeout=900, output_limit=60000)
    evidence.append(push_result)
    push_receipt = _json_stdout(push_result)
    if not _command_ok(push_result) or push_receipt.get("status") != "pushed":
        blocked_extra = {
            "guarded_push_identity": identity,
            "guarded_push_receipt": push_receipt or None,
        }
        if extra:
            blocked_extra.update(dict(extra))
        return False, _blocker(
            plan=plan,
            action=action,
            reason=blocker_reason,
            message=blocker_message,
            evidence=evidence,
            extra=blocked_extra,
        ), push_receipt
    return True, None, push_receipt


def _run_publish_if_clear(
    repo_root: Path,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    audit_result = _invoke_runner(
        runner,
        repo_root,
        ["./repo-python", "run_git.py", "audit", "push", "--json"],
        timeout=300,
    )
    evidence.append(audit_result)
    audit = _json_stdout(audit_result)
    if not _command_ok(audit_result) or audit.get("status") != "clear" or audit.get("blocked_reasons"):
        return _blocker(
            plan=plan,
            action=action,
            reason="PushAuditNotClear",
            message="push audit did not return a clear publication lane",
            evidence=evidence,
        )
    ahead = _int_value(audit.get("ahead"))
    if ahead <= 0:
        head = str(audit.get("head") or "")
        verified = bool(audit.get("remote_ref_verified"))
        return {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "no_action",
            "reason": "AlreadyPublished",
            "message": "push audit reports no local commits ahead of origin/main",
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "head": head,
            "remote_verified": verified,
            "evidence": evidence,
        }

    audited_head = str(audit.get("head") or "")
    ok, blocker, push_receipt = _run_guarded_push_from_audit(
        repo_root,
        plan,
        action,
        audit,
        expected_source=audited_head,
        runner=runner,
        evidence=evidence,
        blocker_reason="GuardedPushFailed",
        blocker_message="guarded push failed or refused the audited publication identity",
    )
    if not ok:
        return blocker or _blocker(
            plan=plan,
            action=action,
            reason="GuardedPushFailed",
            message="guarded push failed or refused the audited publication identity",
            evidence=evidence,
        )
    head, head_result = _current_head(repo_root, runner=runner)
    evidence.append(head_result)
    if audited_head and head != audited_head:
        return _blocker(
            plan=plan,
            action=action,
            reason="LocalHeadChangedAfterGuardedPush",
            message="local HEAD no longer equals the audited commit after guarded push",
            evidence=evidence,
            extra={"audited_head": audited_head, "current_head": head, "guarded_push_receipt": push_receipt},
        )
    verified, verify_evidence = _verify_remote_ref(repo_root, head, runner=runner)
    evidence.extend(verify_evidence)
    if not verified:
        return _blocker(
            plan=plan,
            action=action,
            reason="RemoteRefVerificationFailed",
            message="origin/main did not verify to current HEAD after push",
            evidence=evidence,
        )
    return {
        "schema": RUN_ONE_SCHEMA,
        "kind": "closeout_executor_run_one_receipt",
        "status": "executed",
        "reason": "PublishedLocalAhead",
        "message": "pushed local commits and verified origin/main",
        "plan_id": plan.get("plan_id"),
        "action_id": action.get("action_id"),
        "lane": action.get("lane"),
        "commit": head,
        "remote_verified": True,
        "guarded_push_receipt": push_receipt,
        "evidence": evidence,
    }


def _settlement_plan_refresh_required(payload: Mapping[str, Any]) -> bool:
    haystack = json.dumps(payload, sort_keys=True).lower()
    return "projection_not_fresh" in haystack or "refresh_required" in haystack


def _run_settle_generated_state(
    repo_root: Path,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    source_digest_before = _task_ledger_source_digest(repo_root)
    active_writers_before, active_writers_before_result = _active_task_ledger_writer_processes(
        repo_root,
        runner=runner,
    )
    evidence.append(active_writers_before_result)
    if active_writers_before:
        staged_rows, staged_result = _staged_index_rows(repo_root, runner=runner)
        evidence.append(staged_result)
        return _blocker(
            plan=plan,
            action=action,
            reason="GeneratedStateWriterActive",
            message="generated-state settlement is blocked by an active Task Ledger or generated-state writer",
            evidence=evidence,
            extra={
                "residual_class": "writer_active",
                "source_digest_before": source_digest_before,
                "active_task_ledger_processes": active_writers_before,
                "staged_external_paths": staged_rows,
                "required_next_command": "./repo-python tools/meta/control/closeout_executor.py run-one --json --compact after the writer exits",
            },
        )

    status_result = _invoke_runner(
        runner,
        repo_root,
        ["./repo-python", "tools/meta/control/generated_state_drainer.py", "status", "--compact"],
        timeout=600,
        output_limit=60000,
    )
    evidence.append(status_result)
    plan_result = _invoke_runner(
        runner,
        repo_root,
        ["./repo-python", "tools/meta/control/generated_state_drainer.py", "settlement-plan", "--fast"],
        timeout=600,
        output_limit=120000,
    )
    evidence.append(plan_result)
    settlement_plan = _json_stdout(plan_result)
    if not _command_ok(plan_result) or not settlement_plan:
        return _blocker(
            plan=plan,
            action=action,
            reason="GeneratedStatePlanFailed",
            message="generated-state settlement plan failed or did not emit JSON",
            evidence=evidence,
        )
    if settlement_plan.get("status") == "clean":
        status_rows, status_rows_result = _status_rows_with_evidence(repo_root, runner=runner)
        evidence.append(status_rows_result)
        generated_paths = sorted(
            {
                str(row.get("path") or "")
                for row in status_rows
                if _is_generated_path(str(row.get("path") or ""))
            }
        )
        if generated_paths:
            return _blocker(
                plan=plan,
                action=action,
                reason="GeneratedStateSettlementCleanButGeneratedDirtRemains",
                message=(
                    "generated-state owner settlement plan is clean, but generated-looking dirty paths remain "
                    "outside the settled owner lane"
                ),
                evidence=evidence,
                extra={
                    "generated_paths": generated_paths[:50],
                    "generated_path_count": len(generated_paths),
                    "owner_route": "generated_dirt_outside_registered_settlement_owner",
                    "required_next_command": GENERATED_DIRT_OWNER_REVIEW_COMMAND,
                    "index_quarantine_proof_command": (
                        "./repo-python tools/meta/control/mission_transaction_preflight.py --staged-index-quarantine"
                    ),
                },
            )
        return {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "no_action",
            "reason": "GeneratedStateAlreadySettled",
            "message": "generated-state owner settlement plan is already clean",
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "evidence": evidence,
        }
    if not settlement_plan.get("can_settle") or settlement_plan.get("blocked_by"):
        reason = (
            "GeneratedStateRefreshRequired"
            if _settlement_plan_refresh_required(settlement_plan)
            else "GeneratedStateSettlementNotApplySafe"
        )
        return _blocker(
            plan=plan,
            action=action,
            reason=reason,
            message="generated-state owner settlement plan is not apply-safe",
            evidence=evidence,
            extra={
                "blocked_by": settlement_plan.get("blocked_by") or [],
                "required_next_command": settlement_plan.get("required_next_command"),
            },
        )

    pre_staged_rows, pre_staged_result = _staged_index_rows(repo_root, runner=runner)
    evidence.append(pre_staged_result)
    before_head, before_head_result = _current_head(repo_root, runner=runner)
    evidence.append(before_head_result)
    if not before_head:
        return _blocker(
            plan=plan,
            action=action,
            reason="HeadReadFailed",
            message="could not read current HEAD before generated-state settlement",
            evidence=evidence,
        )

    settle_result = _invoke_runner(
        runner,
        repo_root,
        [
            "./repo-python",
            "tools/meta/control/generated_state_drainer.py",
            "settle",
            "--max-passes",
            "3",
        ],
        timeout=1800,
        output_limit=160000,
    )
    evidence.append(settle_result)
    settle_payload = _json_stdout(settle_result)
    after_head, after_head_result = _current_head(repo_root, runner=runner)
    evidence.append(after_head_result)
    head_advanced = bool(after_head and after_head != before_head)
    commit_hashes: list[str] = []
    progress = settle_payload.get("progress") if isinstance(settle_payload.get("progress"), Mapping) else {}
    if isinstance(progress.get("commit_hashes"), list):
        commit_hashes = [str(value) for value in progress.get("commit_hashes") or [] if value]
    if head_advanced and after_head not in commit_hashes:
        commit_hashes.append(after_head)

    remote_verified = False
    if head_advanced:
        audit_result = _invoke_runner(
            runner,
            repo_root,
            ["./repo-python", "run_git.py", "audit", "push", "--json"],
            timeout=300,
            output_limit=60000,
        )
        evidence.append(audit_result)
        audit = _json_stdout(audit_result)
        if not _command_ok(audit_result) or audit.get("status") != "clear" or audit.get("blocked_reasons"):
            return _blocker(
                plan=plan,
                action=action,
                reason="PushAuditNotClearAfterGeneratedSettlement",
                message="generated-state settlement committed locally, but push audit is not clear",
                evidence=evidence,
                extra={"commits": commit_hashes},
            )
        ok, blocker, push_receipt = _run_guarded_push_from_audit(
            repo_root,
            plan,
            action,
            audit,
            expected_source=after_head,
            runner=runner,
            evidence=evidence,
            blocker_reason="GuardedPushFailedAfterGeneratedSettlement",
            blocker_message="generated-state settlement committed locally, but guarded push failed",
            extra={"commits": commit_hashes},
        )
        if not ok:
            return blocker or _blocker(
                plan=plan,
                action=action,
                reason="GuardedPushFailedAfterGeneratedSettlement",
                message="generated-state settlement committed locally, but guarded push failed",
                evidence=evidence,
                extra={"commits": commit_hashes},
            )
        remote_verified, verify_evidence = _verify_remote_ref(repo_root, after_head, runner=runner)
        evidence.extend(verify_evidence)
        if not remote_verified:
            return _blocker(
                plan=plan,
                action=action,
                reason="RemoteRefVerificationFailedAfterGeneratedSettlement",
                message="origin/main did not verify to the generated-state settlement commit",
                evidence=evidence,
                extra={"commits": commit_hashes, "guarded_push_receipt": push_receipt},
            )

    final_plan_result = _invoke_runner(
        runner,
        repo_root,
        ["./repo-python", "tools/meta/control/generated_state_drainer.py", "settlement-plan", "--fast"],
        timeout=600,
        output_limit=120000,
    )
    evidence.append(final_plan_result)
    final_plan = _json_stdout(final_plan_result)
    if _command_ok(settle_result) and final_plan.get("status") == "clean":
        return {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "executed",
            "reason": "GeneratedStateSettled",
            "message": "generated-state owner settlement committed, pushed, and verified",
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "commits": commit_hashes,
            "commit": after_head if head_advanced else None,
            "remote_verified": remote_verified,
            "settlement_status": final_plan.get("status"),
            "evidence": evidence,
        }
    if not _command_ok(settle_result) and not head_advanced:
        owner_commands = _settlement_owner_commands(settle_payload)
        extra = {
            "settlement_status": settle_payload.get("status"),
            "settlement_reason": settle_payload.get("reason"),
            "blocked_by": settle_payload.get("blocked_by") or [],
        }
        if owner_commands:
            extra.update(
                {
                    "owner_commands": owner_commands,
                    "required_next_command": owner_commands[0],
                    "primary_action": {
                        **dict(action),
                        "commands": owner_commands,
                        "handoff_reason": "generated_state_settlement_failed_owner_commands",
                    },
                }
            )
        return _blocker(
            plan=plan,
            action=action,
            reason="GeneratedStateSettlementFailed",
            message="generated-state owner settlement command failed without creating a commit",
            evidence=evidence,
            extra=extra,
        )
    source_digest_after = _task_ledger_source_digest(repo_root)
    active_writers_after, active_writers_after_result = _active_task_ledger_writer_processes(
        repo_root,
        runner=runner,
    )
    evidence.append(active_writers_after_result)
    residual_reason = "GeneratedStateProjectionStillMismatched"
    residual_class = "projection_mismatch"
    residual_message = "generated-state owner settlement made progress, but projection mismatch remains with a stable source digest"
    if source_digest_before.get("digest") != source_digest_after.get("digest"):
        residual_reason = "GeneratedStateSourceMovedDuringSettlement"
        residual_class = "source_moved"
        residual_message = "generated-state owner settlement made progress, but Task Ledger source authority moved during settlement"
    elif active_writers_after:
        residual_reason = "GeneratedStateWriterActive"
        residual_class = "writer_active"
        residual_message = "generated-state owner settlement made progress, but a Task Ledger or generated-state writer is still active"
    stop_integrity, stop_integrity_evidence = _closeout_stop_state_integrity(
        repo_root,
        reason=residual_reason,
        pre_staged_rows=pre_staged_rows,
        runner=runner,
    )
    evidence.extend(stop_integrity_evidence)
    staged_rows = stop_integrity.get("staged_residue_paths")
    if not isinstance(staged_rows, list):
        staged_rows = []
    residual_extra = {
        "previous_reason": "GeneratedStateSettlementResidual",
        "residual_class": residual_class,
        "commits": commit_hashes,
        "commit": after_head if head_advanced else None,
        "remote_verified": remote_verified,
        "settlement_status": settle_payload.get("status"),
        "final_plan_status": final_plan.get("status"),
        "residual_owners": final_plan.get("owners") or settle_payload.get("residual_owners") or [],
        "source_digest_before": source_digest_before,
        "source_digest_after": source_digest_after,
        "active_task_ledger_processes": active_writers_after,
        "staged_external_paths": staged_rows,
        "closeout_stop_integrity": stop_integrity,
        "required_next_command": "./repo-python tools/meta/control/closeout_executor.py run-one --json --compact",
    }
    if residual_class == "source_moved":
        residual_extra["retry_policy"] = {
            "mode": "wait_for_source_quiescence_then_replan",
            "reason": residual_reason,
            "preflight_commands": [
                "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --fast",
                "./repo-python tools/meta/control/closeout_executor.py run-one --dry-run --json --compact",
            ],
            "blocked_until": [
                "Task Ledger source digest is stable across a settlement attempt",
                "no active Task Ledger or generated-state writer is observed",
            ],
        }
    return _blocker(
        plan=plan,
        action=action,
        reason=residual_reason,
        message=residual_message,
        evidence=evidence,
        extra=residual_extra,
    )


def _run_drain_source_cluster(
    repo_root: Path,
    plan: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    cluster = action.get("cluster") if isinstance(action.get("cluster"), Mapping) else {}
    paths = [str(path) for path in cluster.get("paths") or []]
    if not paths:
        return _blocker(
            plan=plan,
            action=action,
            reason="MissingClusterPaths",
            message="drain_source_cluster action did not include exact paths",
        )
    expected_head = str((plan.get("observed") if isinstance(plan.get("observed"), Mapping) else {}).get("head") or "")
    head, head_result = _current_head(repo_root, runner=runner)
    evidence: list[dict[str, Any]] = [head_result]
    if not head or not _command_ok(head_result):
        return _blocker(
            plan=plan,
            action=action,
            reason="HeadReadFailed",
            message="could not read current HEAD before source-cluster drain",
            evidence=evidence,
        )
    if expected_head and head != expected_head:
        return _blocker(
            plan=plan,
            action=action,
            reason="StalePlanHeadMismatch",
            message=f"plan observed head {expected_head}, but current HEAD is {head}",
            evidence=evidence,
        )

    status_result = _path_status(repo_root, paths, runner=runner)
    evidence.append(status_result)
    if not _command_ok(status_result):
        return _blocker(
            plan=plan,
            action=action,
            reason="ClusterStatusFailed",
            message="git status failed for executor cluster paths",
            evidence=evidence,
        )
    if not str(status_result.get("stdout") or "").strip():
        return {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "executed",
            "reason": "ClusterAlreadyIntegrated",
            "message": (
                "source/test cluster paths are no longer dirty; retired the stale closeout blocker "
                "without committing"
            ),
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "cluster_id": cluster.get("cluster_id"),
            "paths": paths,
            "mutation_performed": False,
            "scheduler_action": "replan_or_continue_owned_closeout",
            "evidence": evidence,
        }
    status_rows = _parse_status_rows(str(status_result.get("stdout") or ""))
    untracked_paths = sorted(
        {
            str(row.get("path") or "")
            for row in status_rows
            if str(row.get("path") or "") in paths and str(row.get("xy") or "") == "??"
        }
    )
    staged_rows = _staged_rows_from_status(str(status_result.get("stdout") or ""))
    if staged_rows:
        return _blocker(
            plan=plan,
            action=action,
            reason="StagedIndexOverlapsExecutorCluster",
            message=(
                "shared index has staged entries for executor cluster paths; "
                "preserve the staged owner batch or clear the exact stale index entry before retrying"
            ),
            evidence=evidence,
            extra={
                "staged_paths": staged_rows,
                "repair_hint": "inspect `git diff --cached -- <paths>`; clear only exact stale entries with `./repo-git reset -- <paths>` when staged and unstaged diffs cancel",
            },
        )

    mutation_check, mutation_check_result = _work_ledger_mutation_check(repo_root, paths, runner=runner)
    evidence.append(mutation_check_result)
    collisions_value = mutation_check.get("collisions")
    collisions = list(collisions_value) if isinstance(collisions_value, Sequence) and not isinstance(collisions_value, (str, bytes, bytearray)) else []
    if mutation_check.get("status") == "blocked" and collisions:
        return _blocker(
            plan=plan,
            action=action,
            reason="WorkLedgerActiveClaimOverlap",
            message="source-cluster paths overlap active Work Ledger path claims; wait for owner release or finalize the owning session before closeout commits",
            evidence=evidence,
            extra={
                "paths": paths,
                "mutation_check": mutation_check,
                "active_claim_collisions": collisions,
                "owner_commands": _mutation_check_commands(paths),
                "required_next_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 30",
                "retry_policy": "retry_after_claim_release_then_replan",
            },
        )
    if not _command_ok(mutation_check_result) and not mutation_check:
        commands = _mutation_check_commands(paths)
        return _blocker(
            plan=plan,
            action=action,
            reason="WorkLedgerMutationCheckFailed",
            message="Work Ledger mutation-check failed before source-cluster commit",
            evidence=evidence,
            extra={
                "paths": paths,
                "owner_commands": commands,
                "required_next_command": commands[0],
            },
        )

    ok, validation_evidence = _run_validation_commands(
        repo_root,
        [str(command) for command in cluster.get("validation_commands") or []],
        runner=runner,
    )
    evidence.extend(validation_evidence)
    if not ok:
        queued = _queued_validation_pressure_receipt(validation_evidence)
        if queued:
            pressure_kind = str(queued.get("pressure_kind") or "host_pressure")
            return _blocker(
                plan=plan,
                action=action,
                reason=(
                    "ValidationQueuedDiskPressure"
                    if pressure_kind == "disk_pressure"
                    else "ValidationQueuedHostPressure"
                ),
                message=(
                    "source-cluster validation was queued by repo-pytest "
                    f"{pressure_kind.replace('_', ' ')} gate; no source validation failure was observed"
                ),
                evidence=evidence,
                extra=queued,
            )
        return _blocker(
            plan=plan,
            action=action,
            reason="ValidationFailed",
            message="source-cluster validation command failed",
            evidence=evidence,
        )

    effect = cluster.get("effect_receipt") if isinstance(cluster.get("effect_receipt"), Mapping) else {}
    effect_receipt: dict[str, Any] | None = None
    if effect.get("required"):
        ok, effect_evidence = _run_validation_commands(
            repo_root,
            [str(command) for command in effect.get("commands") or []],
            runner=runner,
        )
        evidence.extend(effect_evidence)
        if ok:
            effect_receipt = {
                "mode": "production_build",
                "status": "passed",
                "commands": [str(command) for command in effect.get("commands") or []],
            }
        else:
            ui_status = _invoke_runner(
                runner,
                repo_root,
                ["git", "status", "--short", "--porcelain=v1", "-uall", "--", "system/server/ui"],
                timeout=60,
            )
            evidence.append(ui_status)
            failed_effect = effect_evidence[-1] if effect_evidence else {}
            blocker_analysis = _ui_effect_blocker_analysis(
                blocked_cluster=cluster,
                command_result=failed_effect,
                ui_status_rows=_parse_status_rows(str(ui_status.get("stdout") or "")),
                blocker_ref=_active_ui_effect_blocker_ref(repo_root),
            )
            targeted_modes = _targeted_effect_modes(effect)
            if targeted_modes and _targeted_effect_allowed(blocker_analysis):
                targeted_mode = targeted_modes[0]
                ok, targeted_evidence = _run_validation_commands(
                    repo_root,
                    [str(command) for command in targeted_mode.get("commands") or []],
                    runner=runner,
                )
                evidence.extend(targeted_evidence)
                if ok:
                    effect_receipt = {
                        "mode": targeted_mode.get("mode"),
                        "status": "passed",
                        "commands": list(targeted_mode.get("commands") or []),
                        "production_build_status": "blocked_by_external_type_baseline",
                        "build_blocker": blocker_analysis,
                    }
                else:
                    return _blocker(
                        plan=plan,
                        action=action,
                        reason="UiTargetedEffectValidationFailed",
                        message=(
                            "UI production build was blocked by external TypeScript baseline debt, "
                            "and targeted UI effect proof also failed"
                        ),
                        evidence=evidence,
                        extra={
                            "ui_effect_blocker": blocker_analysis,
                            "targeted_effect_mode": targeted_mode.get("mode"),
                        },
                    )
            else:
                if targeted_modes:
                    blocker_analysis = {
                        **blocker_analysis,
                        "targeted_effect_skipped_reason": "build_error_requires_direct_or_dependency_fix",
                    }
                return _blocker(
                    plan=plan,
                    action=action,
                    reason="UiEffectValidationFailed",
                    message="UI effect receipt command failed for operator-visible source cluster",
                    evidence=evidence,
                    extra={
                        "ui_effect_blocker": blocker_analysis,
                        "deferred_action": {
                            "lane": "drain_source_cluster",
                            "cluster_id": cluster.get("cluster_id"),
                            "reason": "UiEffectValidationBlockedByExternalTypeScriptErrors",
                            "blocker_ref": blocker_analysis.get("blocker_ref"),
                        },
                    },
                )

    message = f"Drain {cluster.get('stem') or cluster.get('cluster_id') or 'source'} source cluster"
    commit_result = _invoke_runner(
        runner,
        repo_root,
        _scoped_commit_command(
            paths,
            message,
            head,
            allow_untracked=bool(untracked_paths or cluster.get("allow_untracked")),
        ),
        timeout=900,
    )
    evidence.append(commit_result)
    if not _command_ok(commit_result):
        return _blocker(
            plan=plan,
            action=action,
            reason="ScopedCommitFailed",
            message="scoped_commit.py failed for executor cluster paths",
            evidence=evidence,
        )
    commit_payload = _json_stdout(commit_result)
    new_commit = str(commit_payload.get("new_commit") or "")
    if not new_commit:
        return _blocker(
            plan=plan,
            action=action,
            reason="ScopedCommitMissingReceipt",
            message="scoped commit succeeded but did not return new_commit",
            evidence=evidence,
        )
    if commit_payload.get("remote_fallback") is True:
        verified, verify_evidence = _verify_remote_ref(repo_root, new_commit, runner=runner)
        evidence.extend(verify_evidence)
        if not verified:
            return _blocker(
                plan=plan,
                action=action,
                reason="RemoteRefVerificationFailedAfterRemoteFallback",
                message=(
                    "remote-fallback scoped commit reported success, but "
                    "origin/main did not verify to the fallback commit"
                ),
                evidence=evidence,
            )
        receipt = {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "executed",
            "reason": "SourceClusterDrainedViaRemoteFallback",
            "message": (
                "validated, remote-fallback scoped-committed, and remote-verified "
                "one source/test cluster without writing live Git metadata"
            ),
            "plan_id": plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": action.get("lane"),
            "cluster_id": cluster.get("cluster_id"),
            "paths": paths,
            "commit": new_commit,
            "remote_verified": True,
            "remote_fallback": True,
            "live_repo_head_unchanged": bool(commit_payload.get("live_repo_head_unchanged")),
            "next_local_sync_hint": commit_payload.get("next_local_sync_hint"),
            "scoped_commit_receipt": commit_payload,
            "evidence": evidence,
        }
        if untracked_paths:
            receipt["untracked_paths"] = untracked_paths
        if effect_receipt:
            receipt["effect_receipt"] = effect_receipt
        return receipt

    audit_result = _invoke_runner(
        runner,
        repo_root,
        ["./repo-python", "run_git.py", "audit", "push", "--json"],
        timeout=300,
    )
    evidence.append(audit_result)
    audit = _json_stdout(audit_result)
    if not _command_ok(audit_result) or audit.get("status") != "clear" or audit.get("blocked_reasons"):
        return _blocker(
            plan=plan,
            action=action,
            reason="PushAuditNotClearAfterCommit",
            message="source cluster committed locally, but push audit is not clear",
            evidence=evidence,
        )

    ok, blocker, push_receipt = _run_guarded_push_from_audit(
        repo_root,
        plan,
        action,
        audit,
        expected_source=new_commit,
        runner=runner,
        evidence=evidence,
        blocker_reason="GuardedPushFailedAfterCommit",
        blocker_message="source cluster committed locally, but guarded push failed",
    )
    if not ok:
        return blocker or _blocker(
            plan=plan,
            action=action,
            reason="GuardedPushFailedAfterCommit",
            message="source cluster committed locally, but guarded push failed",
            evidence=evidence,
        )

    verified, verify_evidence = _verify_remote_ref(repo_root, new_commit, runner=runner)
    evidence.extend(verify_evidence)
    if not verified:
        return _blocker(
            plan=plan,
            action=action,
            reason="RemoteRefVerificationFailedAfterCommit",
            message="origin/main did not verify to the new source-cluster commit",
            evidence=evidence,
        )

    receipt = {
        "schema": RUN_ONE_SCHEMA,
        "kind": "closeout_executor_run_one_receipt",
        "status": "executed",
        "reason": "SourceClusterDrained",
        "message": "validated, scoped-committed, pushed, and remote-verified one source/test cluster",
        "plan_id": plan.get("plan_id"),
        "action_id": action.get("action_id"),
        "lane": action.get("lane"),
        "cluster_id": cluster.get("cluster_id"),
        "paths": paths,
        "commit": new_commit,
        "remote_verified": True,
        "guarded_push_receipt": push_receipt,
        "evidence": evidence,
    }
    if untracked_paths:
        receipt["untracked_paths"] = untracked_paths
    if effect_receipt:
        receipt["effect_receipt"] = effect_receipt
    return receipt


def run_closeout_executor_one(
    repo_root: Path | str,
    *,
    dry_run: bool = False,
    plan: Mapping[str, Any] | None = None,
    runner: Callable[..., Mapping[str, Any]] | None = None,
    include_ui_effect_blocked: bool = False,
    max_hygiene_repairs: int = 20,
    current_session_id: str | None = None,
    owned_path_prefixes: Sequence[str] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    current_plan = dict(
        plan
        or build_closeout_executor_plan(
            repo,
            run_push_audit=True,
            include_ui_effect_blocked=include_ui_effect_blocked,
            current_session_id=current_session_id,
            owned_path_prefixes=owned_path_prefixes,
            subject_id=subject_id,
        )
    )
    action = current_plan.get("primary_action") if isinstance(current_plan.get("primary_action"), Mapping) else {}
    lane = str(action.get("lane") or "")
    if dry_run:
        receipt = {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "dry_run",
            "reason": "DryRun",
            "message": "no mutation performed",
            "plan_id": current_plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": lane,
            "planned_commands": action.get("commands") or [],
            "plan": current_plan,
        }
        return _attach_mission_trace_context(receipt, plan=current_plan, action=action)
    hygiene = _run_stale_reverse_index_hygiene(
        repo,
        runner=runner,
        max_repairs=max(0, int(max_hygiene_repairs or 0)),
    )
    if hygiene.get("status") in {"executed", "blocked"}:
        hygiene.setdefault("plan_id", current_plan.get("plan_id"))
        hygiene.setdefault("action_id", action.get("action_id"))
        hygiene.setdefault("lane", "stale_reverse_index_hygiene")
        return _attach_mission_trace_context(hygiene, plan=current_plan, action=action)
    if current_plan.get("status") != "action_required" or lane == "no_action":
        receipt = {
            "schema": RUN_ONE_SCHEMA,
            "kind": "closeout_executor_run_one_receipt",
            "status": "no_action",
            "reason": "CloseoutReady",
            "message": "executor plan has no required action",
            "plan_id": current_plan.get("plan_id"),
            "action_id": action.get("action_id"),
            "lane": lane or "no_action",
        }
        return _attach_mission_trace_context(receipt, plan=current_plan, action=action)
    if lane == "publish_if_clear":
        receipt = _run_publish_if_clear(repo, current_plan, action, runner=runner)
    elif lane == "drain_source_cluster":
        receipt = _run_drain_source_cluster(repo, current_plan, action, runner=runner)
    elif lane == "settle_generated_state":
        receipt = _run_settle_generated_state(repo, current_plan, action, runner=runner)
    elif lane == "drain_worktrees":
        receipt = _run_drain_worktrees(repo, current_plan, action, runner=runner)
    elif lane == "ambient_workspace_state":
        receipt = _blocker(
            plan=current_plan,
            action=action,
            reason="AmbientWorkspaceStateRequiresOwnerReview",
            message="dirty paths are ambient workspace state; review through the owner commands before retrying closeout",
            extra=_owner_routed_dirty_state_handoff(action),
        )
    elif lane == "owner_routed_dirty_state":
        receipt = _blocker(
            plan=current_plan,
            action=action,
            reason="OwnerRoutedDirtyStateRequiresOwnerCommand",
            message="dirty paths are runtime or owner-routed state; run the owner commands before retrying closeout",
            extra=_owner_routed_dirty_state_handoff(action),
        )
    elif lane == "ui_effect_blocked":
        receipt = _blocker(
            plan=current_plan,
            action=action,
            reason="UiEffectBlockedRequiresOwnerCommand",
            message="UI-effect validation is blocked by an existing blocker; run the owner commands or retry override before closeout",
            extra=_owner_routed_dirty_state_handoff(action),
        )
    elif lane == "active_claim_blocked":
        receipt = _blocker(
            plan=current_plan,
            action=action,
            reason="WorkLedgerActiveClaimOverlap",
            message="dirty path mutation is blocked by an active Work Ledger owner claim",
            extra=_owner_routed_dirty_state_handoff(action),
        )
    elif lane in {
        "held_foreign_dirty",
        "held_publication_foreign_dirty",
        "blocked_behind",
        "blocked_publication",
    }:
        status = str(action.get("mission_closeout_verdict_status") or lane)
        if status in MISSION_HELD_CLOSEOUT_STATUSES:
            receipt = _mission_closeout_terminal_receipt(plan=current_plan, action=action)
        else:
            receipt = _blocker(
                plan=current_plan,
                action=action,
                reason=str(action.get("reason") or "MissionCloseoutHeldOrBlocked"),
                message=(
                    "mission-owned scope is clean enough for this verdict; the remaining "
                    f"closeout condition is {status} and must not be drained as foreign work"
                ),
                extra={
                    **_owner_routed_dirty_state_handoff(action),
                    "mission_closeout_verdict": current_plan.get("mission_closeout_verdict"),
                    "foreign_source_cluster_candidates": action.get("foreign_source_cluster_candidates") or [],
                },
            )
    elif lane in {
        "publication_gate",
        "inspect_diff_review",
    }:
        receipt = _blocker(
            plan=current_plan,
            action=action,
            reason="UnsupportedLaneForRunOneV0",
            message=(
                "run-one executes publish_if_clear, safe drain_source_cluster, settle_generated_state, "
                "and safe drain_worktrees lanes; "
                "use the owner commands in primary_action.commands for this lane"
            ),
            extra=_unsupported_lane_handoff(action),
        )
    else:
        receipt = _blocker(
            plan=current_plan,
            action=action,
            reason="UnknownLane",
            message=f"run-one v0 does not know how to execute lane={lane}",
        )
    return _attach_mission_trace_context(receipt, plan=current_plan, action=action)


PlanBuilder = Callable[[Path], Mapping[str, Any]]


def _build_burst_plan(
    repo_root: Path,
    *,
    plan_builder: PlanBuilder | None = None,
    include_ui_effect_blocked: bool = False,
    defer_active_claim_blocked: bool = True,
    current_session_id: str | None = None,
    owned_path_prefixes: Sequence[str] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    if plan_builder is not None:
        return dict(plan_builder(repo_root))
    return build_closeout_executor_plan(
        repo_root,
        run_push_audit=True,
        include_ui_effect_blocked=include_ui_effect_blocked,
        defer_active_claim_blocked=defer_active_claim_blocked,
        current_session_id=current_session_id,
        owned_path_prefixes=owned_path_prefixes,
        subject_id=subject_id,
    )


def _burst_state(plan: Mapping[str, Any]) -> dict[str, Any]:
    action = plan.get("primary_action") if isinstance(plan.get("primary_action"), Mapping) else {}
    cluster = action.get("cluster") if isinstance(action.get("cluster"), Mapping) else {}
    observed = plan.get("observed") if isinstance(plan.get("observed"), Mapping) else {}
    return {
        "head": observed.get("head"),
        "ahead": observed.get("ahead"),
        "dirty_total": observed.get("dirty_total"),
        "staged_total": observed.get("staged_total"),
        "plan_id": plan.get("plan_id"),
        "action_id": action.get("action_id"),
        "lane": action.get("lane"),
        "cluster_id": cluster.get("cluster_id"),
    }


# A publication boundary (red push audit, diverged remote, guarded-push churn)
# that the gate spender has already classified as local-commit-allowed /
# no-human-reentry is terminal for the *local* lane: the scoped commit landed and
# only the separate remote/publication authority remains. Surfacing it as a
# generic `blocked` (status) / `blocked_needs_operator_or_owner_action`
# (disposition) is the over-broad classification -- it contradicts the sibling
# `human_reentry_required_by_gate_spender=False` / `advisory_recovery_receipt_only`
# fields and pressures the actor to keep working (or hand-narrate the held state).
HELD_PUBLICATION_BOUNDARY_DISPOSITION = "held_publication_boundary"
MISSION_HELD_CLOSEOUT_STATUSES = {
    "held_foreign_dirty",
    "held_publication_foreign_dirty",
}
MISSION_HELD_CLOSEOUT_STOP_REASONS = {
    "MissionVerdictHeldForeignDirty": "held_foreign_dirty",
    "MissionVerdictHeldPublicationForeignDirty": "held_publication_foreign_dirty",
}


def _mission_held_status_for_stop(stop_reason: str) -> str | None:
    return MISSION_HELD_CLOSEOUT_STOP_REASONS.get(str(stop_reason or ""))


def _burst_status(
    *,
    actions_executed: int,
    stop_reason: str,
    hygiene_repairs: int = 0,
    recovery_contract: Mapping[str, Any] | None = None,
) -> str:
    work_executed = actions_executed + hygiene_repairs
    if stop_reason == "NoAction" and work_executed == 0:
        return "no_action"
    if stop_reason in {"MaxActionsReached", "DryRun"}:
        return "executed" if work_executed else "dry_run"
    if work_executed:
        return "partial"
    # Keep the top-level status in agreement with the gate_spender_route fields:
    # a publication-boundary-held stop is a typed terminal local state, not a
    # generic operator/owner blocker.
    if (
        isinstance(recovery_contract, Mapping)
        and recovery_contract.get("disposition") == HELD_PUBLICATION_BOUNDARY_DISPOSITION
    ):
        return HELD_PUBLICATION_BOUNDARY_DISPOSITION
    if isinstance(recovery_contract, Mapping):
        disposition = str(recovery_contract.get("disposition") or "")
        if disposition in MISSION_HELD_CLOSEOUT_STATUSES:
            return disposition
    return "blocked"


def _burst_plan_candidate_counts(plan: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        plan = {}
    actor_owned = plan.get("actor_owned_source_cluster_candidates")
    foreign = plan.get("foreign_source_cluster_candidates")
    blocked = plan.get("blocked_source_cluster_candidates")
    runnable = plan.get("runnable_source_cluster_candidates")
    return {
        "actor_owned_candidates": len(actor_owned) if isinstance(actor_owned, Sequence) else 0,
        "foreign_candidates": len(foreign) if isinstance(foreign, Sequence) else 0,
        "blocked_candidates": len(blocked) if isinstance(blocked, Sequence) else 0,
        "runnable_candidates": len(runnable) if isinstance(runnable, Sequence) else 0,
        "foreign_or_blocked_candidates_present": bool(foreign or blocked),
    }


_PUBLICATION_GATE_STOP_HINTS = (
    "PushAudit",
    "GuardedPush",
    "RemoteRefVerification",
    "LocalHeadChangedAfterGuardedPush",
    "ConcurrentPublication",
)

_PRESSURE_GATE_STOP_REASONS = {
    "ValidationQueuedHostPressure",
    "ValidationQueuedDiskPressure",
}


def _is_publication_gate_stop(stop_reason: str) -> bool:
    return any(hint in stop_reason for hint in _PUBLICATION_GATE_STOP_HINTS)


def _gate_spender_route_for_closeout_stop(
    *,
    stop_reason: str,
    next_plan: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    claim_boundary = _burst_plan_candidate_counts(next_plan)
    adjacent_lane_available = bool(
        claim_boundary.get("actor_owned_candidates")
        or claim_boundary.get("runnable_candidates")
    )
    context: _GateSpenderContext | None = None

    if _is_publication_gate_stop(stop_reason):
        context = _GateSpenderContext(
            gate_kind=stop_reason,
            is_publication_gate=True,
            local_commit_possible=True,
            adjacent_lane_available=adjacent_lane_available,
        )
    elif stop_reason == "WorkLedgerActiveClaimOverlap":
        context = _GateSpenderContext(
            gate_kind=stop_reason,
            owner_status=_GateSpenderOwnerStatus.HEALTHY_OTHER,
            owner_responsive_to_yield=True,
            adjacent_lane_available=adjacent_lane_available,
            watch_predicate="owner_session_lands_or_releases_claim_then_replan",
        )
    elif stop_reason in _PRESSURE_GATE_STOP_REASONS:
        context = _GateSpenderContext(
            gate_kind=stop_reason,
            adjacent_lane_available=adjacent_lane_available,
            watch_predicate="pressure_recheck_admits_test_build",
        )
    elif stop_reason == "MaxActionsReached":
        context = _GateSpenderContext(
            gate_kind=stop_reason,
            adjacent_lane_available=adjacent_lane_available,
            watch_predicate="rerun_burst_for_remaining_actions",
        )

    if context is None:
        return None

    route = _select_gate_spender_route(context).to_dict()
    route["source"] = "tools.meta.control.gate_spender.select_route"
    route["effect"] = "advisory_recovery_receipt_only"
    return route


def _latest_receipt_with_key(
    receipts: Sequence[Mapping[str, Any]],
    key: str,
) -> Mapping[str, Any]:
    for receipt in reversed(receipts):
        value = receipt.get(key)
        if value:
            return receipt
    return {}


def _review_lane_recovery_contract(
    *,
    contract: Mapping[str, Any],
    next_plan: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(next_plan, Mapping):
        return None
    action = next_plan.get("primary_action") if isinstance(next_plan.get("primary_action"), Mapping) else {}
    lane = str(action.get("lane") or "")
    if lane not in {"inspect_diff_review", "publication_gate"}:
        return None
    closeout = next_plan.get("closeout") if isinstance(next_plan.get("closeout"), Mapping) else {}
    publication = closeout.get("publication") if isinstance(closeout.get("publication"), Mapping) else {}
    ahead = _int_value(closeout.get("ahead"))
    dirty_total = _int_value(closeout.get("dirty_total"))
    publication_status = str(publication.get("status") or "")
    typed_state = (
        "landed_local_publication_blocked"
        if ahead > 0 or publication_status in {"local_ahead", "blocked_publication"}
        else "manual_review_blocked"
    )
    payload = dict(contract)
    payload.update(
        {
            "disposition": "manual_review_required",
            "finality": "nonterminal",
            "operator_action_required": False,
            "owner_action_required": True,
            "missing_controller": False,
            "reentry_owner": "current_actor_or_closeout_owner",
            "reentry_condition": "run_owner_commands_then_record_typed_closeout_state",
            "retry_safety": "read_only_review_then_replan",
            "review_lane": lane,
            "review_reason": action.get("reason"),
            "owner_commands": [str(command) for command in action.get("commands") or [] if str(command)],
            "typed_closeout_state_after_review": typed_state,
            "required_receipt_fields": [
                "review_command_receipt",
                "local_landing_or_no_owned_paths_receipt",
                "remaining_dirty_path_classification",
                "publication_boundary_status",
                "reentry_condition",
            ],
            "publication_boundary_status": publication_status or None,
            "ahead": ahead,
            "dirty_total": dirty_total,
            "closeout_wording_rule": (
                "Do not report UnsupportedLane as an operator blocker after safe review evidence exists; "
                "close as a typed local/publication or manual-review state."
            ),
        }
    )
    return payload


def _burst_recovery_contract(
    *,
    stop_reason: str,
    actions_executed: int,
    hygiene_repairs: int = 0,
    next_plan: Mapping[str, Any] | None = None,
    receipts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    receipts = list(receipts or [])
    work_executed = actions_executed + hygiene_repairs
    contract: dict[str, Any] = {
        "schema": "closeout_recovery_contract_v0",
        "primary_stop_reason": stop_reason,
        "actions_executed": actions_executed,
        "hygiene_repairs": hygiene_repairs,
        "claim_boundary": _burst_plan_candidate_counts(next_plan),
    }
    gate_spender_route = _gate_spender_route_for_closeout_stop(
        stop_reason=stop_reason,
        next_plan=next_plan,
    )
    if gate_spender_route:
        contract["gate_spender_route"] = gate_spender_route
        contract["human_reentry_required_by_gate_spender"] = bool(
            gate_spender_route.get("human_reentry_required")
        )

    if stop_reason in {"ValidationQueuedHostPressure", "ValidationQueuedDiskPressure"}:
        queued_receipt = _latest_receipt_with_key(receipts, "queued_validation")
        queued = queued_receipt.get("queued_validation")
        if not isinstance(queued, Mapping):
            queued = {}
        pressure_kind = str(queued.get("pressure_kind") or queued_receipt.get("pressure_kind") or "")
        contract.update(
            {
                "disposition": "deferred_reentry_pending",
                "finality": "nonterminal",
                "operator_action_required": False,
                "operator_warning": "do_not_force_validation_under_pressure",
                "owner_action_required": False,
                "missing_controller": True,
                "reentry_owner": "operator_or_session_event_drainer_until_pressure_clear_controller_exists",
                "reentry_condition": "pressure_recheck_admits_test_build",
                "retry_safety": "idempotent_validation_only",
                "pressure_kind": pressure_kind or None,
                "queue_id": queued.get("queue_id"),
                "queue_status": queued.get("queue_status"),
                "recheck_command": queued.get("recheck_command")
                or queued_receipt.get("required_next_command"),
                "scheduler_action": queued_receipt.get("scheduler_action"),
                "retry_policy": queued_receipt.get("retry_policy"),
            }
        )
        return contract

    if stop_reason == "WorkLedgerActiveClaimOverlap":
        claim_receipt = _latest_receipt_with_key(receipts, "active_claim_blocker_lookup")
        contract.update(
            {
                "disposition": "blocked_needs_operator_or_owner_action",
                "finality": "nonterminal",
                "operator_action_required": False,
                "owner_action_required": True,
                "missing_controller": False,
                "reentry_owner": "foreign_or_concurrent_owner",
                "reentry_condition": "owner_session_lands_or_releases_claim_then_replan",
                "retry_safety": "replan_after_claim_release",
            }
        )
        if claim_receipt:
            contract["owner_session_ids"] = claim_receipt.get("owner_session_ids")
            contract["required_next_command"] = claim_receipt.get("required_next_command")
        return contract

    mission_held_status = _mission_held_status_for_stop(stop_reason)
    if mission_held_status:
        verdict_receipt = _latest_receipt_with_key(receipts, "mission_closeout_verdict")
        verdict = verdict_receipt.get("mission_closeout_verdict")
        if not isinstance(verdict, Mapping):
            verdict = (
                next_plan.get("mission_closeout_verdict")
                if isinstance(next_plan, Mapping) and isinstance(next_plan.get("mission_closeout_verdict"), Mapping)
                else {}
            )
        contract.update(
            {
                "disposition": mission_held_status,
                "finality": "terminal_for_current_mission",
                "operator_action_required": False,
                "owner_action_required": False,
                "missing_controller": False,
                "local_landing_terminal": True,
                "foreign_dirty_held": mission_held_status == "held_foreign_dirty",
                "publication_boundary_held": mission_held_status == "held_publication_foreign_dirty",
                "reentry_owner": "foreign_dirty_owner_or_publication_lane",
                "reentry_condition": "foreign_owner_settles_or_publication_lane_runs_if_needed",
                "retry_safety": "current_mission_complete_no_global_queue_retry_required",
                "typed_closeout_state": mission_held_status,
                "machine_classification_trust": bool(verdict.get("machine_classification_trust")),
                "caller_must_carry_local_landing_evidence": not bool(
                    verdict.get("machine_classification_trust")
                ),
                "closeout_wording_rule": (
                    "Do not run-burst the global dirty queue after a mission held-foreign verdict. "
                    "Report the scoped landing evidence, the held-foreign/publication verdict, "
                    "and leave foreign dirty paths to their owner lanes."
                ),
            }
        )
        return contract

    if "ValidationFailed" in stop_reason or stop_reason.endswith("ValidationFailed"):
        contract.update(
            {
                "disposition": "failed_needs_source_fix",
                "finality": "terminal_for_this_attempt",
                "operator_action_required": True,
                "owner_action_required": True,
                "missing_controller": False,
                "reentry_owner": "actor_source_owner",
                "reentry_condition": "source_or_test_fix_then_retry",
                "retry_safety": "retry_after_source_fix_only",
            }
        )
        return contract

    if stop_reason == "NoAction":
        contract.update(
            {
                "disposition": "complete" if work_executed else "no_action",
                "finality": "terminal_for_this_burst",
                "operator_action_required": False,
                "owner_action_required": False,
                "missing_controller": False,
                "reentry_owner": "none",
                "reentry_condition": None,
                "retry_safety": "not_required",
            }
        )
        return contract

    if stop_reason == "DryRun":
        contract.update(
            {
                "disposition": "dry_run_preview",
                "finality": "nonterminal",
                "operator_action_required": False,
                "owner_action_required": False,
                "missing_controller": False,
                "reentry_owner": "actor_or_operator",
                "reentry_condition": "rerun_without_dry_run_to_execute",
                "retry_safety": "no_mutation_performed",
            }
        )
        return contract

    if stop_reason == "MaxActionsReached":
        contract.update(
            {
                "disposition": "deferred_reentry_pending",
                "finality": "nonterminal",
                "operator_action_required": False,
                "owner_action_required": False,
                "missing_controller": False,
                "reentry_owner": "actor_or_scheduler",
                "reentry_condition": "rerun_burst_for_remaining_actions",
                "retry_safety": "bounded_max_actions",
            }
        )
        return contract

    if stop_reason == "UnsupportedLane":
        review_contract = _review_lane_recovery_contract(contract=contract, next_plan=next_plan)
        if review_contract is not None:
            return review_contract

    # Publication-boundary class: the gate spender already proved this is a
    # local-commit-allowed / no-human-reentry condition. Emit a typed terminal
    # held state instead of falling through to the generic operator/owner blocker,
    # so the disposition agrees with `human_reentry_required_by_gate_spender` and
    # the `advisory_recovery_receipt_only` effect. Remote reconciliation is a
    # separate publication authority -- never a local-mutation gate.
    if (
        isinstance(gate_spender_route, Mapping)
        and gate_spender_route.get("publication_boundary_only") is True
        and not gate_spender_route.get("human_reentry_required")
    ):
        contract.update(
            {
                "disposition": HELD_PUBLICATION_BOUNDARY_DISPOSITION,
                "finality": "terminal_local_publication_held",
                "operator_action_required": False,
                "owner_action_required": False,
                "missing_controller": False,
                "local_landing_terminal": True,
                "publication_boundary_held": True,
                "reentry_owner": "remote_publication_or_operator",
                "reentry_condition": "reconcile_or_publish_remote_separately",
                "retry_safety": "local_landing_complete_no_local_mutation_required",
                "typed_closeout_state": "landed_local_publication_held",
                "closeout_wording_rule": (
                    "Do not report a publication boundary as an operator/owner blocker for "
                    "the local lane after the scoped commit landed. Close as a typed "
                    "publication-boundary-held state; remote reconciliation is separate "
                    "publication authority, never a local-mutation gate."
                ),
            }
        )
        return contract

    contract.update(
        {
            "disposition": "blocked_needs_operator_or_owner_action",
            "finality": "nonterminal" if work_executed == 0 else "terminal_for_this_attempt",
            "operator_action_required": True,
            "owner_action_required": True,
            "missing_controller": False,
            "reentry_owner": "actor_or_operator",
            "reentry_condition": "inspect_stop_reason_and_receipts",
            "retry_safety": "manual_classification_required",
        }
    )
    return contract


def _attach_gate_spender_burst_projection(receipt: dict[str, Any]) -> dict[str, Any]:
    recovery_contract = receipt.get("recovery_contract")
    if not isinstance(recovery_contract, Mapping):
        return receipt
    gate_spender_route = recovery_contract.get("gate_spender_route")
    if not isinstance(gate_spender_route, Mapping):
        return receipt
    receipt["gate_spender_route"] = dict(gate_spender_route)
    receipt["human_reentry_required_by_gate_spender"] = bool(
        recovery_contract.get("human_reentry_required_by_gate_spender")
    )
    return receipt


def _latest_closeout_stop_integrity(receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for receipt in reversed(receipts):
        integrity = receipt.get("closeout_stop_integrity")
        if isinstance(integrity, Mapping):
            return dict(integrity)
    return None


def run_closeout_executor_burst(
    repo_root: Path | str,
    *,
    max_actions: int = 3,
    dry_run: bool = False,
    runner: Callable[..., Mapping[str, Any]] | None = None,
    include_ui_effect_blocked: bool = False,
    defer_active_claim_blocked: bool = True,
    plan_builder: PlanBuilder | None = None,
    max_hygiene_repairs: int = 20,
    current_session_id: str | None = None,
    owned_path_prefixes: Sequence[str] | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    max_actions = max(1, min(int(max_actions or 1), 10))
    max_hygiene_repairs = max(0, min(int(max_hygiene_repairs or 0), 100))
    first_plan = _build_burst_plan(
        repo,
        plan_builder=plan_builder,
        include_ui_effect_blocked=include_ui_effect_blocked,
        defer_active_claim_blocked=defer_active_claim_blocked,
        current_session_id=current_session_id,
        owned_path_prefixes=owned_path_prefixes,
        subject_id=subject_id,
    )
    before = _burst_state(first_plan)
    first_action = first_plan.get("primary_action") if isinstance(first_plan.get("primary_action"), Mapping) else {}
    if dry_run:
        receipt = {
            "schema": RUN_BURST_SCHEMA,
            "kind": "closeout_executor_run_burst_receipt",
            "status": "dry_run",
            "stop_reason": "DryRun",
            "max_actions": max_actions,
            "actions_executed": 0,
            "before": before,
            "after": before,
            "receipts": [],
            "planned_action": first_plan.get("primary_action"),
            "next_plan": first_plan,
        }
        receipt["recovery_contract"] = _burst_recovery_contract(
            stop_reason="DryRun",
            actions_executed=0,
            hygiene_repairs=0,
            next_plan=first_plan,
            receipts=[],
        )
        _attach_gate_spender_burst_projection(receipt)
        return _attach_mission_trace_context(receipt, plan=first_plan, action=first_action)

    receipts: list[dict[str, Any]] = []
    actions_executed = 0
    stop_reason = "MaxActionsReached"
    next_plan = first_plan
    previous_action_id: str | None = None
    consecutive_publications = 0
    hygiene_repairs = 0

    while actions_executed < max_actions:
        hygiene = _run_stale_reverse_index_hygiene(
            repo,
            runner=runner,
            max_repairs=max_hygiene_repairs - hygiene_repairs,
        )
        if hygiene.get("status") == "blocked":
            action = next_plan.get("primary_action") if isinstance(next_plan.get("primary_action"), Mapping) else {}
            receipts.append(_attach_mission_trace_context(hygiene, plan=next_plan, action=action))
            stop_reason = str(hygiene.get("reason") or "StaleReverseIndexHygieneBlocked")
            break
        if hygiene.get("status") == "executed":
            action = next_plan.get("primary_action") if isinstance(next_plan.get("primary_action"), Mapping) else {}
            receipts.append(_attach_mission_trace_context(hygiene, plan=next_plan, action=action))
            hygiene_repairs += int(hygiene.get("path_count") or len(hygiene.get("paths") or []))
            if hygiene_repairs >= max_hygiene_repairs and hygiene.get("paths_truncated"):
                stop_reason = "StaleReverseIndexHygieneBudgetExhausted"
                break
            continue

        plan = _build_burst_plan(
            repo,
            plan_builder=plan_builder,
            include_ui_effect_blocked=include_ui_effect_blocked,
            defer_active_claim_blocked=defer_active_claim_blocked,
            current_session_id=current_session_id,
            owned_path_prefixes=owned_path_prefixes,
            subject_id=subject_id,
        )
        next_plan = plan
        action = plan.get("primary_action") if isinstance(plan.get("primary_action"), Mapping) else {}
        lane = str(action.get("lane") or "")
        action_id = str(action.get("action_id") or "")
        if plan.get("status") != "action_required" or lane == "no_action":
            stop_reason = "NoAction"
            break
        if lane == "active_claim_blocked":
            blocker = _blocker(
                plan=plan,
                action=action,
                reason="WorkLedgerActiveClaimOverlap",
                message="source cluster mutation is blocked by an active Work Ledger owner claim",
                extra=_owner_routed_dirty_state_handoff(action),
            )
            receipts.append(_attach_mission_trace_context(blocker, plan=plan, action=action))
            stop_reason = "WorkLedgerActiveClaimOverlap"
            break
        if lane in {
            "held_foreign_dirty",
            "held_publication_foreign_dirty",
            "blocked_behind",
            "blocked_publication",
        }:
            status = str(action.get("mission_closeout_verdict_status") or lane)
            if status in MISSION_HELD_CLOSEOUT_STATUSES:
                terminal = _mission_closeout_terminal_receipt(plan=plan, action=action)
                receipts.append(_attach_mission_trace_context(terminal, plan=plan, action=action))
            else:
                blocker = _blocker(
                    plan=plan,
                    action=action,
                    reason=str(action.get("reason") or "MissionCloseoutHeldOrBlocked"),
                    message=(
                        "mission-scoped closeout is held or blocked by a typed verdict; "
                        "do not run the global queue from this mission owner"
                    ),
                    extra={
                        **_owner_routed_dirty_state_handoff(action),
                        "mission_closeout_verdict": plan.get("mission_closeout_verdict"),
                        "foreign_source_cluster_candidates": action.get("foreign_source_cluster_candidates") or [],
                    },
                )
                receipts.append(_attach_mission_trace_context(blocker, plan=plan, action=action))
            stop_reason = str(action.get("reason") or "MissionCloseoutHeldOrBlocked")
            break
        if lane not in {"publish_if_clear", "drain_source_cluster", "settle_generated_state", "drain_worktrees"}:
            blocker = _blocker(
                plan=plan,
                action=action,
                reason="UnsupportedLaneForRunBurstV0",
                message=(
                    "run-burst executes publish_if_clear, safe drain_source_cluster, "
                    "settle_generated_state, and safe drain_worktrees lanes"
                ),
                extra=_unsupported_lane_handoff(action),
            )
            receipts.append(_attach_mission_trace_context(blocker, plan=plan, action=action))
            stop_reason = "UnsupportedLane"
            break
        if previous_action_id and action_id == previous_action_id:
            blocker = _blocker(
                plan=plan,
                action=action,
                reason="RepeatedActionWithoutOwnedProgress",
                message="fresh burst plan repeated the same action_id after an executed action",
            )
            receipts.append(_attach_mission_trace_context(blocker, plan=plan, action=action))
            stop_reason = "NoOwnedProgress"
            break

        receipt = run_closeout_executor_one(
            repo,
            plan=plan,
            runner=runner,
            include_ui_effect_blocked=include_ui_effect_blocked,
            max_hygiene_repairs=0,
            current_session_id=current_session_id,
            owned_path_prefixes=owned_path_prefixes,
            subject_id=subject_id,
        )
        receipts.append(receipt)
        status = str(receipt.get("status") or "")
        if status != "executed":
            stop_reason = str(receipt.get("reason") or "TypedBlocker")
            break

        actions_executed += 1
        previous_action_id = action_id
        if lane == "publish_if_clear":
            consecutive_publications += 1
            if consecutive_publications >= 2:
                stop_reason = "ConcurrentPublicationChurn"
                break
        else:
            consecutive_publications = 0
    else:
        stop_reason = "MaxActionsReached"

    next_plan = _build_burst_plan(
        repo,
        plan_builder=plan_builder,
        include_ui_effect_blocked=include_ui_effect_blocked,
        defer_active_claim_blocked=defer_active_claim_blocked,
        current_session_id=current_session_id,
        owned_path_prefixes=owned_path_prefixes,
        subject_id=subject_id,
    )
    next_action = next_plan.get("primary_action") if isinstance(next_plan.get("primary_action"), Mapping) else {}
    recovery_contract = _burst_recovery_contract(
        stop_reason=stop_reason,
        actions_executed=actions_executed,
        hygiene_repairs=hygiene_repairs,
        next_plan=next_plan,
        receipts=receipts,
    )
    receipt = {
        "schema": RUN_BURST_SCHEMA,
        "kind": "closeout_executor_run_burst_receipt",
        "status": _burst_status(
            actions_executed=actions_executed,
            stop_reason=stop_reason,
            hygiene_repairs=hygiene_repairs,
            recovery_contract=recovery_contract,
        ),
        "stop_reason": stop_reason,
        "max_actions": max_actions,
        "max_hygiene_repairs": max_hygiene_repairs,
        "actions_executed": actions_executed,
        "hygiene_repairs": hygiene_repairs,
        "before": before,
        "after": _burst_state(next_plan),
        "receipts": receipts,
        "next_plan": next_plan,
        "recovery_contract": recovery_contract,
    }
    stop_integrity = _latest_closeout_stop_integrity(receipts)
    _attach_gate_spender_burst_projection(receipt)
    if stop_integrity:
        receipt["closeout_stop_integrity"] = stop_integrity
    return _attach_mission_trace_context(receipt, plan=next_plan, action=next_action)


def dumps_plan(payload: Mapping[str, Any], *, compact: bool = False) -> str:
    if compact:
        return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
