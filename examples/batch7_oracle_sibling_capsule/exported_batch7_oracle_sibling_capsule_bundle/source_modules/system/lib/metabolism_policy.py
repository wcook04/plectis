"""
Policy layer for metabolism events, scans, and job derivation.

[PURPOSE]
- Teleology: Convert low-level runtime facts into deterministic, small, safe
  maintenance jobs so the daemon can coordinate continuous upkeep without
  re-deriving policy in chat memory.
- Mechanism: Normalize event digests, scan the repo's relevant substrate,
  evaluate reaction-style signals, and map events to launchable operation jobs.

[INTERFACE]
- Exports scan/event construction, reaction signal/effect helpers, job derivation reports, source priority, and provider_budget_for.

[FLOW]
- Mechanism: Scan relevant substrate, digest events, evaluate reactions with per-source fault isolation, and derive launchable job records with idempotency keys.

[DEPENDENCIES]
- embedding_sources/substrate inspect navigator freshness; raw_seed intake/atomization and Work Ledger runtime supply scan evidence; metabolism_store defines provider budgets.

[CONSTRAINTS]
- Writes: No jobs are dispatched by these derivation helpers; callers persist returned events/jobs.
- Guarantee: derive_reaction_jobs_report retains source-lane faults as diagnostics instead of losing the whole reaction set.
- Non-goal: Inferring causal progress from exit status alone.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from system.lib.embedding_sources import all_source_kinds, build_adapter
from system.lib.embedding_substrate import EmbeddingSubstrate
from system.lib.hologram_build_status import load_hologram_build_status
from system.lib.metabolism_raw_seed_intake import discover_family_raw_seed_roots
from system.lib.metabolism_store import DEFAULT_PROVIDER_BUDGETS
from system.lib.raw_seed_atomization import load_raw_seed_pipeline_snapshot
from system.lib.work_ledger_runtime import (
    ACTIVE_CLAIMS_SNAPSHOT_REL,
    RUNTIME_STATUS_REL,
    load_runtime_status as load_work_ledger_runtime_status,
)


SCAN_SCHEMA = "metabolism_scan_state_v1"
SKIP_DIRS = {
    ".git",
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}
SKIP_SUBTREES = {
    ".claude/worktrees",
    "state/metabolism/logs",
}
PRIORITY_HIGH = 10
PRIORITY_MEDIUM = 20
PRIORITY_LOW = 30
NVIDIA_CONTINUOUS_SOURCE_ORDER = [
    "raw_seed_shards",
    "standards_json",
    "python_holographic",
    "raw_seed_paragraphs",
    "raw_seed_navigation",
    "paper_modules",
    "skills",
    "doctrine",
    "archaeology_shards",
    "annex_notes",
]
OVERNIGHT_SOURCE_PRIORITIES = {
    "raw_seed_shards": 8,
    "standards_json": 9,
    "python_holographic": 10,
    "raw_seed_paragraphs": 11,
    "raw_seed_navigation": 12,
    "paper_modules": 30,
    "skills": 32,
    "doctrine": 35,
    "archaeology_shards": 45,
    "annex_notes": 60,
}
ANNEX_TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".sh",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".html",
    ".csv",
}
NAVIGATOR_REFRESHABLE_CATEGORIES = {"standards", "doctrine", "annex", "host_dotfiles"}
OVERNIGHT_NAVIGATOR_SIGNAL_SOURCE_KINDS = (
    "raw_seed_shards",
    "standards_json",
)
ANNEX_UPSTREAM_POLL_INTERVAL_SECONDS = 600
ANNEX_UPSTREAM_POLL_CHUNK_SIZE = 8
ANNEX_UPSTREAM_STALE_THRESHOLD_DAYS = 7
WORK_LEDGER_SIGNAL_EVENT_SCHEMA = "work_ledger_signal_event_payload_v1"
REACTION_EFFECT_MODE_SOURCE_PROGRESS = "source_progress"


def _repo_relative_size(repo_root: Path, rel_path: Path) -> int | None:
    try:
        return int((repo_root / rel_path).stat().st_size)
    except OSError:
        return None


def stable_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_event(
    *,
    source: str,
    kind: str,
    payload: Mapping[str, Any],
    stable_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    digest_basis = dict(stable_fields or {})
    if not digest_basis:
        digest_basis = {
            "source": source,
            "kind": kind,
            "payload": dict(payload),
        }
    return {
        "source": source,
        "kind": kind,
        "payload": dict(payload),
        "stable_digest": stable_digest(digest_basis),
    }


def compact_work_ledger_signal_payload(
    status: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return the inline event body for Work Ledger runtime scan signals.

    The full Work Ledger runtime status can be multi-megabyte session history.
    The metabolism event only needs small routing metadata plus a pointer back
    to the authority artifact.
    """

    counts = dict(status.get("counts") or {})
    triggers = dict(status.get("triggers") or {})
    overview = status.get("cohort_overview") if isinstance(status.get("cohort_overview"), Mapping) else {}
    contention = overview.get("contention") if isinstance(overview.get("contention"), Mapping) else {}
    monitor_cards = list(overview.get("monitor_cards") or []) if isinstance(overview.get("monitor_cards"), list) else []
    authority: dict[str, Any] = {
        "full_payload_ref": RUNTIME_STATUS_REL.as_posix(),
        "active_claims_snapshot_ref": ACTIVE_CLAIMS_SNAPSHOT_REL.as_posix(),
        "posture": "full_runtime_status_remains_authority_event_body_is_summary",
    }
    if repo_root is not None:
        runtime_bytes = _repo_relative_size(repo_root, RUNTIME_STATUS_REL)
        claims_bytes = _repo_relative_size(repo_root, ACTIVE_CLAIMS_SNAPSHOT_REL)
        if runtime_bytes is not None:
            authority["full_payload_bytes"] = runtime_bytes
        if claims_bytes is not None:
            authority["active_claims_snapshot_bytes"] = claims_bytes

    omitted_keys = sorted(
        str(key)
        for key in status.keys()
        if key
        not in {
            "schema",
            "generated_at",
            "counts",
            "triggers",
            "stable_signal_digest",
            "cohort_overview",
        }
    )
    return {
        "schema": WORK_LEDGER_SIGNAL_EVENT_SCHEMA,
        "source_schema": status.get("schema"),
        "generated_at": status.get("generated_at"),
        "stable_signal_digest": status.get("stable_signal_digest"),
        "counts": counts,
        "triggers": triggers,
        "cohort_overview": {
            "schema": overview.get("schema"),
            "counts": dict(overview.get("counts") or {}),
            "risk_level": contention.get("risk_level"),
            "signals": list(contention.get("signals") or [])[:12],
            "recommended_landing_lane": overview.get("recommended_landing_lane"),
            "monitor_cards": monitor_cards[:6],
        },
        "authority": authority,
        "inline_payload_policy": {
            "class_id": "derived_runtime_diagnostic_signal",
            "max_inline_shape": "metadata_summary_plus_authority_refs",
            "omitted_keys": omitted_keys,
        },
    }


def _path_matches_any(path: str, prefixes: Iterable[str]) -> bool:
    token = path.replace("\\", "/")
    return any(token.startswith(prefix.rstrip("/")) for prefix in prefixes)


def categorize_path(rel_path: str) -> str | None:
    path = rel_path.replace("\\", "/")
    if path.endswith(".py"):
        return "python"
    if "raw_seed" in path and (path.endswith(".md") or path.endswith(".json")):
        return "raw_seed"
    if path.startswith("codex/standards/") and path.endswith(".json"):
        return "standards"
    if _path_matches_any(path, ("codex/doctrine/paper_modules/", "codex/doctrine/skills/")) and path.endswith(".md"):
        return "doctrine"
    if path == "annex_import.py":
        return "annex"
    if path.startswith("annexes/") and Path(path).suffix.lower() in ANNEX_TEXT_EXTENSIONS:
        return "annex"
    if _path_matches_any(path, (".claude/", ".codex/")):
        return "host_dotfiles"
    return None


def navigator_source_kind_for_path(rel_path: str, category: str | None = None) -> str | None:
    path = rel_path.replace("\\", "/")
    if path.startswith("codex/doctrine/paper_modules/") and path.endswith(".md"):
        return "paper_modules"
    if path.startswith("codex/doctrine/skills/") and path.endswith(".md"):
        return "skills"
    if path.startswith("annexes/"):
        return "annex_notes"
    if path == "annex_import.py":
        return "annex_notes"
    if path.startswith("codex/standards/") and path.endswith(".json"):
        return "standards_json"
    if category in NAVIGATOR_REFRESHABLE_CATEGORIES:
        return "doctrine"
    return None


def _fingerprint_file(path: Path, previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
    stat = path.stat()
    payload = {
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }
    prior = dict(previous or {})
    if prior.get("mtime_ns") == payload["mtime_ns"] and prior.get("size") == payload["size"] and prior.get("sha1"):
        payload["sha1"] = prior["sha1"]
        return payload
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    payload["sha1"] = digest.hexdigest()
    return payload


def _scan_roots(repo_root: Path) -> list[Path]:
    return [
        repo_root / "system",
        repo_root / "tools",
        repo_root / "codex",
        repo_root / "docs",
        repo_root / "annexes",
        repo_root / "obsidian",
        repo_root / ".claude",
        repo_root / ".codex",
        repo_root / "annex_import.py",
    ]


def _iter_relevant_files(repo_root: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    root = repo_root.resolve()
    for base in _scan_roots(repo_root):
        if not base.exists():
            continue
        if base.is_file():
            try:
                rel_path = base.relative_to(repo_root).as_posix()
            except ValueError:
                continue
            if base not in seen and categorize_path(rel_path):
                seen.add(base)
                yield base
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dir_path = Path(dirpath)
            try:
                rel_dir = dir_path.relative_to(repo_root).as_posix()
            except ValueError:
                continue
            dirnames[:] = [
                item
                for item in dirnames
                if item not in SKIP_DIRS
                and not _path_matches_any(f"{rel_dir}/{item}", SKIP_SUBTREES)
            ]
            for filename in filenames:
                candidate = dir_path / filename
                try:
                    rel_path = candidate.relative_to(repo_root).as_posix()
                except ValueError:
                    continue
                if candidate.is_symlink():
                    try:
                        candidate.resolve().relative_to(root)
                    except ValueError:
                        continue
                if _path_matches_any(rel_path, SKIP_SUBTREES):
                    continue
                if rel_path.startswith(".claude/worktrees/"):
                    continue
                if categorize_path(rel_path) is None:
                    continue
                if candidate in seen:
                    continue
                seen.add(candidate)
                yield candidate


def collect_scan_events(repo_root: Path, previous_state: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    previous_files = dict((previous_state or {}).get("files") or {})
    current_files: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    family_raw_seed_roots = discover_family_raw_seed_roots(repo_root)
    for path in _iter_relevant_files(repo_root):
        try:
            rel_path = path.relative_to(repo_root).as_posix()
            previous_fingerprint = previous_files.get(rel_path)
            fingerprint = _fingerprint_file(path, previous=previous_fingerprint)
        except (OSError, ValueError):
            continue
        current_files[rel_path] = fingerprint
        if previous_fingerprint == fingerprint:
            continue
        category = categorize_path(rel_path)
        if category is None:
            continue
        if rel_path in family_raw_seed_roots:
            root = family_raw_seed_roots[rel_path]
            events.append(
                build_event(
                    source="filesystem_scan",
                    kind="raw_seed_edit_observed",
                    payload={
                        "path": rel_path,
                        "category": category,
                        "fingerprint": fingerprint,
                        "family": root.family_number,
                        "family_dir": root.family_dir,
                        "raw_seed_path": root.raw_seed_path,
                    },
                    stable_fields={
                        "kind": "raw_seed_edit_observed",
                        "path": rel_path,
                        "fingerprint": fingerprint,
                    },
                )
            )
            continue
        events.append(
            build_event(
                source="filesystem_scan",
                kind="file_changed",
                payload={
                    "path": rel_path,
                    "category": category,
                    "fingerprint": fingerprint,
                },
                stable_fields={
                    "kind": "file_changed",
                    "path": rel_path,
                    "fingerprint": fingerprint,
                },
            )
        )
    scan_state = {
        "schema": SCAN_SCHEMA,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "files": current_files,
    }
    return events, scan_state


def _load_latest_operation_event(repo_root: Path, *, operation_id: str, family: str | None = None) -> dict[str, Any]:
    path = repo_root / "tools" / "meta" / "control" / "orchestration_events.jsonl"
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines[-400:]):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(payload.get("kind") or "").strip() != "operation_launched":
            continue
        if str(payload.get("operation_id") or "").strip() != operation_id:
            continue
        params = payload.get("resolved_parameters") if isinstance(payload.get("resolved_parameters"), Mapping) else {}
        if family and str(params.get("family") or "").strip() != family:
            continue
        return dict(payload)
    return {}


def build_runtime_signal_events(repo_root: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    raw_seed = load_raw_seed_pipeline_snapshot(repo_root, family_dir=None, family_number="09")
    raw_payload = {
        "family": "09",
        "counts": {
            "paragraphs_without_atoms": raw_seed.get("paragraphs_without_atoms") or 0,
            "pending_routing_shards": raw_seed.get("pending_routing_shards") or 0,
            "review_queue_entries": raw_seed.get("review_queue_entries") or 0,
            "fresh_pending_bins": raw_seed.get("fresh_pending_bins") or 0,
        },
        "last_updated": raw_seed.get("last_updated"),
        "raw_seed_coverage_path": raw_seed.get("raw_seed_coverage_path"),
    }
    events.append(
        build_event(
            source="runtime_scan",
            kind="raw_seed_signal",
            payload=raw_payload,
            stable_fields={"kind": "raw_seed_signal", "payload": raw_payload},
        )
    )

    work_ledger = load_work_ledger_runtime_status(repo_root)
    work_ledger_payload = compact_work_ledger_signal_payload(work_ledger, repo_root=repo_root)
    events.append(
        build_event(
            source="runtime_scan",
            kind="work_ledger_signal",
            payload=work_ledger_payload,
            stable_fields={
                "kind": "work_ledger_signal",
                "stable_signal_digest": work_ledger.get("stable_signal_digest"),
            },
        )
    )

    hologram = load_hologram_build_status(repo_root)
    events.append(
        build_event(
            source="runtime_scan",
            kind="hologram_signal",
            payload=hologram,
            stable_fields={"kind": "hologram_signal", "payload": hologram},
        )
    )

    # provider-model-catalog availability signal — the deriving function
    # is pure (no provider calls, no transform_job builds, no writes).
    # Reactions targeting this kind dedupe on signal_digest and gate
    # provider_transform_materialize draft-only.
    from system.lib import provider_metabolism_signal as _pms

    catalog_payload = _pms.derive_provider_model_catalog_signal(repo_root)
    events.append(
        build_event(
            source="runtime_scan",
            kind="provider_model_catalog_signal",
            payload=catalog_payload,
            stable_fields={
                "kind": "provider_model_catalog_signal",
                "signal_digest": catalog_payload.get("signal_digest"),
            },
        )
    )

    # Wave_004B: emit the two compliance-reaction signals so the runtime scan
    # surfaces them alongside the existing provider_model_catalog_signal.
    # Both signal producers are pure-read; digests dedupe re-fires.
    try:
        from system.lib import compliance_reaction_signals as _crs

        gap_payload = _crs.build_standard_skill_gap_signal(repo_root)
        events.append(
            build_event(
                source="runtime_scan",
                kind="standard_skill_gap_signal",
                payload=gap_payload,
                stable_fields={
                    "kind": "standard_skill_gap_signal",
                    "signal_digest": gap_payload.get("digest"),
                },
            )
        )
        coverage_payload = _crs.build_compliance_coverage_signal(repo_root)
        events.append(
            build_event(
                source="runtime_scan",
                kind="compliance_coverage_signal",
                payload=coverage_payload,
                stable_fields={
                    "kind": "compliance_coverage_signal",
                    "signal_digest": coverage_payload.get("digest"),
                },
            )
        )
    except ImportError:
        pass

    annex_bucket = int(time.time()) // ANNEX_UPSTREAM_POLL_INTERVAL_SECONDS
    annex_payload = {
        "schema_version": "annex_upstream_poll_signal_v0",
        "kind": "annex_upstream_poll_signal",
        "bucket": annex_bucket,
        "poll_interval_seconds": ANNEX_UPSTREAM_POLL_INTERVAL_SECONDS,
        "chunk_limit": ANNEX_UPSTREAM_POLL_CHUNK_SIZE,
        "stale_days": ANNEX_UPSTREAM_STALE_THRESHOLD_DAYS,
        "operation_id": "annex_sync_digest_pull",
    }
    events.append(
        build_event(
            source="runtime_scan",
            kind="annex_upstream_poll_signal",
            payload=annex_payload,
            stable_fields={
                "kind": "annex_upstream_poll_signal",
                "bucket": annex_bucket,
            },
        )
    )

    navigator_stale = evaluate_navigator_stale(
        repo_root,
        source_kinds=OVERNIGHT_NAVIGATOR_SIGNAL_SOURCE_KINDS,
    )
    if navigator_stale.get("stale_sources"):
        events.append(
            build_event(
                source="runtime_scan",
                kind="navigator_stale_signal",
                payload=navigator_stale,
                stable_fields={"kind": "navigator_stale_signal", "payload": navigator_stale},
            )
        )
    return events


def evaluate_navigator_stale(
    repo_root: Path,
    *,
    source_kinds: Iterable[str] | None = None,
) -> dict[str, Any]:
    state_root = repo_root / "state" / "embeddings"
    if not state_root.exists():
        return {
            "source": "embedding_substrate_status",
            "stale_sources": [],
            "skipped": "embedding_state_root_missing",
        }
    substrate = EmbeddingSubstrate(repo_root)
    requested_source_kinds = [
        str(source_kind).strip()
        for source_kind in (source_kinds if source_kinds is not None else all_source_kinds())
        if str(source_kind).strip()
    ]
    stale_sources: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for source_kind in requested_source_kinds:
        try:
            adapter = build_adapter(source_kind, repo_root)
            status = substrate.status(adapter, fast=True)
        except Exception as exc:
            errors.append({"source_kind": source_kind, "error": f"{type(exc).__name__}: {exc}"})
            continue
        stale_or_missing = int(status.stale_or_missing or 0)
        if stale_or_missing <= 0:
            continue
        stale_sources.append(
            {
                "source_kind": source_kind,
                "stale_or_missing": stale_or_missing,
                "record_count": int(status.record_count or 0),
                "schema_hash": status.schema_hash,
                "path": status.path,
                "stale_preview": list(getattr(status, "stale_preview", []) or []),
                "stale_preview_truncated": bool(getattr(status, "stale_preview_truncated", False)),
                "stale_or_missing_is_estimate": bool(getattr(status, "stale_or_missing_is_estimate", False)),
            }
        )
    return {
        "source": "embedding_substrate_status",
        "source_kinds": requested_source_kinds,
        "stale_sources": stale_sources,
        "errors": errors,
    }


def build_codex_adapter_event(
    *,
    source: str,
    kind: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    stable_fields = {
        "source": source,
        "kind": kind,
        "thread_id": payload.get("thread_id"),
        "session_id": payload.get("session_id"),
        "status": payload.get("status"),
        "fingerprint": payload.get("fingerprint"),
        "delivery_method": payload.get("delivery_method"),
    }
    return build_event(source=source, kind=kind, payload=payload, stable_fields=stable_fields)


def _resolve_field(payload: Mapping[str, Any], field_path: str) -> Any:
    current: Any = payload
    for token in str(field_path or "").split("."):
        if not token:
            continue
        if not isinstance(current, Mapping):
            return None
        current = current.get(token)
    return current


def _predicate_matches(signal: Mapping[str, Any], predicate: Mapping[str, Any]) -> bool:
    field = str(predicate.get("field") or "").strip()
    operator = str(predicate.get("operator") or "").strip().lower()
    expected = predicate.get("value")
    actual = _resolve_field(signal, field) if field else signal
    if operator == "eq":
        return actual == expected
    if operator == "ge":
        try:
            return float(actual) >= float(expected)
        except Exception:
            return str(actual) >= str(expected)
    if operator == "gt":
        try:
            return float(actual) > float(expected)
        except Exception:
            return str(actual) > str(expected)
    if operator == "nonempty":
        if actual is None:
            return False
        if isinstance(actual, (str, list, tuple, dict)):
            return len(actual) > 0
        return bool(actual)
    return False


def _render_parameter_template(value: Any, signal: Mapping[str, Any]) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith("{signal.") and value.endswith("}"):
        return _resolve_field(signal, value[len("{signal.") : -1])
    return value


def _render_parameters(parameters: Mapping[str, Any], signal: Mapping[str, Any]) -> dict[str, Any]:
    rendered: dict[str, Any] = {}
    for key, value in parameters.items():
        resolved = _render_parameter_template(value, signal)
        if resolved is not None:
            rendered[str(key)] = resolved
    return rendered


def compact_reaction_signal(signal: Mapping[str, Any]) -> dict[str, Any]:
    """Keep reaction job rows audit-friendly without embedding huge source projections."""
    compact: dict[str, Any] = {}
    for key in (
        "schema",
        "kind",
        "source",
        "generated_at",
        "stable_signal_digest",
        "last_updated",
        "status",
        "phase_id",
        "family",
    ):
        value = signal.get(key)
        if value is not None:
            compact[key] = value
    for key in ("counts", "triggers"):
        value = signal.get(key)
        if isinstance(value, Mapping):
            compact[key] = dict(value)
    stale_sources = signal.get("stale_sources")
    if isinstance(stale_sources, list):
        compact["stale_sources"] = [
            {
                "source_kind": item.get("source_kind"),
                "stale_or_missing": item.get("stale_or_missing"),
                "record_count": item.get("record_count"),
                "schema_hash": item.get("schema_hash"),
            }
            for item in stale_sources[:12]
            if isinstance(item, Mapping)
        ]
        if len(stale_sources) > 12:
            compact["stale_sources_truncated"] = len(stale_sources) - 12
    omitted = sorted(
        str(key)
        for key in signal.keys()
        if key not in compact
        and key not in {"counts", "triggers", "stale_sources"}
    )
    if omitted:
        compact["omitted_keys"] = omitted[:32]
        if len(omitted) > 32:
            compact["omitted_key_count"] = len(omitted)
    return compact


def _reaction_signal_digest(reaction_id: str, signal: Mapping[str, Any]) -> str:
    stable_signal_digest = str(signal.get("stable_signal_digest") or "").strip()
    if stable_signal_digest:
        return stable_digest(
            {
                "reaction_id": reaction_id,
                "stable_signal_digest": stable_signal_digest,
            }
        )
    compact = compact_reaction_signal(signal)
    compact.pop("generated_at", None)
    return stable_digest(
        {
            "reaction_id": reaction_id,
            "signal": compact,
        }
    )


def _raw_seed_signal_payload(repo_root: Path, source: Mapping[str, Any]) -> dict[str, Any]:
    family = str(source.get("family") or "09").strip() or "09"
    substrate = str(source.get("substrate") or "raw_seed").strip() or "raw_seed"
    raw_seed = load_raw_seed_pipeline_snapshot(
        repo_root,
        family_dir=None,
        family_number=family,
        substrate=substrate,
    )
    return {
        "family": family,
        "substrate": substrate,
        "counts": {
            "paragraphs_without_atoms": raw_seed.get("paragraphs_without_atoms") or 0,
            "pending_routing_shards": raw_seed.get("pending_routing_shards") or 0,
            "review_queue_entries": raw_seed.get("review_queue_entries") or 0,
            "fresh_pending_bins": raw_seed.get("fresh_pending_bins") or 0,
        },
        "last_updated": raw_seed.get("last_updated"),
        "raw_seed_coverage_path": raw_seed.get("raw_seed_coverage_path"),
    }


def _work_ledger_signal_payload(repo_root: Path) -> dict[str, Any]:
    return dict(load_work_ledger_runtime_status(repo_root) or {})


def _hologram_signal_payload(repo_root: Path) -> dict[str, Any]:
    signal = dict(load_hologram_build_status(repo_root) or {})
    signal["phase_list"] = ",".join(signal.get("stale_phase_ids") or [])
    return signal


def _reaction_signal(
    repo_root: Path,
    reaction: Mapping[str, Any],
    *,
    cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source = dict(reaction.get("source") or {})
    kind = str(source.get("kind") or "").strip()
    if kind == "raw_seed_coverage":
        family = str(source.get("family") or "09").strip() or "09"
        substrate = str(source.get("substrate") or "raw_seed").strip() or "raw_seed"
        cache_key = f"raw_seed_coverage:{family}:{substrate}"
        if cache is not None and cache_key in cache:
            return dict(cache[cache_key])
        signal = _raw_seed_signal_payload(repo_root, source)
        if cache is not None:
            cache[cache_key] = dict(signal)
        return signal
    if kind == "work_ledger_status":
        cache_key = "work_ledger_status"
        if cache is not None and cache_key in cache:
            return dict(cache[cache_key])
        signal = _work_ledger_signal_payload(repo_root)
        if cache is not None:
            cache[cache_key] = dict(signal)
        return signal
    if kind == "python_std_compliance_coverage":
        cache_key = "python_std_compliance_coverage"
        if cache is not None and cache_key in cache:
            return dict(cache[cache_key])
        from system.lib.python_std_compliance_runtime import (
            load_python_std_compliance_coverage,
        )

        # Reaction evaluation is a read/control-plane path. It must not rebuild
        # an expensive coverage artifact merely to discover whether an action
        # is eligible; the operation owning that artifact refreshes it.
        signal = dict(load_python_std_compliance_coverage(repo_root) or {})
        if cache is not None:
            cache[cache_key] = dict(signal)
        return signal
    if kind == "hologram_build_status":
        cache_key = "hologram_build_status"
        if cache is not None and cache_key in cache:
            return dict(cache[cache_key])
        signal = _hologram_signal_payload(repo_root)
        if cache is not None:
            cache[cache_key] = dict(signal)
        return signal
    if kind == "operation_event":
        operation_id = str(source.get("operation_id") or "").strip()
        family = str(source.get("family") or "").strip() or None
        return _load_latest_operation_event(repo_root, operation_id=operation_id, family=family)
    return {"kind": kind}


def reaction_effect_observation(
    signal: Mapping[str, Any], effect: Mapping[str, Any]
) -> Any:
    """Read the source-owned progress value declared by one reaction.

    A launch return code proves only that a command exited successfully. A
    ``source_progress`` effect additionally states which source value the
    command is expected to move, allowing the resident runtime to distinguish
    useful completion from a successful no-op.
    """

    if str(effect.get("mode") or "").strip() != REACTION_EFFECT_MODE_SOURCE_PROGRESS:
        return None
    field = str(effect.get("field") or "").strip()
    return _resolve_field(signal, field) if field else None


def evaluate_reaction_effect(
    repo_root: Path,
    *,
    reaction_id: str,
    effect: Mapping[str, Any],
    observation_before: Any,
    source_generation_before: str | None = None,
) -> dict[str, Any]:
    """Re-read a reaction source and classify causal progress after success."""

    mode = str(effect.get("mode") or "").strip()
    if mode != REACTION_EFFECT_MODE_SOURCE_PROGRESS:
        return {
            "schema": "reaction_effect_receipt_v0",
            "status": "not_applicable",
            "mode": mode or None,
            "source_generation_before": source_generation_before,
        }
    config_path = repo_root / "reactions.yaml"
    try:
        import yaml  # local import keeps hook and scan startup light

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return {
            "schema": "reaction_effect_receipt_v0",
            "status": "verification_unavailable",
            "mode": mode,
            "timing": str(effect.get("timing") or "").strip() or None,
            "source_generation_before": source_generation_before,
            "source_generation_after": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    reaction = next(
        (
            row
            for row in config.get("reactions") or []
            if isinstance(row, Mapping)
            and str(row.get("reaction_id") or "").strip() == str(reaction_id).strip()
        ),
        None,
    )
    if not isinstance(reaction, Mapping):
        return {
            "schema": "reaction_effect_receipt_v0",
            "status": "verification_unavailable",
            "mode": mode,
            "timing": str(effect.get("timing") or "").strip() or None,
            "source_generation_before": source_generation_before,
            "source_generation_after": None,
            "error": "reaction_not_found",
        }
    try:
        signal = _reaction_signal(repo_root, reaction)
    except Exception as exc:
        return {
            "schema": "reaction_effect_receipt_v0",
            "status": "verification_unavailable",
            "mode": mode,
            "timing": str(effect.get("timing") or "").strip() or None,
            "field": str(effect.get("field") or "").strip() or None,
            "direction": str(effect.get("direction") or "").strip() or None,
            "observation_before": observation_before,
            "observation_after": None,
            "source_generation_before": source_generation_before,
            "source_generation_after": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    observation_after = reaction_effect_observation(signal, effect)
    source_generation_after = _reaction_signal_digest(str(reaction_id), signal)
    direction = str(effect.get("direction") or "").strip()
    if observation_before is None or observation_after is None:
        return {
            "schema": "reaction_effect_receipt_v0",
            "status": "verification_unavailable",
            "mode": mode,
            "timing": str(effect.get("timing") or "").strip() or None,
            "field": str(effect.get("field") or "").strip() or None,
            "direction": direction or None,
            "observation_before": observation_before,
            "observation_after": observation_after,
            "source_generation_before": source_generation_before,
            "source_generation_after": source_generation_after,
            "error": "source_observation_missing",
        }
    progressed = False
    try:
        if direction == "decrease":
            progressed = float(observation_after) < float(observation_before)
        elif direction == "increase":
            progressed = float(observation_after) > float(observation_before)
        elif direction == "change":
            progressed = observation_after != observation_before
        elif direction == "predicate_clear":
            progressed = not _predicate_matches(signal, dict(reaction.get("predicate") or {}))
    except (TypeError, ValueError):
        progressed = False
    source_superseded = bool(
        source_generation_before
        and source_generation_after
        and source_generation_before != source_generation_after
    )
    return {
        "schema": "reaction_effect_receipt_v0",
        "status": (
            "source_superseded"
            if source_superseded
            else ("progress" if progressed else "no_progress")
        ),
        "mode": mode,
        "timing": str(effect.get("timing") or "").strip() or None,
        "field": str(effect.get("field") or "").strip() or None,
        "direction": direction or None,
        "observation_before": observation_before,
        "observation_after": observation_after,
        "source_generation_before": source_generation_before,
        "source_generation_after": source_generation_after,
        "replay_policy": str(effect.get("no_progress_replay") or "").strip() or None,
        "reentry_condition": (
            "rederive against the current source generation"
            if source_superseded
            else None
        ),
    }


def _reaction_effective_armed(reaction: Mapping[str, Any], reactions_state: Mapping[str, Any]) -> bool:
    reaction_id = str(reaction.get("reaction_id") or "").strip()
    per_reaction = dict(reactions_state.get("per_reaction") or {})
    entry = dict(per_reaction.get(reaction_id) or {})
    override = entry.get("override_armed")
    if isinstance(override, bool):
        return override
    return bool(reaction.get("enabled_by_default", True))


def derive_reaction_jobs_report(repo_root: Path) -> dict[str, Any]:
    """Derive reaction jobs while isolating faults to their source lane."""

    state_path = repo_root / "tools" / "meta" / "control" / "reactions_state.json"
    config_path = repo_root / "reactions.yaml"
    if not state_path.exists() or not config_path.exists():
        return {
            "schema": "reaction_job_derivation_report_v0",
            "jobs": [],
            "source_findings": [],
        }
    try:
        reactions_state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        reactions_state = {}
    if not bool(reactions_state.get("desired_armed")):
        return {
            "schema": "reaction_job_derivation_report_v0",
            "jobs": [],
            "source_findings": [],
        }
    try:
        import yaml  # local import keeps hook path lighter

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        config = {}
    jobs: list[dict[str, Any]] = []
    source_findings: list[dict[str, Any]] = []
    signal_cache: dict[str, dict[str, Any]] = {}
    for reaction in config.get("reactions") or []:
        if not isinstance(reaction, Mapping):
            continue
        if not _reaction_effective_armed(reaction, reactions_state):
            continue
        reaction_id = str(reaction.get("reaction_id") or "").strip()
        source = dict(reaction.get("source") or {})
        try:
            signal = _reaction_signal(repo_root, reaction, cache=signal_cache)
        except Exception as exc:  # one unavailable source must not stop the resident loop
            source_findings.append(
                {
                    "reaction_id": reaction_id or None,
                    "source_kind": str(source.get("kind") or "").strip() or None,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "posture": "reaction_skipped_source_unavailable",
                }
            )
            continue
        if not _predicate_matches(signal, dict(reaction.get("predicate") or {})):
            continue
        action = dict(reaction.get("action") or {})
        parameters = _render_parameters(dict(action.get("parameters") or {}), signal)
        operation_id = str(action.get("operation_id") or "").strip()
        if not operation_id:
            continue
        signal_digest = _reaction_signal_digest(reaction_id, signal)
        effect = dict(reaction.get("effect") or {})
        effect_observation = reaction_effect_observation(signal, effect)
        provider = str(parameters.get("provider") or "local").strip() or "local"
        jobs.append(
            {
                "kind": operation_id,
                "provider": provider,
                "params": {
                    "operation_id": operation_id,
                    "operation_parameters": parameters,
                    "source": "reactions_yaml",
                    "reaction_id": reaction_id,
                    "signal_digest": signal_digest,
                    "signal_excerpt": compact_reaction_signal(signal),
                    "effect_contract": effect,
                    "effect_observation_before": effect_observation,
                },
                "idempotency_key": f"reaction:{reaction_id}:{signal_digest}",
                "priority": {
                    "high": PRIORITY_HIGH,
                    "medium": PRIORITY_MEDIUM,
                    "low": PRIORITY_LOW,
                }.get(str(reaction.get("priority") or "medium").strip().lower(), PRIORITY_MEDIUM),
                "summary": {
                    "source": "reactions_yaml",
                    "reaction_id": reaction_id,
                    "signal_digest": signal_digest,
                    "signal_excerpt": compact_reaction_signal(signal),
                    "effect_contract": effect,
                    "effect_observation_before": effect_observation,
                },
            }
        )
    return {
        "schema": "reaction_job_derivation_report_v0",
        "jobs": jobs,
        "source_findings": source_findings,
    }


def derive_reaction_jobs(repo_root: Path) -> list[dict[str, Any]]:
    """Compatibility list view over the fault-isolating derivation report."""

    return list(derive_reaction_jobs_report(repo_root).get("jobs") or [])


def _job(
    *,
    operation_id: str,
    provider: str,
    params: Mapping[str, Any],
    idempotency_key: str,
    priority: int,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": operation_id,
        "provider": provider,
        "params": {
            "operation_id": operation_id,
            "operation_parameters": dict(params),
            "source": "metabolism_policy",
        },
        "idempotency_key": idempotency_key,
        "priority": priority,
        "summary": dict(summary or {}),
    }


def _ordered_source_kinds(raw_sources: Any) -> list[str]:
    seen: set[str] = set()
    requested: list[str] = []
    known = set(NVIDIA_CONTINUOUS_SOURCE_ORDER)
    for raw_source in raw_sources or []:
        if not isinstance(raw_source, Mapping):
            continue
        source_kind = str(raw_source.get("source_kind") or "").strip()
        if not source_kind or source_kind in seen or source_kind not in known:
            continue
        seen.add(source_kind)
        requested.append(source_kind)
    order = {kind: index for index, kind in enumerate(NVIDIA_CONTINUOUS_SOURCE_ORDER)}
    return sorted(requested, key=lambda kind: (order.get(kind, 999), kind))


def source_kind_overnight_priority(source_kind: str) -> int:
    return OVERNIGHT_SOURCE_PRIORITIES.get(str(source_kind or "").strip(), PRIORITY_LOW)


def source_kinds_overnight_priority(source_kinds: Iterable[str]) -> int:
    priorities = [source_kind_overnight_priority(kind) for kind in source_kinds if str(kind or "").strip()]
    return min(priorities) if priorities else PRIORITY_LOW


def derive_jobs_for_event(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    kind = str(event.get("kind") or "").strip()
    payload = dict(event.get("payload") or {})
    jobs: list[dict[str, Any]] = []
    if kind == "file_changed":
        category = str(payload.get("category") or "").strip()
        if category in NAVIGATOR_REFRESHABLE_CATEGORIES:
            source_kind = navigator_source_kind_for_path(str(payload.get("path") or ""), category)
            if source_kind is None:
                return jobs
            jobs.append(
                _job(
                    operation_id="navigator_refresh",
                    provider="local",
                    params={"kind": source_kind},
                    idempotency_key=f"navigator_refresh:{source_kind}_surface",
                    priority=source_kind_overnight_priority(source_kind),
                    summary={"category": category, "source_kind": source_kind},
                )
            )
    elif kind == "navigator_stale_signal":
        source_kinds = _ordered_source_kinds(payload.get("stale_sources") or [])
        if source_kinds:
            signal_digest = stable_digest(
                {
                    "kind": "navigator_stale_signal",
                    "source_kinds": source_kinds,
                    "stale_sources": [
                        {
                            "source_kind": str(raw_source.get("source_kind") or "").strip(),
                            "stale_or_missing": raw_source.get("stale_or_missing"),
                            "record_count": raw_source.get("record_count"),
                            "schema_hash": raw_source.get("schema_hash"),
                        }
                        for raw_source in payload.get("stale_sources") or []
                        if isinstance(raw_source, Mapping)
                    ],
                }
            )
            jobs.append(
                _job(
                    operation_id="nvidia_continuous_navigation_populate",
                    provider="nvidia",
                    params={
                        "batch_id": "continuous_navigation",
                        "source_kinds": ",".join(source_kinds),
                        "max_sources": 3,
                        "limit_per_source": 25,
                    },
                    idempotency_key=f"nvidia_continuous_navigation_populate:{signal_digest[:16]}",
                    priority=source_kinds_overnight_priority(source_kinds),
                    summary={
                        "source": "navigator_stale_signal",
                        "source_kinds": source_kinds,
                        "stale_source_count": len(source_kinds),
                        "signal_digest": signal_digest,
                        "provenance": {
                            "annex_slug": "lycheemem",
                            "pattern_id": "p002",
                            "adaptation": "foreground recall stays light while background consolidation/populate runs as a resident batch",
                        },
                    },
                )
            )
    elif kind == "raw_seed_entry_settled":
        family = str(payload.get("family") or "").strip()
        entry_id = str(payload.get("entry_id") or "").strip()
        if family:
            jobs.append(
                _job(
                    operation_id="kernel_sync_raw_seed_auto",
                    provider="local",
                    params={
                        "family": family,
                        "entry_id": entry_id,
                    },
                    idempotency_key=f"kernel_sync_raw_seed_auto:{family}",
                    priority=source_kind_overnight_priority("raw_seed_shards"),
                    summary={
                        "family": family,
                        "entry_id": entry_id,
                        "classification": payload.get("classification"),
                        "boundary_kind": payload.get("boundary_kind"),
                    },
                )
            )
    elif kind == "raw_seed_signal":
        counts = dict(payload.get("counts") or {})
        if int(counts.get("paragraphs_without_atoms") or 0) >= 10:
            jobs.append(
                _job(
                    operation_id="raw_seed_provider_candidate_cycle",
                    provider="local",
                    params={
                        "family": "09",
                        "substrate": "raw_seed",
                        "selection_mode": "fresh_first",
                        "providers": "nvidia_nim,openrouter_api",
                        "limit": 8,
                    },
                    idempotency_key="raw_seed_provider_candidate_cycle:raw_seed_backlog",
                    priority=source_kind_overnight_priority("raw_seed_shards"),
                    summary={
                        "source": "raw_seed_signal",
                        "lane": "type_b_provider_candidates_no_bridge",
                    },
                )
            )
        if int(counts.get("pending_routing_shards") or 0) >= 50:
            jobs.append(
                _job(
                    operation_id="nvidia_continuous_navigation_populate",
                    provider="nvidia",
                    params={
                        "batch_id": "raw_seed_route_backlog_navigation",
                        "source_kinds": "raw_seed_shards,raw_seed_paragraphs,raw_seed_navigation",
                        "max_sources": 3,
                        "limit_per_source": 50,
                    },
                    idempotency_key="nvidia_continuous_navigation_populate:raw_seed_route_backlog",
                    priority=source_kinds_overnight_priority(
                        ["raw_seed_shards", "raw_seed_paragraphs", "raw_seed_navigation"]
                    ),
                    summary={
                        "source": "raw_seed_signal",
                        "lane": "nvidia_navigation_population_no_bridge",
                    },
                )
            )
    elif kind == "work_ledger_signal":
        # Work-ledger lifecycle reconciliation is owned directly by the
        # resident daemon. A stale append obligation is a semantic status
        # condition, not projection drift; rebuilding read indexes cannot
        # settle it and must not be scheduled as a surrogate repair.
        return jobs
    elif kind == "annex_upstream_poll_signal":
        jobs.append(
            _job(
                operation_id="annex_sync_digest_pull",
                provider="local",
                params={
                    "stale_days": int(payload.get("stale_days") or ANNEX_UPSTREAM_STALE_THRESHOLD_DAYS),
                    "limit": int(payload.get("chunk_limit") or ANNEX_UPSTREAM_POLL_CHUNK_SIZE),
                },
                idempotency_key="annex_sync_digest_pull:metabolism_chunk",
                priority=source_kind_overnight_priority("annex_notes"),
                summary={
                    "source": "annex_upstream_poll_signal",
                    "bucket": str(payload.get("bucket") or ""),
                    "poll_interval_seconds": int(
                        payload.get("poll_interval_seconds") or ANNEX_UPSTREAM_POLL_INTERVAL_SECONDS
                    ),
                    "chunk_limit": int(payload.get("chunk_limit") or ANNEX_UPSTREAM_POLL_CHUNK_SIZE),
                    "stale_days": int(payload.get("stale_days") or ANNEX_UPSTREAM_STALE_THRESHOLD_DAYS),
                    "metabolism_shape": "bounded rotating upstream annex refresh",
                },
            )
        )
    elif kind == "market_fire":
        fire_point = str(payload.get("fire_point") or "").strip()
        market_date = str(payload.get("market_date") or "").strip()
        if fire_point and market_date:
            feed_run_id = str(payload.get("feed_run_id") or f"FEEDS_{market_date.replace('-', '')}_{fire_point}").strip()
            operation_parameters = {
                "fire_point": fire_point,
                "market_date": market_date,
                "snapshot_key": str(payload.get("snapshot_key") or f"market_snapshot:{fire_point}:{market_date}"),
            }
            for key in (
                "weekday",
                "is_weekend",
                "market_timezone",
                "target_time_market",
                "target_time_utc",
                "target_time_operator_local",
                "operator_timezone",
            ):
                if payload.get(key) is not None:
                    operation_parameters[key] = payload.get(key)
            jobs.append(
                _job(
                    operation_id="market_snapshot",
                    provider="local",
                    params=operation_parameters,
                    idempotency_key=f"market_snapshot:{fire_point}:{market_date}",
                    priority=PRIORITY_HIGH,
                    summary={
                        "fire_point": fire_point,
                        "market_date": market_date,
                        "snapshot_key": operation_parameters["snapshot_key"],
                    },
                )
            )
            bundle_parameters = {
                key: value
                for key, value in operation_parameters.items()
                if key
                in {
                    "fire_point",
                    "market_date",
                    "market_timezone",
                    "target_time_market",
                    "target_time_utc",
                }
            }
            bundle_parameters["run_id"] = feed_run_id
            bundle_parameters["bundle_key"] = f"market_feed_bundle:{fire_point}:{market_date}"
            jobs.append(
                _job(
                    operation_id="market_feed_bundle",
                    provider="local",
                    params=bundle_parameters,
                    idempotency_key=f"market_feed_bundle:{fire_point}:{market_date}",
                    priority=PRIORITY_HIGH,
                    summary={
                        "fire_point": fire_point,
                        "market_date": market_date,
                        "run_id": feed_run_id,
                        "bundle_key": bundle_parameters["bundle_key"],
                    },
                )
            )
    elif kind == "operation_completed":
        operation_id = str(payload.get("operation_id") or "").strip()
        returncode = int(payload.get("returncode") or 0)
        params = dict(payload.get("resolved_parameters") or {})
        if returncode != 0:
            return jobs
        if operation_id == "python_std_compliance_cycle":
            jobs.append(
                _job(
                    operation_id="kernel_embed_refresh",
                    provider="local",
                    params={"source": "python_holographic"},
                    idempotency_key="kernel_embed_refresh:python_holographic_surface",
                    priority=source_kind_overnight_priority("python_holographic"),
                )
            )
        elif operation_id in {"kernel_embed_refresh", "navigator_refresh"}:
            source = str(params.get("source") or params.get("kind") or "doctrine").strip()
            jobs.append(
                _job(
                    operation_id="semantic_route_refresh",
                    provider="local",
                    params={"source": source},
                    idempotency_key=f"semantic_route_refresh:{source}_surface",
                    priority=source_kind_overnight_priority(source),
                )
            )
        elif operation_id in {"kernel_sync_raw_seed", "kernel_sync_raw_seed_auto"}:
            family = str(params.get("family") or "09").strip() or "09"
            jobs.append(
                _job(
                    operation_id="raw_seed_provider_candidate_cycle",
                    provider="local",
                    params={
                        "family": family,
                        "substrate": "raw_seed",
                        "selection_mode": "fresh_first",
                        "providers": "nvidia_nim,openrouter_api",
                        "limit": 8,
                    },
                    idempotency_key=f"raw_seed_provider_candidate_cycle:after_sync:{family}",
                    priority=source_kind_overnight_priority("raw_seed_shards"),
                    summary={
                        "source": "operation_completed",
                        "operation_id": operation_id,
                        "lane": "type_b_provider_candidates_no_bridge",
                    },
                )
            )
        elif operation_id == "raw_seed_distill_cycle":
            jobs.append(
                _job(
                    operation_id="raw_seed_route_review",
                    provider="chatgpt",
                    params={
                        "family": "09",
                        "provider": "chatgpt",
                        "cohort_size": 10,
                        "wave_width": 3,
                    },
                    idempotency_key="raw_seed_route_review:after_distill",
                    priority=PRIORITY_HIGH,
                )
            )
    return jobs


def provider_budget_for(provider: str) -> dict[str, Any]:
    return dict(DEFAULT_PROVIDER_BUDGETS.get(provider) or DEFAULT_PROVIDER_BUDGETS["local"])
