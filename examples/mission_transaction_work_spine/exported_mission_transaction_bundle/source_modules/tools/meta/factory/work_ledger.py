#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_STATUS_REL = Path("state/work_ledger/runtime_status.json")
ACTIVE_CLAIMS_SNAPSHOT_REL = Path("state/work_ledger/active_claims_snapshot.json")
SEED_SPEED_NO_HEARTBEAT_CACHE_REL = Path(
    "state/work_ledger/seed_speed_no_heartbeat_cache.json"
)
SESSION_HEARTBEAT_STATE_ALIASES = {
    "closed": "done",
    "closeout": "closing",
    "close_out": "closing",
    "complete": "done",
    "completed": "done",
    "edit": "editing",
    "fail": "blocked",
    "failed": "blocked",
    "failure": "blocked",
    "finish": "done",
    "finished": "done",
    "inspect": "inspecting",
    "landing": "closing",
    "mutating": "editing",
    "pause": "idle",
    "paused": "idle",
    "success": "done",
    "succeeded": "done",
    "validate": "validating",
    "validation": "validating",
}
WORK_ADMISSION_CLASS_ALIASES = {
    "source_patch": "edit_light_patch",
    "source-patch": "edit_light_patch",
    "standard": "edit_light_patch",
    "validation": "validation_or_build",
    "validate": "validation_or_build",
    "test-build": "validation_or_build",
    "test_build": "validation_or_build",
}
CLAIM_INTENT_ALIASES = {
    "closeout-binding": "closeout_finalizer",
    "closeout_binding": "closeout_finalizer",
    "append-only-ledger": "append_only_ledger",
    "closeout-finalizer": "closeout_finalizer",
    "generated-projection-refresh": "generated_projection_refresh",
    "hard-mutation": "hard_mutation",
    "merge-coordinator": "merge_coordinator",
    "read-acceptance": "read_acceptance",
    "runtime-resource-lease": "runtime_resource_lease",
    "soft-sibling": "soft_sibling",
}
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.git_state_snapshot import build_post_commit_containment_receipt


def _fast_seed_speed_requested(argv: Sequence[str]) -> bool:
    if not argv or argv[0] != "session-status":
        return False
    tokens = list(argv[1:])
    if not tokens:
        return False
    seed_requested = False
    limit = 12
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"--seed-speed", "--speed-only"}:
            seed_requested = True
            index += 1
            continue
        if token == "--json":
            index += 1
            continue
        if token == "--limit":
            if index + 1 >= len(tokens):
                return False
            try:
                limit = int(tokens[index + 1])
            except ValueError:
                return False
            index += 2
            continue
        return False
    return seed_requested and limit == 12


def _fast_overview_cards_requested(argv: Sequence[str]) -> bool:
    if not argv or argv[0] != "session-status":
        return False
    tokens = list(argv[1:])
    if not tokens:
        return False
    overview = False
    cards_only = False
    limit = 12
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--overview":
            overview = True
            index += 1
            continue
        if token == "--cards-only":
            cards_only = True
            index += 1
            continue
        if token == "--json":
            index += 1
            continue
        if token == "--limit":
            if index + 1 >= len(tokens):
                return False
            try:
                limit = int(tokens[index + 1])
            except ValueError:
                return False
            index += 2
            continue
        return False
    return overview and cards_only and limit == 12


def _fast_seed_speed_no_heartbeat_requested(argv: Sequence[str]) -> bool:
    if not argv or argv[0] != "session-status":
        return False
    tokens = list(argv[1:])
    if not tokens:
        return False
    seed_requested = False
    no_heartbeat = False
    limit = 12
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"--seed-speed", "--speed-only"}:
            seed_requested = True
            index += 1
            continue
        if token == "--no-heartbeat":
            no_heartbeat = True
            index += 1
            continue
        if token == "--json":
            index += 1
            continue
        if token == "--limit":
            if index + 1 >= len(tokens):
                return False
            try:
                limit = int(tokens[index + 1])
            except ValueError:
                return False
            index += 2
            continue
        return False
    return seed_requested and no_heartbeat and limit == 12


def _json_file(path: Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _file_receipt(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path.relative_to(REPO_ROOT)), "exists": False}
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "exists": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _fresh_active_claims_snapshot() -> Mapping[str, Any] | None:
    snapshot_path = REPO_ROOT / ACTIVE_CLAIMS_SNAPSHOT_REL
    runtime_path = REPO_ROOT / RUNTIME_STATUS_REL
    snapshot = _json_file(snapshot_path)
    if snapshot is None:
        return None
    source_receipt = snapshot.get("source_receipt")
    if not isinstance(source_receipt, Mapping):
        return None
    current_receipt = _file_receipt(runtime_path)
    if (
        source_receipt.get("mtime_ns") != current_receipt.get("mtime_ns")
        or source_receipt.get("size") != current_receipt.get("size")
    ):
        return None
    return snapshot


def _fast_dirty_paths_from_git_status(repo_root: Path) -> tuple[list[str], str]:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return [], f"git_status_unavailable:{type(exc).__name__}"
    if completed.returncode != 0:
        stderr = " ".join((completed.stderr or "").split())
        return [], f"git_status_failed:{stderr or completed.returncode}"
    paths: list[str] = []
    entries = completed.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:] if len(entry) > 3 else ""
        if path:
            paths.append(path)
        if status[:1] in {"R", "C"} or status[1:2] in {"R", "C"}:
            index += 1
    return paths, "git_status_porcelain_v1_z"


def _dirty_path_receipt(paths: Sequence[str], scan_status: str) -> dict[str, Any]:
    normalized = [str(path) for path in paths if str(path).strip()]
    fingerprint_payload = {
        "dirty_scan_status": scan_status,
        "paths": normalized,
    }
    encoded = json.dumps(
        fingerprint_payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "dirty_scan_status": scan_status,
        "dirty_path_count": len(normalized),
        "dirty_path_fingerprint": hashlib.sha256(encoded).hexdigest(),
    }


def _fast_seed_speed_status_payload(argv: Sequence[str]) -> dict[str, Any] | None:
    if not _fast_seed_speed_requested(argv):
        return None
    snapshot = _fresh_active_claims_snapshot()
    if snapshot is None:
        return None
    seed_speed_hint = snapshot.get("seed_speed_hint")
    if not isinstance(seed_speed_hint, Mapping):
        return None
    if seed_speed_hint.get("schema") != "work_ledger_seed_speed_status_v1":
        return None
    payload = dict(seed_speed_hint)
    payload["fast_dispatch"] = {
        "schema": "work_ledger_seed_speed_fast_dispatch_v0",
        "status": "fresh_snapshot_hit",
        "source": str(ACTIVE_CLAIMS_SNAPSHOT_REL),
        "source_policy": "exact default seed-speed shape may reuse active_claims_snapshot.seed_speed_hint",
    }
    return payload


def _fast_seed_speed_no_heartbeat_payload(argv: Sequence[str]) -> dict[str, Any] | None:
    if not _fast_seed_speed_no_heartbeat_requested(argv):
        return None
    cache = _json_file(REPO_ROOT / SEED_SPEED_NO_HEARTBEAT_CACHE_REL)
    if cache is None:
        return None
    if cache.get("schema") != "work_ledger_seed_speed_no_heartbeat_cache_v0":
        return None
    source_receipt = cache.get("source_receipt")
    if not isinstance(source_receipt, Mapping):
        return None
    current_receipt = _file_receipt(REPO_ROOT / RUNTIME_STATUS_REL)
    if (
        source_receipt.get("mtime_ns") != current_receipt.get("mtime_ns")
        or source_receipt.get("size") != current_receipt.get("size")
    ):
        return None
    dirty_paths, dirty_scan_status = _fast_dirty_paths_from_git_status(REPO_ROOT)
    current_dirty_receipt = _dirty_path_receipt(dirty_paths, dirty_scan_status)
    cached_dirty_receipt = cache.get("dirty_path_receipt")
    if not isinstance(cached_dirty_receipt, Mapping):
        return None
    if (
        cached_dirty_receipt.get("dirty_scan_status")
        != current_dirty_receipt.get("dirty_scan_status")
        or cached_dirty_receipt.get("dirty_path_fingerprint")
        != current_dirty_receipt.get("dirty_path_fingerprint")
    ):
        return None
    cached_payload = cache.get("payload")
    if not isinstance(cached_payload, Mapping):
        return None
    if cached_payload.get("schema") != "work_ledger_seed_speed_status_v1":
        return None
    if cached_payload.get("coordination_mode") != "no_heartbeat":
        return None
    payload = dict(cached_payload)
    payload["fast_dispatch"] = {
        "schema": "work_ledger_seed_speed_no_heartbeat_fast_dispatch_v0",
        "status": "fresh_exact_cache_hit",
        "source": str(SEED_SPEED_NO_HEARTBEAT_CACHE_REL),
        "source_policy": (
            "exact no-heartbeat seed-speed shape may reuse cache when "
            "runtime_status and git dirty-path fingerprint match"
        ),
        "dirty_path_receipt": current_dirty_receipt,
    }
    return payload


def _fast_overview_cards_payload(argv: Sequence[str]) -> dict[str, Any] | None:
    if not _fast_overview_cards_requested(argv):
        return None
    snapshot = _fresh_active_claims_snapshot()
    if snapshot is None:
        return None
    overview_hint = snapshot.get("overview_cards_hint")
    if not isinstance(overview_hint, Mapping):
        return None
    if overview_hint.get("schema") != "work_ledger_session_cohort_overview_v1":
        return None
    if overview_hint.get("mode") != "cards_only_overview":
        return None
    payload = dict(overview_hint)
    payload["fast_dispatch"] = {
        "schema": "work_ledger_overview_cards_fast_dispatch_v0",
        "status": "fresh_snapshot_hit",
        "source": str(ACTIVE_CLAIMS_SNAPSHOT_REL),
        "source_policy": "exact overview cards shape may reuse active_claims_snapshot.overview_cards_hint",
    }
    return payload


def _try_fast_session_status(argv: Sequence[str]) -> int | None:
    payload = _fast_seed_speed_no_heartbeat_payload(argv)
    if payload is None:
        payload = _fast_seed_speed_status_payload(argv)
    if payload is None:
        payload = _fast_overview_cards_payload(argv)
    if payload is None:
        return None
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


_FAST_STATUS = _try_fast_session_status(sys.argv[1:])
if _FAST_STATUS is not None:
    raise SystemExit(_FAST_STATUS)


from system.lib import (
    agent_seed_handoffs,
    resource_pressure,
    shared_worktree_guard,
    work_admission,
    work_ledger,
    work_ledger_runtime,
)
from system.lib.work_ledger_commands import (
    WORK_LEDGER_CLAIM_CARDS_REFRESH_COMMAND,
    WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
    WORK_LEDGER_SEED_SPEED_COMMAND,
    WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
)

CODEX_STATE_DB = Path.home() / ".codex" / "state_5.sqlite"
CLAUDE_IDE_DIR = Path.home() / ".claude" / "ide"
CLAUDE_TODOS_DIR = Path.home() / ".claude" / "todos"
BACKGROUND_DOWNSHIFT_STATE = REPO_ROOT / "state" / "performance" / "background_loop_downshift.json"
SESSION_YIELD_REQUESTS = REPO_ROOT / "state" / "performance" / "session_yield_requests.jsonl"
SESSION_YIELD_RESULTS = REPO_ROOT / "state" / "performance" / "session_yield_results.jsonl"
SESSION_MESSAGES = REPO_ROOT / "state" / "work_ledger" / "session_messages.jsonl"
CODEX_ROLLOUT_TAIL_EVENTS = 400
CODEX_ROLLOUT_COMMAND_LIMIT = 12
CODEX_ROLLOUT_PATH_LIMIT = 40
OVERLAP_TITLE_INLINE_BYTE_LIMIT = 1024
OVERLAP_TITLE_PREVIEW_CHARS = 240
COMPACT_OBSERVED_PATH_OVERLAP_LIMIT = 5
BOUNDED_FULL_OBSERVED_PATH_OVERLAP_LIMIT = 12
TASK_LEDGER_EVENTS_REL = Path("state/task_ledger/events.jsonl")
TASK_LEDGER_RECENT_WRITER_TAIL_LIMIT = 200
TASK_LEDGER_RECENT_WRITER_WINDOW_MINUTES = 10
TASK_LEDGER_RECENT_CLOSEOUT_EVENT_TYPES = {
    "work_item.execution_receipt_recorded",
    "work_item.signoff_recorded",
}
SERIAL_MUTATION_HELP = (
    "Mutation ordering: do not launch Work Ledger lifecycle or claim mutations "
    "in parallel for the same session. Use session-preflight to bootstrap and "
    "claim td/path scopes in one serialized command, then finalize only after a "
    "Work Ledger append or append-exempt evidence exists."
)
HEARTBEAT_PARTICIPATION_HELP = (
    "Heartbeat participation: for long-running Type A/Codex passes, publish one "
    "public now/done heartbeat at pass start, plan pivot, before validation, and "
    "closeout. Do not derive heartbeat text from raw transcripts or hidden reasoning."
)


def _normalize_work_admission_class(value: str | None) -> str | None:
    if not value:
        return value
    token = str(value).strip()
    return WORK_ADMISSION_CLASS_ALIASES.get(token, token)


def _normalize_claim_intent_cli(value: str | None) -> str | None:
    if not value:
        return value
    token = str(value).strip()
    normalized = CLAIM_INTENT_ALIASES.get(token, token)
    if normalized not in work_ledger_runtime.CLAIM_INTENTS:
        choices = ", ".join(
            sorted(set(work_ledger_runtime.CLAIM_INTENTS) | set(CLAIM_INTENT_ALIASES))
        )
        raise argparse.ArgumentTypeError(
            f"invalid claim intent {value!r}; choose from {choices}"
        )
    return normalized


WRITE_PROFILE_PATHS: Dict[str, tuple[str, ...]] = {
    "agent_bootstrap_projection": (
        "AGENTS.md",
        "AGENTS.override.md",
        "CLAUDE.md",
        "CODEX.md",
        "codex/doctrine/agent_bootstrap_live.json",
        "codex/doctrine/agent_bootstrap_injection_strip.json",
    ),
    "paper_module_index": (
        "codex/doctrine/paper_modules/README.md",
        "codex/doctrine/paper_modules/_index.json",
        "codex/doctrine/paper_modules/_validation_report.json",
        "codex/doctrine/paper_modules/_doctrine_to_paper_modules.json",
        "codex/doctrine/paper_modules/_route_coverage.json",
    ),
    "skill_catalog_projection": (
        "AGENTS.md",
        "codex/doctrine/skills/skill_registry.json",
        "codex/doctrine/skills/skill_map.md",
    ),
    "annex_catalog_projection": (
        "annexes/annex_distillation_index.json",
        "docs/annex_registry.md",
    ),
    "annex_assimilation": (
        "annexes",
        "annexes/annex_distillation_index.json",
        "docs/annex_registry.md",
    ),
    "raw_seed_family_projection": (
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.json",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.md",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.snapshot.md",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed",
    ),
    "agent_seed_family_projection": (
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed.json",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed.md",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed.snapshot.md",
    ),
    "doctrine_skill_projection": (
        "codex/doctrine/skills",
        "codex/doctrine/skills/skill_registry.json",
        "codex/doctrine/skills/skill_map.md",
        "AGENTS.md",
    ),
    "orchestration_runtime_projection": (
        "tools/meta/control/orchestration_state.json",
        "tools/meta/control/orchestration_brief.json",
        "tools/meta/control/orchestration_brief.md",
        "tools/meta/control/orchestration_events.jsonl",
    ),
    "navigation_hologram_projection": (
        "codex/navigation_hologram",
    ),
    "architectural_projection": (
        "state/architectural_projection",
        "system/lib/architectural_projection.py",
        "tools/meta/factory/build_architectural_projection.py",
        "codex/standards/std_architectural_projection.json",
        "codex/doctrine/paper_modules/architectural_projection_plane.md",
    ),
    "task_ledger": (
        "state/task_ledger/events.jsonl",
        "state/task_ledger/events_audit.jsonl",
        "state/task_ledger/ledger.json",
        "state/task_ledger/views",
    ),
    "autonomous_seed": (
        "state/meta_missions/type_a_autonomous_seed_loop/README.md",
        "state/meta_missions/type_a_autonomous_seed_loop/seeds",
    ),
    "microcosm_doctrine_lattice_projection": (
        "microcosm-substrate/anti_principles",
        "microcosm-substrate/atlas/doctrine_lattice_entry_card.json",
        "microcosm-substrate/atlas/doctrine_lattice_graph.mmd",
        "microcosm-substrate/atlas/doctrine_lattice_health.json",
        "microcosm-substrate/atlas/doctrine_lattice_projection.json",
        "microcosm-substrate/axioms",
        "microcosm-substrate/concepts",
        "microcosm-substrate/core/doctrine_lattice_coverage.json",
        "microcosm-substrate/mechanisms",
        "microcosm-substrate/organs",
        "microcosm-substrate/paper_modules",
        "microcosm-substrate/principles",
        "microcosm-substrate/skills",
    ),
    "microcosm_public_site_projection": (
        "sites/microcosm/content-graph.json",
        "sites/microcosm/content-manifest.json",
        "sites/microcosm/projection-status.json",
        "sites/microcosm/object-map.json",
        "sites/microcosm/llms.txt",
        "sites/microcosm/assets/search-index.js",
        "sites/microcosm/assets/site-packet.js",
        "sites/microcosm/assets/object-map.js",
        "sites/microcosm/docs",
        "sites/microcosm/_headers",
        "sites/microcosm/_redirects",
        "sites/microcosm/robots.txt",
        "sites/microcosm/security.txt",
        "sites/microcosm/.well-known/security.txt",
        "sites/microcosm/404.html",
        "sites/microcosm/sitemap.xml",
    ),
}
WRITE_PROFILE_SOURCE_INPUT_PATHS: Dict[str, tuple[str, ...]] = {
    "microcosm_doctrine_lattice_projection": (
        "microcosm-substrate/ANTI_PRINCIPLES.md",
        "microcosm-substrate/PRINCIPLES.md",
        "microcosm-substrate/atlas/entry_packet.json",
        "microcosm-substrate/core/axiom_organ_routing.json",
        "microcosm-substrate/core/doctrine_lattice_relations.json",
        "microcosm-substrate/core/mechanism_sources.json",
        "microcosm-substrate/core/organ_atlas.json",
        "microcosm-substrate/core/organ_registry.json",
        "microcosm-substrate/core/paper_module_capsules.json",
        "microcosm-substrate/core/public_surface_manifest.json",
        "microcosm-substrate/core/standards_registry.json",
        "microcosm-substrate/paper_modules",
        "microcosm-substrate/skills",
        "microcosm-substrate/standards",
    ),
    "microcosm_public_site_projection": (
        "microcosm-substrate/README.md",
        "microcosm-substrate/QUICKSTART.md",
        "microcosm-substrate/ARCHITECTURE.md",
        "microcosm-substrate/ORGANS.md",
        "microcosm-substrate/SECURITY.md",
        "microcosm-substrate/LICENSE",
        "microcosm-substrate/NOTICE",
        "microcosm-substrate/PROVENANCE.md",
        "microcosm-substrate/atlas/agent_task_routes.json",
        "microcosm-substrate/atlas/entry_packet.json",
        "microcosm-substrate/core/architecture_kernel.json",
        "microcosm-substrate/core/doctrine_lattice_coverage.json",
        "microcosm-substrate/core/doctrine_lattice_relations.json",
        "microcosm-substrate/core/mechanism_sources.json",
        "microcosm-substrate/core/organ_atlas.json",
        "microcosm-substrate/core/organ_families.json",
        "microcosm-substrate/core/organ_registry.json",
        "microcosm-substrate/core/paper_module_capsules.json",
        "microcosm-substrate/axioms",
        "microcosm-substrate/concepts",
        "microcosm-substrate/mechanisms",
        "microcosm-substrate/paper_modules",
        "microcosm-substrate/principles",
        "sites/microcosm/index.html",
        "sites/microcosm/assets/style.css",
        "sites/microcosm/assets/docs.js",
        "system/lib/graph_scene_core.py",
        "tools/meta/dissemination/build_microcosm_public_site.py",
        "tools/meta/dissemination/microcosm_public_narratives.json",
    ),
}
_CODEX_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_./~-])(?P<path>(?:\./)?(?:(?:\.agents|\.claude|\.codex|\.cursor|annexes|codex|docs|system|tools|state|obsidian|scripts|tests|src|lib)/[A-Za-z0-9_./%+@=-]+|(?:AGENTS|CODEX|CLAUDE|GEMINI)\.md|kernel\.py|(?:pipeline|run)_[A-Za-z0-9_/-]+\.py))"
)
_CODEX_PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Delete|Update) File: (?P<path>.+?)\s*$", re.MULTILINE)

def _print(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _write_seed_speed_no_heartbeat_cache(
    payload: Mapping[str, Any],
    *,
    dirty_paths: Sequence[str],
    dirty_scan_status: str,
) -> None:
    if payload.get("schema") != "work_ledger_seed_speed_status_v1":
        return
    if payload.get("coordination_mode") != "no_heartbeat":
        return
    cache_path = REPO_ROOT / SEED_SPEED_NO_HEARTBEAT_CACHE_REL
    cache = {
        "schema": "work_ledger_seed_speed_no_heartbeat_cache_v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_receipt": _file_receipt(REPO_ROOT / RUNTIME_STATUS_REL),
        "dirty_path_receipt": _dirty_path_receipt(dirty_paths, dirty_scan_status),
        "payload": payload,
    }
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(
            json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(cache_path)
    except OSError:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _print_exit(payload: Dict[str, Any], *, exit_code: int) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return int(exit_code)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl_tail(path: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: deque[str] = deque(maxlen=max(1, int(limit or 1)))
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(line)
    records: list[dict[str, Any]] = []
    for line in rows:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _mint_session_yield_request_id(target_session_id: str | None, requested_action: str | None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seed = f"{stamp}:{target_session_id or 'unknown'}:{requested_action or 'yield'}:{os.getpid()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return f"syr_{stamp}_{digest}"


def _session_yield_request_receipt_from_event(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = row.get("session_yield_request")
    if isinstance(nested, dict):
        return nested
    if row.get("schema") == work_admission.SESSION_YIELD_REQUEST_SCHEMA:
        return dict(row)
    return {}


def _find_session_yield_request(
    *,
    request_id: str | None = None,
    target_session_id: str | None = None,
    limit: int = 400,
) -> dict[str, Any] | None:
    for row in reversed(_read_jsonl_tail(SESSION_YIELD_REQUESTS, limit=limit)):
        receipt = _session_yield_request_receipt_from_event(row)
        if not receipt:
            continue
        if request_id and receipt.get("request_id") == request_id:
            return receipt
        if target_session_id and receipt.get("target_id") == target_session_id:
            return receipt
    return None


def _pending_session_yield_requests_by_target(*, limit: int = 1000) -> Dict[str, Dict[str, Any]]:
    control = work_admission.build_session_yield_control_surface(
        request_events=_read_jsonl_tail(SESSION_YIELD_REQUESTS, limit=limit),
        result_events=_read_jsonl_tail(SESSION_YIELD_RESULTS, limit=limit),
        limit=limit,
        output_profile="full",
    )
    pending_by_target: Dict[str, Dict[str, Any]] = {}
    for request in control.get("pending_requests", []):
        if not isinstance(request, Mapping):
            continue
        target_id = str(request.get("target_id") or "").strip()
        if not target_id:
            continue
        pending_by_target[target_id] = dict(request)
    return pending_by_target


def _is_resident_relief_request_event(row: Mapping[str, Any]) -> bool:
    source = row.get("source") if isinstance(row.get("source"), Mapping) else {}
    return str(source.get("surface") or "") == "resident_pressure_relief"


def _session_yield_request_payload(row: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = row.get("session_yield_request")
    return nested if isinstance(nested, Mapping) else row


def _session_yield_result_payload(row: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = row.get("owner_yield_result")
    return nested if isinstance(nested, Mapping) else row


def _session_yield_pending_age_s(
    pending_request: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> float | None:
    issued_raw = str(pending_request.get("issued_at") or "").strip()
    if not issued_raw:
        return None
    if issued_raw.endswith("Z"):
        issued_raw = issued_raw[:-1] + "+00:00"
    try:
        issued_at = datetime.fromisoformat(issued_raw)
    except ValueError:
        return None
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=timezone.utc)
    observed_at = now or datetime.now(timezone.utc)
    return round(max((observed_at.astimezone(timezone.utc) - issued_at).total_seconds(), 0.0), 3)


def _resident_relief_settlement_window(
    *,
    runtime_status: Mapping[str, Any],
    resident_thread_rows: Sequence[Mapping[str, Any]],
    extra_request_events: Sequence[Mapping[str, Any]] = (),
    limit: int = 20,
    output_profile: str = "compact",
    pending_ttl_s: int | float | None = None,
) -> Dict[str, Any]:
    request_events = [
        row
        for row in _read_jsonl_tail(SESSION_YIELD_REQUESTS, limit=max(1, int(limit or 1)))
        if isinstance(row, Mapping) and _is_resident_relief_request_event(row)
    ]
    request_events.extend(
        row
        for row in extra_request_events
        if isinstance(row, Mapping) and _is_resident_relief_request_event(row)
    )
    request_ids = {
        str(_session_yield_request_payload(row).get("request_id") or "").strip()
        for row in request_events
    }
    request_ids.discard("")
    target_ids = {
        str(_session_yield_request_payload(row).get("target_id") or "").strip()
        for row in request_events
    }
    target_ids.discard("")
    result_events: list[Mapping[str, Any]] = []
    for row in _read_jsonl_tail(SESSION_YIELD_RESULTS, limit=max(1, int(limit or 1))):
        if not isinstance(row, Mapping):
            continue
        result = _session_yield_result_payload(row)
        request_id = str(result.get("request_id") or "").strip()
        target_id = str(result.get("target_id") or "").strip()
        if request_id in request_ids or (not request_id and target_id in target_ids):
            result_events.append(row)
    return work_admission.build_resident_relief_settlement_window(
        request_events=request_events,
        result_events=result_events,
        runtime_status=runtime_status,
        resident_thread_rows=resident_thread_rows,
        pending_ttl_s=pending_ttl_s or work_admission.RESIDENT_RELIEF_PENDING_TTL_S,
        limit=limit,
        output_profile=output_profile,
    )


def _heartbeat_participation_contract(session_id: str | None = None) -> Dict[str, Any]:
    session_token = shlex.quote(str(session_id)) if str(session_id or "").strip() else "<session_id>"
    return {
        "schema": "work_ledger_heartbeat_participation_contract_v0",
        "status": "recommended_for_participating_sessions",
        "when": [
            "long_pass_start",
            "plan_pivot",
            "before_validation",
            "closeout",
        ],
        "command_template": (
            "./repo-python tools/meta/factory/work_ledger.py session-heartbeat "
            f"--session-id {session_token} --state inspecting "
            "--current-pass-line '<public current pass>' "
            "--last-pass-result-line '<public previous result>' "
            "--scope-ref <path-or-claim>"
        ),
        "boundary": (
            "Explicit public coordination assertion; runtime-only; not durable "
            "progress; never summarize raw transcripts or hidden reasoning."
        ),
    }


def _resolution_episode_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    metadata = None
    if args.resolution_metadata_json:
        metadata = json.loads(args.resolution_metadata_json)
        if not isinstance(metadata, dict):
            raise ValueError("resolution_metadata_json must decode to an object")
    return work_ledger.build_resolution_episode(
        args.resolution_kind,
        args.resolution_ref,
        label=args.resolution_label,
        metadata=metadata,
    )


def _progress_bridge_resolution_hint(args: argparse.Namespace) -> tuple[str, str, str]:
    evidence_refs = [
        str(ref).strip()
        for ref in getattr(args, "evidence_ref", [])
        if str(ref).strip()
    ]
    if evidence_refs:
        ref = evidence_refs[0]
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", ref):
            return "git_commit", ref, "Work Ledger progress bridge evidence commit"
        return "artifact", ref, "Work Ledger progress bridge evidence"
    return "session", str(args.actor_session_id), "Work Ledger progress bridge closeout"


def _metadata_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    raw = getattr(args, "metadata_json", None)
    metadata: Dict[str, Any] = {}
    if raw:
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("metadata_json must decode to an object")
        metadata = decoded
    body_ingest = getattr(args, "_body_ingest", None)
    if body_ingest:
        if "body_ingest" in metadata:
            raise SystemExit(
                "metadata_json may not contain body_ingest when --body-file or --body-stdin is used; "
                "body_ingest is system-owned attestation metadata."
            )
        metadata["body_ingest"] = body_ingest
    mutation_guard = getattr(args, "_mutation_guard", None)
    if mutation_guard:
        if "mutation_guard" in metadata:
            raise SystemExit(
                "metadata_json may not contain mutation_guard when Work Ledger mutation authority "
                "is checked; mutation_guard is system-owned concurrency metadata."
            )
        metadata["mutation_guard"] = mutation_guard
    return metadata


def _body_ingest_attestation(
    *,
    mode: str,
    raw: bytes,
    source_text: str,
    path: Path | None = None,
) -> Dict[str, Any]:
    stored_text = str(source_text or "").strip()
    stored_bytes = stored_text.encode("utf-8")
    source_sha256 = hashlib.sha256(raw).hexdigest()
    source_byte_count = len(raw)
    source_newline_count = source_text.count("\n")
    stored_sha256 = hashlib.sha256(stored_bytes).hexdigest()
    stored_byte_count = len(stored_bytes)
    stored_newline_count = stored_text.count("\n")
    attestation: Dict[str, Any] = {
        "mode": mode,
        "sha256": source_sha256,
        "byte_count": source_byte_count,
        "newline_count": source_newline_count,
        "source_sha256": source_sha256,
        "source_byte_count": source_byte_count,
        "source_newline_count": source_newline_count,
        "stored_sha256": stored_sha256,
        "stored_byte_count": stored_byte_count,
        "stored_newline_count": stored_newline_count,
        "canonicalization": {
            "storage": "work_ledger_event_shape_str_strip",
            "leading_trailing_whitespace_stripped": stored_text != source_text,
            "trailing_newline_removed": source_text.endswith("\n")
            and stored_text == source_text.rstrip("\n"),
        },
    }
    if path is not None:
        attestation["path"] = str(path)
    return attestation


def _resolve_body_and_ingest(args: argparse.Namespace) -> None:
    """Resolve --body / --body-file / --body-stdin into args.body and args._body_ingest.

    Closeout bodies are governance evidence; shell command-substitution can corrupt
    inline --body text. --body-file PATH reads UTF-8 bytes from disk; --body-stdin
    reads sys.stdin.buffer; both are mutually exclusive with --body and with each
    other. For file/stdin sources, body_ingest metadata records source-byte and
    stored-body digests so the closeout event carries an attestation envelope
    alongside the body text.
    """
    inline = getattr(args, "body", None)
    body_file = getattr(args, "body_file", None)
    body_stdin = bool(getattr(args, "body_stdin", False))
    sources = sum(1 for v in (inline is not None, bool(body_file), body_stdin) if v)
    if sources > 1:
        raise SystemExit(
            "Only one of --body, --body-file, --body-stdin may be supplied (mutually exclusive)."
        )
    args._body_ingest = None  # type: ignore[attr-defined]
    if body_file:
        path = Path(body_file)
        if not path.is_file():
            raise SystemExit(f"--body-file path does not exist: {path}")
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"--body-file must be UTF-8: {exc}") from exc
        args.body = text
        args._body_ingest = _body_ingest_attestation(  # type: ignore[attr-defined]
            mode="file",
            path=path,
            raw=raw,
            source_text=text,
        )
    elif body_stdin:
        raw = sys.stdin.buffer.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"--body-stdin must receive UTF-8: {exc}") from exc
        args.body = text
        args._body_ingest = _body_ingest_attestation(  # type: ignore[attr-defined]
            mode="stdin",
            raw=raw,
            source_text=text,
        )


def _looks_like_task_ledger_work_item_id(value: str) -> bool:
    return bool(re.match(r"^(cap|task|wi|work_item|self_error)[A-Za-z0-9_.:-]*", value))


def _thread_claim_conflict_payload(
    *,
    operation: str,
    td_id: str,
    session_id: str,
    error: Exception,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema": "work_ledger_mutation_claim_conflict_v1",
        "status": "blocked",
        "operation": operation,
        "td_id": td_id,
        "actor_session_id": session_id,
        "reason": "missing_or_stale_td_id_claim",
        "message": str(error),
        "repair_route": "Run session-claim --td-id for this actor_session_id, then retry the mutation.",
    }
    if td_id and not work_ledger.TD_ID_RE.fullmatch(td_id):
        requested_kind = "task_ledger_work_item_id" if _looks_like_task_ledger_work_item_id(td_id) else "non_work_ledger_td_id"
        payload["identity_axis_mismatch"] = {
            "schema": "work_ledger_identity_axis_mismatch_v1",
            "requested_id": td_id,
            "requested_id_kind": requested_kind,
            "expected_id_kind": "work_ledger_td_id",
            "expected_pattern": "td_*",
            "why": (
                "Work Ledger close/supersede/reopen mutate Work Ledger threads. "
                "Task Ledger WorkItem ids can be recorded through progress, which opens "
                "a bridge thread and returns a generated td_id plus next_close_command."
            ),
            "progress_bridge_command": (
                "./repo-python tools/meta/factory/work_ledger.py progress "
                "--td-id <task_ledger_work_item_id> --title '<progress-title>' "
                "--body-file '<closeout-body.md>'"
            ),
            "task_ledger_receipt_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py "
                "record-execution-receipt --subject-id <task_ledger_work_item_id> "
                "--transaction-id <transaction_id> --commit-hash <commit_hash> --rebuild"
            ),
        }
        if operation in {"todo_close", "todo_supersede", "todo_reopen"}:
            payload["repair_route"] = (
                "Do not pass a Task Ledger WorkItem id to close/supersede/reopen. "
                "Use the generated Work Ledger td_id from a prior progress bridge "
                "result (next_close_command), or record closeout through the Task Ledger "
                "execution-receipt/note lane."
            )
    return payload


def _claim_conflict_exit(*, operation: str, td_id: str, session_id: str, error: Exception) -> None:
    raise SystemExit(
        json.dumps(
            _thread_claim_conflict_payload(
                operation=operation,
                td_id=td_id,
                session_id=session_id,
                error=error,
            ),
            sort_keys=True,
        )
    )


def _work_item_claim_conflict_exit(
    *,
    operation: str,
    work_item_id: str,
    session_id: str,
    error: Exception,
) -> None:
    raise SystemExit(
        json.dumps(
            {
                "schema": "work_ledger_mutation_claim_conflict_v1",
                "status": "blocked",
                "operation": operation,
                "work_item_id": work_item_id,
                "actor_session_id": session_id,
                "reason": "missing_or_stale_work_item_id_claim",
                "message": str(error),
                "repair_route": "Run session-preflight --td-id <work_item_id> for this actor_session_id, then retry the mutation.",
            },
            sort_keys=True,
        )
    )


def _read_receipt_error_reason(message: str) -> str:
    normalized = message.lower()
    if "ended session" in normalized:
        return "ended_session"
    if "does not match" in normalized:
        return "session_mismatch"
    if "not valid" in normalized:
        return "invalid_receipt"
    if "required" in normalized:
        return "missing_receipt"
    return "receipt_validation_failed"


def _read_receipt_error_exit(
    *,
    command: str,
    operation: str,
    args: argparse.Namespace,
    error: Exception,
) -> None:
    message = str(error)
    actor = str(getattr(args, "actor", "") or "<actor>").strip() or "<actor>"
    phase_id = str(getattr(args, "phase_id", "") or "<phase_id>").strip() or "<phase_id>"
    family_id = str(getattr(args, "family_id", "") or "<family_id>").strip() or "<family_id>"
    target_id = str(getattr(args, "td_id", "") or "").strip()
    session_slug = f"<new_{command}_session_slug>"
    recovery_command = (
        "./repo-python tools/meta/factory/work_ledger.py session-preflight "
        f"--session-slug {session_slug} --actor {actor} --phase-id {phase_id} --family-id {family_id}"
    )
    if target_id:
        recovery_command += f" --td-id {target_id}"
    payload: Dict[str, Any] = {
        "schema": "work_ledger_read_receipt_error_v1",
        "status": "blocked",
        "command": command,
        "operation": operation,
        "reason": _read_receipt_error_reason(message),
        "message": message,
        "read_receipt_id": str(getattr(args, "read_receipt_id", "") or "").strip(),
        "actor_session_id": str(getattr(args, "actor_session_id", "") or "").strip(),
        "repair_route": (
            "Read receipts are live-session write tokens. Append progress before "
            "session-finalize; after finalization, bootstrap a new session and retry "
            "with the new read_receipt_id."
        ),
        "recovery_command": recovery_command,
    }
    if target_id:
        payload["td_id"] = target_id
    raise SystemExit(json.dumps(payload, sort_keys=True))


def _verify_thread_claim_or_bypass(
    args: argparse.Namespace,
    *,
    operation: str,
    allow_unclaimed_note: bool = False,
) -> None:
    args._mutation_guard = None  # type: ignore[attr-defined]
    td_id = str(getattr(args, "td_id", "") or "").strip()
    session_id = str(getattr(args, "actor_session_id", "") or "").strip()
    try:
        claim = work_ledger_runtime.require_active_thread_claim(
            REPO_ROOT,
            session_id=session_id,
            td_id=td_id,
            operation=operation,
        )
    except ValueError as exc:
        if not (allow_unclaimed_note and bool(getattr(args, "allow_unclaimed_note", False))):
            _claim_conflict_exit(operation=operation, td_id=td_id, session_id=session_id, error=exc)
        args._mutation_guard = {  # type: ignore[attr-defined]
            "schema": "work_ledger_mutation_guard_v1",
            "status": "claim_bypassed",
            "mode": "explicit_unclaimed_note",
            "severity": "warning",
            "operation": operation,
            "td_id": td_id,
            "actor_session_id": session_id,
            "reason": "operator_marked_low_blast_unclaimed_note",
            "repair_route": "Prefer session-claim --td-id before mutating a WorkItem.",
        }
        return
    args._mutation_guard = {  # type: ignore[attr-defined]
        "schema": "work_ledger_mutation_guard_v1",
        "status": "claim_verified",
        "operation": operation,
        "td_id": td_id,
        "actor_session_id": session_id,
        "claim_id": claim.get("claim_id"),
        "claim_scope": claim.get("scope_id") or claim.get("td_id"),
        "leased_until": claim.get("leased_until"),
    }


def _verify_work_item_claim_or_bypass(
    args: argparse.Namespace,
    *,
    operation: str,
    allow_unclaimed_note: bool = False,
) -> None:
    args._mutation_guard = None  # type: ignore[attr-defined]
    work_item_id = str(getattr(args, "td_id", "") or "").strip()
    session_id = str(getattr(args, "actor_session_id", "") or "").strip()
    try:
        claim = work_ledger_runtime.require_active_work_item_claim(
            REPO_ROOT,
            session_id=session_id,
            work_item_id=work_item_id,
            operation=operation,
        )
    except ValueError as exc:
        if not (allow_unclaimed_note and bool(getattr(args, "allow_unclaimed_note", False))):
            _work_item_claim_conflict_exit(
                operation=operation,
                work_item_id=work_item_id,
                session_id=session_id,
                error=exc,
            )
        args._mutation_guard = {  # type: ignore[attr-defined]
            "schema": "work_ledger_mutation_guard_v1",
            "status": "claim_bypassed",
            "mode": "explicit_unclaimed_work_item_note",
            "severity": "warning",
            "operation": operation,
            "work_item_id": work_item_id,
            "actor_session_id": session_id,
            "reason": "operator_marked_low_blast_unclaimed_note",
            "repair_route": "Prefer session-preflight --td-id <work_item_id> before appending WorkItem progress.",
        }
        return
    args._mutation_guard = {  # type: ignore[attr-defined]
        "schema": "work_ledger_mutation_guard_v1",
        "status": "claim_verified",
        "operation": operation,
        "work_item_id": work_item_id,
        "actor_session_id": session_id,
        "claim_id": claim.get("claim_id"),
        "claim_scope": claim.get("scope_id") or claim.get("work_item_id"),
        "leased_until": claim.get("leased_until"),
    }


def _require_receipt(args: argparse.Namespace) -> Dict[str, Any]:
    session = work_ledger_runtime.validate_read_receipt(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
    )
    if not getattr(args, "actor_session_id", None):
        args.actor_session_id = str(session.get("session_id") or "")
    if not getattr(args, "actor", None):
        args.actor = str(session.get("actor") or "unknown")
    if not getattr(args, "phase_id", None):
        args.phase_id = str(session.get("phase_id") or "")
    if not getattr(args, "family_id", None):
        args.family_id = str(session.get("family_id") or "")
    # Resolve --body / --body-file / --body-stdin once per mutation command and
    # stash any body_ingest attestation metadata on args for _metadata_from_args
    # to pick up. Body args are only present on mutation parsers (append-open /
    # progress / note / close / supersede / reopen); reads are no-ops elsewhere.
    if hasattr(args, "body") or hasattr(args, "body_file") or hasattr(args, "body_stdin"):
        _resolve_body_and_ingest(args)
    return session


def cmd_bootstrap(args: argparse.Namespace) -> int:
    payload = work_ledger.bootstrap_phase_bucket(
        REPO_ROOT,
        phase_id=args.phase_id,
        family_id=args.family_id,
    )
    return _print(payload)


def _compact_bootstrap_work_card(card: Mapping[str, Any]) -> Dict[str, Any]:
    metadata = card.get("metadata") if isinstance(card.get("metadata"), Mapping) else {}
    work_landing_attempt = (
        metadata.get("work_landing_attempt")
        if isinstance(metadata.get("work_landing_attempt"), Mapping)
        else {}
    )
    work_item_id = metadata.get("task_ledger_work_item_id") or work_landing_attempt.get("subject_id")
    return {
        key: value
        for key, value in {
            "td_id": card.get("td_id"),
            "title": card.get("title"),
            "status": card.get("status"),
            "last_actor": card.get("last_actor"),
            "last_event_at": card.get("last_event_at"),
            "work_item_id": work_item_id,
        }.items()
        if value not in (None, "", [], {})
    }


def _compact_session_bootstrap_payload(payload: Mapping[str, Any], *, limit: int) -> Dict[str, Any]:
    safe_limit = max(1, int(limit or 1))
    actor_slice = [
        card for card in (payload.get("open_actor_slice") or []) if isinstance(card, Mapping)
    ]
    family_slice = [
        card for card in (payload.get("open_family_slice") or []) if isinstance(card, Mapping)
    ]
    overview = payload.get("cohort_overview") if isinstance(payload.get("cohort_overview"), Mapping) else {}
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    contention = overview.get("contention") if isinstance(overview.get("contention"), Mapping) else {}
    return {
        "schema": payload.get("schema"),
        "generated_at": payload.get("generated_at"),
        "mode": "compact",
        "command": "session-bootstrap",
        "session_id": payload.get("session_id"),
        "actor": payload.get("actor"),
        "phase_id": payload.get("phase_id"),
        "family_id": payload.get("family_id"),
        "read_receipt_id": payload.get("read_receipt_id"),
        "open_actor_preview": [_compact_bootstrap_work_card(card) for card in actor_slice[:safe_limit]],
        "open_actor_omitted": max(0, len(actor_slice) - safe_limit),
        "open_family_preview": [_compact_bootstrap_work_card(card) for card in family_slice[:safe_limit]],
        "open_family_omitted": max(0, len(family_slice) - safe_limit),
        "auto_sweep_summary": {
            "orphan_swept_count": int(
                ((payload.get("auto_sweep") or {}).get("orphan_sweep") or {}).get("swept_count")
                or 0
            ),
            "expired_claim_swept_count": int(
                ((payload.get("auto_sweep") or {}).get("claim_expiry") or {}).get("swept_count")
                or 0
            ),
        },
        "claim_result_count": len(payload.get("claims") or []),
        "external_observation_count": len(payload.get("external_observations") or []),
        "pass_heartbeat": dict(payload.get("pass_heartbeat") or {}),
        "cohort_summary": {
            "schema": overview.get("schema"),
            "counts": {
                "sessions_total": counts.get("sessions_total", 0),
                "active_sessions": counts.get("active_sessions", 0),
                "effective_active_sessions": counts.get("effective_active_sessions", 0),
                "orphaned_active_sessions": counts.get("orphaned_active_sessions", 0),
                "stale_sessions": counts.get("stale_sessions", 0),
                "active_claims": counts.get("active_claims", 0),
                "claim_collisions": counts.get("claim_collisions", 0),
            },
            "contention": {
                "risk_level": contention.get("risk_level", "clear"),
                "signals": list(contention.get("signals") or []),
            },
        },
        "heartbeat_command": (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-heartbeat --session-id {payload.get('session_id')} --state inspecting "
            "--current-pass-line '<public current pass>' --scope-ref <path-or-claim>"
        ),
        "drilldown_commands": {
            "full_bootstrap": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-bootstrap --session-id {payload.get('session_id')} "
                f"--actor {payload.get('actor')} --phase-id {payload.get('phase_id')} "
                f"--family-id {payload.get('family_id')} --limit {safe_limit} --full"
            ),
            "overview_cards": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-status --overview --cards-only --limit {safe_limit}"
            ),
        },
        "omission_receipt": {
            "omitted": [
                "open_actor_slice full rows",
                "open_family_slice full rows",
                "cohort_overview full session rows",
                "additional_context rendered markdown",
                "auto_sweep detail rows",
            ],
            "reason": "session-bootstrap default is a lifecycle receipt; full bootstrap context remains behind --full.",
        },
    }


def cmd_session_bootstrap(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.bootstrap_session(
        REPO_ROOT,
        session_id=args.session_id,
        actor=args.actor,
        phase_id=args.phase_id,
        family_id=args.family_id,
        limit=args.limit,
    )
    if getattr(args, "full", False):
        return _print(payload)
    return _print(_compact_session_bootstrap_payload(payload, limit=args.limit))


def cmd_session_activity(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.mark_session_activity(
        REPO_ROOT,
        session_id=args.session_id,
        action=args.action,
        td_id=args.td_id,
    )
    if getattr(args, "full", False):
        return _print(payload)
    return _print(
        _compact_session_lifecycle_payload(
            payload,
            schema="work_ledger_session_activity_result_v1",
            command="session-activity",
            session_id=args.session_id,
            action=args.action,
            limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
        )
    )


def _clip_public_heartbeat_line(value: object, *, limit: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return normalized[:limit]
    return f"{normalized[: limit - 3].rstrip()}..."


def _normalize_cli_heartbeat_state(value: object) -> str:
    state = str(value or "").strip().lower().replace("-", "_")
    if not state:
        return "inspecting"
    return SESSION_HEARTBEAT_STATE_ALIASES.get(state, state)


def _heartbeat_state_help() -> str:
    canonical = ", ".join(sorted(work_ledger_runtime.PASS_HEARTBEAT_STATES))
    aliases = ", ".join(sorted(SESSION_HEARTBEAT_STATE_ALIASES))
    return (
        f"Public pass state. Canonical values: {canonical}. "
        f"Compatibility aliases accepted: {aliases}."
    )


def cmd_session_heartbeat(args: argparse.Namespace) -> int:
    if not args.current_pass_line and not args.last_pass_result_line:
        raise SystemExit(
            "session-heartbeat requires --current-pass-line/--now or "
            "--last-pass-result-line/--done; use a valid --state such as "
            "inspecting, editing, validating, closing, blocked, done, or idle"
        )
    pass_state = _normalize_cli_heartbeat_state(args.state)
    current_pass_line = args.current_pass_line
    last_pass_result_line = args.last_pass_result_line
    if bool(getattr(args, "clip_lines", False)):
        current_pass_line = _clip_public_heartbeat_line(
            current_pass_line,
            limit=work_ledger_runtime.PASS_CURRENT_LINE_LIMIT,
        )
        last_pass_result_line = _clip_public_heartbeat_line(
            last_pass_result_line,
            limit=work_ledger_runtime.PASS_RESULT_LINE_LIMIT,
        )
    payload = work_ledger_runtime.mark_session_pass_heartbeat(
        REPO_ROOT,
        session_id=args.session_id,
        pass_state=pass_state,
        current_pass_line=current_pass_line,
        last_pass_result_line=last_pass_result_line,
        td_id=args.td_id,
        scope_refs=list(args.scope_ref or []),
        pass_id=args.pass_id,
        source=args.source,
    )
    if getattr(args, "full", False):
        return _print(payload)
    return _print(
        _compact_session_lifecycle_payload(
            payload,
            schema="work_ledger_session_heartbeat_result_v1",
            command="session-heartbeat",
            session_id=args.session_id,
            action=pass_state,
            limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
        )
    )


def _first_append_exempt_commit_ref(evidence_refs: Sequence[object]) -> str:
    for raw_ref in evidence_refs:
        ref = str(raw_ref or "").strip()
        if not ref:
            continue
        if ref.startswith("commit:"):
            commit_ref = ref.split(":", 1)[1].strip()
            if commit_ref:
                return commit_ref
            continue
        if ":" not in ref:
            return ref
    return ""


def _post_commit_containment_finalize_guard(
    args: argparse.Namespace,
    *,
    evidence_refs: Sequence[object],
) -> Dict[str, Any] | None:
    required = bool(getattr(args, "require_post_commit_containment", False))
    commit_ref = str(getattr(args, "post_commit_containment_commit", "") or "").strip()
    scopes = [
        str(scope or "").strip()
        for scope in list(getattr(args, "post_commit_containment_scope", []) or [])
        if str(scope or "").strip()
    ]
    if not required and not commit_ref and not scopes:
        return None
    if not commit_ref:
        commit_ref = _first_append_exempt_commit_ref(evidence_refs)

    missing: List[str] = []
    if not commit_ref:
        missing.append("--post-commit-containment-commit or commit:* --append-exempt-ref")
    if not scopes:
        missing.append("--post-commit-containment-scope")
    if missing:
        return {
            "schema": "work_ledger_post_commit_containment_finalize_guard_v0",
            "status": "blocked_missing_inputs",
            "ok": False,
            "closeout_safe": False,
            "reason": "PostCommitContainmentInputsMissing",
            "missing": missing,
            "policy": (
                "Append-exempt commit closeout can release claims only after the "
                "cited commit is contained in current HEAD and each declared owned "
                "path remains unchanged and clean."
            ),
        }

    receipt = build_post_commit_containment_receipt(
        REPO_ROOT,
        commit_ref=commit_ref,
        paths=scopes,
    )
    return {
        "schema": "work_ledger_post_commit_containment_finalize_guard_v0",
        "status": receipt.get("status"),
        "ok": bool(receipt.get("ok")),
        "closeout_safe": bool(receipt.get("closeout_safe")),
        "commit_ref": commit_ref,
        "scope_count": len(scopes),
        "scopes": scopes,
        "receipt": receipt,
        "policy": (
            "Append-exempt commit closeout can release claims only after the "
            "cited commit is contained in current HEAD and each declared owned "
            "path remains unchanged and clean."
        ),
    }


def _blocked_post_commit_containment_finalize_payload(
    args: argparse.Namespace,
    *,
    guard: Mapping[str, Any],
) -> Dict[str, Any]:
    pre_status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    payload = _compact_session_lifecycle_payload(
        pre_status,
        schema="work_ledger_session_finalize_result_v1",
        command="session-finalize",
        session_id=args.session_id,
        action=args.action,
        limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
    )
    payload["status"] = "blocked"
    payload["mutation_performed"] = False
    payload["blocked_by"] = ["post_commit_containment_not_safe"]
    payload["safe_next_action"] = (
        "Resolve the cited commit or owned-path containment issue, then rerun "
        "session-finalize with the same append-exempt reason, read receipt, "
        "commit ref, and path scopes."
    )
    payload["post_commit_containment_guard"] = dict(guard)
    return payload


def cmd_session_finalize(args: argparse.Namespace) -> int:
    append_exempt_reason = str(getattr(args, "append_exempt_reason", "") or "").strip()
    append_exempt_refs = list(getattr(args, "append_exempt_ref", []) or [])
    containment_guard = None
    if append_exempt_reason:
        read_receipt_id = str(getattr(args, "read_receipt_id", "") or "").strip()
        if not read_receipt_id:
            raise SystemExit("--read-receipt-id is required with --append-exempt-reason")
        containment_guard = _post_commit_containment_finalize_guard(
            args,
            evidence_refs=append_exempt_refs,
        )
        if containment_guard and not bool(containment_guard.get("closeout_safe")):
            _print(
                _blocked_post_commit_containment_finalize_payload(
                    args,
                    guard=containment_guard,
                )
            )
            return 2
        work_ledger_runtime.mark_session_append_exempt(
            REPO_ROOT,
            read_receipt_id=read_receipt_id,
            session_id=args.session_id,
            reason=append_exempt_reason,
            evidence_refs=append_exempt_refs,
            td_ids=list(getattr(args, "append_exempt_td_id", []) or []),
            work_item_ids=list(getattr(args, "append_exempt_work_item_id", []) or []),
        )
    if not bool(getattr(args, "allow_missing_append", False)):
        pre_status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
        sessions = pre_status.get("sessions") if isinstance(pre_status.get("sessions"), Mapping) else {}
        session = dict(sessions.get(args.session_id) or {}) if isinstance(sessions, Mapping) else {}
        append_satisfied = bool(session.get("session_had_ledger_append")) or bool(
            session.get("append_exempt")
        )
        if session.get("touched_work") and not append_satisfied:
            payload = _compact_session_lifecycle_payload(
                pre_status,
                schema="work_ledger_session_finalize_result_v1",
                command="session-finalize",
                session_id=args.session_id,
                action=args.action,
                limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
            )
            payload["status"] = "blocked"
            payload["mutation_performed"] = False
            payload["blocked_by"] = ["append_missing_before_finalize"]
            payload["safe_next_action"] = (
                "Append progress, close, or append-open evidence with the live "
                "read_receipt_id, then run session-finalize again. For commit-only "
                "or projection-only sessions, rerun session-finalize with "
                "--read-receipt-id <wlr_*> --append-exempt-reason <reason> "
                "--append-exempt-ref <commit-or-receipt-ref>. When the durable "
                "evidence is a commit and HEAD may have moved, add "
                "--require-post-commit-containment and repeat "
                "--post-commit-containment-scope for each owned path."
            )
            payload["append_exempt_closeout"] = {
                "required_flag": "--append-exempt-reason",
                "requires": ["--read-receipt-id"],
                "optional_refs": [
                    "--append-exempt-ref",
                    "--append-exempt-td-id",
                    "--append-exempt-work-item-id",
                    "--require-post-commit-containment",
                    "--post-commit-containment-commit",
                    "--post-commit-containment-scope",
                ],
                "use_when": (
                    "The session touched work through path claims and the durable "
                    "evidence is a scoped commit, Task Ledger receipt, or generated "
                    "projection settlement rather than a Work Ledger append."
                ),
            }
            payload["diagnostic_escape_hatch"] = {
                "flag": "--allow-missing-append",
                "use_only_when": (
                    "You intentionally want to finalize as stale after recording why "
                    "no Work Ledger append can be written in this session."
                ),
            }
            _print(payload)
            return 2
    payload = work_ledger_runtime.finalize_session(
        REPO_ROOT,
        session_id=args.session_id,
        action=args.action,
        release_claims=not bool(getattr(args, "no_release_claims", False)),
        release_reason=args.action,
    )
    if getattr(args, "full", False):
        if containment_guard:
            payload["post_commit_containment_guard"] = containment_guard
        return _print(payload)
    compact_payload = _compact_session_lifecycle_payload(
        payload,
        schema="work_ledger_session_finalize_result_v1",
        command="session-finalize",
        session_id=args.session_id,
        action=args.action,
        limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
    )
    if containment_guard:
        compact_payload["post_commit_containment_guard"] = containment_guard
    return _print(compact_payload)


def cmd_session_status(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    session_id = str(getattr(args, "session_id", "") or "").strip()
    detail = str(getattr(args, "detail", "") or "").strip()
    full_output = bool(getattr(args, "full", False)) or detail == "full"
    raw_limit = getattr(args, "limit", None)
    limit = (
        work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT
        if raw_limit is None
        else raw_limit
    )
    if session_id:
        return _print(
            _compact_single_session_status(
                payload,
                session_id=session_id,
                limit=limit,
                include_full_session=full_output,
            )
        )
    if full_output:
        if raw_limit is not None:
            _print(
                {
                    "schema": "work_ledger_session_status_limit_guard_v0",
                    "status": "refused",
                    "reason": "--full emits the complete runtime status and cannot honor --limit without a --session-id.",
                    "requested_limit": raw_limit,
                    "bounded_alternatives": [
                        "./repo-python tools/meta/factory/work_ledger.py session-status --overview --cards-only --limit "
                        + str(raw_limit),
                        "./repo-python tools/meta/factory/work_ledger.py session-status --overview --with-session-cards --limit "
                        + str(raw_limit),
                        "./repo-python tools/meta/factory/work_ledger.py session-status --session-id <session_id> --full --limit "
                        + str(raw_limit),
                    ],
                    "full_runtime_command": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
                    "omission_receipt": {
                        "omitted": ["runtime_status.sessions"],
                        "reason": "Prevent accidental full-runtime expansion when the caller requested a bounded sample.",
                    },
                },
            )
            return 2
        return _print(payload)
    seed_speed = bool(
        getattr(args, "seed_speed", False) or getattr(args, "speed_only", False)
    )
    overview_limit = max(int(limit or 0), 100) if seed_speed else limit
    overview = work_ledger_runtime.build_session_cohort_overview(
        payload,
        limit=overview_limit,
    )
    if seed_speed:
        dirty_tree_pressure = None
        dirty_paths: List[str] = []
        dirty_scan_status = "not_scanned"
        if bool(getattr(args, "no_heartbeat", False)) or bool(
            getattr(args, "dirty_tree_pressure", False)
        ):
            dirty_paths, dirty_scan_status = _dirty_paths_from_git_status(REPO_ROOT)
            dirty_tree_pressure = work_ledger_runtime.build_dirty_tree_bankruptcy_pressure(
                REPO_ROOT,
                status=payload,
                dirty_paths=dirty_paths,
                dirty_scan_status=dirty_scan_status,
                bankruptcy_authorized=bool(
                    getattr(args, "bankruptcy_authorized", False)
                ),
                limit=limit,
            )
            dirty_tree_pressure["sweep_dry_run"] = True
        seed_speed_payload = _seed_speed_status(
            overview,
            limit=limit,
            prefer_non_heartbeat=bool(getattr(args, "no_heartbeat", False)),
            dirty_tree_pressure=dirty_tree_pressure,
        )
        if bool(getattr(args, "no_heartbeat", False)) and limit == 12:
            _write_seed_speed_no_heartbeat_cache(
                seed_speed_payload,
                dirty_paths=dirty_paths,
                dirty_scan_status=dirty_scan_status,
            )
        return _print(seed_speed_payload)
    if getattr(args, "with_session_cards", False):
        return _print(overview)
    return _print(
        _compact_session_status_overview(
            overview,
            limit=limit,
            include_rows=False,
        )
    )


def _session_matches_list_filter(
    row: Mapping[str, Any],
    *,
    actor: str,
    state_filter: str,
) -> bool:
    if actor and str(row.get("actor") or "") != actor:
        return False
    normalized_filter = str(state_filter or "active").strip()
    if normalized_filter == "all":
        return True
    ended = bool(row.get("ended_at"))
    stale = bool(row.get("stale"))
    if normalized_filter == "active":
        return not ended
    if normalized_filter in {"ended", "closed"}:
        return ended
    if normalized_filter == "stale":
        return stale
    return True


def cmd_list_sessions(args: argparse.Namespace) -> int:
    runtime_status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    actor = str(getattr(args, "actor", "") or "").strip()
    state_filter = str(getattr(args, "session_state_filter", "") or "active").strip()
    limit = max(0, int(getattr(args, "limit", 0) or 0))
    sessions = (
        runtime_status.get("sessions")
        if isinstance(runtime_status.get("sessions"), Mapping)
        else {}
    )
    matched_rows: list[Mapping[str, Any]] = []
    for session_id, raw_row in sessions.items():
        if not isinstance(raw_row, Mapping):
            continue
        row = dict(raw_row)
        row.setdefault("session_id", session_id)
        if _session_matches_list_filter(
            row,
            actor=actor,
            state_filter=state_filter,
        ):
            matched_rows.append(row)
    matched_rows.sort(
        key=lambda row: str(row.get("last_activity_at") or row.get("bootstrapped_at") or ""),
        reverse=True,
    )
    emitted_rows = matched_rows[:limit]
    return _print(
        {
            "schema": "work_ledger_list_sessions_compat_v1",
            "status": "ok",
            "mode": "list_sessions_compat",
            "compatibility_alias_for": "session-status",
            "filters": {
                "actor": actor or None,
                "status": state_filter,
                "limit": limit,
            },
            "matched_session_count": len(matched_rows),
            "emitted_session_count": len(emitted_rows),
            "omitted_session_count": max(0, len(matched_rows) - len(emitted_rows)),
            "sessions": [_compact_session_row(row) for row in emitted_rows],
            "replacement_commands": {
                "seed_speed": WORK_LEDGER_SEED_SPEED_COMMAND,
                "overview": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
                "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
            },
        }
    )


def cmd_session_claims(args: argparse.Namespace) -> int:
    limit = getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT)
    path_filters = list(getattr(args, "path", []) or [])
    session_filters = list(getattr(args, "session_id", []) or [])
    if getattr(args, "refresh", False):
        status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
        work_ledger_runtime.write_active_claims_snapshot(REPO_ROOT, status)
    scan_limit = _session_claims_scan_limit(
        limit=limit,
        session_summary=bool(getattr(args, "session_summary", False)),
        path_filters=path_filters,
        session_filters=session_filters,
    )
    payload = work_ledger_runtime.load_active_claims_snapshot(
        REPO_ROOT,
        limit=scan_limit,
        allow_stale=bool(getattr(args, "allow_stale", False)),
    )
    payload = _filter_active_claims_snapshot_by_paths(
        payload,
        path_filters=path_filters,
        repo_root=REPO_ROOT,
    )
    payload = _filter_active_claims_snapshot_by_session_ids(
        payload,
        session_ids=session_filters,
    )
    if getattr(args, "session_summary", False):
        payload = _compact_claim_session_summary_cards(payload, limit=limit)
        return _print(payload)
    if getattr(args, "full", False) and (path_filters or session_filters):
        payload = _compact_filtered_claims_full_snapshot(payload)
        return _print(payload)
    if not getattr(args, "full", False):
        payload = _compact_session_claims_cards(payload, limit=limit)
    return _print(payload)


def _session_claims_scan_limit(
    *,
    limit: int | None,
    session_summary: bool,
    path_filters: Sequence[str],
    session_filters: Sequence[str],
) -> int | None:
    if session_summary or path_filters or session_filters:
        return max(5000, int(limit or 0))
    return limit


def _compact_claim_card(
    row: Mapping[str, Any],
    *,
    fallback_session: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    owner = fallback_session if isinstance(fallback_session, Mapping) else {}
    return {
        "scope_kind": row.get("scope_kind"),
        "scope_id": row.get("scope_id"),
        "td_id": row.get("td_id"),
        "path": row.get("path"),
        "work_item_id": row.get("work_item_id"),
        "session_id": row.get("session_id") or owner.get("session_id"),
        "actor": row.get("actor") or owner.get("actor"),
        "phase_id": row.get("phase_id") or owner.get("phase_id"),
        "leased_until": row.get("leased_until"),
    }


def _claim_path_token(row: Mapping[str, Any]) -> str:
    return str(row.get("path") or row.get("claim_path") or row.get("scope_id") or "").strip()


def _filter_active_claims_snapshot_by_paths(
    snapshot: Mapping[str, Any],
    *,
    path_filters: Sequence[str],
    repo_root: Path = REPO_ROOT,
) -> Dict[str, Any]:
    requested_paths: List[str] = []
    for path in list(path_filters or []):
        token = _normalize_codex_repo_path(path, repo_root)
        if token and token not in requested_paths:
            requested_paths.append(token)
    payload = dict(snapshot)
    if not requested_paths:
        return payload

    active_claims = [
        row for row in list(payload.get("active_claims") or []) if isinstance(row, Mapping)
    ]
    filtered_claims = [
        dict(row)
        for row in active_claims
        if any(
            _path_scope_overlaps(requested, _claim_path_token(row))
            for requested in requested_paths
        )
    ]
    claim_collisions = [
        row for row in list(payload.get("claim_collisions") or []) if isinstance(row, Mapping)
    ]
    filtered_collisions = [
        dict(row)
        for row in claim_collisions
        if any(
            _path_scope_overlaps(
                requested,
                str(row.get("requested_path") or row.get("claim_path") or row.get("path") or ""),
            )
            for requested in requested_paths
        )
    ]

    counts = dict(payload.get("counts") or {})
    source_counts = dict(counts)
    counts["active_claims"] = len(filtered_claims)
    counts["claim_collisions"] = len(filtered_collisions)
    payload["active_claims"] = filtered_claims
    payload["claim_collisions"] = filtered_collisions
    payload["counts"] = counts
    payload["path_filter"] = {
        "schema": "work_ledger_claim_path_filter_v0",
        "requested_paths": requested_paths,
        "matched_claim_count": len(filtered_claims),
        "matched_collision_count": len(filtered_collisions),
        "source_active_claim_count": source_counts.get("active_claims", len(active_claims)),
        "source_claim_collision_count": source_counts.get(
            "claim_collisions",
            len(claim_collisions),
        ),
        "match_rule": "repo_path_overlap_prefix_or_exact",
    }
    return payload


def _claim_session_token(row: Mapping[str, Any]) -> str:
    return str(row.get("session_id") or "").strip()


def _collision_mentions_session(row: Mapping[str, Any], requested_session_ids: Sequence[str]) -> bool:
    row_session = _claim_session_token(row)
    if row_session and row_session in requested_session_ids:
        return True
    for claim in list(row.get("active_claims") or []):
        if isinstance(claim, Mapping) and _claim_session_token(claim) in requested_session_ids:
            return True
    return False


def _filter_active_claims_snapshot_by_session_ids(
    snapshot: Mapping[str, Any],
    *,
    session_ids: Sequence[str],
) -> Dict[str, Any]:
    requested_session_ids: List[str] = []
    for session_id in list(session_ids or []):
        token = str(session_id or "").strip()
        if token and token not in requested_session_ids:
            requested_session_ids.append(token)
    payload = dict(snapshot)
    if not requested_session_ids:
        return payload

    active_claims = [
        row for row in list(payload.get("active_claims") or []) if isinstance(row, Mapping)
    ]
    filtered_claims = [
        dict(row) for row in active_claims if _claim_session_token(row) in requested_session_ids
    ]
    claim_collisions = [
        row for row in list(payload.get("claim_collisions") or []) if isinstance(row, Mapping)
    ]
    filtered_collisions = [
        dict(row)
        for row in claim_collisions
        if _collision_mentions_session(row, requested_session_ids)
    ]

    counts = dict(payload.get("counts") or {})
    source_counts = dict(counts)
    counts["active_claims"] = len(filtered_claims)
    counts["claim_collisions"] = len(filtered_collisions)
    payload["active_claims"] = filtered_claims
    payload["claim_collisions"] = filtered_collisions
    payload["counts"] = counts
    payload["session_filter"] = {
        "schema": "work_ledger_claim_session_filter_v0",
        "requested_session_ids": requested_session_ids,
        "matched_claim_count": len(filtered_claims),
        "matched_collision_count": len(filtered_collisions),
        "source_active_claim_count": source_counts.get("active_claims", len(active_claims)),
        "source_claim_collision_count": source_counts.get(
            "claim_collisions",
            len(claim_collisions),
        ),
        "match_rule": "session_id_exact_or_nested_collision_claim",
    }
    return payload


def _session_claims_filter_args(snapshot: Mapping[str, Any]) -> str:
    args: List[str] = []
    path_filter = snapshot.get("path_filter")
    if isinstance(path_filter, Mapping):
        requested_paths = [
            str(path or "").strip()
            for path in list(path_filter.get("requested_paths") or [])
            if str(path or "").strip()
        ]
        args.extend(f" --path {shlex.quote(path)}" for path in requested_paths)
    session_filter = snapshot.get("session_filter")
    if isinstance(session_filter, Mapping):
        requested_session_ids = [
            str(session_id or "").strip()
            for session_id in list(session_filter.get("requested_session_ids") or [])
            if str(session_id or "").strip()
        ]
        args.extend(
            f" --session-id {shlex.quote(session_id)}"
            for session_id in requested_session_ids
        )
    return "".join(args)


def _compact_filtered_claims_full_snapshot(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    payload = dict(snapshot)
    omitted: List[str] = []
    for key in ("seed_speed_hint", "overview_cards_hint"):
        if key in payload:
            payload.pop(key, None)
            omitted.append(key)

    if omitted:
        filter_args = _session_claims_filter_args(payload)
        payload["output_profile"] = "filtered_full_claim_rows_compact_cohort_hints"
        payload["filter_output_omission_receipt"] = {
            "schema": "work_ledger_filtered_claims_full_omission_v0",
            "omitted": omitted,
            "reason": (
                "Path/session-filtered full claims preserve matched claim rows; unrelated "
                "cohort hints belong behind their owner routes."
            ),
            "claim_drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims{filter_args} --full"
            ),
            "seed_speed_status": WORK_LEDGER_SEED_SPEED_COMMAND,
            "session_overview_cards": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
        }
    return payload


def _compact_session_claims_cards(snapshot: Mapping[str, Any], *, limit: int) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    filter_args = _session_claims_filter_args(snapshot)
    collisions = [
        row
        for row in list(snapshot.get("claim_collisions") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    return {
        "schema": "work_ledger_active_claims_cards_v1",
        "generated_at": snapshot.get("generated_at"),
        "status": snapshot.get("status"),
        "counts": snapshot.get("counts") or {},
        "count_semantics": work_ledger_runtime.coordination_count_semantics(
            snapshot.get("counts") if isinstance(snapshot.get("counts"), Mapping) else {}
        ),
        "active_claim_cards": [
            _compact_claim_card(row)
            for row in list(snapshot.get("active_claims") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ],
        "claim_collision_cards": [
            {
                "scope_kind": row.get("scope_kind"),
                "scope_id": row.get("scope_id"),
                "td_id": row.get("td_id"),
                "path": row.get("path"),
                "work_item_id": row.get("work_item_id"),
                "claim_count": row.get("claim_count"),
                "actors": list(row.get("actors") or []),
                "active_claim_cards": [
                    _compact_claim_card(claim)
                    for claim in list(row.get("active_claims") or [])[:safe_limit]
                    if isinstance(claim, Mapping)
                ],
            }
            for row in collisions
        ],
        "truncation": snapshot.get("truncation") or {},
        **(
            {"path_filter": snapshot.get("path_filter")}
            if isinstance(snapshot.get("path_filter"), Mapping)
            else {}
        ),
        **(
            {"session_filter": snapshot.get("session_filter")}
            if isinstance(snapshot.get("session_filter"), Mapping)
            else {}
        ),
        "source_freshness": {
            "status": (snapshot.get("source_freshness") or {}).get("status")
            if isinstance(snapshot.get("source_freshness"), Mapping)
            else None,
            "policy": (snapshot.get("source_freshness") or {}).get("policy")
            if isinstance(snapshot.get("source_freshness"), Mapping)
            else None,
        },
        "drilldown_commands": {
            "full_claims": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --limit {safe_limit}{filter_args} --full"
            ),
            "refresh": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --refresh{filter_args}"
            ),
            "session_overview_cards": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
            "seed_speed_status": WORK_LEDGER_SEED_SPEED_COMMAND,
            "mutation_check": "./repo-python tools/meta/factory/work_ledger.py mutation-check --path <path> --require-exclusive",
        },
        "omission_receipt": {
            "omitted": [
                "claim_id",
                "claimed_at",
                "released_at",
                "expired_at",
                "note",
                "release_reason",
                "source_receipt",
                "source_hash",
            ],
            "reason": "cards-only claims preserve scope, owner session, collision, and lease fields for routine routing; full claim rows remain behind the drilldown.",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --limit {safe_limit}{filter_args} --full"
            ),
        },
    }


def _claim_preview(values: List[str], *, limit: int = 5) -> List[str]:
    seen: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return sorted(seen)[:limit]


def _recent_task_ledger_writer_summary(
    repo_root: Path,
    *,
    window_minutes: int = TASK_LEDGER_RECENT_WRITER_WINDOW_MINUTES,
    tail_limit: int = TASK_LEDGER_RECENT_WRITER_TAIL_LIMIT,
    limit: int = 5,
) -> Dict[str, Any]:
    path = repo_root / TASK_LEDGER_EVENTS_REL
    if not path.exists():
        return {
            "schema": "task_ledger_recent_writer_summary_v0",
            "status": "source_missing",
            "event_path": str(TASK_LEDGER_EVENTS_REL),
            "window_minutes": window_minutes,
            "tail_limit": tail_limit,
            "recent_event_count": 0,
            "writer_count": 0,
            "writer_cards": [],
        }

    lines: deque[str] = deque(maxlen=max(1, int(tail_limit or 1)))
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    lines.append(line)
    except OSError as exc:
        return {
            "schema": "task_ledger_recent_writer_summary_v0",
            "status": "read_failed",
            "event_path": str(TASK_LEDGER_EVENTS_REL),
            "window_minutes": window_minutes,
            "tail_limit": tail_limit,
            "error": str(exc),
            "recent_event_count": 0,
            "writer_count": 0,
            "writer_cards": [],
        }

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=max(1, int(window_minutes or 1)))
    recent_events: List[Dict[str, Any]] = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        created_at = _parse_optional_datetime(event.get("created_at"))
        if not created_at or created_at < cutoff:
            continue
        source = event.get("source") if isinstance(event.get("source"), Mapping) else {}
        recent_events.append(
            {
                "created_at": created_at.isoformat(),
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "created_by": event.get("created_by"),
                "agent_run_id": event.get("agent_run_id"),
                "subject_id": event.get("subject_id"),
                "source_kind": source.get("kind"),
            }
        )

    groups: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for event in recent_events:
        key = (
            str(event.get("agent_run_id") or ""),
            str(event.get("created_by") or "unknown"),
            str(event.get("source_kind") or "unknown"),
        )
        group = groups.setdefault(
            key,
            {
                "agent_run_id": event.get("agent_run_id"),
                "created_by": event.get("created_by") or "unknown",
                "source_kind": event.get("source_kind") or "unknown",
                "event_count": 0,
                "latest_created_at": event.get("created_at"),
                "latest_event_id": event.get("event_id"),
                "subjects_preview": [],
            },
        )
        group["event_count"] += 1
        created_at_text = str(event.get("created_at") or "")
        if created_at_text >= str(group.get("latest_created_at") or ""):
            group["latest_created_at"] = created_at_text
            group["latest_event_id"] = event.get("event_id")
        subject_id = str(event.get("subject_id") or "").strip()
        if (
            subject_id
            and subject_id not in group["subjects_preview"]
            and len(group["subjects_preview"]) < 5
        ):
            group["subjects_preview"].append(subject_id)

    writer_cards = sorted(
        groups.values(),
        key=lambda row: (
            int(row.get("event_count") or 0),
            str(row.get("latest_created_at") or ""),
        ),
        reverse=True,
    )
    closeout_event_count = sum(
        1
        for event in recent_events
        if str(event.get("event_type") or "") in TASK_LEDGER_RECENT_CLOSEOUT_EVENT_TYPES
    )
    safe_limit = max(0, int(limit or 0))
    return {
        "schema": "task_ledger_recent_writer_summary_v0",
        "status": "recent_writers" if recent_events else "no_recent_writers",
        "event_path": str(TASK_LEDGER_EVENTS_REL),
        "window_minutes": window_minutes,
        "tail_limit": tail_limit,
        "recent_event_count": len(recent_events),
        "closeout_event_count": closeout_event_count,
        "non_closeout_event_count": max(0, len(recent_events) - closeout_event_count),
        "writer_count": len(writer_cards),
        "writer_cards": writer_cards[:safe_limit] if safe_limit else [],
        "writers_omitted": max(0, len(writer_cards) - safe_limit),
    }


def _compact_claim_session_summary_cards(
    snapshot: Mapping[str, Any],
    *,
    limit: int,
    repo_root: Path = REPO_ROOT,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    filter_args = _session_claims_filter_args(snapshot)
    session_rows: Dict[str, Dict[str, Any]] = {}
    active_claims = [
        row for row in list(snapshot.get("active_claims") or []) if isinstance(row, Mapping)
    ]
    for claim in active_claims:
        session_id = str(claim.get("session_id") or "unknown").strip() or "unknown"
        row = session_rows.setdefault(
            session_id,
            {
                "session_id": session_id,
                "actor": claim.get("actor"),
                "phase_id": claim.get("phase_id"),
                "active_claim_count": 0,
                "path_claim_count": 0,
                "td_claim_count": 0,
                "work_item_claim_count": 0,
                "other_claim_count": 0,
                "_paths": [],
                "_td_ids": [],
                "_work_item_ids": [],
                "lease_until_max": None,
            },
        )
        row["active_claim_count"] += 1
        scope_kind = str(claim.get("scope_kind") or "").strip()
        if scope_kind == "path":
            row["path_claim_count"] += 1
            row["_paths"].append(str(claim.get("path") or claim.get("scope_id") or ""))
        elif scope_kind in {"td", "td_id", "thread"}:
            row["td_claim_count"] += 1
            row["_td_ids"].append(str(claim.get("td_id") or claim.get("scope_id") or ""))
        elif scope_kind in {"work_item", "work_item_id"}:
            row["work_item_claim_count"] += 1
            row["_work_item_ids"].append(
                str(claim.get("work_item_id") or claim.get("scope_id") or "")
            )
        else:
            row["other_claim_count"] += 1
        leased_until = str(claim.get("leased_until") or "").strip()
        if leased_until and (
            not row["lease_until_max"] or leased_until > row["lease_until_max"]
        ):
            row["lease_until_max"] = leased_until
        if not row.get("actor") and claim.get("actor"):
            row["actor"] = claim.get("actor")
        if not row.get("phase_id") and claim.get("phase_id"):
            row["phase_id"] = claim.get("phase_id")

    session_cards = sorted(
        session_rows.values(),
        key=lambda row: (
            -int(row.get("active_claim_count") or 0),
            str(row.get("lease_until_max") or ""),
            str(row.get("session_id") or ""),
        ),
    )
    emitted = session_cards[:safe_limit] if safe_limit else []
    compact_cards: List[Dict[str, Any]] = []
    for row in emitted:
        paths = list(row.pop("_paths", []))
        td_ids = list(row.pop("_td_ids", []))
        work_item_ids = list(row.pop("_work_item_ids", []))
        session_id = str(row.get("session_id") or "unknown")
        compact_cards.append(
            {
                **row,
                "paths_preview": _claim_preview(paths),
                "paths_omitted": max(0, int(row.get("path_claim_count") or 0) - 5),
                "td_ids_preview": _claim_preview(td_ids),
                "td_ids_omitted": max(0, int(row.get("td_claim_count") or 0) - 5),
                "work_item_ids_preview": _claim_preview(work_item_ids),
                "work_item_ids_omitted": max(
                    0, int(row.get("work_item_claim_count") or 0) - 5
                ),
                "drilldown": (
                    "./repo-python tools/meta/factory/work_ledger.py "
                    f"session-status --session-id {shlex.quote(session_id)} --full"
                ),
            }
        )

    truncation = (
        snapshot.get("truncation") if isinstance(snapshot.get("truncation"), Mapping) else {}
    )
    recent_task_ledger_writers = _recent_task_ledger_writer_summary(
        repo_root,
        limit=min(max(safe_limit, 1), 5),
    )
    counts = dict(snapshot.get("counts") or {})
    recent_task_ledger_event_count = int(
        recent_task_ledger_writers.get("recent_event_count") or 0
    )
    recent_non_closeout_event_count = int(
        recent_task_ledger_writers.get("non_closeout_event_count") or 0
    )
    active_claim_count = int(counts.get("active_claims") or 0)
    recent_closeout_only_no_claims = (
        recent_task_ledger_event_count > 0
        and recent_non_closeout_event_count == 0
        and active_claim_count == 0
    )
    coordination_gap_hint = (
        "task_ledger_source_recently_moved_without_active_claims"
        if recent_non_closeout_event_count and active_claim_count == 0
        else None
    )
    return {
        "schema": "work_ledger_active_claim_session_summary_v1",
        "generated_at": snapshot.get("generated_at"),
        "status": snapshot.get("status"),
        "counts": {
            **counts,
            "claim_sessions_total": len(session_cards),
            "claim_sessions_emitted": len(compact_cards),
        },
        "count_semantics": work_ledger_runtime.coordination_count_semantics(counts),
        "recent_task_ledger_writers": {
            **recent_task_ledger_writers,
            **(
                {"coordination_status": "recent_closeout_only_no_active_claims"}
                if recent_closeout_only_no_claims
                else {}
            ),
            **(
                {"coordination_gap_hint": coordination_gap_hint}
                if coordination_gap_hint
                else {}
            ),
        },
        "claim_session_cards": compact_cards,
        "claim_sessions_omitted": max(0, len(session_cards) - len(compact_cards)),
        **(
            {"path_filter": snapshot.get("path_filter")}
            if isinstance(snapshot.get("path_filter"), Mapping)
            else {}
        ),
        **(
            {"session_filter": snapshot.get("session_filter")}
            if isinstance(snapshot.get("session_filter"), Mapping)
            else {}
        ),
        "source_claim_scan": {
            "limit": truncation.get("limit"),
            "active_claims_total": truncation.get("active_claims_total"),
            "active_claims_scanned": truncation.get("active_claims_emitted"),
            "truncated": bool(
                (truncation.get("active_claims_total") or 0)
                > (truncation.get("active_claims_emitted") or 0)
            ),
        },
        "source_freshness": {
            "status": (snapshot.get("source_freshness") or {}).get("status")
            if isinstance(snapshot.get("source_freshness"), Mapping)
            else None,
            "policy": (snapshot.get("source_freshness") or {}).get("policy")
            if isinstance(snapshot.get("source_freshness"), Mapping)
            else None,
        },
        "drilldown_commands": {
            "full_claims": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --limit {safe_limit}{filter_args} --full"
            ),
            "claim_cards": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --refresh --limit {safe_limit}{filter_args} --cards-only"
            ),
            "seed_speed_status": WORK_LEDGER_SEED_SPEED_COMMAND,
            "session_overview_cards": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
        },
        "omission_receipt": {
            "omitted": [
                "per-claim rows",
                "claim_id",
                "claimed_at",
                "release metadata",
                "source receipts",
            ],
            "reason": (
                "session-summary groups refreshed claims by owner session so lane "
                "selection is not dominated by one high-volume session."
            ),
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --limit {safe_limit}{filter_args} --full"
            ),
        },
    }


def _parse_optional_datetime(value: Any) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pass_freshness_for_session(row: Mapping[str, Any], heartbeat: Mapping[str, Any]) -> str | None:
    explicit = str(heartbeat.get("freshness_state") or "").strip()
    if explicit:
        return explicit
    if row.get("ended_at") or row.get("ended"):
        return "ended"
    if row.get("orphaned_active"):
        return "orphaned"
    if row.get("stale"):
        return "stale"
    expires_at = _parse_optional_datetime(heartbeat.get("expires_at"))
    if expires_at is not None and expires_at < datetime.now(timezone.utc):
        return "expired"
    if heartbeat:
        return "live"
    return None


def _compact_session_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    risk_flags: list[str] = []
    session_id = str(row.get("session_id") or "").strip()
    quoted_session_id = shlex.quote(session_id) if session_id else "<session_id>"
    if row.get("orphaned_active"):
        risk_flags.append("orphaned_active")
    if row.get("stale"):
        risk_flags.append("stale")
    if row.get("unclaimed_touched_td_ids") or row.get("unclaimed_touched_work_item_ids"):
        risk_flags.append("unclaimed_touched_work")
    if row.get("active_claims"):
        risk_flags.append("active_claims")
    heartbeat = (
        dict(row.get("pass_heartbeat") or {})
        if isinstance(row.get("pass_heartbeat"), Mapping)
        else {}
    )
    return {
        "session_id": row.get("session_id"),
        "actor": row.get("actor"),
        "phase_id": row.get("phase_id"),
        "last_activity_at": row.get("last_activity_at"),
        "last_signal_at": row.get("last_signal_at"),
        "idle_seconds": row.get("idle_seconds"),
        "pass_state": heartbeat.get("pass_state"),
        "current_pass_line": heartbeat.get("current_pass_line"),
        "last_pass_result_line": heartbeat.get("last_pass_result_line"),
        "freshness_state": _pass_freshness_for_session(row, heartbeat),
        "pass_source": heartbeat.get("source"),
        "risk_flags": risk_flags,
        "drilldown_command": (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-status --session-id {quoted_session_id} --full"
        ),
    }


def _compact_single_session_status(
    runtime_status: Mapping[str, Any],
    *,
    session_id: str,
    limit: int,
    include_full_session: bool = False,
) -> Dict[str, Any]:
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    session = sessions.get(session_id) if isinstance(sessions, Mapping) else None
    safe_limit = max(0, int(limit or 0))
    if not isinstance(session, Mapping):
        return {
            "schema": "work_ledger_session_status_card_v1",
            "status": "missing",
            "session_id": session_id,
            "hint": "Run session-status --seed-speed to inspect active session ids.",
            "drilldown_commands": {
                "seed_speed": WORK_LEDGER_SEED_SPEED_COMMAND,
                "overview_cards": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
                "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
            },
        }

    active_claims = [
        claim
        for claim in list(session.get("claims") or [])[:safe_limit]
        if isinstance(claim, Mapping) and not claim.get("released_at") and not claim.get("expired_at")
    ]
    payload: Dict[str, Any] = {
        "schema": "work_ledger_session_status_detail_v1"
        if include_full_session
        else "work_ledger_session_status_card_v1",
        "status": "found",
        "session_id": session_id,
        "session": dict(session) if include_full_session else _compact_session_row(session),
        "session_state": {
            "ended": bool(session.get("ended_at")),
            "stale": bool(session.get("stale")),
            "append_exempt": bool(session.get("append_exempt")),
            "session_had_ledger_append": bool(session.get("session_had_ledger_append")),
            "touched_work": bool(session.get("touched_work")),
        },
        "active_claim_count": len(active_claims),
        "active_claim_cards": [
            _compact_claim_card(claim, fallback_session=session)
            for claim in active_claims
        ],
        "drilldown_commands": {
            "seed_speed": WORK_LEDGER_SEED_SPEED_COMMAND,
            "overview_cards": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
            "single_full": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-status --session-id {shlex.quote(session_id)} --full"
            ),
            "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
        },
    }
    if not session.get("ended_at"):
        payload["finalize_command"] = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-finalize --session-id {shlex.quote(session_id)}"
        )
    return payload


_AWARENESS_CARD_KEYS: tuple[str, ...] = (
    "session_id",
    "actor",
    "phase_id",
    "freshness_state",
    "idle_seconds",
    "orphaned_active",
    "pass_id",
    "pass_seq",
    "pass_state",
    "current_pass_line",
    "last_pass_result_line",
    "source",
    "updated_at",
    "scope_refs",
    "claim_refs",
    "touched_td_ids",
    "touched_work_item_ids",
)


def _awareness_repair_summary(
    repair_rows: List[Mapping[str, Any]],
    *,
    session_id: str | None,
) -> Dict[str, Any]:
    failure_classes = sorted(
        {
            str(row.get("failure_class"))
            for row in repair_rows
            if row.get("failure_class")
        }
    )
    owning_surfaces = sorted(
        {
            str(row.get("owning_surface"))
            for row in repair_rows
            if row.get("owning_surface")
        }
    )
    drilldown = "./repo-python tools/meta/factory/work_ledger.py session-status --full"
    if session_id:
        drilldown = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-status --session-id {shlex.quote(session_id)} --full"
        )
    return {
        "repair_row_count": len(repair_rows),
        "failure_classes": failure_classes,
        "owning_surfaces": owning_surfaces[:4],
        "drilldown": drilldown,
    }


def _awareness_claim_summary(
    claim_refs: List[Mapping[str, Any]],
    *,
    session_id: str | None,
) -> Dict[str, Any]:
    paths = [str(row.get("path") or "") for row in claim_refs if row.get("path")]
    td_ids = [str(row.get("td_id") or "") for row in claim_refs if row.get("td_id")]
    work_item_ids = [
        str(row.get("work_item_id") or "") for row in claim_refs if row.get("work_item_id")
    ]
    scope_kinds = sorted(
        {str(row.get("scope_kind")) for row in claim_refs if row.get("scope_kind")}
    )
    drilldown = "./repo-python tools/meta/factory/work_ledger.py session-status --full"
    if session_id:
        drilldown = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-status --session-id {shlex.quote(session_id)} --full"
        )
    return {
        "claim_count": len(claim_refs),
        "scope_kinds": scope_kinds[:4],
        "path_count": len(paths),
        "td_id_count": len(td_ids),
        "work_item_id_count": len(work_item_ids),
        "paths_preview": paths[:2],
        "td_ids_preview": td_ids[:2],
        "work_item_ids_preview": work_item_ids[:2],
        "drilldown": drilldown,
    }


def _compact_awareness_card(
    row: Mapping[str, Any],
    *,
    include_repair_rows: bool,
) -> Dict[str, Any]:
    card: Dict[str, Any] = {}
    for key in _AWARENESS_CARD_KEYS:
        if key == "claim_refs" and not include_repair_rows:
            continue
        value = row.get(key)
        if isinstance(value, Mapping):
            card[key] = dict(value)
        elif isinstance(value, list):
            card[key] = list(value)
        else:
            card[key] = value

    claim_refs = [
        dict(item) for item in list(row.get("claim_refs") or []) if isinstance(item, Mapping)
    ]
    if claim_refs and not include_repair_rows:
        card["claim_summary"] = _awareness_claim_summary(
            claim_refs,
            session_id=str(row.get("session_id") or "") or None,
        )

    repair_rows = [
        dict(item) for item in list(row.get("repair_rows") or []) if isinstance(item, Mapping)
    ]
    if not repair_rows:
        return card
    if include_repair_rows:
        card["repair_rows"] = repair_rows
    else:
        card["repair_summary"] = _awareness_repair_summary(
            repair_rows,
            session_id=str(row.get("session_id") or "") or None,
        )
    return card


def _compact_monitor_card(
    row: Mapping[str, Any],
    *,
    include_repair_rows: bool,
) -> Dict[str, Any]:
    card = dict(row)
    repair_rows = [
        dict(item) for item in list(row.get("repair_rows") or []) if isinstance(item, Mapping)
    ]
    if repair_rows and not include_repair_rows:
        card.pop("repair_rows", None)
        card["repair_summary"] = _awareness_repair_summary(
            repair_rows,
            session_id=None,
        )
        if row.get("drilldown"):
            card["repair_summary"]["drilldown"] = row.get("drilldown")
    return card


def _cohort_speed_summary(
    overview: Mapping[str, Any],
    *,
    awareness_cards: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    heartbeat = (
        overview.get("heartbeat_participation")
        if isinstance(overview.get("heartbeat_participation"), Mapping)
        else {}
    )
    active_claim_session_ids = sorted(
        {
            str(card.get("session_id"))
            for card in awareness_cards
            if card.get("session_id")
            and (
                card.get("claim_refs")
                or (
                    isinstance(card.get("claim_summary"), Mapping)
                    and int(card["claim_summary"].get("claim_count") or 0) > 0
                )
            )
        }
    )
    return {
        "effective_active_sessions": counts.get(
            "effective_active_sessions", heartbeat.get("effective_active_sessions")
        ),
        "active_claims": counts.get("active_claims"),
        "active_claim_session_count": len(active_claim_session_ids),
        "active_claim_session_ids": active_claim_session_ids[:8],
        "explicit_current_pass_sessions": heartbeat.get("explicit_current_pass_count", 0),
        "projected_unknown_sessions": heartbeat.get("projected_unknown_count", 0),
        "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
        "first_action": (
            "Use session-level claim summaries for write-active lanes, then publish "
            "session-heartbeat for participating live seeds that can write."
        ),
        "claims_fast_path": (
            "./repo-python tools/meta/factory/work_ledger.py "
            "session-claims --refresh --session-summary --limit 12 --cards-only"
        ),
        "heartbeat_fast_path": (
            "./repo-python tools/meta/factory/work_ledger.py "
            "session-heartbeat --session-id <id> --state inspecting "
            "--current-pass-line '<public current pass>' "
            "--last-pass-result-line '<public previous result>' "
            "--scope-ref <path-or-claim>"
        ),
    }


def _seed_speed_status(
    overview: Mapping[str, Any],
    *,
    limit: int,
    prefer_non_heartbeat: bool = False,
    dirty_tree_pressure: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return work_ledger_runtime.build_seed_speed_status(
        overview,
        limit=limit,
        prefer_non_heartbeat=prefer_non_heartbeat,
        dirty_tree_pressure=dirty_tree_pressure,
    )


def _seed_speed_heartbeat_gap_row(card: Mapping[str, Any]) -> Dict[str, Any]:
    session_id = str(card.get("session_id") or "").strip()
    scope_ref = _seed_speed_scope_ref(card)
    return {
        "session_id": session_id,
        "actor": card.get("actor"),
        "phase_id": card.get("phase_id"),
        "active_claim_count": card.get("active_claim_count"),
        "heartbeat_source": card.get("heartbeat_source"),
        "freshness_state": card.get("freshness_state"),
        "scope_ref": scope_ref,
        "heartbeat_command": (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-heartbeat --session-id {shlex.quote(session_id)} --state inspecting "
            "--current-pass-line '<public current pass>' "
            "--last-pass-result-line '<public previous result>' "
            f"--scope-ref {shlex.quote(scope_ref)}"
        ),
    }


def _seed_speed_scope_ref(card: Mapping[str, Any]) -> str:
    for key in ("paths_preview", "work_item_ids_preview", "td_ids_preview"):
        rows = card.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            text = str(row or "").strip()
            if text:
                return text
    return "<path-or-claim>"


def _seed_speed_claim_collision_failure_class(collision: Mapping[str, Any]) -> str:
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    sessions = {str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")}
    if len(sessions) == 1 and len(claims) > 1:
        return "duplicate_same_session_claim"
    if collision.get("path"):
        return "path_claim_collision"
    if collision.get("work_item_id"):
        return "work_item_claim_collision"
    if collision.get("td_id"):
        return "td_claim_collision"
    return "claim_collision"


def _seed_speed_claim_collision_command(
    collision: Mapping[str, Any],
    *,
    failure_class: str,
) -> str:
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    sessions = sorted({str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")})
    claim_ids = [str(claim.get("claim_id") or "") for claim in claims if claim.get("claim_id")]
    path = str(collision.get("path") or "").strip()
    work_item_id = str(collision.get("work_item_id") or "").strip()
    td_id = str(collision.get("td_id") or "").strip()
    scope_kind = str(collision.get("scope_kind") or "").strip()
    if failure_class == "duplicate_same_session_claim" and sessions and claim_ids:
        return (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-release-claim --session-id {shlex.quote(sessions[0])} "
            f"--claim-id {shlex.quote(claim_ids[-1])} "
            "--reason duplicate_same_session_claim"
        )
    if path:
        return (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"mutation-check --path {shlex.quote(path)} --require-exclusive"
        )
    if work_item_id:
        return (
            "./repo-python tools/meta/control/mission_transaction_preflight.py "
            f"--subject-id {shlex.quote(work_item_id)} --control-summary"
        )
    if td_id:
        return (
            "./repo-python tools/meta/control/mission_transaction_preflight.py "
            f"--subject-id {shlex.quote(td_id)} --control-summary"
        )
    return (
        "./repo-python tools/meta/factory/work_ledger.py "
        f"session-claims --refresh --limit 12 --full # scope_kind={shlex.quote(scope_kind)}"
    )


def _seed_speed_claim_collision_action_row(collision: Mapping[str, Any]) -> Dict[str, Any]:
    failure_class = _seed_speed_claim_collision_failure_class(collision)
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    return {
        "failure_class": failure_class,
        "scope_kind": collision.get("scope_kind"),
        "scope_id": collision.get("scope_id"),
        "td_id": collision.get("td_id"),
        "path": collision.get("path"),
        "work_item_id": collision.get("work_item_id"),
        "claim_count": collision.get("claim_count"),
        "actors": list(collision.get("actors") or []),
        "session_ids": sorted(
            {str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")}
        ),
        "active_claims_preview": [
            {
                "claim_id": claim.get("claim_id"),
                "session_id": claim.get("session_id"),
                "actor": claim.get("actor"),
                "phase_id": claim.get("phase_id"),
                "scope_kind": claim.get("scope_kind"),
                "path": claim.get("path"),
                "work_item_id": claim.get("work_item_id"),
                "td_id": claim.get("td_id"),
                "leased_until": claim.get("leased_until"),
            }
            for claim in claims[:3]
        ],
        "safe_next_command": _seed_speed_claim_collision_command(
            collision,
            failure_class=failure_class,
        ),
    }


def _compact_session_status_overview(
    overview: Mapping[str, Any],
    *,
    limit: int,
    include_rows: bool = True,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    contention = overview.get("contention") if isinstance(overview.get("contention"), Mapping) else {}
    awareness_cards = [
        _compact_awareness_card(row, include_repair_rows=include_rows)
        for row in list(overview.get("awareness_cards") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    repair_rows = [
        dict(row)
        for row in list(overview.get("repair_rows") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    payload: Dict[str, Any] = {
        "schema": overview.get("schema"),
        "generated_at": overview.get("generated_at"),
        "mode": "compact_overview" if include_rows else "cards_only_overview",
        "orphan_after_seconds": overview.get("orphan_after_seconds"),
        "counts": overview.get("counts") or {},
        "count_semantics": work_ledger_runtime.coordination_count_semantics(
            overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {},
            heartbeat=overview.get("heartbeat_participation")
            if isinstance(overview.get("heartbeat_participation"), Mapping)
            else {},
        ),
        "monitor_cards": [
            _compact_monitor_card(row, include_repair_rows=include_rows)
            for row in list(overview.get("monitor_cards") or [])
            if isinstance(row, Mapping)
        ],
        "awareness_cards": awareness_cards,
        "heartbeat_participation": dict(overview.get("heartbeat_participation") or {}),
        "repair_rows": repair_rows,
        "cohort_speed_summary": _cohort_speed_summary(
            overview,
            awareness_cards=awareness_cards,
        ),
        "recommended_landing_lane": overview.get("recommended_landing_lane"),
        "contention": {
            "risk_level": contention.get("risk_level"),
            "signals": list(contention.get("signals") or []),
            "td_id_collision_count": len(contention.get("td_id_collisions") or []),
            "claim_collision_count": len(contention.get("claim_collisions") or []),
            "unknown_scope_active_session_count": len(contention.get("unknown_scope_active_sessions") or []),
            "unclaimed_touched_session_count": len(contention.get("unclaimed_touched_sessions") or []),
            "orphaned_active_session_count": len(contention.get("orphaned_active_sessions") or []),
        },
        "recommended_actions": list(overview.get("recommended_actions") or [])[:safe_limit],
        "drilldown_commands": {
            "seed_speed": WORK_LEDGER_SEED_SPEED_COMMAND,
            "overview_cards": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
            "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
        },
    }
    if include_rows:
        payload["active_session_rows"] = [
            _compact_session_row(row)
            for row in list(overview.get("active_sessions") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ]
        payload["effective_active_session_rows"] = [
            _compact_session_row(row)
            for row in list(overview.get("effective_active_sessions") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ]
        payload["orphaned_active_session_rows"] = [
            _compact_session_row(row)
            for row in list(overview.get("orphaned_active_sessions") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ]
    else:
        payload["omission_receipt"] = {
            "omitted": [
                "active_session_rows",
                "effective_active_session_rows",
                "orphaned_active_session_rows",
                "monitor_card_repair_rows",
                "per_awareness_card_repair_rows",
                "per_awareness_card_claim_refs",
            ],
            "reason": "cards-only overview preserves monitor cards, awareness cards, repair summaries, and counts for routine status checks; row evidence remains behind drilldowns.",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-status --overview --with-session-cards --limit {safe_limit}"
            ),
        }
    return payload


def _compact_session_lifecycle_payload(
    status: Mapping[str, Any],
    *,
    schema: str,
    command: str,
    session_id: str,
    action: str,
    limit: int,
) -> Dict[str, Any]:
    sessions = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    session = dict(sessions.get(session_id) or {}) if isinstance(sessions, Mapping) else {}
    overview = work_ledger_runtime.build_session_cohort_overview(status, limit=limit)
    contention = dict(overview.get("contention") or {})
    counts = dict(overview.get("counts") or {})
    session_summary: Dict[str, Any] | None = None
    if session:
        claims = [item for item in (session.get("claims") or []) if isinstance(item, Mapping)]
        active_claim_count = sum(
            1 for claim in claims if not claim.get("released_at") and not claim.get("expired_at")
        )
        session_summary = {
            "session_id": session.get("session_id"),
            "actor": session.get("actor"),
            "phase_id": session.get("phase_id"),
            "family_id": session.get("family_id"),
            "read_receipt_id": session.get("read_receipt_id"),
            "bootstrapped_at": session.get("bootstrapped_at"),
            "last_activity_at": session.get("last_activity_at"),
            "last_query_at": session.get("last_query_at"),
            "last_append_at": session.get("last_append_at"),
            "pass_heartbeat": dict(session.get("pass_heartbeat") or {})
            if isinstance(session.get("pass_heartbeat"), Mapping)
            else None,
            "ended_at": session.get("ended_at"),
            "end_action": session.get("end_action"),
            "has_activity": bool(session.get("has_activity")),
            "touched_work": bool(session.get("touched_work")),
            "touched_td_ids": list(session.get("touched_td_ids") or []),
            "touched_work_item_ids": list(session.get("touched_work_item_ids") or []),
            "queries": int(session.get("queries") or 0),
            "writes": int(session.get("writes") or 0),
            "session_had_ledger_append": bool(session.get("session_had_ledger_append")),
            "append_exempt": bool(session.get("append_exempt")),
            "append_exempt_reason": session.get("append_exempt_reason"),
            "append_exempt_refs": list(session.get("append_exempt_refs") or []),
            "append_exempted_at": session.get("append_exempted_at"),
            "stale": bool(session.get("stale")),
            "stale_reason": session.get("stale_reason"),
            "open_todos_touched_this_session": int(
                session.get("open_todos_touched_this_session") or 0
            ),
            "claim_count": len(claims),
            "active_claim_count": active_claim_count,
        }
    receipt_authority_guard: Dict[str, Any] | None = None
    if (
        command == "session-finalize"
        and session_summary
        and session_summary["touched_work"]
        and not session_summary["session_had_ledger_append"]
        and not session_summary["append_exempt"]
    ):
        receipt_authority_guard = {
            "status": "append_missing_before_finalize",
            "rule": (
                "Read receipts are live-session write tokens. Append or close the Work "
                "Ledger receipt before session-finalize; after finalization, this "
                "session's read_receipt_id cannot write."
            ),
            "point_of_use": "session-finalize compact payload",
            "mutation_stage": (
                "post_finalize_stale_session" if session_summary.get("ended_at") else "pre_finalize_block"
            ),
            "pre_finalize_repair": (
                "Run progress/close/append-open with the live read_receipt_id before "
                "running session-finalize."
            ),
            "post_finalize_recovery": (
                "Bootstrap a fresh Work Ledger session, append the missing receipt "
                "with the new read_receipt_id, then finalize that recovery session."
            ),
            "recovery_command_template": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-slug <recovery_session_slug> --actor <actor> --phase-id <phase_id> "
                "--td-id <td_or_work_item_id>"
            ),
        }
    payload = {
        "schema": schema,
        "generated_at": status.get("generated_at") or work_ledger.utc_now(),
        "mode": "compact",
        "command": command,
        "session_id": session_id,
        "action": action,
        "session_found": bool(session),
        "session": session_summary,
        "overview_summary": {
            "schema": overview.get("schema"),
            "counts": {
                "sessions_total": counts.get("sessions_total", 0),
                "active_sessions": counts.get("active_sessions", 0),
                "effective_active_sessions": counts.get("effective_active_sessions", 0),
                "orphaned_active_sessions": counts.get("orphaned_active_sessions", 0),
                "stale_sessions": counts.get("stale_sessions", 0),
                "active_claims": counts.get("active_claims", 0),
                "claim_collisions": counts.get("claim_collisions", 0),
                "unclaimed_touched_sessions": counts.get("unclaimed_touched_sessions", 0),
            },
            "contention": {
                "risk_level": contention.get("risk_level", "clear"),
                "signals": list(contention.get("signals") or []),
            },
            "heartbeat_participation": dict(overview.get("heartbeat_participation") or {}),
            "recommended_actions": list(overview.get("recommended_actions") or [])[:limit],
        },
        "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
        "drilldown_commands": {
            "compact_overview": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-status --overview --cards-only --limit {int(limit or 0)}"
            ),
            "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
        },
        "landmine_avoidance": {
            "rule": "Agent-facing lifecycle commands do not print runtime_status.sessions by default, and session-finalize blocks touched/no-append sessions before it releases claims unless an explicit append-exempt closeout is recorded.",
            "why": "The full session map is machine state; use compact overview unless diagnosing the runtime file itself. Finalize is the normal closeout path after a Work Ledger append exists; --append-exempt-reason is for commit-only/projection-only sessions, while --allow-missing-append and --no-release-claims are diagnostic escape hatches.",
        },
    }
    if receipt_authority_guard:
        payload["receipt_authority_guard"] = receipt_authority_guard
    return payload


def _iso_utc_from_epoch(epoch: object) -> str | None:
    try:
        value = int(epoch)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _json_loads_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _compact_codex_command(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    text = text.replace(str(Path.home()), "~")
    if len(text) > 240:
        return f"{text[:237]}..."
    return text


def _compact_handle_preview(value: Any, *, limit: int = OVERLAP_TITLE_PREVIEW_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    safe_limit = max(16, int(limit or 16))
    if len(text) <= safe_limit:
        return text
    return f"{text[: max(0, safe_limit - 3)]}..."


def _handle_payload_kind(value: Any) -> str:
    text = str(value or "").lstrip()
    if text.startswith("PACKET v="):
        return "packet_title_or_long_prompt"
    if "\n" in text:
        return "long_prompt_or_trace_title"
    return "session_title"


def _session_title_handle_fields(row: Mapping[str, Any]) -> Dict[str, Any]:
    title = str(row.get("title") or row.get("external_title") or "")
    title_bytes = len(title.encode("utf-8"))
    title_hash = f"sha256:{hashlib.sha256(title.encode('utf-8')).hexdigest()}"
    preview = _compact_handle_preview(title)
    fields: Dict[str, Any] = {
        "title": title if title_bytes <= OVERLAP_TITLE_INLINE_BYTE_LIMIT else preview,
        "title_preview": preview,
        "title_bytes": title_bytes,
        "title_hash": title_hash,
        "title_kind": _handle_payload_kind(title),
        "title_full_omitted": title_bytes > OVERLAP_TITLE_INLINE_BYTE_LIMIT,
    }
    if title_bytes > OVERLAP_TITLE_INLINE_BYTE_LIMIT:
        session_id = str(row.get("session_id") or "").strip()
        title_drilldown = (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full --raw-full <same session-preflight args>"
        )
        fields["title_ref"] = (
            f"work_ledger_runtime_session:{session_id}:external_title"
            if session_id
            else "work_ledger_runtime_session:external_title"
        )
        fields["title_drilldown"] = title_drilldown
        fields["omission_receipt"] = {
            "omitted": ["full title body"],
            "reason": (
                "Overlap rows identify sessions; full prompt/title bodies remain "
                "recoverable by rerunning the same Work Ledger session-preflight "
                "with --full --raw-full."
            ),
            "drilldown": title_drilldown,
            "source_ref": fields["title_ref"],
        }
    return fields


def _normalize_codex_repo_path(raw_path: Any, repo_root: Path) -> str | None:
    token = str(raw_path or "").strip().strip("\"'`[]{}(),;")
    token = token.replace("\\/", "/")
    root_prefix = f"{repo_root}/"
    if token.startswith(root_prefix):
        token = token[len(root_prefix) :]
    if token.startswith("./"):
        token = token[2:]
    token = re.sub(r"(?::\d+|#L\d+)$", "", token)
    token = token.strip().strip("\"'`[]{}(),;")
    if not token or token.startswith("/") or token.startswith("~"):
        return None
    if "..." in token:
        return None
    parts = [part for part in token.split("/") if part]
    if not parts or any(part == ".." for part in parts):
        return None
    if token.startswith((".codex/auth", ".codex/config", ".claude/.credentials")):
        return None
    return "/".join(parts)


def _extract_codex_repo_paths(text: Any, repo_root: Path) -> List[str]:
    haystack = str(text or "")
    if not haystack:
        return []
    haystack = haystack.replace(f"{repo_root}/", "")
    paths: List[str] = []
    for match in _CODEX_PATH_TOKEN_RE.finditer(haystack):
        path = _normalize_codex_repo_path(match.group("path"), repo_root)
        if path:
            paths.append(path)
    return paths


def _extract_patch_paths(text: Any, repo_root: Path) -> List[str]:
    paths: List[str] = []
    for match in _CODEX_PATCH_FILE_RE.finditer(str(text or "")):
        path = _normalize_codex_repo_path(match.group("path"), repo_root)
        if path:
            paths.append(path)
    return paths


def _recent_unique(values: List[str], limit: int) -> List[str]:
    seen: set[str] = set()
    recent: List[str] = []
    for value in reversed(values):
        if not value or value in seen:
            continue
        seen.add(value)
        recent.append(value)
        if len(recent) >= limit:
            break
    return list(reversed(recent))


def _safe_codex_tool_texts(value: Any) -> List[tuple[str, str]]:
    decoded = _json_loads_maybe(value)
    collected: List[tuple[str, str]] = []
    if isinstance(decoded, dict):
        for key, nested in decoded.items():
            if key in {"encrypted_content", "output", "aggregated_output", "stdout", "stderr", "content", "message"}:
                continue
            if key in {"cmd", "path", "file", "filename", "workdir", "recipient_name"}:
                collected.append((key, str(nested or "")))
            collected.extend(_safe_codex_tool_texts(nested))
        return collected
    if isinstance(decoded, list):
        for nested in decoded:
            collected.extend(_safe_codex_tool_texts(nested))
        return collected
    if isinstance(decoded, str):
        collected.append(("text", decoded))
    return collected


def _codex_command_from_event_payload(payload: Dict[str, Any]) -> str:
    command = payload.get("command")
    if isinstance(command, list):
        argv = [str(part) for part in command]
        if "-lc" in argv:
            index = argv.index("-lc")
            if index + 1 < len(argv):
                return argv[index + 1]
        return " ".join(argv)
    return ""


def _read_recent_nonempty_text_lines(
    path: Path,
    *,
    max_lines: int,
    initial_bytes: int = 256 * 1024,
    max_bytes: int = 64 * 1024 * 1024,
) -> List[str]:
    try:
        file_size = path.stat().st_size
    except OSError:
        return []
    if file_size <= 0:
        return []
    target_lines = max(1, int(max_lines or 1))
    window_size = min(file_size, max(1, int(initial_bytes or 1)))
    byte_ceiling = max(window_size, int(max_bytes or window_size))
    with path.open("rb") as handle:
        while True:
            start = max(0, file_size - window_size)
            handle.seek(start)
            raw = handle.read(file_size - start)
            text = raw.decode("utf-8", errors="replace")
            lines = text.splitlines()
            if start > 0 and lines:
                lines = lines[1:]
            nonempty = [line for line in lines if line.strip()]
            if len(nonempty) >= target_lines or start == 0 or window_size >= byte_ceiling:
                return nonempty[-target_lines:]
            window_size = min(file_size, window_size * 2, byte_ceiling)


def _codex_rollout_activity_summary(
    rollout_path: str | None,
    *,
    repo_root: Path,
    max_events: int = CODEX_ROLLOUT_TAIL_EVENTS,
) -> Dict[str, Any] | None:
    if not rollout_path:
        return None
    path = Path(str(rollout_path)).expanduser()
    if not path.exists() or not path.is_file():
        return {
            "schema": "codex_rollout_activity_summary_v1",
            "rollout_path": str(path),
            "available": False,
            "reason": "rollout_path_missing",
        }
    lines = _read_recent_nonempty_text_lines(path, max_lines=max_events)
    tool_counts: Counter[str] = Counter()
    commands: List[str] = []
    referenced_paths: List[str] = []
    mutation_paths: List[str] = []
    parsed_events = 0
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        parsed_events += 1
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event.get("type") == "response_item" and payload.get("type") == "function_call":
            tool_name = str(payload.get("name") or "unknown")
            tool_counts[tool_name] += 1
            raw_arguments = payload.get("arguments")
            for key, text in _safe_codex_tool_texts(raw_arguments):
                if key == "cmd":
                    command = _compact_codex_command(text)
                    if command:
                        commands.append(command)
                referenced_paths.extend(_extract_codex_repo_paths(text, repo_root))
            if tool_name.endswith("apply_patch"):
                mutation_paths.extend(_extract_patch_paths(raw_arguments, repo_root))
        elif event.get("type") == "event_msg" and payload.get("type") == "exec_command_end":
            tool_counts["exec_command"] += 1
            raw_command = _codex_command_from_event_payload(payload)
            command = _compact_codex_command(raw_command)
            if command:
                commands.append(command)
                referenced_paths.extend(_extract_codex_repo_paths(raw_command, repo_root))
            parsed_cmd = payload.get("parsed_cmd")
            if isinstance(parsed_cmd, list):
                for entry in parsed_cmd:
                    if isinstance(entry, dict):
                        for key in ("cmd", "path", "name"):
                            referenced_paths.extend(_extract_codex_repo_paths(entry.get(key), repo_root))
    return {
        "schema": "codex_rollout_activity_summary_v1",
        "rollout_path": str(path),
        "available": True,
        "tail_event_count": len(lines),
        "parsed_event_count": parsed_events,
        "recent_tool_names": sorted(tool_counts.keys()),
        "recent_commands": _recent_unique(commands, CODEX_ROLLOUT_COMMAND_LIMIT),
        "recent_referenced_paths": _recent_unique(referenced_paths, CODEX_ROLLOUT_PATH_LIMIT),
        "recent_mutation_paths": _recent_unique(mutation_paths, CODEX_ROLLOUT_PATH_LIMIT),
    }


def _codex_thread_candidates(
    *,
    db_path: Path,
    repo_root: Path,
    since_minutes: float,
    limit: int,
    include_all_cwds: bool,
) -> List[Dict[str, Any]]:
    if not db_path.exists():
        return []
    cutoff = int((datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).timestamp())
    conditions = ["archived = 0", "updated_at >= ?"]
    params: List[Any] = [cutoff]
    if not include_all_cwds:
        conditions.append("(cwd = ? OR cwd LIKE ?)")
        params.extend((str(repo_root), f"{repo_root}/.claude/worktrees/%"))
    where_clause = " AND ".join(conditions)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only = 1")
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(threads)").fetchall()}
        rollout_select = "rollout_path" if "rollout_path" in columns else "NULL AS rollout_path"
        sql = (
            "SELECT id, created_at, updated_at, title, agent_role, reasoning_effort, "
            f"tokens_used, git_branch, model, cwd, {rollout_select} "
            f"FROM threads WHERE {where_clause} ORDER BY updated_at DESC LIMIT ?"
        )
        params.append(max(1, int(limit or 1)))
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        (
            thread_id,
            created_at,
            updated_at,
            title,
            agent_role,
            reasoning_effort,
            tokens_used,
            git_branch,
            model,
            cwd,
            rollout_path,
        ) = row
        rollout_activity = _codex_rollout_activity_summary(
            str(rollout_path or ""),
            repo_root=repo_root,
        )
        candidates.append(
            {
                "codex_thread_id": str(thread_id),
                "session_id": f"codex:{thread_id}",
                "title": title or "",
                "created_at": _iso_utc_from_epoch(created_at),
                "updated_at": _iso_utc_from_epoch(updated_at),
                "agent_role": agent_role or "",
                "reasoning_effort": reasoning_effort or "",
                "tokens_used": int(tokens_used or 0),
                "git_branch": git_branch or "",
                "model": model or "",
                "cwd": cwd or "",
                "rollout_path": rollout_path or "",
                "rollout_activity": rollout_activity,
            }
        )
    return candidates


def _import_codex_sessions(
    *,
    db_path: Path,
    actor: str,
    phase_id: str | None,
    family_id: str | None,
    since_minutes: float,
    limit: int,
    include_all_cwds: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    candidates = _codex_thread_candidates(
        db_path=db_path,
        repo_root=REPO_ROOT,
        since_minutes=since_minutes,
        limit=limit,
        include_all_cwds=include_all_cwds,
    )
    observation_inputs = [
        {
            "session_id": str(row["session_id"]),
            "actor": actor,
            "phase_id": phase_id,
            "family_id": family_id,
            "started_at": row.get("created_at"),
            "last_signal_at": row.get("updated_at"),
            "title": row.get("title"),
            "source": "codex_state_5.sqlite",
            "metadata": {
                "codex_thread_id": row.get("codex_thread_id"),
                "agent_role": row.get("agent_role"),
                "reasoning_effort": row.get("reasoning_effort"),
                "tokens_used": row.get("tokens_used"),
                "git_branch": row.get("git_branch"),
                "model": row.get("model"),
                "cwd": row.get("cwd"),
                "rollout_path": row.get("rollout_path"),
                "rollout_activity": row.get("rollout_activity"),
            },
        }
        for row in candidates
    ]
    observations: List[Dict[str, Any]] = []
    if not dry_run:
        observations = work_ledger_runtime.observe_external_sessions(
            REPO_ROOT,
            observations=observation_inputs,
        )
    return {
        "schema": "work_ledger_codex_session_import_v1",
        "dry_run": bool(dry_run),
        "db_path": str(db_path),
        "since_minutes": float(since_minutes),
        "candidate_count": len(candidates),
        "imported_count": len(observations),
        "candidates": candidates,
        "observation_inputs": observation_inputs,
        "observations": observations,
    }


def cmd_session_import_codex(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).expanduser() if args.db_path else CODEX_STATE_DB
    return _print(
        _import_codex_sessions(
            db_path=db_path,
            actor=args.actor,
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.limit,
            include_all_cwds=bool(args.include_all_cwds),
            dry_run=bool(args.dry_run),
        )
    )


def _iso_utc_from_mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _safe_load_json_file(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _claude_todo_counts() -> Dict[str, int]:
    total = 0
    nonempty = 0
    if not CLAUDE_TODOS_DIR.exists():
        return {"todo_files_total": 0, "todo_files_nonempty": 0}
    for path in CLAUDE_TODOS_DIR.glob("*.json"):
        total += 1
        try:
            if path.stat().st_size > 5:
                nonempty += 1
        except OSError:
            continue
    return {"todo_files_total": total, "todo_files_nonempty": nonempty}


def _claude_ide_candidates(
    *,
    since_minutes: float,
    limit: int,
    include_all_workspaces: bool,
) -> List[Dict[str, Any]]:
    if not CLAUDE_IDE_DIR.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=float(since_minutes or 0))
    rows: List[Dict[str, Any]] = []
    for path in sorted(CLAUDE_IDE_DIR.glob("*.lock")):
        mtime_iso = _iso_utc_from_mtime(path)
        mtime = datetime.fromisoformat(mtime_iso) if mtime_iso else None
        if mtime is not None and since_minutes > 0 and mtime < cutoff:
            continue
        payload = _safe_load_json_file(path)
        workspace_folders = [
            str(item)
            for item in payload.get("workspaceFolders") or []
            if str(item or "").strip()
        ]
        repo_resolved = REPO_ROOT.resolve(strict=False)
        in_repo_scope = False
        for folder in workspace_folders:
            try:
                folder_resolved = Path(folder).expanduser().resolve(strict=False)
                in_repo_scope = in_repo_scope or (
                    folder_resolved == repo_resolved
                    or repo_resolved in folder_resolved.parents
                    or folder_resolved in repo_resolved.parents
                )
            except OSError:
                in_repo_scope = in_repo_scope or folder == str(REPO_ROOT) or folder.startswith(f"{REPO_ROOT}/")
        if not include_all_workspaces and workspace_folders and not in_repo_scope:
            continue
        pid = str(payload.get("pid") or path.stem).strip()
        rows.append(
            {
                "session_id": f"claude_ide:{pid}",
                "pid": pid,
                "lock_path": str(path),
                "last_activity_at": mtime_iso,
                "title": f"Claude IDE lock {pid}",
                "workspace_folders": workspace_folders,
                "in_repo_scope": in_repo_scope,
                "ide_name": str(payload.get("ideName") or ""),
                "transport": str(payload.get("transport") or ""),
                "running_in_windows": bool(payload.get("runningInWindows")),
            }
        )
    rows.sort(key=lambda row: str(row.get("last_activity_at") or ""), reverse=True)
    return rows[: max(1, int(limit or 1))]


def _import_claude_ide_sessions(
    *,
    phase_id: str | None,
    family_id: str | None,
    since_minutes: float,
    limit: int,
    include_all_workspaces: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    candidates = _claude_ide_candidates(
        since_minutes=since_minutes,
        limit=limit,
        include_all_workspaces=include_all_workspaces,
    )
    todo_counts = _claude_todo_counts()
    observation_inputs = [
        {
            "session_id": str(row["session_id"]),
            "actor": "claude_code",
            "phase_id": phase_id,
            "family_id": family_id,
            "started_at": row.get("last_activity_at"),
            "last_signal_at": row.get("last_activity_at"),
            "title": row.get("title"),
            "source": "claude_ide_lock",
            "metadata": {
                "pid": row.get("pid"),
                "lock_path": row.get("lock_path"),
                "workspace_folders": row.get("workspace_folders"),
                "in_repo_scope": row.get("in_repo_scope"),
                "ide_name": row.get("ide_name"),
                "transport": row.get("transport"),
                "running_in_windows": row.get("running_in_windows"),
                **todo_counts,
            },
        }
        for row in candidates
    ]
    observations: List[Dict[str, Any]] = []
    if not dry_run:
        observations = work_ledger_runtime.observe_external_sessions(
            REPO_ROOT,
            observations=observation_inputs,
        )
    return {
        "schema": "work_ledger_claude_ide_import_v1",
        "dry_run": bool(dry_run),
        "since_minutes": float(since_minutes),
        "candidate_count": len(candidates),
        "imported_count": len(observations),
        "todo_counts": todo_counts,
        "candidates": candidates,
        "observation_inputs": observation_inputs,
        "observations": observations,
    }


def cmd_session_import_host_surfaces(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).expanduser() if args.db_path else CODEX_STATE_DB
    codex_import = None
    claude_import = None
    if not args.skip_codex:
        codex_import = _import_codex_sessions(
            db_path=db_path,
            actor="codex",
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.limit,
            include_all_cwds=bool(args.include_all_cwds),
            dry_run=bool(args.dry_run),
        )
    if not args.skip_claude:
        claude_import = _import_claude_ide_sessions(
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.limit,
            include_all_workspaces=bool(args.include_all_workspaces),
            dry_run=bool(args.dry_run),
        )
    status_after_imports = work_ledger_runtime.load_runtime_status(REPO_ROOT, rebuild=False)
    cached_overview = (
        status_after_imports.get("cohort_overview")
        if isinstance(status_after_imports.get("cohort_overview"), Mapping)
        else None
    )
    if (
        int(args.overview_limit or 0) == work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT
        and cached_overview is not None
    ):
        overview = dict(cached_overview)
    else:
        overview = work_ledger_runtime.build_session_cohort_overview(
            status_after_imports,
            limit=args.overview_limit,
        )
    signals = list((overview.get("contention") or {}).get("signals") or [])
    if claude_import and int(claude_import.get("candidate_count") or 0) > 1:
        signals.append("multiple_claude_ide_locks")
    return _print(
        {
            "schema": "work_ledger_host_surface_import_v1",
            "dry_run": bool(args.dry_run),
            "since_minutes": float(args.since_minutes),
            "codex_import": codex_import,
            "claude_ide_import": claude_import,
            "coordination": {
                "risk_level": (overview.get("contention") or {}).get("risk_level"),
                "signals": sorted(set(signals)),
                "counts": overview.get("counts") or {},
                "heartbeat_participation": overview.get("heartbeat_participation") or {},
                "recommended_actions": overview.get("recommended_actions") or [],
            },
        }
    )


def _session_slug(value: str | None) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "autonomous").strip()).strip("_")
    return slug.lower() or "autonomous"


def _mint_preflight_session_id(actor: str, slug: str | None) -> str:
    actor_token = _session_slug(actor)
    slug_token = _session_slug(slug)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{actor_token}_{now}_{slug_token}"


def _claim_scope(row: Mapping[str, Any]) -> tuple[str, str]:
    claim = row.get("claim") if isinstance(row.get("claim"), Mapping) else {}
    scope_kind = str(claim.get("scope_kind") or row.get("scope_kind") or "").strip()
    scope_id = str(
        claim.get("scope_id")
        or claim.get("td_id")
        or claim.get("work_item_id")
        or claim.get("path")
        or row.get("scope_id")
        or row.get("td_id")
        or row.get("work_item_id")
        or row.get("path")
        or ""
    ).strip()
    return scope_kind, scope_id


def _claim_closeout_plan(
    session_id: str,
    claims: List[Dict[str, Any]],
    *,
    read_receipt_id: str = "",
    actor: str = "",
    phase_id: str = "",
    family_id: str = "",
) -> Dict[str, Any]:
    progress_commands: List[str] = []
    close_commands: List[str] = []
    alternative_commands: List[Dict[str, Any]] = []
    session_arg = shlex.quote(session_id)
    receipt_arg = shlex.quote(read_receipt_id or "<live_read_receipt_id>")
    actor_arg = shlex.quote(actor or "<actor>")
    phase_arg = shlex.quote(phase_id or "<phase_id>")
    family_arg = shlex.quote(family_id or "<family_id>")
    td_ids: List[str] = []
    work_item_ids: List[str] = []
    path_scopes: List[str] = []
    path_claim_seen = False
    for row in claims:
        if not isinstance(row, Mapping):
            continue
        scope_kind, scope_id = _claim_scope(row)
        if not scope_id:
            continue
        if scope_kind == "td_id" and scope_id not in td_ids:
            td_ids.append(scope_id)
        elif scope_kind == "work_item_id" and scope_id not in work_item_ids:
            work_item_ids.append(scope_id)
        elif scope_kind == "path":
            path_claim_seen = True
            if scope_id not in path_scopes:
                path_scopes.append(scope_id)
    for work_item_id in work_item_ids[:3]:
        progress_commands.append(
            "./repo-python tools/meta/factory/work_ledger.py progress "
            f"--actor {actor_arg} --actor-session-id {session_arg} "
            f"--phase-id {phase_arg} --family-id {family_arg} "
            f"--read-receipt-id {receipt_arg} "
            f"--td-id {shlex.quote(work_item_id)} "
            "--title '<progress-title>' --body-file '<closeout-body.md>'"
        )
    for td_id in td_ids[:3]:
        close_commands.append(
            "./repo-python tools/meta/factory/work_ledger.py close "
            f"--actor {actor_arg} --actor-session-id {session_arg} "
            f"--phase-id {phase_arg} --family-id {family_arg} "
            f"--read-receipt-id {receipt_arg} "
            f"--td-id {shlex.quote(td_id)} "
            "--resolution-kind '<artifact|git_commit|orchestration_event|raw_seed_paragraph|session>' "
            "--resolution-ref '<ref>'"
        )
    append_exempt_command = ""
    append_exempt_commit_command = ""
    if path_claim_seen:
        append_exempt_ref_suffix = ""
        for td_id in td_ids[:3]:
            append_exempt_ref_suffix += f" --append-exempt-td-id {shlex.quote(td_id)}"
        for work_item_id in work_item_ids[:3]:
            append_exempt_ref_suffix += f" --append-exempt-work-item-id {shlex.quote(work_item_id)}"
        append_exempt_command = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-finalize --session-id {session_arg} --action codex-turn-end "
            f"--read-receipt-id {receipt_arg} "
            "--append-exempt-reason '<commit-or-projection-closeout>' "
            "--append-exempt-ref '<commit-or-receipt-ref>'"
            + append_exempt_ref_suffix
        )
        if path_scopes:
            append_exempt_commit_command = (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-finalize --session-id {session_arg} --action codex-turn-end "
                f"--read-receipt-id {receipt_arg} "
                "--append-exempt-reason '<commit-closeout>' "
                "--append-exempt-ref 'commit:<commit-ref>' "
                "--require-post-commit-containment"
            )
            for path_scope in path_scopes:
                append_exempt_commit_command += (
                    f" --post-commit-containment-scope {shlex.quote(path_scope)}"
                )
            append_exempt_commit_command += append_exempt_ref_suffix
    bare_finalize_command = (
        "./repo-python tools/meta/factory/work_ledger.py "
        f"session-finalize --session-id {session_arg} --action codex-turn-end"
    )

    recommended_sequence: List[str] = []
    if progress_commands or close_commands:
        recommended_sequence.extend(progress_commands)
        recommended_sequence.extend(close_commands)
        recommended_sequence.append(bare_finalize_command)
        if append_exempt_command:
            alternative_commands.append(
                {
                    "role": "commit_or_projection_closeout",
                    "command": append_exempt_command,
                    "use_when": (
                        "The touched path work is fully evidenced by a scoped commit, "
                        "Task Ledger receipt, or generated projection settlement instead "
                        "of a Work Ledger progress/close append."
                    ),
                    "finalizes_session": True,
                    "do_not_follow_with_bare_finalize": True,
                }
            )
        if append_exempt_commit_command:
            alternative_commands.append(
                {
                    "role": "commit_closeout_with_post_commit_containment",
                    "command": append_exempt_commit_command,
                    "use_when": (
                        "The durable evidence is a scoped commit for claimed paths; "
                        "the finalizer should prove the commit is contained in current "
                        "HEAD and claimed paths stayed clean before releasing claims."
                    ),
                    "finalizes_session": True,
                    "do_not_follow_with_bare_finalize": True,
                }
            )
    elif append_exempt_command:
        recommended_sequence.append(append_exempt_command)
    else:
        recommended_sequence.append(bare_finalize_command)

    command_roles: List[Dict[str, Any]] = []
    if progress_commands:
        command_roles.append(
            {
                "role": "work_item_progress_before_finalize",
                "commands": progress_commands,
                "finalizes_session": False,
            }
        )
    if close_commands:
        command_roles.append(
            {
                "role": "work_ledger_close_before_finalize",
                "commands": close_commands,
                "finalizes_session": False,
            }
        )
    if append_exempt_command:
        command_roles.append(
            {
                "role": "append_exempt_finalize_for_path_or_projection_closeout",
                "commands": [append_exempt_command],
                "finalizes_session": True,
                "do_not_follow_with_bare_finalize": True,
            }
        )
    if append_exempt_commit_command:
        command_roles.append(
            {
                "role": "commit_finalize_with_post_commit_containment",
                "commands": [append_exempt_commit_command],
                "finalizes_session": True,
                "do_not_follow_with_bare_finalize": True,
            }
        )
    command_roles.append(
        {
            "role": "bare_finalize_after_append_exists",
            "commands": [bare_finalize_command],
            "finalizes_session": True,
            "only_after": "session_had_ledger_append=true or append_exempt=true",
            "will_block_if": "touched_work=true and no Work Ledger append or append-exempt closeout exists",
        }
    )
    return {
        "schema": "work_ledger_closeout_plan_v1",
        "ordering_rule": (
            "Choose one closeout path. If progress/close writes a Work Ledger append, "
            "finish with bare session-finalize. If the durable evidence is commit-only "
            "or projection-only, use the append-exempt session-finalize command as the "
            "finalizer and do not run bare session-finalize afterward."
        ),
        "read_receipt_id": read_receipt_id or "<live_read_receipt_id>",
        "recommended_sequence": recommended_sequence,
        "command_roles": command_roles,
        "alternative_commands": alternative_commands,
        "legacy_flat_commands_policy": (
            "closeout_commands is a compatibility field containing only the recommended "
            "sequence for the detected claims; use closeout_plan for role and ordering details."
        ),
    }


def _claim_closeout_commands(
    session_id: str,
    claims: List[Dict[str, Any]],
    *,
    read_receipt_id: str = "",
    actor: str = "",
    phase_id: str = "",
    family_id: str = "",
) -> List[str]:
    return list(
        _claim_closeout_plan(
            session_id,
            claims,
            read_receipt_id=read_receipt_id,
            actor=actor,
            phase_id=phase_id,
            family_id=family_id,
        )["recommended_sequence"]
    )


def _path_scope_overlaps(left: str, right: str) -> bool:
    left_parts = tuple(part for part in str(left or "").split("/") if part)
    right_parts = tuple(part for part in str(right or "").split("/") if part)
    if not left_parts or not right_parts:
        return False
    if left_parts == right_parts:
        return True
    if len(left_parts) < len(right_parts):
        return right_parts[: len(left_parts)] == left_parts
    return left_parts[: len(right_parts)] == right_parts


def _preflight_requested_paths(paths: List[str]) -> List[str]:
    normalized: List[str] = []
    for path in paths:
        token = _normalize_codex_repo_path(path, REPO_ROOT)
        if token and token not in normalized:
            normalized.append(token)
    return normalized


def _preflight_write_profiles(profile_names: List[str]) -> List[Dict[str, Any]]:
    profiles: List[Dict[str, Any]] = []
    for name in profile_names:
        token = str(name or "").strip()
        if not token:
            continue
        if token not in WRITE_PROFILE_PATHS:
            raise ValueError(f"unknown write profile: {token}")
        paths = list(WRITE_PROFILE_PATHS[token])
        source_input_paths = list(WRITE_PROFILE_SOURCE_INPUT_PATHS.get(token, ()))
        profiles.append(
            {
                "profile": token,
                "paths": paths,
                "path_count": len(paths),
                "source_input_paths": source_input_paths,
                "source_input_path_count": len(source_input_paths),
                "source_input_claim_policy": (
                    "must_be_clean_committed_or_owned_before_landing_outputs"
                    if source_input_paths
                    else "not_declared_for_profile"
                ),
            }
        )
    return profiles


def _preflight_source_input_paths(profiles: List[Dict[str, Any]]) -> List[str]:
    input_paths: List[str] = []
    for profile in profiles:
        for path in profile.get("source_input_paths") or []:
            token = _normalize_codex_repo_path(str(path), REPO_ROOT)
            if token and token not in input_paths:
                input_paths.append(token)
    return input_paths


def _preflight_claim_paths(paths: List[str], profiles: List[Dict[str, Any]]) -> List[str]:
    claimed_paths: List[str] = []
    for path in paths:
        token = _normalize_codex_repo_path(path, REPO_ROOT)
        if token and token not in claimed_paths:
            claimed_paths.append(token)
    for profile in profiles:
        for path in profile.get("paths") or []:
            token = _normalize_codex_repo_path(path, REPO_ROOT)
            if token and token not in claimed_paths:
                claimed_paths.append(token)
    return claimed_paths


def _observed_path_overlaps(
    *,
    requested_paths: List[str],
    codex_import: Dict[str, Any] | None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    if not requested_paths or not isinstance(codex_import, dict):
        return []
    rows: List[Dict[str, Any]] = []
    imported_rows = codex_import.get("candidates") or codex_import.get("observations") or []
    for row in imported_rows:
        if not isinstance(row, dict):
            continue
        metadata = row.get("external_metadata") if isinstance(row.get("external_metadata"), dict) else {}
        activity = row.get("rollout_activity") or metadata.get("rollout_activity")
        if not isinstance(activity, dict):
            continue
        mutation_paths = [
            path
            for path in activity.get("recent_mutation_paths") or []
            if isinstance(path, str)
        ]
        referenced_paths = [
            path
            for path in activity.get("recent_referenced_paths") or []
            if isinstance(path, str)
        ]
        for requested in requested_paths:
            mutation_overlaps = [
                path for path in mutation_paths if _path_scope_overlaps(requested, path)
            ]
            reference_overlaps = [
                path
                for path in referenced_paths
                if _path_scope_overlaps(requested, path) and path not in mutation_overlaps
            ]
            if not mutation_overlaps and not reference_overlaps:
                continue
            overlap_row = {
                "requested_path": requested,
                "session_id": row.get("session_id"),
                "updated_at": row.get("updated_at") or row.get("last_activity_at"),
                "mutation_paths": mutation_overlaps[:8],
                "referenced_paths": reference_overlaps[:8],
                "recent_commands": list(activity.get("recent_commands") or [])[:3],
            }
            overlap_row.update(_session_title_handle_fields(row))
            rows.append(overlap_row)
            if len(rows) >= limit:
                return rows
    return rows


def _observed_shared_worktree_git_risks(
    *,
    codex_import: Dict[str, Any] | None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    if not isinstance(codex_import, dict):
        return []
    rows: List[Dict[str, Any]] = []
    imported_rows = codex_import.get("candidates") or codex_import.get("observations") or []
    for row in imported_rows:
        if not isinstance(row, dict):
            continue
        metadata = row.get("external_metadata") if isinstance(row.get("external_metadata"), dict) else {}
        activity = row.get("rollout_activity") or metadata.get("rollout_activity")
        if not isinstance(activity, dict):
            continue
        for command in activity.get("recent_commands") or []:
            risks = shared_worktree_guard.detect_git_risks_in_text(str(command or ""))
            if not risks:
                continue
            for risk in risks:
                risk_row = dict(risk)
                risk_row.update(
                    {
                        "session_id": row.get("session_id"),
                        "updated_at": row.get("updated_at") or row.get("last_activity_at"),
                    }
                )
                risk_row.update(_session_title_handle_fields(row))
                rows.append(risk_row)
                if len(rows) >= limit:
                    return rows
            break
    return rows


def _compact_preflight_claim(result: Dict[str, Any]) -> Dict[str, Any]:
    claim = result.get("claim") if isinstance(result.get("claim"), dict) else {}
    collisions = result.get("collisions") if isinstance(result.get("collisions"), list) else []
    return {
        "status": result.get("status"),
        "scope_kind": claim.get("scope_kind") or result.get("scope_kind"),
        "scope_id": claim.get("scope_id") or result.get("scope_id"),
        "claim_id": claim.get("claim_id"),
        "td_id": claim.get("td_id") or result.get("td_id") or "",
        "path": claim.get("path") or result.get("path") or "",
        "work_item_id": claim.get("work_item_id") or result.get("work_item_id") or "",
        "leased_until": claim.get("leased_until"),
        "collision_count": len(collisions),
        "collision_sessions": [
            {
                "session_id": row.get("session_id"),
                "actor": row.get("actor"),
                "scope_kind": (row.get("claim") or {}).get("scope_kind")
                if isinstance(row.get("claim"), dict)
                else None,
                "scope_id": (row.get("claim") or {}).get("scope_id")
                if isinstance(row.get("claim"), dict)
                else None,
            }
            for row in collisions
            if isinstance(row, dict)
        ],
    }


def _compact_preflight_overview(overview: Dict[str, Any]) -> Dict[str, Any]:
    contention = overview.get("contention") if isinstance(overview.get("contention"), dict) else {}
    counts = overview.get("counts") if isinstance(overview.get("counts"), dict) else {}
    count_keys = (
        "sessions_total",
        "effective_active_sessions",
        "orphaned_active_sessions",
        "stale_sessions",
        "active_claims",
        "claim_collisions",
        "unclaimed_touched_sessions",
    )
    return {
        "risk_level": contention.get("risk_level"),
        "signals": list(contention.get("signals") or []),
        "counts": {key: counts.get(key, 0) for key in count_keys},
        "heartbeat_participation": _compact_preflight_heartbeat_participation(
            overview.get("heartbeat_participation")
            if isinstance(overview.get("heartbeat_participation"), Mapping)
            else {}
        ),
        "recommended_actions": list(overview.get("recommended_actions") or []),
    }


def _compact_preflight_heartbeat_participation(
    heartbeat: Mapping[str, Any],
    *,
    preview_limit: int = 3,
) -> Dict[str, Any]:
    explicit_ids = [
        str(value)
        for value in list(heartbeat.get("explicit_session_ids") or [])
        if str(value or "").strip()
    ]
    projected_ids = [
        str(value)
        for value in list(heartbeat.get("projected_unknown_session_ids") or [])
        if str(value or "").strip()
    ]
    safe_limit = max(0, int(preview_limit))
    compact: Dict[str, Any] = {
        "schema": heartbeat.get("schema"),
        "scope": heartbeat.get("scope"),
        "status": heartbeat.get("status"),
        "effective_active_sessions": heartbeat.get("effective_active_sessions"),
        "explicit_current_pass_count": heartbeat.get("explicit_current_pass_count"),
        "projected_unknown_count": heartbeat.get("projected_unknown_count"),
        "missing_current_pass_count": heartbeat.get("missing_current_pass_count"),
        "participation_ratio": heartbeat.get("participation_ratio"),
        "source_counts": dict(heartbeat.get("source_counts") or {}),
        "freshness_counts": dict(heartbeat.get("freshness_counts") or {}),
        "explicit_session_count": len(explicit_ids),
        "explicit_session_ids_preview": explicit_ids[:safe_limit],
        "explicit_session_ids_omitted": max(0, len(explicit_ids) - safe_limit),
        "projected_unknown_session_count": len(projected_ids),
        "projected_unknown_session_ids_preview": projected_ids[:safe_limit],
        "projected_unknown_session_ids_omitted": max(0, len(projected_ids) - safe_limit),
        "first_contact": heartbeat.get("first_contact") or {},
        "policy": heartbeat.get("policy") or {},
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }
    return {
        key: value
        for key, value in compact.items()
        if value not in (None, "", [], {})
    }


def _compact_closeout_plan(plan: Mapping[str, Any]) -> Dict[str, Any]:
    recommended_sequence = [
        str(command)
        for command in list(plan.get("recommended_sequence") or [])
        if str(command or "").strip()
    ]
    command_roles = [
        row for row in list(plan.get("command_roles") or []) if isinstance(row, Mapping)
    ]
    alternatives = [
        row for row in list(plan.get("alternative_commands") or []) if isinstance(row, Mapping)
    ]
    compact_roles: List[Dict[str, Any]] = []
    for row in command_roles:
        commands = [
            str(command)
            for command in list(row.get("commands") or [])
            if str(command or "").strip()
        ]
        compact: Dict[str, Any] = {
            "role": row.get("role"),
            "command_count": len(commands),
            "commands_omitted": len(commands),
            "finalizes_session": bool(row.get("finalizes_session")),
        }
        for key in ("do_not_follow_with_bare_finalize", "only_after", "will_block_if"):
            if row.get(key) not in (None, "", [], {}):
                compact[key] = row.get(key)
        compact_roles.append({key: value for key, value in compact.items() if value not in (None, "", [], {})})
    compact_alternatives: List[Dict[str, Any]] = []
    for row in alternatives:
        compact = {
            "role": row.get("role"),
            "command_omitted": bool(row.get("command")),
            "use_when": row.get("use_when"),
            "finalizes_session": bool(row.get("finalizes_session")),
            "do_not_follow_with_bare_finalize": bool(row.get("do_not_follow_with_bare_finalize")),
        }
        compact_alternatives.append(
            {key: value for key, value in compact.items() if value not in (None, "", [], {})}
        )
    return {
        "schema": plan.get("schema") or "work_ledger_closeout_plan_v1",
        "mode": "compact",
        "ordering_rule": plan.get("ordering_rule"),
        "read_receipt_id": plan.get("read_receipt_id"),
        "recommended_sequence_count": len(recommended_sequence),
        "recommended_sequence_ref": "closeout_commands",
        "command_roles": compact_roles,
        "alternative_command_count": len(alternatives),
        "alternative_commands": compact_alternatives,
        "commands_omitted": sum(int(row.get("commands_omitted") or 0) for row in compact_roles)
        + sum(1 for row in alternatives if row.get("command")),
        "legacy_flat_commands_policy": plan.get("legacy_flat_commands_policy"),
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }


def _compact_closeout_command_preview(commands: Sequence[Any], *, limit: int = 2) -> Dict[str, Any]:
    command_rows = [
        str(command)
        for command in list(commands or [])
        if str(command or "").strip()
    ]
    safe_limit = max(0, int(limit))
    if len(command_rows) <= safe_limit:
        preview = command_rows
    elif safe_limit <= 1:
        preview = command_rows[-safe_limit:] if safe_limit else []
    else:
        preview = [command_rows[0], command_rows[-1]]
    return {
        "commands": preview,
        "total": len(command_rows),
        "returned": len(preview),
        "omitted": max(0, len(command_rows) - len(preview)),
        "selection": "all" if len(command_rows) == len(preview) else "first_step_and_finalizer",
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }


def _compact_preflight_work_admission(admission: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(admission, Mapping):
        return {}
    compact: Dict[str, Any] = {
        "schema": admission.get("schema"),
        "status": admission.get("status"),
        "result": admission.get("result"),
        "allow": admission.get("allow"),
        "work_class": admission.get("work_class"),
        "host_pressure_workload_class": admission.get("host_pressure_workload_class"),
        "policy": admission.get("policy"),
        "heavy": admission.get("heavy"),
        "host_pressure_status": admission.get("host_pressure_status"),
        "host_pressure_decision": admission.get("host_pressure_decision"),
        "host_pressure_reason": admission.get("host_pressure_reason"),
        "coverage_closure_status": admission.get("coverage_closure_status"),
        "coverage_blocking_gap_count": admission.get("coverage_blocking_gap_count"),
        "new_heavy_work_launched": admission.get("new_heavy_work_launched"),
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }
    if admission.get("allow") is False or admission.get("result") != "allow":
        compact["override_hint"] = admission.get("override_hint")
    host = admission.get("host_pressure_admission")
    if isinstance(host, Mapping):
        compact["host_pressure_admission"] = {
            key: host.get(key)
            for key in (
                "schema",
                "status",
                "requested_workload_class",
                "decision",
                "should_block_run",
            )
            if host.get(key) not in (None, "", [], {})
        }
    return {
        key: value
        for key, value in compact.items()
        if value is not None and value not in ("", [], {})
    }


def _compact_preflight_resource_pressure(packet: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(packet, Mapping):
        return {}
    return resource_pressure.compact_host_resource_pressure_packet(packet)


def _compact_preflight_heartbeat_contract(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(contract, Mapping):
        return {}
    when_rows = [
        str(value)
        for value in list(contract.get("when") or [])
        if str(value or "").strip()
    ]
    compact = {
        "schema": contract.get("schema"),
        "status": contract.get("status"),
        "when_count": len(when_rows),
        "when_preview": when_rows[:4],
        "command_template_ref": "session-heartbeat --help",
        "boundary_ref": "public_runtime_coordination_no_transcript_summary",
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }
    return {
        key: value
        for key, value in compact.items()
        if value is not None and value not in ("", [], {})
    }


def _compact_preflight_closeout_rule(rule: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(rule, Mapping):
        return {}
    compact = {
        "schema": rule.get("schema"),
        "status": rule.get("status"),
        "read_receipt_id": rule.get("read_receipt_id"),
        "rule_ref": "append_or_append_exempt_before_finalize",
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }
    return {
        key: value
        for key, value in compact.items()
        if value is not None and value not in ("", [], {})
    }


def _compact_observed_path_overlap(row: Mapping[str, Any]) -> Dict[str, Any]:
    mutation_paths = [path for path in list(row.get("mutation_paths") or []) if isinstance(path, str)]
    referenced_paths = [path for path in list(row.get("referenced_paths") or []) if isinstance(path, str)]
    recent_commands = [
        _compact_handle_preview(_compact_codex_command(command), limit=120)
        for command in list(row.get("recent_commands") or [])
        if str(command or "").strip()
    ]
    compact: Dict[str, Any] = {
        "requested_path": row.get("requested_path"),
        "session_id": row.get("session_id"),
        "updated_at": row.get("updated_at"),
        "mutation_paths": mutation_paths[:4],
        "mutation_path_count": len(mutation_paths),
        "referenced_paths": referenced_paths[:4],
        "referenced_path_count": len(referenced_paths),
        "recent_commands": recent_commands[:1],
        "recent_command_count": len(recent_commands),
        "title_bytes": row.get("title_bytes"),
        "title_hash": row.get("title_hash"),
        "title_kind": row.get("title_kind"),
        "title_full_omitted": row.get("title_full_omitted"),
    }
    if row.get("title_full_omitted"):
        compact["title_preview"] = row.get("title_preview")
        compact["title_ref"] = row.get("title_ref")
        compact["title_drilldown"] = row.get("title_drilldown")
        if isinstance(row.get("omission_receipt"), Mapping):
            receipt = row.get("omission_receipt") or {}
            compact["omission_receipt"] = {
                key: receipt.get(key)
                for key in ("omitted", "drilldown", "source_ref")
                if receipt.get(key) not in (None, "", [], {})
            }
    else:
        compact["title_preview"] = row.get("title_preview")
    return {
        key: value
        for key, value in compact.items()
        if value not in (None, "", [], {})
    }


def _compact_shared_worktree_git_risk(row: Mapping[str, Any]) -> Dict[str, Any]:
    command = str(row.get("command") or "")
    command_bytes = len(command.encode("utf-8"))
    compact: Dict[str, Any] = {
        "schema": row.get("schema"),
        "risk": row.get("risk"),
        "verb": row.get("verb"),
        "severity": row.get("severity"),
        "advice": row.get("advice"),
        "session_id": row.get("session_id"),
        "updated_at": row.get("updated_at"),
        "command": _compact_handle_preview(command, limit=160),
        "command_bytes": command_bytes,
        "command_hash": f"sha256:{hashlib.sha256(command.encode('utf-8')).hexdigest()}",
        "command_full_omitted": command_bytes > 160,
    }
    title_fields = _session_title_handle_fields(row)
    for key in (
        "title_preview",
        "title_bytes",
        "title_hash",
        "title_kind",
        "title_full_omitted",
        "title_ref",
        "title_drilldown",
        "omission_receipt",
    ):
        if title_fields.get(key) not in (None, "", [], {}):
            compact[key] = title_fields.get(key)
    return {
        key: value
        for key, value in compact.items()
        if value not in (None, "", [], {})
    }


def _compact_preflight_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    codex_import = payload.get("codex_import")
    import_summary = None
    if isinstance(codex_import, dict):
        import_summary = {
            "candidate_count": codex_import.get("candidate_count", 0),
            "imported_count": codex_import.get("imported_count", 0),
            "since_minutes": codex_import.get("since_minutes"),
            "db_path": codex_import.get("db_path"),
        }
    claude_import = payload.get("claude_ide_import")
    claude_summary = None
    if isinstance(claude_import, dict):
        claude_summary = {
            "candidate_count": claude_import.get("candidate_count", 0),
            "imported_count": claude_import.get("imported_count", 0),
            "since_minutes": claude_import.get("since_minutes"),
            "todo_counts": claude_import.get("todo_counts") or {},
        }
    claims = payload.get("claims") if isinstance(payload.get("claims"), list) else []
    claim_rows = [_compact_preflight_claim(row) for row in claims if isinstance(row, dict)]
    status_counts = Counter(str(row.get("status") or "unknown") for row in claim_rows)
    payload_claim_summary = (
        payload.get("claim_summary") if isinstance(payload.get("claim_summary"), Mapping) else None
    )
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    overlap_rows = [
        row for row in list(payload.get("observed_path_overlaps") or []) if isinstance(row, Mapping)
    ]
    compact_overlap_rows = [
        _compact_observed_path_overlap(row)
        for row in overlap_rows[:COMPACT_OBSERVED_PATH_OVERLAP_LIMIT]
    ]
    overlap_summary = {
        "returned": len(compact_overlap_rows),
        "total": len(overlap_rows),
        "omitted": max(0, len(overlap_rows) - len(compact_overlap_rows)),
        "row_limit": COMPACT_OBSERVED_PATH_OVERLAP_LIMIT,
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }
    claim_summary = {
        "requested": len(claim_rows),
        "claimed": (
            status_counts.get("claimed", 0)
            + status_counts.get("extended", 0)
            + status_counts.get("already_claimed", 0)
        ),
        "claimed_with_collision": status_counts.get("claimed_with_collision", 0),
        "refused": status_counts.get("refused", 0),
    }
    if status_counts.get("extended", 0):
        claim_summary["extended"] = status_counts.get("extended", 0)
    if status_counts.get("already_claimed", 0):
        claim_summary["already_claimed"] = status_counts.get("already_claimed", 0)
    closeout_commands = list(payload.get("closeout_commands") or [])
    compact_closeout_commands = _compact_closeout_command_preview(closeout_commands)
    return {
        "schema": payload.get("schema"),
        "mode": "compact",
        "status": payload.get("status"),
        "session_id": payload.get("session_id"),
        "actor": payload.get("actor"),
        "phase_id": payload.get("phase_id"),
        "family_id": payload.get("family_id"),
        "read_receipt_id": payload.get("read_receipt_id"),
        "codex_import_summary": import_summary,
        "claude_ide_import_summary": claude_summary,
        "claim_summary": dict(payload_claim_summary)
        if payload_claim_summary
        else claim_summary,
        "claims": claim_rows,
        "write_profiles": payload.get("write_profiles") or [],
        "work_creation_classification": payload.get("work_creation_classification") or {},
        "host_resource_pressure": _compact_preflight_resource_pressure(
            payload.get("host_resource_pressure")
            if isinstance(payload.get("host_resource_pressure"), Mapping)
            else {}
        ),
        "work_admission": _compact_preflight_work_admission(
            payload.get("work_admission") if isinstance(payload.get("work_admission"), Mapping) else {}
        ),
        "observed_path_overlaps": compact_overlap_rows,
        "observed_path_overlap_summary": overlap_summary,
        "shared_worktree_git_risks": [
            _compact_shared_worktree_git_risk(row)
            for row in list(payload.get("shared_worktree_git_risks") or [])
            if isinstance(row, Mapping)
        ],
        "overview_summary": _compact_preflight_overview(overview),
        "initial_heartbeat": payload.get("initial_heartbeat") or {},
        "heartbeat_participation_contract": _compact_preflight_heartbeat_contract(
            payload.get("heartbeat_participation_contract")
            if isinstance(payload.get("heartbeat_participation_contract"), Mapping)
            else {}
        ),
        "closeout_rule": _compact_preflight_closeout_rule(
            payload.get("closeout_rule") if isinstance(payload.get("closeout_rule"), Mapping) else {}
        ),
        "closeout_plan": _compact_closeout_plan(
            payload.get("closeout_plan") if isinstance(payload.get("closeout_plan"), Mapping) else {}
        ),
        "closeout_commands": compact_closeout_commands["commands"],
        "closeout_command_summary": {
            key: value
            for key, value in compact_closeout_commands.items()
            if key != "commands" and value not in (None, "", [], {})
        },
        "full_payload_hint": (
            "rerun with --full for expanded bounded diagnostics; add --raw-full only "
            "when unbounded bootstrap/import/cohort internals are required"
        ),
    }


def _bounded_import_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    observations = [row for row in list(payload.get("observations") or []) if isinstance(row, Mapping)]
    candidates = [row for row in list(payload.get("candidates") or []) if isinstance(row, Mapping)]
    return {
        "schema": payload.get("schema") or "codex_import_summary_v0",
        "mode": "bounded_full",
        "candidate_count": payload.get("candidate_count", len(candidates)),
        "imported_count": payload.get("imported_count", len(observations)),
        "since_minutes": payload.get("since_minutes"),
        "db_path": payload.get("db_path"),
        "observation_count": len(observations),
        "candidate_rows_omitted": len(candidates),
        "observation_rows_omitted": len(observations),
        "omission_receipt": {
            "omitted": ["candidates", "observations", "observation_inputs"],
            "reason": "Recent external thread rows can carry long prompts and rollout metadata.",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--full --raw-full <same args>"
            ),
        },
    }


def _bounded_bootstrap_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    external_results = [
        row for row in list(payload.get("external_observations") or []) if isinstance(row, Mapping)
    ]
    compact = {
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "session_id": payload.get("session_id"),
        "actor": payload.get("actor"),
        "phase_id": payload.get("phase_id"),
        "family_id": payload.get("family_id"),
        "read_receipt_id": payload.get("read_receipt_id"),
        "claim_count": len(list(payload.get("claims") or [])),
        "external_observation_count": len(external_results),
        "pass_heartbeat": payload.get("pass_heartbeat") or {},
        "cohort_overview_summary": _compact_preflight_overview(
            payload.get("cohort_overview") if isinstance(payload.get("cohort_overview"), dict) else {}
        ),
        "omission_receipt": {
            "omitted": ["claims", "external_observations", "cohort_overview"],
            "reason": "Expanded preflight keeps owner diagnostics bounded; raw bootstrap remains a drilldown.",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--full --raw-full <same args>"
            ),
        },
    }
    return {key: value for key, value in compact.items() if value not in (None, "", [], {})}


def _bounded_full_preflight_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    bounded = dict(payload)
    bounded["mode"] = "full"
    bounded["full_payload_mode"] = "bounded"
    bounded["raw_full_payload_hint"] = (
        "./repo-python tools/meta/factory/work_ledger.py session-preflight "
        "--full --raw-full <same args>"
    )
    bounded["codex_import"] = _bounded_import_payload(payload.get("codex_import"))
    bounded["claude_ide_import"] = _bounded_import_payload(payload.get("claude_ide_import"))
    bounded["bootstrap"] = _bounded_bootstrap_payload(payload.get("bootstrap"))
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    bounded["overview"] = {
        "schema": overview.get("schema") or "work_ledger_session_cohort_overview_v1",
        "mode": "bounded_full",
        **_compact_preflight_overview(overview),
        "omission_receipt": {
            "omitted": ["sessions", "claim rows", "contention detail beyond summary"],
            "reason": "Cohort internals dominate session-preflight --full output in busy repos.",
            "drilldown": bounded["raw_full_payload_hint"],
        },
    }
    overlap_rows = [
        row for row in list(payload.get("observed_path_overlaps") or []) if isinstance(row, Mapping)
    ]
    bounded["observed_path_overlaps"] = [
        _compact_observed_path_overlap(row)
        for row in overlap_rows[:BOUNDED_FULL_OBSERVED_PATH_OVERLAP_LIMIT]
    ]
    bounded["observed_path_overlap_summary"] = {
        "returned": len(bounded["observed_path_overlaps"]),
        "total": len(overlap_rows),
        "omitted": max(0, len(overlap_rows) - len(bounded["observed_path_overlaps"])),
        "row_limit": BOUNDED_FULL_OBSERVED_PATH_OVERLAP_LIMIT,
        "raw_full_payload_drilldown": bounded["raw_full_payload_hint"],
    }
    bounded["shared_worktree_git_risks"] = [
        _compact_shared_worktree_git_risk(row)
        for row in list(payload.get("shared_worktree_git_risks") or [])
        if isinstance(row, Mapping)
    ]
    return bounded


def _active_claim_collisions_for_paths(paths: List[str], *, session_id: str | None = None) -> List[Dict[str, Any]]:
    status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    return work_ledger_runtime.active_claim_collisions_for_paths(
        REPO_ROOT,
        paths,
        status=status,
        session_id=session_id,
    )


def cmd_mutation_check(args: argparse.Namespace) -> int:
    write_profiles = _preflight_write_profiles(list(getattr(args, "write_profile", []) or []))
    paths = _preflight_claim_paths(list(args.path or []), write_profiles)
    collisions = _active_claim_collisions_for_paths(paths, session_id=args.session_id)
    source_input_paths = _preflight_source_input_paths(write_profiles)
    source_input_collisions = _active_claim_collisions_for_paths(
        source_input_paths,
        session_id=args.session_id,
    )
    all_collision_count = len(collisions) + len(source_input_collisions)
    status = (
        "blocked"
        if all_collision_count and args.require_exclusive
        else ("watch" if all_collision_count else "clear")
    )
    contention_envelope = work_ledger_runtime.build_shared_substrate_contention_envelope(
        requested_paths=paths,
        collisions=collisions,
        requester_session_id=args.session_id,
        require_exclusive=bool(args.require_exclusive),
    )
    recommended_actions = []
    if status == "clear" and not args.session_id:
        recommended_actions.append(
            "Run session-preflight with the same --path/--write-profile and claim the work before mutation."
        )
    if collisions:
        recommended_actions.append(
            "Use contention_envelope.owner_sessions[].read_full_session_command or coordination_brief_command before reporting the blocker."
        )
    if source_input_collisions:
        recommended_actions.append(
            "Source-coupled write profile inputs are actively claimed; wait, coordinate, or rebuild from a clean committed snapshot before landing generated outputs."
        )
    payload = {
        "schema": "work_ledger_mutation_check_v1",
        "status": status,
        "require_exclusive": bool(args.require_exclusive),
        "write_profiles": write_profiles,
        "paths": paths,
        "collision_count": len(collisions),
        "collisions": collisions,
        "source_input_paths": source_input_paths,
        "source_input_collision_count": len(source_input_collisions),
        "source_input_collisions": source_input_collisions,
        "source_input_claim_policy": (
            "must_be_clean_committed_or_owned_before_landing_outputs"
            if source_input_paths
            else "not_declared_for_selected_profiles"
        ),
        "contention_envelope": contention_envelope,
        "recommended_actions": recommended_actions,
    }
    _print(payload)
    return 2 if status == "blocked" else 0


def _current_tool_server_pressure_inventory_summary() -> Dict[str, Any] | None:
    try:
        from tools.meta.control import orphan_reaper

        inventory = orphan_reaper.build_tool_server_pressure_inventory()
    except Exception:
        return None
    summary = inventory.get("summary")
    return dict(summary) if isinstance(summary, dict) else None


def cmd_helper_lease_admission(args: argparse.Namespace) -> int:
    inventory_summary = _current_tool_server_pressure_inventory_summary()
    decision = work_admission.build_helper_lease_admission_decision(
        REPO_ROOT,
        lease_kind=args.lease_kind,
        policy=getattr(args, "host_pressure_policy", None) or "auto",
        request_id=getattr(args, "request_id", None),
        requested_by=getattr(args, "requested_by", None),
        owner_status=getattr(args, "owner_status", None),
        current_lease_count=getattr(args, "current_lease_count", None),
        inventory_summary=inventory_summary,
    )
    _print(decision)
    return work_admission.ADMISSION_TEMPFAIL if not bool(decision.get("allow", True)) else 0


def _json_mapping_cli_arg(value: Any) -> Dict[str, Any]:
    decoded = _json_loads_maybe(value)
    return dict(decoded) if isinstance(decoded, Mapping) else {}


def cmd_dev_resource_admission(args: argparse.Namespace) -> int:
    existing_leases = [
        _json_mapping_cli_arg(raw)
        for raw in list(getattr(args, "existing_lease_json", []) or [])
    ]
    decision = work_admission.build_dev_resource_lease_decision(
        REPO_ROOT,
        resource_kind=args.resource_kind,
        fingerprint=_json_mapping_cli_arg(getattr(args, "fingerprint_json", None)),
        existing_leases=existing_leases,
        policy=getattr(args, "host_pressure_policy", None) or "auto",
        request_id=getattr(args, "request_id", None),
        requested_by=getattr(args, "requested_by", None),
        user_facing=bool(getattr(args, "user_facing", False)),
        exclusive_required=bool(getattr(args, "exclusive_required", False)),
        unsafe_host_or_proxy=bool(getattr(args, "unsafe_host_or_proxy", False)),
        host_pressure_packet=_current_host_pressure_packet(workload_class="test_build"),
    )
    _print(decision)
    return work_admission.ADMISSION_TEMPFAIL if not bool(decision.get("allow", True)) else 0


def cmd_concurrency_pathology_index(args: argparse.Namespace) -> int:
    from system.lib import concurrency_pathology

    host_pressure_surface = {} if getattr(args, "skip_host_pressure", False) else None
    payload = concurrency_pathology.build_concurrency_pathology_index(
        REPO_ROOT,
        host_pressure_surface=host_pressure_surface,
    )
    if getattr(args, "families", None):
        families = {str(item).strip() for item in args.families if str(item).strip()}
        rows = [row for row in payload.get("rows", []) if str(row.get("family") or "") in families]
        payload = dict(payload)
        payload["rows"] = rows
        payload["summary"] = dict(payload.get("summary") or {})
        payload["summary"]["row_count"] = len(rows)
        payload["summary"]["filtered_families"] = sorted(families)
    if getattr(args, "write", False):
        payload = {
            **payload,
            "write_receipt": concurrency_pathology.write_concurrency_pathology_index(
                REPO_ROOT,
                payload,
            ),
        }
    _print(payload)
    return 2 if payload.get("rows") else 0


def cmd_exact_copy_settlement_item(args: argparse.Namespace) -> int:
    from system.lib import concurrency_pathology

    item = concurrency_pathology.build_exact_copy_settlement_item(
        REPO_ROOT,
        source_path=args.source_path,
        target_path=args.target_path,
        active_claim_owner=getattr(args, "active_claim_owner", None),
        dependency_release_condition=getattr(args, "dependency_release_condition", None),
        dry_run_repair_command=getattr(args, "dry_run_repair_command", None),
        settlement_group_id=getattr(args, "settlement_group_id", None),
    )
    _print(item)
    return 0 if item.get("status") == "digests_match" else 2


def _current_host_pressure_packet(*, workload_class: str = "mixed_realistic") -> Dict[str, Any]:
    try:
        from system.lib.agent_observability import AgentTraceStore
        from system.lib.host_pressure import build_progress_pressure_packet_from_store

        store = AgentTraceStore(REPO_ROOT, max_history=500)
        return build_progress_pressure_packet_from_store(
            store,
            REPO_ROOT,
            event_limit=500,
            include_processes=True,
            requested_workload_class=workload_class,
        )
    except Exception as exc:  # pragma: no cover - host adapters must degrade.
        return {
            "summary": {
                "bottleneck_class": "unknown",
                "pressure_index": 0,
                "progress_per_pressure": 0,
            },
            "source_error": {
                "error_class": type(exc).__name__,
                "message": str(exc),
            },
        }


def _host_pressure_relief_summary(packet: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(packet, Mapping):
        return {}
    summary = packet.get("summary") if isinstance(packet.get("summary"), Mapping) else {}
    load_shed = packet.get("load_shed") if isinstance(packet.get("load_shed"), Mapping) else {}
    resident_threads = (
        packet.get("resident_threads")
        if isinstance(packet.get("resident_threads"), Mapping)
        else {}
    )
    return {
        "summary": {
            "bottleneck_class": summary.get("bottleneck_class"),
            "pressure_index": summary.get("pressure_index"),
            "progress_per_pressure": summary.get("progress_per_pressure"),
            "active_agents": summary.get("active_agents"),
        },
        "load_shed": {
            "target_classes": list(load_shed.get("target_classes") or []),
            "recommended_actions": list(load_shed.get("recommended_actions") or []),
        },
        "resident_threads": {
            "counts": dict(resident_threads.get("counts") or {}),
            "action_counts": dict(resident_threads.get("action_counts") or {}),
            "safety": dict(resident_threads.get("safety") or {}),
        },
    }


def _resident_thread_yield_context(row: Mapping[str, Any]) -> Dict[str, Any] | None:
    action = str(row.get("recommended_action") or "").strip()
    if action == "yield_request":
        return {
            "target_class": "low_progress_session",
            "owner_status": "quiet_active_claim",
            "requested_action": "yield",
            "result_note": (
                "resident-pressure-relief: active claim is quiet beyond warm "
                "threshold; ask owner to yield or refresh"
            ),
        }
    if action == "nap":
        return {
            "target_class": "idle_session",
            "owner_status": "idle_unclaimed",
            "requested_action": "yield",
            "result_note": (
                "resident-pressure-relief: unclaimed idle thread can downshift "
                "while preserving resume state"
            ),
        }
    return None


def _resident_thread_skip_reason(row: Mapping[str, Any]) -> str:
    action = str(row.get("recommended_action") or "").strip()
    if action == "terminate_grace":
        return "terminate_grace_requires_recheck_not_yield_bus_spend"
    if action == "stale_claim_sweep":
        return "active_claim_requires_claim_demote_or_sweep_not_host_action"
    if action == "archive_only":
        return "archive_only_uses_session_sweep_dry_run_lane"
    if action == "keep":
        return "inside_warm_threshold_or_pressure_inactive"
    return "not_a_resident_yield_candidate"


def _resident_thread_source_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "session_id": row.get("session_id"),
        "state": row.get("state"),
        "recommended_action": row.get("recommended_action"),
        "reason": row.get("reason"),
        "idle_seconds": row.get("idle_seconds"),
        "idle_minutes": row.get("idle_minutes"),
        "active_claim_count": row.get("active_claim_count"),
        "protected_by_active_claim": row.get("protected_by_active_claim"),
        "safe_to_nap": row.get("safe_to_nap"),
        "safe_to_terminate_after_grace": row.get("safe_to_terminate_after_grace"),
        "safe_next_command": row.get("safe_next_command"),
    }


def _resident_thread_yield_request_event(
    row: Mapping[str, Any],
    *,
    pressure_mode: str,
    request_result: str,
) -> Dict[str, Any]:
    context = _resident_thread_yield_context(row) or {}
    session_id = str(row.get("session_id") or "unknown")
    requested_action = str(context.get("requested_action") or "yield")
    request_id = _mint_session_yield_request_id(session_id, requested_action)
    try:
        idle_age_s = float(row.get("idle_seconds") or 0.0)
    except (TypeError, ValueError):
        idle_age_s = 0.0
    try:
        active_claim_count = int(row.get("active_claim_count") or 0)
    except (TypeError, ValueError):
        active_claim_count = 0
    receipt = work_admission.build_session_yield_request_receipt(
        target_id=session_id,
        request_id=request_id,
        target_class=str(context.get("target_class") or "idle_session"),
        requested_action=requested_action,
        owner_status=str(context.get("owner_status") or "unknown"),
        pressure_mode=pressure_mode,
        result=request_result,
        helper_rss_mb=0.0,
        recent_progress_units=0.0,
        result_note=str(context.get("result_note") or ""),
    )
    rank = work_admission.build_session_pressure_rank(
        [
            {
                "session_id": session_id,
                "owner_status": receipt.get("owner_status"),
                "helper_rss_mb": 0.0,
                "recent_progress_units": 0.0,
                "idle_age_s": idle_age_s,
                "last_heartbeat_age_s": idle_age_s,
                "active_claim_count": active_claim_count,
                "operator_priority_hint": None,
            }
        ],
        limit=1,
    )
    request_context = {
        "request_id": request_id,
        "requested_action": receipt.get("requested_action"),
        "target_class": receipt.get("target_class"),
        "result": receipt.get("result"),
        "rank_candidate_preserved": True,
        "reason": "resident_thread_governor_spend",
    }
    for rank_row in rank.get("rows", []):
        rank_row["explicit_request"] = dict(request_context)
    return {
        "schema": "session_yield_request_command_v1",
        "status": receipt.get("result"),
        "written": False,
        "request_id": request_id,
        "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
        "session_yield_request": receipt,
        "session_pressure_rank": rank,
        "source": {
            "surface": "resident_pressure_relief",
            "resident_thread_governor_row": _resident_thread_source_row(row),
        },
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def _resident_thread_yield_spend(args: argparse.Namespace, *, before_packet: Mapping[str, Any]) -> Dict[str, Any]:
    if not bool(getattr(args, "spend_resident_thread_relief", False)):
        return {
            "schema": "resident_thread_yield_spend_receipt_v1",
            "status": "not_requested",
            "dry_run": True,
            "written_count": 0,
            "safety": {
                "no_process_signal_sent": True,
                "no_unknown_owner_killed": True,
                "no_active_session_terminated": True,
            },
        }
    apply_requests = bool(getattr(args, "apply_session_yield_requests", False))
    request_limit = max(0, int(getattr(args, "resident_thread_request_limit", 5) or 0))
    scan_limit = max(0, int(getattr(args, "resident_thread_scan_limit", 100) or 0))
    existing_request_scan_limit = max(
        1,
        int(getattr(args, "resident_thread_existing_request_scan_limit", 1000) or 1000),
    )
    pending_ttl_s = max(
        1,
        int(
            getattr(
                args,
                "resident_thread_pending_ttl_s",
                work_admission.RESIDENT_RELIEF_PENDING_TTL_S,
            )
            or work_admission.RESIDENT_RELIEF_PENDING_TTL_S
        ),
    )
    warm_after = timedelta(
        minutes=float(getattr(args, "resident_thread_warm_after_minutes", 10.0) or 10.0)
    )
    terminate_after = timedelta(
        minutes=float(getattr(args, "resident_thread_terminate_after_minutes", 30.0) or 30.0)
    )
    request_result = str(getattr(args, "resident_thread_request_result", "requested") or "requested")
    status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    governor = work_ledger_runtime.build_resident_thread_governor(
        status,
        pressure_mode=args.pressure_mode,
        warm_after=warm_after,
        terminate_after=terminate_after,
        limit=scan_limit,
    )
    pending_requests_by_target = _pending_session_yield_requests_by_target(
        limit=existing_request_scan_limit,
    )
    requests: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    spendable_source_count = 0
    already_pending_count = 0
    stale_pending_count = 0
    observed_at = datetime.now(timezone.utc)
    for row in governor.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        context = _resident_thread_yield_context(row)
        if not context:
            skipped.append(
                {
                    **_resident_thread_source_row(row),
                    "spendable": False,
                    "skip_reason": _resident_thread_skip_reason(row),
                }
            )
            continue
        spendable_source_count += 1
        target_id = str(row.get("session_id") or "").strip()
        pending_request = pending_requests_by_target.get(target_id)
        if pending_request:
            already_pending_count += 1
            pending_age_s = _session_yield_pending_age_s(
                pending_request,
                now=observed_at,
            )
            pending_stale = bool(pending_age_s is not None and pending_age_s >= pending_ttl_s)
            if pending_stale:
                stale_pending_count += 1
            skipped.append(
                {
                    **_resident_thread_source_row(row),
                    "spendable": True,
                    "skip_reason": "resident_thread_yield_request_stale_pending_recheck_required"
                    if pending_stale
                    else "resident_thread_yield_request_already_pending",
                    "pending_request_id": pending_request.get("request_id"),
                    "pending_requested_action": pending_request.get("requested_action"),
                    "pending_issued_at": pending_request.get("issued_at"),
                    "pending_age_s": pending_age_s,
                    "pending_ttl_s": pending_ttl_s,
                    "pending_stale": pending_stale,
                }
            )
            continue
        if len(requests) >= request_limit:
            skipped.append(
                {
                    **_resident_thread_source_row(row),
                    "spendable": True,
                    "skip_reason": "resident_thread_request_limit_reached",
                }
            )
            continue
        requests.append(
            _resident_thread_yield_request_event(
                row,
                pressure_mode=args.pressure_mode,
                request_result=request_result,
            )
        )

    if apply_requests:
        for request in requests:
            request["written"] = True
            _append_jsonl(SESSION_YIELD_REQUESTS, request)

    after_packet: Dict[str, Any] | None = None
    if bool(getattr(args, "resident_thread_recheck", True)):
        after_packet = _current_host_pressure_packet()
    extra_request_events = [] if apply_requests else requests
    settlement = _resident_relief_settlement_window(
        runtime_status=status,
        resident_thread_rows=[
            row for row in governor.get("rows", []) if isinstance(row, Mapping)
        ],
        extra_request_events=extra_request_events,
        limit=existing_request_scan_limit,
        output_profile="compact",
        pending_ttl_s=pending_ttl_s,
    )

    if requests and apply_requests:
        spend_status = "requests_written"
    elif requests:
        spend_status = "dry_run_ready"
    elif stale_pending_count:
        spend_status = "stale_pending_recheck_required"
    elif already_pending_count:
        spend_status = "requests_already_pending"
    elif governor.get("rows"):
        spend_status = "no_spendable_resident_rows"
    else:
        spend_status = "no_resident_rows"

    return {
        "schema": "resident_thread_yield_spend_receipt_v1",
        "status": spend_status,
        "dry_run": not apply_requests,
        "apply_session_yield_requests": apply_requests,
        "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
        "scan_limit": scan_limit,
        "existing_request_scan_limit": existing_request_scan_limit,
        "pending_ttl_s": pending_ttl_s,
        "request_limit": request_limit,
        "scanned_count": len(governor.get("rows", []) or []),
        "rows_omitted": governor.get("rows_omitted"),
        "spendable_source_count": spendable_source_count,
        "already_pending_count": already_pending_count,
        "stale_pending_count": stale_pending_count,
        "requested_count": len(requests),
        "written_count": len(requests) if apply_requests else 0,
        "skipped_count": len(skipped),
        "before_host_pressure_summary": _host_pressure_relief_summary(before_packet),
        "after_host_pressure_summary": (
            _host_pressure_relief_summary(after_packet) if after_packet is not None else None
        ),
        "resident_thread_governor": {
            "schema": governor.get("schema"),
            "pressure_mode": governor.get("pressure_mode"),
            "thresholds": dict(governor.get("thresholds") or {}),
            "counts": dict(governor.get("counts") or {}),
            "action_counts": dict(governor.get("action_counts") or {}),
            "safety": dict(governor.get("safety") or {}),
        },
        "resident_relief_settlement": settlement,
        "session_yield_requests": requests,
        "skipped_resident_rows": skipped[:20],
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def cmd_resident_pressure_relief(args: argparse.Namespace) -> int:
    before_packet = _current_host_pressure_packet()
    release_request = work_admission.build_helper_owner_release_request(
        process_kind=args.process_kind,
        owner_status=args.owner_status,
        rss_mb_total=args.rss_mb_total,
        target_owner=args.target_owner,
        pressure_mode=args.pressure_mode,
    )
    release_result = work_admission.build_owner_release_result_receipt(
        release_request=release_request,
        result=args.owner_release_result,
        result_note=args.result_note,
    )
    downshift = None
    if args.background_loop_kind:
        downshift_result = "applied" if args.apply_background_downshift else args.background_loop_result
        downshift = work_admission.build_background_loop_downshift_receipt(
            loop_kind=args.background_loop_kind,
            owner_surface=args.owner_surface or "unknown",
            pressure_mode=args.pressure_mode,
            result=downshift_result,
            duration_s=args.duration_s,
            effective_interval_s=args.effective_interval_s,
        )
        if args.apply_background_downshift:
            BACKGROUND_DOWNSHIFT_STATE.parent.mkdir(parents=True, exist_ok=True)
            BACKGROUND_DOWNSHIFT_STATE.write_text(
                json.dumps(downshift, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    window = work_admission.build_resident_pressure_relief_window(
        before_packet=before_packet,
        owner_release_results=[release_result],
        background_downshifts=[downshift] if downshift else [],
        blocked_work_starts=args.blocked_work_starts,
        blocked_helper_leases=args.blocked_helper_leases,
        workload_mix_changed=bool(args.workload_mix_changed),
    )
    resident_thread_spend = _resident_thread_yield_spend(args, before_packet=before_packet)
    payload = {
        "schema": "resident_pressure_relief_command_v1",
        "status": window.get("verdict"),
        "pressure_mode": args.pressure_mode,
        "helper_owner_release_request": release_request,
        "owner_release_result": release_result,
        "background_loop_downshift": downshift,
        "background_downshift_state_path": str(BACKGROUND_DOWNSHIFT_STATE.relative_to(REPO_ROOT))
        if args.apply_background_downshift and downshift
        else None,
        "resident_pressure_relief_window": window,
        "resident_thread_yield_spend": resident_thread_spend,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }
    _print(payload)
    resident_spend_ready = resident_thread_spend.get("status") in {
        "dry_run_ready",
        "requests_already_pending",
        "requests_written",
        "stale_pending_recheck_required",
    }
    return (
        0
        if window.get("verdict") != "no_resident_actuator" or resident_spend_ready
        else work_admission.ADMISSION_TEMPFAIL
    )


def cmd_resident_thread_governor(args: argparse.Namespace) -> int:
    status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    payload = work_ledger_runtime.build_resident_thread_governor(
        status,
        pressure_mode=args.pressure_mode,
        warm_after=timedelta(minutes=float(args.warm_after_minutes)),
        terminate_after=timedelta(minutes=float(args.terminate_after_minutes)),
        limit=int(args.limit or 0),
    )
    _print(payload)
    return 0


def cmd_session_yield_request(args: argparse.Namespace) -> int:
    request_id = getattr(args, "request_id", None) or _mint_session_yield_request_id(
        args.target_session_id,
        args.requested_action,
    )
    receipt = work_admission.build_session_yield_request_receipt(
        target_id=args.target_session_id,
        request_id=request_id,
        target_class=args.target_class,
        requested_action=args.requested_action,
        owner_status=args.owner_status,
        pressure_mode=args.pressure_mode,
        result=args.result,
        helper_rss_mb=args.helper_rss_mb,
        recent_progress_units=args.recent_progress_units,
        result_note=args.result_note,
    )
    coordination_brief_requested = bool(getattr(args, "coordination_brief", False)) or any(
        [
            getattr(args, "requester_label", None),
            getattr(args, "requester_session_id", None),
            getattr(args, "blocked_on", None),
            getattr(args, "validation_status", None),
            list(getattr(args, "held_path", []) or []),
            list(getattr(args, "avoid_path", []) or []),
            list(getattr(args, "avoid_session_id", []) or []),
            getattr(args, "requested_action_note", None),
        ]
    )
    coordination_request: dict[str, Any] | None = None
    if coordination_brief_requested:
        coordination_request = work_admission.build_session_yield_coordination_request(
            yield_request=receipt,
            requester_label=getattr(args, "requester_label", None),
            requester_session_id=getattr(args, "requester_session_id", None),
            blocked_on=getattr(args, "blocked_on", None),
            validation_status=getattr(args, "validation_status", None),
            held_paths=list(getattr(args, "held_path", []) or []),
            avoid_paths=list(getattr(args, "avoid_path", []) or []),
            avoid_session_ids=list(getattr(args, "avoid_session_id", []) or []),
            requested_action_note=getattr(args, "requested_action_note", None),
        )
        receipt["coordination_request"] = coordination_request
    rank = work_admission.build_session_pressure_rank(
        [
            {
                "session_id": args.target_session_id,
                "owner_status": args.owner_status,
                "helper_rss_mb": args.helper_rss_mb,
                "recent_progress_units": args.recent_progress_units,
                "idle_age_s": args.idle_age_s,
                "last_heartbeat_age_s": args.last_heartbeat_age_s,
                "active_claim_count": args.active_claim_count,
                "operator_priority_hint": args.operator_priority_hint,
            }
        ],
        limit=1,
    )
    request_context = {
        "request_id": request_id,
        "requested_action": receipt.get("requested_action"),
        "target_class": receipt.get("target_class"),
        "result": receipt.get("result"),
        "rank_candidate_preserved": True,
        "reason": "explicit_owner_visible_request",
    }
    for row in rank.get("rows", []):
        row["explicit_request"] = dict(request_context)
    payload = {
        "schema": "session_yield_request_command_v1",
        "status": receipt.get("result"),
        "written": not bool(args.dry_run),
        "request_id": request_id,
        "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
        "session_yield_request": receipt,
        "session_yield_coordination_request": coordination_request,
        "session_pressure_rank": rank,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }
    if not args.dry_run:
        _append_jsonl(SESSION_YIELD_REQUESTS, payload)
    _print(payload)
    return 0 if receipt.get("result") != "owner_unresolved" else work_admission.ADMISSION_TEMPFAIL


def cmd_session_yield_result(args: argparse.Namespace) -> int:
    yield_request = _find_session_yield_request(
        request_id=getattr(args, "request_id", None),
        target_session_id=getattr(args, "target_session_id", None),
    )
    if not yield_request:
        payload = {
            "schema": "owner_yield_result_command_v1",
            "status": "request_not_found",
            "written": False,
            "request_id": getattr(args, "request_id", None),
            "target_session_id": getattr(args, "target_session_id", None),
            "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
            "result_log_path": str(SESSION_YIELD_RESULTS.relative_to(REPO_ROOT)),
            "safety": {
                "no_process_signal_sent": True,
                "no_unknown_owner_killed": True,
                "no_active_session_terminated": True,
            },
        }
        _print(payload)
        return work_admission.ADMISSION_TEMPFAIL
    result = work_admission.build_owner_yield_result_receipt(
        yield_request=yield_request,
        result=args.result,
        applied_action=args.applied_action,
        delivery=args.delivery,
        result_note=args.result_note,
    )
    payload = {
        "schema": "owner_yield_result_command_v1",
        "status": result.get("status"),
        "written": not bool(args.dry_run),
        "request_id": result.get("request_id"),
        "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
        "result_log_path": str(SESSION_YIELD_RESULTS.relative_to(REPO_ROOT)),
        "matched_request": yield_request,
        "owner_yield_result": result,
        "safety": result.get("safety"),
    }
    if not args.dry_run:
        _append_jsonl(SESSION_YIELD_RESULTS, payload)
    _print(payload)
    return 0 if result.get("result") != "owner_unresolved" else work_admission.ADMISSION_TEMPFAIL


def cmd_session_yield_control(args: argparse.Namespace) -> int:
    background_loop_downshift: dict[str, Any] | None = None
    if BACKGROUND_DOWNSHIFT_STATE.exists():
        try:
            decoded = json.loads(BACKGROUND_DOWNSHIFT_STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            background_loop_downshift = decoded
    request_events = _read_jsonl_tail(SESSION_YIELD_REQUESTS, limit=args.limit)
    result_events = _read_jsonl_tail(SESSION_YIELD_RESULTS, limit=args.limit)
    payload = work_admission.build_session_yield_control_surface(
        request_events=request_events,
        result_events=result_events,
        background_loop_downshift=background_loop_downshift,
        limit=args.limit,
        output_profile="full" if getattr(args, "full", False) else "compact",
    )
    resident_request_events = [
        row
        for row in request_events
        if isinstance(row, Mapping) and _is_resident_relief_request_event(row)
    ]
    resident_request_ids = {
        str(_session_yield_request_payload(row).get("request_id") or "").strip()
        for row in resident_request_events
    }
    resident_request_ids.discard("")
    resident_target_ids = {
        str(_session_yield_request_payload(row).get("target_id") or "").strip()
        for row in resident_request_events
    }
    resident_target_ids.discard("")
    resident_result_events = []
    for row in result_events:
        if not isinstance(row, Mapping):
            continue
        result = _session_yield_result_payload(row)
        request_id = str(result.get("request_id") or "").strip()
        target_id = str(result.get("target_id") or "").strip()
        if request_id in resident_request_ids or (not request_id and target_id in resident_target_ids):
            resident_result_events.append(row)
    try:
        runtime_status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    except Exception:  # noqa: BLE001 - observation surface must degrade
        runtime_status = {}
    payload["resident_relief_settlement"] = work_admission.build_resident_relief_settlement_window(
        request_events=resident_request_events,
        result_events=resident_result_events,
        runtime_status=runtime_status,
        pending_ttl_s=getattr(
            args,
            "pending_ttl_s",
            work_admission.RESIDENT_RELIEF_PENDING_TTL_S,
        ),
        limit=args.limit,
        output_profile="full" if getattr(args, "full", False) else "compact",
    )
    _print(payload)
    return 0


def cmd_session_yield_inbox(args: argparse.Namespace) -> int:
    payload = work_admission.build_session_yield_inbox_surface(
        session_id=args.session_id,
        request_events=_read_jsonl_tail(SESSION_YIELD_REQUESTS, limit=args.scan_limit),
        result_events=_read_jsonl_tail(SESSION_YIELD_RESULTS, limit=args.scan_limit),
        limit=args.limit,
    )
    _print(payload)
    return 0


def cmd_session_message(args: argparse.Namespace) -> int:
    message = work_ledger_runtime.build_session_message_receipt(
        message_id=getattr(args, "message_id", None),
        from_session_id=args.from_session_id,
        to_session_id=args.to_session_id,
        message_type=args.message_type,
        subject=getattr(args, "subject", None),
        body=args.body,
        related_paths=list(getattr(args, "related_path", []) or []),
        related_request_id=getattr(args, "related_request_id", None),
        reply_to_message_id=getattr(args, "reply_to_message_id", None),
        requires_ack=bool(getattr(args, "requires_ack", False)),
    )
    payload = {
        "schema": "session_message_command_v1",
        "status": "dry_run" if args.dry_run else "written",
        "written": not bool(args.dry_run),
        "message_id": message.get("message_id"),
        "message_log_path": str(SESSION_MESSAGES.relative_to(REPO_ROOT)),
        "session_message": message,
        "recommended_commands": {
            "recipient_inbox": message.get("inbox_command"),
            "sender_inbox": message.get("sender_inbox_command"),
            "ack": message.get("ack_command"),
        },
        "safety": message.get("safety"),
    }
    if not args.dry_run:
        _append_jsonl(SESSION_MESSAGES, payload)
    _print(payload)
    return 0


def cmd_session_message_inbox(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.build_session_message_inbox_surface(
        session_id=args.session_id,
        message_events=_read_jsonl_tail(SESSION_MESSAGES, limit=args.scan_limit),
        limit=args.limit,
        include_sent=bool(getattr(args, "include_sent", False)),
    )
    _print(payload)
    return 0


def cmd_session_preflight(args: argparse.Namespace) -> int:
    session_id = args.session_id or _mint_preflight_session_id(args.actor, args.session_slug)
    write_profiles = _preflight_write_profiles(list(getattr(args, "write_profile", []) or []))
    claim_paths = _preflight_claim_paths(list(args.path or []), write_profiles)
    host_resource_pressure = resource_pressure.build_host_resource_pressure_packet(REPO_ROOT)
    source_input_paths = _preflight_source_input_paths(write_profiles)
    source_input_collisions = _active_claim_collisions_for_paths(
        source_input_paths,
        session_id=session_id,
    )
    if source_input_collisions and bool(args.require_exclusive):
        blocked_payload = {
            "schema": "work_ledger_session_preflight_v1",
            "mode": "full",
            "status": "blocked_by_source_input_claim",
            "session_id": session_id,
            "actor": args.actor,
            "phase_id": args.phase_id,
            "family_id": args.family_id,
            "read_receipt_id": None,
            "codex_import": None,
            "claude_ide_import": None,
            "bootstrap": {},
            "write_profiles": write_profiles,
            "source_input_paths": source_input_paths,
            "source_input_collision_count": len(source_input_collisions),
            "source_input_collisions": source_input_collisions,
            "source_input_claim_policy": "must_be_clean_committed_or_owned_before_landing_outputs",
            "work_creation_classification": {},
            "host_resource_pressure": host_resource_pressure,
            "work_admission": {},
            "claim_summary": {
                "requested": len(claim_paths) + len(args.td_id or []),
                "claimed": 0,
                "claimed_with_collision": 0,
                "refused": len(claim_paths) + len(args.td_id or []),
            },
            "claims": [],
            "observed_path_overlaps": [],
            "shared_worktree_git_risks": [],
            "overview": {},
            "closeout_rule": {
                "schema": "work_ledger_preflight_closeout_rule_v1",
                "status": "not_started_blocked_by_source_input_claim",
                "rule": (
                    "No Work Ledger claims were written because a source-coupled "
                    "write profile would read source inputs held by another active session."
                ),
            },
            "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
            "closeout_plan": {
                "schema": "work_ledger_closeout_plan_v1",
                "recommended_sequence": [],
            },
            "closeout_commands": [],
        }
        if getattr(args, "full", False):
            _print(blocked_payload)
        else:
            _print(_compact_preflight_payload(blocked_payload))
        return 2
    requested_work_class = _normalize_work_admission_class(
        getattr(args, "work_admission_class", None)
    )
    work_creation_classification = work_admission.classify_work_creation_request(
        paths=claim_paths,
        write_profiles=write_profiles,
        requested_class=requested_work_class,
    )
    work_admission_decision = work_admission.build_work_admission_decision(
        REPO_ROOT,
        work_class=str(work_creation_classification.get("work_class") or work_admission.CHEAP_READ),
        policy=getattr(args, "host_pressure_policy", None) or "auto",
        request_id=session_id,
    )
    if (
        host_resource_pressure.get("status") == "critical"
        and not resource_pressure.declared_paths_are_resource_repair(claim_paths)
        and bool(work_creation_classification.get("heavy"))
        and str(getattr(args, "host_pressure_policy", None) or "auto") == "auto"
    ):
        blocked_payload = {
            "schema": "work_ledger_session_preflight_v1",
            "mode": "full",
            "status": "blocked_by_host_resource_pressure",
            "session_id": session_id,
            "actor": args.actor,
            "phase_id": args.phase_id,
            "family_id": args.family_id,
            "read_receipt_id": None,
            "codex_import": None,
            "claude_ide_import": None,
            "bootstrap": {},
            "write_profiles": write_profiles,
            "source_input_paths": source_input_paths,
            "source_input_collision_count": 0,
            "source_input_collisions": [],
            "source_input_claim_policy": "not_evaluated_resource_pressure_blocked",
            "work_creation_classification": work_creation_classification,
            "host_resource_pressure": host_resource_pressure,
            "work_admission": {
                **work_admission_decision,
                "schema": "work_creation_admission_decision_v0",
                "status": "blocked_by_host_resource_pressure",
                "result": "block",
                "allow": False,
                "resource_pressure_result": "critical_resource_pressure_heavy_work_blocked",
                "override_hint": (
                    "Enter the resource repair lane or rerun only with an operator-authorized "
                    "urgent override receipt, --host-pressure-policy=warn, or --host-pressure-policy=off."
                ),
            },
            "claim_summary": {
                "requested": len(claim_paths) + len(args.td_id or []),
                "claimed": 0,
                "claimed_with_collision": 0,
                "refused": len(claim_paths) + len(args.td_id or []),
            },
            "claims": [],
            "observed_path_overlaps": [],
            "shared_worktree_git_risks": [],
            "overview": {},
            "closeout_rule": {
                "schema": "work_ledger_preflight_closeout_rule_v1",
                "status": "not_started_blocked_by_host_resource_pressure",
                "rule": (
                    "No Work Ledger claims were written because critical host resource "
                    "pressure admits only repair-lane or explicitly authorized urgent work."
                ),
            },
            "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
            "closeout_plan": {
                "schema": "work_ledger_closeout_plan_v1",
                "recommended_sequence": [],
            },
            "closeout_commands": [],
        }
        if getattr(args, "full", False):
            _print(blocked_payload)
        else:
            _print(_compact_preflight_payload(blocked_payload))
        return work_admission.ADMISSION_TEMPFAIL
    if not bool(work_admission_decision.get("allow", True)):
        blocked_payload = {
            "schema": "work_ledger_session_preflight_v1",
            "mode": "full",
            "status": "blocked_by_work_admission",
            "session_id": session_id,
            "actor": args.actor,
            "phase_id": args.phase_id,
            "family_id": args.family_id,
            "read_receipt_id": None,
            "codex_import": None,
            "claude_ide_import": None,
            "bootstrap": {},
            "write_profiles": write_profiles,
            "work_creation_classification": work_creation_classification,
            "host_resource_pressure": host_resource_pressure,
            "work_admission": work_admission_decision,
            "claim_summary": {
                "requested": len(claim_paths) + len(args.td_id or []),
                "claimed": 0,
                "claimed_with_collision": 0,
                "refused": len(claim_paths) + len(args.td_id or []),
            },
            "claims": [],
            "observed_path_overlaps": [],
            "shared_worktree_git_risks": [],
            "overview": {},
            "closeout_rule": {
                "schema": "work_ledger_preflight_closeout_rule_v1",
                "status": "not_started_blocked_by_work_admission",
                "rule": "No Work Ledger claims were written because pressure admission refused this work start.",
            },
            "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
            "closeout_plan": {
                "schema": "work_ledger_closeout_plan_v1",
                "recommended_sequence": [],
            },
            "closeout_commands": [],
        }
        if getattr(args, "full", False):
            _print(blocked_payload)
        else:
            _print(_compact_preflight_payload(blocked_payload))
        return work_admission.ADMISSION_TEMPFAIL
    codex_import = None
    if not getattr(args, "skip_import_codex", False):
        db_path = Path(args.db_path).expanduser() if args.db_path else CODEX_STATE_DB
        codex_import = _import_codex_sessions(
            db_path=db_path,
            actor=args.actor,
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.import_limit,
            include_all_cwds=bool(args.include_all_cwds),
            dry_run=True,
        )
    claude_import = None
    if not getattr(args, "skip_import_claude", False):
        claude_import = _import_claude_ide_sessions(
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.import_limit,
            include_all_workspaces=bool(args.include_all_workspaces),
            dry_run=True,
        )
    claim_scopes: List[Dict[str, str]] = [
        {"scope_kind": work_ledger_runtime.CLAIM_SCOPE_THREAD, "scope_id": str(td_id)}
        for td_id in (args.td_id or [])
    ]
    claim_scopes.extend(
        {
            "scope_kind": work_ledger_runtime.CLAIM_SCOPE_PATH,
            "scope_id": str(path),
        }
        for path in claim_paths
    )
    heartbeat_current_line = getattr(args, "heartbeat_current_pass_line", None)
    heartbeat_result_line = getattr(args, "heartbeat_last_pass_result_line", None)
    if bool(getattr(args, "heartbeat_clip_lines", False)):
        heartbeat_current_line = _clip_public_heartbeat_line(
            heartbeat_current_line,
            limit=work_ledger_runtime.PASS_CURRENT_LINE_LIMIT,
        )
        heartbeat_result_line = _clip_public_heartbeat_line(
            heartbeat_result_line,
            limit=work_ledger_runtime.PASS_RESULT_LINE_LIMIT,
        )
    heartbeat_scope_refs = list(getattr(args, "heartbeat_scope_ref", []) or [])
    heartbeat_scope_policy = "explicit"
    if (heartbeat_current_line or heartbeat_result_line) and not heartbeat_scope_refs:
        heartbeat_scope_refs = list(args.td_id or []) + list(claim_paths)
        heartbeat_scope_policy = "claimed_scopes"
    heartbeat_state = _normalize_cli_heartbeat_state(
        getattr(args, "heartbeat_state", "inspecting")
    )
    bootstrap_heartbeat = None
    if heartbeat_current_line or heartbeat_result_line:
        bootstrap_heartbeat = {
            "pass_state": heartbeat_state,
            "current_pass_line": heartbeat_current_line,
            "last_pass_result_line": heartbeat_result_line,
            "td_id": (args.td_id or [None])[0],
            "scope_refs": heartbeat_scope_refs,
            "source": getattr(args, "heartbeat_source", "manual_cli") or "manual_cli",
        }
    external_observations = []
    if isinstance(codex_import, Mapping):
        external_observations.extend(
            row for row in list(codex_import.get("observation_inputs") or []) if isinstance(row, Mapping)
        )
    if isinstance(claude_import, Mapping):
        external_observations.extend(
            row for row in list(claude_import.get("observation_inputs") or []) if isinstance(row, Mapping)
        )
    bootstrap = work_ledger_runtime.bootstrap_session(
        REPO_ROOT,
        session_id=session_id,
        actor=args.actor,
        phase_id=args.phase_id,
        family_id=args.family_id,
        limit=args.bootstrap_limit,
        claim_scopes=claim_scopes,
        claim_lease_minutes=args.lease_minutes,
        claim_note=args.note,
        require_exclusive_claims=bool(args.require_exclusive),
        pass_heartbeat=bootstrap_heartbeat,
        external_observations=external_observations,
    )
    external_observation_results = list(bootstrap.get("external_observations") or [])
    if isinstance(codex_import, dict):
        codex_count = len(list(codex_import.get("observation_inputs") or []))
        codex_import["observations"] = external_observation_results[:codex_count]
        codex_import["imported_count"] = len(codex_import["observations"])
    if isinstance(claude_import, dict):
        codex_count = len(list((codex_import or {}).get("observation_inputs") or []))
        claude_import["observations"] = external_observation_results[codex_count:]
        claude_import["imported_count"] = len(claude_import["observations"])
    claims = list(bootstrap.get("claims") or [])
    initial_heartbeat: Dict[str, Any] = {"status": "not_requested"}
    if heartbeat_current_line or heartbeat_result_line:
        initial_heartbeat = {
            "schema": "work_ledger_session_preflight_initial_heartbeat_v0",
            "status": "written",
            "scope_ref_policy": heartbeat_scope_policy,
            "pass_heartbeat": dict(bootstrap.get("pass_heartbeat") or {}),
        }
    observed_path_overlaps = _observed_path_overlaps(
        requested_paths=_preflight_requested_paths(claim_paths),
        codex_import=codex_import,
    )
    shared_worktree_git_risks = _observed_shared_worktree_git_risks(codex_import=codex_import)
    cached_overview = (
        bootstrap.get("cohort_overview")
        if isinstance(bootstrap.get("cohort_overview"), Mapping)
        else None
    )
    if (
        int(args.overview_limit or 0) == work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT
        and cached_overview is not None
    ):
        overview = dict(cached_overview)
    else:
        status_after_claims = work_ledger_runtime.load_runtime_status(REPO_ROOT, rebuild=False)
        overview = work_ledger_runtime.build_session_cohort_overview(
            status_after_claims,
            limit=args.overview_limit,
        )
    closeout_plan = _claim_closeout_plan(
        session_id,
        claims,
        read_receipt_id=str(bootstrap.get("read_receipt_id") or ""),
        actor=args.actor,
        phase_id=str(bootstrap.get("phase_id") or args.phase_id or ""),
        family_id=str(bootstrap.get("family_id") or args.family_id or ""),
    )
    payload = {
        "schema": "work_ledger_session_preflight_v1",
        "mode": "full",
        "session_id": session_id,
        "actor": args.actor,
        "phase_id": bootstrap.get("phase_id"),
        "family_id": bootstrap.get("family_id"),
        "read_receipt_id": bootstrap.get("read_receipt_id"),
        "codex_import": codex_import,
        "claude_ide_import": claude_import,
        "bootstrap": bootstrap,
        "write_profiles": write_profiles,
        "source_input_paths": source_input_paths,
        "source_input_collision_count": len(source_input_collisions),
        "source_input_collisions": source_input_collisions,
        "source_input_claim_policy": (
            "must_be_clean_committed_or_owned_before_landing_outputs"
            if source_input_paths
            else "not_declared_for_selected_profiles"
        ),
        "work_creation_classification": work_creation_classification,
        "host_resource_pressure": host_resource_pressure,
        "work_admission": work_admission_decision,
        "claims": claims,
        "observed_path_overlaps": observed_path_overlaps,
        "shared_worktree_git_risks": shared_worktree_git_risks,
        "overview": overview,
        "initial_heartbeat": initial_heartbeat,
        "closeout_rule": {
            "schema": "work_ledger_preflight_closeout_rule_v1",
            "status": "append_or_append_exempt_before_finalize",
            "read_receipt_id": bootstrap.get("read_receipt_id"),
            "rule": (
                "If this session touched claimed work, write Work Ledger progress/close "
                "evidence or record an append-exempt closeout before bare session-finalize. "
                "The finalizer blocks touched/no-append sessions unless append-exempt is explicit."
            ),
        },
        "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
        "closeout_plan": closeout_plan,
        "closeout_commands": closeout_plan["recommended_sequence"],
    }
    if getattr(args, "full", False) and getattr(args, "raw_full", False):
        return _print(payload)
    if getattr(args, "full", False):
        return _print(_bounded_full_preflight_payload(payload))
    return _print(_compact_preflight_payload(payload))


def _claim_refusal_payload(
    *,
    exc: ValueError,
    session_id: str,
    scope_kind: str,
    scope_id: str,
) -> Dict[str, Any] | None:
    message = str(exc)
    if "has already ended; re-bootstrap before claiming" not in message:
        return None
    quoted_session = shlex.quote(str(session_id or ""))
    quoted_scope = shlex.quote(str(scope_id or ""))
    refresh_command = (
        "./repo-python tools/meta/factory/work_ledger.py session-status "
        "--seed-speed --limit 12"
    )
    drilldown_command = (
        "./repo-python tools/meta/factory/work_ledger.py session-status "
        f"--session-id {quoted_session} --full"
    )
    if scope_kind == "path":
        retry_command = (
            "./repo-python tools/meta/factory/work_ledger.py session-claim-path "
            f"--session-id {quoted_session} --path {quoted_scope} "
            "--lease-minutes 30 --require-exclusive"
        )
        rebootstrap_command = (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            f"--session-id {quoted_session} --path {quoted_scope} "
            "--lease-minutes 30 --require-exclusive"
        )
    elif scope_kind == "work_item_id":
        retry_command = (
            "./repo-python tools/meta/factory/work_ledger.py session-claim "
            f"--session-id {quoted_session} --td-id {quoted_scope} "
            "--conflict-scope-kind work_item_id --lease-minutes 30 "
            "--require-exclusive"
        )
        rebootstrap_command = (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            f"--session-id {quoted_session} --heartbeat-state inspecting "
            "--heartbeat-current-pass-line '<public current pass>' "
            f"--heartbeat-scope-ref {quoted_scope}"
        )
    else:
        retry_command = (
            "./repo-python tools/meta/factory/work_ledger.py session-claim "
            f"--session-id {quoted_session} --td-id {quoted_scope} "
            "--lease-minutes 30 --require-exclusive"
        )
        rebootstrap_command = (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            f"--session-id {quoted_session} --td-id {quoted_scope} "
            "--lease-minutes 30 --require-exclusive"
        )
    return {
        "schema": "work_ledger_session_claim_blocked_v1",
        "status": "blocked",
        "failure_class": "ended_session_requires_rebootstrap",
        "session_id": str(session_id or ""),
        "scope_kind": scope_kind,
        "scope_id": str(scope_id or ""),
        "message": message,
        "owner_action": (
            "The claim target session has ended. Re-run seed-speed or re-bootstrap "
            "the owner session before claiming this scope."
        ),
        "read_only_drilldown": drilldown_command,
        "refresh_command": refresh_command,
        "rebootstrap_command": rebootstrap_command,
        "claim_command_after_rebootstrap": retry_command,
    }


def cmd_session_claim(args: argparse.Namespace) -> int:
    try:
        payload = work_ledger_runtime.claim_work_thread(
            REPO_ROOT,
            session_id=args.session_id,
            td_id=args.td_id,
            lease_minutes=args.lease_minutes,
            note=args.note,
            require_exclusive=bool(getattr(args, "require_exclusive", False)),
            claim_intent=getattr(args, "claim_intent", work_ledger_runtime.CLAIM_INTENT_HARD_MUTATION),
            conflict_scope_kind=getattr(args, "conflict_scope_kind", None),
        )
    except ValueError as exc:
        blocked = _claim_refusal_payload(
            exc=exc,
            session_id=args.session_id,
            scope_kind=getattr(args, "conflict_scope_kind", None) or "td_id",
            scope_id=args.td_id,
        )
        if blocked is None:
            raise
        return _print_exit(blocked, exit_code=2)
    return _print(payload)


def cmd_session_claim_path(args: argparse.Namespace) -> int:
    try:
        payload = work_ledger_runtime.claim_work_path(
            REPO_ROOT,
            session_id=args.session_id,
            path=args.path,
            lease_minutes=args.lease_minutes,
            note=args.note,
            require_exclusive=bool(getattr(args, "require_exclusive", False)),
            claim_intent=getattr(args, "claim_intent", work_ledger_runtime.CLAIM_INTENT_HARD_MUTATION),
            conflict_scope_kind=getattr(args, "conflict_scope_kind", None),
        )
    except ValueError as exc:
        blocked = _claim_refusal_payload(
            exc=exc,
            session_id=args.session_id,
            scope_kind="path",
            scope_id=args.path,
        )
        if blocked is None:
            raise
        return _print_exit(blocked, exit_code=2)
    return _print(payload)


def cmd_session_release_claim(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.release_claim(
        REPO_ROOT,
        session_id=args.session_id,
        claim_id=args.claim_id,
        td_id=args.td_id,
        path=args.path,
        reason=args.reason,
    )
    return _print(payload)


def _dirty_paths_from_git_status(repo_root: Path) -> tuple[List[str], str]:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return [], f"git_status_unavailable:{type(exc).__name__}"
    if completed.returncode != 0:
        stderr = " ".join((completed.stderr or "").split())
        return [], f"git_status_failed:{stderr or completed.returncode}"
    paths: List[str] = []
    entries = completed.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:] if len(entry) > 3 else ""
        if path:
            paths.append(path)
        if status[:1] in {"R", "C"} or status[1:2] in {"R", "C"}:
            # Porcelain -z rename/copy entries carry the old path in the next field.
            index += 1
    return paths, "git_status_porcelain_v1_z"


def cmd_session_sweep(args: argparse.Namespace) -> int:
    import datetime as _dt

    if bool(getattr(args, "dirty_tree_pressure", False)) and not bool(args.dry_run):
        print(
            json.dumps(
                {
                    "schema": "work_ledger_sweep_report_v1",
                    "status": "blocked",
                    "reason": "DirtyTreePressureRequiresDryRun",
                    "dry_run": False,
                    "next_safe_command": (
                        "./repo-python tools/meta/factory/work_ledger.py "
                        "session-sweep --dry-run --dirty-tree-pressure"
                    ),
                    "mutation_policy": (
                        "dirty-tree pressure is an orientation readback; run session-sweep "
                        "without --dirty-tree-pressure for the explicit live sweep lane"
                    ),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    hours = float(args.orphan_after_hours or 0)
    orphan_after = (
        _dt.timedelta(hours=hours)
        if hours > 0
        else work_ledger_runtime.ACTIVE_SESSION_ORPHAN_SWEEP_AFTER
    )
    expiry = work_ledger_runtime.sweep_expired_claims(
        REPO_ROOT,
        dry_run=bool(args.dry_run),
    )
    orphans = work_ledger_runtime.sweep_orphan_sessions(
        REPO_ROOT,
        orphan_sweep_after=orphan_after,
        dry_run=bool(args.dry_run),
    )
    dirty_tree_pressure = None
    if bool(getattr(args, "dirty_tree_pressure", False)):
        supplied_dirty_paths = list(getattr(args, "dirty_path", None) or [])
        if supplied_dirty_paths:
            dirty_paths = supplied_dirty_paths
            dirty_scan_status = "provided"
        else:
            dirty_paths, dirty_scan_status = _dirty_paths_from_git_status(REPO_ROOT)
        dirty_tree_pressure = work_ledger_runtime.build_dirty_tree_bankruptcy_pressure(
            REPO_ROOT,
            dirty_paths=dirty_paths,
            dirty_scan_status=dirty_scan_status,
            bankruptcy_authorized=bool(getattr(args, "bankruptcy_authorized", False)),
            orphan_sweep_after=orphan_after,
            limit=int(
                getattr(args, "dirty_path_limit", 0)
                or work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT
            ),
        )
        dirty_tree_pressure["sweep_dry_run"] = bool(args.dry_run)
    duplicate_claim_dedupe = None
    if bool(getattr(args, "dedupe_duplicate_claims", False)):
        dedupe_preview_limit = int(
            getattr(args, "dedupe_preview_limit", 0)
            or work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT
        )
        duplicate_claim_dedupe = work_ledger_runtime.dedupe_duplicate_same_session_claims(
            REPO_ROOT,
            dry_run=bool(args.dry_run),
            limit=dedupe_preview_limit,
        )
        if not bool(getattr(args, "full", False)):
            duplicate_claim_dedupe = _compact_duplicate_claim_dedupe_cli_payload(
                duplicate_claim_dedupe,
                released_limit=dedupe_preview_limit,
            )
    dirty_tree_pressure_alias = (
        work_ledger_runtime.dirty_tree_pressure_alias(dirty_tree_pressure)
        if dirty_tree_pressure is not None
        else None
    )
    if dirty_tree_pressure_alias is not None and not bool(getattr(args, "full", False)):
        dirty_tree_pressure_alias = _compact_dirty_tree_pressure_alias_cli_payload(
            dirty_tree_pressure_alias
        )
    dirty_tree_pressure_payload = None
    if dirty_tree_pressure is not None:
        dirty_tree_pressure_payload = (
            dirty_tree_pressure
            if bool(getattr(args, "full", False))
            else _legacy_dirty_tree_bankruptcy_pressure_cli_pointer(
                dirty_tree_pressure
            )
        )
    return _print(
        {
            "schema": "work_ledger_sweep_report_v1",
            "dry_run": bool(args.dry_run),
            "orphan_sweep_after_hours": orphan_after.total_seconds() / 3600.0,
            "claim_expiry": expiry,
            "orphan_sessions": orphans,
            **(
                {"dirty_tree_bankruptcy_pressure": dirty_tree_pressure_payload}
                if dirty_tree_pressure_payload is not None
                else {}
            ),
            **(
                {"dirty_tree_pressure": dirty_tree_pressure_alias}
                if dirty_tree_pressure_alias is not None
                else {}
            ),
            **(
                {"duplicate_claim_dedupe": duplicate_claim_dedupe}
                if duplicate_claim_dedupe is not None
                else {}
            ),
        }
    )


def _compact_dirty_tree_pressure_alias_cli_payload(
    payload: Mapping[str, Any],
) -> Dict[str, Any]:
    compact = {
        key: payload.get(key)
        for key in (
            "schema",
            "alias_of",
            "output_profile",
            "authority_boundary",
            "safety_authority",
            "bankruptcy_authorized",
            "dirty_scan_status",
            "dirty_total",
            "class_counts",
            "dirty_path_class_counts",
            "operator_authorized_mainline_checkpoint",
            "operator_authorized_unclaimed_checkpoint",
            "containment_plan",
            "blocked_residual_count",
            "next_safe_action",
            "full_card_command",
        )
        if payload.get(key) not in (None, "", [], {})
    }
    compact["omission_receipt"] = {
        "omitted": [
            "nested path previews",
            "containment plan detail",
            "claim collision action rows",
            "repeat policy detail",
            "command map",
        ],
        "reason": (
            "session-sweep compact output keeps the legacy "
            "dirty_tree_bankruptcy_pressure key as a pointer; the alias carries "
            "the handle-sized first-action fields."
        ),
        "drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py "
            "session-sweep --dry-run --dirty-tree-pressure --full"
        ),
    }
    return compact


def _legacy_dirty_tree_bankruptcy_pressure_cli_pointer(
    payload: Mapping[str, Any],
) -> Dict[str, Any]:
    class_counts = (
        payload.get("class_counts")
        or payload.get("dirty_path_class_counts")
        or {}
    )
    checkpoint = payload.get("operator_authorized_mainline_checkpoint")
    mainline_checkpoint_status = (
        checkpoint.get("status") if isinstance(checkpoint, Mapping) else None
    )
    unclaimed_checkpoint = payload.get("operator_authorized_unclaimed_checkpoint")
    unclaimed_checkpoint_status = (
        unclaimed_checkpoint.get("status")
        if isinstance(unclaimed_checkpoint, Mapping)
        else None
    )
    available_checkpoint_lane = None
    checkpoint_command = None
    if mainline_checkpoint_status == "available":
        available_checkpoint_lane = "mainline"
        checkpoint_command = (
            checkpoint.get("command") if isinstance(checkpoint, Mapping) else None
        )
    elif unclaimed_checkpoint_status == "available":
        available_checkpoint_lane = "unclaimed"
        checkpoint_command = (
            unclaimed_checkpoint.get("command")
            if isinstance(unclaimed_checkpoint, Mapping)
            else None
        )
    checkpoint_status = (
        "available"
        if available_checkpoint_lane is not None
        else mainline_checkpoint_status
    )
    return {
        "schema": payload.get("schema") or "dirty_tree_bankruptcy_pressure_v0",
        "output_profile": "legacy_pointer",
        "alias_of": "dirty_tree_pressure",
        "authority_boundary": payload.get("authority_boundary"),
        "safety_authority": payload.get("safety_authority"),
        "bankruptcy_authorized": payload.get("bankruptcy_authorized"),
        "dirty_scan_status": payload.get("dirty_scan_status"),
        "dirty_total": payload.get("dirty_total"),
        "class_counts": class_counts,
        "dirty_path_class_counts": class_counts,
        "checkpoint_status": checkpoint_status,
        "mainline_checkpoint_status": mainline_checkpoint_status,
        "unclaimed_checkpoint_status": unclaimed_checkpoint_status,
        "available_checkpoint_lane": available_checkpoint_lane,
        "checkpoint_command": checkpoint_command,
        "next_safe_action": payload.get("next_safe_action"),
        "full_card_command": (
            "./repo-python tools/meta/factory/work_ledger.py "
            "session-sweep --dry-run --dirty-tree-pressure --full"
        ),
        "omission_receipt": {
            "omitted": [
                "checkpoint detail",
                "dirty path class previews",
                "active claim group previews",
                "containment plan",
                "policy detail",
                "command map",
            ],
            "reason": (
                "Default session-sweep emits dirty_tree_pressure as the compact "
                "first-action card; the legacy bankruptcy key is retained as a "
                "small compatibility pointer."
            ),
            "compact_alias_key": "dirty_tree_pressure",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                "session-sweep --dry-run --dirty-tree-pressure --full"
            ),
        },
    }


def _compact_duplicate_claim_dedupe_cli_payload(
    payload: Mapping[str, Any],
    *,
    released_limit: int,
) -> Dict[str, Any]:
    compact = dict(payload)
    released = compact.pop("released", None)
    if not isinstance(released, list):
        return compact
    safe_limit = max(0, int(released_limit or 0))
    released_preview = released[:safe_limit] if safe_limit else []
    compact["released_preview"] = released_preview
    compact["released_omitted"] = max(0, len(released) - len(released_preview))
    compact["released_detail_omitted"] = True
    compact["full_output_hint"] = (
        "./repo-python tools/meta/factory/work_ledger.py session-sweep "
        "--dedupe-duplicate-claims --full"
    )
    return compact


def cmd_append_open(args: argparse.Namespace) -> int:
    _require_receipt(args)
    result = work_ledger.open_thread(
        REPO_ROOT,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        title=args.title,
        body=args.body,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[str(result["event"]["td_id"])],
        event_ids=[str(result["event"]["event_id"])],
    )
    td_id = str(result["event"]["td_id"])
    try:
        result["runtime_claim"] = work_ledger_runtime.claim_work_thread(
            REPO_ROOT,
            session_id=args.actor_session_id,
            td_id=td_id,
            note="append-open auto-claim for same-session follow-up mutation",
        )
    except Exception as exc:
        result["runtime_claim"] = {
            "schema": "work_ledger_append_open_runtime_claim_v1",
            "status": "claim_failed",
            "td_id": td_id,
            "session_id": args.actor_session_id,
            "reason": str(exc),
            "repair_route": "Run session-claim --td-id for this actor_session_id, then retry close/supersede/reopen.",
        }
    return _print(result)


def cmd_progress(args: argparse.Namespace) -> int:
    try:
        _require_receipt(args)
    except ValueError as exc:
        _read_receipt_error_exit(
            command="progress",
            operation="progress_note",
            args=args,
            error=exc,
        )
    target_id = str(args.td_id or "").strip()
    if not work_ledger.TD_ID_RE.fullmatch(target_id):
        _verify_work_item_claim_or_bypass(
            args,
            operation="work_item_progress_note",
            allow_unclaimed_note=True,
        )
        metadata = _metadata_from_args(args)
        bridge = metadata.setdefault("task_ledger_work_item_bridge", {})
        if not isinstance(bridge, dict):
            raise SystemExit("metadata_json.task_ledger_work_item_bridge must be an object when present")
        bridge.update(
            {
                "receipt_mode": "task_ledger_work_item_progress",
                "task_ledger_work_item_id": target_id,
                "requested_work_ledger_td_id": target_id,
            }
        )
        result = work_ledger.open_thread(
            REPO_ROOT,
            actor=args.actor,
            actor_session_id=args.actor_session_id,
            phase_id=args.phase_id,
            family_id=args.family_id,
            title=args.title or f"Task Ledger progress: {target_id}",
            body=args.body,
            evidence_refs=args.evidence_ref,
            read_receipt_id=args.read_receipt_id,
            metadata=metadata,
            projection_mode="append_open_target_only",
        )
        work_ledger_runtime.mark_ledger_append(
            REPO_ROOT,
            read_receipt_id=args.read_receipt_id,
            session_id=args.actor_session_id,
            work_item_ids=[target_id],
            event_ids=[str(result["event"]["event_id"])],
        )
        generated_td_id = str(result["event"]["td_id"])
        try:
            result["runtime_claim"] = work_ledger_runtime.claim_work_thread(
                REPO_ROOT,
                session_id=args.actor_session_id,
                td_id=generated_td_id,
                note="work-item progress auto-claim for same-session close",
            )
        except Exception as exc:
            result["runtime_claim"] = {
                "schema": "work_ledger_work_item_progress_runtime_claim_v1",
                "status": "claim_failed",
                "td_id": generated_td_id,
                "work_item_id": target_id,
                "session_id": args.actor_session_id,
                "reason": str(exc),
                "repair_route": (
                    "Run session-claim --td-id for the generated Work Ledger td_id, "
                    "then retry close/supersede/reopen."
                ),
            }
        result["work_item_bridge"] = dict(bridge)
        result["generated_td_id"] = generated_td_id
        resolution_kind, resolution_ref, resolution_label = _progress_bridge_resolution_hint(args)
        result["next_claim_command"] = (
            "./repo-python tools/meta/factory/work_ledger.py session-claim "
            f"--session-id {shlex.quote(str(args.actor_session_id))} "
            f"--td-id {shlex.quote(generated_td_id)} "
            "--lease-minutes 30 "
            "--note 'Claim generated Work Ledger receipt for closeout'"
        )
        result["next_close_command"] = (
            "./repo-python tools/meta/factory/work_ledger.py close "
            f"--actor {shlex.quote(str(args.actor))} "
            f"--actor-session-id {shlex.quote(str(args.actor_session_id))} "
            f"--phase-id {shlex.quote(str(args.phase_id))} "
            f"--family-id {shlex.quote(str(args.family_id))} "
            f"--read-receipt-id {shlex.quote(str(args.read_receipt_id))} "
            f"--td-id {shlex.quote(generated_td_id)} "
            f"--resolution-kind {shlex.quote(resolution_kind)} "
            f"--resolution-ref {shlex.quote(resolution_ref)} "
            f"--resolution-label {shlex.quote(resolution_label)}"
        )
        result["repair_route"] = (
            "Use next_claim_command if the generated td_id claim is missing, then "
            "use next_close_command with the generated Work Ledger td_id; do not "
            "pass the original Task Ledger WorkItem id to close."
        )
        return _print(result)

    _verify_thread_claim_or_bypass(args, operation="progress_note", allow_unclaimed_note=True)
    result = work_ledger.progress_thread(
        REPO_ROOT,
        td_id=target_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        body=args.body,
        title=args.title,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[target_id],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_close(args: argparse.Namespace) -> int:
    _require_receipt(args)
    _verify_thread_claim_or_bypass(args, operation="todo_close")
    result = work_ledger.close_thread(
        REPO_ROOT,
        td_id=args.td_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        resolution_episode=_resolution_episode_from_args(args),
        body=args.body,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[args.td_id],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_supersede(args: argparse.Namespace) -> int:
    _require_receipt(args)
    _verify_thread_claim_or_bypass(args, operation="todo_supersede")
    result = work_ledger.supersede_thread(
        REPO_ROOT,
        td_id=args.td_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        title=args.title,
        resolution_episode=_resolution_episode_from_args(args),
        body=args.body,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[args.td_id, str(result.get("successor_td_id") or "")],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_reopen(args: argparse.Namespace) -> int:
    _require_receipt(args)
    _verify_thread_claim_or_bypass(args, operation="todo_reopen")
    result = work_ledger.reopen_thread(
        REPO_ROOT,
        td_id=args.td_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        body=args.body,
        title=args.title,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[args.td_id],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_project(args: argparse.Namespace) -> int:
    if args.all and args.target_only:
        raise SystemExit("--target-only cannot be used with --all")
    if args.check:
        if args.all:
            return _print(work_ledger.check_project_all(REPO_ROOT))
        return _print(
            work_ledger.check_project_phase(
                REPO_ROOT,
                phase_id=args.phase_id,
                family_id=args.family_id,
                target_only=bool(args.target_only),
            )
        )
    if args.all:
        return _print(work_ledger.project_all(REPO_ROOT))
    payload = work_ledger.project_phase(
        REPO_ROOT,
        phase_id=args.phase_id,
        family_id=args.family_id,
        target_only=bool(args.target_only),
    )
    if args.target_only and not args.full:
        payload = _compact_target_only_project_payload(payload)
    return _print(payload)


def _compact_target_only_project_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    compact = dict(payload)
    projection = compact.pop("projection", None)
    if not isinstance(projection, Mapping):
        return compact

    threads = projection.get("threads")
    compact["projection_summary"] = {
        "schema": projection.get("schema"),
        "generated_at": projection.get("generated_at"),
        "phase_id": projection.get("phase_id") or compact.get("phase_id"),
        "family_id": projection.get("family_id") or compact.get("family_id"),
        "counts": projection.get("counts"),
        "thread_count": len(threads) if isinstance(threads, Mapping) else None,
    }
    compact["omission_receipt"] = {
        "omitted": ["projection"],
        "reason": (
            "project --target-only CLI output omits the full Work Ledger index "
            "body by default; projection_results and projection_summary retain "
            "refresh status and counts."
        ),
        "drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py project "
            "--target-only --full"
        ),
    }
    return compact


def cmd_query(args: argparse.Namespace) -> int:
    if args.read_receipt_id:
        work_ledger_runtime.mark_ledger_query(
            REPO_ROOT,
            read_receipt_id=args.read_receipt_id,
            session_id=args.actor_session_id,
            td_id=args.td_id,
        )
    payload = work_ledger.query_recipe(
        REPO_ROOT,
        recipe=args.recipe,
        phase_id=args.phase_id,
        family_id=args.family_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        td_id=args.td_id,
        limit=args.limit,
    )
    return _print(payload)


def cmd_agent_seed_handoffs(args: argparse.Namespace) -> int:
    if args.live:
        _require_receipt(args)
    payload = agent_seed_handoffs.extract_agent_seed_handoffs(
        REPO_ROOT,
        family_id=args.family_id,
        since_date=args.since_date,
        limit=args.limit,
        include_imported=bool(args.include_imported),
    )
    opened: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    if args.live:
        for candidate in payload.get("candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            if candidate.get("imported"):
                skipped.append(
                    {
                        "candidate_id": candidate.get("candidate_id"),
                        "reason": "already_imported",
                        "existing_td_id": candidate.get("existing_td_id"),
                    }
                )
                continue
            result = work_ledger.open_thread(
                REPO_ROOT,
                actor=args.actor,
                actor_session_id=args.actor_session_id,
                phase_id=args.phase_id,
                family_id=args.family_id,
                title=str(candidate.get("title") or "Agent-seed handoff"),
                body=str(candidate.get("body") or ""),
                evidence_refs=list(candidate.get("evidence_refs") or []),
                read_receipt_id=args.read_receipt_id,
                metadata=dict(candidate.get("metadata") or {}),
            )
            opened.append(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "td_id": result["event"]["td_id"],
                    "event_id": result["event"]["event_id"],
                    "title": result["event"].get("title"),
                }
            )
        if opened:
            work_ledger_runtime.mark_ledger_append(
                REPO_ROOT,
                read_receipt_id=args.read_receipt_id,
                session_id=args.actor_session_id,
                td_ids=[str(row.get("td_id")) for row in opened if row.get("td_id")],
                event_ids=[str(row.get("event_id")) for row in opened if row.get("event_id")],
            )
        payload = {
            **payload,
            "live": True,
            "opened_count": len(opened),
            "opened": opened,
            "skipped": skipped,
        }
    else:
        payload = {**payload, "live": False}
    return _print(payload)


def _add_common_mutation_args(
    parser: argparse.ArgumentParser,
    *,
    require_td_id: bool = False,
    allow_unclaimed_note_arg: bool = False,
) -> None:
    parser.add_argument("--actor", default=None)
    parser.add_argument("--actor-session-id", default=None)
    parser.add_argument("--phase-id", default=None)
    parser.add_argument("--family-id", default=None)
    parser.add_argument("--read-receipt-id", required=True)
    parser.add_argument("--title", default=None)
    parser.add_argument("--body", default=None,
                        help="Inline body text. Mutually exclusive with --body-file and --body-stdin.")
    parser.add_argument("--body-file", default=None,
                        help="Read body from a UTF-8 file. Closeout bodies are governance evidence; "
                             "this avoids shell command-substitution corruption of inline text.")
    parser.add_argument("--body-stdin", action="store_true",
                        help="Read body from stdin (UTF-8). Mutually exclusive with --body and --body-file.")
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--metadata-json", default=None)
    if require_td_id:
        parser.add_argument(
            "--td-id",
            required=True,
            help=(
                "Work Ledger td_* thread id. For progress/note only, a claimed Task Ledger "
                "WorkItem id such as cap_* is accepted and converted into a linked open receipt."
            ),
        )
    if allow_unclaimed_note_arg:
        parser.add_argument(
            "--allow-unclaimed-note",
            action="store_true",
            help=(
                "Explicitly allow a low-blast progress/note append without an active td_id "
                "claim; writes warning metadata."
            ),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified work ledger CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--phase-id", default=None)
    bootstrap.add_argument("--family-id", default=None)
    bootstrap.set_defaults(func=cmd_bootstrap)

    session_bootstrap = subparsers.add_parser(
        "session-bootstrap",
        aliases=["session-start"],
        help="Bootstrap a Work Ledger session; session-start is a compatibility alias.",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_bootstrap.add_argument("--session-id", required=True)
    session_bootstrap.add_argument("--actor", default="codex")
    session_bootstrap.add_argument("--phase-id", default=None)
    session_bootstrap.add_argument("--family-id", default=None)
    session_bootstrap.add_argument("--limit", type=int, default=work_ledger_runtime.BOOTSTRAP_SLICE_LIMIT)
    session_bootstrap.add_argument("--full", action="store_true", help="Print the full bootstrap payload.")
    session_bootstrap.set_defaults(func=cmd_session_bootstrap)

    session_activity = subparsers.add_parser("session-activity")
    session_activity.add_argument("--session-id", required=True)
    session_activity.add_argument("--action", required=True)
    session_activity.add_argument("--td-id", default=None)
    session_activity.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help="Limit compact overview rows included in the lifecycle result.",
    )
    session_activity.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_activity.set_defaults(func=cmd_session_activity)

    session_heartbeat = subparsers.add_parser(
        "session-heartbeat",
        aliases=["heartbeat"],
        help=(
            "Write a bounded public now/done pass heartbeat for one live session; "
            "heartbeat is a compatibility alias."
        ),
        epilog=f"{SERIAL_MUTATION_HELP} {HEARTBEAT_PARTICIPATION_HELP}",
    )
    session_heartbeat.add_argument("--session-id", required=True)
    session_heartbeat.add_argument(
        "--state",
        "--status",
        dest="state",
        default="inspecting",
        help=_heartbeat_state_help(),
    )
    session_heartbeat.add_argument(
        "--current-pass-line",
        "--now",
        "--note",
        dest="current_pass_line",
        default=None,
        help=f"Public one-sentence current pass line, <= {work_ledger_runtime.PASS_CURRENT_LINE_LIMIT} chars.",
    )
    session_heartbeat.add_argument(
        "--last-pass-result-line",
        "--done",
        dest="last_pass_result_line",
        default=None,
        help=f"Public one-sentence previous pass result, <= {work_ledger_runtime.PASS_RESULT_LINE_LIMIT} chars.",
    )
    session_heartbeat.add_argument(
        "--clip-lines",
        action="store_true",
        help=(
            "Trim --now/--done text to heartbeat public line limits before "
            "runtime validation. Default is strict rejection."
        ),
    )
    session_heartbeat.add_argument("--td-id", "--work-item-id", dest="td_id", default=None)
    session_heartbeat.add_argument(
        "--scope-ref",
        action="append",
        default=[],
        help="Bounded public scope/evidence ref such as a path, claim id, or receipt. Repeatable.",
    )
    session_heartbeat.add_argument("--pass-id", default=None)
    session_heartbeat.add_argument(
        "--source",
        default="manual_cli",
        choices=sorted(work_ledger_runtime.PASS_HEARTBEAT_SOURCES),
    )
    session_heartbeat.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help="Limit compact overview rows included in the lifecycle result.",
    )
    session_heartbeat.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_heartbeat.set_defaults(func=cmd_session_heartbeat)

    session_finalize = subparsers.add_parser(
        "session-finalize",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_finalize.add_argument("--session-id", required=True)
    session_finalize.add_argument("--action", default="session-end")
    session_finalize.add_argument(
        "--read-receipt-id",
        default="",
        help="Live session read receipt; required when recording append-exempt closeout.",
    )
    session_finalize.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help="Limit compact overview rows included in the lifecycle result.",
    )
    session_finalize.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_finalize.add_argument(
        "--no-release-claims",
        action="store_true",
        help="Diagnostic escape hatch: finalize the session without releasing its active claims.",
    )
    session_finalize.add_argument(
        "--allow-missing-append",
        action="store_true",
        help=(
            "Diagnostic escape hatch only: allow finalizing a touched session that "
            "has not written a Work Ledger append; this marks the session stale. "
            "Normal closeout should append Work Ledger evidence first or use "
            "--append-exempt-reason with --read-receipt-id and --append-exempt-ref."
        ),
    )
    session_finalize.add_argument(
        "--append-exempt-reason",
        default="",
        help=(
            "Record a non-stale append-exempt closeout for commit-only or "
            "projection-only sessions before finalizing. Requires --read-receipt-id."
        ),
    )
    session_finalize.add_argument(
        "--append-exempt-ref",
        action="append",
        default=[],
        help="Evidence ref for append-exempt closeout, such as a commit hash or receipt id.",
    )
    session_finalize.add_argument(
        "--append-exempt-td-id",
        action="append",
        default=[],
        help="Optional td_* touched by the append-exempt closeout.",
    )
    session_finalize.add_argument(
        "--append-exempt-work-item-id",
        action="append",
        default=[],
        help="Optional Task Ledger WorkItem id touched by the append-exempt closeout.",
    )
    session_finalize.add_argument(
        "--require-post-commit-containment",
        action="store_true",
        help=(
            "For append-exempt commit closeout, require the cited commit to be "
            "contained in current HEAD and every declared scope to be unchanged "
            "and clean before marking the session append-exempt or releasing claims."
        ),
    )
    session_finalize.add_argument(
        "--post-commit-containment-commit",
        default="",
        help=(
            "Commit/ref to verify for post-commit containment; defaults to the "
            "first commit:* --append-exempt-ref, or a raw unprefixed append-exempt ref."
        ),
    )
    session_finalize.add_argument(
        "--post-commit-containment-scope",
        action="append",
        default=[],
        help=(
            "Owned path scope that must remain unchanged in HEAD and clean in the "
            "worktree before append-exempt commit finalization. Repeatable."
        ),
    )
    session_finalize.set_defaults(func=cmd_session_finalize)

    session_status = subparsers.add_parser(
        "session-status",
        aliases=["overview", "status"],
        help="Print Work Ledger session status; overview/status are aliases.",
    )
    session_status.add_argument(
        "--json",
        action="store_true",
        help="Compatibility no-op; session-status output is already JSON.",
    )
    session_status.add_argument(
        "--overview",
        action="store_true",
        help="Print the cards-only multi-agent session overview. This is the default.",
    )
    session_status.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_status.add_argument(
        "--with-session-cards",
        action="store_true",
        help="Include detailed compact session cards in overview output.",
    )
    session_status.add_argument(
        "--cards-only",
        action="store_true",
        help="Compatibility no-op; default overview already omits session row arrays.",
    )
    session_status.add_argument(
        "--detail",
        choices=["compact", "full"],
        default="compact",
        help="Compatibility selector; compact is the default and full maps to --full.",
    )
    session_status.add_argument(
        "--seed-speed",
        action="store_true",
        help="Print the tiny active-seed coordination packet: claim sessions, heartbeat counts, risks, and drilldowns.",
    )
    session_status.add_argument(
        "--speed-only",
        action="store_true",
        help="Alias for --seed-speed.",
    )
    session_status.add_argument(
        "--no-heartbeat",
        action="store_true",
        help=(
            "For --seed-speed, promote the non-heartbeat coordination lane to "
            "first_action when heartbeat repair would otherwise be first."
        ),
    )
    session_status.add_argument(
        "--dirty-tree-pressure",
        action="store_true",
        help=(
            "For --seed-speed, include a compact dirty-tree pressure focus; "
            "--no-heartbeat enables this automatically."
        ),
    )
    session_status.add_argument(
        "--bankruptcy-authorized",
        action="store_true",
        help=(
            "For --seed-speed --dirty-tree-pressure, evaluate the broad checkpoint "
            "guard as operator-authorized while still remaining read-only."
        ),
    )
    session_status.add_argument(
        "--session-id",
        default="",
        help="Print one bounded session card; combine with --full for that session only.",
    )
    session_status.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit compact overview rows; with --full, use --session-id for bounded diagnostics.",
    )
    session_status.set_defaults(func=cmd_session_status)

    list_sessions = subparsers.add_parser(
        "list-sessions",
        help=(
            "Compatibility alias for agents that expect a list-sessions probe; "
            "returns bounded session-status rows with optional actor/status filters."
        ),
    )
    list_sessions.add_argument(
        "--json",
        action="store_true",
        help="Compatibility no-op; output is already JSON.",
    )
    list_sessions.add_argument("--actor", default=None)
    list_sessions.add_argument(
        "--status",
        dest="session_state_filter",
        choices=["active", "ended", "closed", "stale", "all"],
        default="active",
        help="Compatibility status filter. active means not ended.",
    )
    list_sessions.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
    )
    list_sessions.set_defaults(func=cmd_list_sessions)

    session_claims = subparsers.add_parser(
        "session-claims",
        help="Print the compact active-claims snapshot without expanding session cards.",
    )
    session_claims.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
    )
    session_claims.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild the active-claims snapshot from runtime_status.json before printing it.",
    )
    session_claims.add_argument(
        "--allow-stale",
        action="store_true",
        help="Print a stale snapshot with source-freshness metadata instead of suppressing rows.",
    )
    session_claims.add_argument(
        "--path",
        action="append",
        default=[],
        help=(
            "Filter active claims to repo paths that overlap this path. Repeatable; "
            "works with compact, --full, and --session-summary output."
        ),
    )
    session_claims.add_argument(
        "--session-id",
        action="append",
        default=[],
        help=(
            "Filter active claims to owner session ids. Repeatable; works with "
            "compact, --full, and --session-summary output."
        ),
    )
    session_claims.add_argument(
        "--full",
        action="store_true",
        help="Print full claim rows, notes, source receipts, and nested collision details.",
    )
    session_claims.add_argument(
        "--session-summary",
        action="store_true",
        help="Group active claims into compact owner-session cards for lane selection.",
    )
    session_claims.add_argument(
        "--cards-only",
        action="store_true",
        help="Compatibility no-op: compact cards are the default output.",
    )
    session_claims.set_defaults(func=cmd_session_claims)

    session_import_codex = subparsers.add_parser(
        "session-import-codex",
        help="Import recently updated local Codex threads as runtime-only work-ledger sessions.",
    )
    session_import_codex.add_argument("--actor", default="codex")
    session_import_codex.add_argument("--phase-id", default=None)
    session_import_codex.add_argument("--family-id", default=None)
    session_import_codex.add_argument("--since-minutes", type=float, default=60.0)
    session_import_codex.add_argument("--limit", type=int, default=20)
    session_import_codex.add_argument("--db-path", default=None)
    session_import_codex.add_argument("--include-all-cwds", action="store_true")
    session_import_codex.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview candidate Codex threads without mutating runtime_status.json.",
    )
    session_import_codex.set_defaults(func=cmd_session_import_codex)

    session_import_host = subparsers.add_parser(
        "session-import-host-surfaces",
        help="Import visible Codex threads plus Claude IDE locks as runtime-only coordination sessions.",
    )
    session_import_host.add_argument("--phase-id", default=None)
    session_import_host.add_argument("--family-id", default=None)
    session_import_host.add_argument("--since-minutes", type=float, default=60.0)
    session_import_host.add_argument("--limit", type=int, default=20)
    session_import_host.add_argument("--overview-limit", type=int, default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT)
    session_import_host.add_argument("--db-path", default=None)
    session_import_host.add_argument("--include-all-cwds", action="store_true")
    session_import_host.add_argument("--include-all-workspaces", action="store_true")
    session_import_host.add_argument("--skip-codex", action="store_true")
    session_import_host.add_argument("--skip-claude", action="store_true")
    session_import_host.add_argument("--dry-run", action="store_true")
    session_import_host.set_defaults(func=cmd_session_import_host_surfaces)

    mutation_check = subparsers.add_parser(
        "mutation-check",
        help="Check requested paths/write profiles against active path claims without mutating runtime state.",
    )
    mutation_check.add_argument("--session-id", default=None)
    mutation_check.add_argument("--path", action="append", default=[])
    mutation_check.add_argument(
        "--write-profile",
        action="append",
        choices=sorted(WRITE_PROFILE_PATHS),
        default=[],
    )
    mutation_check.add_argument("--require-exclusive", action="store_true")
    mutation_check.set_defaults(func=cmd_mutation_check)

    helper_lease_admission = subparsers.add_parser(
        "helper-lease-admission",
        help=(
            "Gate a proposed persistent helper/tool lease through the host-pressure "
            "budget before starting another MCP/Codex helper process."
        ),
    )
    helper_lease_admission.add_argument(
        "--lease-kind",
        required=True,
        choices=work_admission.HELPER_LEASE_KINDS,
    )
    helper_lease_admission.add_argument("--request-id", default=None)
    helper_lease_admission.add_argument("--requested-by", default=None)
    helper_lease_admission.add_argument("--owner-status", default="unknown")
    helper_lease_admission.add_argument("--current-lease-count", type=int, default=None)
    helper_lease_admission.add_argument(
        "--host-pressure-policy",
        choices=work_admission.ADMISSION_POLICY_VALUES,
        default=os.environ.get("AIW_HELPER_LEASE_HOST_PRESSURE_POLICY", "auto"),
        help=(
            "Admission policy before allocating a persistent helper lease: auto queues "
            "under degraded pressure, warn reports but admits, off disables the gate."
        ),
    )
    helper_lease_admission.set_defaults(func=cmd_helper_lease_admission)

    dev_resource_admission = subparsers.add_parser(
        "dev-resource-admission",
        help=(
            "Gate frontend/backend/browser/test/build resources through the "
            "resource broker before starting another long-lived dev service."
        ),
    )
    dev_resource_admission.add_argument(
        "--resource-kind",
        required=True,
        choices=work_admission.DEV_RESOURCE_KINDS,
    )
    dev_resource_admission.add_argument("--fingerprint-json", default="{}")
    dev_resource_admission.add_argument("--existing-lease-json", action="append", default=[])
    dev_resource_admission.add_argument("--request-id", default=None)
    dev_resource_admission.add_argument("--requested-by", default=None)
    dev_resource_admission.add_argument("--user-facing", action="store_true")
    dev_resource_admission.add_argument("--exclusive-required", action="store_true")
    dev_resource_admission.add_argument("--unsafe-host-or-proxy", action="store_true")
    dev_resource_admission.add_argument(
        "--host-pressure-policy",
        choices=work_admission.ADMISSION_POLICY_VALUES,
        default=os.environ.get("AIW_DEV_RESOURCE_HOST_PRESSURE_POLICY", "auto"),
        help=(
            "Admission policy before allocating a long-lived dev resource: auto queues "
            "new starts under pressure, warn reports but admits, off disables the gate."
        ),
    )
    dev_resource_admission.set_defaults(func=cmd_dev_resource_admission)

    concurrency_pathology_index = subparsers.add_parser(
        "concurrency-pathology-index",
        help=(
            "Print concurrency_pathology_index_v1: a generated operating picture "
            "over claims, CAP pressure, ledger settlement, resources, closeout, "
            "host pressure, exact-copy lanes, and Git bankruptcy."
        ),
    )
    concurrency_pathology_index.add_argument(
        "--family",
        dest="families",
        action="append",
        default=[],
        help="Filter emitted rows to a pathology family. Repeatable.",
    )
    concurrency_pathology_index.add_argument(
        "--skip-host-pressure",
        action="store_true",
        help="Avoid sampling the host-pressure read model; useful for fast tests.",
    )
    concurrency_pathology_index.add_argument(
        "--write",
        action="store_true",
        help="Write the generated projection to state/work_ledger/concurrency_pathology_index.json.",
    )
    concurrency_pathology_index.set_defaults(func=cmd_concurrency_pathology_index)

    exact_copy_settlement_item = subparsers.add_parser(
        "exact-copy-settlement-item",
        help=(
            "Build an exact_copy_settlement_item_v1 with source/target digests, "
            "claim owner, release condition, and dry-run repair command."
        ),
    )
    exact_copy_settlement_item.add_argument("--source-path", required=True)
    exact_copy_settlement_item.add_argument("--target-path", required=True)
    exact_copy_settlement_item.add_argument("--active-claim-owner", default=None)
    exact_copy_settlement_item.add_argument("--dependency-release-condition", default=None)
    exact_copy_settlement_item.add_argument("--dry-run-repair-command", default=None)
    exact_copy_settlement_item.add_argument("--settlement-group-id", default=None)
    exact_copy_settlement_item.set_defaults(func=cmd_exact_copy_settlement_item)

    resident_pressure_relief = subparsers.add_parser(
        "resident-pressure-relief",
        help=(
            "Record a resident-pressure relief attempt: owner-release result, "
            "optional background-loop downshift, and recovery-window verdict."
        ),
    )
    resident_pressure_relief.add_argument(
        "--process-kind",
        required=True,
        choices=work_admission.HELPER_LEASE_KINDS,
    )
    resident_pressure_relief.add_argument("--owner-status", default="unknown")
    resident_pressure_relief.add_argument("--target-owner", default=None)
    resident_pressure_relief.add_argument("--rss-mb-total", type=float, default=None)
    resident_pressure_relief.add_argument(
        "--pressure-mode",
        choices=("normal", "degraded", "relief_window", "recovery_monitoring", "unknown"),
        default="degraded",
    )
    resident_pressure_relief.add_argument(
        "--owner-release-result",
        choices=work_admission.OWNER_RELEASE_RESULT_VALUES,
        default="unsupported",
    )
    resident_pressure_relief.add_argument("--result-note", default=None)
    resident_pressure_relief.add_argument(
        "--background-loop-kind",
        choices=work_admission.BACKGROUND_LOOP_KINDS,
        default=None,
    )
    resident_pressure_relief.add_argument("--owner-surface", default=None)
    resident_pressure_relief.add_argument(
        "--background-loop-result",
        choices=work_admission.BACKGROUND_DOWNSHIFT_RESULTS,
        default="unsupported",
    )
    resident_pressure_relief.add_argument("--duration-s", type=int, default=600)
    resident_pressure_relief.add_argument("--effective-interval-s", type=float, default=15.0)
    resident_pressure_relief.add_argument(
        "--apply-background-downshift",
        action="store_true",
        help=(
            "Write the background-loop downshift receipt to the resident state file. "
            "Current consumers only downshift known loops such as agent_observability_sampler."
        ),
    )
    resident_pressure_relief.add_argument("--blocked-work-starts", type=int, default=0)
    resident_pressure_relief.add_argument("--blocked-helper-leases", type=int, default=0)
    resident_pressure_relief.add_argument("--workload-mix-changed", action="store_true")
    resident_pressure_relief.add_argument(
        "--spend-resident-thread-relief",
        action="store_true",
        help=(
            "Scan resident Work Ledger threads and convert safe nap/yield "
            "recommendations into owner-visible session-yield request receipts."
        ),
    )
    resident_pressure_relief.add_argument(
        "--apply-session-yield-requests",
        action="store_true",
        help=(
            "Append resident-thread yield requests to state/performance/session_yield_requests.jsonl. "
            "Without this flag the spender is a dry-run receipt."
        ),
    )
    resident_pressure_relief.add_argument(
        "--resident-thread-request-limit",
        type=int,
        default=5,
        help="Maximum resident nap/yield requests to emit or append.",
    )
    resident_pressure_relief.add_argument(
        "--resident-thread-scan-limit",
        type=int,
        default=100,
        help=(
            "Maximum resident governor rows to scan; keep higher than the display "
            "limit so terminate-grace rows do not hide spendable nap/yield rows."
        ),
    )
    resident_pressure_relief.add_argument(
        "--resident-thread-existing-request-scan-limit",
        type=int,
        default=1000,
        help=(
            "Tail size for detecting existing pending session-yield requests before "
            "appending another resident-thread request for the same target."
        ),
    )
    resident_pressure_relief.add_argument(
        "--resident-thread-pending-ttl-s",
        type=int,
        default=work_admission.RESIDENT_RELIEF_PENDING_TTL_S,
        help=(
            "Age after which an unanswered resident session-yield request is "
            "reported as stale and routed to recheck/escalation, not duplicated."
        ),
    )
    resident_pressure_relief.add_argument(
        "--resident-thread-warm-after-minutes",
        type=float,
        default=10.0,
        help="Quiet threshold for resident nap/yield request candidates.",
    )
    resident_pressure_relief.add_argument(
        "--resident-thread-terminate-after-minutes",
        type=float,
        default=30.0,
        help="Terminate-grace threshold; terminate rows are skipped by this spender.",
    )
    resident_pressure_relief.add_argument(
        "--resident-thread-request-result",
        choices=work_admission.SESSION_YIELD_RESULTS,
        default="requested",
        help="Result to stamp on generated resident-thread session-yield requests.",
    )
    resident_pressure_relief.add_argument(
        "--skip-resident-thread-recheck",
        dest="resident_thread_recheck",
        action="store_false",
        default=True,
        help="Skip the post-spend host-pressure sample.",
    )
    resident_pressure_relief.set_defaults(func=cmd_resident_pressure_relief)

    resident_thread_governor = subparsers.add_parser(
        "resident-thread-governor",
        help=(
            "Dry-run stale resident thread governor: classify active Work Ledger "
            "sessions into keep/yield/nap/terminate-grace/archive recommendations."
        ),
    )
    resident_thread_governor.add_argument(
        "--pressure-mode",
        choices=("normal", "degraded", "relief_window", "recovery_monitoring", "unknown"),
        default="degraded",
    )
    resident_thread_governor.add_argument(
        "--warm-after-minutes",
        type=float,
        default=10.0,
        help="Quiet threshold for yield/nap recommendations.",
    )
    resident_thread_governor.add_argument(
        "--terminate-after-minutes",
        type=float,
        default=30.0,
        help="Quiet threshold for unclaimed terminate-grace recommendations.",
    )
    resident_thread_governor.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help="Maximum governor rows to print.",
    )
    resident_thread_governor.set_defaults(func=cmd_resident_thread_governor)

    session_yield_request = subparsers.add_parser(
        "session-yield-request",
        help=(
            "Append a non-destructive owner-visible yield/release request for "
            "already-resident pressure. This is a request bus, not a kill lane."
        ),
    )
    session_yield_request.add_argument("--target-session-id", required=True)
    session_yield_request.add_argument("--request-id", default=None)
    session_yield_request.add_argument(
        "--target-class",
        choices=(
            "idle_session",
            "low_progress_session",
            "high_helper_footprint_session",
            "background_loop_owner",
            "settlement_obligation_owner",
            "projection_refresh_owner",
        ),
        default="high_helper_footprint_session",
    )
    session_yield_request.add_argument(
        "--requested-action",
        choices=work_admission.SESSION_YIELD_ACTIONS,
        default="release_tool_lease",
    )
    session_yield_request.add_argument("--owner-status", default="active_session")
    session_yield_request.add_argument(
        "--pressure-mode",
        choices=("normal", "degraded", "relief_window", "recovery_monitoring", "unknown"),
        default="degraded",
    )
    session_yield_request.add_argument(
        "--result",
        choices=work_admission.SESSION_YIELD_RESULTS,
        default="requested",
    )
    session_yield_request.add_argument("--helper-rss-mb", type=float, default=0.0)
    session_yield_request.add_argument("--recent-progress-units", type=float, default=0.0)
    session_yield_request.add_argument("--idle-age-s", type=float, default=0.0)
    session_yield_request.add_argument("--last-heartbeat-age-s", type=float, default=0.0)
    session_yield_request.add_argument("--active-claim-count", type=int, default=0)
    session_yield_request.add_argument("--operator-priority-hint", default=None)
    session_yield_request.add_argument("--result-note", default=None)
    session_yield_request.add_argument(
        "--coordination-brief",
        action="store_true",
        help=(
            "Emit a paste-ready sibling-thread coordination request alongside "
            "the append-only yield receipt."
        ),
    )
    session_yield_request.add_argument("--requester-label", default=None)
    session_yield_request.add_argument("--requester-session-id", default=None)
    session_yield_request.add_argument("--blocked-on", default=None)
    session_yield_request.add_argument("--validation-status", default=None)
    session_yield_request.add_argument("--held-path", action="append", default=[])
    session_yield_request.add_argument("--avoid-path", action="append", default=[])
    session_yield_request.add_argument("--avoid-session-id", action="append", default=[])
    session_yield_request.add_argument(
        "--requested-action-note",
        default=None,
        help="Optional one-sentence human action line for the generated coordination brief.",
    )
    session_yield_request.add_argument("--dry-run", action="store_true")
    session_yield_request.set_defaults(func=cmd_session_yield_request)

    session_yield_result = subparsers.add_parser(
        "session-yield-result",
        help=(
            "Close a resident pressure yield request with the owning session's "
            "visible result. Accepted still requires an applied action to count as relief."
        ),
    )
    session_yield_result.add_argument("--request-id", default=None)
    session_yield_result.add_argument("--target-session-id", default=None)
    session_yield_result.add_argument(
        "--result",
        choices=work_admission.OWNER_YIELD_RESULT_VALUES,
        required=True,
    )
    session_yield_result.add_argument(
        "--applied-action",
        choices=work_admission.OWNER_YIELD_APPLIED_ACTIONS,
        default="none",
    )
    session_yield_result.add_argument(
        "--delivery",
        choices=work_admission.OWNER_YIELD_DELIVERY_VALUES,
        default="visible_to_owner",
    )
    session_yield_result.add_argument("--result-note", default=None)
    session_yield_result.add_argument("--dry-run", action="store_true")
    session_yield_result.set_defaults(func=cmd_session_yield_result)

    session_yield_control = subparsers.add_parser(
        "session-yield-control",
        help="Summarize pending, accepted, and applied resident pressure relief requests.",
    )
    session_yield_control.add_argument("--limit", type=int, default=20)
    session_yield_control.add_argument(
        "--pending-ttl-s",
        type=int,
        default=work_admission.RESIDENT_RELIEF_PENDING_TTL_S,
        help="TTL for resident relief pending-request settlement classification.",
    )
    session_yield_control.add_argument(
        "--full",
        action="store_true",
        help="Emit full request/result rows, including coordination message bodies.",
    )
    session_yield_control.set_defaults(func=cmd_session_yield_control)

    session_yield_inbox = subparsers.add_parser(
        "session-yield-inbox",
        help="Show yield/release requests addressed to one Work Ledger session.",
    )
    session_yield_inbox.add_argument("--session-id", required=True)
    session_yield_inbox.add_argument("--limit", type=int, default=12)
    session_yield_inbox.add_argument(
        "--scan-limit",
        type=int,
        default=400,
        help="Number of recent request/result log rows to scan before filtering to the session.",
    )
    session_yield_inbox.set_defaults(func=cmd_session_yield_inbox)

    session_message = subparsers.add_parser(
        "session-message",
        help="Append a lightweight Work Ledger session-to-session coordination message.",
    )
    session_message.add_argument("--message-id", default=None)
    session_message.add_argument("--from-session-id", required=True)
    session_message.add_argument("--to-session-id", required=True)
    session_message.add_argument(
        "--message-type",
        choices=work_ledger_runtime.SESSION_WORKFLOW_MESSAGE_TYPES,
        default="signal_blocker",
    )
    session_message.add_argument("--subject", default=None)
    session_message.add_argument("--body", required=True)
    session_message.add_argument("--related-path", action="append", default=[])
    session_message.add_argument("--related-request-id", default=None)
    session_message.add_argument("--reply-to-message-id", default=None)
    session_message.add_argument("--requires-ack", action="store_true")
    session_message.add_argument("--dry-run", action="store_true")
    session_message.set_defaults(func=cmd_session_message)

    session_message_inbox = subparsers.add_parser(
        "session-message-inbox",
        aliases=["session-inbox"],
        help="Show append-only coordination messages addressed to one Work Ledger session.",
    )
    session_message_inbox.add_argument("--session-id", required=True)
    session_message_inbox.add_argument("--limit", type=int, default=12)
    session_message_inbox.add_argument(
        "--scan-limit",
        type=int,
        default=400,
        help="Number of recent session message log rows to scan before filtering.",
    )
    session_message_inbox.add_argument("--include-sent", action="store_true")
    session_message_inbox.add_argument(
        "--include-acked",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    session_message_inbox.set_defaults(func=cmd_session_message_inbox)

    session_preflight = subparsers.add_parser(
        "session-preflight",
        help=(
            "One-command autonomous-seed preflight: import recent Codex peers, "
            "bootstrap this session, optionally claim td/path scopes, and print closeout commands."
        ),
        epilog=(
            "This is the serial setup lane for one session; prefer it over parallel "
            "session-bootstrap plus session-claim-path calls."
        ),
    )
    session_preflight.add_argument("--session-id", default=None)
    session_preflight.add_argument("--session-slug", default="autonomous")
    session_preflight.add_argument("--actor", default="codex")
    session_preflight.add_argument("--phase-id", default=None)
    session_preflight.add_argument("--family-id", default=None)
    session_preflight.add_argument("--td-id", "--work-item-id", dest="td_id", action="append", default=[])
    session_preflight.add_argument("--path", "--claim-path", dest="path", action="append", default=[])
    session_preflight.add_argument(
        "--write-profile",
        action="append",
        choices=sorted(WRITE_PROFILE_PATHS),
        default=[],
        help=(
            "Claim the known generated write set for a projection command. "
            "May be repeated; choices: %(choices)s."
        ),
    )
    session_preflight.add_argument("--lease-minutes", type=float, default=30.0)
    session_preflight.add_argument("--note", default=None)
    session_preflight.add_argument(
        "--host-pressure-policy",
        choices=work_admission.ADMISSION_POLICY_VALUES,
        default=os.environ.get("AIW_WORK_LEDGER_HOST_PRESSURE_POLICY", "auto"),
        help=(
            "Admission policy before creating session claims: auto queues heavy work "
            "under host-pressure load-shed, warn reports but admits, off disables the gate."
        ),
    )
    session_preflight.add_argument(
        "--work-admission-class",
        default=None,
        choices=sorted(
            set(work_admission.HOST_PRESSURE_WORKLOAD_BY_CLASS)
            | set(WORK_ADMISSION_CLASS_ALIASES)
        ),
        help="Override the inferred work-creation class for this session preflight.",
    )
    session_preflight.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Refuse any requested td/path claim that collides with an active overlapping claim.",
    )
    session_preflight.add_argument(
        "--skip-import-codex",
        action="store_true",
        help="Do not import recent Codex host threads before bootstrapping this session.",
    )
    session_preflight.add_argument(
        "--skip-import-claude",
        action="store_true",
        help="Do not import Claude IDE lock observations before bootstrapping this session.",
    )
    session_preflight.add_argument("--since-minutes", type=float, default=60.0)
    session_preflight.add_argument("--import-limit", type=int, default=20)
    session_preflight.add_argument("--bootstrap-limit", type=int, default=work_ledger_runtime.BOOTSTRAP_SLICE_LIMIT)
    session_preflight.add_argument(
        "--overview-limit",
        "--limit",
        dest="overview_limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
    )
    session_preflight.add_argument("--db-path", default=None)
    session_preflight.add_argument("--include-all-cwds", action="store_true")
    session_preflight.add_argument("--include-all-workspaces", action="store_true")
    session_preflight.add_argument(
        "--heartbeat-current-pass-line",
        "--current-pass-line",
        "--heartbeat-now",
        "--now",
        dest="heartbeat_current_pass_line",
        default=None,
        help=(
            "Optional public current-pass line to write as part of the same "
            "session-preflight mutation."
        ),
    )
    session_preflight.add_argument(
        "--heartbeat-last-pass-result-line",
        "--heartbeat-result-line",
        "--last-pass-result-line",
        "--heartbeat-done",
        "--done",
        dest="heartbeat_last_pass_result_line",
        default=None,
        help=(
            "Optional public previous-result line to write as part of the same "
            "session-preflight mutation."
        ),
    )
    session_preflight.add_argument(
        "--heartbeat-clip-lines",
        action="store_true",
        help=(
            "Trim preflight heartbeat now/done text to Work Ledger public line "
            "limits before runtime validation. Default is strict rejection."
        ),
    )
    session_preflight.add_argument(
        "--heartbeat-state",
        "--heartbeat-status",
        dest="heartbeat_state",
        default="inspecting",
        help=_heartbeat_state_help(),
    )
    session_preflight.add_argument(
        "--heartbeat-scope-ref",
        action="append",
        default=[],
        help=(
            "Optional heartbeat scope ref. Repeatable. Defaults to claimed "
            "WorkItem/thread ids plus claimed paths when heartbeat text is supplied."
        ),
    )
    session_preflight.add_argument(
        "--heartbeat-source",
        default="manual_cli",
        choices=sorted(work_ledger_runtime.PASS_HEARTBEAT_SOURCES),
    )
    session_preflight.add_argument(
        "--full",
        action="store_true",
        help=(
            "Print expanded bounded diagnostics instead of the compact default. "
            "Pair with --raw-full for unbounded bootstrap/import/cohort internals."
        ),
    )
    session_preflight.add_argument(
        "--raw-full",
        action="store_true",
        help=(
            "With --full, include unbounded bootstrap/import/cohort internals. "
            "Use only for selected drilldowns."
        ),
    )
    session_preflight.add_argument(
        "--status-json",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    session_preflight.set_defaults(func=cmd_session_preflight)

    session_claim = subparsers.add_parser(
        "session-claim",
        help="Record a forward-looking lease on a td_* and surface any active claim collision.",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_claim.add_argument("--session-id", required=True)
    session_claim.add_argument("--td-id", required=True)
    session_claim.add_argument(
        "--lease-minutes",
        type=float,
        default=30.0,
        help="Lease duration in minutes (default 30, clamped to 12h max).",
    )
    session_claim.add_argument("--note", default=None)
    session_claim.add_argument(
        "--claim-intent",
        type=_normalize_claim_intent_cli,
        choices=sorted(work_ledger_runtime.CLAIM_INTENTS),
        default=work_ledger_runtime.CLAIM_INTENT_HARD_MUTATION,
        help="Optional conflict intent; hard_mutation preserves the historical exclusive behavior.",
    )
    session_claim.add_argument(
        "--conflict-scope-kind",
        choices=sorted(work_ledger_runtime.CLAIM_CONFLICT_SCOPE_KINDS),
        default=None,
        help="Optional semantic conflict range label recorded alongside the td_id/WorkItem claim.",
    )
    session_claim.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Refuse the claim if another active session holds an unexpired claim on the same td_id, WorkItem id, or path.",
    )
    session_claim.set_defaults(func=cmd_session_claim)

    session_claim_path = subparsers.add_parser(
        "session-claim-path",
        help="Record a forward-looking lease on a repo-relative path and surface active path collisions.",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_claim_path.add_argument("--session-id", required=True)
    session_claim_path.add_argument("--path", required=True)
    session_claim_path.add_argument(
        "--lease-minutes",
        type=float,
        default=30.0,
        help="Lease duration in minutes (default 30, clamped to 12h max).",
    )
    session_claim_path.add_argument("--note", default=None)
    session_claim_path.add_argument(
        "--claim-intent",
        type=_normalize_claim_intent_cli,
        choices=sorted(work_ledger_runtime.CLAIM_INTENTS),
        default=work_ledger_runtime.CLAIM_INTENT_HARD_MUTATION,
        help="Optional conflict intent; hard_mutation preserves the historical exclusive behavior.",
    )
    session_claim_path.add_argument(
        "--conflict-scope-kind",
        choices=sorted(work_ledger_runtime.CLAIM_CONFLICT_SCOPE_KINDS),
        default=None,
        help="Optional semantic conflict range label recorded alongside the path claim.",
    )
    session_claim_path.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Refuse the claim if another active session holds an overlapping unexpired path claim.",
    )
    session_claim_path.set_defaults(func=cmd_session_claim_path)

    session_release_claim = subparsers.add_parser(
        "session-release-claim",
        help="Release an active claim by --claim-id, --td-id, or --path.",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_release_claim.add_argument("--session-id", required=True)
    session_release_claim.add_argument("--claim-id", default=None)
    session_release_claim.add_argument("--td-id", default=None)
    session_release_claim.add_argument("--path", default=None)
    session_release_claim.add_argument(
        "--reason",
        default="released_by_operator",
        help="Free-form release reason recorded on the claim.",
    )
    session_release_claim.set_defaults(func=cmd_session_release_claim)

    session_sweep = subparsers.add_parser(
        "session-sweep",
        help=(
            "Auto-finalize crashed orphan sessions and mark expired claims. "
            "Idempotent; preserves history (end_action=auto_orphan_sweep, expired_at set explicitly)."
        ),
    )
    session_sweep.add_argument(
        "--orphan-after-hours",
        type=float,
        default=0.0,
        help=(
            "Override the orphan sweep threshold in hours "
            "(default uses ACTIVE_SESSION_ORPHAN_SWEEP_AFTER = 24h)."
        ),
    )
    session_sweep.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which sessions/claims would be swept without mutating state.",
    )
    session_sweep.add_argument(
        "--dirty-tree-pressure",
        action="store_true",
        help=(
            "Include a read-only dirty-tree bankruptcy pressure card that routes "
            "expired work to sweep/private-backup/scoped owner lanes without committing from age alone."
        ),
    )
    session_sweep.add_argument(
        "--dirty-path",
        action="append",
        default=[],
        help=(
            "Repo-relative dirty path fixture for pressure classification. "
            "Repeatable; when omitted, git status --porcelain=v1 -z --untracked-files=all is read."
        ),
    )
    session_sweep.add_argument(
        "--dirty-path-limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help=(
            "Preview row limit for dirty-tree pressure path classes. Use a high "
            "value only for machine consumers that need a full path manifest."
        ),
    )
    session_sweep.add_argument(
        "--bankruptcy-authorized",
        action="store_true",
        help=(
            "For explicit operator dirty-tree-bankruptcy requests, allow the pressure "
            "card to route to the broad checkpoint arbiter command when no dirty path "
            "is covered by an active claim."
        ),
    )
    session_sweep.add_argument(
        "--dedupe-duplicate-claims",
        action="store_true",
        help=(
            "Release older duplicate claims held by the same session and scope. "
            "True cross-session collisions remain explicit coordination blockers."
        ),
    )
    session_sweep.add_argument(
        "--dedupe-preview-limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help=(
            "Preview row limit for duplicate-claim dedupe actions and released "
            "claim rows. Use --full only for machine consumers that need every "
            "released claim record."
        ),
    )
    session_sweep.add_argument(
        "--full",
        action="store_true",
        help=(
            "Print full sweep detail, including every duplicate claim released. "
            "Default output keeps bounded previews for agent-facing coordination."
        ),
    )
    session_sweep.set_defaults(func=cmd_session_sweep)

    append_open = subparsers.add_parser("append-open")
    _add_common_mutation_args(append_open)
    append_open.set_defaults(func=cmd_append_open)

    progress = subparsers.add_parser("progress")
    _add_common_mutation_args(progress, require_td_id=True, allow_unclaimed_note_arg=True)
    progress.set_defaults(func=cmd_progress)

    note = subparsers.add_parser("note")
    _add_common_mutation_args(note, require_td_id=True, allow_unclaimed_note_arg=True)
    note.set_defaults(func=cmd_progress)

    close = subparsers.add_parser("close")
    _add_common_mutation_args(close, require_td_id=True)
    close.add_argument("--resolution-kind", required=True, choices=sorted(work_ledger.RESOLUTION_KINDS))
    close.add_argument("--resolution-ref", required=True)
    close.add_argument("--resolution-label", default=None)
    close.add_argument("--resolution-metadata-json", default=None)
    close.set_defaults(func=cmd_close)

    supersede = subparsers.add_parser("supersede")
    _add_common_mutation_args(supersede, require_td_id=True)
    supersede.add_argument("--resolution-kind", required=True, choices=sorted(work_ledger.RESOLUTION_KINDS))
    supersede.add_argument("--resolution-ref", required=True)
    supersede.add_argument("--resolution-label", default=None)
    supersede.add_argument("--resolution-metadata-json", default=None)
    supersede.set_defaults(func=cmd_supersede)

    reopen = subparsers.add_parser("reopen")
    _add_common_mutation_args(reopen, require_td_id=True)
    reopen.set_defaults(func=cmd_reopen)

    project = subparsers.add_parser("project")
    project.add_argument("--phase-id", default=None)
    project.add_argument("--family-id", default=None)
    project.add_argument("--all", action="store_true")
    project.add_argument("--check", action="store_true")
    project.add_argument(
        "--target-only",
        action="store_true",
        help=(
            "Refresh or check only the selected phase/family index. Sibling "
            "family bucket projections are reported as deferred instead of rewritten."
        ),
    )
    project.add_argument(
        "--full",
        action="store_true",
        help="Print the full projection payload for project --target-only diagnostics.",
    )
    project.set_defaults(func=cmd_project)

    query = subparsers.add_parser("query")
    query.add_argument("--recipe", required=True, choices=work_ledger.supported_query_recipes())
    query.add_argument("--phase-id", default=None)
    query.add_argument("--family-id", default=None)
    query.add_argument("--actor", default=None)
    query.add_argument("--actor-session-id", default=None)
    query.add_argument("--td-id", default=None)
    query.add_argument("--limit", type=int, default=20)
    query.add_argument("--read-receipt-id", default=None)
    query.set_defaults(func=cmd_query)

    handoffs = subparsers.add_parser(
        "agent-seed-handoffs",
        help="Extract agent_seed handoff/deferred-work paragraphs and optionally open deduped work-ledger rows.",
    )
    handoffs.add_argument("--phase-id", default=None)
    handoffs.add_argument("--family-id", default=None)
    handoffs.add_argument("--since-date", default=None)
    handoffs.add_argument("--limit", type=int, default=100)
    handoffs.add_argument("--include-imported", action="store_true")
    handoffs.add_argument("--live", action="store_true")
    handoffs.add_argument("--read-receipt-id", default=None)
    handoffs.add_argument("--actor", default=None)
    handoffs.add_argument("--actor-session-id", default=None)
    handoffs.set_defaults(func=cmd_agent_seed_handoffs)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
