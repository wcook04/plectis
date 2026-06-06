"""
[PURPOSE]
- Teleology: Apply and metabolize command group for the kernel CLI -- plan execution,
  validated apply loops, session-based apply, rollback, validation, quick-apply,
  check, scratchpad, and metabolize (observe-to-reference artifact promotion).
- Mechanism: Each cmd_* function orchestrates an apply pipeline stage (routing,
  mutation, validation, builder rebuild, optional rollback) and emits structured
  JSON results via the kernel output layer.

[INTERFACE]
- Exports: cmd_apply, cmd_apply_loop, cmd_apply_session, cmd_apply_session_loop,
           cmd_apply_rollback, cmd_apply_validate, cmd_quick_apply,
           cmd_check, cmd_scratchpad, cmd_metabolize

[FLOW]
- kernel.py dispatch imports and calls the relevant cmd_* function based on CLI flags.
- Apply helpers resolve plan payloads, run mutation via tools.meta.apply, and
  write receipts / loop results to APPLY_RESULT / APPLY_LOOP_RESULT.

[DEPENDENCIES]
- system.lib.kernel.state: REPO_ROOT, rel(), path constants
- system.lib.kernel.output: emit_json, emit_navigation
- system.lib.kernel.helpers: safe_load_json, load_builder_config
- system.lib.kernel_navigation: KernelNavigation, NavigationResult
- system.lib.markdown_routing: parse_frontmatter, markdown_kind, etc.
- system.lib.phase_harbor: ingest_apply_loop_result
- system.lib.hologram_index: load/query/summarize hologram entries
- tools.meta.apply: apply engine and snapshot restore
- kernel: private helpers not yet extracted (_compile_session_apply_payload, etc.)

[CONSTRAINTS]
- All filesystem mutation goes through tools.meta.apply; this module never writes
  target files directly.
- Exit codes: 0 = success, 1 = failure.
- When-needed: Open when the kernel CLI task is about previewing, validating, replaying, or looping apply plans rather than building navigation context.
- Escalates-to: kernel.py; codex/doctrine/skills/kernel/apply.md; system/lib/kernel/commands/navigate.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from system.lib.kernel import state
from system.lib.kernel.output import emit_json, emit_navigation
from system.lib.kernel.helpers import safe_load_json, load_builder_config
from system.lib.kernel_navigation import KernelNavigation, NavigationResult
from system.lib.hologram_index import (
    load_hologram_index,
    query_hologram_dependencies,
    summarize_hologram_entry,
)
from system.lib.markdown_routing import (
    extract_observe_artifact_payload,
    markdown_kind,
    normalize_repo_relative_path,
    parse_frontmatter,
    propose_patch_map_from_observe_payload,
    resolve_reference_artifact_target_family,
)
from system.lib.observe_sessions import (
    load_session_candidates,
    session_resolution_sort_key,
)
from system.lib.phase_harbor import ingest_apply_loop_result


# ---------------------------------------------------------------------------
# Private helpers -- thin wrappers / local utilities
# ---------------------------------------------------------------------------

def _rel(p: Path) -> str:
    """[ACTION] Repo-relative path string via state.rel()."""
    return state.rel(p)


def _safe_read_text(path: Path) -> str | None:
    """[ACTION] Best-effort file read returning None on any OS/encoding error."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    except OSError:
        return None


def _normalize_lookup_token(value: object) -> str:
    """[ACTION] Lowercase alphanumeric-only token for fuzzy matching."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _markdown_title(text: str, *, fallback: str) -> str:
    """[ACTION] Extract first H1 title from markdown text, or use fallback."""
    _, body = parse_frontmatter(text)
    match = re.search(r"(?m)^#\s+(.+?)\s*$", body or text)
    if match:
        return match.group(1).strip()
    return fallback


def _repo_markdown_paths(root: Path) -> list[Path]:
    """[ACTION] Collect all .md files under root, skipping noisy directories."""
    paths: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            continue
        if any(part in state.METABOLIZE_MARKDOWN_SKIP_DIRS for part in rel_path.parts):
            continue
        paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Lazy imports from kernel.py for helpers not yet extracted
# ---------------------------------------------------------------------------

def _observe_history_entry_paths() -> list[Path]:
    """[ACTION] Sorted list of observe history JSON entries (newest first)."""
    if not state.OBSERVE_HISTORY_ENTRIES_DIR.exists():
        return []
    return sorted(
        state.OBSERVE_HISTORY_ENTRIES_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _resolve_observe_entry(ref: str | None) -> Path | None:
    """[ACTION] Resolve an observe entry reference to a history JSON path."""
    token = str(ref or "latest").strip() or "latest"
    entries = _observe_history_entry_paths()
    if token == "latest":
        return entries[0] if entries else None

    candidate = Path(token)
    if candidate.is_absolute() or "/" in token:
        resolved = (candidate if candidate.is_absolute() else (state.REPO_ROOT / candidate)).resolve()
        if resolved.is_file():
            return resolved if resolved.exists() else None
        if resolved.is_dir():
            token = resolved.name

    for entry_path in entries:
        try:
            payload = json.loads(entry_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        observe_id = str(payload.get("observe_id", "")).strip()
        dump_dir = str(payload.get("dump_dir", "")).strip()
        dump_name = Path(dump_dir).name if dump_dir else ""
        if token in {observe_id, entry_path.stem, entry_path.name, dump_name}:
            return entry_path
    return None


def _observe_response_index(payload: dict[str, object]) -> list[dict[str, object]]:
    """[ACTION] Extract response index from an observe history payload."""
    from system.lib.observe_surfaces import observe_response_index
    return observe_response_index(payload)


def _clean_optional_text(value: object) -> str:
    """[ACTION] Coerce value to stripped string, empty-string on None."""
    if value is None:
        return ""
    return str(value).strip()


def _select_observe_source_artifact(payload: dict[str, Any]) -> dict[str, Any] | None:
    """[ACTION] Select the best observe source artifact from a history entry payload."""
    candidate_paths: list[tuple[str, str]] = []
    result_note = payload.get("result_note")
    if isinstance(result_note, dict):
        result_note_path = _clean_optional_text(result_note.get("path"))
        if result_note_path:
            candidate_paths.append(("result_note", result_note_path))

    continuation = payload.get("continuation")
    if isinstance(continuation, dict):
        for path_value in continuation.get("read_paths", []):
            candidate = _clean_optional_text(path_value)
            if candidate:
                candidate_paths.append(("continuation", candidate))

    for item in _observe_response_index(payload):
        response_file = str(item.get("response_file") or "").strip()
        if response_file:
            candidate_paths.append(("response_file", response_file))

    seen_paths: set[str] = set()
    for origin, raw_path in candidate_paths:
        normalized = normalize_repo_relative_path(raw_path, repo_root=state.REPO_ROOT)
        if not normalized or normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        text = _safe_read_text(state.REPO_ROOT / normalized)
        if text is None:
            continue
        try:
            artifact = extract_observe_artifact_payload(
                source_text=text,
                source_artifact=normalized,
            )
        except ValueError:
            continue
        artifact["path"] = normalized
        artifact["origin"] = origin
        return artifact
    return None


def _score_metabolize_source(payload: dict[str, Any], target: dict[str, Any]) -> tuple[int, list[str]]:
    """[ACTION] Score an observe history entry as a metabolize source for a given target."""
    score = 0
    reasons: list[str] = []
    observe_id = str(payload.get("observe_id") or "").strip()
    promotion = payload.get("promotion")
    promotion_target = ""
    if isinstance(promotion, dict):
        promotion_target = str(promotion.get("target_path") or "").strip()

    reference_maps = payload.get("reference_maps")
    resolved_reference_maps = (
        reference_maps.get("resolved", [])
        if isinstance(reference_maps, dict) and isinstance(reference_maps.get("resolved"), list)
        else []
    )

    target_path = str(target.get("path") or "").strip()
    target_kind = str(target.get("kind") or "").strip()
    target_id = str(target.get("id") or "").strip()
    target_boundary = str(target.get("boundary") or "").strip()

    if target_kind == "living_map":
        if observe_id and observe_id == str(target.get("last_observe_id") or "").strip():
            score += 1200
            reasons.append("observe_id matches living_map.last_observe_id")
        if promotion_target and promotion_target == target_path:
            score += 1000
            reasons.append("promotion target matches living-map path")
        for entry in resolved_reference_maps:
            if not isinstance(entry, dict):
                continue
            if target_path and str(entry.get("path") or "").strip() == target_path:
                score += 900
                reasons.append("reference_maps path matches living-map path")
                break
        for entry in resolved_reference_maps:
            if not isinstance(entry, dict):
                continue
            if target_id and str(entry.get("id") or "").strip() == target_id:
                score += 850
                reasons.append("reference_maps id matches living-map id")
                break
        for entry in resolved_reference_maps:
            if not isinstance(entry, dict):
                continue
            if target_boundary and str(entry.get("boundary") or "").strip() == target_boundary:
                score += 700
                reasons.append("reference_maps boundary matches living-map boundary")
                break
    elif target_kind == "idea_packet":
        if promotion_target and promotion_target == target_path:
            score += 1000
            reasons.append("promotion target matches idea-packet path")
        companion_maps = {
            normalize_repo_relative_path(item, repo_root=state.REPO_ROOT) or str(item).strip()
            for item in target.get("companion_maps", [])
            if str(item).strip()
        }
        primary_boundaries = {
            str(item).strip()
            for item in target.get("primary_boundaries", [])
            if str(item).strip()
        }
        for entry in resolved_reference_maps:
            if not isinstance(entry, dict):
                continue
            entry_path = str(entry.get("path") or "").strip()
            entry_boundary = str(entry.get("boundary") or "").strip()
            if entry_path and entry_path in companion_maps:
                score += 750
                reasons.append("reference_maps path matches idea-packet companion_map")
                break
            if entry_boundary and entry_boundary in primary_boundaries:
                score += 500
                reasons.append("reference_maps boundary matches idea-packet primary_boundaries")
                break
    else:
        if promotion_target and promotion_target == target_path:
            score += 1000
            reasons.append("promotion target matches authored-note path")

    return score, reasons


# ---------------------------------------------------------------------------
# Apply plan helpers
# ---------------------------------------------------------------------------

def _normalize_apply_plan_payload(payload: object) -> dict[str, object]:
    """[ACTION] Normalize a raw apply plan payload into a dict with operations."""
    if not isinstance(payload, dict):
        raise ValueError("Apply plan payload must be a JSON object.")
    if "operations" in payload:
        plan_body = payload
    elif "plan" in payload and isinstance(payload.get("plan"), dict):
        plan_body = payload["plan"]
    else:
        plan_body = payload
    if not isinstance(plan_body, dict):
        raise ValueError("Apply plan payload must resolve to an object containing operations.")
    return plan_body


def _coerce_apply_invocation_context(payload: object) -> dict[str, object]:
    """[ACTION] Extract invocation context (miner_chain, apply_config) from plan payload."""
    if not isinstance(payload, dict):
        return {}
    miner_chain = payload.get("miner_chain")
    context: dict[str, object] = {}
    if isinstance(miner_chain, dict):
        context["miner_chain"] = dict(miner_chain)
    apply_config = payload.get("apply_config")
    if isinstance(apply_config, dict):
        context["apply_config"] = dict(apply_config)
    compiled_operations = payload.get("compiled_operations")
    if isinstance(compiled_operations, list):
        context["compiled_operations"] = [dict(item) for item in compiled_operations if isinstance(item, dict)]
    return context


def _parse_apply_plan_file_payload(payload: object) -> tuple[dict[str, object], dict[str, object]]:
    """[ACTION] Parse a full plan file payload into (plan_body, invocation_context)."""
    if isinstance(payload, dict) and isinstance(payload.get("apply_config"), dict):
        plan_body = _normalize_apply_plan_payload(payload["apply_config"].get("plan"))
        return plan_body, _coerce_apply_invocation_context(payload)
    return _normalize_apply_plan_payload(payload), _coerce_apply_invocation_context(payload)


def _read_apply_plan(plan_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    """[ACTION]
    - Teleology: Resolve the authoritative disk-read seam for kernel apply plans before preview, validation, or live execution.
    - Mechanism: Read JSON from `plan_path`, raise FileNotFoundError or ValueError on invalid inputs, and hand the payload to `_parse_apply_plan_file_payload`.
    - When-needed: Open when the routing question is specifically about `_read_apply_plan` as the helper that loads persisted apply plans from disk for downstream apply commands.
    - Escalates-to: _parse_apply_plan_file_payload; cmd_apply; cmd_validate_apply
    - Navigation-group: kernel_lib
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"Apply plan not found: {plan_path}")
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    return _parse_apply_plan_file_payload(payload)


def _run_apply_plan(
    plan_body: dict[str, object],
    *,
    dry_run: bool,
    capture_diffs: bool = True,
    result_path: Path | None = None,
    enforce_target_routing: bool = False,
    preferred_target_family: str | None = None,
) -> dict[str, object]:
    """[ACTION] Execute an apply plan via tools.meta.apply and write result to disk."""
    from tools.meta import apply as meta_apply

    config = {
        "mode": "apply",
        "plan": plan_body,
        "dry_run": dry_run,
        "capture_diffs": capture_diffs,
        "enforce_target_routing": enforce_target_routing,
        "preferred_target_family": preferred_target_family,
        "root_hint": str(state.REPO_ROOT),
    }
    result = meta_apply.run(config)
    target_result_path = result_path or state.APPLY_RESULT
    target_result_path.parent.mkdir(parents=True, exist_ok=True)
    target_result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Metabolize target / source resolution
# ---------------------------------------------------------------------------

def _resolve_idea_packet_target(selector: str) -> dict[str, Any]:
    """[ACTION] Resolve a metabolize target selector to an idea_packet note."""
    requested = str(selector or "").strip()
    if not requested:
        raise ValueError("metabolize target is required")

    normalized_requested = normalize_repo_relative_path(requested, repo_root=state.REPO_ROOT) or ""
    if normalized_requested:
        direct_path = state.REPO_ROOT / normalized_requested
        direct_text = _safe_read_text(direct_path)
        if direct_text is not None and markdown_kind(direct_text) == "idea_packet":
            card, body = parse_frontmatter(direct_text)
            section_titles = re.findall(r"(?m)^##\s+(.+?)\s*$", body)
            return {
                "kind": "idea_packet",
                "requested": requested,
                "resolution_mode": "path",
                "path": normalized_requested,
                "title": _markdown_title(direct_text, fallback=direct_path.stem),
                "id": str(card.get("id", "")).strip() or None,
                "summary": str(card.get("summary", "")).strip() or None,
                "primary_boundaries": [str(item).strip() for item in card.get("primary_boundaries", []) if str(item).strip()] if isinstance(card.get("primary_boundaries"), list) else [],
                "companion_maps": [str(item).strip() for item in card.get("companion_maps", []) if str(item).strip()] if isinstance(card.get("companion_maps"), list) else [],
                "section_titles": section_titles,
                "frontmatter": card,
            }

    query_token = _normalize_lookup_token(requested)
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for path in _repo_markdown_paths(state.REPO_ROOT):
        text = _safe_read_text(path)
        if text is None or markdown_kind(text) != "idea_packet":
            continue

        rel_path = _rel(path)
        card, body = parse_frontmatter(text)
        title = _markdown_title(text, fallback=path.stem)
        entry_id = str(card.get("id", "")).strip() or None
        primary_boundaries = [
            str(item).strip()
            for item in card.get("primary_boundaries", [])
            if str(item).strip()
        ] if isinstance(card.get("primary_boundaries"), list) else []
        companion_maps = [
            str(item).strip()
            for item in card.get("companion_maps", [])
            if str(item).strip()
        ] if isinstance(card.get("companion_maps"), list) else []
        section_titles = re.findall(r"(?m)^##\s+(.+?)\s*$", body)

        score = 0
        if requested and requested == entry_id:
            score += 900
        if normalized_requested:
            if normalized_requested == rel_path:
                score += 1000
            elif rel_path.endswith(normalized_requested):
                score += 850
        if query_token:
            for value, weight in (
                (title, 500),
                (path.stem, 420),
                (entry_id or "", 650),
                (rel_path, 220),
            ):
                if query_token and query_token == _normalize_lookup_token(value):
                    score += weight
                elif query_token and query_token in _normalize_lookup_token(value):
                    score += max(100, weight // 3)

        if score <= 0:
            continue

        try:
            mtime_epoch = int(path.stat().st_mtime)
        except OSError:
            mtime_epoch = 0

        candidates.append(
            (
                score,
                mtime_epoch,
                rel_path,
                {
                    "kind": "idea_packet",
                    "requested": requested,
                    "resolution_mode": "token",
                    "path": rel_path,
                    "title": title,
                    "id": entry_id,
                    "summary": str(card.get("summary", "")).strip() or None,
                    "primary_boundaries": primary_boundaries,
                    "companion_maps": companion_maps,
                    "section_titles": section_titles,
                    "frontmatter": card,
                },
            )
        )

    if not candidates:
        raise ValueError(f"Could not resolve idea_packet target: {requested}")

    candidates.sort(reverse=True)
    return candidates[0][3]


def _resolve_authored_obsidian_note_target(selector: str) -> dict[str, Any]:
    """[ACTION] Resolve a metabolize target selector to an authored obsidian note."""
    requested = str(selector or "").strip()
    if not requested:
        raise ValueError("authored note target selector is required")
    normalized_requested = normalize_repo_relative_path(requested, repo_root=state.REPO_ROOT)
    if normalized_requested:
        direct_text = _safe_read_text(state.REPO_ROOT / normalized_requested)
        if direct_text is not None:
            try:
                _, note_kind = resolve_reference_artifact_target_family(
                    target_text=direct_text,
                    target_path=normalized_requested,
                )
            except ValueError:
                pass
            else:
                card, body = parse_frontmatter(direct_text)
                section_titles = re.findall(r"(?m)^##\s+(.+?)\s*$", body)
                return {
                    "kind": note_kind,
                    "target_family": "authored_obsidian_note",
                    "requested": requested,
                    "resolution_mode": "path",
                    "path": normalized_requested,
                    "title": _markdown_title(direct_text, fallback=Path(normalized_requested).stem),
                    "id": str(card.get("id", "")).strip() or None,
                    "summary": str(card.get("summary", "")).strip() or None,
                    "section_titles": section_titles,
                    "frontmatter": card,
                }

    query_token = _normalize_lookup_token(requested)
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for path in _repo_markdown_paths(state.REPO_ROOT):
        rel_path = _rel(path)
        if not rel_path.startswith("obsidian/"):
            continue
        text = _safe_read_text(path)
        if text is None:
            continue
        try:
            _, note_kind = resolve_reference_artifact_target_family(
                target_text=text,
                target_path=rel_path,
            )
        except ValueError:
            continue

        card, body = parse_frontmatter(text)
        title = _markdown_title(text, fallback=path.stem)
        entry_id = str(card.get("id", "")).strip() or None
        section_titles = re.findall(r"(?m)^##\s+(.+?)\s*$", body)

        score = 0
        if requested and requested == entry_id:
            score += 900
        if normalized_requested:
            if normalized_requested == rel_path:
                score += 1000
            elif rel_path.endswith(normalized_requested):
                score += 850
        if query_token:
            for value, weight in (
                (title, 500),
                (path.stem, 420),
                (entry_id or "", 650),
                (rel_path, 220),
            ):
                if query_token and query_token == _normalize_lookup_token(value):
                    score += weight
                elif query_token and query_token in _normalize_lookup_token(value):
                    score += max(100, weight // 3)

        if score <= 0:
            continue

        try:
            mtime_epoch = int(path.stat().st_mtime)
        except OSError:
            mtime_epoch = 0

        candidates.append(
            (
                score,
                mtime_epoch,
                rel_path,
                {
                    "kind": note_kind,
                    "target_family": "authored_obsidian_note",
                    "requested": requested,
                    "resolution_mode": "token",
                    "path": rel_path,
                    "title": title,
                    "id": entry_id,
                    "summary": str(card.get("summary", "")).strip() or None,
                    "section_titles": section_titles,
                    "frontmatter": card,
                },
            )
        )

    if not candidates:
        raise ValueError(f"Could not resolve authored obsidian note target: {requested}")

    candidates.sort(reverse=True)
    return candidates[0][3]


def _resolve_metabolize_target(selector: str) -> tuple[dict[str, Any], list[str]]:
    """[ACTION] Resolve a metabolize target selector to a target dict (living_map, idea_packet, or authored note)."""
    warnings: list[str] = []
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_map(selector)
        payload = result.payload
        living_map = payload.get("living_map", {})
        target = {
            "kind": "living_map",
            "requested": selector,
            "resolution_mode": payload.get("selector_resolution", {}).get("mode"),
            "path": str(living_map.get("path") or ""),
            "title": living_map.get("title"),
            "id": living_map.get("id"),
            "boundary": living_map.get("boundary"),
            "summary": living_map.get("summary"),
            "last_observe_id": living_map.get("last_observe_id"),
            "default_section": "HISTORY",
            "section_titles": ["KNOWN", "BROKEN", "UNKNOWN", "HISTORY"],
            "frontmatter": payload.get("frontmatter", {}),
        }
        warnings.extend(result.warnings)
        return target, warnings
    except ValueError as map_exc:
        map_error = str(map_exc)

    try:
        idea_packet = _resolve_idea_packet_target(selector)
    except ValueError as idea_exc:
        warnings.append(
            f"Living-map resolution did not match `{selector}`; falling back to idea_packet resolution ({map_error})."
        )
        authored_note = _resolve_authored_obsidian_note_target(selector)
        warnings.append(
            f"Idea-packet resolution did not match `{selector}`; falling back to authored obsidian note resolution ({idea_exc})."
        )
        return authored_note, warnings

    warnings.append(
        f"Living-map resolution did not match `{selector}`; falling back to idea_packet resolution ({map_error})."
    )
    return idea_packet, warnings


def _resolve_metabolize_source(
    *,
    target: dict[str, Any],
    from_observe: str | None = None,
    source_artifact: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """[ACTION] Resolve the observe source artifact for a metabolize operation."""
    warnings: list[str] = []
    if from_observe and source_artifact:
        raise ValueError("Use either --from-observe or --source-artifact, not both.")

    if source_artifact:
        normalized = normalize_repo_relative_path(source_artifact, repo_root=state.REPO_ROOT)
        if not normalized:
            raise ValueError(f"source_artifact must resolve inside the repo: {source_artifact}")
        text = _safe_read_text(state.REPO_ROOT / normalized)
        if text is None:
            raise ValueError(f"source_artifact not found: {normalized}")
        artifact = extract_observe_artifact_payload(
            source_text=text,
            source_artifact=normalized,
        )
        return (
            {
                "selection_mode": "explicit_source_artifact",
                "artifact_path": normalized,
                "artifact_origin": "source_artifact",
                "observe_id": str(artifact.get("observe_id") or "").strip() or None,
                "history_entry": None,
                "selection_reasons": ["explicit source_artifact"],
                "artifact": artifact,
            },
            warnings,
        )

    if from_observe:
        entry_path = _resolve_observe_entry(from_observe)
        if entry_path is None or not entry_path.exists():
            raise ValueError(f"Observe history entry not found: {from_observe}")
        try:
            payload = json.loads(entry_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Failed to read observe history entry: {exc}") from exc
        artifact = _select_observe_source_artifact(payload if isinstance(payload, dict) else {})
        if artifact is None:
            raise ValueError(f"Observe history entry has no parseable result note or response artifact: {from_observe}")
        return (
            {
                "selection_mode": "explicit_observe_entry",
                "artifact_path": str(artifact.get("path") or ""),
                "artifact_origin": str(artifact.get("origin") or ""),
                "observe_id": str(payload.get("observe_id") or "").strip() or None,
                "history_entry": _rel(entry_path),
                "selection_reasons": [f"explicit observe entry `{from_observe}`"],
                "artifact": artifact,
            },
            warnings,
        )

    candidates: list[dict[str, Any]] = []
    fallback_candidates: list[dict[str, Any]] = []
    for entry_path in _observe_history_entry_paths():
        try:
            payload = json.loads(entry_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        artifact = _select_observe_source_artifact(payload)
        if artifact is None:
            continue
        score, reasons = _score_metabolize_source(payload, target)
        candidate = {
            "selection_mode": "auto",
            "artifact_path": str(artifact.get("path") or ""),
            "artifact_origin": str(artifact.get("origin") or ""),
            "observe_id": str(payload.get("observe_id") or "").strip() or None,
            "history_entry": _rel(entry_path),
            "selection_reasons": reasons,
            "artifact": artifact,
            "score": score,
        }
        if score > 0:
            candidates.append(candidate)
        else:
            fallback_candidates.append(candidate)

    if candidates:
        candidates.sort(
            key=lambda item: (
                int(item.get("score") or 0),
                str(item.get("history_entry") or ""),
            ),
            reverse=True,
        )
        return candidates[0], warnings

    if fallback_candidates:
        warnings.append(
            "No observe artifact linked directly to the target was found; falling back to the latest parseable observe artifact."
        )
        return fallback_candidates[0], warnings

    raise ValueError("No parseable observe result note or response artifact was found in observe history.")


def _resolve_metabolize_section(target: dict[str, Any], requested_section: str | None) -> tuple[str, list[str]]:
    """[ACTION] Resolve the section name for a metabolize operation."""
    warnings: list[str] = []
    target_kind = str(target.get("kind") or "").strip()
    section = str(requested_section or "").strip()
    if target_kind == "living_map":
        return section or str(target.get("default_section") or "HISTORY"), warnings

    if section:
        return section, warnings

    section_titles = [str(item).strip() for item in target.get("section_titles", []) if str(item).strip()]
    if len(section_titles) == 1:
        if target_kind == "idea_packet":
            warnings.append(f"Auto-selected idea-packet section `{section_titles[0]}` because it is the only heading.")
        else:
            warnings.append(f"Auto-selected note section `{section_titles[0]}` because it is the only heading.")
        return section_titles[0], warnings

    if target_kind == "idea_packet":
        raise ValueError("idea_packet metabolize targets require --section unless the note has exactly one section heading.")
    raise ValueError("authored obsidian note metabolize targets require --section unless the note has exactly one section heading.")


# ---------------------------------------------------------------------------
# Apply loop helpers
# ---------------------------------------------------------------------------

_PHASE_CONTEXT_NOTE_SUFFIXES = ("synth_seed.md", "observe_seed.md", "raw_seed.md", "reference.md", "plan.md")


def _phase_entry_from_markdown_card(path: Path) -> dict[str, str] | None:
    """[ACTION] Extract phase entry from a markdown file's frontmatter."""
    if not path.exists() or path.suffix.lower() not in {".md", ".markdown"}:
        return None
    try:
        card, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    phase_id = str(card.get("phase_id") or "").strip()
    phase_title = str(card.get("phase_title") or "").strip()
    phase_dir = str(card.get("phase_dir") or "").strip()
    if not phase_id or not phase_title or not phase_dir:
        return None
    return {
        "phase_id": phase_id,
        "phase_number": str(card.get("phase_number") or "").strip(),
        "phase_title": phase_title,
        "phase_dir": phase_dir,
    }


def _phase_entry_from_plan_payload(plan_payload: Mapping[str, object]) -> dict[str, str] | None:
    """[ACTION] Extract phase entry from an observe plan payload's context files."""
    context_candidates: list[str] = []
    for item in plan_payload.get("context_files", []) if isinstance(plan_payload.get("context_files"), list) else []:
        token = str(item or "").strip()
        if token:
            context_candidates.append(token)
    groups = plan_payload.get("groups", []) if isinstance(plan_payload.get("groups"), list) else []
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        for item in group.get("context_files", []) if isinstance(group.get("context_files"), list) else []:
            token = str(item or "").strip()
            if token:
                context_candidates.append(token)
    for token in context_candidates:
        if not token.endswith(_PHASE_CONTEXT_NOTE_SUFFIXES):
            continue
        candidate = (state.REPO_ROOT / token).resolve()
        phase_entry = _phase_entry_from_markdown_card(candidate)
        if phase_entry is not None:
            return phase_entry
    return None


def _resolve_apply_loop_phase_entry(
    invocation_context: Mapping[str, object],
) -> tuple[dict[str, str] | None, dict[str, object] | None, str | None]:
    """[ACTION] Resolve phase context from an apply loop invocation context."""
    miner_chain = invocation_context.get("miner_chain") if isinstance(invocation_context.get("miner_chain"), Mapping) else {}
    session_manifest_rel = str(miner_chain.get("session_manifest") or "").strip() if isinstance(miner_chain, Mapping) else ""
    manifest_payload: dict[str, object] | None = None
    if session_manifest_rel:
        manifest_path = (state.REPO_ROOT / session_manifest_rel).resolve()
        manifest_payload = safe_load_json(manifest_path)
    if isinstance(manifest_payload, Mapping):
        session_phase = manifest_payload.get("session_phase") if isinstance(manifest_payload.get("session_phase"), Mapping) else {}
        phase_id = str(session_phase.get("phase_id") or "").strip()
        phase_title = str(session_phase.get("phase_title") or "").strip()
        phase_dir = str(session_phase.get("phase_dir") or "").strip()
        if phase_id and phase_title and phase_dir:
            return (
                {
                    "phase_id": phase_id,
                    "phase_number": str(session_phase.get("phase_number") or "").strip(),
                    "phase_title": phase_title,
                    "phase_dir": phase_dir,
                },
                dict(manifest_payload),
                session_manifest_rel or None,
            )
        plan_snapshot_rel = str(manifest_payload.get("plan_snapshot_path") or "").strip()
        if plan_snapshot_rel:
            plan_payload = safe_load_json((state.REPO_ROOT / plan_snapshot_rel).resolve())
            if isinstance(plan_payload, Mapping):
                phase_entry = _phase_entry_from_plan_payload(plan_payload)
                if phase_entry is not None:
                    return phase_entry, dict(manifest_payload), session_manifest_rel or None
    promoted_plan_note = str(miner_chain.get("promoted_plan_note") or "").strip() if isinstance(miner_chain, Mapping) else ""
    if promoted_plan_note:
        phase_entry = _phase_entry_from_markdown_card((state.REPO_ROOT / promoted_plan_note).resolve())
        if phase_entry is not None:
            return phase_entry, manifest_payload, session_manifest_rel or None
    return None, manifest_payload, session_manifest_rel or None


def _maybe_write_apply_loop_phase_harbor(
    *,
    live: bool,
    invocation_context: Mapping[str, object],
    apply_loop_result: Mapping[str, object],
) -> dict[str, object]:
    """[ACTION] Conditionally write apply loop result into the phase harbor."""
    if not live:
        return {
            "status": "skipped",
            "reason": "preview_mode",
        }
    phase_entry, manifest_payload, session_manifest_rel = _resolve_apply_loop_phase_entry(invocation_context)
    if phase_entry is None:
        return {
            "status": "skipped",
            "reason": "phase_context_unavailable",
            "session_manifest": session_manifest_rel,
        }
    miner_chain = invocation_context.get("miner_chain") if isinstance(invocation_context.get("miner_chain"), Mapping) else {}
    readback_state = (manifest_payload or {}).get("readback_state") if isinstance(manifest_payload, Mapping) else {}
    readback_state = readback_state if isinstance(readback_state, Mapping) else {}
    source = {
        "session_manifest": session_manifest_rel,
        "observe_id": str((manifest_payload or {}).get("observe_id") or "").strip() or None,
        "primary_artifact": (
            str(miner_chain.get("primary_artifact") or "").strip()
            or str(readback_state.get("primary_artifact") or "").strip()
            or None
        ),
        "apply_loop_result_path": _rel(state.APPLY_LOOP_RESULT),
    }
    try:
        writeback = ingest_apply_loop_result(
            state.REPO_ROOT,
            phase_entry,
            apply_loop_result,
            source=source,
            live=True,
        )
    except Exception as exc:
        return {
            "status": "failure",
            "reason": str(exc),
            "session_manifest": session_manifest_rel,
            "phase_entry": phase_entry,
        }
    return {
        "status": str(writeback.get("status") or "applied"),
        "session_manifest": session_manifest_rel,
        "phase_entry": phase_entry,
        "meta_ledger_path": writeback.get("meta_ledger_path"),
        "entry": writeback.get("entry"),
        "writes": writeback.get("writes"),
    }


def _summarize_apply_result(result: dict[str, object]) -> dict[str, object]:
    """[ACTION] Extract a compact summary from a full apply result."""
    metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
    data = result.get("data", {}) if isinstance(result, dict) else {}
    return {
        "status": metadata.get("status"),
        "timestamp": metadata.get("timestamp"),
        "error": metadata.get("error"),
        "warnings": data.get("warnings", []),
        "failures": data.get("failures", []),
        "touched_files": data.get("touched_files", []),
        "logs": data.get("logs", []),
        "diffs": data.get("diffs", []),
    }


def _apply_loop_skip_receipt(stage: str, reason: str) -> dict[str, object]:
    """[ACTION] Build a skip receipt for apply loop stages that did not run."""
    return {
        "stage": stage,
        "status": "skipped",
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Apply loop inspection / validation / builder / rollback helpers
# ---------------------------------------------------------------------------

def _serialize_inspector_detail(detail: object) -> dict[str, object]:
    """[ACTION] Serialize an InspectorService detail into a plain dict."""
    return {
        "path": str(getattr(detail, "path", "") or ""),
        "file_type": str(getattr(detail, "file_type", "") or ""),
        "is_compliant": bool(getattr(detail, "is_compliant", False)),
        "errors": list(getattr(detail, "errors", []) or []),
        "missing_module_tags": list(getattr(detail, "missing_module_tags", []) or []),
        "classes_missing_role": list(getattr(detail, "classes_missing_role", []) or []),
        "functions_missing_action": list(getattr(detail, "functions_missing_action", []) or []),
    }


def _normalize_validator_strings(values: object) -> list[str]:
    """[ACTION] Deduplicate and sort a list of validator string values."""
    if not isinstance(values, list):
        return []
    normalized = {
        str(value).strip()
        for value in values
        if str(value).strip()
    }
    return sorted(normalized)


def _std_python_enforcement_signature(detail: Mapping[str, object]) -> dict[str, list[str]]:
    """[ACTION] Extract the std_python enforcement signature from an inspector detail."""
    errors = _normalize_validator_strings(detail.get("errors"))
    general_errors = [
        error
        for error in errors
        if not (
            error.startswith("Module missing tags:")
            or error.startswith("Class '")
            or error.startswith("Method '")
            or error.startswith("Func '")
        )
    ]
    return {
        "missing_module_tags": _normalize_validator_strings(detail.get("missing_module_tags")),
        "classes_missing_role": _normalize_validator_strings(detail.get("classes_missing_role")),
        "functions_missing_action": _normalize_validator_strings(detail.get("functions_missing_action")),
        "general_errors": general_errors,
    }


def _std_python_enforcement_gap_count(signature: Mapping[str, Sequence[str]]) -> int:
    """[ACTION] Count total enforcement gaps across all signature categories."""
    return sum(len(list(signature.get(key, []))) for key in (
        "missing_module_tags",
        "classes_missing_role",
        "functions_missing_action",
        "general_errors",
    ))


def _std_python_enforcement_delta(
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> dict[str, object]:
    """[ACTION] Compute delta between pre/post std_python enforcement snapshots."""
    before_sig = _std_python_enforcement_signature(before)
    after_sig = _std_python_enforcement_signature(after)
    new_gaps = {
        key: sorted(set(after_sig.get(key, [])) - set(before_sig.get(key, [])))
        for key in before_sig.keys()
    }
    resolved_gaps = {
        key: sorted(set(before_sig.get(key, [])) - set(after_sig.get(key, [])))
        for key in before_sig.keys()
    }
    pre_gap_count = _std_python_enforcement_gap_count(before_sig)
    post_gap_count = _std_python_enforcement_gap_count(after_sig)
    before_clean = bool(before.get("is_compliant"))
    after_clean = bool(after.get("is_compliant"))
    regressions = any(values for values in new_gaps.values()) or (before_clean and not after_clean)
    progress = any(values for values in resolved_gaps.values()) or (not before_clean and after_clean)

    status = "clean_stable"
    if before_clean and not after_clean:
        status = "regressed"
    elif not before_clean and after_clean:
        status = "resolved"
    elif regressions:
        status = "regressed"
    elif progress:
        status = "improved"
    elif not before_clean:
        status = "no_progress"

    return {
        "path": str(after.get("path") or before.get("path") or ""),
        "file_type": str(after.get("file_type") or before.get("file_type") or ""),
        "status": status,
        "before_is_compliant": before_clean,
        "after_is_compliant": after_clean,
        "pre_gap_count": pre_gap_count,
        "post_gap_count": post_gap_count,
        "progress_made": progress,
        "regressed": status == "regressed",
        "new_gaps": new_gaps,
        "resolved_gaps": resolved_gaps,
        "before_signature": before_sig,
        "after_signature": after_sig,
    }


def _inspect_apply_targets(paths: Sequence[str]) -> list[dict[str, object]]:
    """[ACTION] Batch-inspect apply target paths for std_python compliance."""
    from system.server.inspector import InspectorService

    normalized_paths = [str(path).strip() for path in paths if str(path).strip()]
    if not normalized_paths:
        return []
    inspector = InspectorService(state.REPO_ROOT)
    details = inspector.batch_inspect(normalized_paths)
    return [_serialize_inspector_detail(detail) for detail in details]


def _build_apply_receipt(result: dict[str, object], *, stage: str) -> dict[str, object]:
    """[ACTION] Build a structured receipt from an apply result."""
    metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
    data = result.get("data", {}) if isinstance(result, dict) else {}
    if not isinstance(data, dict):
        data = {}
    snapshot = data.get("snapshot", {})
    if not isinstance(snapshot, dict):
        snapshot = {}
    return {
        "stage": stage,
        "status": metadata.get("status"),
        "timestamp": metadata.get("timestamp"),
        "dry_run": bool(data.get("dry_run", False)),
        "error": metadata.get("error"),
        "warnings": data.get("warnings", []),
        "failures": data.get("failures", []),
        "logs": data.get("logs", []),
        "touched_files": data.get("touched_files", []),
        "diffs": data.get("diffs", []),
        "snapshot_id": snapshot.get("snapshot_id"),
        "snapshot_manifest": snapshot.get("snapshot_manifest"),
        "rollback_ready": bool(snapshot.get("rollback_ready", False)),
        "target_routing": data.get("target_routing", {}),
    }


def _planned_apply_targets(plan_body: dict[str, object]) -> list[str]:
    """[ACTION] Compile and return sorted unique target paths from an apply plan."""
    from tools.meta.apply import ApplyError, compile_apply_plan

    try:
        compiled_plan = compile_apply_plan(plan_body if isinstance(plan_body, dict) else {}, root_hint=str(state.REPO_ROOT))
    except ApplyError:
        operations = plan_body.get("operations", []) if isinstance(plan_body, dict) else []
    else:
        operations = compiled_plan.get("operations", [])
    if not isinstance(operations, list):
        return []
    targets: list[str] = []
    for op in operations:
        if not isinstance(op, dict):
            continue
        normalized = normalize_repo_relative_path(op.get("target"), repo_root=state.REPO_ROOT)
        if normalized:
            targets.append(normalized)
    return sorted(set(targets))


def _expected_hologram_entry(path: str) -> bool:
    """[ACTION] Check if a path is expected to have a hologram entry."""
    normalized = str(path or "").strip()
    if not normalized:
        return False
    suffix = Path(normalized).suffix.lower()
    if suffix not in {".py", ".json", ".md", ".txt"}:
        return False
    return normalized.startswith(("system/", "tools/", "codex/"))


def _capture_hologram_confirmation_state(paths: Sequence[str]) -> dict[str, dict[str, object]]:
    """[ACTION] Capture hologram state snapshot for a set of paths."""
    normalized_paths = [str(path).strip() for path in paths if str(path).strip()]
    index = load_hologram_index(state.REPO_ROOT)
    snapshot: dict[str, dict[str, object]] = {}
    for rel_path in normalized_paths:
        entry = index.get(rel_path)
        dependencies = {
            kind: query_hologram_dependencies(index, rel_path, query_type=kind)
            for kind in ("imports_internal", "reverse_dependents", "callers")
        }
        snapshot[rel_path] = {
            "path": rel_path,
            "present": entry is not None,
            "expected": _expected_hologram_entry(rel_path),
            "summary": summarize_hologram_entry(entry) if entry is not None else None,
            "dependencies": dependencies,
        }
    return snapshot


def _build_hologram_confirmation_receipt(
    touched_files: Sequence[str],
    *,
    pre_state: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """[ACTION] Build hologram confirmation receipt comparing pre/post state."""
    normalized_paths = [str(path).strip() for path in touched_files if str(path).strip()]
    post_state = _capture_hologram_confirmation_state(normalized_paths)
    confirmations: list[dict[str, object]] = []
    missing_paths: list[str] = []

    for rel_path in normalized_paths:
        before = dict(pre_state.get(rel_path, {})) if isinstance(pre_state.get(rel_path), Mapping) else {}
        after = dict(post_state.get(rel_path, {})) if isinstance(post_state.get(rel_path), Mapping) else {}
        before_present = bool(before.get("present"))
        after_present = bool(after.get("present"))
        summary_changed = before.get("summary") != after.get("summary")
        dependencies_changed = before.get("dependencies") != after.get("dependencies")
        expected = bool(after.get("expected") or before.get("expected"))
        if not after_present and (before_present or expected):
            status = "missing_post_build_entry"
            missing_paths.append(rel_path)
        elif after_present:
            status = "confirmed_delta" if summary_changed or dependencies_changed or not before_present else "confirmed_no_delta"
        else:
            status = "not_indexed"
        confirmations.append(
            {
                "path": rel_path,
                "status": status,
                "pre_state": before,
                "post_state": after,
                "summary_changed": summary_changed,
                "dependencies_changed": dependencies_changed,
            }
        )

    return {
        "status": "success" if not missing_paths else "failure",
        "files": confirmations,
        "missing_post_build_entries": missing_paths,
    }


def _run_apply_validator(
    touched_files: list[str],
    *,
    validator_policy: str = "strict_compliance",
    baseline_details: Sequence[Mapping[str, object]] | None = None,
    rollout_policy: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """[ACTION] Run post-apply validation (InspectorService) on touched files."""
    detail_payloads = _inspect_apply_targets(touched_files)
    defects = [payload for payload in detail_payloads if not payload.get("is_compliant")]
    policy_name = str(validator_policy or "strict_compliance").strip() or "strict_compliance"
    if policy_name != "std_python_delta_enforcement":
        return {
            "stage": "validator",
            "status": "success" if not defects else "failure",
            "validator_used": "InspectorService.batch_inspect",
            "validator_policy": policy_name,
            "policy_passed": not defects,
            "touched_files_inspected": touched_files,
            "inspected_file_count": len(detail_payloads),
            "is_compliant": not defects,
            "details": detail_payloads,
            "defects": defects,
            "baseline_details": list(baseline_details or []),
        }

    baseline_by_path = {
        str(detail.get("path") or "").strip(): dict(detail)
        for detail in (baseline_details or [])
        if isinstance(detail, Mapping) and str(detail.get("path") or "").strip()
    }
    evaluations: list[dict[str, object]] = []
    regressions: list[dict[str, object]] = []
    no_progress: list[dict[str, object]] = []
    improvements: list[dict[str, object]] = []
    dirty_files_remaining: list[str] = []
    require_progress = True
    if isinstance(rollout_policy, Mapping) and "require_progress_on_dirty_files" in rollout_policy:
        require_progress = bool(rollout_policy.get("require_progress_on_dirty_files"))

    for payload in detail_payloads:
        path = str(payload.get("path") or "").strip()
        before = baseline_by_path.get(
            path,
            {
                "path": path,
                "file_type": payload.get("file_type", ""),
                "is_compliant": True,
                "errors": [],
                "missing_module_tags": [],
                "classes_missing_role": [],
                "functions_missing_action": [],
            },
        )
        evaluation = _std_python_enforcement_delta(before, payload)
        evaluations.append(evaluation)
        if evaluation["status"] == "regressed":
            regressions.append(evaluation)
        elif evaluation["status"] == "no_progress":
            no_progress.append(evaluation)
        elif evaluation["progress_made"]:
            improvements.append(evaluation)
        if not payload.get("is_compliant"):
            dirty_files_remaining.append(path)

    blocked_no_progress = [
        item
        for item in no_progress
        if require_progress and not item.get("before_is_compliant", False)
    ]
    policy_passed = not regressions and not blocked_no_progress
    return {
        "stage": "validator",
        "status": "success" if policy_passed else "failure",
        "validator_used": "InspectorService.batch_inspect",
        "validator_policy": policy_name,
        "policy_passed": policy_passed,
        "touched_files_inspected": touched_files,
        "inspected_file_count": len(detail_payloads),
        "is_compliant": not defects,
        "details": detail_payloads,
        "defects": defects,
        "baseline_details": list(baseline_details or []),
        "rollout_policy": dict(rollout_policy or {}),
        "coverage_deltas": evaluations,
        "regressions": regressions,
        "no_progress": blocked_no_progress,
        "improvements": improvements,
        "dirty_files_remaining": sorted(set(path for path in dirty_files_remaining if path)),
    }


def _required_apply_validators(target_routing: Mapping[str, object]) -> set[str]:
    """[ACTION] Extract required validator names from target routing."""
    raw = target_routing.get("required_validators", []) if isinstance(target_routing, Mapping) else []
    if not isinstance(raw, list):
        return set()
    return {
        str(item).strip()
        for item in raw
        if str(item).strip()
    }


def _candidate_test_paths_for_targets(touched_files: Sequence[str]) -> list[str]:
    """[ACTION] Find candidate test files for a set of touched Python files."""
    candidates: set[str] = set()
    normalized = [str(path).strip() for path in touched_files if str(path).strip().endswith(".py")]
    for rel_path in normalized:
        if rel_path.startswith(("system/server/tests/", "tests/")):
            candidates.add(rel_path)
            continue
        stem = Path(rel_path).stem
        for base in ("system/server/tests", "tests"):
            base_path = state.REPO_ROOT / base
            if not base_path.exists():
                continue
            for path in base_path.rglob(f"test*{stem}*.py"):
                try:
                    rel = path.resolve().relative_to(state.REPO_ROOT.resolve()).as_posix()
                except ValueError:
                    continue
                candidates.add(rel)
    return sorted(candidates)


def _run_apply_tests_validator(touched_files: Sequence[str]) -> dict[str, object]:
    """[ACTION] Run pytest or py_compile on touched Python files."""
    python_targets = [str(path).strip() for path in touched_files if str(path).strip().endswith(".py")]
    if not python_targets:
        return _apply_loop_skip_receipt("tests", "no touched python files required runtime test validation")

    candidate_tests = _candidate_test_paths_for_targets(python_targets)
    if candidate_tests:
        command = [sys.executable, "-m", "pytest", *candidate_tests, "-q"]
        mode = "pytest"
        selected_paths = candidate_tests
    else:
        command = [sys.executable, "-m", "py_compile", *python_targets]
        mode = "py_compile_fallback"
        selected_paths = python_targets

    completed = subprocess.run(
        command,
        cwd=state.REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = str(completed.stdout or "")
    stderr = str(completed.stderr or "")
    return {
        "stage": "tests",
        "status": "success" if completed.returncode == 0 else "failure",
        "mode": mode,
        "command": command,
        "selected_paths": selected_paths,
        "returncode": int(completed.returncode),
        "stdout": stdout[-4000:] if stdout else "",
        "stderr": stderr[-4000:] if stderr else "",
    }


def _run_builder_refresh(
    *,
    touched_files: Sequence[str],
    pre_hologram_state: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """[ACTION] Rebuild hologram artifacts and confirm state after apply."""
    from tools.meta import builder

    result = builder.run(load_builder_config())
    metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
    data = result.get("data", {}) if isinstance(result, dict) else {}
    if not isinstance(data, dict):
        data = {}
    warnings = data.get("warnings", [])
    rebuild_status = str(metadata.get("status") or "unknown")
    hologram_confirmation = _build_hologram_confirmation_receipt(
        list(touched_files),
        pre_state=pre_hologram_state,
    )
    clean = rebuild_status == "success" and not warnings and hologram_confirmation.get("status") == "success"
    error = metadata.get("error")
    if not error and hologram_confirmation.get("status") != "success":
        missing = hologram_confirmation.get("missing_post_build_entries", [])
        error = (
            f"Hologram confirmation failed; missing post-build entries for {', '.join(missing)}."
            if isinstance(missing, list) and missing
            else "Hologram confirmation failed."
        )
    return {
        "stage": "builder",
        "status": "success" if clean else "failure",
        "rebuild_status": rebuild_status,
        "error": error,
        "warnings": warnings,
        "artifacts_written": data.get("artifacts_written"),
        "phase_artifacts": data.get("phase_artifacts", {}),
        "phases": data.get("phases", []),
        "stats": data.get("stats", {}),
        "generated_at": data.get("generated_at"),
        "root": data.get("root"),
        "hologram_confirmation": hologram_confirmation,
    }


def _run_apply_rollback_receipt(snapshot_id: str | None, *, auto_rollback: bool, failure_stage: str) -> dict[str, object]:
    """[ACTION] Attempt rollback via snapshot restore after a loop stage failure."""
    if not auto_rollback:
        return _apply_loop_skip_receipt("rollback", f"auto_rollback disabled after {failure_stage} failure")
    if not snapshot_id:
        return _apply_loop_skip_receipt("rollback", f"snapshot unavailable after {failure_stage} failure")

    from tools.meta.apply import ApplyError, restore_apply_snapshot

    try:
        payload = restore_apply_snapshot(snapshot_id, root_hint=str(state.REPO_ROOT))
    except ApplyError as exc:
        return {
            "stage": "rollback",
            "status": "failure",
            "executed": True,
            "snapshot_id": snapshot_id,
            "error": str(exc),
            "restored_files": [],
            "removed_files": [],
        }
    return {
        "stage": "rollback",
        "status": "success",
        "executed": True,
        "snapshot_id": payload.get("snapshot_id"),
        "snapshot_manifest": payload.get("snapshot_manifest"),
        "restored_files": payload.get("restored_files", []),
        "removed_files": payload.get("removed_files", []),
    }


def _write_apply_loop_result(payload: dict[str, object]) -> dict[str, object]:
    """[ACTION] Persist an apply loop result to disk."""
    state.APPLY_LOOP_RESULT.parent.mkdir(parents=True, exist_ok=True)
    state.APPLY_LOOP_RESULT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _emit_apply_loop_result(
    *,
    status: str,
    loop_status: str,
    live: bool,
    target_family: str | None,
    auto_rollback: bool,
    target_routing: dict[str, object],
    apply_receipt: dict[str, object],
    validator_receipt: dict[str, object],
    tests_receipt: dict[str, object],
    builder_receipt: dict[str, object],
    rollback_receipt: dict[str, object],
    error: str | None = None,
    failure_stage: str | None = None,
) -> dict[str, object]:
    """[ACTION] Build and persist the full apply loop result payload."""
    return _write_apply_loop_result(
        {
            "metadata": {
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": error,
            },
            "mode": "apply_loop",
            "loop_status": loop_status,
            "live": live,
            "auto_rollback": auto_rollback,
            "target_family": target_family,
            "failure_stage": failure_stage,
            "target_routing": target_routing,
            "apply_receipt": apply_receipt,
            "validator_receipt": validator_receipt,
            "tests_receipt": tests_receipt,
            "builder_receipt": builder_receipt,
            "rollback_receipt": rollback_receipt,
            "artifacts": {
                "apply_result_path": _rel(state.APPLY_RESULT),
                "apply_loop_result_path": _rel(state.APPLY_LOOP_RESULT),
            },
        }
    )


def _assert_apply_loop_target_family(target_routing: dict[str, object], target_family: str | None) -> None:
    """[ACTION] Validate that resolved target routing matches requested target_family."""
    if not target_family:
        return
    resolved_ops = target_routing.get("resolved_ops", []) if isinstance(target_routing, dict) else []
    families = sorted(
        {
            str(route.get("family") or "").strip()
            for route in resolved_ops
            if isinstance(route, dict) and str(route.get("family") or "").strip()
        }
    )
    if not families:
        raise ValueError("target_family was provided but no resolved target_routing family was available.")
    if any(family != target_family for family in families):
        raise ValueError(
            f"target_family `{target_family}` did not match resolved families: {', '.join(families)}"
        )


def _enforce_apply_loop_rollout_policy(
    *,
    target_routing: Mapping[str, object],
    planned_targets: Sequence[str],
) -> None:
    """[ACTION] Check batch rollout policy constraints before apply."""
    rollout_policy = target_routing.get("batch_rollout_policy", {}) if isinstance(target_routing, Mapping) else {}
    if not isinstance(rollout_policy, Mapping):
        return
    max_touched_files = rollout_policy.get("max_touched_files")
    if isinstance(max_touched_files, int) and max_touched_files > 0 and len(planned_targets) > max_touched_files:
        raise ValueError(
            f"Rollout policy rejected batch: planned cohort has {len(planned_targets)} targets, "
            f"limit is {max_touched_files}."
        )


def _build_validator_failure_error(validator_receipt: Mapping[str, object]) -> str:
    """[ACTION] Build a human-readable error string from a failed validator receipt."""
    policy_name = str(validator_receipt.get("validator_policy") or "strict_compliance").strip()
    if policy_name == "std_python_delta_enforcement":
        regressions = validator_receipt.get("regressions", [])
        if isinstance(regressions, list) and regressions:
            paths = ", ".join(
                str(item.get("path") or "").strip()
                for item in regressions
                if isinstance(item, Mapping) and str(item.get("path") or "").strip()
            )
            if paths:
                return f"std_python enforcement regressed coverage on: {paths}."
            return "std_python enforcement introduced a coverage regression."
        no_progress = validator_receipt.get("no_progress", [])
        if isinstance(no_progress, list) and no_progress:
            paths = ", ".join(
                str(item.get("path") or "").strip()
                for item in no_progress
                if isinstance(item, Mapping) and str(item.get("path") or "").strip()
            )
            if paths:
                return f"std_python enforcement did not improve dirty files: {paths}."
            return "std_python enforcement made no coverage progress on dirty files."
    return "InspectorService.batch_inspect reported non-compliant touched files."


def _run_validated_apply_loop(
    plan_body: dict[str, object],
    *,
    live: bool,
    auto_rollback: bool,
    target_family: str | None = None,
    capture_diffs: bool = True,
) -> dict[str, object]:
    """[ACTION] Full validated apply loop: routing -> apply -> validate -> test -> build -> rollback."""
    from tools.meta.apply import ApplyError, summarize_apply_target_routing

    target_routing: dict[str, object] = {}
    apply_receipt = _apply_loop_skip_receipt("apply", "apply did not start")
    validator_receipt = _apply_loop_skip_receipt("validator", "validator did not run")
    tests_receipt = _apply_loop_skip_receipt("tests", "tests validator did not run")
    builder_receipt = _apply_loop_skip_receipt("builder", "builder did not run")
    rollback_receipt = _apply_loop_skip_receipt("rollback", "rollback was not needed")
    planned_targets = _planned_apply_targets(plan_body)
    pre_validation_details: list[dict[str, object]] = []

    try:
        target_routing = summarize_apply_target_routing(
            plan_body,
            root_hint=str(state.REPO_ROOT),
            strict=True,
            preferred_target_family=target_family,
        )
        _assert_apply_loop_target_family(target_routing, target_family)
        _enforce_apply_loop_rollout_policy(
            target_routing=target_routing,
            planned_targets=planned_targets,
        )
    except (ApplyError, ValueError) as exc:
        return _emit_apply_loop_result(
            status="failure",
            loop_status="routing_rejected",
            live=live,
            target_family=target_family,
            auto_rollback=auto_rollback,
            target_routing=target_routing,
            apply_receipt=apply_receipt,
            validator_receipt=validator_receipt,
            tests_receipt=tests_receipt,
            builder_receipt=builder_receipt,
            rollback_receipt=rollback_receipt,
            error=str(exc),
            failure_stage="routing",
        )

    pre_hologram_state = _capture_hologram_confirmation_state(planned_targets) if live else {}
    validator_policy = str(target_routing.get("batch_validator_policy") or "strict_compliance").strip() or "strict_compliance"
    rollout_policy = target_routing.get("batch_rollout_policy", {}) if isinstance(target_routing.get("batch_rollout_policy", {}), Mapping) else {}
    if live and planned_targets and validator_policy == "std_python_delta_enforcement":
        pre_validation_details = _inspect_apply_targets(planned_targets)

    apply_result = _run_apply_plan(
        plan_body,
        dry_run=not live,
        capture_diffs=capture_diffs,
        result_path=state.APPLY_RESULT,
        enforce_target_routing=True,
        preferred_target_family=target_family,
    )
    apply_receipt = _build_apply_receipt(apply_result, stage="apply")
    target_routing = apply_receipt.get("target_routing", target_routing)

    if apply_receipt.get("status") != "success":
        return _emit_apply_loop_result(
            status="failure",
            loop_status="apply_failed",
            live=live,
            target_family=target_family,
            auto_rollback=auto_rollback,
            target_routing=target_routing,
            apply_receipt=apply_receipt,
            validator_receipt=validator_receipt,
            tests_receipt=tests_receipt,
            builder_receipt=builder_receipt,
            rollback_receipt=rollback_receipt,
            error=str(apply_receipt.get("error") or "Apply failed."),
            failure_stage="apply",
        )

    if not live:
        validator_receipt = _apply_loop_skip_receipt("validator", "preview mode does not mutate the repo")
        tests_receipt = _apply_loop_skip_receipt("tests", "preview mode does not run runtime test validation")
        builder_receipt = _apply_loop_skip_receipt("builder", "preview mode does not rebuild artifacts")
        rollback_receipt = _apply_loop_skip_receipt("rollback", "preview mode does not create snapshots")
        return _emit_apply_loop_result(
            status="success",
            loop_status="preview",
            live=live,
            target_family=target_family,
            auto_rollback=auto_rollback,
            target_routing=target_routing,
            apply_receipt=apply_receipt,
            validator_receipt=validator_receipt,
            tests_receipt=tests_receipt,
            builder_receipt=builder_receipt,
            rollback_receipt=rollback_receipt,
        )

    touched_files = [
        str(path)
        for path in apply_receipt.get("touched_files", [])
        if isinstance(path, str) and str(path).strip()
    ]
    validator_policy = str(target_routing.get("batch_validator_policy") or validator_policy).strip() or "strict_compliance"
    rollout_policy = target_routing.get("batch_rollout_policy", rollout_policy)
    if not isinstance(rollout_policy, Mapping):
        rollout_policy = {}
    required_validators = _required_apply_validators(target_routing)
    if "miner" in required_validators or validator_policy == "std_python_delta_enforcement":
        validator_receipt = _run_apply_validator(
            touched_files,
            validator_policy=validator_policy,
            baseline_details=pre_validation_details,
            rollout_policy=rollout_policy,
        )
    else:
        validator_receipt = _apply_loop_skip_receipt(
            "validator",
            "target_routing did not require miner-backed post-apply validation",
        )
    if validator_receipt.get("status") != "success" and validator_receipt.get("status") != "skipped":
        rollback_receipt = _run_apply_rollback_receipt(
            str(apply_receipt.get("snapshot_id") or "").strip() or None,
            auto_rollback=auto_rollback,
            failure_stage="validator",
        )
        loop_status = "rollback_failed"
        if rollback_receipt.get("status") == "success":
            loop_status = "rolled_back"
        elif rollback_receipt.get("status") == "skipped":
            loop_status = "validator_failed"
        return _emit_apply_loop_result(
            status="failure",
            loop_status=loop_status,
            live=live,
            target_family=target_family,
            auto_rollback=auto_rollback,
            target_routing=target_routing,
            apply_receipt=apply_receipt,
            validator_receipt=validator_receipt,
            tests_receipt=tests_receipt,
            builder_receipt=builder_receipt,
            rollback_receipt=rollback_receipt,
            error=_build_validator_failure_error(validator_receipt),
            failure_stage="validator",
        )

    if "tests" in required_validators:
        tests_receipt = _run_apply_tests_validator(touched_files)
        if tests_receipt.get("status") != "success":
            rollback_receipt = _run_apply_rollback_receipt(
                str(apply_receipt.get("snapshot_id") or "").strip() or None,
                auto_rollback=auto_rollback,
                failure_stage="tests",
            )
            loop_status = "rollback_failed"
            if rollback_receipt.get("status") == "success":
                loop_status = "rolled_back"
            elif rollback_receipt.get("status") == "skipped":
                loop_status = "tests_failed"
            error = "Runtime test validation failed."
            stderr = str(tests_receipt.get("stderr") or "").strip()
            if stderr:
                error = f"{error} {stderr}"
            return _emit_apply_loop_result(
                status="failure",
                loop_status=loop_status,
                live=live,
                target_family=target_family,
                auto_rollback=auto_rollback,
                target_routing=target_routing,
                apply_receipt=apply_receipt,
                validator_receipt=validator_receipt,
                tests_receipt=tests_receipt,
                builder_receipt=builder_receipt,
                rollback_receipt=rollback_receipt,
                error=error,
                failure_stage="tests",
            )
    else:
        tests_receipt = _apply_loop_skip_receipt(
            "tests",
            "target_routing did not require runtime test validation",
        )

    builder_receipt = _run_builder_refresh(
        touched_files=touched_files,
        pre_hologram_state=pre_hologram_state,
    )
    if builder_receipt.get("status") != "success":
        rollback_receipt = _run_apply_rollback_receipt(
            str(apply_receipt.get("snapshot_id") or "").strip() or None,
            auto_rollback=auto_rollback,
            failure_stage="builder",
        )
        loop_status = "rollback_failed"
        if rollback_receipt.get("status") == "success":
            loop_status = "rolled_back"
        elif rollback_receipt.get("status") == "skipped":
            loop_status = "builder_failed"
        builder_error = str(builder_receipt.get("error") or "").strip()
        warning_count = len(builder_receipt.get("warnings", [])) if isinstance(builder_receipt.get("warnings"), list) else 0
        if not builder_error and warning_count:
            builder_error = f"Builder emitted {warning_count} warning(s); apply loop fails closed on builder warnings."
        elif not builder_error:
            builder_error = "Builder refresh failed."
        return _emit_apply_loop_result(
            status="failure",
            loop_status=loop_status,
            live=live,
            target_family=target_family,
            auto_rollback=auto_rollback,
            target_routing=target_routing,
            apply_receipt=apply_receipt,
            validator_receipt=validator_receipt,
            tests_receipt=tests_receipt,
            builder_receipt=builder_receipt,
            rollback_receipt=rollback_receipt,
            error=builder_error,
            failure_stage="builder",
        )

    return _emit_apply_loop_result(
        status="success",
        loop_status="success",
        live=live,
        target_family=target_family,
        auto_rollback=auto_rollback,
        target_routing=target_routing,
        apply_receipt=apply_receipt,
        validator_receipt=validator_receipt,
        tests_receipt=tests_receipt,
        builder_receipt=builder_receipt,
        rollback_receipt=rollback_receipt,
    )


# ---------------------------------------------------------------------------
# Metabolize trust policy / follow-on patch map
# ---------------------------------------------------------------------------

def _build_follow_on_patch_map_payload(
    *,
    target: dict[str, Any],
    source: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """[ACTION] Build follow-on patch_map proposal from observe payload for living_map targets."""
    warnings: list[str] = []
    if str(target.get("kind") or "") != "living_map":
        return (
            {
                "status": "not_applicable",
                "plan_path": None,
                "apply_result_path": None,
                "plan": None,
                "preview": None,
                "candidate_count": 0,
                "candidate_sections": {},
                "suppressed_candidates": {},
                "signal_summary": {},
            },
            warnings,
        )

    target_path = str(target.get("path") or "").strip()
    target_text = _safe_read_text(state.REPO_ROOT / target_path) if target_path else None
    artifact = source.get("artifact")
    payload_markdown = str(artifact.get("payload_markdown") or "").strip() if isinstance(artifact, dict) else ""
    proposal = propose_patch_map_from_observe_payload(
        payload_markdown=payload_markdown,
        existing_map_text=target_text,
    )
    warnings.extend(proposal.get("warnings", []))
    patches = proposal.get("patches", [])
    if not isinstance(patches, list):
        patches = []

    payload: dict[str, Any] = {
        "status": str(proposal.get("status") or "no_deterministic_candidates"),
        "plan_path": None,
        "apply_result_path": None,
        "plan": None,
        "preview": None,
        "candidate_count": len(patches),
        "candidate_sections": proposal.get("candidate_sections", {}),
        "suppressed_candidates": proposal.get("suppressed_candidates", {}),
        "signal_summary": proposal.get("signal_summary", {}),
    }
    if not patches:
        return payload, warnings

    plan_body: dict[str, object] = {
        "operations": [
            {
                "op": "patch_map",
                "target": target_path,
                "patches": patches,
            }
        ]
    }
    state.APPLY_METABOLIZE_PATCH_MAP_PLAN.parent.mkdir(parents=True, exist_ok=True)
    state.APPLY_METABOLIZE_PATCH_MAP_PLAN.write_text(json.dumps(plan_body, indent=2), encoding="utf-8")
    preview_result = _run_apply_plan(
        plan_body,
        dry_run=True,
        capture_diffs=True,
        result_path=state.APPLY_METABOLIZE_PATCH_MAP_RESULT,
        enforce_target_routing=False,
    )
    preview_summary = _summarize_apply_result(preview_result)
    if preview_summary.get("status") != "success":
        warnings.append(
            f"Follow-on patch_map preview failed: {preview_summary.get('error') or 'unknown apply failure'}"
        )
        payload["status"] = "preview_failed"
    else:
        payload["status"] = "ready"
    payload["plan_path"] = _rel(state.APPLY_METABOLIZE_PATCH_MAP_PLAN)
    payload["apply_result_path"] = _rel(state.APPLY_METABOLIZE_PATCH_MAP_RESULT)
    payload["plan"] = plan_body
    payload["preview"] = preview_summary
    return payload, warnings


def _build_metabolize_trust_policy(
    *,
    target: dict[str, Any],
    source: dict[str, Any],
    live: bool,
    follow_on_patch_map: dict[str, Any],
) -> dict[str, Any]:
    """[ACTION] Build the trust policy envelope for a metabolize operation."""
    target_kind = str(target.get("kind") or "").strip()
    target_family = str(target.get("target_family") or target_kind).strip()
    artifact_origin = str(source.get("artifact_origin") or "").strip()
    if artifact_origin == "result_note":
        resolved_source_kind = "typed_result_note"
    elif artifact_origin == "response_file":
        resolved_source_kind = "grouped_response_markdown"
    else:
        resolved_source_kind = "typed_observe_artifact"

    follow_on_status = str(follow_on_patch_map.get("status") or "not_applicable").strip() or "not_applicable"
    follow_on_ready = follow_on_status == "ready"
    return {
        "reference_artifact": {
            "default_mode": "preview_only",
            "current_mode": "explicit_live_requested" if live else "preview_only",
            "preview_required": True,
            "live_apply_requested": live,
            "live_apply_rule": "Requires explicit --live after a successful preview.",
            "risk_label": "low_risk_doc_only_reference",
            "preferred_source_kind": "typed_result_note",
            "fallback_source_kind": "grouped_response_markdown",
            "resolved_source_kind": resolved_source_kind,
            "target_kind": target_kind,
            "target_family": target_family,
        },
        "follow_on_patch_map": {
            "proposal_only": True,
            "auto_apply_from_metabolize": False,
            "eligible_target_kind": "living_map",
            "target_kind": target_kind,
            "target_family": target_family,
            "current_status": follow_on_status,
            "candidate_ready": follow_on_ready,
            "risk_label": (
                "higher_risk_owned_section_mutation"
                if target_kind == "living_map"
                else "not_applicable"
            ),
            "rule": (
                "Only proposed for living_map targets when the payload carries deterministic section or tag cues. "
                "Apply separately with kernel apply."
            ),
        },
        "guardrails": [
            "Prefer the typed result note as the connector source when it exists.",
            "Do not treat patch_map as a substitute for provenance-bearing artifact linkage.",
            "Metabolize never auto-applies the follow-on patch_map plan.",
        ],
    }


# ---------------------------------------------------------------------------
# Session-based apply helpers
# ---------------------------------------------------------------------------

def _resolve_apply_session_manifest(ref: str | None) -> Path | None:
    """[ACTION] Resolve a session manifest path suitable for apply operations."""
    from kernel import _resolve_session_manifest
    token = str(ref or "latest").strip() or "latest"
    if token != "latest":
        return _resolve_session_manifest(token)
    candidates = load_session_candidates(
        state.REPO_ROOT,
        sessions_root=state.OBSERVE_SESSION_ROOT,
        include_provisional=False,
        include_compiled_apply=True,
    )
    manifest_candidates = [
        candidate
        for candidate in candidates
        if isinstance(candidate.get("manifest_path"), Path)
        and candidate.get("compiled_apply_ready") is True
    ]
    if not manifest_candidates:
        return _resolve_session_manifest(token)
    best_candidate = max(
        manifest_candidates,
        key=lambda candidate: session_resolution_sort_key(candidate, intent="apply"),
    )
    manifest_path = best_candidate.get("manifest_path")
    return manifest_path if isinstance(manifest_path, Path) else None


def _build_session_manifest_invocation_context(
    manifest_path: Path,
    manifest_payload: Mapping[str, object],
    compiled_plan: Mapping[str, object],
) -> dict[str, object]:
    """[ACTION] Build invocation context from a session manifest for apply loop tracking."""
    readback_state = manifest_payload.get("readback_state") if isinstance(manifest_payload.get("readback_state"), Mapping) else {}
    continuation = manifest_payload.get("continuation") if isinstance(manifest_payload.get("continuation"), Mapping) else {}
    response_index = manifest_payload.get("response_index") if isinstance(manifest_payload.get("response_index"), list) else []
    artifact_queue = [
        str(item).strip()
        for item in readback_state.get("artifact_queue", [])
        if str(item).strip()
    ] if isinstance(readback_state.get("artifact_queue"), list) else []
    primary_artifact = (
        str(readback_state.get("primary_artifact") or "").strip()
        or str(continuation.get("latest_artifact") or "").strip()
        or None
    )
    return {
        "compiled_operations": [
            dict(item)
            for item in compiled_plan.get("operations", [])
            if isinstance(item, Mapping)
        ],
        "miner_chain": {
            "session_manifest": _rel(manifest_path),
            "primary_artifact": primary_artifact,
            "artifact_queue": artifact_queue,
            "response_index": [dict(item) for item in response_index if isinstance(item, Mapping)],
        },
    }


def _finalize_apply_loop_result(
    *,
    result: dict[str, object],
    invocation_context: Mapping[str, object],
    live: bool,
) -> dict[str, object]:
    """[ACTION] Post-process apply loop result: phase harbor writeback and session attachment."""
    phase_harbor_writeback = _maybe_write_apply_loop_phase_harbor(
        live=live,
        invocation_context=invocation_context,
        apply_loop_result=result,
    )
    result["phase_harbor_writeback"] = phase_harbor_writeback
    state.APPLY_LOOP_RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    miner_chain = invocation_context.get("miner_chain") if isinstance(invocation_context.get("miner_chain"), dict) else {}
    session_manifest = str(miner_chain.get("session_manifest") or "").strip() if isinstance(miner_chain, dict) else ""
    if session_manifest:
        try:
            from tools.meta.apply.observe_session import attach_apply_loop_transaction

            session_writeback = attach_apply_loop_transaction(
                repo_root=state.REPO_ROOT,
                session_manifest=session_manifest,
                apply_loop_result=result,
                apply_loop_result_path=_rel(state.APPLY_LOOP_RESULT),
                miner_chain=miner_chain,
                compiled_apply=result.get("compiled_apply") if isinstance(result.get("compiled_apply"), Mapping) else None,
            )
            result["session_writeback"] = session_writeback
            state.APPLY_LOOP_RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        except Exception as exc:
            result["session_writeback"] = {
                "status": "failure",
                "session_manifest": session_manifest,
                "error": str(exc),
            }
            state.APPLY_LOOP_RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# ===========================================================================
# Public command functions
# ===========================================================================

def cmd_metabolize(
    target_selector: str,
    *,
    from_observe: str | None = None,
    source_artifact: str | None = None,
    section: str | None = None,
    live: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Generate the reference-artifact stage that promotes observe output into a governed reference surface and optional follow-on patch-map.
    - Mechanism: Resolve the metabolize target/source/section, preview the apply plan, optionally run it live, and emit navigation payload plus trust policy.
    - Guarantee: Returns 0 with a navigation result when the preview succeeds; live mode only proceeds after the preview passes.
    - Fails: Returns 1 for invalid selectors or failed preview/live apply execution.
    - When-needed: Open when an observe result needs to become a reference artifact or patch-map proposal through the sanctioned metabolize lane.
    - Escalates-to: codex/doctrine/skills/kernel/apply.md; kernel.py
    """
    warnings: list[str] = []
    replay_command = ["python3", "kernel.py", "--metabolize", target_selector]
    if from_observe:
        replay_command.extend(["--from-observe", from_observe])
    if source_artifact:
        replay_command.extend(["--source-artifact", source_artifact])
    if section:
        replay_command.extend(["--section", section])
    try:
        target, target_warnings = _resolve_metabolize_target(target_selector)
        source, source_warnings = _resolve_metabolize_source(
            target=target,
            from_observe=from_observe,
            source_artifact=source_artifact,
        )
        resolved_section, section_warnings = _resolve_metabolize_section(target, section)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    warnings.extend(target_warnings)
    warnings.extend(source_warnings)
    warnings.extend(section_warnings)

    operation: dict[str, object] = {
        "op": "reference_artifact",
        "target": str(target.get("path") or ""),
        "source_artifact": str(source.get("artifact_path") or ""),
        "section": resolved_section,
    }
    plan_body = {"operations": [operation]}
    state.APPLY_METABOLIZE_PLAN.parent.mkdir(parents=True, exist_ok=True)
    state.APPLY_METABOLIZE_PLAN.write_text(json.dumps(plan_body, indent=2), encoding="utf-8")

    preview_result = _run_apply_plan(
        plan_body,
        dry_run=True,
        capture_diffs=True,
        result_path=state.APPLY_METABOLIZE_RESULT,
    )
    preview_summary = _summarize_apply_result(preview_result)
    if preview_summary.get("status") != "success":
        print(
            f"ERROR: metabolize preview failed: {preview_summary.get('error') or 'unknown apply failure'}",
            file=sys.stderr,
        )
        return 1

    live_summary: dict[str, object] | None = None
    if live:
        live_result = _run_apply_plan(
            plan_body,
            dry_run=False,
            capture_diffs=True,
            result_path=state.APPLY_METABOLIZE_RESULT,
        )
        live_summary = _summarize_apply_result(live_result)
        if live_summary.get("status") != "success":
            print(
                f"ERROR: metabolize live apply failed: {live_summary.get('error') or 'unknown apply failure'}",
                file=sys.stderr,
            )
            return 1

    follow_on_patch_map, patch_warnings = _build_follow_on_patch_map_payload(
        target=target,
        source=source,
    )
    warnings.extend(patch_warnings)
    trust_policy = _build_metabolize_trust_policy(
        target=target,
        source=source,
        live=live,
        follow_on_patch_map=follow_on_patch_map,
    )

    replay_preview = " ".join(shlex.quote(part) for part in replay_command)
    replay_live = " ".join(shlex.quote(part) for part in [*replay_command, "--live"])
    suggested_next = [
        (
            {
                "command": replay_live,
                "reason": "Apply the previewed reference_artifact plan live.",
            }
            if not live
            else {
                "command": replay_preview,
                "reason": "Re-run the metabolize preview to confirm the duplicate guard now blocks a second insertion.",
            }
        ),
        {
            "command": (
                f"python3 kernel.py --map {shlex.quote(str(target.get('path') or target_selector))}"
                if str(target.get("kind") or "") == "living_map"
                else str(target.get("path") or target_selector)
            ),
            "reason": "Inspect the updated target note after the preview/live reference routing.",
        },
    ]
    observe_ref = str(source.get("observe_id") or source.get("history_entry") or "").strip()
    if observe_ref:
        suggested_next.append(
            {
                "command": f"python3 kernel.py --read-observe {shlex.quote(observe_ref)}",
                "reason": "Reopen the source observe artifact and compare it against the promoted reference block.",
            }
        )
    if (
        live
        and str(follow_on_patch_map.get("status") or "") == "ready"
        and str(follow_on_patch_map.get("plan_path") or "").strip()
    ):
        suggested_next.append(
            {
                "command": f"python3 kernel.py --apply {shlex.quote(str(follow_on_patch_map['plan_path']))} --live",
                "reason": "Apply the follow-on patch_map plan now that the provenance reference stage is live.",
            }
        )

    result = NavigationResult(
        kind="kernel.apply.metabolize",
        query={
            "command": "metabolize",
            "target": target_selector,
            "from_observe": from_observe,
            "source_artifact": source_artifact,
            "section": section,
            "live": live,
        },
        payload={
            "target": {
                "kind": target.get("kind"),
                "target_family": target.get("target_family"),
                "path": target.get("path"),
                "title": target.get("title"),
                "id": target.get("id"),
                "boundary": target.get("boundary"),
                "summary": target.get("summary"),
                "resolution_mode": target.get("resolution_mode"),
            },
            "source": {
                "selection_mode": source.get("selection_mode"),
                "artifact_path": source.get("artifact_path"),
                "artifact_origin": source.get("artifact_origin"),
                "observe_id": source.get("observe_id"),
                "history_entry": source.get("history_entry"),
                "selection_reasons": source.get("selection_reasons"),
            },
            "resolved_section": resolved_section,
            "plan_path": _rel(state.APPLY_METABOLIZE_PLAN),
            "apply_result_path": _rel(state.APPLY_METABOLIZE_RESULT),
            "plan": plan_body,
            "preview": preview_summary,
            "live_apply": live_summary,
            "follow_on_patch_map": follow_on_patch_map,
            "trust_policy": trust_policy,
        },
        live_sources=[
            str(target.get("path") or ""),
            str(source.get("artifact_path") or ""),
        ],
        derived_sources=[
            _rel(state.APPLY_METABOLIZE_PLAN),
            _rel(state.APPLY_METABOLIZE_RESULT),
            *(
                [_rel(state.APPLY_METABOLIZE_PATCH_MAP_PLAN), _rel(state.APPLY_METABOLIZE_PATCH_MAP_RESULT)]
                if str(follow_on_patch_map.get("plan_path") or "").strip()
                else []
            ),
        ],
        suggested_next=suggested_next,
        warnings=warnings,
    )
    return emit_navigation(result)


def cmd_apply(plan_path: Path, dry_run: bool = True, capture_diffs: bool = True) -> int:
    """[ACTION]
    - Teleology: Execute or preview one apply plan from disk.
    - Mechanism: Read the plan payload, run `_run_apply_plan`, and print touched files, warnings, diffs, logs, and snapshot metadata.
    - Guarantee: Returns 0 when the apply engine reports success; writes the structured result to `APPLY_RESULT`.
    - Fails: Returns 1 for unreadable plans or failed apply execution.
    - When-needed: Open when the kernel task is about the direct `--apply` command contract, especially preview versus live execution behavior.
    - Escalates-to: codex/doctrine/skills/kernel/apply.md; kernel.py
    - Navigation-group: kernel_lib
    """
    try:
        plan_body, _invocation_context = _read_apply_plan(plan_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    result = _run_apply_plan(
        plan_body,
        dry_run=dry_run,
        capture_diffs=capture_diffs,
        result_path=state.APPLY_RESULT,
        enforce_target_routing=False,
    )
    meta = result.get("metadata", {})
    data = result.get("data", {})

    if meta.get("status") == "success":
        logs = data.get("logs", [])
        diffs = data.get("diffs", [])
        touched = data.get("touched_files", [])
        warnings = data.get("warnings", [])
        failures = data.get("failures", [])
        snapshot = data.get("snapshot", {}) if isinstance(data.get("snapshot"), dict) else {}

        mode_label = "DRY RUN" if dry_run else "LIVE"
        print(f"OK [{mode_label}] ops={len(logs)} touched={len(touched)} warnings={len(warnings)} failures={len(failures)}")

        if warnings:
            print(f"\nWARNINGS:")
            for w in warnings:
                print(f"  ! {w}")

        if touched:
            print(f"\nTOUCHED FILES:")
            for t in touched:
                print(f"  {t}")

        if snapshot.get("snapshot_manifest"):
            print(f"\nSNAPSHOT:")
            print(f"  id={snapshot.get('snapshot_id')}")
            print(f"  manifest={snapshot.get('snapshot_manifest')}")

        if diffs:
            print(f"\nDIFFS:")
            for d in diffs:
                print(d)

        if logs:
            print(f"\nOPERATION LOG:")
            for i, log in enumerate(logs):
                print(f"  [{i}] {log}")

        if failures:
            print(f"\nFAILURES:")
            for f in failures:
                print(f"  {f}")

        print(f"\nResult written: {_rel(state.APPLY_RESULT)}")
        return 0
    else:
        print(f"FAIL {meta.get('error', 'unknown')}", file=sys.stderr)
        # Still write result for inspection
        print(f"Result written: {_rel(state.APPLY_RESULT)}", file=sys.stderr)
        return 1


def cmd_apply_loop(
    plan_path: Path,
    *,
    live: bool = False,
    auto_rollback: bool = True,
    target_family: str | None = None,
) -> int:
    """[ACTION]
    - Teleology: Run the validated closed-loop apply path that includes routing, validation, builder rebuild, and optional rollback.
    - Mechanism: Read the plan, execute `_run_validated_apply_loop`, finalize receipts, and emit the resulting JSON payload.
    - Guarantee: Returns 0 only when the loop result reports success.
    - Fails: Returns 1 for unreadable plans or failed loop execution.
    - When-needed: Open when the user asks for the full guarded apply loop rather than a single preview/live apply pass.
    - Escalates-to: codex/doctrine/skills/kernel/apply.md; kernel.py
    """
    try:
        plan_body, invocation_context = _read_apply_plan(plan_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    result = _run_validated_apply_loop(
        plan_body,
        live=live,
        auto_rollback=auto_rollback,
        target_family=target_family,
        capture_diffs=True,
    )
    result = _finalize_apply_loop_result(
        result=result,
        invocation_context=invocation_context,
        live=live,
    )
    status = result.get("metadata", {}).get("status")
    emit_json(result)
    return 0 if status == "success" else 1


def cmd_apply_session(
    session_ref: str | None,
    *,
    live: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Turn an observe session manifest into a standard apply run.
    - Mechanism: Resolve the session manifest, compile session apply payload, run `_run_apply_plan`, and attach session transaction metadata.
    - Guarantee: Returns 0 when the compiled session apply succeeds and emits a structured payload describing the run.
    - Fails: Returns 1 when the session manifest cannot be resolved, compiled, or applied successfully.
    - When-needed: Open when an observe session needs to be applied directly without the validated loop wrapper.
    - Escalates-to: system/lib/observe_sessions.py; kernel.py
    """
    from kernel import _compile_session_apply_payload, _load_session_manifest_payload

    manifest_path = _resolve_apply_session_manifest(session_ref)
    if manifest_path is None:
        print("ERROR: Observe session manifest not found.", file=sys.stderr)
        return 1
    manifest_payload = _load_session_manifest_payload(manifest_path)
    if not isinstance(manifest_payload, Mapping):
        print(f"ERROR: Failed to read session manifest: {_rel(manifest_path)}", file=sys.stderr)
        return 1
    compiled_apply, compiled_plan = _compile_session_apply_payload(manifest_path, manifest_payload)
    if not compiled_plan:
        print(f"ERROR: {compiled_apply.get('error')}", file=sys.stderr)
        return 1
    result = _run_apply_plan(
        dict(compiled_plan),
        dry_run=not live,
        capture_diffs=True,
        result_path=state.APPLY_RESULT,
        enforce_target_routing=False,
    )
    apply_summary = _summarize_apply_result(result)
    success = apply_summary.get("status") == "success"
    invocation_context = _build_session_manifest_invocation_context(
        manifest_path,
        manifest_payload,
        compiled_plan,
    )
    payload = {
        "status": "success" if success else "failure",
        "observe_id": manifest_payload.get("observe_id"),
        "session_slug": manifest_payload.get("session_slug"),
        "session_manifest": _rel(manifest_path),
        "apply_result_path": _rel(state.APPLY_RESULT),
        "dry_run": not live,
        "compiled_apply": compiled_apply,
        "apply_summary": apply_summary,
    }
    session_manifest_rel = str(payload.get("session_manifest") or "").strip()
    if session_manifest_rel:
        try:
            from tools.meta.apply.observe_session import attach_apply_transaction

            miner_chain = (
                invocation_context.get("miner_chain")
                if isinstance(invocation_context.get("miner_chain"), Mapping)
                else {}
            )
            session_writeback = attach_apply_transaction(
                repo_root=state.REPO_ROOT,
                session_manifest=session_manifest_rel,
                apply_result=result,
                apply_result_path=_rel(state.APPLY_RESULT),
                apply_summary=apply_summary,
                dry_run=not live,
                live=live,
                compiled_apply=compiled_apply,
                miner_chain=miner_chain if isinstance(miner_chain, Mapping) else None,
            )
            payload["session_writeback"] = session_writeback
            if state.APPLY_RESULT.exists():
                result_payload = safe_load_json(state.APPLY_RESULT)
                if isinstance(result_payload, dict):
                    result_payload["compiled_apply"] = compiled_apply
                    result_payload["session_writeback"] = session_writeback
                    state.APPLY_RESULT.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
        except Exception as exc:
            payload["session_writeback"] = {
                "status": "failure",
                "session_manifest": session_manifest_rel,
                "error": str(exc),
            }
    emit_json(payload)
    return 0 if success else 1


def cmd_apply_session_loop(
    session_ref: str | None,
    *,
    live: bool = False,
    auto_rollback: bool = True,
    target_family: str | None = None,
) -> int:
    """[ACTION]
    - Teleology: Run a compiled observe-session apply payload through the validated apply loop.
    - Mechanism: Resolve the session manifest, compile the apply plan, execute `_run_validated_apply_loop`, and emit the finalized loop payload.
    - Guarantee: Returns 0 only when the session-backed loop completes successfully.
    - Fails: Returns 1 when the session manifest cannot be resolved, compiled, or validated through the loop.
    - When-needed: Open when a stored observe session must go through the same guarded apply-loop contract as a normal apply plan.
    - Escalates-to: system/lib/observe_sessions.py; codex/doctrine/skills/kernel/apply.md
    """
    from kernel import _compile_session_apply_payload, _load_session_manifest_payload

    manifest_path = _resolve_apply_session_manifest(session_ref)
    if manifest_path is None:
        print("ERROR: Observe session manifest not found.", file=sys.stderr)
        return 1
    manifest_payload = _load_session_manifest_payload(manifest_path)
    if not isinstance(manifest_payload, Mapping):
        print(f"ERROR: Failed to read session manifest: {_rel(manifest_path)}", file=sys.stderr)
        return 1
    compiled_apply, compiled_plan = _compile_session_apply_payload(manifest_path, manifest_payload)
    if not compiled_plan:
        print(f"ERROR: {compiled_apply.get('error')}", file=sys.stderr)
        return 1
    invocation_context = _build_session_manifest_invocation_context(
        manifest_path,
        manifest_payload,
        compiled_plan,
    )
    result = _run_validated_apply_loop(
        dict(compiled_plan),
        live=live,
        auto_rollback=auto_rollback,
        target_family=target_family,
        capture_diffs=True,
    )
    result["compiled_apply"] = compiled_apply
    result = _finalize_apply_loop_result(
        result=result,
        invocation_context=invocation_context,
        live=live,
    )
    status = result.get("metadata", {}).get("status")
    emit_json(result)
    return 0 if status == "success" else 1


def cmd_apply_rollback(snapshot_ref: str, *, group_label: str | None = None) -> int:
    """[ACTION]
    - Teleology: Restore a previously captured live-apply snapshot.
    - Mechanism: Delegate snapshot resolution and restoration to `restore_apply_snapshot` and emit the JSON result.
    - Guarantee: Returns the restore payload through `emit_json` when a matching snapshot is found.
    - Fails: Returns 1 when snapshot restoration raises `ApplyError`.
    - When-needed: Open when a live apply must be rolled back from snapshot id, manifest path, or latest pointer.
    - Escalates-to: codex/doctrine/skills/kernel/apply.md; kernel.py
    """
    from tools.meta.apply import ApplyError, restore_apply_snapshot

    try:
        result = restore_apply_snapshot(snapshot_ref, root_hint=str(state.REPO_ROOT), group_label=group_label)
    except ApplyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json(result)


def cmd_apply_validate(plan_path: Path) -> int:
    """[ACTION]
    - Teleology: Validate an apply plan without executing any mutations.
    - Mechanism: Read the plan, run the apply engine in `validate_only` mode, and print operation summaries plus warnings.
    - Guarantee: Returns 0 when validation passes; no target files are mutated.
    - Fails: Returns 1 for unreadable plans or failed validation.
    - When-needed: Open when you need the sanctioned preflight check for an apply plan before any live mutation.
    - Escalates-to: codex/doctrine/skills/kernel/apply.md; kernel.py
    """
    from tools.meta import apply as meta_apply

    try:
        plan_body, _invocation_context = _read_apply_plan(plan_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    config = {
        "mode": "apply",
        "plan": plan_body,
        "validate_only": True,
        "root_hint": str(state.REPO_ROOT),
    }

    result = meta_apply.run(config)
    meta = result.get("metadata", {})
    data = result.get("data", {})

    if meta.get("status") in ("success", "info"):
        warnings = data.get("warnings", [])
        ops = plan_body.get("operations", [])
        print(f"OK validate_only ops={len(ops)} warnings={len(warnings)}")

        # Show operation summary
        for i, op in enumerate(ops):
            op_type = op.get("op", "?")
            target = op.get("target", "?")
            target_exists = (state.REPO_ROOT / target).exists() if target != "?" else False
            exists_tag = "[exists]" if target_exists else "[MISSING]"
            print(f"  [{i}] {op_type:20s} {target} {exists_tag}")

        if warnings:
            print(f"\nWARNINGS:")
            for w in warnings:
                print(f"  ! {w}")
        return 0
    else:
        print(f"VALIDATION FAILED: {meta.get('error', 'unknown')}", file=sys.stderr)
        return 1


def cmd_quick_apply(op_type: str, target: str, live: bool = False, **kwargs) -> int:
    """[ACTION]
    - Teleology: Build a one-operation apply plan from CLI arguments and run the preview/live sequence for it.
    - Mechanism: Translate CLI kwargs into one operation, persist `_quick_apply_plan.json`, always dry-run first, and optionally perform a live apply.
    - Guarantee: Returns the preview result unless `live=True`, in which case the live apply runs only after a successful preview.
    - Fails: Returns the underlying apply command failure code when preview or live execution fails.
    - When-needed: Open when a one-off kernel mutation should still go through apply-plan generation instead of ad hoc file editing.
    - Escalates-to: codex/doctrine/skills/kernel/apply.md; kernel.py
    """
    # Build single-op plan
    operation = {"op": op_type, "target": target}

    # Map CLI kwargs to operation fields
    field_map = {
        "search": "search", "replace": "replace", "fuzzy": "fuzzy",
        "function_name": "function_name", "new_body": "new_body",
        "after_function": "after_function", "code": "code",
        "statement": "statement", "tag": "tag", "content": "content",
        "scope": "scope", "section": "section",
    }
    for cli_key, op_key in field_map.items():
        if cli_key in kwargs and kwargs[cli_key] is not None:
            operation[op_key] = kwargs[cli_key]

    plan = {"operations": [operation]}

    # Write plan for inspection
    plan_path = state.APPLY_DIR / "_quick_apply_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Plan: {_rel(plan_path)}")
    print(f"  op={op_type} target={target}")
    for k, v in operation.items():
        if k not in ("op", "target"):
            preview = str(v)[:80] + ("..." if len(str(v)) > 80 else "")
            print(f"  {k}={preview}")

    # Always dry-run first
    print(f"\nDry-running...")
    preview_rc = cmd_apply(plan_path, dry_run=True, capture_diffs=True)
    if preview_rc != 0 or not live:
        return preview_rc

    print(f"\nApplying live...")
    return cmd_apply(plan_path, dry_run=False, capture_diffs=True)


def cmd_check(plan_doc: str, code_files: list[str]) -> int:
    """[ACTION]
    - Teleology: Check whether plan-document invariants appear in the current codebase.
    - Mechanism: Read the plan doc plus requested code files, extract code-referencing checklist items, and report found-versus-missing matches deterministically.
    - Guarantee: Returns 0 after printing an invariant coverage report; no files are mutated.
    - Fails: Returns 1 only when the plan document cannot be found.
    - When-needed: Open when a kernel session needs the deterministic plan-versus-code check surface instead of a freeform review.
    - Escalates-to: system/lib/kernel/commands/navigate.py::cmd_plan_phase; kernel.py
    """
    # Resolve plan doc
    plan_path = Path(plan_doc)
    if not plan_path.is_absolute():
        plan_path = state.REPO_ROOT / plan_doc
    if not plan_path.exists():
        print(f"ERROR: Plan document not found: {plan_doc}", file=sys.stderr)
        return 1

    plan_text = plan_path.read_text(encoding="utf-8")

    # Extract invariants: lines that look like implementation directives
    invariants = []
    current_section = ""
    for line in plan_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("##"):
            current_section = stripped.lstrip("#").strip()
        elif stripped.startswith("- ") or stripped.startswith("1.") or stripped.startswith("2.") or stripped.startswith("3.") or stripped.startswith("4.") or stripped.startswith("5."):
            # Check if it references code artifacts
            has_code_ref = any(marker in stripped for marker in [
                "`", "()", ".py", ".json", ".ts", ".tsx", ".md",
                "def ", "class ", "import ", "raise ", "return ",
                "cache_policy", "target_time_iso", "as_of", "horizon",
                "hard_failure", "missing_artifacts", "HTTPException",
            ])
            if has_code_ref:
                invariants.append({"section": current_section, "text": stripped, "found_in": []})

    if not invariants:
        print("No code invariants extracted from plan document.")
        return 0

    # Read code files and check each invariant
    code_contents: dict[str, str] = {}
    for cf in code_files:
        cfp = Path(cf)
        if not cfp.is_absolute():
            cfp = state.REPO_ROOT / cf
        if cfp.exists():
            try:
                code_contents[cf] = cfp.read_text(encoding="utf-8")
            except Exception:
                code_contents[cf] = ""
        else:
            print(f"  WARNING: code file not found: {cf}")

    # For each invariant, extract searchable tokens and check presence in code
    print(f"{'=' * 70}")
    print(f"PLAN CHECK: {plan_path.name}")
    print(f"  invariants extracted: {len(invariants)}")
    print(f"  code files loaded: {len(code_contents)}")
    print(f"{'=' * 70}")

    found_count = 0
    missing_count = 0

    for inv in invariants:
        # Extract backtick-quoted tokens as search patterns
        tokens = re.findall(r'`([^`]+)`', inv["text"])
        # Also extract quoted strings
        tokens += re.findall(r'"([^"]+)"', inv["text"])
        # Also look for specific patterns
        tokens += re.findall(r'(\w+(?:\.\w+)+)\s*(?:\(|==|!=|>=|<=|>|<)', inv["text"])

        if not tokens:
            continue

        matches = []
        for cf, content in code_contents.items():
            for token in tokens:
                # Clean token for search
                search_token = token.strip()
                if len(search_token) < 3:
                    continue
                if search_token in content:
                    matches.append(f"{cf}")
                    break

        inv["found_in"] = list(set(matches))
        status = "FOUND" if matches else "MISSING"

        if matches:
            found_count += 1
        else:
            missing_count += 1

        marker = "+" if matches else "-"
        section_short = inv["section"][:30] if inv["section"] else ""
        print(f"\n  [{marker}] {status} ({section_short})")
        print(f"      {inv['text'][:120]}")
        if tokens:
            print(f"      tokens: {', '.join(tokens[:5])}")
        if matches:
            print(f"      in: {', '.join(inv['found_in'])}")

    # Summary
    total = found_count + missing_count
    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {found_count}/{total} invariants found, {missing_count}/{total} missing")
    if total > 0:
        pct = int(100 * found_count / total)
        print(f"  coverage: {pct}%")
    print(f"{'=' * 70}")

    return 0


def cmd_scratchpad(show_pass: bool = False, as_json: bool = False) -> int:
    """[ACTION]
    - Teleology: Run the standalone scratchpad verification script through the kernel CLI.
    - Mechanism: Assemble the `scratchpad.py` subprocess command with optional flags and return the subprocess exit code.
    - Guarantee: Returns the wrapped scratchpad process exit code directly.
    - Fails: Returns 1 immediately when `scratchpad.py` is missing.
    - When-needed: Open when you need the exact kernel wrapper around `scratchpad.py` rather than invoking the script manually.
    - Escalates-to: kernel.py; codex/doctrine/skills/kernel/apply.md
    """
    if not state.SCRATCHPAD_PY.exists():
        print(f"ERROR: scratchpad.py not found at {state.SCRATCHPAD_PY}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(state.SCRATCHPAD_PY)]
    if show_pass:
        cmd.append("--show-pass")
    if as_json:
        cmd.append("--json")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode
