#!/usr/bin/env python3
"""YouTube story package compiler for demo-take recordings.

This is the corrected product gate: instead of asking "did the operator name
substrate concepts often enough to trigger bespoke animations?" (the deprecated
natural_mixed_lane_audit gate), it asks "did this recording cover the planned
video structure, and can we assemble a watchable YouTube cut?"

Inputs:
  docs/dissemination/recording_run_map_v0.json       (51-step planned itinerary)
  docs/dissemination/recording_pattern_narration_v0.json
  docs/dissemination/short_montage_sequence_v0.json
  state/dissemination/demo_takes/<take_id>/{transcript,view_timeline,per_view_segments,intent_events}

Outputs (all under state/dissemination/video_projects/<project_id>/):
  shoot_script.json
  story_coverage_audit_<take_id>.json
  intro_montage_plan.json
  chapter_plan.json
  rough_cut_plan.json
  publication_pickup_plan_<take_id>.json/.md
  publication_lock_<take_id>_<pickup_take_id>.json/.md
  youtube_package.json

Locked by codex/standards/std_demo_take_story_package.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECTS_ROOT = REPO_ROOT / "state" / "dissemination" / "video_projects"
TAKES_ROOT = REPO_ROOT / "state" / "dissemination" / "demo_takes"
RUN_MAP_PATH = REPO_ROOT / "docs" / "dissemination" / "recording_run_map_v0.json"
PATTERN_NARRATION_PATH = REPO_ROOT / "docs" / "dissemination" / "recording_pattern_narration_v0.json"
SHORT_MONTAGE_PATH = REPO_ROOT / "docs" / "dissemination" / "short_montage_sequence_v0.json"

SCHEMA_SHOOT_SCRIPT = "demo_take_shoot_script_v0"
SCHEMA_COVERAGE_AUDIT = "demo_take_story_coverage_audit_v0"
SCHEMA_INTRO_MONTAGE = "demo_take_intro_montage_plan_v0"
SCHEMA_CHAPTER_PLAN = "demo_take_chapter_plan_v0"
SCHEMA_ROUGH_CUT_PLAN = "demo_take_rough_cut_plan_v0"
SCHEMA_YOUTUBE_PACKAGE = "demo_take_youtube_package_v0"
SCHEMA_PUBLICATION_PICKUP_PLAN = "demo_take_publication_pickup_plan_v0"
SCHEMA_PUBLICATION_LOCK = "demo_take_publication_lock_v0"

YOUTUBE_MIN_CHAPTERS = 3
YOUTUBE_MIN_CHAPTER_DURATION_SECONDS = 10
DEFAULT_INTRO_DURATION_SECONDS = 18.0
DEFAULT_CONTENTS_CARD_DURATION_SECONDS = 6.0
DEFAULT_CHAPTER_CARD_DURATION_SECONDS = 2.0
DEFAULT_OUTRO_DURATION_SECONDS = 5.0
DEFAULT_PICKUP_FILE = "system/lib/kernel/commands/navigate.py"
DEFAULT_PICKUP_TAKE_ID = "take_20260528T003146Z_station_app_pickups"

# Coverage truthfulness gate (cap_quick_coverage_audit_view_id_schema_mismatch_c_8e1528c0861f):
# A view segment is "usable" only if it is long enough, scored high enough,
# public-safe, and not a retake. 0.2-second telemetry flashes never count.
USABLE_MIN_DURATION_SECONDS = 5.0
USABLE_MIN_SCORE = 0.35


import re as _re


def canonical_view_id(value: Any) -> str | None:
    """Normalize a view-id across schemas: shoot_script's camelCase surface_id,
    take view_timeline's kebab-case view_id, and any snake_case or Title Case
    fallback all canonicalize to kebab-case lower. Resolves the recorded-vs-
    planned schema mismatch in story coverage audits.

    Examples:
        canonical_view_id('rootNavigator') == 'root-navigator'
        canonical_view_id('root_navigator') == 'root-navigator'
        canonical_view_id('Root Navigator') == 'root-navigator'
        canonical_view_id('root-navigator') == 'root-navigator'
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    # Insert separator at camelCase boundary BEFORE lowering.
    s = _re.sub(r"(?<!^)(?=[A-Z])", "-", raw).lower()
    # Replace underscores and whitespace with hyphens.
    s = _re.sub(r"[_\s]+", "-", s)
    # Collapse repeated hyphens.
    s = _re.sub(r"-+", "-", s).strip("-")
    return s or None


def _is_usable_segment(seg: dict[str, Any]) -> bool:
    """Coverage truthfulness gate: a real recordable section, not a flash."""
    if not seg.get("public_safe", False):
        return False
    if float(seg.get("duration_seconds") or 0.0) < USABLE_MIN_DURATION_SECONDS:
        return False
    if float(seg.get("score") or 0.0) < USABLE_MIN_SCORE:
        return False
    intent_summary = seg.get("intent_event_summary") or {}
    if intent_summary.get("mark_retake", 0):
        return False
    if intent_summary.get("mark_private", 0):
        return False
    return True


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = _read_json(path)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_relative(path: Path) -> str:
    """Render a path as repo-relative when possible, otherwise its bare string.
    Mirrors the helper in demo_take_scene_plan.py — used so tests can drive the
    builders against tmp_path fixtures without blowing up on relative_to()."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _fmt_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def _project_root(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id


# ---------------------------------------------------------------------------
# 1. Shoot script — synthesize from planned itinerary
# ---------------------------------------------------------------------------


def build_shoot_script(
    project_id: str,
    *,
    run_map_path: Path = RUN_MAP_PATH,
    pattern_narration_path: Path = PATTERN_NARRATION_PATH,
    short_montage_path: Path = SHORT_MONTAGE_PATH,
) -> dict[str, Any]:
    run_map = _optional_json(run_map_path)
    pattern_narration = _optional_json(pattern_narration_path)
    short_montage = _optional_json(short_montage_path)

    steps: list[dict[str, Any]] = run_map.get("steps", []) or []
    narration_rows: list[dict[str, Any]] = pattern_narration.get("rows", []) or []
    narration_by_step: dict[str, dict[str, Any]] = {row.get("step_id"): row for row in narration_rows if row.get("step_id")}

    # Contents beats — group steps by block, keeping declared order. Skip
    # steps whose block id is empty, whitespace, or a non-word single character
    # (the run-map carries a literal "—" em-dash separator row that should not
    # become a chapter).
    beats: list[dict[str, Any]] = []
    seen_blocks: dict[str, dict[str, Any]] = {}
    for step in steps:
        raw_block = (step.get("block") or "").strip()
        if not raw_block or len(raw_block) < 2 or not any(ch.isalnum() for ch in raw_block):
            continue
        block = raw_block
        if block not in seen_blocks:
            beat = {
                "id": block,
                "label": _label_for_block(block),
                "block": block,
                "step_ids": [],
                "duration_target_seconds": 0.0,
            }
            seen_blocks[block] = beat
            beats.append(beat)
        seen_blocks[block]["step_ids"].append(step.get("step_id"))

    # Per-view script rows for hero-treatment fe_view steps.
    per_view: list[dict[str, Any]] = []
    for step in steps:
        if step.get("step_kind") != "fe_view":
            continue
        if step.get("recording_treatment") not in {"hero", "support"}:
            continue
        step_id = step.get("step_id")
        narration_row = narration_by_step.get(step_id, {})
        say_short = step.get("short_say") or narration_row.get("say") or step.get("flash_say") or ""
        anchors = narration_row.get("anchors", []) or step.get("long_bullets", []) or []
        pattern_refs = [pr.get("pattern_id") for pr in narration_row.get("pattern_refs", []) if isinstance(pr, dict) and pr.get("pattern_id")]
        must_show = list(step.get("long_bullets", []) or [])
        per_view.append(
            {
                "view_id": step.get("surface_id"),
                "step_id": step_id,
                "route": step.get("route"),
                "block": step.get("block"),
                "recording_treatment": step.get("recording_treatment"),
                "say_short": say_short,
                "must_show": must_show,
                "avoid": [
                    "explaining every concept individually",
                    "reading labels one by one",
                    "long pauses while finding the right tab",
                ],
                "long_anchors": anchors,
                "pattern_refs": pattern_refs,
                "public_claim_boundary": step.get("public_claim_boundary"),
                "view_checklist": step.get("view_checklist"),
            }
        )

    short_seq = short_montage.get("sequence", []) or []
    hook_lines = [
        "In this video I'm going to show the system operating live, not describe it abstractly.",
        "Every claim has a receipt; every surface has a route; every recording becomes editable evidence.",
    ]
    if short_seq:
        hook_lines.append(short_seq[0].get("flash_say") or "")
    return {
        "schema": SCHEMA_SHOOT_SCRIPT,
        "project_id": project_id,
        "created_at": _now_iso(),
        "source_run_map": _safe_relative(run_map_path) if run_map_path.exists() else None,
        "source_pattern_narration": _safe_relative(pattern_narration_path) if pattern_narration_path.exists() else None,
        "source_short_montage": _safe_relative(short_montage_path) if short_montage_path.exists() else None,
        "video_title_working": run_map.get("framing", {}).get("video_title_working") if isinstance(run_map.get("framing"), dict) else None or "AI Workflow — Live Demo",
        "hook_lines": [h for h in hook_lines if h],
        "contents_beats": beats,
        "per_view_script": per_view,
        "per_view_script_count": len(per_view),
        "contents_beat_count": len(beats),
    }


def _label_for_block(block_id: str) -> str:
    # Friendly label fallback; readable but unopinionated.
    return block_id.replace("_", " ").title()


# ---------------------------------------------------------------------------
# 2. Story coverage audit — score a take against the shoot script
# ---------------------------------------------------------------------------


def _intent_events_for_view_span(
    intent_events: list[dict[str, Any]],
    start: float,
    end: float,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ev in intent_events:
        t = ev.get("video_t_seconds")
        if t is None:
            continue
        try:
            tf = float(t)
        except (TypeError, ValueError):
            continue
        if start <= tf < end + 0.5:
            kind = ev.get("kind") or "unknown"
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def _transcript_excerpt_for_span(
    transcript_segments: list[dict[str, Any]],
    start: float,
    end: float,
    max_chars: int = 240,
) -> str:
    parts: list[str] = []
    for seg in transcript_segments:
        s = float(seg.get("start", 0.0))
        e = float(seg.get("end", s))
        # overlap test
        if e < start or s > end:
            continue
        text = (seg.get("text") or "").strip()
        # Strip whisper marks like <|0.00|>
        cleaned: list[str] = []
        in_marker = False
        for ch in text:
            if ch == "<":
                in_marker = True
                continue
            if ch == ">":
                in_marker = False
                continue
            if not in_marker:
                cleaned.append(ch)
        parts.append("".join(cleaned).strip().strip('"').strip())
        if sum(len(p) for p in parts) >= max_chars:
            break
    out = " ".join(p for p in parts if p)
    if len(out) > max_chars:
        out = out[: max_chars - 1] + "…"
    return out


def _score_view_segment(
    *,
    span_duration: float,
    target_duration: float,
    anchor_hits: int,
    anchor_total: int,
    intent_counts: dict[str, int],
) -> float:
    duration_component = min(1.0, span_duration / max(1.0, target_duration))
    anchor_component = (anchor_hits / anchor_total) if anchor_total else 0.5
    retake_penalty = 0.3 * intent_counts.get("mark_retake", 0)
    confusing_penalty = 0.2 * intent_counts.get("mark_confusing", 0)
    private_penalty = 1.0 if intent_counts.get("mark_private", 0) else 0.0
    good_bonus = 0.15 * intent_counts.get("mark_good", 0)
    verdict_bonus = 0.0
    verdict = intent_counts.get("view_verdict_high", 0)
    if verdict:
        verdict_bonus = 0.2
    score = (
        0.55 * duration_component
        + 0.30 * anchor_component
        + good_bonus
        + verdict_bonus
        - retake_penalty
        - confusing_penalty
        - private_penalty
    )
    return max(0.0, min(1.0, round(score, 3)))


def build_story_coverage_audit(
    project_id: str,
    take_id: str,
    shoot_script: dict[str, Any],
    *,
    takes_root: Path = TAKES_ROOT,
    min_segment_duration_seconds: float = 5.0,
) -> dict[str, Any]:
    take_root = takes_root / take_id
    if not take_root.is_dir():
        return {
            "schema": SCHEMA_COVERAGE_AUDIT,
            "project_id": project_id,
            "take_id": take_id,
            "created_at": _now_iso(),
            "status": "fail",
            "covered_beats": [],
            "missed_beats": [b["id"] for b in shoot_script.get("contents_beats", [])],
            "best_view_segments": [],
            "recommended_next_recording": [f"Take {take_id} not found at {take_root}"],
            "coverage_percent": 0.0,
        }
    # Wave 4 preference: if the multimodal take index already wrote
    # candidate_clips.json + view_episodes.json, those are the editorial
    # authority. Raw view_timeline scoring is the fallback path.
    candidate_clips_path = take_root / "candidate_clips.json"
    view_episodes_path = take_root / "view_episodes.json"
    if candidate_clips_path.exists() and view_episodes_path.exists():
        return _coverage_audit_from_candidate_clips(
            project_id=project_id,
            take_id=take_id,
            shoot_script=shoot_script,
            candidate_clips=_optional_json(candidate_clips_path),
            view_episodes=_optional_json(view_episodes_path),
        )
    transcript = _optional_json(take_root / "transcript" / "transcript.json")
    view_timeline = _optional_json(take_root / "view_timeline.json")
    intent_events_doc = _optional_json(take_root / "intent_events.json")
    per_view_segments = _optional_json(take_root / "per_view_segments.json")

    transcript_segments = transcript.get("segments", []) or []
    view_spans = view_timeline.get("spans", []) or []
    intent_events = intent_events_doc.get("events", []) or []

    # Index script rows by CANONICAL view_id for cross-schema lookup. The shoot
    # script uses run_map surface_id (camelCase); take view_timeline uses
    # frontend telemetry view_id (kebab). Canonicalize both ends.
    per_view_script_by_view: dict[str, dict[str, Any]] = {}
    for row in shoot_script.get("per_view_script", []) or []:
        view_id = canonical_view_id(row.get("view_id"))
        if view_id:
            per_view_script_by_view[view_id] = row

    # Score every view span against its matching script row.
    best_segments: list[dict[str, Any]] = []
    for span in view_spans:
        raw_view_id = span.get("view_id")
        view_id = canonical_view_id(raw_view_id)
        if not view_id:
            continue
        start = float(span.get("start_video_t", 0.0))
        end = float(span.get("end_video_t", start))
        duration = max(0.0, end - start)
        if duration < min_segment_duration_seconds:
            # Calibration / inadvertent flashes — keep but mark low score; the
            # operator can still see them in the audit.
            pass
        script_row = per_view_script_by_view.get(view_id, {})
        anchors = script_row.get("long_anchors", []) or []
        excerpt = _transcript_excerpt_for_span(transcript_segments, start, end)
        anchor_hits = _count_anchor_hits(anchors, excerpt)
        intent_counts = _intent_events_for_view_span(intent_events, start, end)
        score = _score_view_segment(
            span_duration=duration,
            target_duration=20.0,  # rule-of-thumb target per view
            anchor_hits=anchor_hits,
            anchor_total=len(anchors),
            intent_counts=intent_counts,
        )
        public_safe = "mark_private" not in intent_counts
        reason_parts: list[str] = []
        reason_parts.append(f"view covered for {duration:.1f}s")
        if anchors:
            reason_parts.append(f"{anchor_hits}/{len(anchors)} anchors matched in transcript")
        if intent_counts.get("mark_retake"):
            reason_parts.append(f"{intent_counts['mark_retake']} retake mark(s)")
        if intent_counts.get("mark_confusing"):
            reason_parts.append(f"{intent_counts['mark_confusing']} confusing mark(s)")
        if intent_counts.get("mark_good"):
            reason_parts.append(f"{intent_counts['mark_good']} mark_good")
        if not public_safe:
            reason_parts.append("PRIVATE — excluded from public cut")
        seg_row = {
            "view_id": view_id,
            "view_id_raw": raw_view_id,
            "view_label": span.get("view_label"),
            "route": span.get("route"),
            "view_span_id": span.get("id"),
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "duration_seconds": round(duration, 3),
            "score": score,
            "reason": "; ".join(reason_parts),
            "transcript_excerpt": excerpt,
            "intent_event_summary": intent_counts,
            "public_safe": public_safe,
        }
        seg_row["usable"] = _is_usable_segment(seg_row)
        if not seg_row["usable"]:
            usable_blockers: list[str] = []
            if not public_safe:
                usable_blockers.append("not_public_safe")
            if duration < USABLE_MIN_DURATION_SECONDS:
                usable_blockers.append(f"duration<{USABLE_MIN_DURATION_SECONDS}s")
            if score < USABLE_MIN_SCORE:
                usable_blockers.append(f"score<{USABLE_MIN_SCORE}")
            if intent_counts.get("mark_retake"):
                usable_blockers.append("mark_retake")
            seg_row["usable_blockers"] = usable_blockers
        best_segments.append(seg_row)
    best_segments.sort(key=lambda r: -r["score"])

    # covered_views must come from USABLE segments only — not any public-safe
    # span. A 0.2s flash from telemetry never counts as coverage.
    covered_views = {s["view_id"] for s in best_segments if s.get("usable")}
    covered_beats: list[str] = []
    missed_beats: list[str] = []
    for beat in shoot_script.get("contents_beats", []) or []:
        beat_id = beat["id"]
        step_ids = set(beat.get("step_ids", []) or [])
        beat_views: set[str] = set()
        for row in shoot_script.get("per_view_script", []) or []:
            if row.get("step_id") in step_ids and row.get("view_id"):
                canon = canonical_view_id(row["view_id"])
                if canon:
                    beat_views.add(canon)
        if not beat_views:
            continue  # not a recordable beat (e.g., intro/outro non-view blocks)
        if beat_views & covered_views:
            covered_beats.append(beat_id)
        else:
            missed_beats.append(beat_id)

    total_recordable = len(covered_beats) + len(missed_beats)
    coverage_percent = (len(covered_beats) / total_recordable * 100.0) if total_recordable else 0.0
    coverage_percent = round(coverage_percent, 1)

    if missed_beats:
        recommended = [f"Record {b} section" for b in missed_beats]
    else:
        recommended = ["Coverage is complete; proceed to assemble rough cut."]
    if not any(s["score"] >= 0.6 for s in best_segments):
        recommended.append("Re-record best-scoring sections at slower pace; current best score < 0.6.")
    if not any(intent_events for _ in [0]):
        pass  # intent_events presence noted via best_segments reasons
    status = "pass" if covered_beats and not missed_beats else ("warn" if covered_beats else "fail")

    return {
        "schema": SCHEMA_COVERAGE_AUDIT,
        "project_id": project_id,
        "take_id": take_id,
        "created_at": _now_iso(),
        "status": status,
        "covered_beats": covered_beats,
        "missed_beats": missed_beats,
        "best_view_segments": best_segments,
        "recommended_next_recording": recommended,
        "coverage_percent": coverage_percent,
        "total_view_segments": len(best_segments),
    }


def _coverage_audit_from_candidate_clips(
    *,
    project_id: str,
    take_id: str,
    shoot_script: dict[str, Any],
    candidate_clips: dict[str, Any],
    view_episodes: dict[str, Any],
) -> dict[str, Any]:
    """Coverage audit derived from the multimodal take index. Treats
    view_explanation candidate_clips as the editorial truth for "covered_views";
    explicit retake_reject / private_reject clips never count as coverage."""
    clips = candidate_clips.get("clips", []) or []
    # Project candidate_clips into best_view_segments shape that downstream
    # consumers (rough_cut_plan_assembly, intro_montage_plan) already speak.
    best_view_segments: list[dict[str, Any]] = []
    for clip in clips:
        view_id = canonical_view_id(clip.get("view_id"))
        if not view_id:
            continue
        usable = clip.get("clip_kind") in {"view_explanation", "hook_candidate", "outro_candidate"}
        best_view_segments.append({
            "view_id": view_id,
            "view_id_raw": clip.get("view_id"),
            "view_label": clip.get("view_label"),
            "route": clip.get("route"),
            "view_span_id": (clip.get("episode_refs") or [None])[0],
            "start_seconds": float(clip.get("start_seconds") or 0.0),
            "end_seconds": float(clip.get("end_seconds") or 0.0),
            "duration_seconds": float(clip.get("duration_seconds") or 0.0),
            "score": float(clip.get("score") or 0.0),
            "reason": clip.get("why") or "",
            "transcript_excerpt": "",  # not duplicated here; available via view_episodes if needed
            "intent_event_summary": {},
            "public_safe": bool(clip.get("public_safe", True)),
            "usable": usable,
            "clip_kind": clip.get("clip_kind"),
            "exclude_reason": clip.get("exclude_reason"),
            "source": "candidate_clips",
        })
    best_view_segments.sort(key=lambda r: -r["score"])

    covered_views = {s["view_id"] for s in best_view_segments if s.get("usable")}
    covered_beats: list[str] = []
    missed_beats: list[str] = []
    for beat in shoot_script.get("contents_beats", []) or []:
        beat_id = beat["id"]
        step_ids = set(beat.get("step_ids", []) or [])
        beat_views: set[str] = set()
        for row in shoot_script.get("per_view_script", []) or []:
            if row.get("step_id") in step_ids and row.get("view_id"):
                canon = canonical_view_id(row["view_id"])
                if canon:
                    beat_views.add(canon)
        if not beat_views:
            continue
        if beat_views & covered_views:
            covered_beats.append(beat_id)
        else:
            missed_beats.append(beat_id)

    total_recordable = len(covered_beats) + len(missed_beats)
    coverage_percent = round(
        (len(covered_beats) / total_recordable * 100.0) if total_recordable else 0.0,
        1,
    )
    if missed_beats:
        recommended = [f"Record {b} section" for b in missed_beats]
    else:
        recommended = ["Coverage is complete; proceed to assemble rough cut."]
    status = "pass" if covered_beats and not missed_beats else ("warn" if covered_beats else "fail")
    return {
        "schema": SCHEMA_COVERAGE_AUDIT,
        "project_id": project_id,
        "take_id": take_id,
        "created_at": _now_iso(),
        "status": status,
        "covered_beats": covered_beats,
        "missed_beats": missed_beats,
        "best_view_segments": best_view_segments,
        "recommended_next_recording": recommended,
        "coverage_percent": coverage_percent,
        "total_view_segments": len(best_view_segments),
        "input_source": "candidate_clips",
        "usable_episode_count": view_episodes.get("usable_episode_count", 0),
        "view_episode_count": view_episodes.get("episode_count", 0),
    }


def _count_anchor_hits(anchors: list[str], text: str) -> int:
    if not anchors or not text:
        return 0
    lower = text.lower()
    hits = 0
    for anchor in anchors:
        head = (anchor or "").split(".")[0].strip().lower()
        if len(head) < 4:
            continue
        # Word-ish match: at least 2 content words from the anchor head appear
        # in the transcript.
        anchor_words = [w for w in head.split() if len(w) >= 4]
        if not anchor_words:
            continue
        present = sum(1 for w in anchor_words if w in lower)
        if present >= max(1, len(anchor_words) // 2):
            hits += 1
    return hits


# ---------------------------------------------------------------------------
# 3. Intro montage plan — pull best clips from take(s) to fill montage slots
# ---------------------------------------------------------------------------


def build_intro_montage_plan(
    project_id: str,
    take_id: str,
    coverage_audit: dict[str, Any],
    *,
    short_montage_path: Path = SHORT_MONTAGE_PATH,
    duration_target_seconds: float = DEFAULT_INTRO_DURATION_SECONDS,
) -> dict[str, Any]:
    montage = _optional_json(short_montage_path)
    sequence = montage.get("sequence", []) or []
    best_segments = coverage_audit.get("best_view_segments", []) or []
    # Index by canonical view_id; only keep usable segments (a 0.2s flash is
    # never a good montage clip).
    best_by_view: dict[str, dict[str, Any]] = {}
    for seg in best_segments:
        if not seg.get("usable"):
            continue
        v = canonical_view_id(seg.get("view_id"))
        if not v:
            continue
        if v not in best_by_view or best_by_view[v]["score"] < seg["score"]:
            best_by_view[v] = seg

    clips: list[dict[str, Any]] = []
    accumulated = 0.0
    for entry in sequence:
        target = float(entry.get("duration_target_seconds") or 1.0)
        if accumulated + target > duration_target_seconds * 1.3:
            break
        # Canonicalize candidates from step_id/capture_slug so kebab/camel/snake
        # all collapse into the same lookup key.
        step_id = entry.get("step_id") or ""
        view_candidates = _view_id_candidates_from_step(step_id, entry.get("capture_slug"))
        canon_candidates = [canonical_view_id(v) for v in view_candidates if v]
        chosen: dict[str, Any] | None = None
        for v in canon_candidates:
            if v and v in best_by_view:
                chosen = best_by_view[v]
                break
        if chosen is None:
            # No real take segment for this slot — emit a caption-only flash with
            # no clip ref; the renderer can substitute a still frame later.
            clips.append({
                "ord": entry.get("ord"),
                "kind": "still_flash",
                "take_id": None,
                "view_id": view_candidates[0] if view_candidates else None,
                "start_seconds": None,
                "end_seconds": None,
                "duration_seconds": target,
                "caption": entry.get("flash_say") or entry.get("title") or "",
                "source_step_id": step_id,
                "remotion_static_path": None,
            })
        else:
            # Pick a target-duration window inside the chosen span; default to
            # the first `target` seconds.
            seg_start = float(chosen["start_seconds"])
            seg_end = float(chosen["end_seconds"])
            window_end = min(seg_end, seg_start + target)
            clip_dur = max(0.5, window_end - seg_start)
            clips.append({
                "ord": entry.get("ord"),
                "kind": "frontend_flash",
                "take_id": take_id,
                "view_id": chosen["view_id"],
                "start_seconds": round(seg_start, 3),
                "end_seconds": round(window_end, 3),
                "duration_seconds": round(clip_dur, 3),
                "caption": entry.get("flash_say") or entry.get("title") or "",
                "source_step_id": step_id,
                "remotion_static_path": f"take-assets/{take_id}/tracks/screen_2.mp4",
            })
        accumulated += target
    return {
        "schema": SCHEMA_INTRO_MONTAGE,
        "project_id": project_id,
        "created_at": _now_iso(),
        "duration_target_seconds": round(duration_target_seconds, 3),
        "clip_count": len(clips),
        "clips": clips,
        "source_short_montage": _safe_relative(short_montage_path) if short_montage_path.exists() else None,
    }


def _view_id_candidates_from_step(step_id: str, capture_slug: str | None) -> list[str]:
    out: list[str] = []
    if step_id and "." in step_id:
        tail = step_id.split(".", 1)[1]
        out.append(tail)
        # snake_case + kebab-case variants
        import re
        kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", tail).lower()
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", tail).lower()
        out.extend([kebab, snake])
    if capture_slug:
        out.append(capture_slug)
        out.append(capture_slug.replace("_", "-"))
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------------------
# 4. Chapter plan — YouTube-compatible chapter map
# ---------------------------------------------------------------------------


def build_chapter_plan(
    project_id: str,
    rough_cut_plan: dict[str, Any] | None = None,
    *,
    shoot_script: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a chapter map. When a rough_cut_plan is supplied, use its actual
    scene timestamps; otherwise estimate from shoot_script.contents_beats."""
    chapters: list[dict[str, Any]] = []
    if rough_cut_plan:
        running = 0.0
        ord_idx = 0
        intro_emitted = False
        for scene in rough_cut_plan.get("scenes", []) or []:
            dur = float(scene.get("duration_seconds") or 0.0)
            kind = scene.get("kind")
            # Intro + contents card are collapsed into one "Intro" chapter at
            # 0:00 — YouTube wants real section boundaries, not a chapter per
            # title card. Per-section chapter_card scenes still emit one chapter
            # each at their actual start time. outro_card emits a final chapter.
            if kind in {"intro_montage", "contents_card"} and not intro_emitted:
                ord_idx += 1
                chapters.append({
                    "ord": ord_idx,
                    "start_seconds": 0.0,
                    "start_timestamp": _fmt_timestamp(0.0),
                    "title": "Intro",
                    "source_beat_id": "intro",
                })
                intro_emitted = True
            elif kind in {"chapter_card", "outro_card"}:
                ord_idx += 1
                chapters.append({
                    "ord": ord_idx,
                    "start_seconds": round(running, 3),
                    "start_timestamp": _fmt_timestamp(running),
                    "title": scene.get("title") or scene.get("id"),
                    "source_beat_id": scene.get("source_beat_id"),
                })
            running += dur
    elif shoot_script:
        # Estimate ~30s per beat as a planning placeholder.
        estimate = 30.0
        running = 0.0
        ord_idx = 0
        for beat in shoot_script.get("contents_beats", []) or []:
            ord_idx += 1
            chapters.append({
                "ord": ord_idx,
                "start_seconds": round(running, 3),
                "start_timestamp": _fmt_timestamp(running),
                "title": beat.get("label") or beat.get("id"),
                "source_beat_id": beat.get("id"),
            })
            running += estimate

    # Enforce YouTube constraints: ≥3 chapters, first at 0, each ≥10s, ascending.
    starts_at_zero = bool(chapters) and chapters[0]["start_seconds"] == 0
    at_least_three = len(chapters) >= YOUTUBE_MIN_CHAPTERS
    ascending = all(
        chapters[i]["start_seconds"] < chapters[i + 1]["start_seconds"]
        for i in range(len(chapters) - 1)
    ) if len(chapters) > 1 else True
    min_dur_ok = True
    for i in range(len(chapters) - 1):
        if chapters[i + 1]["start_seconds"] - chapters[i]["start_seconds"] < YOUTUBE_MIN_CHAPTER_DURATION_SECONDS:
            min_dur_ok = False
            break
    validation = {
        "starts_at_zero": starts_at_zero,
        "at_least_three_chapters": at_least_three,
        "all_chapters_min_ten_seconds": min_dur_ok,
        "ascending_order": ascending,
    }
    youtube_compatible = all(validation.values())
    return {
        "schema": SCHEMA_CHAPTER_PLAN,
        "project_id": project_id,
        "created_at": _now_iso(),
        "chapters": chapters,
        "chapter_count": len(chapters),
        "youtube_compatible": youtube_compatible,
        "validation": validation,
    }


# ---------------------------------------------------------------------------
# 5. Rough cut plan — full scene sequence consumed by render-story-package
# ---------------------------------------------------------------------------


def build_rough_cut_plan(
    project_id: str,
    take_id: str,
    coverage_audit: dict[str, Any],
    intro_montage_plan: dict[str, Any],
    shoot_script: dict[str, Any],
    *,
    min_view_clip_duration_seconds: float = 6.0,
) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    order = 0
    running = 0.0

    # Scene 1: intro montage (one scene; renderer expands sub-clips).
    intro_clips = intro_montage_plan.get("clips", []) or []
    intro_dur = float(intro_montage_plan.get("duration_target_seconds") or DEFAULT_INTRO_DURATION_SECONDS)
    if intro_clips:
        order += 1
        scenes.append({
            "id": "scene_intro_montage",
            "order_index": order,
            "kind": "intro_montage",
            "title": "Hook",
            "duration_seconds": round(intro_dur, 3),
            "audio_source": None,
            "video_source": None,
            "intro_clips": intro_clips,
            "chapter_items": None,
            "public_safe": True,
            "source_beat_id": "intro",
        })
        running += intro_dur

    # Scene 2: contents card.
    contents_items = [
        {"label": b.get("label"), "beat_id": b.get("id")}
        for b in shoot_script.get("contents_beats", []) or []
        if b.get("id") not in {"intro", "outro"}
    ]
    order += 1
    scenes.append({
        "id": "scene_contents_card",
        "order_index": order,
        "kind": "contents_card",
        "title": "Contents",
        "duration_seconds": DEFAULT_CONTENTS_CARD_DURATION_SECONDS,
        "audio_source": None,
        "video_source": None,
        "intro_clips": None,
        "chapter_items": contents_items,
        "public_safe": True,
        "source_beat_id": "contents",
    })
    running += DEFAULT_CONTENTS_CARD_DURATION_SECONDS

    # Scenes 3..N: one chapter card + one view clip per covered beat. View
    # selection uses USABLE segments only and matches across canonical view_id
    # forms so kebab-vs-camel doesn't false-miss.
    best_segments = coverage_audit.get("best_view_segments", []) or []
    best_usable = [s for s in best_segments if s.get("usable")]
    best_by_view: dict[str, dict[str, Any]] = {}
    for seg in best_usable:
        v = canonical_view_id(seg.get("view_id"))
        if not v:
            continue
        if v not in best_by_view or best_by_view[v]["score"] < seg["score"]:
            best_by_view[v] = seg

    per_view_by_step: dict[str, dict[str, Any]] = {row.get("step_id"): row for row in shoot_script.get("per_view_script", []) or [] if row.get("step_id")}
    for beat in shoot_script.get("contents_beats", []) or []:
        beat_id = beat.get("id")
        if beat_id in {"intro", "outro"}:
            continue
        # Find the first hero-treatment per_view row in this beat's step_ids.
        chosen_view: dict[str, Any] | None = None
        chosen_row: dict[str, Any] | None = None
        for sid in beat.get("step_ids", []) or []:
            row = per_view_by_step.get(sid)
            if not row:
                continue
            canon = canonical_view_id(row.get("view_id"))
            if not canon:
                continue
            seg = best_by_view.get(canon)
            if seg:
                chosen_view = seg
                chosen_row = row
                break
        if not chosen_view:
            continue
        order += 1
        scenes.append({
            "id": f"scene_chapter_{beat_id}",
            "order_index": order,
            "kind": "chapter_card",
            "title": beat.get("label"),
            "duration_seconds": DEFAULT_CHAPTER_CARD_DURATION_SECONDS,
            "audio_source": None,
            "video_source": None,
            "intro_clips": None,
            "chapter_items": None,
            "public_safe": True,
            "source_beat_id": beat_id,
        })
        running += DEFAULT_CHAPTER_CARD_DURATION_SECONDS

        # View clip — clip to the planned target inside the chosen span.
        seg_start = float(chosen_view["start_seconds"])
        seg_end = float(chosen_view["end_seconds"])
        clip_duration = max(min_view_clip_duration_seconds, min(seg_end - seg_start, 45.0))
        clip_end = seg_start + clip_duration
        order += 1
        scenes.append({
            "id": f"scene_view_{chosen_view['view_id']}",
            "order_index": order,
            "kind": "view_clip",
            "title": (chosen_row or {}).get("say_short") or chosen_view.get("view_label") or chosen_view["view_id"],
            "duration_seconds": round(clip_duration, 3),
            "audio_source": {
                "take_id": take_id,
                "transcript_segment_ids": [],
                "start_seconds": round(seg_start, 3),
                "end_seconds": round(clip_end, 3),
                "duration_seconds": round(clip_duration, 3),
            },
            "video_source": {
                "take_id": take_id,
                "track_id": "screen_2",
                "start_seconds": round(seg_start, 3),
                "end_seconds": round(clip_end, 3),
                "duration_seconds": round(clip_duration, 3),
            },
            "intro_clips": None,
            "chapter_items": None,
            "public_safe": True,
            "source_beat_id": beat_id,
            "view_id": chosen_view["view_id"],
            "view_label": chosen_view.get("view_label"),
            "route": chosen_view.get("route"),
        })
        running += clip_duration

    # Outro card.
    order += 1
    scenes.append({
        "id": "scene_outro",
        "order_index": order,
        "kind": "outro_card",
        "title": "Thanks for watching",
        "duration_seconds": DEFAULT_OUTRO_DURATION_SECONDS,
        "audio_source": None,
        "video_source": None,
        "intro_clips": None,
        "chapter_items": None,
        "public_safe": True,
        "source_beat_id": "outro",
    })
    running += DEFAULT_OUTRO_DURATION_SECONDS

    return {
        "schema": SCHEMA_ROUGH_CUT_PLAN,
        "project_id": project_id,
        "created_at": _now_iso(),
        "take_ids": [take_id],
        "duration_seconds": round(running, 3),
        "scene_count": len(scenes),
        "scenes": scenes,
        "public_safe": True,
    }


# ---------------------------------------------------------------------------
# 6. YouTube package — titles / description / chapters / thumbnails
# ---------------------------------------------------------------------------


def build_youtube_package(
    project_id: str,
    *,
    shoot_script: dict[str, Any],
    chapter_plan: dict[str, Any],
    take_id: str | None = None,
    coverage_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title_seed = shoot_script.get("video_title_working") or "AI Workflow Live Demo"
    titles = [
        title_seed,
        "I Built an AI Workflow OS That Records Its Own Evidence",
        "The Substrate Behind the System — Live Demo",
        "Receipts, Not Vibes: An AI Workflow Walkthrough",
    ]
    chapters_section_lines: list[str] = []
    for c in chapter_plan.get("chapters", []) or []:
        chapters_section_lines.append(f"{c['start_timestamp']} {c['title']}")
    hook = " ".join(shoot_script.get("hook_lines") or [])
    beat_summary = ", ".join(
        b.get("label", "") for b in shoot_script.get("contents_beats", []) or []
        if b.get("id") not in {"intro", "outro"}
    )
    description = (
        f"{hook}\n\nWhat you see in this video: {beat_summary}.\n\n"
        f"Chapters\n" + "\n".join(chapters_section_lines)
    )
    thumbnail_candidates: list[dict[str, Any]] = []
    if take_id and coverage_audit:
        top_segments = coverage_audit.get("best_view_segments", [])[:3]
        for idx, seg in enumerate(top_segments):
            mid = float(seg["start_seconds"]) + float(seg["duration_seconds"]) / 2.0
            frame_index = max(1, int(round(mid)))
            thumbnail_candidates.append({
                "background_frame": f"asset://{take_id}/frames/screen_2_{frame_index:06d}.jpg",
                "text": (seg.get("view_label") or seg.get("view_id") or "AI Workflow").upper(),
                "badge": "LIVE DEMO" if idx == 0 else "EVIDENCE",
                "composition": "frontend screenshot + 3-word claim badge",
            })
    if not thumbnail_candidates:
        thumbnail_candidates.append({
            "background_frame": None,
            "text": "AI WORKFLOW OS",
            "badge": "LIVE DEMO",
            "composition": "title card; supply real frame after first take",
        })
    return {
        "schema": SCHEMA_YOUTUBE_PACKAGE,
        "project_id": project_id,
        "created_at": _now_iso(),
        "titles": titles,
        "description": description,
        "chapters": chapter_plan.get("chapters", []),
        "thumbnail_candidates": thumbnail_candidates,
    }


# ---------------------------------------------------------------------------
# 7. Publication pickup plan — bind take review to app-target pickups
# ---------------------------------------------------------------------------


def _review_candidates(project_id: str, take_id: str) -> list[Path]:
    return [
        _project_root(project_id) / f"take_review_{take_id}.json",
        TAKES_ROOT / take_id / "review" / "take_review.json",
    ]


def _load_take_review(project_id: str, take_id: str) -> dict[str, Any]:
    for path in _review_candidates(project_id, take_id):
        payload = _optional_json(path)
        if payload:
            return payload
    return {}


def _take_manifest(take_id: str) -> dict[str, Any]:
    return _optional_json(TAKES_ROOT / take_id / "manifest.json")


def _take_transcript(take_id: str) -> dict[str, Any]:
    return _optional_json(TAKES_ROOT / take_id / "transcript" / "transcript.json")


def _take_review(take_id: str) -> dict[str, Any]:
    return _optional_json(TAKES_ROOT / take_id / "review" / "take_review.json")


def _has_audio_or_transcript(take_id: str) -> dict[str, Any]:
    manifest = _take_manifest(take_id)
    transcript = _take_transcript(take_id)
    sources = manifest.get("sources") if isinstance(manifest.get("sources"), dict) else {}
    tracks = manifest.get("tracks") if isinstance(manifest.get("tracks"), list) else []
    microphone = sources.get("microphone") if isinstance(sources, dict) else None
    audio_tracks = [
        row for row in tracks
        if isinstance(row, dict) and str(row.get("role") or "").lower() in {"audio", "microphone", "mic"}
    ]
    transcript_status = transcript.get("status") or "missing"
    word_count = int(transcript.get("word_count") or transcript.get("timestamped_word_count") or 0)
    transcript_ready = transcript_status == "ready" and word_count > 0
    return {
        "take_id": take_id,
        "microphone_present": microphone is not None,
        "audio_track_count": len(audio_tracks),
        "transcript_status": transcript_status,
        "transcript_word_count": word_count,
        "publication_audio_ready": bool(microphone or audio_tracks or transcript_ready),
    }


def _pickup_receipt_status(pickup_take_id: str) -> dict[str, Any]:
    manifest = _take_manifest(pickup_take_id)
    receipts = manifest.get("receipts") if isinstance(manifest.get("receipts"), list) else []
    required = {"pickup.codemap.selected_node", "pickup.inspector.selected_file"}
    by_id = {row.get("id"): row for row in receipts if isinstance(row, dict) and row.get("id")}
    green = {
        rid: bool(by_id.get(rid) and by_id[rid].get("verdict") == "green")
        for rid in sorted(required)
    }
    return {
        "pickup_take_id": pickup_take_id,
        "manifest_present": bool(manifest),
        "final_capture_target": manifest.get("final_capture_target"),
        "required_pickups": green,
        "all_required_green": all(green.values()),
        "receipt_count": len(receipts),
        "receipts": [
            {
                "id": row.get("id"),
                "frame": row.get("frame"),
                "recording": row.get("recording"),
                "verdict": row.get("verdict"),
                "duration_seconds": row.get("duration_seconds"),
                "frame_size": row.get("frame_size"),
            }
            for row in receipts
            if isinstance(row, dict)
        ],
    }


def _review_rows_by_step(take_review: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in take_review.get("scene_verdicts", []) or []:
        if not isinstance(row, dict):
            continue
        step_id = row.get("step_id")
        if isinstance(step_id, str) and step_id:
            rows[step_id] = row
    return rows


def _pickup_codemap_route(pickup_file: str) -> str:
    return f"/station/codemap?focus={quote(pickup_file, safe='')}"


def _pickup_inspector_route(pickup_file: str) -> str:
    return (
        "/inspector?panel=inspect"
        f"&file={quote(pickup_file, safe='')}"
        f"&returnTo={quote('/station/codemap', safe='')}"
    )


def build_publication_pickup_plan(
    project_id: str,
    take_id: str,
    *,
    take_review: dict[str, Any] | None = None,
    pickup_file: str = DEFAULT_PICKUP_FILE,
    final_capture_target: str = "station_app",
) -> dict[str, Any]:
    """Compile the reviewed pilot into a publication pickup plan.

    This is deliberately narrower than a new run map: it treats the existing
    take as the visual bed, names the app as the final operator target, and
    requires only the two missing proof interactions.
    """
    review = take_review if take_review is not None else _load_take_review(project_id, take_id)
    review_by_step = _review_rows_by_step(review)

    def scene(
        *,
        step_id: str,
        surface: str,
        route: str,
        claim: str,
        voiceover: str,
        short_form: str,
        long_form: str,
        treatment: str,
        pickup_id: str | None = None,
    ) -> dict[str, Any]:
        review_row = review_by_step.get(step_id, {})
        return {
            "step_id": step_id,
            "surface": surface,
            "route": route,
            "claim": claim,
            "voiceover": voiceover,
            "short_form": short_form,
            "long_form": long_form,
            "treatment": treatment,
            "pickup_id": pickup_id,
            "source_review": {
                "verdict": review_row.get("verdict"),
                "decision": review_row.get("decision"),
                "evidence_frame": review_row.get("evidence_frame"),
                "review_note": review_row.get("review_note"),
            },
        }

    codemap_route = _pickup_codemap_route(pickup_file)
    inspector_route = _pickup_inspector_route(pickup_file)

    scenes = [
        scene(
            step_id="atlas.home",
            surface="Surface Atlas",
            route="/station",
            claim="The frontend is a generated map over backend substrate, not the product center.",
            voiceover=(
                "This is the map of the system. It is not a normal homepage and it is not the product. "
                "It is a generated surface over routes, surface groups, relation types, capture state, "
                "and the places where the frontend can or cannot honestly explain the substrate."
            ),
            short_form="include",
            long_form="include",
            treatment="keep_visual_bed",
        ),
        scene(
            step_id="view.rootNavigator",
            surface="Root Navigator",
            route="/station/root-navigator",
            claim="The system has a shared grammar rendered from AI-native substrate.",
            voiceover=(
                "Now we move from what surfaces exist to the grammar underneath them. The system is trying "
                "to make AI-native substrate human-readable: standards, concepts, mechanisms, evidence, "
                "and routing. The graph is a reading surface over source-owned structure."
            ),
            short_form="include",
            long_form="include",
            treatment="keep_with_projection_frame",
        ),
        scene(
            step_id="view.codemap",
            surface="Code Map",
            route=codemap_route,
            claim="Generated architecture can be interrogated at node level for auditability and blast radius.",
            voiceover=(
                "When the backend grows too quickly for manual memory, the answer cannot be a static diagram. "
                "Code Map is generated architecture: warning locality, dependency neighborhoods, and a way "
                "to ask where a change would matter. This pickup selects one file node so the claim is visible."
            ),
            short_form="pickup_required",
            long_form="pickup_required",
            treatment="replace_idle_frame_with_selected_node_pickup",
            pickup_id="pickup.codemap.selected_node",
        ),
        scene(
            step_id="view.inspector",
            surface="Inspector",
            route=inspector_route,
            claim="The generated map resolves into source-level substrate inspection.",
            voiceover=(
                "A map is not enough. Eventually you need to drop into the actual substrate: files, functions, "
                "docstrings, standards, errors, and source lines. Inspector is the bridge from generated map "
                "to source-level accountability."
            ),
            short_form="pickup_required",
            long_form="pickup_required",
            treatment="replace_idle_frame_with_selected_file_pickup",
            pickup_id="pickup.inspector.selected_file",
        ),
        scene(
            step_id="view.intelligence.default",
            surface="Intelligence Markets",
            route="/station/intelligence",
            claim="External market evidence is handled as state with provenance, validation debt, safe-use labels, and uncertainty.",
            voiceover=(
                "This is the data side. The point is not that the system predicts markets. The point is that "
                "external evidence is treated as state with provenance, safe-use constraints, validation debt, "
                "and explicit uncertainty."
            ),
            short_form="include",
            long_form="include",
            treatment="keep_visual_bed",
        ),
        scene(
            step_id="view.intelligence.work",
            surface="Intelligence Work",
            route="/station/intelligence?lens=work",
            claim="Captures, CAPs, signoff, blocked state, stale state, and residuals are visible as work substrate.",
            voiceover=(
                "This is the work spine. Captures, CAPs, signoff, blocked state, stale state, routed and "
                "unrouted work all become visible. The system is not just prompts; it has memory of work, "
                "evidence, residuals, and what still has to be resolved."
            ),
            short_form="include",
            long_form="include",
            treatment="keep_with_work_atlas_frame",
        ),
        scene(
            step_id="view.intelligence.system",
            surface="Intelligence System",
            route="/station/intelligence?lens=system",
            claim="Runtime debt and blocked state are first-class evidence, not something hidden behind a glossy demo.",
            voiceover=(
                "This is the honesty boundary. A polished demo would hide failed or stale runtime state. "
                "The better rule is the opposite: if the runtime is blocked, the system should show that as evidence."
            ),
            short_form="cut_unless_honesty_frame_required",
            long_form="include_as_debt_frame",
            treatment="long_form_frame_or_short_cut",
        ),
        {
            "step_id": "closing.microcosm_bridge",
            "surface": "Microcosm / release bridge",
            "route": None,
            "claim": "The macro-system motivates a smaller releasable microcosm rather than asking viewers to trust the full private substrate.",
            "voiceover": (
                "The public proof cannot just be a glossy frontend. It has to connect back to substrate and, "
                "eventually, to a microcosm people can run."
            ),
            "short_form": "include_as_closing_sentence",
            "long_form": "include_as_release_bridge",
            "treatment": "voiceover_bridge_no_new_surface_required",
            "pickup_id": None,
            "source_review": {},
        },
    ]

    pickup_shots = [
        {
            "id": "pickup.codemap.selected_node",
            "surface": "Code Map",
            "final_capture_target": final_capture_target,
            "route": codemap_route,
            "selected_file": pickup_file,
            "required_action": "Open Code Map in the app with the focus route or select the file node manually; hold with the node drawer populated.",
            "required_evidence": [
                "selected file path visible in the Code Map node drawer",
                "blast-radius or focus/proof-plan pane populated",
                "architecture graph visible behind the selected-node detail",
            ],
            "machine_selectors": [
                "[data-zenith-codemap-surface=\"ready\"]",
                "[data-zenith-codemap-band=\"graph\"]",
                "[data-zenith-codemap-mode=\"focus\"]",
                "[data-zenith-codemap-focus-ready=\"true\"]",
                f"[data-zenith-codemap-node=\"{pickup_file}\"]",
            ],
            "narration_bridge": "This is the same substrate seen first as generated architecture.",
        },
        {
            "id": "pickup.inspector.selected_file",
            "surface": "Inspector",
            "final_capture_target": final_capture_target,
            "route": inspector_route,
            "selected_file": pickup_file,
            "required_action": "Open Inspector in the app with the file route; hold with source/detail visible.",
            "required_evidence": [
                "Inspector surface ready",
                "selected file path visible",
                "source/detail pane visible enough to support source-level accountability",
            ],
            "machine_selectors": [
                "[data-zenith-inspector-surface=\"ready\"]",
            ],
            "narration_bridge": "Then the same substrate resolves into source inspection.",
        },
    ]

    return {
        "schema": SCHEMA_PUBLICATION_PICKUP_PLAN,
        "project_id": project_id,
        "take_id": take_id,
        "created_at": _now_iso(),
        "source_take_review": review.get("schema") and {
            "overall_verdict": review.get("overall_verdict"),
            "review_take_id": review.get("take_id"),
            "review_project_id": review.get("project_id"),
        },
        "current_state": "pilot_visual_bed_publication_no_go_until_voiceover_and_pickups",
        "final_capture_target": final_capture_target,
        "existing_visual_bed": {
            "take_id": take_id,
            "use": "visual_choreography_bed_and_reusable_clean_segments",
            "capture_environment_note": (
                "The reviewed browser/Safari take is not the operator's final target. "
                "Final publication capture should come from the app or explicitly state otherwise."
            ),
            "do_not_retake_whole_spine_by_default": True,
        },
        "short_form_sequence": [
            "atlas.home",
            "view.rootNavigator",
            "pickup.codemap.selected_node",
            "pickup.inspector.selected_file",
            "view.intelligence.default",
            "view.intelligence.work",
            "closing.microcosm_bridge",
        ],
        "long_form_sequence": [
            "atlas.home",
            "view.rootNavigator",
            "pickup.codemap.selected_node",
            "pickup.inspector.selected_file",
            "view.intelligence.default",
            "view.intelligence.work",
            "view.intelligence.system",
            "closing.microcosm_bridge",
        ],
        "audio_plan": {
            "status": "voiceover_required",
            "rule": "Record voiceover against the visual edit; do not use a silent take as publication evidence.",
            "style": "direct thinking, high-signal pedagogy, no sales demo language",
        },
        "scenes": scenes,
        "pickup_shots": pickup_shots,
        "publication_blockers": [
            {
                "id": "voiceover_missing",
                "status": "blocking",
                "resolution": "record or attach narration, then generate transcript/coverage review",
            },
            {
                "id": "codemap_selected_node_missing",
                "status": "blocking",
                "resolution": "capture pickup.codemap.selected_node in the app",
            },
            {
                "id": "inspector_selected_file_missing",
                "status": "blocking",
                "resolution": "capture pickup.inspector.selected_file in the app",
            },
        ],
        "negative_evidence_policy": {
            "chrome_leak_sheet": "internal_only",
            "rule": "Provider/operator workspace leakage is a recording-scope defect, not public scene material.",
        },
    }


def render_publication_pickup_plan_markdown(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Publication Pickup Plan")
    lines.append("")
    lines.append(f"- Project: `{plan.get('project_id')}`")
    lines.append(f"- Source take: `{plan.get('take_id')}`")
    lines.append(f"- State: `{plan.get('current_state')}`")
    lines.append(f"- Final capture target: `{plan.get('final_capture_target')}`")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(
        "Use the reviewed clean visual take as the choreography bed. Do not re-record the whole spine by default. "
        "Record voiceover against the edit, then capture only the two missing proof interactions in the app."
    )
    lines.append("")
    lines.append("## Short Form")
    lines.append("")
    for item in plan.get("short_form_sequence", []) or []:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Long Form")
    lines.append("")
    for item in plan.get("long_form_sequence", []) or []:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Pickup Shots")
    lines.append("")
    for shot in plan.get("pickup_shots", []) or []:
        lines.append(f"### {shot.get('id')}")
        lines.append("")
        lines.append(f"- Surface: {shot.get('surface')}")
        lines.append(f"- Route: `{shot.get('route')}`")
        lines.append(f"- Selected file: `{shot.get('selected_file')}`")
        lines.append(f"- Action: {shot.get('required_action')}")
        lines.append("- Required evidence:")
        for ev in shot.get("required_evidence", []) or []:
            lines.append(f"  - {ev}")
        lines.append("")
    lines.append("## Scene Voiceover Map")
    lines.append("")
    for row in plan.get("scenes", []) or []:
        lines.append(f"### {row.get('step_id')} - {row.get('surface')}")
        lines.append("")
        lines.append(f"- Treatment: `{row.get('treatment')}`")
        lines.append(f"- Short: `{row.get('short_form')}`")
        lines.append(f"- Long: `{row.get('long_form')}`")
        route = row.get("route")
        if route:
            lines.append(f"- Route: `{route}`")
        lines.append(f"- Claim: {row.get('claim')}")
        lines.append("")
        lines.append(row.get("voiceover") or "")
        lines.append("")
    lines.append("## Blockers")
    lines.append("")
    for blocker in plan.get("publication_blockers", []) or []:
        lines.append(f"- `{blocker.get('id')}`: {blocker.get('resolution')}")
    lines.append("")
    return "\n".join(lines)


def build_publication_pickup_plan_artifacts(
    project_id: str,
    take_id: str,
    *,
    pickup_file: str = DEFAULT_PICKUP_FILE,
    final_capture_target: str = "station_app",
) -> dict[str, Path]:
    project_root = _project_root(project_id)
    plan = build_publication_pickup_plan(
        project_id,
        take_id,
        pickup_file=pickup_file,
        final_capture_target=final_capture_target,
    )
    json_path = project_root / f"publication_pickup_plan_{take_id}.json"
    md_path = project_root / f"publication_pickup_plan_{take_id}.md"
    _write_json(json_path, plan)
    md_path.write_text(render_publication_pickup_plan_markdown(plan), encoding="utf-8")
    return {"publication_pickup_plan": json_path, "publication_pickup_plan_markdown": md_path}


def _source_identity_status(take_id: str, final_capture_target: str) -> dict[str, Any]:
    lower = take_id.lower()
    safari_named = "safari" in lower or "browser" in lower or "chrome" in lower
    if final_capture_target == "station_app" and safari_named:
        status = "blocked_as_public_app_identity"
        public_use = "storyboard_reference_only_unless_cropped_source_neutral_or_replaced_by_app_full_spine"
    else:
        status = "source_identity_not_blocking"
        public_use = "usable_if_reviewed_public_safe"
    return {
        "base_visual_bed_take_id": take_id,
        "final_capture_target": final_capture_target,
        "status": status,
        "safari_or_browser_provenance_detected": safari_named,
        "public_use": public_use,
        "rule": (
            "Browser/Safari receipts may remain provenance or choreography evidence; "
            "they do not define the final app-target public source identity."
        ),
    }


def _voiceover_segments_from_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scene in plan.get("scenes", []) or []:
        if not isinstance(scene, dict):
            continue
        step_id = scene.get("step_id")
        voiceover = scene.get("voiceover")
        if not step_id or not voiceover:
            continue
        rows.append({
            "step_id": step_id,
            "surface": scene.get("surface"),
            "short_form": scene.get("short_form"),
            "long_form": scene.get("long_form"),
            "claim": scene.get("claim"),
            "voiceover": voiceover,
        })
    return rows


def build_publication_lock(
    project_id: str,
    take_id: str,
    *,
    pickup_take_id: str = DEFAULT_PICKUP_TAKE_ID,
    final_capture_target: str = "station_app",
) -> dict[str, Any]:
    pickup_plan = _optional_json(_project_root(project_id) / f"publication_pickup_plan_{take_id}.json")
    if not pickup_plan:
        pickup_plan = build_publication_pickup_plan(
            project_id,
            take_id,
            final_capture_target=final_capture_target,
        )
    audio = _has_audio_or_transcript(take_id)
    pickup_status = _pickup_receipt_status(pickup_take_id)
    source_identity = _source_identity_status(take_id, final_capture_target)
    pickup_review = _take_review(pickup_take_id)

    audio_blocked = not audio["publication_audio_ready"]
    source_blocked = source_identity["status"] == "blocked_as_public_app_identity"
    pickups_blocked = not pickup_status["all_required_green"]
    if audio_blocked and source_blocked:
        verdict = "publication_no_go_audio_and_source_identity"
    elif audio_blocked:
        verdict = "publication_no_go_audio"
    elif source_blocked:
        verdict = "publication_no_go_source_identity"
    elif pickups_blocked:
        verdict = "publication_no_go_missing_pickups"
    else:
        verdict = "publication_candidate"

    if source_blocked:
        required_visual_move = "record_app_full_spine_with_voiceover_or_crop_existing_bed_to_source_neutral"
    else:
        required_visual_move = "assemble_app_target_or_source_neutral_cut"
    if audio_blocked:
        required_audio_move = "record_or_attach_operator_voiceover_then_generate_transcript_and_caption_files"
    else:
        required_audio_move = "review_existing_audio_transcript_against_scene_claims"

    return {
        "schema": SCHEMA_PUBLICATION_LOCK,
        "project_id": project_id,
        "take_id": take_id,
        "pickup_take_id": pickup_take_id,
        "created_at": _now_iso(),
        "final_capture_target": final_capture_target,
        "overall_verdict": verdict,
        "source_identity": source_identity,
        "audio_gate": audio,
        "pickup_gate": pickup_status,
        "pickup_review_summary": {
            "overall_verdict": pickup_review.get("overall_verdict"),
            "remaining_publication_blockers": pickup_review.get("remaining_publication_blockers", []),
        },
        "voiceover_lock": {
            "status": "script_locked_audio_pending" if audio_blocked else "audio_available_review_required",
            "style": "direct thinking, high-signal pedagogy, no sales-demo cadence",
            "segments": _voiceover_segments_from_plan(pickup_plan),
        },
        "short_form_sequence": pickup_plan.get("short_form_sequence", []),
        "long_form_sequence": pickup_plan.get("long_form_sequence", []),
        "required_next_actions": [
            {
                "id": "audio.voiceover",
                "status": "blocking" if audio_blocked else "review",
                "action": required_audio_move,
            },
            {
                "id": "visual.source_identity",
                "status": "blocking" if source_blocked else "review",
                "action": required_visual_move,
            },
            {
                "id": "visual.pickups",
                "status": "satisfied" if not pickups_blocked else "blocking",
                "action": "reuse_green_app_pickup_receipts" if not pickups_blocked else "capture_missing_app_pickups",
            },
            {
                "id": "captions.transcript",
                "status": "blocked_by_voiceover" if audio_blocked else "required",
                "action": "generate transcript and captions from the actual audio, not from the script alone",
            },
        ],
        "cap_binding": {
            "cap_id": "cap_quick_station_app_pickup_visuals_ready_voiceov_c29cfc326e71",
            "status": "keep_open_until_audio_transcript_publication_review",
            "closure_condition": "audio track, transcript/captions, source-identity-safe visual cut, and final publication verdict exist",
        },
    }


def render_publication_lock_markdown(lock: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Publication Lock")
    lines.append("")
    lines.append(f"- Project: `{lock.get('project_id')}`")
    lines.append(f"- Base visual bed: `{lock.get('take_id')}`")
    lines.append(f"- App pickup take: `{lock.get('pickup_take_id')}`")
    lines.append(f"- Final capture target: `{lock.get('final_capture_target')}`")
    lines.append(f"- Verdict: `{lock.get('overall_verdict')}`")
    lines.append("")
    source = lock.get("source_identity") or {}
    lines.append("## Source Identity")
    lines.append("")
    lines.append(f"- Status: `{source.get('status')}`")
    lines.append(f"- Public use: `{source.get('public_use')}`")
    lines.append(f"- Safari/browser provenance detected: `{source.get('safari_or_browser_provenance_detected')}`")
    lines.append("")
    audio = lock.get("audio_gate") or {}
    lines.append("## Audio")
    lines.append("")
    lines.append(f"- Publication audio ready: `{audio.get('publication_audio_ready')}`")
    lines.append(f"- Transcript status: `{audio.get('transcript_status')}`")
    lines.append(f"- Transcript word count: `{audio.get('transcript_word_count')}`")
    lines.append(f"- Microphone present: `{audio.get('microphone_present')}`")
    lines.append("")
    pickups = lock.get("pickup_gate") or {}
    lines.append("## App Pickups")
    lines.append("")
    lines.append(f"- All required green: `{pickups.get('all_required_green')}`")
    for row in pickups.get("receipts", []) or []:
        lines.append(f"- `{row.get('id')}`: `{row.get('verdict')}` — `{row.get('recording')}`")
    lines.append("")
    lines.append("## Voiceover Lock")
    lines.append("")
    voice = lock.get("voiceover_lock") or {}
    lines.append(f"- Status: `{voice.get('status')}`")
    lines.append(f"- Style: {voice.get('style')}")
    lines.append("")
    for row in voice.get("segments", []) or []:
        lines.append(f"### {row.get('step_id')} — {row.get('surface')}")
        lines.append("")
        lines.append(row.get("voiceover") or "")
        lines.append("")
    lines.append("## Required Next Actions")
    lines.append("")
    for action in lock.get("required_next_actions", []) or []:
        lines.append(f"- `{action.get('id')}`: `{action.get('status')}` — {action.get('action')}")
    lines.append("")
    cap = lock.get("cap_binding") or {}
    lines.append("## CAP")
    lines.append("")
    lines.append(f"- `{cap.get('cap_id')}`: `{cap.get('status')}`")
    lines.append("")
    return "\n".join(lines)


def build_publication_lock_artifacts(
    project_id: str,
    take_id: str,
    *,
    pickup_take_id: str = DEFAULT_PICKUP_TAKE_ID,
    final_capture_target: str = "station_app",
) -> dict[str, Path]:
    project_root = _project_root(project_id)
    lock = build_publication_lock(
        project_id,
        take_id,
        pickup_take_id=pickup_take_id,
        final_capture_target=final_capture_target,
    )
    stem = f"publication_lock_{take_id}_{pickup_take_id}"
    json_path = project_root / f"{stem}.json"
    md_path = project_root / f"{stem}.md"
    _write_json(json_path, lock)
    md_path.write_text(render_publication_lock_markdown(lock), encoding="utf-8")
    return {"publication_lock": json_path, "publication_lock_markdown": md_path}


# ---------------------------------------------------------------------------
# Orchestration + CLI
# ---------------------------------------------------------------------------


def build_all(project_id: str, *, take_id: str | None = None) -> dict[str, Path]:
    project_root = _project_root(project_id)
    shoot_script = build_shoot_script(project_id)
    _write_json(project_root / "shoot_script.json", shoot_script)
    outputs: dict[str, Path] = {"shoot_script": project_root / "shoot_script.json"}

    if take_id:
        coverage = build_story_coverage_audit(project_id, take_id, shoot_script)
        _write_json(project_root / f"story_coverage_audit_{take_id}.json", coverage)
        outputs["story_coverage_audit"] = project_root / f"story_coverage_audit_{take_id}.json"

        intro = build_intro_montage_plan(project_id, take_id, coverage)
        _write_json(project_root / "intro_montage_plan.json", intro)
        outputs["intro_montage_plan"] = project_root / "intro_montage_plan.json"

        rough_cut = build_rough_cut_plan(project_id, take_id, coverage, intro, shoot_script)
        _write_json(project_root / "rough_cut_plan.json", rough_cut)
        outputs["rough_cut_plan"] = project_root / "rough_cut_plan.json"

        chapter_plan = build_chapter_plan(project_id, rough_cut_plan=rough_cut, shoot_script=shoot_script)
        _write_json(project_root / "chapter_plan.json", chapter_plan)
        outputs["chapter_plan"] = project_root / "chapter_plan.json"

        yt = build_youtube_package(
            project_id,
            shoot_script=shoot_script,
            chapter_plan=chapter_plan,
            take_id=take_id,
            coverage_audit=coverage,
        )
        _write_json(project_root / "youtube_package.json", yt)
        outputs["youtube_package"] = project_root / "youtube_package.json"
    else:
        chapter_plan = build_chapter_plan(project_id, shoot_script=shoot_script)
        _write_json(project_root / "chapter_plan.json", chapter_plan)
        outputs["chapter_plan"] = project_root / "chapter_plan.json"

    return outputs


def _emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, sort_keys=True, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def cmd_build_script(args: argparse.Namespace) -> int:
    payload = build_shoot_script(args.project_id)
    project_root = _project_root(args.project_id)
    _write_json(project_root / "shoot_script.json", payload)
    _emit({
        "project_id": args.project_id,
        "contents_beat_count": payload["contents_beat_count"],
        "per_view_script_count": payload["per_view_script_count"],
        "output": str((project_root / "shoot_script.json").relative_to(REPO_ROOT)),
    })
    return 0


def cmd_coverage_audit(args: argparse.Namespace) -> int:
    project_root = _project_root(args.project_id)
    shoot_path = project_root / "shoot_script.json"
    if not shoot_path.exists():
        _emit({"error": "shoot_script_missing", "hint": "run build-script first", "project_id": args.project_id})
        return 2
    shoot_script = _read_json(shoot_path)
    audit = build_story_coverage_audit(args.project_id, args.take_id, shoot_script)
    out_path = project_root / f"story_coverage_audit_{args.take_id}.json"
    _write_json(out_path, audit)
    _emit({
        "project_id": args.project_id,
        "take_id": args.take_id,
        "status": audit["status"],
        "covered_beats": audit["covered_beats"],
        "missed_beats": audit["missed_beats"],
        "coverage_percent": audit["coverage_percent"],
        "best_view_segment_count": len(audit["best_view_segments"]),
        "output": str(out_path.relative_to(REPO_ROOT)),
    })
    return 0 if audit["status"] == "pass" else (1 if audit["status"] == "warn" else 2)


def cmd_pickup_plan(args: argparse.Namespace) -> int:
    outputs = build_publication_pickup_plan_artifacts(
        args.project_id,
        args.take_id,
        pickup_file=args.pickup_file,
        final_capture_target=args.final_capture_target,
    )
    plan = _read_json(outputs["publication_pickup_plan"])
    _emit({
        "project_id": args.project_id,
        "take_id": args.take_id,
        "schema": plan["schema"],
        "state": plan["current_state"],
        "final_capture_target": plan["final_capture_target"],
        "pickup_count": len(plan.get("pickup_shots", []) or []),
        "outputs": {k: str(v.relative_to(REPO_ROOT)) for k, v in outputs.items()},
    })
    return 0


def cmd_publication_lock(args: argparse.Namespace) -> int:
    outputs = build_publication_lock_artifacts(
        args.project_id,
        args.take_id,
        pickup_take_id=args.pickup_take_id,
        final_capture_target=args.final_capture_target,
    )
    lock = _read_json(outputs["publication_lock"])
    _emit({
        "project_id": args.project_id,
        "take_id": args.take_id,
        "pickup_take_id": args.pickup_take_id,
        "schema": lock["schema"],
        "overall_verdict": lock["overall_verdict"],
        "final_capture_target": lock["final_capture_target"],
        "audio_ready": lock["audio_gate"]["publication_audio_ready"],
        "pickups_ready": lock["pickup_gate"]["all_required_green"],
        "source_identity_status": lock["source_identity"]["status"],
        "outputs": {k: str(v.relative_to(REPO_ROOT)) for k, v in outputs.items()},
    })
    return 0 if lock["overall_verdict"] == "publication_candidate" else 1


def cmd_all(args: argparse.Namespace) -> int:
    outputs = build_all(args.project_id, take_id=args.take_id)
    _emit({
        "project_id": args.project_id,
        "take_id": args.take_id,
        "outputs": {k: str(v.relative_to(REPO_ROOT)) for k, v in outputs.items()},
    })
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demo_take_story_package.py", description="Compile YouTube story package from planned itinerary + take packages.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("build-script", help="Build shoot_script.json from planning docs.")
    p1.add_argument("--project-id", required=True)
    p1.set_defaults(func=cmd_build_script)

    p2 = sub.add_parser("coverage-audit", help="Score a take against the shoot script.")
    p2.add_argument("--project-id", required=True)
    p2.add_argument("--take", dest="take_id", required=True)
    p2.set_defaults(func=cmd_coverage_audit)

    p_pickup = sub.add_parser("pickup-plan", help="Build publication pickup/voiceover plan from a reviewed take.")
    p_pickup.add_argument("--project-id", required=True)
    p_pickup.add_argument("--take", dest="take_id", required=True)
    p_pickup.add_argument("--pickup-file", default=DEFAULT_PICKUP_FILE)
    p_pickup.add_argument("--final-capture-target", default="station_app")
    p_pickup.set_defaults(func=cmd_pickup_plan)

    p_lock = sub.add_parser("publication-lock", help="Build publication voiceover/source-identity lock after app pickups.")
    p_lock.add_argument("--project-id", required=True)
    p_lock.add_argument("--take", dest="take_id", required=True)
    p_lock.add_argument("--pickup-take", dest="pickup_take_id", default=DEFAULT_PICKUP_TAKE_ID)
    p_lock.add_argument("--final-capture-target", default="station_app")
    p_lock.set_defaults(func=cmd_publication_lock)

    p3 = sub.add_parser("all", help="Build every artifact end-to-end.")
    p3.add_argument("--project-id", required=True)
    p3.add_argument("--take", dest="take_id", default=None)
    p3.set_defaults(func=cmd_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
