#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Mapping


DEVICE_RE = re.compile(r"^\s*\[[^\]]+\]\s+\[(\d+)\]\s+(.+)$")
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_TAKE_APP_ROOT = REPO_ROOT / "apps" / "demo-take-console"
RUN_MAP_PATH = REPO_ROOT / "docs" / "dissemination" / "recording_run_map_v0.json"
COMMON_FFPROBE_PATHS = [
    Path("/opt/homebrew/bin/ffprobe"),
    Path("/usr/local/bin/ffprobe"),
    Path("/Applications/Demo Take Console.app/Contents/Resources/ffprobe"),
]


def _backend_call(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Best-effort backend call. Returns {} when the backend is unreachable."""
    base = os.environ.get("DEMO_TAKE_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")
    url = f"{base}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=2.0) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return {}


def _http_get_json(url: str, timeout: float = 2.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return {}

DEFAULT_MARKER_PHRASES = [
    "new page",
    "new section",
    "next clip",
    "clip",
]
DEFAULT_SPEECH_BLOCK_PAUSE_SECONDS = 0.72
DEFAULT_SPEECH_BLOCK_MAX_SECONDS = 18.0
DEFAULT_SEMANTIC_SILENCE_MIN_SECONDS = 0.35
DEFAULT_SEMANTIC_SILENCE_MAX_SECONDS = 30.0
DEFAULT_TRANSCRIBE_MODEL = "openai_whisper-base"
DEFAULT_TRANSCRIBE_PROVIDER = "auto"
DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS = 180
DEFAULT_TRANSCRIBE_AUTO_DOWNLOAD_MODEL = True
TRANSCRIBE_PROVIDERS = {"auto", "whisperkit", "whisper_cpp"}
TRANSCRIPTION_AUDIO_CACHE_RELATIVE_PATH = "transcript/audio_for_transcribe.wav"
WHISPER_CPP_CACHE_RELATIVE_PATH = "transcript/whisper_cpp.json"
WHISPER_CPP_SRT_CACHE_RELATIVE_PATH = "transcript/whisper_cpp.srt"
MICROPHONE_TRACK_MISSING_TRANSCRIBE_FAILURE = "Microphone track missing on disk; cannot transcribe."
TAKE_OPERATION_LOCK_NAME = ".demo_take_operation.lock"
TAKE_EXCLUSIVE_OPERATIONS = {"finalize", "postprocess", "transcribe"}
WHISPER_CPP_MODEL_DIR = REPO_ROOT / "state" / "whisper"
WHISPER_CPP_MODEL_URL_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
EXTERNAL_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
DEFAULT_STORAGE_PROFILE = "efficient"
STORAGE_PROFILES = {"efficient", "source"}
DEFAULT_RECORDING_QUALITY = "efficient"
RECORDING_QUALITY_PROFILES = {"efficient", "source"}
EFFICIENT_VIDEO_MAX_WIDTH = 1280
EFFICIENT_VIDEO_MAX_HEIGHT = 720
EFFICIENT_SCREEN_BITRATE = "3500k"
EFFICIENT_WEBCAM_BITRATE = "2000k"
EFFICIENT_AUDIO_BITRATE = "160k"
DEFAULT_REVIEW_AUDIO_BITRATE = "64k"
DEFAULT_REVIEW_AUDIO_SAMPLE_RATE = "44100"
RECORDING_QUALITY_SETTINGS = {
    "efficient": {
        "screen_bitrate": EFFICIENT_SCREEN_BITRATE,
        "webcam_bitrate": EFFICIENT_WEBCAM_BITRATE,
        "audio_bitrate": EFFICIENT_AUDIO_BITRATE,
        "audio_codec": "aac",
        "audio_extension": ".m4a",
        "audio_sample_rate": "48000",
        "scale_filter": (
            "scale="
            f"w='if(gt(iw/ih,{EFFICIENT_VIDEO_MAX_WIDTH}/{EFFICIENT_VIDEO_MAX_HEIGHT}),"
            f"min({EFFICIENT_VIDEO_MAX_WIDTH},iw),-2)':"
            f"h='if(gt(iw/ih,{EFFICIENT_VIDEO_MAX_WIDTH}/{EFFICIENT_VIDEO_MAX_HEIGHT}),"
            f"-2,min({EFFICIENT_VIDEO_MAX_HEIGHT},ih))'"
        ),
    },
    "source": {
        "screen_bitrate": "24000k",
        "webcam_bitrate": "8000k",
        "audio_bitrate": "256k",
        "audio_codec": "pcm_s24le",
        "audio_extension": ".wav",
        "audio_sample_rate": "48000",
        "scale_filter": None,
    },
}
DEFAULT_FRAME_THUMBNAIL_WIDTH = 1280
DEFAULT_FRAME_JPEG_QUALITY = 5
EXPORTS_RELATIVE_ROOT = Path("state") / "dissemination" / "demo_exports"
DEFAULT_CLOUD_ARCHIVE_REMOTE = "memeister_drive:aiw-cold-spillway/demo_takes"
CLOUD_ARCHIVE_LOCAL_RETENTIONS = {"full", "proxy", "review"}
DEFAULT_CLOUD_ARCHIVE_AFTER_STOP = True
# New captures are already efficient 720p30. The default retention keeps the
# local rough cut + semantic proxy, not a second proxy video.
DEFAULT_CLOUD_ARCHIVE_LOCAL_RETENTION = "review"
LOCAL_STORAGE_HARD_FLOOR_BYTES = 10 * 1024 * 1024 * 1024
LOCAL_STORAGE_SOFT_FLOOR_BYTES = 35 * 1024 * 1024 * 1024
LOCAL_STORAGE_TARGET_FREE_BYTES = 50 * 1024 * 1024 * 1024
STORAGE_GOVERNOR_STATES = {
    "cloud_verified_review_local",
    "cloud_verified_proxy_local",
    "cloud_pending_raw_local",
    "cloud_failed_raw_local_blocked",
    "manual_source_retention",
}
RESTORE_DRILL_STATUSES = {"pass", "warn", "fail", "missing"}
RESTORE_DRILL_RECEIPT_RELATIVE_PATH = "render/restore_drill_receipt.json"
SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH = "render/source_requirement_lease.json"
SOURCE_REQUIREMENT_PRUNE_BLOCKING_STATUSES = {"active", "blocked"}
GENERATED_MEDIA_RECEIPT_SCHEMA = "demo_take_generated_media_receipt_v0"
GENERATED_MEDIA_COMMAND_VERSION = "2026-06-26.generated_media_build_v1"
GENERATED_MEDIA_RECEIPTS_DIR = Path("render") / "generated_media_receipts"
GENERATED_MEDIA_ENVELOPE_SAFETY_FACTOR = 3.0
GENERATED_MEDIA_ENVELOPE_MIN_OVERHEAD_BYTES = 2 * 1024 * 1024
GENERATED_CACHE_EVICTABLE_PREFIXES = (
    "tracks/spliced/parts/",
    "tracks/spliced/placeholders/",
    "frames/phrase_cards/",
)
GENERATED_SPLICE_CACHE_EVICTABLE_PREFIXES = (
    "tracks/spliced/parts/",
    "tracks/spliced/placeholders/",
)
GENERATED_PHRASE_FRAME_CACHE_PREFIX = "frames/phrase_cards/"
GENERATED_RENDER_PARTS_CACHE_SUFFIX = "_parts"
GENERATED_CACHE_EVICTION_RECEIPT_RELATIVE_PATH = "render/generated_cache_eviction_receipt.json"
GENERATED_CACHE_EVICTION_RECEIPT_ROW_LIMIT = 200
LOCAL_RETENTION_MINIMIZE_RECEIPT_RELATIVE_PATH = "render/local_retention_minimize_receipt.json"
CALIBRATION_RECEIPT_SCHEMA = "demo_take_calibration_receipt_v0"
CALIBRATION_COMMAND_VERSION = "2026-06-26.byte_slope_gate_v1"
CALIBRATION_RECEIPT_RELATIVE_PATH = "render/calibration_receipt.json"
CALIBRATION_ENVELOPE_FACTOR = 3.0
CALIBRATION_FILE_OVERHEAD_BYTES = 1024 * 1024
CALIBRATION_MIN_DURATION_SECONDS = 1.0
CALIBRATION_SOURCE_ROLES = {"screen", "webcam", "microphone"}
CALIBRATION_VIDEO_CODECS = {"h264"}
CALIBRATION_AUDIO_CODECS = {"aac"}
TIMELINE_SYNC_RECEIPT_SCHEMA = "demo_take_timeline_sync_receipt_v0"
TIMELINE_SYNC_COMMAND_VERSION = "2026-06-26.timeline_sync_gate_v1"
TIMELINE_SYNC_RECEIPT_RELATIVE_PATH = "render/timeline_sync_receipt.json"
TIMELINE_SYNC_FRAME_BUDGET_MS = 1000.0 / 30.0
TIMELINE_SYNC_WARN_THRESHOLD_MS = 50.0
TIMELINE_SYNC_FAIL_THRESHOLD_MS = 125.0
TIMELINE_SYNC_ROLES = {"screen", "webcam", "microphone"}
TIMELINE_SYNC_PCM_AUDIO_BITRATE = "2304k"
# Observed source-quality captures land above the configured target bitrates
# (encoder overshoot + sidecar artifacts), so spool projections carry a margin.
SPOOL_ESTIMATE_SAFETY_FACTOR = 1.5
PCM_S24LE_BYTES_PER_SECOND = 48000 * 3 * 2  # 48kHz, 24-bit, stereo
# Archive transport: Drive throughput is request-shaped, so high-file-count
# packages upload the sidecar tail as ONE indexed zip object while media files
# stay direct at their native relative paths (hydrate/restore compatibility).
# Non-solid zip deliberately chosen over solid 7z: cloud-readable member access.
ARCHIVE_TRANSPORT_MODES = {"auto", "file_tree", "sidecar_bundle"}
ARCHIVE_TRANSPORT_FILE_COUNT_THRESHOLD = 64
ARCHIVE_TRANSPORT_SMALL_FILE_MAX_BYTES = 1024 * 1024
ARCHIVE_TRANSPORT_SMALL_FILE_COUNT_THRESHOLD = 32
ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH = "package/sidecars.zip"
ARCHIVE_DIRECT_ROLES = {"source_media", "local_review_proxy", "local_review_video", "local_review_audio"}
RAW_MEDIA_SUFFIXES = {".mp4", ".mov", ".m4v", ".m4a", ".wav", ".aac"}
REVIEW_MEDIA_SUFFIXES = RAW_MEDIA_SUFFIXES | {".mp3"}
TITLE_SLUG_RE = re.compile(r"[^a-z0-9]+")
DEMO_TAKE_INDEX_SCRIPT = REPO_ROOT / "tools" / "meta" / "dissemination" / "demo_take_index.py"
ATTENTION_TARGET_POLICIES = {
    "station_view": {
        "public_safe_default": True,
        "post_edit_policy": "public_safe",
        "reason": "station_route_visible_on_recorded_display",
    },
    "agent_trace": {
        "public_safe_default": True,
        "post_edit_policy": "review_for_provider_payloads",
        "reason": "agent_trace_surface",
    },
    "system_bar": {
        "public_safe_default": True,
        "post_edit_policy": "review_for_operator_controls",
        "reason": "system_bar_surface",
    },
    "ai_work_surface": {
        "public_safe_default": True,
        "post_edit_policy": "review_for_private_state",
        "reason": "ai_work_surface",
    },
    "demo_take_console": {
        "public_safe_default": True,
        "post_edit_policy": "public_safe",
        "reason": "demo_take_console",
    },
    "microcosm_site": {
        "public_safe_default": True,
        "post_edit_policy": "public_safe",
        "reason": "microcosm_public_site",
    },
    "obsidian_teleprompter": {
        "public_safe_default": False,
        "post_edit_policy": "review_or_cut_unless_intentional",
        "reason": "obsidian_or_teleprompter_window",
    },
    "browser_generic": {
        "public_safe_default": False,
        "post_edit_policy": "review_before_public",
        "reason": "generic_browser_window",
    },
    "terminal": {
        "public_safe_default": False,
        "post_edit_policy": "review_or_cut_unless_intentional",
        "reason": "terminal_window",
    },
    "finder": {
        "public_safe_default": False,
        "post_edit_policy": "review_before_public",
        "reason": "finder_window",
    },
    "application_window": {
        "public_safe_default": False,
        "post_edit_policy": "review_before_public",
        "reason": "generic_application_window",
    },
    "application": {
        "public_safe_default": False,
        "post_edit_policy": "review_before_public",
        "reason": "frontmost_application_only",
    },
    "private_or_review": {
        "public_safe_default": False,
        "post_edit_policy": "review_or_cut",
        "reason": "explicit_private_or_review_signal",
    },
    "unknown": {
        "public_safe_default": False,
        "post_edit_policy": "review_before_public",
        "reason": "unknown_attention_target",
    },
}
BROWSER_BUNDLE_HINTS = ("chrome", "chromium", "safari", "firefox", "arc", "brave", "edge")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def clean_take_title(value: Any, *, fallback: str | None = None) -> str | None:
    text = str(value or "").strip()
    if not text and fallback is not None:
        text = str(fallback or "").strip()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)[:120]


def take_title_slug(value: Any) -> str | None:
    title = clean_take_title(value)
    if not title:
        return None
    slug = TITLE_SLUG_RE.sub("-", title.lower()).strip("-")
    return slug[:48].strip("-") or None


def clean_recipient_id(value: Any, *, fallback: Any = None) -> str | None:
    text = str(value or fallback or "").strip().lower()
    if not text:
        return None
    slug = TITLE_SLUG_RE.sub("-", text).strip("-")
    return slug[:64].strip("-") or None


def recipient_metadata(config: Mapping[str, Any]) -> dict[str, Any] | None:
    recipient_id = clean_recipient_id(config.get("recipient_id"), fallback=config.get("recipient_name"))
    recipient_name = clean_take_title(config.get("recipient_name"))
    if not recipient_id and not recipient_name:
        return None
    return {
        "recipient_id": recipient_id or clean_recipient_id(recipient_name),
        "recipient_name": recipient_name,
        "recipient_slug": recipient_id or clean_recipient_id(recipient_name),
    }


def take_output_root(repo_root: Path, config: Mapping[str, Any]) -> Path:
    configured = str(config.get("local_archive_root") or "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else repo_root / path
    return repo_root / "state" / "dissemination" / "demo_takes"


def _config_int(config: dict[str, Any], key: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(config.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _bool_value(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
    return default


def storage_profile(config: dict[str, Any]) -> str:
    profile = str(config.get("storage_profile", DEFAULT_STORAGE_PROFILE)).strip().lower()
    return profile if profile in STORAGE_PROFILES else DEFAULT_STORAGE_PROFILE


def recording_quality(config: dict[str, Any]) -> str:
    quality = str(config.get("recording_quality", DEFAULT_RECORDING_QUALITY)).strip().lower()
    if quality == "source" and _bool_value(config.get("allow_source_recording_quality"), False):
        return "source"
    return quality if quality == DEFAULT_RECORDING_QUALITY else DEFAULT_RECORDING_QUALITY


def recording_quality_settings(config: dict[str, Any]) -> dict[str, Any]:
    return RECORDING_QUALITY_SETTINGS[recording_quality(config)]


def efficient_video_filter(config: Mapping[str, Any] | None = None) -> str:
    settings = recording_quality_settings(dict(config or {"recording_quality": "efficient"}))
    return str(settings.get("scale_filter") or RECORDING_QUALITY_SETTINGS["efficient"]["scale_filter"])


def selected_capture_screens(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    screens = config.get("screens")
    if not isinstance(screens, list):
        return []
    return [dict(screen) for screen in screens if isinstance(screen, Mapping)][:1]


def config_bool(config: Mapping[str, Any], key: str, default: bool = False) -> bool:
    return _bool_value(config.get(key, default), default)


def cloud_archive_remote(config: Mapping[str, Any]) -> str:
    remote = str(
        config.get("cloud_archive_remote")
        or os.environ.get("DEMO_TAKE_CLOUD_ARCHIVE_REMOTE")
        or DEFAULT_CLOUD_ARCHIVE_REMOTE
    ).strip()
    return remote or DEFAULT_CLOUD_ARCHIVE_REMOTE


def cloud_archive_local_retention(config: Mapping[str, Any]) -> str:
    retention = str(config.get("cloud_archive_local_retention") or DEFAULT_CLOUD_ARCHIVE_LOCAL_RETENTION).strip().lower()
    return retention if retention in CLOUD_ARCHIVE_LOCAL_RETENTIONS else DEFAULT_CLOUD_ARCHIVE_LOCAL_RETENTION


def cloud_archive_after_stop(config: Mapping[str, Any]) -> bool:
    # Real recordings default to cold custody after stop. Synthetic/fake
    # fixtures stay local unless a test asks for archive behavior explicitly.
    capture_backend = str(config.get("capture_backend") or "").strip().lower()
    default = False if capture_backend == "fake" else DEFAULT_CLOUD_ARCHIVE_AFTER_STOP
    return config_bool(config, "cloud_archive_after_stop", default)


def cloud_archive_preflight(config: Mapping[str, Any], *, timeout: float = 20.0) -> dict[str, Any]:
    remote_root = cloud_archive_remote(config)
    if not cloud_archive_after_stop(config):
        return {
            "schema": "demo_take_cloud_archive_preflight_v0",
            "status": "skipped",
            "reason": "cloud_archive_after_stop_false",
            "remote": remote_root,
        }

    rclone = os.environ.get("DEMO_TAKE_RCLONE") or shutil.which("rclone")
    if not rclone:
        return {
            "schema": "demo_take_cloud_archive_preflight_v0",
            "status": "fail",
            "remote": remote_root,
            "known_failures": ["rclone executable not found"],
        }

    probe = _run_rclone([str(rclone), "lsf", remote_root, "--max-depth", "1"], timeout=timeout)
    compact_probe = {
        "status": probe.get("status"),
        "exit_code": probe.get("exit_code"),
        "stderr_tail": probe.get("stderr_tail", "") if probe.get("status") != "pass" else "",
    }
    if probe.get("status") != "pass":
        return {
            "schema": "demo_take_cloud_archive_preflight_v0",
            "status": "fail",
            "remote": remote_root,
            "rclone_path": str(rclone),
            "probe": compact_probe,
            "known_failures": ["configured cloud archive remote is not reachable"],
        }
    return {
        "schema": "demo_take_cloud_archive_preflight_v0",
        "status": "pass",
        "remote": remote_root,
        "rclone_path": str(rclone),
        "probe": compact_probe,
    }


def _bitrate_bytes_per_second(value: Any) -> float:
    text = str(value or "").strip().lower()
    if not text:
        return 0.0
    multiplier = 1.0
    if text.endswith("k"):
        multiplier, text = 1000.0, text[:-1]
    elif text.endswith("m"):
        multiplier, text = 1_000_000.0, text[:-1]
    try:
        return float(text) * multiplier / 8.0
    except ValueError:
        return 0.0


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _calibration_budget_bytes_per_second(config: Mapping[str, Any], role: str) -> tuple[float, str | None]:
    settings = recording_quality_settings(dict(config))
    if role == "screen":
        bitrate = str(settings.get("screen_bitrate") or "")
        return _bitrate_bytes_per_second(bitrate), bitrate
    if role == "webcam":
        bitrate = str(settings.get("webcam_bitrate") or "")
        return _bitrate_bytes_per_second(bitrate), bitrate
    if role == "microphone":
        if settings.get("audio_codec") == "pcm_s24le":
            return float(PCM_S24LE_BYTES_PER_SECOND), "pcm_s24le"
        bitrate = str(settings.get("audio_bitrate") or "")
        return _bitrate_bytes_per_second(bitrate), bitrate
    return 0.0, None


def estimated_spool_bytes_per_second(config: Mapping[str, Any]) -> float:
    settings = recording_quality_settings(dict(config))
    screen_count = max(1, len(selected_capture_screens(config)))
    total = _bitrate_bytes_per_second(settings.get("screen_bitrate")) * screen_count
    if config.get("webcam"):
        total += _bitrate_bytes_per_second(settings.get("webcam_bitrate"))
    if config.get("microphone"):
        if settings.get("audio_codec") == "pcm_s24le":
            total += PCM_S24LE_BYTES_PER_SECOND
        else:
            total += _bitrate_bytes_per_second(settings.get("audio_bitrate"))
    return total * SPOOL_ESTIMATE_SAFETY_FACTOR


def storage_governor_preflight(config: Mapping[str, Any], *, spool_root: Path) -> dict[str, Any]:
    """Active-spool budget check before a take root is created.

    Fail-closed only below the hard disk floor; the soft floor warns so the
    operator can still record deliberately on a tight disk.
    """
    spool_root = spool_root.expanduser()
    usage_root = spool_root
    while not usage_root.exists() and usage_root.parent != usage_root:
        usage_root = usage_root.parent
    try:
        free_bytes: int | None = shutil.disk_usage(usage_root).free
    except OSError:
        free_bytes = None
    bytes_per_second = estimated_spool_bytes_per_second(config)
    payload: dict[str, Any] = {
        "schema": "demo_take_storage_governor_preflight_v0",
        "spool_role": "active_capture_output_root",
        "spool_root": str(spool_root),
        "spool_volume_root": str(usage_root),
        "free_bytes": free_bytes,
        "hard_floor_bytes": LOCAL_STORAGE_HARD_FLOOR_BYTES,
        "soft_floor_bytes": LOCAL_STORAGE_SOFT_FLOOR_BYTES,
        "estimated_spool_bytes_per_second": int(bytes_per_second),
        "estimated_spool_bytes_per_minute": int(bytes_per_second * 60),
    }
    if free_bytes is None:
        payload["status"] = "warn"
        payload["operator_line"] = "Active spool budget unknown: free disk space could not be read."
        return payload
    budget_line = f"Active spool budget: about {human_bytes(int(bytes_per_second * 60))}/minute at this quality"
    if bytes_per_second > 0:
        minutes_to_hard_floor = max(0.0, (free_bytes - LOCAL_STORAGE_HARD_FLOOR_BYTES) / bytes_per_second / 60.0)
        payload["minutes_until_hard_floor"] = round(minutes_to_hard_floor, 1)
        budget_line += f"; roughly {_human_minutes(minutes_to_hard_floor)} of recording before the local disk floor"
    if free_bytes < LOCAL_STORAGE_HARD_FLOOR_BYTES:
        payload["status"] = "fail"
        payload["known_failures"] = [
            f"free disk {human_bytes(free_bytes)} is below the {human_bytes(LOCAL_STORAGE_HARD_FLOOR_BYTES)} hard floor for a new active spool"
        ]
        payload["operator_line"] = (
            f"Recording blocked: only {human_bytes(free_bytes)} free on the active spool volume, "
            f"below the {human_bytes(LOCAL_STORAGE_HARD_FLOOR_BYTES)} floor. Reclaim space by "
            "archiving cold takes to the cloud and evicting them locally: "
            "`repo-python apps/demo-take-console/support/demo_take_capture.py reclaim-space`."
        )
        return payload
    payload["status"] = "warn" if free_bytes < LOCAL_STORAGE_SOFT_FLOOR_BYTES else "pass"
    payload["operator_line"] = budget_line + f" ({human_bytes(free_bytes)} free)."
    return payload


def _human_minutes(minutes: float) -> str:
    if minutes >= 120:
        return f"{minutes / 60.0:.1f} hours"
    return f"{int(round(minutes))} minutes"


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_bounds(value: Any) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    aliases = {
        "x": ("x", "minX", "left"),
        "y": ("y", "minY", "top"),
        "width": ("width", "w"),
        "height": ("height", "h"),
    }
    normalized: dict[str, float] = {}
    for key, names in aliases.items():
        found = None
        for name in names:
            if name in value:
                found = _safe_float(value.get(name))
                break
        if found is None:
            return None
        normalized[key] = round(found, 3)
    return normalized


def _capture_target_from_config(config: dict[str, Any]) -> dict[str, Any] | None:
    existing = config.get("capture_target")
    if isinstance(existing, dict):
        return existing
    screens = selected_capture_screens(config)
    if not screens:
        return None

    displays: list[dict[str, Any]] = []
    for screen in screens:
        if not isinstance(screen, Mapping):
            continue
        display_payload = screen.get("display") if isinstance(screen.get("display"), Mapping) else {}
        bounds = (
            _normalize_bounds(screen.get("display_bounds"))
            or _normalize_bounds(screen.get("bounds"))
            or _normalize_bounds(display_payload.get("bounds"))
        )
        display_id = (
            screen.get("display_id")
            or display_payload.get("display_id")
            or screen.get("id")
            or screen.get("index")
        )
        display = {
            "kind": "display",
            "display_id": str(display_id) if display_id is not None else None,
            "display_name": screen.get("display_name") or display_payload.get("name") or screen.get("name"),
            "ffmpeg_screen_index": screen.get("index"),
            "bounds": bounds,
            "scale_factor": _safe_float(screen.get("scale_factor") or display_payload.get("scale_factor")),
            "mapping_confidence": screen.get("mapping_confidence") or display_payload.get("mapping_confidence"),
        }
        displays.append({key: value for key, value in display.items() if value is not None})
    if not displays:
        return None

    target_id = (
        f"display:{displays[0].get('display_id')}"
        if len(displays) == 1 and displays[0].get("display_id") is not None
        else "display_set:" + ",".join(str(display.get("display_id") or display.get("ffmpeg_screen_index")) for display in displays)
    )
    payload: dict[str, Any] = {
        "schema": "demo_take_capture_target_v0",
        "kind": "display" if len(displays) == 1 else "display_set",
        "capture_target_id": target_id,
        "display_count": len(displays),
        "displays": displays,
        "source": "recorder_config",
    }
    if len(displays) == 1:
        payload.update({
            "display_id": displays[0].get("display_id"),
            "display_name": displays[0].get("display_name"),
            "ffmpeg_screen_index": displays[0].get("ffmpeg_screen_index"),
            "bounds": displays[0].get("bounds"),
            "scale_factor": displays[0].get("scale_factor"),
            "mapping_confidence": displays[0].get("mapping_confidence"),
        })
    return {key: value for key, value in payload.items() if value is not None}


def frame_thumbnail_filter(config: dict[str, Any], interval: int | None = None) -> str:
    if storage_profile(config) == "source":
        filters = []
        if interval is not None:
            filters.append(f"fps=1/{max(1, int(interval))}")
        filters.append("format=yuvj420p")
        return ",".join(filters)

    width = _config_int(
        config,
        "frame_thumbnail_width",
        DEFAULT_FRAME_THUMBNAIL_WIDTH,
        minimum=320,
        maximum=2560,
    )
    filters = []
    if interval is not None:
        filters.append(f"fps=1/{max(1, int(interval))}")
    filters.append(f"scale=w='min({width},iw)':h=-2")
    filters.append("format=yuvj420p")
    return ",".join(filters)


def frame_jpeg_quality(config: dict[str, Any]) -> str:
    default = 3 if storage_profile(config) == "source" else DEFAULT_FRAME_JPEG_QUALITY
    return str(_config_int(config, "frame_jpeg_quality", default, minimum=2, maximum=12))


def files_are_same(left: Path, right: Path) -> bool:
    try:
        return left.exists() and right.exists() and left.samefile(right)
    except OSError:
        return False


def replace_with_hardlink(target: Path, source: Path) -> bool:
    """Replace target with a hardlink to source without touching source bytes."""
    if files_are_same(target, source):
        return True
    if not source.exists():
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = secrets.token_hex(4)
    tmp_link = target.with_name(f".{target.name}.link_tmp_{suffix}")
    backup = target.with_name(f".{target.name}.pre_compact_{suffix}")
    try:
        os.link(source, tmp_link)
        if target.exists():
            target.rename(backup)
        os.replace(tmp_link, target)
        if backup.exists():
            backup.unlink()
        return files_are_same(target, source)
    except OSError:
        try:
            if tmp_link.exists():
                tmp_link.unlink()
        except OSError:
            pass
        try:
            if backup.exists() and not target.exists():
                backup.rename(target)
        except OSError:
            pass
        return False


def directory_size_bytes(root: Path, *, physical: bool) -> int:
    total = 0
    seen: set[tuple[int, int]] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if physical:
            key = (stat.st_dev, stat.st_ino)
            if key in seen:
                continue
            seen.add(key)
        total += stat.st_size
    return total


def disk_usage_probe_root(path: Path) -> Path:
    probe = path.expanduser()
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    return probe


def human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(0, value))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024


def unique_take_root(repo_root: Path, *, prefix: str, title: Any = None,
                     config: Mapping[str, Any] | None = None) -> tuple[str, Path]:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = take_title_slug(title)
    base_id = f"{prefix}_{stamp}" + (f"_{slug}" if slug else "")
    config = config or {}
    takes_root = take_output_root(repo_root, config)
    recipient = recipient_metadata(config)
    if recipient and config.get("group_by_recipient", True):
        takes_root = takes_root / "recipients" / str(recipient["recipient_slug"])
    for index in range(100):
        take_id = base_id if index == 0 else f"{base_id}_{index:02d}"
        root = takes_root / take_id
        if not root.exists():
            return take_id, root
    raise RuntimeError(f"could not allocate unique take package id for {base_id}")


def apply_title_metadata(payload: dict[str, Any], title: Any) -> dict[str, Any]:
    cleaned = clean_take_title(title)
    payload["title"] = cleaned
    payload["take_title"] = cleaned
    payload["take_slug"] = take_title_slug(cleaned)
    return payload


def transcribe_binary_candidates() -> list[Path]:
    return [
        DEMO_TAKE_APP_ROOT / "dist" / "demo-take-transcribe",
        DEMO_TAKE_APP_ROOT / "dist" / "Demo Take Console.app" / "Contents" / "Resources" / "demo-take-transcribe",
        Path("/Applications/Demo Take Console.app/Contents/Resources/demo-take-transcribe"),
        DEMO_TAKE_APP_ROOT / ".build" / "debug" / "demo-take-transcribe",
        DEMO_TAKE_APP_ROOT / ".build" / "release" / "demo-take-transcribe",
        DEMO_TAKE_APP_ROOT / ".build" / "arm64-apple-macosx" / "debug" / "demo-take-transcribe",
        DEMO_TAKE_APP_ROOT / ".build" / "arm64-apple-macosx" / "release" / "demo-take-transcribe",
    ]


def find_transcribe_binary() -> Path | None:
    for candidate in transcribe_binary_candidates():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def whisper_cpp_binary_candidates() -> list[Path]:
    return [
        Path("/opt/homebrew/bin/whisper-cli"),
        Path("/usr/local/bin/whisper-cli"),
        Path("/opt/homebrew/bin/whisper-cpp"),
        Path("/usr/local/bin/whisper-cpp"),
        DEMO_TAKE_APP_ROOT / "dist" / "whisper-cli",
        DEMO_TAKE_APP_ROOT / "dist" / "whisper-cpp",
        REPO_ROOT / "annexes" / "whisper.cpp" / "repo" / "build" / "bin" / "whisper-cli",
    ]


def find_whisper_cpp_binary(config: dict[str, Any] | None = None) -> Path | None:
    override = (config or {}).get("whisper_cpp_binary") or os.environ.get("WHISPER_CPP_BINARY")
    if override:
        candidate = Path(str(override)).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    for name in ["whisper-cli", "whisper-cpp"]:
        found = shutil.which(name)
        if found:
            return Path(found)
    for candidate in whisper_cpp_binary_candidates():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _whisper_cpp_model_names(model: str, language: str | None) -> list[str]:
    normalized = model.strip()
    if normalized.startswith("openai_whisper-"):
        normalized = normalized.removeprefix("openai_whisper-")
    normalized = normalized.replace("_", "-")
    if normalized.startswith("ggml-"):
        normalized = normalized.removeprefix("ggml-")
    names: list[str] = []
    if normalized.endswith(".bin"):
        names.append(normalized)
    else:
        prefer_english = language == "en"
        if prefer_english and not normalized.endswith(".en"):
            names.append(f"ggml-{normalized}.en.bin")
        names.append(f"ggml-{normalized}.bin")
        if not prefer_english and not normalized.endswith(".en"):
            names.append(f"ggml-{normalized}.en.bin")
        if not normalized.startswith("ggml-"):
            names.append(f"{normalized}.bin")
    return list(dict.fromkeys(names))


def default_whisper_cpp_model_path(
    model: str = DEFAULT_TRANSCRIBE_MODEL,
    language: str | None = "en",
    model_dir: Path | None = None,
) -> Path:
    directory = model_dir or WHISPER_CPP_MODEL_DIR
    return directory / _whisper_cpp_model_names(model, language)[0]


def find_whisper_cpp_model(config: dict[str, Any], model: str, language: str | None) -> Path | None:
    override = config.get("whisper_cpp_model") or os.environ.get("WHISPER_CPP_MODEL")
    if override:
        candidate = Path(str(override)).expanduser()
        if candidate.is_file():
            return candidate

    raw_model = Path(str(model)).expanduser()
    if raw_model.is_file():
        return raw_model

    search_dirs = [
        REPO_ROOT / "state" / "whisper",
        REPO_ROOT / "state" / "whisper" / "models",
        REPO_ROOT / "state" / "dissemination" / "whisper",
        REPO_ROOT / "annexes" / "whisper.cpp" / "repo" / "models",
        Path.home() / "Library" / "Application Support" / "whisper.cpp" / "models",
    ]
    for directory in search_dirs:
        for name in _whisper_cpp_model_names(model, language):
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def _run_logged(command: list[str], log_path: Path, *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        log.write(("\n$ " + " ".join(command) + "\n").encode("utf-8"))
        return subprocess.run(
            command,
            stdout=log,
            stderr=log,
            text=True,
            check=False,
            timeout=timeout,
        )


def _download_url_to_file(url: str, target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_name(target.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "ai-workflow-demo-take/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, temp_target.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    temp_target.replace(target)
    return {
        "url": url,
        "target": str(target),
        "bytes": target.stat().st_size,
    }


def setup_whisper_cpp(
    *,
    install_brew: bool = False,
    download_model: bool = False,
    model: str = DEFAULT_TRANSCRIBE_MODEL,
    language: str | None = "en",
    model_dir: Path | None = None,
    force_model: bool = False,
) -> dict[str, Any]:
    model_root = model_dir or WHISPER_CPP_MODEL_DIR
    logs_dir = WHISPER_CPP_MODEL_DIR / "logs"
    actions: list[dict[str, Any]] = []
    binary = find_whisper_cpp_binary({})
    if not binary and install_brew:
        brew = shutil.which("brew")
        if not brew:
            actions.append({"id": "brew_install", "status": "skipped", "reason": "brew_missing"})
        else:
            log_path = logs_dir / "brew_install_whisper_cpp.log"
            proc = _run_logged([brew, "install", "whisper-cpp"], log_path)
            actions.append({
                "id": "brew_install",
                "status": "pass" if proc.returncode == 0 else "fail",
                "exit_code": proc.returncode,
                "log": str(log_path),
            })
            binary = find_whisper_cpp_binary({})

    existing_model = None if force_model else find_whisper_cpp_model({}, model, language)
    target_model = default_whisper_cpp_model_path(model, language, model_root)
    model_path = existing_model
    if not model_path and target_model.is_file() and not force_model:
        model_path = target_model
    if (not model_path or force_model) and download_model:
        filename = target_model.name
        url = f"{WHISPER_CPP_MODEL_URL_BASE}/{filename}"
        try:
            download = _download_url_to_file(url, target_model)
        except Exception as exc:
            actions.append({
                "id": "download_model",
                "status": "fail",
                "url": url,
                "target": str(target_model),
                "error": str(exc),
            })
        else:
            model_path = target_model
            actions.append({"id": "download_model", "status": "pass", **download})
    elif model_path:
        actions.append({
            "id": "model_present",
            "status": "pass",
            "path": str(model_path),
            "bytes": model_path.stat().st_size,
        })
    else:
        actions.append({
            "id": "download_model",
            "status": "skipped",
            "reason": "download_model_false",
            "target": str(target_model),
        })

    ready = bool(binary and model_path and model_path.is_file())
    payload = {
        "schema": "demo_take_whisper_cpp_setup_v0",
        "created_at": now_iso(),
        "status": "ready" if ready else "unavailable",
        "provider": "whisper_cpp",
        "binary": str(binary) if binary else None,
        "model": model,
        "language": language,
        "model_path": str(model_path) if model_path else None,
        "default_model_path": str(target_model),
        "actions": actions,
        "next_action": None if ready else (
            "Run setup-transcription with --install-brew --download-model, or pass --whisper-cpp-model to transcribe."
        ),
    }
    receipt_path = WHISPER_CPP_MODEL_DIR / "whisper_cpp_setup_receipt.json"
    write_json(receipt_path, payload)
    payload["receipt_path"] = str(receipt_path)
    return payload


def run_ffmpeg_devices(ffmpeg: str) -> dict[str, Any]:
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    video: list[dict[str, Any]] = []
    audio: list[dict[str, Any]] = []
    current: str | None = None
    for line in proc.stdout.splitlines():
        if "AVFoundation video devices" in line:
            current = "video"
            continue
        if "AVFoundation audio devices" in line:
            current = "audio"
            continue
        match = DEVICE_RE.match(line)
        if not match or current is None:
            continue
        index = int(match.group(1))
        name = match.group(2).strip()
        row = {
            "id": f"{current}-{index}-{name}",
            "index": index,
            "name": name,
            "kind": current,
        }
        if current == "video":
            video.append(row)
        else:
            audio.append(row)
    return {"videoDevices": video, "audioDevices": audio, "raw_status": proc.returncode}


def _coerce_device_index(device: Mapping[str, Any], *, role: str) -> int:
    try:
        return int(device.get("index"))
    except (TypeError, ValueError):
        raise ValueError(f"{role} device is missing a valid AVFoundation index")


def _device_identity_fields(device: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    unique_id = str(device.get("unique_id") or "").strip()
    if unique_id:
        payload["device_unique_id"] = unique_id
    return payload


def _is_screen_device(device: Mapping[str, Any]) -> bool:
    name = str(device.get("name") or "").strip().lower()
    return name.startswith("capture screen") or name.startswith("screen capture")


def _live_device_by_index(devices: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    return next((device for device in devices if int(device.get("index", -1)) == index), None)


def validate_capture_sources(config: dict[str, Any]) -> dict[str, Any]:
    """Fail closed before FFmpeg opens a stale numeric video index."""
    capture_backend = str(config.get("capture_backend", "ffmpeg")).strip().lower()
    native_capture = capture_backend in {"screencapturekit", "screen_capture_kit", "native_screen"}
    if capture_backend != "ffmpeg" and not native_capture:
        return {"status": "skipped", "reason": "non_ffmpeg_capture_backend"}

    ffmpeg = str(config.get("ffmpeg_path") or "")
    screens = [] if native_capture else selected_capture_screens(config)
    webcam = config.get("webcam") if isinstance(config.get("webcam"), Mapping) else None
    microphone = None if native_capture else config.get("microphone") if isinstance(config.get("microphone"), Mapping) else None
    if not screens and webcam is None and microphone is None:
        return {"status": "pass", "reason": "no_live_capture_sources_requested"}

    inventory = run_ffmpeg_devices(ffmpeg)
    live_video = [device for device in inventory.get("videoDevices", []) if isinstance(device, dict)]
    live_audio = [device for device in inventory.get("audioDevices", []) if isinstance(device, dict)]
    failures: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []

    for screen in screens:
        index = _coerce_device_index(screen, role="screen")
        live = _live_device_by_index(live_video, index)
        selected_name = str(screen.get("name") or "")
        if live is None:
            failures.append({
                "id": "screen_source_missing",
                "message": f"Selected screen index {index} is not present in the current AVFoundation video devices.",
                "selected": {"index": index, "name": selected_name},
            })
            continue
        if not _is_screen_device(live):
            failures.append({
                "id": "screen_source_resolves_to_camera",
                "message": f"Selected screen index {index} currently resolves to video device {live.get('name')!r}, not a screen-capture device.",
                "selected": {"index": index, "name": selected_name},
                "live": {"index": live.get("index"), "name": live.get("name")},
            })
            continue
        checked.append({
            "role": "screen",
            "index": index,
            "selected_name": selected_name,
            "live_name": live.get("name"),
        })

    if webcam is not None:
        index = _coerce_device_index(webcam, role="webcam")
        live = _live_device_by_index(live_video, index)
        if live is None:
            failures.append({
                "id": "webcam_source_missing",
                "message": f"Selected webcam index {index} is not present in the current AVFoundation video devices.",
                "selected": {"index": index, "name": webcam.get("name")},
            })
        elif _is_screen_device(live):
            failures.append({
                "id": "webcam_source_resolves_to_screen",
                "message": f"Selected webcam index {index} currently resolves to screen-capture device {live.get('name')!r}.",
                "selected": {"index": index, "name": webcam.get("name")},
                "live": {"index": live.get("index"), "name": live.get("name")},
            })
        else:
            checked.append({
                "role": "webcam",
                "index": index,
                "selected_name": webcam.get("name"),
                "live_name": live.get("name"),
            })

    if microphone is not None:
        index = _coerce_device_index(microphone, role="microphone")
        live = _live_device_by_index(live_audio, index)
        if live is None:
            failures.append({
                "id": "microphone_source_missing",
                "message": f"Selected microphone index {index} is not present in the current AVFoundation audio devices.",
                "selected": {"index": index, "name": microphone.get("name")},
            })
        else:
            checked.append({
                "role": "microphone",
                "index": index,
                "selected_name": microphone.get("name"),
                "live_name": live.get("name"),
            })

    payload = {
        "schema": "demo_take_source_validation_v0",
        "status": "fail" if failures else "pass",
        "raw_status": inventory.get("raw_status"),
        "checked": checked,
        "failures": failures,
        "live_video_devices": [{"index": device.get("index"), "name": device.get("name")} for device in live_video],
        "live_audio_devices": [{"index": device.get("index"), "name": device.get("name")} for device in live_audio],
    }
    if failures:
        first = failures[0]
        raise RuntimeError(
            "Capture source validation failed before recording: "
            f"{first.get('message')} Use Reload Devices and choose a real display before pressing Start."
        )
    return payload


def test_microphone(ffmpeg: str, index: int, name: str, seconds: float = 1.25) -> dict[str, Any]:
    output = Path(tempfile.gettempdir()) / f"demo_take_mic_test_{os.getpid()}_{index}.m4a"
    command = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-f",
        "avfoundation",
        "-t",
        f"{seconds:.2f}",
        "-i",
        f"none:{index}",
        "-vn",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        str(output),
    ]
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=max(5.0, seconds + 4.0),
        )
        byte_count = output.stat().st_size if output.exists() else 0
    except subprocess.TimeoutExpired as exc:
        tail = (exc.stdout or exc.stderr or "").strip().splitlines()[-1:] or ["FFmpeg microphone test timed out."]
        return {
            "status": "failed",
            "deviceIndex": index,
            "deviceName": name,
            "bytes": 0,
            "statusLines": [tail[0]],
        }
    finally:
        try:
            output.unlink()
        except FileNotFoundError:
            pass

    log_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if proc.returncode == 0 and byte_count > 1024:
        return {
            "status": "ready",
            "deviceIndex": index,
            "deviceName": name,
            "bytes": byte_count,
            "statusLines": [f"Mic test passed for {name or f'audio device {index}'}."],
        }
    tail = log_lines[-1] if log_lines else f"FFmpeg exited {proc.returncode} without recording audio."
    return {
        "status": "failed",
        "deviceIndex": index,
        "deviceName": name,
        "bytes": byte_count,
        "statusLines": [f"Mic test failed for {name or f'audio device {index}'}: {tail}"],
    }


def manifest(
    take_id: str,
    root: Path,
    state: str,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    known_failures: list[str],
    markers: list[dict[str, Any]] | None = None,
    pause_events: list[dict[str, Any]] | None = None,
    media_segments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    def maybe(rel_path: str) -> str | None:
        return rel_path if (root / rel_path).exists() else None

    def first_existing_track(role_names: set[str]) -> str | None:
        for track in tracks:
            if track.get("role") not in role_names:
                continue
            rel_path = track.get("relative_path")
            if not rel_path:
                continue
            path = root / rel_path
            try:
                if path.exists() and path.stat().st_size > 0:
                    return rel_path
            except OSError:
                continue
        return None

    def source_from_track(role: str) -> dict[str, Any] | None:
        for track in tracks:
            if track.get("role") != role:
                continue
            rel_path = track.get("relative_path")
            if not rel_path:
                continue
            path = root / str(rel_path)
            try:
                if not path.exists() or path.stat().st_size <= 0:
                    continue
            except OSError:
                continue
            source: dict[str, Any] = {
                "index": track.get("device_index"),
                "name": track.get("device_name"),
                "kind": "video" if role in {"screen", "webcam"} else "audio",
                "capture_engine": track.get("capture_engine"),
            }
            if track.get("device_unique_id"):
                source["unique_id"] = track.get("device_unique_id")
            return {key: value for key, value in source.items() if value is not None}
        return None

    review_video = maybe("render/rough_cut.mp4") or first_existing_track({"external_video", "screen", "webcam"})
    timeline_projection = _read_json_dict(root / "render" / "timeline_projection_receipt.json")

    payload = {
        "schema": "demo_take_manifest_v0",
        "take_id": take_id,
        "created_at": now_iso(),
        "recording_state": state,
        "repo_root": config["repo_root"],
        "output_root": str(root.parent),
        "active_spool_root": str(take_output_root(Path(config["repo_root"]), config)),
        "active_spool_mode": "configured_external_root" if config.get("local_archive_root") else "repo_default",
        "default_output_root": str(Path(config["repo_root"]) / "state" / "dissemination" / "demo_takes"),
        "local_archive_root": config.get("local_archive_root") or None,
        "recipient": recipient_metadata(config),
        "ffmpeg_path": config["ffmpeg_path"],
        "screenshot_interval_seconds": config["screenshot_interval_seconds"],
        "storage_profile": storage_profile(config),
        "recording_quality": recording_quality(config),
        "marker_phrases": config.get("marker_phrases", DEFAULT_MARKER_PHRASES),
        "sources": {
            "screens": config.get("screens", []),
            "microphone": config.get("microphone"),
            "webcam": config.get("webcam") or source_from_track("webcam"),
        },
        "tracks": tracks,
        "marker_count": len(markers or []),
        "pause_event_count": len(pause_events or []),
        "media_segment_count": len(media_segments or []),
        "timeline_event_count": timeline_projection.get("event_count", 0),
        "chapter_count": timeline_projection.get("chapter_count", 0),
        "media_segments": media_segments or [],
        "transcript": maybe("transcript/transcript.json"),
        "visual_index": maybe("visual_index.json"),
        "edl": maybe("edl.json"),
        "view_telemetry": maybe("view_telemetry.jsonl"),
        "view_timeline": maybe("view_timeline.json"),
        "attention_events": maybe("attention_events.jsonl"),
        "active_timeline": maybe("active_timeline.json"),
        "timeline_events": maybe("timeline_events.jsonl"),
        "attention_spans": maybe("attention_spans.json"),
        "attention_editor_spans": maybe("attention_editor_spans.json"),
        "per_view_segments": maybe("per_view_segments.json"),
        "speech_blocks": maybe("speech_blocks.json"),
        "semantic_proxy": maybe("semantic_proxy.json"),
        "schedule_progress": maybe("schedule_progress.jsonl"),
        "intent_events": maybe("intent_events.json"),
        "view_episodes": maybe("view_episodes.json"),
        "ui_delta_index": maybe("ui_delta_index.json"),
        "candidate_clips": maybe("candidate_clips.json"),
        "multimodal_index": maybe("multimodal_index.json"),
        "render_receipt": maybe("render/render_receipt.json"),
        "clip_render_index": maybe("render/clips/index.json"),
        "media_timeline_receipt": maybe("render/media_timeline_receipt.json"),
        "timeline_sync_receipt": maybe(TIMELINE_SYNC_RECEIPT_RELATIVE_PATH),
        "timeline_projection_receipt": maybe("render/timeline_projection_receipt.json"),
        "storage_receipt": maybe("render/storage_receipt.json"),
        "local_storage_receipt": maybe("render/local_storage_receipt.json"),
        "proxy_review_receipt": maybe("render/proxy_review_receipt.json"),
        "markers_vtt": maybe("render/markers.vtt"),
        "chapters_vtt": maybe("render/chapters.vtt"),
        "chapters_ffmetadata": maybe("render/chapters.ffmetadata"),
        "transcript_with_markers": maybe("render/transcript_with_markers.json"),
        "review_video": review_video,
        "review_audio": maybe("render/review_audio.mp3"),
        "cloud_archive_manifest": maybe("render/cloud_archive_manifest.json"),
        "cloud_archive_receipt": maybe("render/cloud_archive_receipt.json"),
        "restore_drill_receipt": maybe(RESTORE_DRILL_RECEIPT_RELATIVE_PATH),
        "calibration_receipt": maybe(CALIBRATION_RECEIPT_RELATIVE_PATH),
        "edl_otio": maybe("edl.otio"),
        "autoedit_receipt": maybe("render/autoedit_receipt.json"),
        "capture_target": config.get("capture_target"),
        "source_kind": config.get("capture_backend", "ffmpeg"),
        "known_failures": known_failures,
    }
    return apply_title_metadata(payload, config.get("take_title") or config.get("title"))


def video_t_seconds(wall_t: float, pause_events: list[dict[str, Any]], cutoff_iso: str) -> float:
    """Subtract elapsed paused-duration before cutoff from a wall-clock seconds offset."""
    paused = 0.0
    last_pause: dt.datetime | None = None
    cutoff = dt.datetime.fromisoformat(cutoff_iso)
    for event in pause_events:
        at_iso = event.get("at_iso")
        if not at_iso:
            continue
        at = dt.datetime.fromisoformat(at_iso)
        if at > cutoff:
            break
        if event.get("kind") == "pause" and last_pause is None:
            last_pause = at
        elif event.get("kind") == "resume" and last_pause is not None:
            paused += (at - last_pause).total_seconds()
            last_pause = None
    if last_pause is not None:
        paused += (cutoff - last_pause).total_seconds()
    return max(0.0, wall_t - paused)


def launch_ffmpeg(
    ffmpeg: str,
    args: list[str],
    log_path: Path,
    *,
    control_path: Path | None = None,
) -> subprocess.Popen[Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    control_stdin = None
    stdin: Any = subprocess.DEVNULL
    if control_path is not None:
        try:
            control_path.parent.mkdir(parents=True, exist_ok=True)
            if control_path.exists() or control_path.is_symlink():
                control_path.unlink()
            os.mkfifo(control_path, 0o600)
            control_stdin = os.fdopen(os.open(control_path, os.O_RDWR), "rb", buffering=0)
            stdin = control_stdin
        except (AttributeError, OSError):
            stdin = subprocess.DEVNULL
            control_stdin = None

    log = log_path.open("ab")
    try:
        return subprocess.Popen(
            [ffmpeg, *args],
            stdout=log,
            stderr=log,
            stdin=stdin,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        log.close()
        if control_stdin is not None:
            control_stdin.close()


def ffmpeg_control_path_for_log(log_path: Path) -> Path:
    return log_path.with_suffix(".stdin")


def ffmpeg_process_record(
    root: Path,
    role: str,
    proc: subprocess.Popen[Any],
    log_path: Path,
    control_path: Path | None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": role,
        "pid": proc.pid,
        "log": relative(root, log_path),
    }
    if control_path is not None and control_path.exists():
        record["stop_control"] = relative(root, control_path)
        record["stop_contract"] = "stdin_q_then_signal_escalation"
    return record


def request_ffmpeg_quit(root: Path, proc: Mapping[str, Any]) -> bool:
    control = proc.get("stop_control")
    if not control:
        return False
    control_path = root / str(control)
    try:
        fd = os.open(control_path, os.O_WRONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "wb", buffering=0) as handle:
            handle.write(b"q\n")
        return True
    except OSError:
        return False


def start(config: dict[str, Any]) -> dict[str, Any]:
    repo_root = Path(config["repo_root"])
    config["storage_profile"] = storage_profile(config)
    config["recording_quality"] = recording_quality(config)
    config["screens"] = selected_capture_screens(config)
    quality_settings = recording_quality_settings(config)
    config["frame_thumbnail_width"] = _config_int(
        config,
        "frame_thumbnail_width",
        DEFAULT_FRAME_THUMBNAIL_WIDTH,
        minimum=320,
        maximum=2560,
    )
    config["frame_jpeg_quality"] = _config_int(
        config,
        "frame_jpeg_quality",
        3 if config["storage_profile"] == "source" else DEFAULT_FRAME_JPEG_QUALITY,
        minimum=2,
        maximum=12,
    )
    title = clean_take_title(config.get("take_title") or config.get("title"))
    if title:
        config["take_title"] = title
        config["take_slug"] = take_title_slug(title)
    recipient = recipient_metadata(config)
    if recipient:
        config.update({key: value for key, value in recipient.items() if value is not None})
    output_root = take_output_root(repo_root, config)
    config["take_output_root"] = str(output_root)
    capture_target = _capture_target_from_config(config)
    if capture_target:
        config["capture_target"] = capture_target
    ffmpeg = config["ffmpeg_path"]
    source_validation = validate_capture_sources(config)
    config["source_validation"] = source_validation
    archive_preflight = cloud_archive_preflight(config)
    config["cloud_archive_preflight"] = archive_preflight
    archive_preflight_warnings: list[str] = []
    if archive_preflight.get("status") == "fail":
        failures = archive_preflight.get("known_failures")
        detail = (
            "; ".join(str(item) for item in failures)
            if isinstance(failures, list)
            else "unknown failure"
        )
        archive_preflight_warnings.append(
            "Cloud archive preflight warning: "
            f"{detail}; recording will continue and source media will stay local if archive fails after stop."
        )
    governor_preflight = storage_governor_preflight(config, spool_root=output_root)
    config["storage_governor_preflight"] = governor_preflight
    if governor_preflight.get("status") == "fail":
        raise RuntimeError(
            governor_preflight.get("operator_line")
            or "Storage governor preflight failed: local disk is below the recording floor."
        )
    take_id, root = unique_take_root(repo_root, prefix="take", title=title, config=config)
    tracks_dir = root / "tracks"
    logs_dir = root / "logs"
    for name in ["tracks", "frames", "transcript", "render", "review", "logs"]:
        (root / name).mkdir(parents=True, exist_ok=True)

    tracks: list[dict[str, Any]] = []
    processes: list[dict[str, Any]] = []
    failures: list[str] = list(archive_preflight_warnings)
    capture_backend = str(config.get("capture_backend", "ffmpeg")).strip().lower()
    native_capture = capture_backend in {"screencapturekit", "screen_capture_kit", "native_screen"}

    for screen in config.get("screens", []):
        role = f"screen_{screen['index']}"
        output = tracks_dir / f"{role}.mp4"
        if native_capture:
            tracks.append(
                {
                    "id": role,
                    "role": "screen",
                    "device_name": screen["name"],
                    "device_index": screen["index"],
                    "relative_path": relative(root, output),
                    "capture_engine": "screencapturekit",
                }
            )
            continue
        screen_filter = quality_settings.get("scale_filter")
        screen_video_args: list[str] = []
        if screen_filter:
            screen_video_args = ["-vf", str(screen_filter)]
        log_path = logs_dir / f"{role}.log"
        control_path = ffmpeg_control_path_for_log(log_path)
        proc = launch_ffmpeg(
            ffmpeg,
            [
                "-hide_banner",
                "-y",
                "-f",
                "avfoundation",
                "-framerate",
                "30",
                "-capture_cursor",
                "1",
                "-i",
                f"{screen['index']}:none",
                "-r",
                "30",
                *screen_video_args,
                "-c:v",
                "h264_videotoolbox",
                "-b:v",
                quality_settings["screen_bitrate"],
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+frag_keyframe+empty_moov+default_base_moof",
                str(output),
            ],
            log_path,
            control_path=control_path,
        )
        tracks.append(
            {
                "id": role,
                "role": "screen",
                "device_name": screen["name"],
                "device_index": screen["index"],
                "relative_path": relative(root, output),
            }
        )
        processes.append(ffmpeg_process_record(root, role, proc, log_path, control_path))

    webcam = config.get("webcam")
    if webcam:
        role = f"webcam_{webcam['index']}"
        output = tracks_dir / "webcam.mp4"
        webcam_filter = quality_settings.get("scale_filter")
        webcam_video_args: list[str] = []
        if webcam_filter:
            webcam_video_args = ["-vf", str(webcam_filter)]
        log_path = logs_dir / f"{role}.log"
        control_path = ffmpeg_control_path_for_log(log_path)
        proc = launch_ffmpeg(
            ffmpeg,
            [
                "-hide_banner",
                "-y",
                "-f",
                "avfoundation",
                "-framerate",
                "30",
                "-i",
                f"{webcam['index']}:none",
                "-r",
                "30",
                *webcam_video_args,
                "-c:v",
                "h264_videotoolbox",
                "-b:v",
                quality_settings["webcam_bitrate"],
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+frag_keyframe+empty_moov+default_base_moof",
                str(output),
            ],
            log_path,
            control_path=control_path,
        )
        tracks.append(
            {
                "id": role,
                "role": "webcam",
                "device_name": webcam["name"],
                "device_index": webcam["index"],
                "relative_path": relative(root, output),
            }
        )
        processes.append(ffmpeg_process_record(root, role, proc, log_path, control_path))

    microphone = config.get("microphone")
    if microphone:
        role = f"microphone_{microphone['index']}"
        audio_extension = str(quality_settings.get("audio_extension") or ".m4a")
        output = tracks_dir / f"microphone{audio_extension}"
        if native_capture:
            tracks.append(
                {
                    "id": role,
                    "role": "microphone",
                    "device_name": microphone["name"],
                    "device_index": microphone["index"],
                    **_device_identity_fields(microphone),
                    "relative_path": relative(root, output),
                    "capture_engine": "avfoundation_native",
                }
            )
        else:
            audio_args = [
                "-c:a",
                str(quality_settings.get("audio_codec") or "aac"),
                "-ar",
                str(quality_settings.get("audio_sample_rate") or "48000"),
            ]
            if quality_settings.get("audio_codec") == "aac":
                audio_args += ["-b:a", quality_settings["audio_bitrate"]]
            log_path = logs_dir / f"{role}.log"
            control_path = ffmpeg_control_path_for_log(log_path)
            proc = launch_ffmpeg(
                ffmpeg,
                [
                    "-hide_banner",
                    "-y",
                    "-f",
                    "avfoundation",
                    "-i",
                    f"none:{microphone['index']}",
                    *audio_args,
                    str(output),
                ],
                log_path,
                control_path=control_path,
            )
            tracks.append(
                {
                    "id": role,
                    "role": "microphone",
                    "device_name": microphone["name"],
                    "device_index": microphone["index"],
                    **_device_identity_fields(microphone),
                    "relative_path": relative(root, output),
                }
            )
            processes.append(ffmpeg_process_record(root, role, proc, log_path, control_path))

    session = {
        "schema": "demo_take_session_v0",
        "take_id": take_id,
        "created_at": now_iso(),
        "config": config,
        "tracks": tracks,
        "processes": processes,
        "markers": [],
        "pause_events": [],
        "capture_target": capture_target,
        "known_failures": failures,
    }
    write_json(root / "session.json", session)
    write_json(
        root / "manifest.json",
        manifest(take_id, root, "recording", config, tracks, failures, markers=[], pause_events=[]),
    )
    backend_register = _backend_call(
        "PUT",
        "/api/recording/active-take",
        {"take_id": take_id, "take_root": str(root), "title": title},
    )
    status_lines = [f"Started {len(processes)} capture process(es)."]
    if title:
        status_lines.append(f"Take title: {title}.")
    if recipient:
        status_lines.append(
            "Recipient grouping: "
            f"{recipient.get('recipient_name') or recipient.get('recipient_id')}."
        )
    if output_root != repo_root / "state" / "dissemination" / "demo_takes":
        status_lines.append(f"Local archive root: {output_root}.")
    status_lines.append(f"Recording quality: {config['recording_quality']}.")
    if archive_preflight.get("status") == "pass":
        status_lines.append(f"Cloud archive preflight: {archive_preflight.get('remote')} reachable.")
    elif archive_preflight_warnings:
        status_lines.extend(archive_preflight_warnings)
    if governor_preflight.get("operator_line"):
        status_lines.append(str(governor_preflight["operator_line"]))
    if backend_register.get("active_take"):
        status_lines.append("View telemetry: FE registered with backend; navigation events will land in view_telemetry.jsonl.")
    else:
        status_lines.append("View telemetry: backend not reachable; recording proceeds without per-view events.")
    return {"takeID": take_id, "rootPath": str(root), "title": title, "statusLines": status_lines}


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        proc = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
            timeout=1,
        )
        stat = proc.stdout.strip()
        if proc.returncode != 0 or not stat:
            return False
        if stat.startswith("Z"):
            return False
    except (OSError, subprocess.TimeoutExpired):
        pass
    return True


def _take_operation_payload(root: Path, operation: str) -> dict[str, Any]:
    return {
        "schema": "demo_take_operation_lock_v0",
        "take_id": root.name,
        "root": str(root),
        "operation": operation,
        "pid": os.getpid(),
        "started_at": now_iso(),
    }


def _take_root_match_strings(root: Path) -> set[str]:
    values = {str(root), root.as_posix()}
    try:
        resolved = root.resolve()
        values.add(str(resolved))
        values.add(resolved.as_posix())
        if resolved.is_relative_to(REPO_ROOT):
            rel = resolved.relative_to(REPO_ROOT)
            values.add(str(rel))
            values.add(rel.as_posix())
    except (OSError, ValueError):
        pass
    return {value for value in values if value}


def _operation_from_helper_command(command: str) -> str | None:
    for operation in sorted(TAKE_EXCLUSIVE_OPERATIONS):
        if f" {operation} " in f" {command} ":
            return operation
    return None


def _find_active_take_helper_operation(root: Path, *, exclude_pid: int | None = None) -> dict[str, Any] | None:
    root_markers = _take_root_match_strings(root)
    try:
        proc = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            pid_text, command = stripped.split(maxsplit=1)
            pid = int(pid_text)
        except ValueError:
            continue
        if exclude_pid is not None and pid == exclude_pid:
            continue
        if "demo_take_capture.py" not in command or "--take-root" not in command:
            continue
        if not any(marker in command for marker in root_markers):
            continue
        operation = _operation_from_helper_command(command)
        if not operation or not pid_alive(pid):
            continue
        return {
            "schema": "demo_take_active_operation_v0",
            "source": "process_scan",
            "take_id": root.name,
            "root": str(root),
            "operation": operation,
            "pid": pid,
            "command": command,
        }
    return None


def _read_take_operation_lock(lock_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _take_operation_busy_response(root: Path, requested_operation: str, active: Mapping[str, Any]) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    take_id = str(session.get("take_id") or root.name)
    operation = str(active.get("operation") or "helper")
    pid = active.get("pid")
    message = (
        f"{requested_operation.capitalize()} deferred for {take_id}: "
        f"{operation} is already running" + (f" (pid {pid})" if pid else "") + "."
    )
    known_failures = list(session.get("known_failures", [])) if isinstance(session.get("known_failures"), list) else []
    return {
        "takeID": take_id,
        "rootPath": str(root),
        "status": "busy",
        "reason": "take_operation_busy",
        "statusLines": [message],
        "knownFailures": known_failures + [message],
        "result": {
            "status": "skipped",
            "reason": "take_operation_busy",
            "requested_operation": requested_operation,
            "active_operation": operation,
            "active_pid": pid,
        },
    }


def _acquire_take_operation_lock(root: Path, operation: str) -> tuple[Any | None, dict[str, Any] | None]:
    active_process = _find_active_take_helper_operation(root, exclude_pid=os.getpid())
    if active_process:
        return None, active_process
    lock_path = root / TAKE_OPERATION_LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        existing = _read_take_operation_lock(lock_path)
        handle.close()
        return None, existing or {"operation": "helper", "pid": None, "source": "file_lock"}
    payload = _take_operation_payload(root, operation)
    handle.seek(0)
    handle.truncate()
    handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    handle.flush()
    return handle, None


def run_take_operation(root: Path, operation: str, callback: Any) -> dict[str, Any]:
    handle, active = _acquire_take_operation_lock(root, operation)
    if active:
        return _take_operation_busy_response(root, operation, active)
    assert handle is not None
    lock_path = root / TAKE_OPERATION_LOCK_NAME
    try:
        return callback()
    finally:
        try:
            handle.seek(0)
            handle.truncate()
            handle.flush()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def signal_capture_process(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return
    except OSError:
        os.kill(pid, sig)


def _wait_for_capture_processes(processes: list[Mapping[str, Any]], timeout_seconds: float) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not any(pid_alive(int(proc["pid"])) for proc in processes):
            break
        time.sleep(0.25)


def _mark_newly_stopped(
    receipts: list[dict[str, Any]],
    processes: list[Mapping[str, Any]],
    status: str,
) -> None:
    for proc in processes:
        pid = int(proc["pid"])
        receipt = next((row for row in receipts if int(row.get("pid") or -1) == pid), None)
        if receipt is None or receipt.get("status"):
            continue
        if not pid_alive(pid):
            receipt["status"] = status


def stop_capture_processes(root: Path, processes: list[Mapping[str, Any]], failures: list[str]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    live_processes: list[Mapping[str, Any]] = []
    quit_requested = False

    for proc in processes:
        pid = int(proc["pid"])
        receipt: dict[str, Any] = {
            "id": proc.get("id"),
            "pid": pid,
            "stop_contract": proc.get("stop_contract") or "signal_escalation",
            "stop_control": proc.get("stop_control"),
            "stdin_q_requested": False,
            "sigint_sent": False,
            "sigterm_sent": False,
            "sigkill_sent": False,
        }
        receipts.append(receipt)
        if not pid_alive(pid):
            receipt["status"] = "already_stopped"
            continue

        live_processes.append(proc)
        signal_capture_process(pid, signal.SIGCONT)
        if request_ffmpeg_quit(root, proc):
            quit_requested = True
            receipt["stdin_q_requested"] = True

    if quit_requested:
        _wait_for_capture_processes(live_processes, 8)
        _mark_newly_stopped(receipts, live_processes, "stopped_after_stdin_q")

    sigint_processes = [proc for proc in live_processes if pid_alive(int(proc["pid"]))]
    for proc in sigint_processes:
        pid = int(proc["pid"])
        signal_capture_process(pid, signal.SIGCONT)
        signal_capture_process(pid, signal.SIGINT)
        for receipt in receipts:
            if int(receipt.get("pid") or -1) == pid:
                receipt["sigint_sent"] = True
                break

    _wait_for_capture_processes(sigint_processes, 15)
    _mark_newly_stopped(receipts, sigint_processes, "stopped_after_sigint")

    sigterm_processes = [proc for proc in sigint_processes if pid_alive(int(proc["pid"]))]
    for proc in sigterm_processes:
        pid = int(proc["pid"])
        signal_capture_process(pid, signal.SIGCONT)
        signal_capture_process(pid, signal.SIGTERM)
        failures.append(f"{proc['id']} did not stop after graceful quit/SIGINT; SIGTERM sent.")
        for receipt in receipts:
            if int(receipt.get("pid") or -1) == pid:
                receipt["sigterm_sent"] = True
                break

    _wait_for_capture_processes(sigterm_processes, 3)
    _mark_newly_stopped(receipts, sigterm_processes, "stopped_after_sigterm")

    for proc in sigterm_processes:
        pid = int(proc["pid"])
        if not pid_alive(pid):
            continue
        signal_capture_process(pid, signal.SIGKILL)
        failures.append(f"{proc['id']} did not stop after SIGTERM; SIGKILL sent.")
        for receipt in receipts:
            if int(receipt.get("pid") or -1) == pid:
                receipt["sigkill_sent"] = True
                receipt["status"] = "sigkill_sent"
                break

    for receipt in receipts:
        if not receipt.get("status"):
            receipt["status"] = "stopped"
    return receipts


def session_is_paused(session: Mapping[str, Any]) -> bool:
    last_pause_open = False
    pause_events = session.get("pause_events", [])
    if not isinstance(pause_events, list):
        return False
    for event in pause_events:
        if not isinstance(event, Mapping):
            continue
        if event.get("kind") == "pause":
            last_pause_open = True
        elif event.get("kind") == "resume":
            last_pause_open = False
    return last_pause_open


def signal_session(root: Path, sig: signal.Signals) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    sent: list[str] = []
    if sig == signal.SIGSTOP and session_is_paused(session):
        return {"statusLines": ["Recording already paused; duplicate pause ignored."]}
    if sig == signal.SIGCONT and not session_is_paused(session):
        return {"statusLines": ["Recording already running; duplicate resume ignored."]}

    for proc in session.get("processes", []):
        pid = int(proc["pid"])
        if pid_alive(pid):
            signal_capture_process(pid, sig)
            sent.append(proc["id"])

    if sig in (signal.SIGSTOP, signal.SIGCONT):
        pause_events = session.setdefault("pause_events", [])
        kind = "pause" if sig == signal.SIGSTOP else "resume"
        pause_events.append({"kind": kind, "at_iso": now_iso()})
        write_json(session_path, session)
        config = session.get("config", {})
        markers = session.get("markers", [])
        tracks = session.get("tracks", [])
        failures = session.get("known_failures", [])
        write_active_timeline_projection(root, config, session, tracks, failures)
        write_json(
            root / "manifest.json",
            manifest(
                session["take_id"],
                root,
                "paused" if kind == "pause" else "recording",
                config,
                tracks,
                failures,
                markers=markers,
                pause_events=pause_events,
                media_segments=session.get("media_segments", []),
            ),
        )

    return {"statusLines": [f"Sent {sig.name} to {', '.join(sent) if sent else 'no active processes'}."]}


def _append_marker_record(
    root: Path,
    session: dict[str, Any],
    record: dict[str, Any],
    recording_state: str,
) -> int:
    markers = session.setdefault("markers", [])
    markers.append(record)
    write_json(root / "session.json", session)
    config = session.get("config", {})
    tracks = session.get("tracks", [])
    failures = session.get("known_failures", [])
    pause_events = session.get("pause_events", [])
    write_active_timeline_projection(root, config, session, tracks, failures)
    write_json(
        root / "manifest.json",
        manifest(
            session["take_id"],
            root,
            recording_state,
            config,
            tracks,
            failures,
            markers=markers,
            pause_events=pause_events,
            media_segments=session.get("media_segments", []),
        ),
    )
    return len(markers)


def mark(root: Path, source: str, label: str | None) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    created_at = now_iso()
    started_at_iso = session.get("created_at")
    if not started_at_iso:
        raise ValueError("session.json is missing created_at; cannot compute marker timing")
    wall_t = (
        dt.datetime.fromisoformat(created_at) - dt.datetime.fromisoformat(started_at_iso)
    ).total_seconds()
    pause_events = session.get("pause_events", [])
    video_t = video_t_seconds(wall_t, pause_events, created_at)

    record = {
        "id": f"mark_{secrets.token_hex(6)}",
        "source": source,
        "label": label,
        "wall_t_seconds": round(wall_t, 3),
        "video_t_seconds": round(video_t, 3),
        "created_at": created_at,
    }
    recording_state = "paused" if session_is_paused(session) else "recording"
    count = _append_marker_record(root, session, record, recording_state)
    return {"marker": record, "markerCount": count}


def mark_at_video_t(
    root: Path,
    source: str,
    video_t: float,
    label: str | None,
    recording_state: str = "package_ready",
) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    record = {
        "id": f"mark_{secrets.token_hex(6)}",
        "source": source,
        "label": label,
        "wall_t_seconds": round(float(video_t), 3),
        "video_t_seconds": round(float(video_t), 3),
        "created_at": now_iso(),
    }
    count = _append_marker_record(root, session, record, recording_state)
    return {"marker": record, "markerCount": count}


def list_markers(root: Path) -> dict[str, Any]:
    session = json.loads((root / "session.json").read_text(encoding="utf-8"))
    return {"markers": session.get("markers", []), "pauseEvents": session.get("pause_events", [])}


def set_take_title(root: Path, title: str | None) -> dict[str, Any]:
    session_path = root / "session.json"
    manifest_path = root / "manifest.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    config = session.setdefault("config", {})
    cleaned = clean_take_title(title)
    if cleaned:
        config["take_title"] = cleaned
        config["take_slug"] = take_title_slug(cleaned)
    else:
        config.pop("take_title", None)
        config.pop("take_slug", None)
    write_json(session_path, session)

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    apply_title_metadata(manifest_payload, cleaned)
    manifest_payload["updated_at"] = now_iso()
    write_json(manifest_path, manifest_payload)
    return {
        "schema": "demo_take_title_update_v0",
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "title": cleaned,
        "slug": take_title_slug(cleaned),
        "statusLines": [f"Updated take title to {cleaned}." if cleaned else "Cleared take title."],
    }


def _load_run_map(path: Path = RUN_MAP_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"recording run map not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _route_key(route: str | None) -> str:
    if not route:
        return ""
    path = str(route).split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return path or "/"


def _title_for_step(step: dict[str, Any] | None) -> str | None:
    if not step:
        return None
    if step.get("title"):
        return str(step["title"])
    surface = str(step.get("surface_id") or step.get("step_id") or "")
    spaced = re.sub(r"(?<!^)([A-Z])", r" \1", surface).replace("_", " ")
    return spaced[:1].upper() + spaced[1:]


def _long_anchors_for_step(step: dict[str, Any]) -> list[str]:
    anchors: list[str] = []
    for bullet in step.get("long_bullets", [])[:5]:
        text = re.sub(r"\s+", " ", str(bullet)).strip()
        if not text:
            continue
        first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
        anchors.append(first_sentence if len(first_sentence) <= 110 else first_sentence[:107].rstrip() + "...")
    return anchors


def _controls_for_schedule_step(step: dict[str, Any]) -> list[str]:
    if step.get("step_kind") == "fe_view":
        surface = step.get("surface_id") or step.get("step_id")
        controls = [f"SLATE VIEW {surface}", "MARK SHORT"]
        if step.get("recording_treatment") == "hero":
            controls.append("MARK LONG")
        controls.extend([f"VIEW VERDICT {str(step.get('rank') or 'medium').upper()}", "VIEW DONE"])
        return controls
    title = _title_for_step(step) or str(step.get("step_id"))
    return [f"MARK CHAPTER {title}", "MARK GOOD"]


def _fetch_recent_route_state(backend_url: str) -> dict[str, Any] | None:
    root = backend_url.rstrip("/")
    current = _http_get_json(root + "/api/recording/current-surface")
    if isinstance(current, dict):
        surface = current.get("current_surface")
        if isinstance(surface, dict):
            return surface

    data = _http_get_json(root + "/api/recording/recent-view-events?limit=1")
    events = data.get("events") if isinstance(data, dict) else None
    if isinstance(events, list) and events:
        event = events[-1]
        return event if isinstance(event, dict) else None
    return None


def _match_schedule_step(
    run_map: dict[str, Any],
    *,
    route: str | None = None,
    capture_slug: str | None = None,
    step_id: str | None = None,
) -> dict[str, Any] | None:
    steps = run_map.get("steps", [])
    by_id = {step.get("step_id"): step for step in steps if isinstance(step, dict)}
    if step_id and step_id in by_id:
        return by_id[step_id]
    if capture_slug:
        for step in steps:
            if step.get("capture_slug") == capture_slug or step.get("surface_id") == capture_slug:
                return step
    route_norm = _route_key(route)
    if route_norm:
        for step in steps:
            if _route_key(step.get("route")) == route_norm:
                return step
    return None


def _append_schedule_progress(root: Path, state: dict[str, Any]) -> bool:
    path = root / "schedule_progress.jsonl"
    key = (state.get("current_step_id"), state.get("current_route"), state.get("status"))
    if path.exists():
        try:
            last = path.read_text(encoding="utf-8").splitlines()[-1]
            last_state = json.loads(last)
            last_key = (
                last_state.get("current_step_id"),
                last_state.get("current_route"),
                last_state.get("status"),
            )
            if last_key == key:
                return False
        except (IndexError, json.JSONDecodeError, OSError):
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(state, sort_keys=True) + "\n")
    return True


def schedule_state(
    *,
    route: str | None = None,
    capture_slug: str | None = None,
    step_id: str | None = None,
    backend_url: str | None = None,
    take_root: Path | None = None,
    emit_progress: bool = False,
) -> dict[str, Any]:
    run_map = _load_run_map()
    event = None
    if not (route or capture_slug or step_id):
        event = _fetch_recent_route_state(backend_url or DEFAULT_BACKEND_URL)
        if event:
            route = event.get("route") or event.get("pathname")
            capture_slug = event.get("view_id")

    step = _match_schedule_step(
        run_map,
        route=route,
        capture_slug=capture_slug,
        step_id=step_id,
    )
    sequence = run_map.get("recording_sequence", [])
    steps_by_id = {row.get("step_id"): row for row in run_map.get("steps", []) if isinstance(row, dict)}

    if not step:
        state = {
            "schema": "demo_take_schedule_state_v0",
            "status": "no_match" if (route or capture_slug or step_id) else "no_route",
            "created_at": now_iso(),
            "source_run_map": "docs/dissemination/recording_run_map_v0.json",
            "current_step_id": None,
            "current_route": route,
            "current_capture_slug": capture_slug,
            "step_index": None,
            "total_steps": len(sequence),
            "remaining_steps": len(sequence),
            "next_step_id": sequence[0] if sequence else None,
            "current_flash_say": "",
            "current_short_say": "",
            "long_anchors": [],
            "operator_cue": "",
            "public_claim_boundary": "",
            "recording_treatment": None,
            "controls": [],
            "event": event,
        }
    else:
        current_step_id = step["step_id"]
        step_index = sequence.index(current_step_id) + 1 if current_step_id in sequence else None
        next_step_id = step.get("after_step")
        next_step = steps_by_id.get(next_step_id) if next_step_id else None
        state = {
            "schema": "demo_take_schedule_state_v0",
            "status": "ready",
            "created_at": now_iso(),
            "source_run_map": "docs/dissemination/recording_run_map_v0.json",
            "current_step_id": current_step_id,
            "current_title": _title_for_step(step),
            "current_route": step.get("route") or route,
            "current_capture_slug": step.get("capture_slug") or capture_slug,
            "step_index": step_index,
            "total_steps": len(sequence),
            "remaining_steps": (len(sequence) - step_index) if step_index else None,
            "next_step_id": next_step_id,
            "next_title": _title_for_step(next_step),
            "current_flash_say": step.get("flash_say") or "",
            "current_short_say": step.get("short_say") or step.get("operator_cue") or "",
            "long_anchors": _long_anchors_for_step(step),
            "operator_cue": step.get("operator_cue") or "",
            "public_claim_boundary": step.get("public_claim_boundary") or "",
            "recording_treatment": step.get("recording_treatment"),
            "rank": step.get("rank"),
            "block": step.get("block"),
            "controls": _controls_for_schedule_step(step),
            "event": event,
        }
    if take_root and emit_progress:
        state["progress_appended"] = _append_schedule_progress(take_root, state)
    return state


_WORD_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_WHISPER_MARK_RE = re.compile(r"<\|[^|]*\|>")
_INTENT_CONTROL_SOURCE = (
    r"(?:slate\s+(?:block|view|short|long|retake)|"
    r"mark\s+(?:good|retake|cut\s+this|chapter|note|private|redact|do\s+not\s+publish|"
    r"confusing|too\s+much|needs\s+(?:example|visual)|short(?:\s+only)?|long(?:\s+only)?|"
    r"skip\s+view|uncertain)|(?:view|you)\s+(?:verdict|done))"
)
_INTENT_PAYLOAD_BOUNDARY_RE = re.compile(rf"\b{_INTENT_CONTROL_SOURCE}\b", re.IGNORECASE)
_INTENT_LABEL_CAPTURE = rf"(?P<label>.+?)(?=\s*(?:[.?!;\n]|\b{_INTENT_CONTROL_SOURCE}\b|$))"
_INTENT_LABEL_AFTER_SPACE = rf"\s+(?!{_INTENT_CONTROL_SOURCE}\b){_INTENT_LABEL_CAPTURE}"
_INTENT_VIEW_ALIAS_BLOCKLIST = (
    r"(?:verdict|done|can|could|should|would|will|are|were|is|was|do|did|does|"
    r"don't|dont|can't|cant|cannot|have|has|had|know|see|select|later|just|kind|"
    r"need|needs|want|wants|click|open|focus|go|get|got)"
)
_INTENT_RULES: list[dict[str, Any]] = [
    {"kind": "slate_block", "command": "SLATE BLOCK", "pattern": re.compile(rf"\bslate\s+block{_INTENT_LABEL_AFTER_SPACE}", re.IGNORECASE)},
    {"kind": "slate_view", "command": "SLATE VIEW", "pattern": re.compile(rf"\b(?:slate\s+view|you(?!\s+{_INTENT_VIEW_ALIAS_BLOCKLIST}\b)){_INTENT_LABEL_AFTER_SPACE}", re.IGNORECASE)},
    {"kind": "slate_short", "command": "SLATE SHORT VERSION", "pattern": re.compile(r"\bslate\s+short(?:\s+version)?\b", re.IGNORECASE)},
    {"kind": "slate_long", "command": "SLATE LONG EXPLANATION", "pattern": re.compile(r"\bslate\s+long(?:\s+explanation)?\b", re.IGNORECASE)},
    {"kind": "slate_retake", "command": "SLATE RETAKE", "pattern": re.compile(rf"\bslate\s+retake(?:{_INTENT_LABEL_AFTER_SPACE})?", re.IGNORECASE)},
    {"kind": "mark_good", "command": "MARK GOOD", "pattern": re.compile(r"\bmark\s+good\b", re.IGNORECASE)},
    {"kind": "mark_retake", "command": "MARK RETAKE", "pattern": re.compile(r"\bmark\s+retake\b", re.IGNORECASE)},
    {"kind": "mark_cut_this", "command": "MARK CUT THIS", "pattern": re.compile(r"\bmark\s+cut\s+this\b", re.IGNORECASE)},
    {"kind": "mark_chapter", "command": "MARK CHAPTER", "pattern": re.compile(rf"\bmark\s+chapter{_INTENT_LABEL_AFTER_SPACE}", re.IGNORECASE)},
    {"kind": "mark_note", "command": "MARK NOTE", "pattern": re.compile(rf"\bmark\s+note{_INTENT_LABEL_AFTER_SPACE}", re.IGNORECASE)},
    {"kind": "mark_private", "command": "MARK PRIVATE", "pattern": re.compile(r"\bmark\s+private\b", re.IGNORECASE), "privacy_flag": True},
    {"kind": "mark_redact", "command": "MARK REDACT", "pattern": re.compile(r"\bmark\s+redact\b", re.IGNORECASE), "privacy_flag": True},
    {"kind": "mark_do_not_publish", "command": "MARK DO NOT PUBLISH", "pattern": re.compile(r"\bmark\s+do\s+not\s+publish\b", re.IGNORECASE), "privacy_flag": True},
    {"kind": "mark_confusing", "command": "MARK CONFUSING", "pattern": re.compile(r"\bmark\s+confusing\b", re.IGNORECASE)},
    {"kind": "mark_too_much", "command": "MARK TOO MUCH", "pattern": re.compile(r"\bmark\s+too\s+much\b", re.IGNORECASE)},
    {"kind": "mark_needs_example", "command": "MARK NEEDS EXAMPLE", "pattern": re.compile(r"\bmark\s+needs\s+example\b", re.IGNORECASE)},
    {"kind": "mark_needs_visual", "command": "MARK NEEDS VISUAL", "pattern": re.compile(r"\bmark\s+needs\s+visual\b", re.IGNORECASE)},
    {"kind": "mark_short_only", "command": "MARK SHORT ONLY", "pattern": re.compile(r"\bmark\s+short\s+only\b", re.IGNORECASE)},
    {"kind": "mark_long_only", "command": "MARK LONG ONLY", "pattern": re.compile(r"\bmark\s+long\s+only\b", re.IGNORECASE)},
    {"kind": "mark_short", "command": "MARK SHORT", "pattern": re.compile(r"\bmark\s+short(?!\s+only)\b", re.IGNORECASE)},
    {"kind": "mark_long", "command": "MARK LONG", "pattern": re.compile(r"\bmark\s+long(?!\s+only)\b", re.IGNORECASE)},
    {"kind": "mark_skip_view", "command": "MARK SKIP VIEW", "pattern": re.compile(r"\bmark\s+skip\s+view\b", re.IGNORECASE)},
    {"kind": "mark_uncertain", "command": "MARK UNCERTAIN", "pattern": re.compile(r"\bmark\s+uncertain\b", re.IGNORECASE)},
    {"kind": "view_verdict", "command": "VIEW VERDICT", "pattern": re.compile(r"\b(?:view|you)\s+verdict\s+(?P<verdict>high|medium|low|skip|long\s+only)\b", re.IGNORECASE)},
    {"kind": "view_done", "command": "VIEW DONE", "pattern": re.compile(r"\b(?:view|you)\s+done\b", re.IGNORECASE), "canonical_phrase": True},
]
_FEEDBACK_RULES: list[dict[str, Any]] = [
    {
        "feedback_type": "complaint",
        "failure_class": "recording_timer_overlay_obstruction",
        "owner": "demo_take_console_recording_overlay",
        "observed": "The recording timer pop-up obstructs recorded content.",
        "expected": "The timer overlay can be minimized or hidden during recording.",
        "patterns": [
            re.compile(r"\bwe\s+need\s+to\s+minimize\b[^.?!;]*", re.IGNORECASE),
            re.compile(r"\bgetting\s+in\s+the\s+way\b", re.IGNORECASE),
            re.compile(r"\bhide\s+it\s+maybe\b", re.IGNORECASE),
        ],
    },
    {
        "feedback_type": "complaint",
        "failure_class": "inspector_scroll_blocked",
        "owner": "zenith_inspector_route",
        "observed": "The inspector view is not scrollable enough to inspect content.",
        "expected": "Inspector tree and detail panes own bounded scroll regions.",
        "patterns": [
            re.compile(r"\b(?:i\s+)?(?:can't|cant|cannot)\s+scroll\b[^.?!;]*", re.IGNORECASE),
            re.compile(r"\bjust\s+scroll\b[^.?!;]*\bannoying\b", re.IGNORECASE),
        ],
    },
    {
        "feedback_type": "expected_behavior",
        "failure_class": "related_file_navigation_expected",
        "owner": "zenith_inspector_relations",
        "observed": "Related file rows are visible while the expected navigation is being narrated.",
        "expected": "Clicking a related file should navigate through to that file.",
        "patterns": [
            re.compile(r"\bshould\s+take\s+(?:through|you|me)\b[^.?!;]*", re.IGNORECASE),
            re.compile(r"\bclick\s+on\s+those\b[^.?!;]*", re.IGNORECASE),
        ],
    },
    {
        "feedback_type": "confusion",
        "failure_class": "codemap_focus_control_discoverability",
        "owner": "zenith_codemap_route",
        "observed": "The focus control path is unclear during the demo.",
        "expected": "Focus should be directly discoverable from the active codemap workflow.",
        "patterns": [
            re.compile(r"\bwhy\s+can't\s+i\b[^.?!;]*\bfocus\b", re.IGNORECASE),
            re.compile(r"\bdo\s+i\s+have\s+to\s+open\s+focus\b[^.?!;]*", re.IGNORECASE),
            re.compile(r"\bopen\s+focus\b[^.?!;]*\bannoying\b", re.IGNORECASE),
        ],
    },
]


def _normalize_word(text: str) -> str:
    return _WORD_NORMALIZE_RE.sub("", text.lower())


def _clean_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _clean_transcript_text(text: Any) -> str:
    return _clean_text(_WHISPER_MARK_RE.sub(" ", str(text or "")))


def _trim_intent_payload(value: str) -> str:
    cleaned = _clean_text(value).strip(" .,:;-")
    boundary = _INTENT_PAYLOAD_BOUNDARY_RE.search(cleaned)
    if boundary and boundary.start() > 0:
        cleaned = cleaned[: boundary.start()].strip(" .,:;-")
    return cleaned


def _intent_phrase(rule: dict[str, Any], payload: dict[str, Any], raw_phrase: str) -> str:
    command = str(rule["command"])
    label = payload.get("label")
    if isinstance(label, str) and label:
        return f"{command} {label}"
    verdict = payload.get("verdict")
    if isinstance(verdict, str) and verdict:
        return f"{command} {verdict.replace('_', ' ').upper()}"
    if rule.get("canonical_phrase"):
        return command
    return _clean_text(raw_phrase) or command


def _segment_words(segment: dict[str, Any]) -> list[dict[str, Any]]:
    words = segment.get("words", [])
    return [word for word in words if isinstance(word, dict)]


def _event_time_from_segment(segment: dict[str, Any], phrase: str) -> float:
    tokens = [_normalize_word(token) for token in phrase.split() if token.strip()]
    tokens = [token for token in tokens if token]
    words = _segment_words(segment)
    normalized = [_normalize_word(str(word.get("word", ""))) for word in words]
    if tokens and normalized:
        for index in range(0, max(0, len(normalized) - len(tokens) + 1)):
            if normalized[index : index + len(tokens)] == tokens:
                try:
                    return float(words[index].get("start", segment.get("start", 0.0)))
                except (TypeError, ValueError):
                    break
    try:
        return float(segment.get("start", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _event_word_span_from_segment(segment: dict[str, Any], phrase: str) -> dict[str, Any]:
    tokens = [_normalize_word(token) for token in phrase.split() if token.strip()]
    tokens = [token for token in tokens if token]
    words = _segment_words(segment)
    normalized = [_normalize_word(str(word.get("word", ""))) for word in words]
    if tokens and normalized:
        for index in range(0, max(0, len(normalized) - len(tokens) + 1)):
            if normalized[index : index + len(tokens)] == tokens:
                end_index = index + len(tokens) - 1
                start_word = words[index]
                end_word = words[end_index]
                return {
                    "start_word_index": start_word.get("word_index", index),
                    "end_word_index": end_word.get("word_index", end_index),
                    "word_ids": [
                        str(word.get("id") or word.get("word_id") or word.get("word_index") or f"{segment.get('id', 'segment')}:w{word_index:04d}")
                        for word_index, word in enumerate(words[index : end_index + 1], start=index)
                    ],
                    "start_seconds": _word_float(start_word, "start"),
                    "end_seconds": _word_float(end_word, "end"),
                }
        joined_tokens = "".join(tokens)
        for index in range(len(normalized)):
            joined_words = ""
            for end_index in range(index, len(normalized)):
                joined_words += normalized[end_index]
                if joined_words == joined_tokens:
                    start_word = words[index]
                    end_word = words[end_index]
                    return {
                        "start_word_index": start_word.get("word_index", index),
                        "end_word_index": end_word.get("word_index", end_index),
                        "word_ids": [
                            str(word.get("id") or word.get("word_id") or word.get("word_index") or f"{segment.get('id', 'segment')}:w{word_index:04d}")
                            for word_index, word in enumerate(words[index : end_index + 1], start=index)
                        ],
                        "start_seconds": _word_float(start_word, "start"),
                        "end_seconds": _word_float(end_word, "end"),
                    }
                if len(joined_words) >= len(joined_tokens):
                    break
    start = _word_float(segment, "start") or 0.0
    end = _word_float(segment, "end")
    return {
        "start_word_index": None,
        "end_word_index": None,
        "word_ids": [],
        "start_seconds": start,
        "end_seconds": end if end is not None else start,
    }


def _load_view_span_index(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "view_timeline.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    spans = payload.get("spans")
    if not isinstance(spans, list):
        return {}
    return {
        str(span.get("id")): span
        for span in spans
        if isinstance(span, dict) and span.get("id")
    }


def _route_for_segment(segment: dict[str, Any], view_spans_by_id: dict[str, dict[str, Any]]) -> str | None:
    if isinstance(segment.get("route"), str):
        return str(segment["route"])
    span_id = str(segment.get("view_span_id") or "")
    span = view_spans_by_id.get(span_id)
    if isinstance(span, dict) and isinstance(span.get("route"), str):
        return str(span["route"])
    return None


def _nearest_visual_frames(root: Path, timestamp: float, *, limit: int = 3) -> list[dict[str, Any]]:
    path = root / "visual_index.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    frames = payload.get("frames")
    if not isinstance(frames, list):
        return []
    candidates: list[dict[str, Any]] = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        rel = frame.get("relative_path")
        if not isinstance(rel, str):
            continue
        try:
            frame_t = float(frame.get("timestamp_seconds"))
        except (TypeError, ValueError):
            continue
        candidates.append({
            "relative_path": rel,
            "timestamp_seconds": round(frame_t, 3),
            "time_error_seconds": round(frame_t - timestamp, 3),
            "track_id": frame.get("track_id"),
        })
    candidates.sort(key=lambda row: (abs(float(row["timestamp_seconds"]) - timestamp), row["relative_path"]))
    return candidates[:limit]


def _transcript_source_identity(transcript_path: Path, segment: dict[str, Any]) -> dict[str, Any]:
    digest: str | None = None
    if transcript_path.exists():
        try:
            digest = hashlib.sha256(transcript_path.read_bytes()).hexdigest()
        except OSError:
            digest = None
    return {
        "transcript_ref": "transcript/transcript.json",
        "transcript_sha256": f"sha256:{digest}" if digest else None,
        "transcript_segment_id": segment.get("id"),
        "segment_start_seconds": segment.get("start"),
        "segment_end_seconds": segment.get("end"),
    }


def _feedback_events_from_segment(
    root: Path,
    transcript_path: Path,
    segment: dict[str, Any],
    text: str,
    view_spans_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    route = _route_for_segment(segment, view_spans_by_id)
    for rule in _FEEDBACK_RULES:
        matched: re.Match[str] | None = None
        for pattern in rule["patterns"]:
            matched = pattern.search(text)
            if matched:
                break
        if not matched:
            continue
        spoken_excerpt = _clean_text(matched.group(0)).strip(" .,:;-")
        word_span = _event_word_span_from_segment(segment, spoken_excerpt)
        source_time = _word_float(word_span, "start_seconds")
        if source_time is None:
            source_time = _event_time_from_segment(segment, spoken_excerpt)
        source_time = round(source_time, 3)
        end_seconds = _word_float(word_span, "end_seconds")
        end_seconds = round(end_seconds, 3) if end_seconds is not None else source_time
        failure_class = str(rule["failure_class"])
        source_identity = _transcript_source_identity(transcript_path, segment)
        nearby_frames = _nearest_visual_frames(root, source_time)
        evidence_refs = [
            f"transcript:{source_identity.get('transcript_ref')}#{source_identity.get('transcript_segment_id')}",
        ]
        if segment.get("view_span_id"):
            evidence_refs.append(f"view_span:{segment.get('view_span_id')}")
        if route:
            evidence_refs.append(f"route:{route}")
        evidence_refs.extend(f"frame:{frame.get('relative_path')}" for frame in nearby_frames if frame.get("relative_path"))
        payload = {
            "feedback_type": rule["feedback_type"],
            "failure_class": failure_class,
            "observed": rule["observed"],
            "expected": rule["expected"],
            "owner": rule["owner"],
            "disposition": "captured_for_triage",
            "source_identity": source_identity,
            "source_time_seconds": source_time,
            "source_end_seconds": end_seconds,
            "spoken_excerpt": spoken_excerpt,
            "word_range": {
                "start_word_index": word_span.get("start_word_index"),
                "end_word_index": word_span.get("end_word_index"),
            },
            "word_ids": word_span.get("word_ids") if isinstance(word_span.get("word_ids"), list) else [],
            "nearby_frames": nearby_frames,
            "app_route": route,
        }
        events.append({
            "_match_start": matched.start(),
            "kind": "operator_feedback",
            "command": "OPERATOR FEEDBACK",
            "phrase": f"OPERATOR FEEDBACK {failure_class}",
            "payload": payload,
            "feedback_type": rule["feedback_type"],
            "failure_class": failure_class,
            "start_seconds": source_time,
            "end_seconds": end_seconds,
            "word_range": payload["word_range"],
            "word_ids": payload["word_ids"],
            "observed_behavior": rule["observed"],
            "expected_behavior": rule["expected"],
            "owner_family": rule["owner"],
            "disposition": "captured_for_triage",
            "evidence_refs": evidence_refs,
            "confidence": 0.85,
            "video_t_seconds": source_time,
            "transcript_segment_id": segment.get("id"),
            "view_id": segment.get("view_id"),
            "view_label": segment.get("view_label"),
            "view_span_id": segment.get("view_span_id"),
            "route": route,
            "text": text,
        })
    return events


def _flatten_transcript_words(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    flat = transcript.get("words")
    if isinstance(flat, list) and flat:
        for word in flat:
            if isinstance(word, dict) and "start" in word:
                words.append(word)
        return words
    for segment in transcript.get("segments", []):
        for word in segment.get("words", []) or []:
            if isinstance(word, dict) and "start" in word:
                words.append(word)
    return words


def voice_scan(
    root: Path,
    phrases_override: list[str] | None = None,
    debounce_seconds: float = 2.0,
) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    transcript_path = root / "transcript" / "transcript.json"
    if not transcript_path.exists():
        return {"status": "skipped", "reason": "no_transcript"}
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    if transcript.get("status") != "ready":
        return {"status": "skipped", "reason": "transcript_not_ready"}

    raw_phrases = (
        phrases_override
        or session.get("config", {}).get("marker_phrases")
        or DEFAULT_MARKER_PHRASES
    )
    phrases: list[tuple[str, list[str]]] = []
    for phrase in raw_phrases:
        tokens = [_normalize_word(token) for token in phrase.split() if token.strip()]
        tokens = [token for token in tokens if token]
        if tokens:
            phrases.append((phrase, tokens))
    if not phrases:
        return {"status": "skipped", "reason": "no_phrases"}

    words = _flatten_transcript_words(transcript)
    if not words:
        return {"status": "skipped", "reason": "no_words"}

    normalized = [
        (_normalize_word(str(word.get("word", ""))), float(word.get("start", 0.0)))
        for word in words
    ]

    existing_markers = session.get("markers", [])
    voice_marker_times = sorted(
        float(marker["video_t_seconds"])
        for marker in existing_markers
        if marker.get("source") == "voice" and "video_t_seconds" in marker
    )
    fired: list[dict[str, Any]] = []
    last_fired_at = voice_marker_times[-1] if voice_marker_times else -1e9

    for index in range(len(normalized)):
        for phrase_text, tokens in phrases:
            if index + len(tokens) > len(normalized):
                continue
            window = normalized[index : index + len(tokens)]
            if any(not token for token in (token for token, _ in window)):
                continue
            if all(window[i][0] == tokens[i] for i in range(len(tokens))):
                marker_t = window[0][1]
                if marker_t - last_fired_at < debounce_seconds:
                    continue
                fired.append({"phrase": phrase_text, "video_t_seconds": marker_t})
                last_fired_at = marker_t

    appended: list[dict[str, Any]] = []
    for hit in fired:
        record = mark_at_video_t(
            root,
            source="voice",
            video_t=hit["video_t_seconds"],
            label=hit["phrase"],
        )
        appended.append(record["marker"])

    return {
        "status": "ready",
        "phrases_checked": [phrase for phrase, _ in phrases],
        "matched_count": len(appended),
        "markers": appended,
    }


def _read_view_telemetry_events(root: Path) -> list[dict[str, Any]]:
    path = root / "view_telemetry.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "video_t_seconds" in event:
            events.append(event)
    def event_time(event: dict[str, Any]) -> float:
        try:
            return float(event.get("video_t_seconds") or 0.0)
        except (TypeError, ValueError):
            return 0.0
    events.sort(key=event_time)
    return events


def _take_total_seconds(root: Path) -> float:
    session_path = root / "session.json"
    transcript_path = root / "transcript" / "transcript.json"
    candidates: list[float] = []
    if session_path.exists():
        session = json.loads(session_path.read_text(encoding="utf-8"))
        for marker in session.get("markers", []):
            candidates.append(float(marker.get("video_t_seconds") or 0.0))
    if transcript_path.exists():
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        duration = transcript.get("duration_seconds")
        if isinstance(duration, (int, float)):
            candidates.append(float(duration))
        for segment in transcript.get("segments", []):
            end = segment.get("end")
            if isinstance(end, (int, float)):
                candidates.append(float(end))
    return max(candidates) if candidates else 0.0


def build_view_timeline(root: Path) -> dict[str, Any]:
    events = _read_view_telemetry_events(root)
    if not events:
        timeline = {
            "schema": "demo_take_view_timeline_v0",
            "take_id": (root.name),
            "created_at": now_iso(),
            "spans": [],
            "event_count": 0,
            "status": "no_events",
        }
        write_json(root / "view_timeline.json", timeline)
        return timeline

    end_anchor = max(_take_total_seconds(root), float(events[-1].get("video_t_seconds") or 0.0))
    spans: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        start = float(event.get("video_t_seconds") or 0.0)
        if index + 1 < len(events):
            end = float(events[index + 1].get("video_t_seconds") or start)
        else:
            end = max(start, end_anchor)
        spans.append({
            "id": f"vs_{index:04d}",
            "view_id": event.get("view_id"),
            "view_label": event.get("view_label"),
            "route": event.get("route"),
            "start_video_t": round(start, 3),
            "end_video_t": round(end, 3),
            "duration_seconds": round(max(0.0, end - start), 3),
            "wall_t_seconds": float(event.get("wall_t_seconds") or 0.0),
            "at_iso": event.get("at_iso"),
        })
    timeline = {
        "schema": "demo_take_view_timeline_v0",
        "take_id": root.name,
        "created_at": now_iso(),
        "spans": spans,
        "event_count": len(events),
        "status": "ready",
    }
    write_json(root / "view_timeline.json", timeline)
    return timeline


def _attention_event_time(event: dict[str, Any]) -> float | None:
    for key in ("video_t_seconds", "video_t", "time_seconds"):
        value = _safe_float(event.get(key))
        if value is not None:
            return value
    return None


def _read_attention_events(root: Path) -> list[dict[str, Any]]:
    path = root / "attention_events.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and _attention_event_time(event) is not None:
            events.append(event)
    events.sort(key=lambda event: _attention_event_time(event) or 0.0)
    return events


def _attention_frontmost(event: dict[str, Any]) -> dict[str, Any]:
    for key in ("frontmost_app", "frontmost", "application"):
        value = event.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _attention_window(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("window")
    return value if isinstance(value, dict) else {}


def _attention_overlap(event: dict[str, Any]) -> float:
    window = _attention_window(event)
    for source in (window, event):
        for key in ("recorded_display_overlap", "intersection_ratio", "overlap_ratio"):
            value = _safe_float(source.get(key))
            if value is not None:
                return max(0.0, min(1.0, value))
    if event.get("is_on_recorded_display") is True or window.get("is_on_recorded_display") is True:
        return 1.0
    return 0.0


def _attention_on_recorded_display(event: dict[str, Any]) -> bool:
    if event.get("is_on_recorded_display") is False:
        return False
    return _attention_overlap(event) > 0.0 or event.get("is_on_recorded_display") is True


def _attention_station_hint(event: dict[str, Any]) -> bool:
    frontmost = _attention_frontmost(event)
    window = _attention_window(event)
    parts = [
        event.get("route"),
        event.get("pathname"),
        event.get("public_safe_label"),
        frontmost.get("localized_name"),
        frontmost.get("bundle_identifier"),
        frontmost.get("bundleIdentifier"),
        window.get("title"),
        window.get("public_safe_title"),
        window.get("owner_name"),
    ]
    text = " ".join(str(part) for part in parts if part).lower()
    hints = (
        "/station",
        "station",
        "ai workflow",
        "localhost",
        "127.0.0.1",
        "root navigator",
        "system atlas",
        "demo take",
        "codemap",
    )
    return any(hint in text for hint in hints)


def _attention_accepts_view_telemetry(event: dict[str, Any]) -> bool:
    return _attention_on_recorded_display(event) and _attention_station_hint(event)


def _attention_text(event: dict[str, Any], view_span: dict[str, Any] | None = None) -> str:
    frontmost = _attention_frontmost(event)
    window = _attention_window(event)
    target = event.get("attention_target") if isinstance(event.get("attention_target"), Mapping) else {}
    parts = [
        event.get("route"),
        event.get("pathname"),
        event.get("public_safe_label"),
        frontmost.get("localized_name"),
        frontmost.get("name"),
        frontmost.get("bundle_identifier"),
        frontmost.get("bundleIdentifier"),
        window.get("title"),
        window.get("public_safe_title"),
        window.get("owner_name"),
        target.get("kind"),
        target.get("label"),
        target.get("route"),
        (view_span or {}).get("view_id"),
        (view_span or {}).get("view_label"),
        (view_span or {}).get("route"),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def _attention_is_browser(event: dict[str, Any]) -> bool:
    frontmost = _attention_frontmost(event)
    bundle = str(frontmost.get("bundle_identifier") or frontmost.get("bundleIdentifier") or "").lower()
    name = str(frontmost.get("localized_name") or frontmost.get("name") or "").lower()
    return any(hint in bundle or hint in name for hint in BROWSER_BUNDLE_HINTS)


def _attention_policy(kind: str) -> dict[str, Any]:
    return ATTENTION_TARGET_POLICIES.get(kind, ATTENTION_TARGET_POLICIES["unknown"])


def _attention_kind_for_event(event: dict[str, Any], view_span: dict[str, Any] | None = None) -> str:
    target = event.get("attention_target") if isinstance(event.get("attention_target"), Mapping) else {}
    declared_kind = str(target.get("kind") or "").strip()
    if declared_kind in ATTENTION_TARGET_POLICIES:
        return declared_kind
    privacy = event.get("privacy") if isinstance(event.get("privacy"), Mapping) else {}
    if privacy.get("public_safe_default") is False:
        return "private_or_review"
    if view_span:
        return "station_view"

    text = _attention_text(event, view_span)
    frontmost = _attention_frontmost(event)
    window = _attention_window(event)
    bundle = str(frontmost.get("bundle_identifier") or frontmost.get("bundleIdentifier") or "").lower()
    app_name = str(frontmost.get("localized_name") or frontmost.get("name") or "").lower()

    if "obsidian" in bundle or "obsidian" in app_name or "obsidian" in text or "record_all_master_script" in text:
        return "obsidian_teleprompter"
    if "demo take" in text or "demotake" in bundle:
        return "demo_take_console"
    if "agent trace" in text or "/agent-trace" in text or "agent-trace" in text:
        return "agent_trace"
    if "system bar" in text or "system-bar" in text or "workbar" in text:
        return "system_bar"
    if "microcosm" in text:
        return "microcosm_site"
    if ("station" in text or "ai workflow" in text or "localhost" in text or "127.0.0.1" in text) and _attention_is_browser(event):
        return "ai_work_surface"
    if "terminal" in bundle or "terminal" in app_name or "iterm" in bundle or "iterm" in app_name:
        return "terminal"
    if "finder" in bundle or "finder" in app_name:
        return "finder"
    if _attention_is_browser(event):
        return "browser_generic"
    if window:
        return "application_window"
    if frontmost:
        return "application"
    return "unknown"


def _attention_resolver(kind: str, view_span: dict[str, Any] | None) -> str:
    if view_span:
        return "os_window+station_recent_view"
    if kind in {"agent_trace", "system_bar", "ai_work_surface", "demo_take_console", "microcosm_site", "obsidian_teleprompter", "browser_generic", "terminal", "finder"}:
        return "os_window+app_classifier"
    return "frontmost_app+window_geometry"


def _attention_target_payload(
    event: dict[str, Any],
    *,
    kind: str,
    view_span: dict[str, Any] | None,
    public_label: str | None,
) -> dict[str, Any]:
    declared = event.get("attention_target") if isinstance(event.get("attention_target"), Mapping) else {}
    return {
        "kind": kind,
        "label": public_label or declared.get("label") or _attention_policy(kind)["reason"],
        "route": (view_span or {}).get("route") or declared.get("route"),
        "view_id": (view_span or {}).get("view_id") or declared.get("view_id"),
        "resolver": declared.get("resolver") or _attention_resolver(kind, view_span),
        "confidence": declared.get("confidence") or event.get("confidence") or "unknown",
    }


def _attention_public_label(event: dict[str, Any], view_span: dict[str, Any] | None = None) -> str | None:
    if view_span and view_span.get("view_label"):
        return str(view_span.get("view_label"))
    frontmost = _attention_frontmost(event)
    window = _attention_window(event)
    for value in (
        event.get("public_safe_label"),
        window.get("public_safe_title"),
        window.get("title_public"),
        frontmost.get("localized_name"),
        frontmost.get("name"),
    ):
        if value:
            return str(value)
    return None


def _attention_span_target_key(span: dict[str, Any]) -> tuple[Any, ...]:
    return (
        span.get("attention_kind"),
        span.get("view_span_id"),
        (span.get("privacy") or {}).get("post_edit_policy"),
        span.get("public_safe_label"),
        (span.get("frontmost_app") or {}).get("bundle_identifier"),
        (span.get("window") or {}).get("window_id"),
    )


def _merge_attention_spans(raw_spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for span in raw_spans:
        if not merged or _attention_span_target_key(merged[-1]) != _attention_span_target_key(span):
            row = dict(span)
            row["source_event_count"] = 1
            merged.append(row)
            continue
        previous = merged[-1]
        previous["end_video_t"] = span["end_video_t"]
        previous["duration_seconds"] = round(max(0.0, previous["end_video_t"] - previous["start_video_t"]), 3)
        previous["source_event_count"] = int(previous.get("source_event_count") or 1) + 1
        previous["confidence"] = span.get("confidence") or previous.get("confidence")
        previous["recorded_display_overlap"] = max(
            _safe_float(previous.get("recorded_display_overlap")) or 0.0,
            _safe_float(span.get("recorded_display_overlap")) or 0.0,
        )
    for index, span in enumerate(merged):
        span["id"] = f"as_{index:04d}"
    return merged


def build_attention_spans(root: Path) -> dict[str, Any]:
    events = _read_attention_events(root)
    if not events:
        payload = {
            "schema": "demo_take_attention_spans_v0",
            "take_id": root.name,
            "created_at": now_iso(),
            "status": "no_events",
            "event_count": 0,
            "span_count": 0,
            "spans": [],
            "sources": {
                "attention_events": "attention_events.jsonl",
                "view_timeline": "view_timeline.json" if (root / "view_timeline.json").exists() else None,
            },
        }
        write_json(root / "attention_spans.json", payload)
        return payload

    if not (root / "view_timeline.json").exists() and (root / "view_telemetry.jsonl").exists():
        build_view_timeline(root)
    view_timeline = json.loads((root / "view_timeline.json").read_text(encoding="utf-8")) if (root / "view_timeline.json").exists() else {}
    view_spans = view_timeline.get("spans", []) if isinstance(view_timeline.get("spans"), list) else []
    end_anchor = max(_take_total_seconds(root), _attention_event_time(events[-1]) or 0.0)

    raw_spans: list[dict[str, Any]] = []
    accepted_view_merge_count = 0
    suppressed_view_merge_count = 0
    for index, event in enumerate(events):
        start = _attention_event_time(event) or 0.0
        end = _attention_event_time(events[index + 1]) if index + 1 < len(events) else end_anchor
        end = max(start, end if end is not None else start)
        view_span = _span_for_time(view_spans, start) if _attention_accepts_view_telemetry(event) else None
        if view_span:
            accepted_view_merge_count += 1
        elif view_spans:
            suppressed_view_merge_count += 1
        frontmost = _attention_frontmost(event)
        window = _attention_window(event)
        public_label = _attention_public_label(event, view_span)
        attention_kind = _attention_kind_for_event(event, view_span)
        policy = _attention_policy(attention_kind)
        attention_target = _attention_target_payload(
            event,
            kind=attention_kind,
            view_span=view_span,
            public_label=public_label,
        )
        raw_spans.append({
            "id": f"as_raw_{index:04d}",
            "attention_kind": attention_kind,
            "attention_target": attention_target,
            "privacy": {
                "public_safe_default": bool(policy["public_safe_default"]),
                "post_edit_policy": policy["post_edit_policy"],
                "reason": policy["reason"],
            },
            "public_safe_label": public_label,
            "start_video_t": round(start, 3),
            "end_video_t": round(end, 3),
            "duration_seconds": round(max(0.0, end - start), 3),
            "confidence": event.get("confidence") or ("recorded_display_window" if _attention_on_recorded_display(event) else "frontmost_app_only"),
            "recorded_display_overlap": round(_attention_overlap(event), 4),
            "at_iso": event.get("at_iso"),
            "wall_t_seconds": _safe_float(event.get("wall_t_seconds")),
            "monotonic_seconds": _safe_float(event.get("monotonic_seconds")),
            "capture_target_id": event.get("capture_target_id"),
            "display_id": event.get("display_id"),
            "view_id": (view_span or {}).get("view_id"),
            "view_label": (view_span or {}).get("view_label"),
            "view_span_id": (view_span or {}).get("id"),
            "route": (view_span or {}).get("route"),
            "frontmost_app": {
                "localized_name": frontmost.get("localized_name") or frontmost.get("name"),
                "bundle_identifier": frontmost.get("bundle_identifier") or frontmost.get("bundleIdentifier"),
                "process_identifier": frontmost.get("process_identifier") or frontmost.get("pid"),
            },
            "window": {
                "window_id": window.get("window_id") or window.get("number"),
                "owner_name": window.get("owner_name"),
                "owner_pid": window.get("owner_pid"),
                "public_safe_title": window.get("public_safe_title") or window.get("title_public"),
            },
        })

    spans = _merge_attention_spans(raw_spans)
    payload = {
        "schema": "demo_take_attention_spans_v0",
        "take_id": root.name,
        "created_at": now_iso(),
        "status": "ready" if spans else "no_spans",
        "event_count": len(events),
        "span_count": len(spans),
        "spans": spans,
        "sources": {
            "attention_events": "attention_events.jsonl",
            "view_timeline": "view_timeline.json" if (root / "view_timeline.json").exists() else None,
        },
        "route_telemetry_merge": {
            "policy": "attach view_timeline fields only when attention shows Station/browser-localhost focus on the recorded display",
            "accepted_event_count": accepted_view_merge_count,
            "suppressed_event_count": suppressed_view_merge_count,
        },
    }
    write_json(root / "attention_spans.json", payload)
    return payload


def _span_for_time(spans: list[dict[str, Any]], t: float) -> dict[str, Any] | None:
    for span in spans:
        if span["start_video_t"] <= t < span["end_video_t"]:
            return span
    if spans and t >= spans[-1]["end_video_t"]:
        return spans[-1]
    return None


def _attention_span_for_time(spans: list[dict[str, Any]], t: float) -> dict[str, Any] | None:
    return _span_for_time(spans, t)


def _enrich_word_list(
    words: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    fallback_start: float = 0.0,
) -> int:
    enriched = 0
    for word in words:
        if not isinstance(word, dict):
            continue
        try:
            word_start = float(word.get("start", fallback_start))
        except (TypeError, ValueError):
            word_start = fallback_start
        word_span = _span_for_time(spans, word_start)
        if word_span:
            word["view_id"] = word_span["view_id"]
            word["view_span_id"] = word_span["id"]
            enriched += 1
    return enriched


def _enrich_attention_word_list(
    words: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    fallback_start: float = 0.0,
) -> int:
    enriched = 0
    for word in words:
        if not isinstance(word, dict):
            continue
        start = _safe_float(word.get("start"))
        if start is None:
            start = fallback_start
        span = _attention_span_for_time(spans, start)
        if not span:
            continue
        word["attention_span_id"] = span.get("id")
        word["attention_kind"] = span.get("attention_kind")
        word["attention_label"] = span.get("public_safe_label")
        word["attention_confidence"] = span.get("confidence")
        privacy = span.get("privacy") if isinstance(span.get("privacy"), Mapping) else {}
        word["attention_public_safe"] = privacy.get("public_safe_default")
        word["attention_post_edit_policy"] = privacy.get("post_edit_policy")
        enriched += 1
    return enriched


def enrich_transcript_with_views(root: Path) -> dict[str, Any]:
    transcript_path = root / "transcript" / "transcript.json"
    timeline_path = root / "view_timeline.json"
    if not transcript_path.exists() or not timeline_path.exists():
        return {"status": "skipped", "reason": "missing_transcript_or_timeline"}
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    if transcript.get("status") != "ready":
        return {"status": "skipped", "reason": "transcript_not_ready"}
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    spans = timeline.get("spans", [])
    if not spans:
        return {"status": "skipped", "reason": "no_view_spans"}

    enriched_segments = 0
    enriched_words = 0
    for segment in transcript.get("segments", []):
        start = float(segment.get("start", 0.0))
        span = _span_for_time(spans, start)
        if span:
            segment["view_id"] = span["view_id"]
            segment["view_label"] = span["view_label"]
            segment["view_span_id"] = span["id"]
            enriched_segments += 1
        enriched_words += _enrich_word_list(segment.get("words", []) or [], spans, fallback_start=start)
    enriched_words += _enrich_word_list(transcript.get("words", []) or [], spans)
    transcript["view_enriched_at"] = now_iso()
    write_json(transcript_path, transcript)
    return {
        "status": "ready",
        "enriched_segments": enriched_segments,
        "enriched_words": enriched_words,
        "span_count": len(spans),
    }


def enrich_transcript_with_attention(root: Path) -> dict[str, Any]:
    transcript_path = root / "transcript" / "transcript.json"
    spans_path = root / "attention_spans.json"
    if not transcript_path.exists():
        return {"status": "skipped", "reason": "missing_transcript"}
    if not spans_path.exists():
        if (root / "attention_events.jsonl").exists():
            build_attention_spans(root)
        if not spans_path.exists():
            return {"status": "skipped", "reason": "missing_attention_spans"}
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    if transcript.get("status") != "ready":
        return {"status": "skipped", "reason": "transcript_not_ready"}
    payload = json.loads(spans_path.read_text(encoding="utf-8"))
    spans = payload.get("spans", [])
    if not isinstance(spans, list) or not spans:
        return {"status": "skipped", "reason": "no_attention_spans"}

    enriched_segments = 0
    enriched_words = 0
    for segment in transcript.get("segments", []):
        if not isinstance(segment, dict):
            continue
        start = _safe_float(segment.get("start")) or 0.0
        span = _attention_span_for_time(spans, start)
        if span:
            segment["attention_span_id"] = span.get("id")
            segment["attention_kind"] = span.get("attention_kind")
            segment["attention_label"] = span.get("public_safe_label")
            segment["attention_confidence"] = span.get("confidence")
            privacy = span.get("privacy") if isinstance(span.get("privacy"), Mapping) else {}
            segment["attention_public_safe"] = privacy.get("public_safe_default")
            segment["attention_post_edit_policy"] = privacy.get("post_edit_policy")
            enriched_segments += 1
        enriched_words += _enrich_attention_word_list(segment.get("words", []) or [], spans, fallback_start=start)
    enriched_words += _enrich_attention_word_list(transcript.get("words", []) or [], spans)
    transcript["attention_enriched_at"] = now_iso()
    write_json(transcript_path, transcript)
    return {
        "status": "ready",
        "enriched_segments": enriched_segments,
        "enriched_words": enriched_words,
        "span_count": len(spans),
    }


def build_per_view_segments(root: Path) -> dict[str, Any]:
    transcript_path = root / "transcript" / "transcript.json"
    timeline_path = root / "view_timeline.json"
    if not transcript_path.exists():
        return {"status": "skipped", "reason": "no_transcript"}
    if not timeline_path.exists():
        build_view_timeline(root)
        if not timeline_path.exists():
            return {"status": "skipped", "reason": "no_view_timeline"}
    enrich_result = enrich_transcript_with_views(root)
    if enrich_result.get("status") not in {"ready", "skipped"}:
        return enrich_result
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    spans_by_id = {span["id"]: span for span in timeline.get("spans", [])}

    per_view: dict[str, dict[str, Any]] = {}
    for segment in transcript.get("segments", []):
        span_id = segment.get("view_span_id")
        if not span_id or span_id not in spans_by_id:
            continue
        span = spans_by_id[span_id]
        bucket = per_view.setdefault(span_id, {
            "id": span_id,
            "view_id": span["view_id"],
            "view_label": span["view_label"],
            "route": span["route"],
            "start_video_t": span["start_video_t"],
            "end_video_t": span["end_video_t"],
            "transcript_segments": [],
            "text_parts": [],
        })
        bucket["transcript_segments"].append(segment.get("id"))
        bucket["text_parts"].append(segment.get("text", "").strip())

    rows: list[dict[str, Any]] = []
    for bucket in per_view.values():
        bucket["text"] = " ".join(part for part in bucket["text_parts"] if part)
        del bucket["text_parts"]
        rows.append(bucket)
    rows.sort(key=lambda row: row["start_video_t"])

    payload = {
        "schema": "demo_take_per_view_segments_v0",
        "take_id": root.name,
        "created_at": now_iso(),
        "rows": rows,
        "row_count": len(rows),
    }
    write_json(root / "per_view_segments.json", payload)
    return payload


def _word_float(word: dict[str, Any], key: str) -> float | None:
    try:
        return float(word.get(key))
    except (TypeError, ValueError):
        return None


def _word_view_metadata(
    word: dict[str, Any],
    segment: dict[str, Any],
    spans: list[dict[str, Any]],
) -> dict[str, Any]:
    start = _word_float(word, "start")
    span = _span_for_time(spans, start) if start is not None else None
    return {
        "view_id": word.get("view_id") or segment.get("view_id") or (span or {}).get("view_id"),
        "view_label": word.get("view_label") or segment.get("view_label") or (span or {}).get("view_label"),
        "view_span_id": word.get("view_span_id") or segment.get("view_span_id") or (span or {}).get("id"),
        "route": (span or {}).get("route"),
    }


def _word_attention_metadata(word: dict[str, Any], segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "attention_span_id": word.get("attention_span_id") or segment.get("attention_span_id"),
        "attention_kind": word.get("attention_kind") or segment.get("attention_kind"),
        "attention_label": word.get("attention_label") or segment.get("attention_label"),
        "attention_confidence": word.get("attention_confidence") or segment.get("attention_confidence"),
        "attention_public_safe": word.get("attention_public_safe") if word.get("attention_public_safe") is not None else segment.get("attention_public_safe"),
        "attention_post_edit_policy": word.get("attention_post_edit_policy") or segment.get("attention_post_edit_policy"),
    }


def _flatten_timed_transcript_words(
    transcript: dict[str, Any],
    spans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment in transcript.get("segments", []) if isinstance(transcript.get("segments"), list) else []:
        if not isinstance(segment, dict):
            continue
        segment_words = segment.get("words", [])
        if not isinstance(segment_words, list):
            continue
        for word in segment_words:
            if not isinstance(word, dict):
                continue
            start = _word_float(word, "start")
            end = _word_float(word, "end")
            if start is None or end is None:
                continue
            row = {
                "word": str(word.get("word") or ""),
                "start": round(start, 3),
                "end": round(max(start, end), 3),
                "probability": _word_float(word, "probability"),
                "transcript_segment_id": segment.get("id"),
            }
            row.update(_word_view_metadata(word, segment, spans))
            row.update(_word_attention_metadata(word, segment))
            rows.append(row)

    if rows:
        rows.sort(key=lambda row: (row["start"], row["end"]))
        for index, row in enumerate(rows):
            row["word_index"] = index
        return rows

    flat_words = transcript.get("words")
    if not isinstance(flat_words, list):
        return []
    for word in flat_words:
        if not isinstance(word, dict):
            continue
        start = _word_float(word, "start")
        end = _word_float(word, "end")
        if start is None or end is None:
            continue
        span = _span_for_time(spans, start) if spans else None
        row = {
            "word": str(word.get("word") or ""),
            "start": round(start, 3),
            "end": round(max(start, end), 3),
            "probability": _word_float(word, "probability"),
            "transcript_segment_id": word.get("transcript_segment_id"),
            "view_id": word.get("view_id") or (span or {}).get("view_id"),
            "view_label": word.get("view_label") or (span or {}).get("view_label"),
            "view_span_id": word.get("view_span_id") or (span or {}).get("id"),
            "route": (span or {}).get("route"),
            "attention_span_id": word.get("attention_span_id"),
            "attention_kind": word.get("attention_kind"),
            "attention_label": word.get("attention_label"),
            "attention_confidence": word.get("attention_confidence"),
        }
        rows.append(row)
    rows.sort(key=lambda row: (row["start"], row["end"]))
    for index, row in enumerate(rows):
        row["word_index"] = index
    return rows


def _join_words_for_block(words: list[dict[str, Any]]) -> str:
    text = " ".join(_clean_text(word.get("word", "")) for word in words)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return _clean_text(text)


def _intent_events_in_range(root: Path, start: float, end: float) -> list[dict[str, Any]]:
    path = root / "intent_events.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    events = payload.get("events", [])
    if not isinstance(events, list):
        return []
    matches: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        t = _word_float(event, "video_t_seconds")
        if t is None:
            continue
        if start <= t < end or (start == end and t == start):
            matches.append({
                "id": event.get("id"),
                "kind": event.get("kind"),
                "phrase": event.get("phrase"),
                "video_t_seconds": round(t, 3),
            })
    return matches


def _speech_boundary_reason(
    current_words: list[dict[str, Any]],
    previous_word: dict[str, Any],
    next_word: dict[str, Any],
    *,
    pause_gap_seconds: float,
    max_block_seconds: float,
) -> str | None:
    gap = float(next_word["start"]) - float(previous_word["end"])
    if gap >= pause_gap_seconds:
        return "pause_gap"
    previous_span = previous_word.get("view_span_id")
    next_span = next_word.get("view_span_id")
    if previous_span and next_span and previous_span != next_span:
        return "view_change"
    block_start = float(current_words[0]["start"])
    if float(next_word["end"]) - block_start >= max_block_seconds:
        return "max_duration"
    return None


def _finalize_speech_block(
    root: Path,
    index: int,
    words: list[dict[str, Any]],
    boundary_reason: str,
) -> dict[str, Any]:
    start = float(words[0]["start"])
    end = float(words[-1]["end"])
    segment_ids = sorted({
        str(word.get("transcript_segment_id"))
        for word in words
        if word.get("transcript_segment_id")
    })
    span_ids = []
    for word in words:
        span_id = word.get("view_span_id")
        if span_id and span_id not in span_ids:
            span_ids.append(span_id)
    attention_span_ids = []
    for word in words:
        span_id = word.get("attention_span_id")
        if span_id and span_id not in attention_span_ids:
            attention_span_ids.append(span_id)
    probabilities = [
        float(word["probability"])
        for word in words
        if isinstance(word.get("probability"), (int, float))
    ]
    first = words[0]
    return {
        "id": f"speech_{index:04d}",
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3),
        "duration_seconds": round(max(0.0, end - start), 3),
        "boundary_reason": boundary_reason,
        "text": _join_words_for_block(words),
        "word_count": len(words),
        "word_index_start": words[0].get("word_index"),
        "word_index_end": words[-1].get("word_index"),
        "transcript_segment_ids": segment_ids,
        "view_id": first.get("view_id"),
        "view_label": first.get("view_label"),
        "view_span_id": first.get("view_span_id"),
        "view_span_ids": span_ids,
        "route": first.get("route"),
        "attention_span_id": first.get("attention_span_id"),
        "attention_span_ids": attention_span_ids,
        "attention_kind": first.get("attention_kind"),
        "attention_label": first.get("attention_label"),
        "attention_confidence": first.get("attention_confidence"),
        "attention_public_safe": first.get("attention_public_safe"),
        "attention_post_edit_policy": first.get("attention_post_edit_policy"),
        "avg_word_probability": round(sum(probabilities) / len(probabilities), 4) if probabilities else None,
        "intent_events": _intent_events_in_range(root, start, end),
        "splice": {
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "handle_seconds": 0.12,
            "source": "word_timestamp_block",
        },
        "words": [
            {
                "word": word.get("word"),
                "start": word.get("start"),
                "end": word.get("end"),
                "probability": word.get("probability"),
                "attention_span_id": word.get("attention_span_id"),
            }
            for word in words
        ],
    }


def build_speech_blocks(
    root: Path,
    *,
    pause_gap_seconds: float = DEFAULT_SPEECH_BLOCK_PAUSE_SECONDS,
    max_block_seconds: float = DEFAULT_SPEECH_BLOCK_MAX_SECONDS,
) -> dict[str, Any]:
    transcript_path = root / "transcript" / "transcript.json"
    if not transcript_path.exists():
        payload = {
            "schema": "demo_take_speech_blocks_v0",
            "take_id": root.name,
            "created_at": now_iso(),
            "status": "no_transcript",
            "blocks": [],
            "block_count": 0,
        }
        write_json(root / "speech_blocks.json", payload)
        return payload
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    if transcript.get("status") != "ready":
        payload = {
            "schema": "demo_take_speech_blocks_v0",
            "take_id": root.name,
            "created_at": now_iso(),
            "status": "transcript_not_ready",
            "transcript_status": transcript.get("status"),
            "blocks": [],
            "block_count": 0,
        }
        write_json(root / "speech_blocks.json", payload)
        return payload

    timeline_path = root / "view_timeline.json"
    if not timeline_path.exists():
        build_view_timeline(root)
    enrich_transcript_with_views(root)
    if (root / "attention_events.jsonl").exists() and not (root / "attention_spans.json").exists():
        build_attention_spans(root)
    enrich_transcript_with_attention(root)
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8")) if timeline_path.exists() else {}
    spans = timeline.get("spans", []) if isinstance(timeline.get("spans"), list) else []
    timed_words = _flatten_timed_transcript_words(transcript, spans)
    if not timed_words:
        payload = {
            "schema": "demo_take_speech_blocks_v0",
            "take_id": root.name,
            "created_at": now_iso(),
            "status": "no_timestamped_words",
            "blocks": [],
            "block_count": 0,
            "notes": {
                "reason": "Speech blocks require word-level start/end timestamps."
            },
        }
        write_json(root / "speech_blocks.json", payload)
        return payload

    blocks: list[dict[str, Any]] = []
    current_words: list[dict[str, Any]] = [timed_words[0]]
    current_reason = "take_start"
    for word in timed_words[1:]:
        reason = _speech_boundary_reason(
            current_words,
            current_words[-1],
            word,
            pause_gap_seconds=pause_gap_seconds,
            max_block_seconds=max_block_seconds,
        )
        if reason:
            blocks.append(_finalize_speech_block(root, len(blocks), current_words, current_reason))
            current_words = [word]
            current_reason = reason
        else:
            current_words.append(word)
    blocks.append(_finalize_speech_block(root, len(blocks), current_words, current_reason))

    payload = {
        "schema": "demo_take_speech_blocks_v0",
        "take_id": root.name,
        "created_at": now_iso(),
        "status": "ready" if blocks else "no_blocks",
        "thresholds": {
            "pause_gap_seconds": pause_gap_seconds,
            "max_block_seconds": max_block_seconds,
        },
        "source": {
            "transcript": "transcript/transcript.json",
            "view_timeline": "view_timeline.json" if timeline_path.exists() else None,
            "attention_spans": "attention_spans.json" if (root / "attention_spans.json").exists() else None,
            "intent_events": "intent_events.json" if (root / "intent_events.json").exists() else None,
        },
        "word_count": len(timed_words),
        "block_count": len(blocks),
        "blocks": blocks,
        "notes": {
            "edit_contract": "Blocks are contiguous spoken-word spans split by silence, view changes, or max duration. Use splice.start_seconds/end_seconds for rough clip cuts.",
        },
    }
    write_json(root / "speech_blocks.json", payload)
    return payload


def _visual_index_duration_floor(root: Path) -> float | None:
    visual = _read_json_dict(root / "visual_index.json")
    frames = visual.get("frames") if isinstance(visual.get("frames"), list) else []
    values: list[float] = []
    for frame in frames:
        if not isinstance(frame, Mapping):
            continue
        value = _timeline_seconds(frame.get("timestamp_seconds"))
        if value is not None:
            values.append(value)
    return max(values) if values else None


def _semantic_duration_floor(root: Path, speech_blocks: Mapping[str, Any]) -> float | None:
    candidates: list[float] = []
    active_timeline = _read_json_dict(root / "active_timeline.json")
    transcript = _read_json_dict(root / "transcript" / "transcript.json")
    for value in (
        active_timeline.get("duration_seconds"),
        transcript.get("duration_seconds"),
        _visual_index_duration_floor(root),
    ):
        parsed = _timeline_seconds(value)
        if parsed is not None:
            candidates.append(parsed)
    for block in speech_blocks.get("blocks") or []:
        if isinstance(block, Mapping):
            parsed = _timeline_seconds(block.get("end_seconds"))
            if parsed is not None:
                candidates.append(parsed)
    return max(candidates) if candidates else None


def _copy_semantic_frame(
    root: Path,
    *,
    section_id: str,
    role: str,
    timestamp: float,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    nearest = _nearest_visual_frames(root, timestamp, limit=1)
    frames_dir = root / "frames" / "semantic"
    frames_dir.mkdir(parents=True, exist_ok=True)
    safe_section = _safe_marker_frame_stem(section_id).lower()
    safe_role = _safe_marker_frame_stem(role).lower()
    if nearest:
        source_rel = str(nearest[0].get("relative_path") or "")
        source_path = root / source_rel
        suffix = source_path.suffix.lower() if source_path.suffix else ".jpg"
        target = frames_dir / f"{safe_section}_{safe_role}{suffix}"
        if source_path.exists():
            try:
                if source_path.resolve() != target.resolve():
                    shutil.copy2(source_path, target)
            except OSError:
                return {
                    "role": role,
                    "t": round(timestamp, 3),
                    "path": source_rel,
                    "source": "nearest_visual_index_frame",
                    "copy_status": "failed",
                    "time_error_seconds": nearest[0].get("time_error_seconds"),
                }
            return {
                "role": role,
                "t": round(timestamp, 3),
                "path": relative(root, target),
                "source": "nearest_visual_index_frame",
                "source_path": source_rel,
                "source_timestamp_seconds": nearest[0].get("timestamp_seconds"),
                "time_error_seconds": nearest[0].get("time_error_seconds"),
            }
    if config and _is_fake_capture(dict(config)):
        target = frames_dir / f"{safe_section}_{safe_role}.jpg"
        target.write_bytes(f"fake semantic frame {section_id} {role}\n".encode("utf-8"))
        return {
            "role": role,
            "t": round(timestamp, 3),
            "path": relative(root, target),
            "source": "fake_semantic_frame",
        }
    return None


def _semantic_frame_refs(
    root: Path,
    *,
    section_id: str,
    points: list[tuple[str, float]],
    config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for role, timestamp in points:
        if role in seen_roles:
            continue
        seen_roles.add(role)
        ref = _copy_semantic_frame(
            root,
            section_id=section_id,
            role=role,
            timestamp=max(0.0, float(timestamp)),
            config=config,
        )
        if ref:
            refs.append(ref)
    return refs


def _semantic_activity_refs(root: Path, start: float, end: float) -> list[dict[str, Any]]:
    active = _read_json_dict(root / "active_timeline.json")
    refs: list[dict[str, Any]] = []
    for event in active.get("events") or []:
        if not isinstance(event, Mapping):
            continue
        t = _timeline_seconds(event.get("active_time_seconds"))
        if t is None or t < start or t > end:
            continue
        refs.append({
            "id": event.get("id"),
            "kind": event.get("kind"),
            "t": round(t, 3),
            "label": event.get("label"),
        })
    return refs


def _semantic_speech_section(
    root: Path,
    index: int,
    block: Mapping[str, Any],
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    start = _timeline_seconds(block.get("start_seconds"))
    end = _timeline_seconds(block.get("end_seconds"))
    if start is None or end is None or end <= start:
        return None
    section_id = f"sec_{index:04d}"
    section = {
        "id": section_id,
        "kind": "speech",
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3),
        "duration_seconds": round(end - start, 3),
        "text": str(block.get("text") or ""),
        "source": "speech_blocks",
        "speech_block_id": block.get("id"),
        "transcript_segment_ids": block.get("transcript_segment_ids")
        if isinstance(block.get("transcript_segment_ids"), list)
        else [],
        "view_id": block.get("view_id"),
        "view_label": block.get("view_label"),
        "attention_span_id": block.get("attention_span_id"),
        "attention_kind": block.get("attention_kind"),
        "attention_public_safe": block.get("attention_public_safe"),
        "intent_events": block.get("intent_events") if isinstance(block.get("intent_events"), list) else [],
        "frame_refs": [],
    }
    return section


def _semantic_silence_sections(
    root: Path,
    *,
    start: float,
    end: float,
    next_index: int,
    config: Mapping[str, Any] | None = None,
    max_seconds: float = DEFAULT_SEMANTIC_SILENCE_MAX_SECONDS,
) -> list[dict[str, Any]]:
    if end - start < DEFAULT_SEMANTIC_SILENCE_MIN_SECONDS:
        return []
    sections: list[dict[str, Any]] = []
    cursor = start
    while cursor < end - DEFAULT_SEMANTIC_SILENCE_MIN_SECONDS:
        chunk_end = min(end, cursor + max_seconds)
        if end - chunk_end < DEFAULT_SEMANTIC_SILENCE_MIN_SECONDS:
            chunk_end = end
        section_id = f"sec_{next_index + len(sections):04d}"
        mid = cursor + ((chunk_end - cursor) / 2.0)
        sections.append({
            "id": section_id,
            "kind": "silence",
            "start_seconds": round(cursor, 3),
            "end_seconds": round(chunk_end, 3),
            "duration_seconds": round(chunk_end - cursor, 3),
            "text": "",
            "source": "speech_gap",
            "activity_refs": _semantic_activity_refs(root, cursor, chunk_end),
            "frame_refs": _semantic_frame_refs(
                root,
                section_id=section_id,
                points=[("mid", mid)],
                config=config,
            ),
        })
        cursor = chunk_end
    return sections


def build_semantic_proxy(root: Path) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    speech_blocks = _read_json_dict(root / "speech_blocks.json")
    if speech_blocks.get("schema") != "demo_take_speech_blocks_v0":
        speech_blocks = build_speech_blocks(root)
    duration = _semantic_duration_floor(root, speech_blocks)

    sections: list[dict[str, Any]] = []
    speech_sections: list[dict[str, Any]] = []
    for block in speech_blocks.get("blocks") or []:
        if not isinstance(block, Mapping):
            continue
        section = _semantic_speech_section(root, len(speech_sections) + 1, block, config=config)
        if section:
            speech_sections.append(section)
    speech_sections.sort(key=lambda row: (float(row["start_seconds"]), str(row["id"])))

    next_index = 1
    cursor = 0.0
    for speech in speech_sections:
        start = float(speech["start_seconds"])
        end = float(speech["end_seconds"])
        silence = _semantic_silence_sections(
            root,
            start=cursor,
            end=start,
            next_index=next_index,
            config=config,
        )
        sections.extend(silence)
        next_index += len(silence)
        speech["id"] = f"sec_{next_index:04d}"
        # Re-copy refs under the final stable section id.
        mid = start + ((end - start) / 2.0)
        speech["frame_refs"] = _semantic_frame_refs(
            root,
            section_id=str(speech["id"]),
            points=[("start", start), ("mid", mid), ("end", max(start, end - 0.001))],
            config=config,
        )
        sections.append(speech)
        next_index += 1
        cursor = max(cursor, end)
    if duration is not None and duration > cursor:
        tail = _semantic_silence_sections(
            root,
            start=cursor,
            end=duration,
            next_index=next_index,
            config=config,
        )
        sections.extend(tail)

    status = "ready" if sections else str(speech_blocks.get("status") or "no_sections")
    payload = {
        "schema": "demo_take_semantic_proxy_v0",
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "status": status,
        "duration_seconds": round(duration, 3) if duration is not None else None,
        "section_count": len(sections),
        "speech_section_count": sum(1 for row in sections if row.get("kind") == "speech"),
        "silence_section_count": sum(1 for row in sections if row.get("kind") == "silence"),
        "sections": sections,
        "sources": {
            "speech_blocks": "speech_blocks.json" if (root / "speech_blocks.json").exists() else None,
            "transcript": "transcript/transcript.json" if (root / "transcript" / "transcript.json").exists() else None,
            "visual_index": "visual_index.json" if (root / "visual_index.json").exists() else None,
            "active_timeline": "active_timeline.json" if (root / "active_timeline.json").exists() else None,
        },
        "frame_policy": "copy_nearest_existing_visual_index_frame_to_frames_semantic",
        "notes": {
            "custody_boundary": "Semantic proxy is local inspection evidence. Source video authority remains local raw media until a verified cloud archive receipt exists.",
            "silence_contract": "Intervals without transcript words are typed silence sections rather than omitted gaps.",
        },
    }
    write_json(root / "semantic_proxy.json", payload)
    return payload


def build_multimodal_index(root: Path) -> dict[str, Any]:
    if not DEMO_TAKE_INDEX_SCRIPT.exists():
        return {
            "status": "skipped",
            "reason": "demo_take_index_script_missing",
            "script": str(DEMO_TAKE_INDEX_SCRIPT),
        }
    command = [
        sys.executable,
        str(DEMO_TAKE_INDEX_SCRIPT),
        "build",
        root.name,
        "--takes-root",
        str(root.parent),
    ]
    proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {
            "status": "failed",
            "command": " ".join(command),
            "exit_code": proc.returncode,
            "stderr_tail": proc.stderr.strip()[-1200:],
            "stdout_tail": proc.stdout.strip()[-1200:],
        }
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {"stdout_tail": proc.stdout.strip()[-1200:]}
    outputs = payload.get("outputs", {}) if isinstance(payload, dict) else {}
    return {
        "status": "ready",
        "command": " ".join(command),
        "outputs": outputs,
    }


def build_intent_events(root: Path) -> dict[str, Any]:
    transcript_path = root / "transcript" / "transcript.json"
    if not transcript_path.exists():
        payload = {
            "schema": "demo_take_intent_events_v0",
            "take_id": root.name,
            "created_at": now_iso(),
            "status": "no_transcript",
            "events": [],
            "event_count": 0,
        }
        write_json(root / "intent_events.json", payload)
        return payload

    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    if transcript.get("status") != "ready":
        payload = {
            "schema": "demo_take_intent_events_v0",
            "take_id": root.name,
            "created_at": now_iso(),
            "status": "transcript_not_ready",
            "transcript_status": transcript.get("status"),
            "events": [],
            "event_count": 0,
        }
        write_json(root / "intent_events.json", payload)
        return payload

    candidates: list[dict[str, Any]] = []
    view_spans_by_id = _load_view_span_index(root)
    for segment in transcript.get("segments", []):
        if not isinstance(segment, dict):
            continue
        text = _clean_transcript_text(segment.get("text", ""))
        if not text:
            continue
        for rule in _INTENT_RULES:
            pattern = rule["pattern"]
            for match in pattern.finditer(text):
                raw_phrase = _clean_text(match.group(0))
                payload: dict[str, Any] = {}
                label = match.groupdict().get("label")
                verdict = match.groupdict().get("verdict")
                if label:
                    payload["label"] = _trim_intent_payload(label)
                if verdict:
                    payload["verdict"] = _clean_text(verdict).replace(" ", "_").lower()
                if rule.get("privacy_flag"):
                    payload["privacy_review_required"] = True
                phrase = _intent_phrase(rule, payload, raw_phrase)
                candidates.append(
                    {
                        "_match_start": match.start(),
                        "kind": rule["kind"],
                        "command": rule["command"],
                        "phrase": phrase,
                        "payload": payload,
                        "video_t_seconds": round(_event_time_from_segment(segment, phrase), 3),
                        "transcript_segment_id": segment.get("id"),
                        "view_id": segment.get("view_id"),
                        "view_label": segment.get("view_label"),
                        "view_span_id": segment.get("view_span_id"),
                        "text": text,
                    }
                )
        candidates.extend(_feedback_events_from_segment(root, transcript_path, segment, text, view_spans_by_id))

    candidates.sort(key=lambda event: (float(event.get("video_t_seconds") or 0.0), int(event.get("_match_start") or 0)))
    events: list[dict[str, Any]] = []
    for index, event in enumerate(candidates):
        event.pop("_match_start", None)
        event["id"] = f"intent_{index:04d}"
        events.append(event)

    payload = {
        "schema": "demo_take_intent_events_v0",
        "take_id": root.name,
        "created_at": now_iso(),
        "status": "ready" if events else "no_events",
        "event_count": len(events),
        "events": events,
        "notes": {
            "source": "transcript/transcript.json",
            "protocol": "docs/dissemination/first_take_protocol_v0.md",
            "time_origin": "Each event uses the matched word start when available, otherwise the transcript segment start.",
        },
    }
    write_json(root / "intent_events.json", payload)
    return payload


def _transcription_audio_track_ready(root: Path, tracks: list[dict[str, Any]]) -> bool:
    mic_track = next((track for track in tracks if track.get("role") == "microphone"), None)
    if not mic_track:
        return False
    rel_path = mic_track.get("relative_path")
    if not isinstance(rel_path, str) or not rel_path:
        return False
    return (root / rel_path).exists()


def _can_reuse_prepared_transcription_tracks(
    root: Path,
    session: dict[str, Any],
    tracks: list[dict[str, Any]],
) -> bool:
    if not _transcription_audio_track_ready(root, tracks):
        return False
    media_segments = [segment for segment in session.get("media_segments", []) if isinstance(segment, Mapping)]
    if len(media_segments) <= 1:
        return True
    mic_track = next((track for track in tracks if track.get("role") == "microphone"), None)
    rel_path = str((mic_track or {}).get("relative_path") or "")
    return bool((mic_track or {}).get("splice_source_tracks")) or rel_path.startswith("tracks/spliced/")


def prepared_tracks_for_existing_transcription(
    root: Path,
    config: dict[str, Any],
    session: dict[str, Any],
    failures: list[str],
) -> list[dict[str, Any]]:
    tracks = [dict(track) for track in session.get("tracks", []) if isinstance(track, Mapping)]
    if _can_reuse_prepared_transcription_tracks(root, session, tracks):
        return tracks
    return prepare_segment_tracks(root, config, session, failures)


def refresh_transcript_derived_outputs(
    root: Path,
    session: dict[str, Any],
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str],
) -> dict[str, Any]:
    transcript = _read_json_dict(root / "transcript" / "transcript.json")
    if transcript.get("status") != "ready":
        return {"status": "skipped", "reason": "transcript_not_ready"}

    outputs: dict[str, Any] = {}
    take_id = str(session.get("take_id") or root.name)
    markers = list(session.get("markers", []))

    append_postprocess_progress(root, "voice_scan", "running", "Scanning transcript for voice marker phrases")
    voice_result = voice_scan(root)
    outputs["voice_scan"] = voice_result
    append_postprocess_progress(
        root,
        "voice_scan",
        "pass" if voice_result.get("status") == "ready" else "warn",
        "Voice marker scan complete",
        voice_result,
    )
    if voice_result.get("status") == "ready" and voice_result.get("matched_count", 0):
        session = _read_json_dict(root / "session.json")
        markers = list(session.get("markers", markers))

    append_postprocess_progress(root, "view_timeline", "running", "Building view timeline from telemetry")
    view_timeline = build_view_timeline(root)
    outputs["view_timeline"] = {
        "status": view_timeline.get("status"),
        "event_count": view_timeline.get("event_count"),
    }
    append_postprocess_progress(
        root,
        "view_timeline",
        "pass" if view_timeline.get("status") == "ready" else "warn",
        "View timeline built",
        outputs["view_timeline"],
    )

    append_postprocess_progress(root, "attention_spans", "running", "Building recorded-screen attention spans")
    attention_spans = build_attention_spans(root)
    outputs["attention_spans"] = {
        "status": attention_spans.get("status"),
        "event_count": attention_spans.get("event_count"),
        "span_count": attention_spans.get("span_count"),
    }
    append_postprocess_progress(
        root,
        "attention_spans",
        "pass" if attention_spans.get("status") == "ready" else "warn",
        "Attention spans built" if attention_spans.get("status") == "ready" else "Attention events unavailable",
        outputs["attention_spans"],
    )

    outputs["transcript_view_enrichment"] = enrich_transcript_with_views(root)
    outputs["transcript_attention_enrichment"] = enrich_transcript_with_attention(root)

    append_postprocess_progress(root, "per_view_segments", "running", "Building per-view narration segments")
    per_view = build_per_view_segments(root)
    outputs["per_view_segments"] = {
        "status": per_view.get("status", "ready"),
        "row_count": per_view.get("row_count"),
    }
    append_postprocess_progress(
        root,
        "per_view_segments",
        "pass",
        "Per-view narration segments built",
        outputs["per_view_segments"],
    )

    append_postprocess_progress(root, "intent_events", "running", "Building spoken-control intent events")
    intent_events = build_intent_events(root)
    outputs["intent_events"] = {
        "status": intent_events.get("status"),
        "event_count": intent_events.get("event_count"),
    }
    append_postprocess_progress(
        root,
        "intent_events",
        "pass" if intent_events.get("status") in {"ready", "no_events"} else "warn",
        "Intent events built",
        outputs["intent_events"],
    )

    append_postprocess_progress(root, "speech_blocks", "running", "Building spoken-word splice blocks")
    speech_blocks = build_speech_blocks(root)
    outputs["speech_blocks"] = {
        "status": speech_blocks.get("status"),
        "block_count": speech_blocks.get("block_count"),
    }
    append_postprocess_progress(
        root,
        "speech_blocks",
        "pass" if speech_blocks.get("status") == "ready" else "warn",
        "Speech blocks built" if speech_blocks.get("status") == "ready" else "Speech blocks unavailable",
        outputs["speech_blocks"],
    )

    append_postprocess_progress(root, "edl", "running", "Rebuilding marker-derived EDL")
    write_edl(root, take_id, tracks, markers)
    outputs["edl"] = {"status": "ready", "marker_count": len(markers)}
    append_postprocess_progress(root, "edl", "pass", "EDL rebuilt", outputs["edl"])

    append_postprocess_progress(root, "otio_export", "running", "Projecting EDL to OpenTimelineIO format")
    write_edl_otio(root, take_id, tracks, markers)
    otio_present = (root / "edl.otio").exists()
    outputs["otio_export"] = {
        "status": "ready" if otio_present else "missing",
        "output": "edl.otio" if otio_present else None,
    }
    append_postprocess_progress(
        root,
        "otio_export",
        "pass" if otio_present else "warn",
        "OTIO timeline written" if otio_present else "OTIO timeline missing",
        outputs["otio_export"],
    )

    append_postprocess_progress(root, "active_timeline", "running", "Projecting active timeline markers and chapters")
    active_timeline = write_active_timeline_projection(root, config, session, tracks, failures)
    outputs["active_timeline"] = {
        "event_count": active_timeline.get("event_count"),
        "checkpoint_count": active_timeline.get("checkpoint_count"),
        "pause_gap_count": active_timeline.get("pause_gap_count"),
    }
    append_postprocess_progress(root, "active_timeline", "pass", "Active timeline projected", outputs["active_timeline"])

    append_postprocess_progress(root, "semantic_proxy", "running", "Building transcript/silence semantic proxy")
    semantic_proxy = build_semantic_proxy(root)
    outputs["semantic_proxy"] = {
        "status": semantic_proxy.get("status"),
        "section_count": semantic_proxy.get("section_count"),
        "speech_section_count": semantic_proxy.get("speech_section_count"),
        "silence_section_count": semantic_proxy.get("silence_section_count"),
    }
    append_postprocess_progress(
        root,
        "semantic_proxy",
        "pass" if semantic_proxy.get("status") == "ready" else "warn",
        "Semantic inspection proxy ready" if semantic_proxy.get("status") == "ready" else "Semantic inspection proxy unavailable",
        outputs["semantic_proxy"],
    )

    append_postprocess_progress(root, "multimodal_index", "running", "Building editor-facing multimodal index")
    multimodal_index = build_multimodal_index(root)
    outputs["multimodal_index"] = {
        "status": multimodal_index.get("status"),
        "outputs": multimodal_index.get("outputs"),
    }
    append_postprocess_progress(
        root,
        "multimodal_index",
        "pass" if multimodal_index.get("status") == "ready" else "warn",
        "Multimodal editor index built" if multimodal_index.get("status") == "ready" else "Multimodal editor index unavailable",
        outputs["multimodal_index"],
    )
    return {"status": "ready", "outputs": outputs}


def transcribe_existing(
    root: Path,
    binary_override: str | None,
    model_override: str | None,
    language_override: str | None,
    provider_override: str | None = None,
    whisper_cpp_binary_override: str | None = None,
    whisper_cpp_model_override: str | None = None,
) -> dict[str, Any]:
    session = json.loads((root / "session.json").read_text(encoding="utf-8"))
    config = dict(session.get("config", {}))
    if binary_override:
        config["transcribe_binary"] = binary_override
    if model_override:
        config["transcribe_model"] = model_override
    if language_override:
        config["transcribe_language"] = language_override
    if provider_override:
        config["transcribe_provider"] = provider_override
    if whisper_cpp_binary_override:
        config["whisper_cpp_binary"] = whisper_cpp_binary_override
    if whisper_cpp_model_override:
        config["whisper_cpp_model"] = whisper_cpp_model_override
    failures: list[str] = list(session.get("known_failures", []))
    tracks = prepared_tracks_for_existing_transcription(root, config, session, failures)
    session["tracks"] = tracks
    result = transcribe_track(root, config, tracks, failures)
    write_media_timeline_receipt(root, config, session, tracks, failures)
    write_active_timeline_projection(root, config, session, tracks, failures)
    session["known_failures"] = list(dict.fromkeys(failures))
    write_json(root / "session.json", session)
    write_timeline_sync_receipt(root)
    derived_outputs = {"status": "skipped", "reason": "transcript_not_ready"}
    if result.get("status") == "ready":
        derived_outputs = refresh_transcript_derived_outputs(root, session, config, tracks, failures)
        session = _read_json_dict(root / "session.json")
        session["tracks"] = tracks
        session["known_failures"] = list(dict.fromkeys(failures))
        write_json(root / "session.json", session)
    manifest_path = root / "manifest.json"
    manifest_state = "review_ready"
    if manifest_path.exists():
        try:
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_state = str(existing_manifest.get("recording_state") or manifest_state)
        except (OSError, json.JSONDecodeError):
            pass
    if result.get("status") == "ready":
        manifest_state = "package_ready"
    if "repo_root" in config and "ffmpeg_path" in config and "screenshot_interval_seconds" in config:
        write_json(
            manifest_path,
            manifest(
                session.get("take_id", root.name),
                root,
                manifest_state,
                config,
                tracks,
                session["known_failures"],
                markers=session.get("markers", []),
                pause_events=session.get("pause_events", []),
                media_segments=session.get("media_segments", []),
            ),
        )

    status = str(result.get("status") or "unknown")
    if status == "ready":
        summary = "Transcript ready."
    else:
        summary = f"Transcript unavailable: {result.get('reason') or status}."
    return {
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "statusLines": [summary],
        "knownFailures": session["known_failures"],
        "result": result,
        "derivedOutputs": derived_outputs,
    }


def append_postprocess_progress(
    root: Path,
    stage: str,
    status: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "schema": "demo_take_postprocess_progress_event_v0",
        "at": now_iso(),
        "stage": stage,
        "status": status,
        "message": message,
    }
    if detail:
        event["detail"] = detail
    with (root / "postprocess_progress.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def enqueue_storage_spillway_after_finalize(root: Path, failures: list[str]) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    config = session.get("config") if isinstance(session.get("config"), Mapping) else {}
    if _is_fake_capture(dict(config)):
        append_postprocess_progress(
            root,
            "storage_spillway_enqueue",
            "skipped",
            "Storage spillway enqueue skipped for fake capture fixture",
            {"reason": "fake_capture_fixture_no_external_io"},
        )
        return {
            "schema": "demo_take_storage_spillway_enqueue_v0",
            "status": "skipped",
            "reason": "fake_capture_fixture_no_external_io",
        }
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from tools.meta.storage_spillway import enqueue_path

        item = enqueue_path(
            root,
            adapter="demo_take",
            reason="recorder_finalize",
            source="demo_take_capture",
        )
        append_postprocess_progress(
            root,
            "storage_spillway_enqueue",
            "pass",
            "Storage spillway queue item recorded",
            {"item_id": item.get("item_id"), "status": item.get("status")},
        )
        return {
            "schema": "demo_take_storage_spillway_enqueue_v0",
            "status": "queued",
            "item_id": item.get("item_id"),
            "queue_status": item.get("status"),
        }
    except Exception as exc:
        message = f"Storage spillway enqueue failed: {exc}"
        failures.append(message)
        append_postprocess_progress(root, "storage_spillway_enqueue", "warn", message)
        return {
            "schema": "demo_take_storage_spillway_enqueue_v0",
            "status": "failed",
            "known_failures": [message],
        }


def _is_recomputed_review_failure(message: Any) -> bool:
    text = str(message)
    return (
        text == "Rough render failed; see logs/rough_render.log."
        or text.startswith("Cannot build MP3 review audio because ")
        or text == "MP3 review audio export failed; see logs/review_audio.log."
        or "screen-only review video will be used" in text
        or text.startswith("Paused recording segment splice failed for ")
        or text.startswith("Webcam track shorter than ")
        or text.startswith("Webcam track missing for ")
        or text.startswith("Webcam placeholder generation failed for ")
        or text.startswith("Timeline failed: ")
    )


def _segment_track_path(root: Path, track: Mapping[str, Any] | None) -> Path | None:
    if not isinstance(track, Mapping):
        return None
    rel_path = track.get("relative_path")
    if not rel_path:
        return None
    path = root / str(rel_path)
    try:
        if path.exists() and path.stat().st_size > 0:
            return path
    except OSError:
        return None
    return None


def _concat_file_text(paths: list[Path]) -> str:
    rows: list[str] = []
    for path in paths:
        escaped = str(path.resolve()).replace("'", "'\\''")
        rows.append(f"file '{escaped}'")
    return "\n".join(rows) + "\n"


def _concat_media_segments(
    root: Path,
    config: dict[str, Any],
    paths: list[Path],
    output: Path,
    *,
    log_name: str,
    failures: list[str],
) -> bool:
    if len(paths) < 2:
        return False
    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg:
        failures.append(f"Cannot splice paused recording segments for {output.name}: ffmpeg path missing.")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output.with_suffix(output.suffix + ".concat.txt")
    output_tmp = output.with_name(output.stem + ".tmp" + output.suffix)
    log_path = root / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    concat_file.write_text(_concat_file_text(paths), encoding="utf-8")
    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass

    command = [
        str(ffmpeg),
        "-hide_banner",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(output_tmp),
    ]
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"segment splice unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status == 0 and output_tmp.exists():
        os.replace(output_tmp, output)
        return True

    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    failures.append(f"Paused recording segment splice failed for {output.name}; see logs/{log_name}.")
    return False


def _ffprobe_path(config: dict[str, Any]) -> str | None:
    override = os.environ.get("FFPROBE_PATH")
    if override:
        path = Path(override)
        if path.exists() and os.access(str(path), os.X_OK):
            return str(path)
    ffmpeg = config.get("ffmpeg_path")
    if ffmpeg:
        sibling = Path(str(ffmpeg)).with_name("ffprobe")
        if sibling.exists() and os.access(str(sibling), os.X_OK):
            return str(sibling)
    found = shutil.which("ffprobe")
    if found:
        return found
    for candidate in COMMON_FFPROBE_PATHS:
        if candidate.exists() and os.access(str(candidate), os.X_OK):
            return str(candidate)
    return None


def probe_media_duration_seconds(config: dict[str, Any], path: Path) -> float | None:
    ffprobe = _ffprobe_path(config)
    if not ffprobe or not path.exists():
        return None
    command = [
        ffprobe,
        "-hide_banner",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(getattr(proc, "stdout", "") or "{}")
        duration = payload.get("format", {}).get("duration")
        if duration is None:
            return None
        value = float(duration)
        return value if value > 0 else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _probe_media_container(config: dict[str, Any], path: Path) -> dict[str, Any]:
    ffprobe = _ffprobe_path(config)
    if not path.exists():
        return {"status": "missing", "exists": False}
    if not ffprobe:
        return {"status": "unavailable", "exists": True, "reason": "ffprobe_not_found"}
    command = [
        ffprobe,
        "-hide_banner",
        "-v",
        "error",
        "-show_entries",
        (
            "format=duration,size,start_time:"
            "stream=index,codec_type,codec_name,time_base,start_time,duration,"
            "width,height,avg_frame_rate,r_frame_rate,nb_frames"
        ),
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "fail", "exists": True, "error": str(exc)}
    if proc.returncode != 0:
        return {
            "status": "fail",
            "exists": True,
            "exit_code": proc.returncode,
            "stderr": (getattr(proc, "stderr", "") or "").strip()[-1200:],
        }
    try:
        payload = json.loads(getattr(proc, "stdout", "") or "{}")
    except json.JSONDecodeError as exc:
        return {"status": "fail", "exists": True, "error": f"invalid ffprobe json: {exc}"}
    fmt = payload.get("format") if isinstance(payload.get("format"), Mapping) else {}
    streams: list[dict[str, Any]] = []
    for stream in payload.get("streams") or []:
        if not isinstance(stream, Mapping):
            continue
        streams.append({
            "index": stream.get("index"),
            "codec_type": stream.get("codec_type"),
            "codec_name": stream.get("codec_name"),
            "time_base": stream.get("time_base"),
            "start_time": _timeline_seconds(stream.get("start_time")),
            "duration_seconds": _timeline_seconds(stream.get("duration")),
            "width": stream.get("width"),
            "height": stream.get("height"),
            "avg_frame_rate": stream.get("avg_frame_rate"),
            "r_frame_rate": stream.get("r_frame_rate"),
            "nb_frames": stream.get("nb_frames"),
        })
    duration = _timeline_seconds(fmt.get("duration"))
    return {
        "status": "pass" if duration is not None and duration > 0 else "fail",
        "exists": True,
        "duration_seconds": round(duration, 6) if duration is not None else None,
        "size_bytes": int(fmt["size"]) if str(fmt.get("size") or "").isdigit() else None,
        "start_time": _timeline_seconds(fmt.get("start_time")),
        "stream_count": len(streams),
        "streams": streams,
    }


def _stable_json_digest(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _path_state_signature(root: Path, path: Path) -> dict[str, Any]:
    stat = _safe_stat(path)
    try:
        rel = relative(root, path)
    except ValueError:
        rel = str(path)
    return {
        "relative_path": rel,
        "exists": bool(stat and path.is_file()),
        "bytes": stat.st_size if stat else None,
        "mtime_ns": stat.st_mtime_ns if stat else None,
    }


def _receipt_safe_name(relative_path: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "__", relative_path).strip("._")
    return text[:180] or "generated_media"


def _generated_media_receipt_path(root: Path, output: Path) -> Path:
    try:
        rel = relative(root, output)
    except ValueError:
        rel = output.name
    return root / GENERATED_MEDIA_RECEIPTS_DIR / f"{_receipt_safe_name(rel)}.json"


def _media_build_signature(
    root: Path,
    *,
    stage: str,
    output: Path,
    inputs: list[Path],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "command_version": GENERATED_MEDIA_COMMAND_VERSION,
        "stage": stage,
        "output": _path_state_signature(root, output).get("relative_path"),
        "inputs": [_path_state_signature(root, path) for path in inputs],
        "params": dict(params),
    }
    payload["digest"] = _stable_json_digest(payload)
    return payload


def _read_matching_generated_media_receipt(root: Path, output: Path, signature: Mapping[str, Any]) -> dict[str, Any] | None:
    if not output.exists():
        return None
    receipt = _read_json_dict(_generated_media_receipt_path(root, output))
    if receipt.get("schema") != GENERATED_MEDIA_RECEIPT_SCHEMA:
        return None
    if receipt.get("status") != "ready":
        return None
    if receipt.get("signature", {}).get("digest") != signature.get("digest"):
        return None
    output_state = _path_state_signature(root, output)
    recorded_state = receipt.get("output_state") if isinstance(receipt.get("output_state"), Mapping) else {}
    if recorded_state.get("bytes") != output_state.get("bytes"):
        return None
    if recorded_state.get("mtime_ns") != output_state.get("mtime_ns"):
        return None
    envelope = receipt.get("envelope") if isinstance(receipt.get("envelope"), Mapping) else {}
    if envelope.get("status") == "fail":
        return None
    return receipt


def _video_stream_row(probe: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for stream in probe.get("streams") or []:
        if isinstance(stream, Mapping) and stream.get("codec_type") == "video":
            return stream
    return None


def _generated_media_envelope(
    root: Path,
    config: dict[str, Any],
    path: Path,
    *,
    role: str,
    expected_duration: float | None,
    video_bitrate: str,
    audio_bitrate: str | None = None,
    max_width: int = EFFICIENT_VIDEO_MAX_WIDTH,
    max_height: int = EFFICIENT_VIDEO_MAX_HEIGHT,
    probe_container: bool = True,
) -> dict[str, Any]:
    stat = _safe_stat(path)
    duration = (
        expected_duration
        if expected_duration and expected_duration > 0
        else (probe_media_duration_seconds(config, path) if probe_container else None)
    )
    per_second = _bitrate_bytes_per_second(video_bitrate)
    if audio_bitrate:
        per_second += _bitrate_bytes_per_second(audio_bitrate)
    max_bytes = None
    if duration and per_second > 0:
        max_bytes = int(duration * per_second * GENERATED_MEDIA_ENVELOPE_SAFETY_FACTOR) + GENERATED_MEDIA_ENVELOPE_MIN_OVERHEAD_BYTES
    failures: list[str] = []
    if stat is None or stat.st_size <= 0:
        failures.append("output_missing_or_empty")
    if max_bytes is not None and stat is not None and stat.st_size > max_bytes:
        failures.append("output_exceeds_configured_byte_envelope")
    probe = _probe_media_container(config, path) if probe_container else {"status": "skipped", "reason": "probe_disabled"}
    video = _video_stream_row(probe)
    if video:
        try:
            width = int(video.get("width") or 0)
            height = int(video.get("height") or 0)
        except (TypeError, ValueError):
            width = 0
            height = 0
        if width > max_width or height > max_height:
            failures.append("output_exceeds_configured_dimensions")
    return {
        "schema": "demo_take_generated_media_envelope_v0",
        "status": "fail" if failures else ("pass" if probe.get("status") == "pass" else "warn"),
        "role": role,
        "relative_path": _path_state_signature(root, path).get("relative_path"),
        "bytes": stat.st_size if stat else None,
        "expected_duration_seconds": round(duration, 6) if duration else None,
        "video_bitrate": video_bitrate,
        "audio_bitrate": audio_bitrate,
        "max_bytes": max_bytes,
        "max_width": max_width,
        "max_height": max_height,
        "probe_status": probe.get("status"),
        "video_stream": dict(video) if video else None,
        "failures": failures,
    }


def _write_generated_media_receipt(
    root: Path,
    output: Path,
    *,
    stage: str,
    signature: Mapping[str, Any],
    envelope: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": GENERATED_MEDIA_RECEIPT_SCHEMA,
        "status": "ready" if envelope.get("status") != "fail" else "failed",
        "stage": stage,
        "created_at": now_iso(),
        "output": _path_state_signature(root, output).get("relative_path"),
        "output_state": _path_state_signature(root, output),
        "signature": dict(signature),
        "envelope": dict(envelope),
    }
    if extra:
        payload.update(dict(extra))
    receipt_path = _generated_media_receipt_path(root, output)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(receipt_path, payload)
    return payload


def _compact_sample_point(label: str, seconds: float, source: str) -> dict[str, Any]:
    return {
        "label": label,
        "seconds": round(max(0.0, float(seconds)), 3),
        "source": source,
    }


def _media_conformance_sample_points(
    root: Path,
    expected_total: float,
    segment_rows: list[dict[str, Any]],
    track_durations: list[float],
) -> tuple[list[dict[str, Any]], int]:
    duration_candidates = [expected_total, *track_durations]
    duration = max([value for value in duration_candidates if value and value > 0] or [0.0])
    raw_points: list[dict[str, Any]] = []
    if duration > 0:
        raw_points.extend([
            _compact_sample_point("beginning", 0.0, "whole_take"),
            _compact_sample_point("midpoint", duration / 2.0, "whole_take"),
            _compact_sample_point("end", max(0.0, duration - 0.5), "whole_take"),
        ])
    cursor = 0.0
    for row in segment_rows:
        expected = _timeline_seconds(row.get("expected_duration_seconds"), 0.0) or 0.0
        if expected <= 0:
            continue
        raw_points.append(_compact_sample_point(f"{row.get('id') or 'segment'}_start", cursor, "media_segment"))
        raw_points.append(_compact_sample_point(f"{row.get('id') or 'segment'}_end", max(0.0, cursor + expected - 0.2), "media_segment"))
        cursor += expected

    final_receipt = _read_json_dict(root / "render" / "final" / "final_render_receipt.json")
    for segment in final_receipt.get("source_segments") or []:
        if not isinstance(segment, Mapping):
            continue
        clip_id = str(segment.get("clip_id") or "render_segment")
        start = _timeline_seconds(segment.get("start_seconds"))
        end = _timeline_seconds(segment.get("end_seconds"))
        if start is not None:
            raw_points.append(_compact_sample_point(f"{clip_id}_render_start", start, "final_render_source_segment"))
        if end is not None:
            raw_points.append(_compact_sample_point(f"{clip_id}_render_end", max(0.0, end - 0.2), "final_render_source_segment"))

    intent_events = _read_json_dict(root / "intent_events.json")
    for event in intent_events.get("events") or []:
        if not isinstance(event, Mapping) or event.get("kind") != "operator_feedback":
            continue
        event_id = str(event.get("id") or "operator_feedback")
        start = _timeline_seconds(event.get("start_seconds"), _timeline_seconds(event.get("video_t_seconds")))
        if start is not None:
            raw_points.append(_compact_sample_point(f"{event_id}_complaint", start, "operator_feedback_window"))

    placement = _read_json_dict(root / "edit" / "webcam_placement.json")
    for index, segment in enumerate(placement.get("segments") or []):
        if not isinstance(segment, Mapping):
            continue
        start = _timeline_seconds(segment.get("start"))
        end = _timeline_seconds(segment.get("end"))
        mode = str(segment.get("mode") or f"webcam_{index:04d}")
        if start is not None:
            raw_points.append(_compact_sample_point(f"webcam_{index:04d}_{mode}_start", start, "webcam_state_transition"))
        if end is not None:
            raw_points.append(_compact_sample_point(f"webcam_{index:04d}_{mode}_end", max(0.0, end - 0.2), "webcam_state_transition"))

    seen: set[tuple[str, float, str]] = set()
    deduped: list[dict[str, Any]] = []
    for point in sorted(raw_points, key=lambda row: (float(row["seconds"]), str(row["label"]))):
        key = (str(point["label"]), float(point["seconds"]), str(point["source"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(point)
    limit = 32
    return deduped[:limit], max(0, len(deduped) - limit)


def _probe_packet_sample(config: dict[str, Any], path: Path, point: dict[str, Any]) -> dict[str, Any]:
    ffprobe = _ffprobe_path(config)
    if not path.exists():
        return {**point, "status": "missing", "packet_count": 0}
    if not ffprobe:
        return {**point, "status": "unavailable", "packet_count": 0, "reason": "ffprobe_not_found"}
    start = max(0.0, float(point.get("seconds") or 0.0))
    command = [
        ffprobe,
        "-hide_banner",
        "-v",
        "error",
        "-read_intervals",
        f"{start:.3f}%+0.500",
        "-show_entries",
        "packet=stream_index,pts_time,dts_time,duration_time,size,flags",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {**point, "status": "fail", "packet_count": 0, "error": str(exc)}
    if proc.returncode != 0:
        return {
            **point,
            "status": "fail",
            "packet_count": 0,
            "exit_code": proc.returncode,
            "stderr": (proc.stderr or "").strip()[-600:],
        }
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {**point, "status": "fail", "packet_count": 0, "error": f"invalid ffprobe json: {exc}"}
    packets = [packet for packet in payload.get("packets") or [] if isinstance(packet, Mapping)]
    last_pts_by_stream: dict[str, float] = {}
    last_dts_by_stream: dict[str, float] = {}
    pts_monotonic = True
    dts_monotonic = True
    pts_values: list[float] = []
    dts_values: list[float] = []
    duration_values: list[float] = []
    for packet in packets:
        stream_index = str(packet.get("stream_index") or "0")
        pts = _timeline_seconds(packet.get("pts_time"))
        dts = _timeline_seconds(packet.get("dts_time"))
        order_time = dts if dts is not None else pts
        if order_time is None:
            continue
        if pts is not None:
            if stream_index in last_pts_by_stream and pts < last_pts_by_stream[stream_index] - 0.000001:
                pts_monotonic = False
            last_pts_by_stream[stream_index] = pts
            pts_values.append(pts)
        if dts is not None:
            if stream_index in last_dts_by_stream and dts < last_dts_by_stream[stream_index] - 0.000001:
                dts_monotonic = False
            last_dts_by_stream[stream_index] = dts
            dts_values.append(dts)
        duration_value = _timeline_seconds(packet.get("duration_time"))
        if duration_value is not None:
            duration_values.append(duration_value)
    monotonic = dts_monotonic if dts_values else pts_monotonic
    return {
        **point,
        "status": "pass" if packets else "empty",
        "packet_count": len(packets),
        "stream_count": len({str(packet.get("stream_index") or "0") for packet in packets}),
        "first_pts_time": round(min(pts_values), 6) if pts_values else None,
        "last_pts_time": round(max(pts_values), 6) if pts_values else None,
        "first_dts_time": round(min(dts_values), 6) if dts_values else None,
        "last_dts_time": round(max(dts_values), 6) if dts_values else None,
        "pts_monotonic_in_packet_order": pts_monotonic if pts_values else None,
        "dts_monotonic_in_packet_order": dts_monotonic if dts_values else None,
        "monotonic_packet_timestamps": monotonic if (pts_values or dts_values) else None,
        "min_packet_duration_seconds": round(min(duration_values), 6) if duration_values else None,
        "max_packet_duration_seconds": round(max(duration_values), 6) if duration_values else None,
    }


def _media_conformance_track_row(
    root: Path,
    config: dict[str, Any],
    track: dict[str, Any],
    sample_points: list[dict[str, Any]],
) -> dict[str, Any]:
    rel = str(track.get("relative_path") or "")
    path = root / rel if rel else root / "__missing_track__"
    probe = _probe_media_container(config, path)
    samples = [_probe_packet_sample(config, path, point) for point in sample_points]
    sampled_monotonic = [
        sample.get("monotonic_packet_timestamps")
        for sample in samples
        if sample.get("monotonic_packet_timestamps") is not None
    ]
    return {
        "id": track.get("id"),
        "role": track.get("role"),
        "relative_path": rel or None,
        "exists": path.exists() if rel else False,
        "probe_status": probe.get("status"),
        "duration_seconds": probe.get("duration_seconds"),
        "size_bytes": probe.get("size_bytes"),
        "stream_count": probe.get("stream_count"),
        "streams": probe.get("streams") if isinstance(probe.get("streams"), list) else [],
        "sample_count": len(samples),
        "sampled_packet_count": sum(int(sample.get("packet_count") or 0) for sample in samples),
        "sampled_monotonic_packet_timestamps": (
            all(bool(value) for value in sampled_monotonic) if sampled_monotonic else None
        ),
        "samples": samples,
    }


def _media_conformance_receipt(
    root: Path,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    segment_rows: list[dict[str, Any]],
    expected_total: float,
    rough_cut_duration: float | None,
) -> dict[str, Any]:
    track_durations = [
        duration
        for duration in (
            probe_media_duration_seconds(config, root / str(track.get("relative_path")))
            for track in tracks
            if isinstance(track, Mapping) and track.get("relative_path")
        )
        if duration is not None
    ]
    sample_points, sample_points_omitted = _media_conformance_sample_points(
        root,
        expected_total,
        segment_rows,
        track_durations,
    )
    track_rows = [
        _media_conformance_track_row(root, config, track, sample_points)
        for track in tracks
        if isinstance(track, Mapping) and track.get("relative_path")
    ]
    parseable_count = sum(1 for row in track_rows if row.get("probe_status") == "pass")
    existing_count = sum(1 for row in track_rows if row.get("exists"))
    monotonic_values = [
        row.get("sampled_monotonic_packet_timestamps")
        for row in track_rows
        if row.get("sampled_monotonic_packet_timestamps") is not None
    ]
    duration_checks: list[dict[str, Any]] = []
    if expected_total > 0:
        checked_roles: set[str] = set()
        for row in track_rows:
            role = str(row.get("role") or "")
            if role not in {"screen", "microphone", "webcam"}:
                continue
            if role in checked_roles:
                continue
            duration = _timeline_seconds(row.get("duration_seconds"))
            if duration is None:
                continue
            checked_roles.add(role)
            duration_checks.append({
                "role": role,
                "relative_path": row.get("relative_path"),
                "duration_seconds": round(duration, 3),
                "expected_active_duration_seconds": round(expected_total, 3),
                "delta_seconds": round(abs(duration - expected_total), 3),
                "within_tolerance": abs(duration - expected_total) <= max(1.0, expected_total * 0.05),
            })
    if rough_cut_duration is not None and expected_total > 0:
        duration_checks.append({
            "role": "rough_cut",
            "relative_path": "render/rough_cut.mp4",
            "duration_seconds": round(float(rough_cut_duration), 3),
            "expected_active_duration_seconds": round(expected_total, 3),
            "delta_seconds": round(abs(float(rough_cut_duration) - expected_total), 3),
            "within_tolerance": abs(float(rough_cut_duration) - expected_total) <= max(1.0, expected_total * 0.05),
        })
    status = "pass"
    if existing_count and parseable_count < existing_count:
        status = "fail"
    elif monotonic_values and not all(bool(value) for value in monotonic_values):
        status = "fail"
    elif duration_checks and not all(bool(row.get("within_tolerance")) for row in duration_checks):
        status = "warn"
    elif not track_rows:
        status = "missing"
    return {
        "schema": "demo_take_media_conformance_v0",
        "status": status,
        "ffprobe_present": bool(_ffprobe_path(config)),
        "track_count": len(track_rows),
        "existing_track_count": existing_count,
        "parseable_track_count": parseable_count,
        "sample_point_count": len(sample_points),
        "sample_points_omitted_count": sample_points_omitted,
        "sample_points": sample_points,
        "sampled_monotonic_packet_timestamps": (
            all(bool(value) for value in monotonic_values) if monotonic_values else None
        ),
        "duration_alignment": {
            "status": (
                "pass"
                if duration_checks and all(bool(row.get("within_tolerance")) for row in duration_checks)
                else ("missing" if not duration_checks else "warn")
            ),
            "checks": duration_checks,
        },
        "track_proofs": track_rows,
    }


def _parse_iso(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _segment_wall_duration_seconds(segment: Mapping[str, Any]) -> float | None:
    started = _parse_iso(segment.get("started_at"))
    ended = _parse_iso(segment.get("ended_at"))
    if not started or not ended:
        return None
    duration = (ended - started).total_seconds()
    return duration if duration > 0 else None


def _segment_expected_duration_seconds(
    root: Path,
    config: dict[str, Any],
    segment: Mapping[str, Any],
) -> tuple[float | None, str]:
    wall_duration = _segment_wall_duration_seconds(segment)
    if wall_duration:
        return wall_duration, "segment_wall_clock"
    mic_track = segment.get("microphone_track")
    mic_path = _segment_track_path(root, mic_track if isinstance(mic_track, Mapping) else None)
    if mic_path:
        mic_duration = probe_media_duration_seconds(config, mic_path)
        if mic_duration:
            return mic_duration, "microphone_duration"
    screen_tracks = segment.get("screen_tracks", []) or []
    for track in screen_tracks:
        screen_path = _segment_track_path(root, track if isinstance(track, Mapping) else None)
        if screen_path:
            screen_duration = probe_media_duration_seconds(config, screen_path)
            if screen_duration:
                return screen_duration, "screen_duration"
    return None, "unknown"


def _segment_expected_rows(
    root: Path,
    config: dict[str, Any],
    segments: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    active_cursor = 0.0
    for index, segment in enumerate(segments, start=1):
        expected_duration, expected_source = _segment_expected_duration_seconds(root, config, segment)
        row = {
            "segment": segment,
            "segment_id": str(segment.get("id") or f"segment_{index:04d}"),
            "index": segment.get("index", index),
            "expected_start_seconds": active_cursor,
            "expected_duration": expected_duration,
            "expected_source": expected_source,
        }
        if expected_duration and expected_duration > 0:
            active_cursor += expected_duration
        rows.append(row)
    return rows


def _track_capture_delay_seconds(segment: Mapping[str, Any], track: Mapping[str, Any] | None) -> float:
    if not isinstance(track, Mapping):
        return 0.0
    segment_started = _parse_iso(segment.get("timeline_started_at") or segment.get("started_at"))
    capture_started = _parse_iso(track.get("capture_started_at"))
    if segment_started and capture_started:
        return (capture_started - segment_started).total_seconds()
    offset = _track_timeline_offset_seconds(track)
    if offset > 0:
        return -offset
    return 0.0


def _timeline_sync_plan_for_track(
    *,
    role: str,
    segment: Mapping[str, Any],
    track: Mapping[str, Any] | None,
    relative_path: str | None,
    raw_duration: float | None,
    expected_start_seconds: float,
    expected_duration: float,
    expected_source: str,
) -> dict[str, Any]:
    capture_delay = _track_capture_delay_seconds(segment, track)
    media_duration = raw_duration if raw_duration is not None and raw_duration > 0 else None
    track_window_start = capture_delay
    track_window_end = capture_delay + media_duration if media_duration is not None else None
    intersection_start = max(0.0, track_window_start)
    intersection_end = min(expected_duration, track_window_end) if track_window_end is not None else expected_duration
    trim_start = max(0.0, -track_window_start)
    trim_duration = max(0.0, intersection_end - intersection_start)
    front_pad = max(0.0, track_window_start)
    end_pad = max(0.0, expected_duration - front_pad - trim_duration)
    output_duration = front_pad + trim_duration + end_pad
    boundary_error_ms = abs(output_duration - expected_duration) * 1000.0
    failures: list[str] = []
    warnings: list[str] = []
    if relative_path is None:
        failures.append("track_missing")
    if expected_duration <= 0:
        failures.append("expected_duration_missing")
    if media_duration is None and relative_path is not None:
        warnings.append("media_duration_unknown")
    if trim_duration <= 0 and expected_duration > 0 and relative_path is not None:
        failures.append("track_has_no_overlap_with_segment_window")
    if boundary_error_ms > TIMELINE_SYNC_FAIL_THRESHOLD_MS:
        failures.append("normalized_boundary_exceeds_fail_threshold")
    elif boundary_error_ms > TIMELINE_SYNC_WARN_THRESHOLD_MS:
        warnings.append("normalized_boundary_exceeds_warn_threshold")
    correction_applied = front_pad > 0.0005 or end_pad > 0.0005 or trim_start > 0.0005
    return {
        "role": role,
        "segment_id": str(segment.get("id") or ""),
        "segment_index": segment.get("index"),
        "relative_path": relative_path,
        "capture_started_at": track.get("capture_started_at") if isinstance(track, Mapping) else None,
        "segment_started_at": segment.get("timeline_started_at") or segment.get("started_at"),
        "capture_start_delta_seconds": round(capture_delay, 6),
        "expected_start_seconds": round(expected_start_seconds, 6),
        "expected_duration_seconds": round(expected_duration, 6),
        "expected_duration_source": expected_source,
        "media_start_time_seconds": round(track_window_start, 6),
        "media_duration_seconds": round(media_duration, 6) if media_duration is not None else None,
        "media_end_time_seconds": round(track_window_end, 6) if track_window_end is not None else None,
        "front_pad_seconds": round(front_pad, 6),
        "trim_start_seconds": round(trim_start, 6),
        "trim_duration_seconds": round(trim_duration, 6),
        "end_pad_seconds": round(end_pad, 6),
        "output_duration_seconds": round(output_duration, 6),
        "boundary_error_ms": round(boundary_error_ms, 3),
        "correction_applied": correction_applied,
        "status": "fail" if failures else ("warn" if warnings else "pass"),
        "failures": failures,
        "warnings": warnings,
    }


def _video_normalization_filter(sync_plan: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    expected_duration = float(sync_plan.get("expected_duration_seconds") or 0.0)
    trim_start = float(sync_plan.get("trim_start_seconds") or 0.0)
    trim_duration = max(0.001, float(sync_plan.get("trim_duration_seconds") or 0.0))
    front_pad = float(sync_plan.get("front_pad_seconds") or 0.0)
    end_pad = float(sync_plan.get("end_pad_seconds") or 0.0)
    filter_text = (
        f"trim=start={trim_start:.6f}:duration={trim_duration:.6f},"
        "setpts=PTS-STARTPTS,"
        "fps=30,"
        f"tpad=start_mode=add:start_duration={front_pad:.6f}:"
        f"stop_mode=clone:stop_duration={end_pad:.6f}:color=black,"
        f"trim=duration={expected_duration:.6f},"
        "setpts=PTS-STARTPTS,"
        "format=yuv420p"
    )
    return filter_text, dict(sync_plan)


def _normalize_video_segment(
    root: Path,
    config: dict[str, Any],
    source: Path,
    output: Path,
    *,
    role: str,
    expected_duration: float,
    raw_duration: float | None,
    sync_plan: Mapping[str, Any] | None = None,
    log_name: str,
    failures: list[str],
) -> dict[str, Any] | None:
    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg:
        failures.append(f"Cannot normalize video segment {source.name}: ffmpeg path missing.")
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    output_tmp = output.with_name(output.stem + ".tmp" + output.suffix)
    log_path = root / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    if sync_plan is None:
        sync_plan = _timeline_sync_plan_for_track(
            role=role,
            segment={},
            track={"relative_path": relative(root, source)},
            relative_path=relative(root, source),
            raw_duration=raw_duration,
            expected_start_seconds=0.0,
            expected_duration=expected_duration,
            expected_source="legacy_duration_only",
        )
    video_filter, receipt = _video_normalization_filter(sync_plan)
    quality_settings = recording_quality_settings(config)
    scale_filter = quality_settings.get("scale_filter")
    if scale_filter:
        video_filter = f"{video_filter},{scale_filter},format=yuv420p"
        receipt["scale_filter"] = str(scale_filter)
    bitrate_key = "webcam_bitrate" if role == "webcam" else "screen_bitrate"
    video_bitrate = str(quality_settings.get(bitrate_key) or quality_settings["screen_bitrate"])
    signature = _media_build_signature(
        root,
        stage="normalize_video_segment",
        output=output,
        inputs=[source],
        params={
            "role": role,
            "expected_duration_seconds": round(expected_duration, 6),
            "raw_duration_seconds": round(raw_duration, 6) if raw_duration is not None else None,
            "timeline_sync": {
                key: receipt.get(key)
                for key in (
                    "segment_id",
                    "capture_start_delta_seconds",
                    "front_pad_seconds",
                    "trim_start_seconds",
                    "trim_duration_seconds",
                    "end_pad_seconds",
                )
            },
            "video_filter": video_filter,
            "video_bitrate": video_bitrate,
            "encoder": "h264_videotoolbox",
        },
    )
    cached = _read_matching_generated_media_receipt(root, output, signature)
    if cached:
        extra = cached.get("extra") if isinstance(cached.get("extra"), Mapping) else {}
        return {
            **dict(extra),
            "source": relative(root, source),
            "output": relative(root, output),
            "normalized_duration_seconds": cached.get("duration_seconds"),
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "skipped": True,
        }
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-vf",
        video_filter,
        "-an",
        "-t",
        f"{float(receipt.get('expected_duration_seconds') or expected_duration):.6f}",
        "-c:v",
        "h264_videotoolbox",
        "-b:v",
        video_bitrate,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_tmp),
    ]
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"video segment normalization unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status == 0 and output_tmp.exists():
        envelope = _generated_media_envelope(
            root,
            config,
            output_tmp,
            role=role,
            expected_duration=expected_duration,
            video_bitrate=video_bitrate,
        )
        if envelope.get("status") == "fail":
            _write_generated_media_receipt(
                root,
                output,
                stage="normalize_video_segment",
                signature=signature,
                envelope=envelope,
                extra={"extra": {**receipt, "source": relative(root, source), "output": relative(root, output)}},
            )
            try:
                output_tmp.unlink()
            except OSError:
                pass
            failures.append(
                f"Generated media envelope failed for {source.name}: "
                f"{', '.join(str(item) for item in envelope.get('failures') or [])}."
            )
            return None
        os.replace(output_tmp, output)
        normalized_duration = probe_media_duration_seconds(config, output)
        generated_receipt = _write_generated_media_receipt(
            root,
            output,
            stage="normalize_video_segment",
            signature=signature,
            envelope={
                **dict(envelope),
                "relative_path": relative(root, output),
                "bytes": output.stat().st_size if output.exists() else None,
            },
            extra={
                "duration_seconds": normalized_duration,
                "extra": {
                    **receipt,
                    "source": relative(root, source),
                    "output": relative(root, output),
                },
            },
        )
        return {
            **receipt,
            "source": relative(root, source),
            "output": relative(root, output),
            "normalized_duration_seconds": normalized_duration,
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "generated_media_status": generated_receipt.get("status"),
            "skipped": False,
        }

    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    failures.append(f"Video segment normalization failed for {source.name}; see logs/{log_name}.")
    return None


def _audio_normalization_filter(sync_plan: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    expected_duration = float(sync_plan.get("expected_duration_seconds") or 0.0)
    trim_start = float(sync_plan.get("trim_start_seconds") or 0.0)
    trim_duration = max(0.001, float(sync_plan.get("trim_duration_seconds") or 0.0))
    front_pad = float(sync_plan.get("front_pad_seconds") or 0.0)
    end_pad = float(sync_plan.get("end_pad_seconds") or 0.0)
    delay_ms = int(round(front_pad * 1000.0))
    filters = [
        f"atrim=start={trim_start:.6f}:duration={trim_duration:.6f}",
        "asetpts=PTS-STARTPTS",
    ]
    if delay_ms > 0:
        filters.append(f"adelay={delay_ms}:all=1")
    if end_pad > 0:
        filters.append(f"apad=pad_dur={end_pad:.6f}")
    filters.extend([
        f"atrim=duration={expected_duration:.6f}",
        "asetpts=PTS-STARTPTS",
        "aresample=48000",
        "aformat=sample_rates=48000:channel_layouts=stereo",
    ])
    return ",".join(filters), dict(sync_plan)


def _normalize_audio_segment(
    root: Path,
    config: dict[str, Any],
    source: Path,
    output: Path,
    *,
    expected_duration: float,
    raw_duration: float | None,
    sync_plan: Mapping[str, Any],
    log_name: str,
    failures: list[str],
) -> dict[str, Any] | None:
    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg:
        failures.append(f"Cannot normalize audio segment {source.name}: ffmpeg path missing.")
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    output_tmp = output.with_name(output.stem + ".tmp" + output.suffix)
    log_path = root / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    audio_filter, receipt = _audio_normalization_filter(sync_plan)
    signature = _media_build_signature(
        root,
        stage="normalize_audio_segment",
        output=output,
        inputs=[source],
        params={
            "expected_duration_seconds": round(expected_duration, 6),
            "raw_duration_seconds": round(raw_duration, 6) if raw_duration is not None else None,
            "timeline_sync": {
                key: receipt.get(key)
                for key in (
                    "segment_id",
                    "capture_start_delta_seconds",
                    "front_pad_seconds",
                    "trim_start_seconds",
                    "trim_duration_seconds",
                    "end_pad_seconds",
                )
            },
            "audio_filter": audio_filter,
            "audio_codec": "pcm_s16le",
            "sample_rate": 48000,
        },
    )
    cached = _read_matching_generated_media_receipt(root, output, signature)
    if cached:
        extra = cached.get("extra") if isinstance(cached.get("extra"), Mapping) else {}
        return {
            **dict(extra),
            "source": relative(root, source),
            "output": relative(root, output),
            "normalized_duration_seconds": cached.get("duration_seconds"),
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "skipped": True,
        }
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-af",
        audio_filter,
        "-t",
        f"{float(receipt.get('expected_duration_seconds') or expected_duration):.6f}",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
        str(output_tmp),
    ]
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"audio segment normalization unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status == 0 and output_tmp.exists():
        envelope = _generated_media_envelope(
            root,
            config,
            output_tmp,
            role="audio",
            expected_duration=expected_duration,
            video_bitrate="0",
            audio_bitrate=TIMELINE_SYNC_PCM_AUDIO_BITRATE,
        )
        if envelope.get("status") == "fail":
            _write_generated_media_receipt(
                root,
                output,
                stage="normalize_audio_segment",
                signature=signature,
                envelope=envelope,
                extra={"extra": {**receipt, "source": relative(root, source), "output": relative(root, output)}},
            )
            try:
                output_tmp.unlink()
            except OSError:
                pass
            failures.append(
                f"Generated media envelope failed for {source.name}: "
                f"{', '.join(str(item) for item in envelope.get('failures') or [])}."
            )
            return None
        os.replace(output_tmp, output)
        normalized_duration = probe_media_duration_seconds(config, output)
        generated_receipt = _write_generated_media_receipt(
            root,
            output,
            stage="normalize_audio_segment",
            signature=signature,
            envelope={
                **dict(envelope),
                "relative_path": relative(root, output),
                "bytes": output.stat().st_size if output.exists() else None,
            },
            extra={
                "duration_seconds": normalized_duration,
                "extra": {
                    **receipt,
                    "source": relative(root, source),
                    "output": relative(root, output),
                },
            },
        )
        return {
            **receipt,
            "source": relative(root, source),
            "output": relative(root, output),
            "normalized_duration_seconds": normalized_duration,
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "generated_media_status": generated_receipt.get("status"),
            "skipped": False,
        }
    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    failures.append(f"Audio segment normalization failed for {source.name}; see logs/{log_name}.")
    return None


def _video_dimensions_from_probe(probe: Mapping[str, Any]) -> tuple[int, int] | None:
    for stream in probe.get("streams") or []:
        if not isinstance(stream, Mapping) or stream.get("codec_type") != "video":
            continue
        try:
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            return width, height
    return None


def _write_black_video_placeholder(
    root: Path,
    config: dict[str, Any],
    output: Path,
    *,
    duration: float,
    width: int,
    height: int,
    log_name: str,
    failures: list[str],
) -> bool:
    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg:
        failures.append(f"Webcam placeholder generation failed for {output.name}: ffmpeg path missing.")
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    output_tmp = output.with_name(output.stem + ".tmp" + output.suffix)
    log_path = root / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    quality_settings = recording_quality_settings(config)
    video_bitrate = str(quality_settings["webcam_bitrate"])
    signature = _media_build_signature(
        root,
        stage="webcam_placeholder",
        output=output,
        inputs=[],
        params={
            "duration_seconds": round(duration, 6),
            "width": width,
            "height": height,
            "video_bitrate": video_bitrate,
            "encoder": "h264_videotoolbox",
        },
    )
    cached = _read_matching_generated_media_receipt(root, output, signature)
    if cached:
        return True
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={width}x{height}:r=30",
        "-t",
        f"{duration:.6f}",
        "-an",
        "-c:v",
        "h264_videotoolbox",
        "-b:v",
        video_bitrate,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_tmp),
    ]
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"webcam placeholder generation unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status == 0 and output_tmp.exists():
        envelope = _generated_media_envelope(
            root,
            config,
            output_tmp,
            role="webcam",
            expected_duration=duration,
            video_bitrate=video_bitrate,
            max_width=width,
            max_height=height,
        )
        if envelope.get("status") == "fail":
            _write_generated_media_receipt(
                root,
                output,
                stage="webcam_placeholder",
                signature=signature,
                envelope=envelope,
                extra={"duration_seconds": duration},
            )
            try:
                output_tmp.unlink()
            except OSError:
                pass
            failures.append(
                f"Generated media envelope failed for {output.name}: "
                f"{', '.join(str(item) for item in envelope.get('failures') or [])}."
            )
            return False
        os.replace(output_tmp, output)
        _write_generated_media_receipt(
            root,
            output,
            stage="webcam_placeholder",
            signature=signature,
            envelope={
                **dict(envelope),
                "relative_path": relative(root, output),
                "bytes": output.stat().st_size if output.exists() else None,
            },
            extra={"duration_seconds": probe_media_duration_seconds(config, output) or duration},
        )
        return True
    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    failures.append(f"Webcam placeholder generation failed for {output.name}; see logs/{log_name}.")
    return False


def _concat_timeline_video_segments(
    root: Path,
    config: dict[str, Any],
    entries: list[tuple[dict[str, Any], Path, dict[str, Any], str]],
    output: Path,
    *,
    role: str,
    suffix: str,
    failures: list[str],
) -> dict[str, Any] | None:
    if not entries:
        return None
    parts_dir = output.parent / "parts"
    normalized_paths: list[Path] = []
    normalizations: list[dict[str, Any]] = []
    for index, (_track, path, sync_plan, expected_source) in enumerate(entries, start=1):
        expected_duration = float(sync_plan.get("expected_duration_seconds") or 0.0)
        raw_duration = probe_media_duration_seconds(config, path)
        part_output = parts_dir / f"{role}_{suffix}_{index:04d}.mp4"
        result = _normalize_video_segment(
            root,
            config,
            path,
            part_output,
            role=role,
            expected_duration=expected_duration,
            raw_duration=raw_duration,
            sync_plan=sync_plan,
            log_name=f"normalize_{role}_{suffix}_{index:04d}.log",
            failures=failures,
        )
        if result is None:
            return None
        result["expected_duration_source"] = expected_source
        normalized_paths.append(part_output)
        normalizations.append(result)

    expected_total = sum(float(item[2].get("expected_duration_seconds") or 0.0) for item in entries)
    quality_settings = recording_quality_settings(config)
    bitrate_key = "webcam_bitrate" if role == "webcam" else "screen_bitrate"
    video_bitrate = str(quality_settings.get(bitrate_key) or quality_settings["screen_bitrate"])
    signature = _media_build_signature(
        root,
        stage="concat_timeline_video_segments",
        output=output,
        inputs=normalized_paths,
        params={
            "role": role,
            "suffix": suffix,
            "expected_duration_seconds": round(expected_total, 6),
            "source_tracks": [relative(root, path) for _track, path, _plan, _source in entries],
            "expected_duration_sources": [source for _track, _path, _plan, source in entries],
            "timeline_sync": [
                {
                    "segment_id": sync_plan.get("segment_id"),
                    "capture_start_delta_seconds": sync_plan.get("capture_start_delta_seconds"),
                    "front_pad_seconds": sync_plan.get("front_pad_seconds"),
                    "trim_start_seconds": sync_plan.get("trim_start_seconds"),
                    "trim_duration_seconds": sync_plan.get("trim_duration_seconds"),
                    "end_pad_seconds": sync_plan.get("end_pad_seconds"),
                    "status": sync_plan.get("status"),
                }
                for _track, _path, sync_plan, _source in entries
            ],
        },
    )
    cached = _read_matching_generated_media_receipt(root, output, signature)
    if cached:
        return {
            "normalizations": normalizations,
            "expected_duration_seconds": round(expected_total, 3),
            "output_duration_seconds": cached.get("duration_seconds") or probe_media_duration_seconds(config, output),
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "skipped": True,
        }

    if len(normalized_paths) == 1:
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(normalized_paths[0], output)
        concat_ready = True
    else:
        concat_ready = _concat_media_segments(
            root,
            config,
            normalized_paths,
            output,
            log_name=f"splice_{role}_{suffix}.log",
            failures=failures,
        )
    if not concat_ready:
        return None
    envelope = _generated_media_envelope(
        root,
        config,
        output,
        role=role,
        expected_duration=expected_total,
        video_bitrate=video_bitrate,
    )
    output_duration = probe_media_duration_seconds(config, output)
    _write_generated_media_receipt(
        root,
        output,
        stage="concat_timeline_video_segments",
        signature=signature,
        envelope=envelope,
        extra={
            "duration_seconds": output_duration,
            "extra": {
                "normalization_count": len(normalizations),
                "expected_duration_seconds": round(expected_total, 3),
            },
        },
    )
    if envelope.get("status") == "fail":
        failures.append(
            f"Generated media envelope failed for {output.name}: "
            f"{', '.join(str(item) for item in envelope.get('failures') or [])}."
        )
        return None
    return {
        "normalizations": normalizations,
        "expected_duration_seconds": round(expected_total, 3),
        "output_duration_seconds": output_duration,
        "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
        "skipped": False,
    }


def _concat_timeline_audio_segments(
    root: Path,
    config: dict[str, Any],
    entries: list[tuple[dict[str, Any], Path, dict[str, Any], str]],
    output: Path,
    *,
    suffix: str,
    failures: list[str],
) -> dict[str, Any] | None:
    if not entries:
        return None
    parts_dir = output.parent / "parts"
    normalized_paths: list[Path] = []
    normalizations: list[dict[str, Any]] = []
    for index, (_track, path, sync_plan, expected_source) in enumerate(entries, start=1):
        expected_duration = float(sync_plan.get("expected_duration_seconds") or 0.0)
        raw_duration = probe_media_duration_seconds(config, path)
        part_output = parts_dir / f"microphone_{suffix}_{index:04d}.wav"
        result = _normalize_audio_segment(
            root,
            config,
            path,
            part_output,
            expected_duration=expected_duration,
            raw_duration=raw_duration,
            sync_plan=sync_plan,
            log_name=f"normalize_microphone_{suffix}_{index:04d}.log",
            failures=failures,
        )
        if result is None:
            return None
        result["expected_duration_source"] = expected_source
        normalized_paths.append(part_output)
        normalizations.append(result)

    expected_total = sum(float(item[2].get("expected_duration_seconds") or 0.0) for item in entries)
    signature = _media_build_signature(
        root,
        stage="concat_timeline_audio_segments",
        output=output,
        inputs=normalized_paths,
        params={
            "suffix": suffix,
            "expected_duration_seconds": round(expected_total, 6),
            "source_tracks": [relative(root, path) for _track, path, _plan, _source in entries],
            "expected_duration_sources": [source for _track, _path, _plan, source in entries],
            "timeline_sync": [
                {
                    "segment_id": sync_plan.get("segment_id"),
                    "capture_start_delta_seconds": sync_plan.get("capture_start_delta_seconds"),
                    "front_pad_seconds": sync_plan.get("front_pad_seconds"),
                    "trim_start_seconds": sync_plan.get("trim_start_seconds"),
                    "trim_duration_seconds": sync_plan.get("trim_duration_seconds"),
                    "end_pad_seconds": sync_plan.get("end_pad_seconds"),
                    "status": sync_plan.get("status"),
                }
                for _track, _path, sync_plan, _source in entries
            ],
        },
    )
    cached = _read_matching_generated_media_receipt(root, output, signature)
    if cached:
        return {
            "normalizations": normalizations,
            "expected_duration_seconds": round(expected_total, 3),
            "output_duration_seconds": cached.get("duration_seconds") or probe_media_duration_seconds(config, output),
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "skipped": True,
        }

    if len(normalized_paths) == 1:
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(normalized_paths[0], output)
        concat_ready = True
    else:
        concat_ready = _concat_media_segments(
            root,
            config,
            normalized_paths,
            output,
            log_name=f"splice_microphone_{suffix}.log",
            failures=failures,
        )
    if not concat_ready:
        return None
    envelope = _generated_media_envelope(
        root,
        config,
        output,
        role="audio",
        expected_duration=expected_total,
        video_bitrate="0",
        audio_bitrate=TIMELINE_SYNC_PCM_AUDIO_BITRATE,
    )
    output_duration = probe_media_duration_seconds(config, output)
    _write_generated_media_receipt(
        root,
        output,
        stage="concat_timeline_audio_segments",
        signature=signature,
        envelope=envelope,
        extra={
            "duration_seconds": output_duration,
            "extra": {
                "normalization_count": len(normalizations),
                "expected_duration_seconds": round(expected_total, 3),
            },
        },
    )
    if envelope.get("status") == "fail":
        failures.append(
            f"Generated media envelope failed for {output.name}: "
            f"{', '.join(str(item) for item in envelope.get('failures') or [])}."
        )
        return None
    return {
        "normalizations": normalizations,
        "expected_duration_seconds": round(expected_total, 3),
        "output_duration_seconds": output_duration,
        "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
        "skipped": False,
    }


def prepare_segment_tracks(
    root: Path,
    config: dict[str, Any],
    session: dict[str, Any],
    failures: list[str],
) -> list[dict[str, Any]]:
    tracks = list(session.get("tracks", []))
    segments = [
        segment
        for segment in session.get("media_segments", [])
        if isinstance(segment, Mapping)
    ]
    if not segments:
        return tracks

    segments.sort(key=lambda segment: int(segment.get("index") or 0))
    spliced_tracks: list[dict[str, Any]] = []
    plan: dict[str, Any] = {
        "schema": "demo_take_pause_splice_plan_v0",
        "created_at": now_iso(),
        "status": "ready",
        "segment_count": len(segments),
        "outputs": [],
    }

    segment_rows = _segment_expected_rows(root, config, segments)

    screen_groups: dict[str, list[tuple[dict[str, Any], Path, dict[str, Any], str]]] = {}
    for row in segment_rows:
        segment = row["segment"]
        expected_duration = row.get("expected_duration")
        expected_source = str(row.get("expected_source") or "unknown")
        if not expected_duration:
            continue
        for track in segment.get("screen_tracks", []) or []:
            if not isinstance(track, Mapping):
                continue
            path = _segment_track_path(root, track)
            if not path:
                continue
            track_dict = dict(track)
            raw_duration = probe_media_duration_seconds(config, path)
            sync_plan = _timeline_sync_plan_for_track(
                role="screen",
                segment=segment,
                track=track_dict,
                relative_path=relative(root, path),
                raw_duration=raw_duration,
                expected_start_seconds=float(row.get("expected_start_seconds") or 0.0),
                expected_duration=float(expected_duration),
                expected_source=expected_source,
            )
            key = str(track.get("device_index") if track.get("device_index") is not None else track.get("id") or "screen")
            screen_groups.setdefault(key, []).append((track_dict, path, sync_plan, expected_source))

    for key, entries in screen_groups.items():
        if len(entries) < 1:
            continue
        first_track, first_path, first_plan, _source = entries[0]
        expected_duration = float(first_plan.get("expected_duration_seconds") or 0.0)
        raw_duration = float(first_plan["media_duration_seconds"]) if first_plan.get("media_duration_seconds") is not None else probe_media_duration_seconds(config, first_path)
        tolerance = max(TIMELINE_SYNC_FRAME_BUDGET_MS / 1000.0, expected_duration * 0.01)
        needs_timeline_output = (
            len(entries) > 1
            or raw_duration is None
            or abs(raw_duration - expected_duration) > tolerance
            or any(bool(sync_plan.get("correction_applied")) or sync_plan.get("status") != "pass" for _track, _path, sync_plan, _source in entries)
        )
        if not needs_timeline_output:
            continue
        device_index = first_track.get("device_index")
        suffix = str(device_index if device_index is not None else key)
        output = root / "tracks" / "spliced" / f"screen_{suffix}.mp4"
        result = _concat_timeline_video_segments(root, config, entries, output, role="screen", suffix=suffix, failures=failures)
        if result:
            track = dict(first_track)
            track["id"] = f"screen_{suffix}_spliced"
            track["relative_path"] = relative(root, output)
            track["splice_source_tracks"] = [relative(root, path) for _, path, _, _ in entries]
            track["capture_engine"] = track.get("capture_engine") or "screencapturekit"
            spliced_tracks.append(track)
            plan["outputs"].append({
                "role": "screen",
                "device_index": device_index,
                "relative_path": track["relative_path"],
                "source_tracks": track["splice_source_tracks"],
                "expected_duration_seconds": result.get("expected_duration_seconds"),
                "output_duration_seconds": result.get("output_duration_seconds"),
                "generated_media_receipt": result.get("generated_media_receipt"),
                "skipped": bool(result.get("skipped")),
                "normalizations": result.get("normalizations", []),
            })

    webcam_rows: list[dict[str, Any]] = []
    for row in segment_rows:
        segment = row["segment"]
        expected_duration = row.get("expected_duration")
        expected_source = str(row.get("expected_source") or "unknown")
        if not expected_duration:
            continue
        track = segment.get("webcam_track")
        track_dict = dict(track) if isinstance(track, Mapping) else None
        path = _segment_track_path(root, track_dict)
        key = None
        if track_dict:
            key = str(track_dict.get("device_index") if track_dict.get("device_index") is not None else track_dict.get("id") or "webcam")
        webcam_rows.append({
            "segment": segment,
            "segment_id": str(segment.get("id") or f"segment_{int(segment.get('index') or 0):04d}"),
            "track": track_dict,
            "path": path,
            "key": key,
            "expected_duration": expected_duration,
            "expected_source": expected_source,
            "expected_start_seconds": float(row.get("expected_start_seconds") or 0.0),
        })

    webcam_keys = [str(row["key"]) for row in webcam_rows if row.get("key") and row.get("path")]
    webcam_groups: dict[str, list[tuple[dict[str, Any], Path, dict[str, Any], str]]] = {}
    webcam_placeholders: dict[str, list[Path]] = {}
    for key in dict.fromkeys(webcam_keys):
        concrete_rows = [row for row in webcam_rows if row.get("key") == key and row.get("path")]
        if not concrete_rows:
            continue
        first_track = dict(concrete_rows[0]["track"])
        first_path = concrete_rows[0]["path"]
        dimensions = _video_dimensions_from_probe(_probe_media_container(config, first_path)) if isinstance(first_path, Path) else None
        width, height = dimensions or (1280, 720)
        device_index = first_track.get("device_index")
        suffix = str(device_index if device_index is not None else key)
        entries: list[tuple[dict[str, Any], Path, dict[str, Any], str]] = []
        placeholders: list[Path] = []
        for row in webcam_rows:
            expected_duration = float(row["expected_duration"])
            expected_source = str(row["expected_source"])
            row_path = row.get("path")
            if row.get("key") == key and isinstance(row_path, Path):
                raw_duration = probe_media_duration_seconds(config, row_path)
                sync_plan = _timeline_sync_plan_for_track(
                    role="webcam",
                    segment=row["segment"],
                    track=dict(row["track"]),
                    relative_path=relative(root, row_path),
                    raw_duration=raw_duration,
                    expected_start_seconds=float(row.get("expected_start_seconds") or 0.0),
                    expected_duration=expected_duration,
                    expected_source=expected_source,
                )
                if raw_duration is not None and expected_duration - raw_duration > max(1.0, expected_duration * 0.02):
                    message = (
                        f"Webcam track shorter than {row['segment_id']} by "
                        f"{expected_duration - raw_duration:.1f}s; padded in tracks/spliced/webcam_{suffix}.mp4."
                    )
                    if message not in failures:
                        failures.append(message)
                entries.append((dict(row["track"]), row_path, sync_plan, expected_source))
                continue
            segment = row["segment"]
            segment_id = str(row["segment_id"])
            segment_index = int(segment.get("index") or len(entries) + 1)
            placeholder = root / "tracks" / "spliced" / "placeholders" / f"webcam_{suffix}_{segment_index:04d}.mp4"
            if _write_black_video_placeholder(
                root,
                config,
                placeholder,
                duration=expected_duration,
                width=width,
                height=height,
                log_name=f"placeholder_webcam_{suffix}_{segment_index:04d}.log",
                failures=failures,
            ):
                message = (
                    f"Webcam track missing for {segment_id}; inserted black placeholder "
                    f"in tracks/spliced/webcam_{suffix}.mp4."
                )
                if message not in failures:
                    failures.append(message)
                placeholders.append(placeholder)
                placeholder_track = dict(first_track)
                placeholder_track["relative_path"] = relative(root, placeholder)
                sync_plan = _timeline_sync_plan_for_track(
                    role="webcam",
                    segment=segment,
                    track=placeholder_track,
                    relative_path=relative(root, placeholder),
                    raw_duration=expected_duration,
                    expected_start_seconds=float(row.get("expected_start_seconds") or 0.0),
                    expected_duration=expected_duration,
                    expected_source="missing_webcam_placeholder",
                )
                entries.append((placeholder_track, placeholder, sync_plan, "missing_webcam_placeholder"))
        if entries:
            webcam_groups[key] = entries
            webcam_placeholders[key] = placeholders

    for key, entries in webcam_groups.items():
        if len(entries) < 1:
            continue
        first_track, first_path, first_plan, _source = entries[0]
        expected_duration = float(first_plan.get("expected_duration_seconds") or 0.0)
        raw_duration = float(first_plan["media_duration_seconds"]) if first_plan.get("media_duration_seconds") is not None else probe_media_duration_seconds(config, first_path)
        tolerance = max(1.0, expected_duration * 0.05)
        needs_timeline_output = (
            bool(webcam_placeholders.get(key))
            or len(entries) > 1
            or raw_duration is None
            or abs(raw_duration - expected_duration) > tolerance
            or any(bool(sync_plan.get("correction_applied")) or sync_plan.get("status") != "pass" for _track, _path, sync_plan, _source in entries)
        )
        if not needs_timeline_output:
            continue
        device_index = first_track.get("device_index")
        suffix = str(device_index if device_index is not None else key)
        output = root / "tracks" / "spliced" / f"webcam_{suffix}.mp4"
        result = _concat_timeline_video_segments(root, config, entries, output, role="webcam", suffix=suffix, failures=failures)
        if result:
            track = dict(first_track)
            track["id"] = f"webcam_{suffix}_spliced"
            track["relative_path"] = relative(root, output)
            track["splice_source_tracks"] = [relative(root, path) for _, path, _, _ in entries]
            if webcam_placeholders.get(key):
                track["splice_placeholder_tracks"] = [relative(root, path) for path in webcam_placeholders[key]]
            track["capture_engine"] = track.get("capture_engine") or "avfoundation_native_camera"
            spliced_tracks.append(track)
            plan["outputs"].append({
                "role": "webcam",
                "device_index": device_index,
                "relative_path": track["relative_path"],
                "source_tracks": track["splice_source_tracks"],
                "placeholder_tracks": [relative(root, path) for path in webcam_placeholders.get(key, [])],
                "expected_duration_seconds": result.get("expected_duration_seconds"),
                "output_duration_seconds": result.get("output_duration_seconds"),
                "generated_media_receipt": result.get("generated_media_receipt"),
                "skipped": bool(result.get("skipped")),
                "normalizations": result.get("normalizations", []),
            })

    mic_entries: list[tuple[dict[str, Any], Path, dict[str, Any], str]] = []
    for row in segment_rows:
        segment = row["segment"]
        expected_duration = row.get("expected_duration")
        expected_source = str(row.get("expected_source") or "unknown")
        if not expected_duration:
            continue
        mic_track = segment.get("microphone_track")
        if not isinstance(mic_track, Mapping):
            continue
        path = _segment_track_path(root, mic_track)
        if path:
            track_dict = dict(mic_track)
            raw_duration = probe_media_duration_seconds(config, path)
            sync_plan = _timeline_sync_plan_for_track(
                role="microphone",
                segment=segment,
                track=track_dict,
                relative_path=relative(root, path),
                raw_duration=raw_duration,
                expected_start_seconds=float(row.get("expected_start_seconds") or 0.0),
                expected_duration=float(expected_duration),
                expected_source=expected_source,
            )
            mic_entries.append((track_dict, path, sync_plan, expected_source))
    if mic_entries:
        first_track = mic_entries[0][0]
        output = root / "tracks" / "spliced" / "microphone.wav"
        expected_total = sum(float(sync_plan.get("expected_duration_seconds") or 0.0) for _track, _path, sync_plan, _source in mic_entries)
        raw_total = sum(float(sync_plan.get("media_duration_seconds") or 0.0) for _track, _path, sync_plan, _source in mic_entries)
        tolerance = max(TIMELINE_SYNC_FRAME_BUDGET_MS / 1000.0, expected_total * 0.01)
        needs_timeline_output = (
            len(mic_entries) > 1
            or abs(raw_total - expected_total) > tolerance
            or any(bool(sync_plan.get("correction_applied")) or sync_plan.get("status") != "pass" for _track, _path, sync_plan, _source in mic_entries)
        )
        result = (
            _concat_timeline_audio_segments(root, config, mic_entries, output, suffix="active", failures=failures)
            if needs_timeline_output
            else None
        )
        if result:
            track = dict(first_track)
            track["id"] = "microphone_spliced"
            track["relative_path"] = relative(root, output)
            track["splice_source_tracks"] = [relative(root, path) for _, path, _, _ in mic_entries]
            track["capture_engine"] = track.get("capture_engine") or "avfoundation_native"
            spliced_tracks.append(track)
            plan["outputs"].append({
                "role": "microphone",
                "relative_path": track["relative_path"],
                "source_tracks": track["splice_source_tracks"],
                "expected_duration_seconds": result.get("expected_duration_seconds"),
                "output_duration_seconds": result.get("output_duration_seconds"),
                "generated_media_receipt": result.get("generated_media_receipt"),
                "skipped": bool(result.get("skipped")),
                "normalizations": result.get("normalizations", []),
            })

    if not spliced_tracks:
        plan["status"] = "unavailable"
    write_json(root / "render" / "edit_plan.json", plan)

    if not spliced_tracks:
        return tracks
    spliced_paths = {track.get("relative_path") for track in spliced_tracks}
    spliced_roles = {track.get("role") for track in spliced_tracks}
    spliced_role_devices = {
        (track.get("role"), track.get("device_index"))
        for track in spliced_tracks
        if track.get("device_index") is not None
    }
    remaining: list[dict[str, Any]] = []
    for track in tracks:
        rel_path = track.get("relative_path")
        if rel_path in spliced_paths:
            continue
        if rel_path and not (root / str(rel_path)).exists():
            role = track.get("role")
            device_index = track.get("device_index")
            if (role, device_index) in spliced_role_devices or (device_index is None and role in spliced_roles):
                continue
        remaining.append(track)
    return spliced_tracks + remaining


def _transcript_last_cue_end_seconds(root: Path) -> float | None:
    transcript_path = root / "transcript" / "transcript.json"
    if not transcript_path.exists():
        return None
    try:
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    candidates: list[float] = []
    duration = transcript.get("duration_seconds")
    if isinstance(duration, (int, float)):
        candidates.append(float(duration))
    for segment in transcript.get("segments", []) or []:
        if not isinstance(segment, Mapping):
            continue
        end = segment.get("end")
        if isinstance(end, (int, float)):
            candidates.append(float(end))
    return max(candidates) if candidates else None


def _append_render_timeline_failure(root: Path, message: str) -> None:
    receipt_path = root / "render" / "render_receipt.json"
    if not receipt_path.exists():
        return
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    failures = receipt.get("known_failures")
    if not isinstance(failures, list):
        failures = []
    if message not in failures:
        failures.append(message)
    receipt["known_failures"] = failures
    receipt["status"] = "timeline_failed"
    write_json(receipt_path, receipt)


def write_media_timeline_receipt(
    root: Path,
    config: dict[str, Any],
    session: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str],
) -> dict[str, Any]:
    segment_rows: list[dict[str, Any]] = []
    expected_total = 0.0
    for segment in session.get("media_segments", []) or []:
        if not isinstance(segment, Mapping):
            continue
        expected, expected_source = _segment_expected_duration_seconds(root, config, segment)
        expected = expected or 0.0
        expected_total += expected
        screen_track = next(
            (track for track in segment.get("screen_tracks", []) or [] if isinstance(track, Mapping)),
            None,
        )
        mic_track = segment.get("microphone_track") if isinstance(segment.get("microphone_track"), Mapping) else None
        webcam_track = segment.get("webcam_track") if isinstance(segment.get("webcam_track"), Mapping) else None
        screen_path = _segment_track_path(root, screen_track)
        mic_path = _segment_track_path(root, mic_track)
        webcam_path = _segment_track_path(root, webcam_track)
        segment_rows.append({
            "id": segment.get("id"),
            "index": segment.get("index"),
            "expected_duration_seconds": round(expected, 3) if expected else None,
            "expected_duration_source": expected_source,
            "screen_path": relative(root, screen_path) if screen_path else None,
            "screen_probe_duration_seconds": probe_media_duration_seconds(config, screen_path) if screen_path else None,
            "mic_path": relative(root, mic_path) if mic_path else None,
            "mic_probe_duration_seconds": probe_media_duration_seconds(config, mic_path) if mic_path else None,
            "webcam_path": relative(root, webcam_path) if webcam_path else None,
            "webcam_probe_duration_seconds": probe_media_duration_seconds(config, webcam_path) if webcam_path else None,
        })

    screen_track = next((track for track in tracks if track.get("role") == "screen"), None)
    mic_track = next((track for track in tracks if track.get("role") == "microphone"), None)
    spliced_screen_duration = None
    spliced_mic_duration = None
    if screen_track and screen_track.get("relative_path"):
        spliced_screen_duration = probe_media_duration_seconds(config, root / str(screen_track["relative_path"]))
    if mic_track and mic_track.get("relative_path"):
        spliced_mic_duration = probe_media_duration_seconds(config, root / str(mic_track["relative_path"]))
    rough_cut_duration = probe_media_duration_seconds(config, root / "render" / "rough_cut.mp4")
    transcript_end = _transcript_last_cue_end_seconds(root)

    status = "ready"
    reason = None
    duration_floor = max(expected_total, transcript_end or 0.0)
    if duration_floor > 0 and rough_cut_duration is not None and rough_cut_duration < duration_floor * 0.80:
        status = "timeline_failed"
        reason = f"review video {rough_cut_duration:.2f}s, expected at least {duration_floor:.2f}s from active media timeline"
    elif expected_total > 0 and spliced_screen_duration is not None and spliced_screen_duration < expected_total * 0.80:
        status = "timeline_failed"
        reason = f"spliced screen {spliced_screen_duration:.2f}s, expected {expected_total:.2f}s from active segments"

    media_conformance = _media_conformance_receipt(
        root,
        config,
        tracks,
        segment_rows,
        expected_total,
        rough_cut_duration,
    )
    payload = {
        "schema": "demo_take_media_timeline_receipt_v0",
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "status": status,
        "reason": reason,
        "expected_active_duration_seconds": round(expected_total, 3) if expected_total else None,
        "segments": segment_rows,
        "spliced_screen_duration_seconds": spliced_screen_duration,
        "spliced_microphone_duration_seconds": spliced_mic_duration,
        "rough_cut_duration_seconds": rough_cut_duration,
        "transcript_last_cue_end_seconds": transcript_end,
        "media_conformance": media_conformance,
    }
    write_json(root / "render" / "media_timeline_receipt.json", payload)
    if status != "ready" and reason:
        message = f"Timeline failed: {reason}."
        if message not in failures:
            failures.append(message)
        _append_render_timeline_failure(root, message)
    return payload


def _safe_stat(path: Path) -> os.stat_result | None:
    try:
        return path.stat()
    except OSError:
        return None


def _file_sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _timeline_input_hashes(root: Path, rel_paths: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel_path in rel_paths:
        digest = _file_sha256(root / rel_path)
        if digest:
            hashes[rel_path] = f"sha256:{digest}"
    return hashes


def _timeline_seconds(value: Any, default: float | None = None) -> float | None:
    parsed = _safe_float(value)
    if parsed is None:
        return default
    return max(0.0, parsed)


def _track_timeline_offset_seconds(track: Mapping[str, Any] | None) -> float:
    if not isinstance(track, Mapping):
        return 0.0
    value = _timeline_seconds(track.get("timeline_offset_seconds"), 0.0)
    return value or 0.0


def _track_for_media_path(root: Path, session: Mapping[str, Any], path: Path) -> dict[str, Any] | None:
    try:
        rel_path = relative(root, path)
    except ValueError:
        rel_path = str(path)
    tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
    for track in tracks:
        if not isinstance(track, Mapping):
            continue
        rel = track.get("relative_path")
        if isinstance(rel, str) and rel == rel_path:
            return dict(track)
    return None


def _media_timeline_offset_seconds(root: Path, session: Mapping[str, Any], path: Path) -> float:
    track = _track_for_media_path(root, session, path)
    return _track_timeline_offset_seconds(track)


def _offset_start_seconds(start: float, offset: float) -> float:
    return max(0.0, float(start) + max(0.0, float(offset)))


def _media_receipt_segment_lookup(media_receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in media_receipt.get("segments", []) or []:
        if not isinstance(row, Mapping):
            continue
        copied = dict(row)
        row_id = row.get("id")
        if row_id:
            lookup[str(row_id)] = copied
        index = row.get("index")
        if index is not None:
            lookup[f"index:{index}"] = copied
    return lookup


def _active_timeline_segments(
    root: Path,
    session: Mapping[str, Any],
    tracks: list[dict[str, Any]],
    media_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    segments = [
        segment
        for segment in session.get("media_segments", []) or []
        if isinstance(segment, Mapping)
    ]
    segments.sort(key=lambda segment: int(segment.get("index") or 0))
    receipt_lookup = _media_receipt_segment_lookup(media_receipt)
    rows: list[dict[str, Any]] = []
    active_cursor = 0.0
    for index, segment in enumerate(segments, start=1):
        segment_id = str(segment.get("id") or f"segment_{index:04d}")
        receipt_row = receipt_lookup.get(segment_id) or receipt_lookup.get(f"index:{segment.get('index')}")
        active_duration = None
        duration_source = None
        if receipt_row:
            active_duration = _timeline_seconds(receipt_row.get("expected_duration_seconds"))
            duration_source = receipt_row.get("expected_duration_source")
        if active_duration is None:
            active_duration = _segment_wall_duration_seconds(segment)
            duration_source = "wall_clock_segment" if active_duration is not None else None
        screen_track = next(
            (track for track in segment.get("screen_tracks", []) or [] if isinstance(track, Mapping)),
            None,
        )
        mic_track = segment.get("microphone_track") if isinstance(segment.get("microphone_track"), Mapping) else None
        webcam_track = segment.get("webcam_track") if isinstance(segment.get("webcam_track"), Mapping) else None
        row: dict[str, Any] = {
            "id": segment_id,
            "index": segment.get("index", index),
            "raw_started_at": segment.get("started_at"),
            "raw_ended_at": segment.get("ended_at"),
            "active_start_seconds": round(active_cursor, 3),
            "active_duration_seconds": round(active_duration, 3) if active_duration is not None else None,
            "active_end_seconds": round(active_cursor + active_duration, 3) if active_duration is not None else None,
            "duration_source": duration_source,
            "status": segment.get("status"),
            "screen_track": dict(screen_track) if screen_track else None,
            "microphone_track": dict(mic_track) if isinstance(mic_track, Mapping) else None,
            "webcam_track": dict(webcam_track) if isinstance(webcam_track, Mapping) else None,
        }
        rows.append(row)
        active_cursor += active_duration or 0.0

    if rows:
        return rows

    duration = _timeline_duration_floor(root, session, tracks, media_receipt, transcript={})
    screen_track = next((track for track in tracks if track.get("role") == "screen"), None)
    mic_track = next((track for track in tracks if track.get("role") == "microphone"), None)
    webcam_track = next((track for track in tracks if track.get("role") == "webcam"), None)
    return [
        {
            "id": "segment_0001",
            "index": 1,
            "raw_started_at": session.get("created_at"),
            "raw_ended_at": session.get("ended_at"),
            "active_start_seconds": 0.0,
            "active_duration_seconds": round(duration, 3) if duration is not None else None,
            "active_end_seconds": round(duration, 3) if duration is not None else None,
            "duration_source": "take_duration_floor" if duration is not None else None,
            "status": session.get("status") or "single_segment",
            "screen_track": dict(screen_track) if screen_track else None,
            "microphone_track": dict(mic_track) if mic_track else None,
            "webcam_track": dict(webcam_track) if webcam_track else None,
        }
    ]


def _timeline_duration_floor(
    root: Path,
    session: Mapping[str, Any],
    tracks: list[dict[str, Any]],
    media_receipt: Mapping[str, Any],
    transcript: Mapping[str, Any],
) -> float | None:
    candidates: list[float] = []
    for key in (
        "expected_active_duration_seconds",
        "rough_cut_duration_seconds",
        "spliced_screen_duration_seconds",
        "spliced_microphone_duration_seconds",
        "transcript_last_cue_end_seconds",
    ):
        value = _timeline_seconds(media_receipt.get(key))
        if value is not None:
            candidates.append(value)
    value = _timeline_seconds(transcript.get("duration_seconds"))
    if value is not None:
        candidates.append(value)
    for segment in transcript.get("segments", []) or []:
        if isinstance(segment, Mapping):
            value = _timeline_seconds(segment.get("end"))
            if value is not None:
                candidates.append(value)
    for marker in session.get("markers", []) or []:
        if isinstance(marker, Mapping):
            value = _timeline_seconds(marker.get("video_t_seconds"))
            if value is not None:
                candidates.append(value)
    duration = _timeline_seconds(session.get("duration_seconds"))
    if duration is not None:
        candidates.append(duration)
    for track in tracks:
        if track.get("role") not in {"screen", "microphone", "external_video"}:
            continue
        rel_path = track.get("relative_path")
        if not isinstance(rel_path, str):
            continue
        duration = _timeline_seconds(probe_media_duration_seconds(dict(session.get("config", {})), root / rel_path))
        if duration is not None:
            candidates.append(duration)
    return max(candidates) if candidates else None


def _timeline_sync_required_roles(config: Mapping[str, Any], plans: list[dict[str, Any]]) -> list[str]:
    roles = {str(plan.get("role")) for plan in plans if plan.get("role") in TIMELINE_SYNC_ROLES}
    if selected_capture_screens(config) or "screen" in roles:
        roles.add("screen")
    if config.get("microphone") or "microphone" in roles:
        roles.add("microphone")
    if config.get("webcam") or "webcam" in roles:
        roles.add("webcam")
    return sorted(role for role in roles if role in TIMELINE_SYNC_ROLES)


def _timeline_sync_plan_from_track(
    root: Path,
    config: dict[str, Any],
    *,
    role: str,
    segment: Mapping[str, Any],
    track: Mapping[str, Any] | None,
    expected_start_seconds: float,
    expected_duration: float,
    expected_source: str,
    fake_capture: bool,
) -> dict[str, Any]:
    rel = str(track.get("relative_path") or "").strip() if isinstance(track, Mapping) else ""
    path = root / rel if rel else None
    raw_duration = None
    if path and path.exists():
        raw_duration = expected_duration if fake_capture else probe_media_duration_seconds(config, path)
    return _timeline_sync_plan_for_track(
        role=role,
        segment=segment,
        track=track,
        relative_path=rel or None,
        raw_duration=raw_duration,
        expected_start_seconds=expected_start_seconds,
        expected_duration=expected_duration,
        expected_source=expected_source,
    )


def _timeline_sync_segment_plans(
    root: Path,
    config: dict[str, Any],
    session: Mapping[str, Any],
    tracks: list[dict[str, Any]],
    *,
    fake_capture: bool,
) -> list[dict[str, Any]]:
    segments = [
        segment
        for segment in session.get("media_segments", []) or []
        if isinstance(segment, Mapping)
    ]
    segments.sort(key=lambda segment: int(segment.get("index") or 0))
    plans: list[dict[str, Any]] = []
    if segments:
        for row in _segment_expected_rows(root, config, segments):
            expected_duration = row.get("expected_duration")
            if not expected_duration or float(expected_duration) <= 0:
                continue
            segment = row["segment"]
            expected_start = float(row.get("expected_start_seconds") or 0.0)
            expected_source = str(row.get("expected_source") or "unknown")
            for screen_track in segment.get("screen_tracks", []) or []:
                if isinstance(screen_track, Mapping):
                    plans.append(_timeline_sync_plan_from_track(
                        root,
                        config,
                        role="screen",
                        segment=segment,
                        track=screen_track,
                        expected_start_seconds=expected_start,
                        expected_duration=float(expected_duration),
                        expected_source=expected_source,
                        fake_capture=fake_capture,
                    ))
            webcam_track = segment.get("webcam_track")
            if isinstance(webcam_track, Mapping):
                plans.append(_timeline_sync_plan_from_track(
                    root,
                    config,
                    role="webcam",
                    segment=segment,
                    track=webcam_track,
                    expected_start_seconds=expected_start,
                    expected_duration=float(expected_duration),
                    expected_source=expected_source,
                    fake_capture=fake_capture,
                ))
            microphone_track = segment.get("microphone_track")
            if isinstance(microphone_track, Mapping):
                plans.append(_timeline_sync_plan_from_track(
                    root,
                    config,
                    role="microphone",
                    segment=segment,
                    track=microphone_track,
                    expected_start_seconds=expected_start,
                    expected_duration=float(expected_duration),
                    expected_source=expected_source,
                    fake_capture=fake_capture,
                ))
        return plans

    media_receipt = _read_json_dict(root / "render" / "media_timeline_receipt.json")
    transcript = _read_json_dict(root / "transcript" / "transcript.json")
    expected_duration = _timeline_duration_floor(root, session, tracks, media_receipt, transcript)
    if expected_duration is None:
        durations = [
            duration
            for duration in (
                probe_media_duration_seconds(config, root / str(track.get("relative_path")))
                for track in tracks
                if isinstance(track, Mapping) and track.get("relative_path")
            )
            if duration is not None
        ]
        expected_duration = max(durations) if durations else None
    if expected_duration is None or expected_duration <= 0:
        expected_duration = 6.0 if fake_capture else 0.0
    segment = {
        "id": "segment_0001",
        "index": 1,
        "started_at": session.get("created_at"),
        "timeline_started_at": session.get("created_at"),
    }
    for track in tracks:
        if not isinstance(track, Mapping) or track.get("role") not in TIMELINE_SYNC_ROLES:
            continue
        plans.append(_timeline_sync_plan_from_track(
            root,
            config,
            role=str(track.get("role")),
            segment=segment,
            track=track,
            expected_start_seconds=0.0,
            expected_duration=float(expected_duration),
            expected_source="single_segment_duration_floor",
            fake_capture=fake_capture,
        ))
    return plans


def _timeline_sync_cut_boundary_checks(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    by_role: dict[str, list[dict[str, Any]]] = {}
    for plan in plans:
        if plan.get("status") == "fail" or plan.get("relative_path") is None:
            continue
        by_role.setdefault(str(plan.get("role") or ""), []).append(plan)
    for role, rows in by_role.items():
        rows.sort(key=lambda row: (float(row.get("expected_start_seconds") or 0.0), str(row.get("segment_id") or "")))
        for previous, current in zip(rows, rows[1:]):
            previous_end = float(previous.get("expected_start_seconds") or 0.0) + float(previous.get("output_duration_seconds") or 0.0)
            current_start = float(current.get("expected_start_seconds") or 0.0)
            error_ms = abs(current_start - previous_end) * 1000.0
            status = (
                "fail"
                if error_ms > TIMELINE_SYNC_FAIL_THRESHOLD_MS
                else ("warn" if error_ms > TIMELINE_SYNC_WARN_THRESHOLD_MS else "pass")
            )
            checks.append({
                "role": role,
                "from_segment_id": previous.get("segment_id"),
                "to_segment_id": current.get("segment_id"),
                "expected_previous_end_seconds": round(previous_end, 6),
                "expected_current_start_seconds": round(current_start, 6),
                "boundary_error_ms": round(error_ms, 3),
                "status": status,
            })
    return checks


def _timeline_sync_spliced_roles(root: Path, tracks: list[dict[str, Any]]) -> set[str]:
    roles: set[str] = set()
    for track in tracks:
        role = str(track.get("role") or "")
        rel = str(track.get("relative_path") or "")
        if role not in TIMELINE_SYNC_ROLES or not rel.startswith("tracks/spliced/"):
            continue
        if (root / rel).exists():
            roles.add(role)
    return roles


def write_timeline_sync_receipt(root: Path) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    tracks = [
        dict(track)
        for track in session.get("tracks", []) or []
        if isinstance(track, Mapping)
    ]
    fake_capture = _is_fake_capture(config)
    plans = _timeline_sync_segment_plans(root, config, session, tracks, fake_capture=fake_capture)
    required_roles = _timeline_sync_required_roles(config, plans)
    roles_with_pass_or_warn = {
        str(plan.get("role"))
        for plan in plans
        if plan.get("status") in {"pass", "warn"}
    }
    missing_required_roles = [
        role
        for role in required_roles
        if role not in roles_with_pass_or_warn
    ]
    failing = [plan for plan in plans if plan.get("status") == "fail"]
    warning = [plan for plan in plans if plan.get("status") == "warn"]
    corrected = [plan for plan in plans if plan.get("correction_applied")]
    boundary_checks = _timeline_sync_cut_boundary_checks(plans)
    failing_boundaries = [row for row in boundary_checks if row.get("status") == "fail"]
    warning_boundaries = [row for row in boundary_checks if row.get("status") == "warn"]
    roles_requiring_splice = sorted(
        role
        for role in TIMELINE_SYNC_ROLES
        if (
            sum(1 for plan in plans if plan.get("role") == role) > 1
            or any(plan.get("role") == role and plan.get("correction_applied") for plan in plans)
        )
    )
    spliced_roles = _timeline_sync_spliced_roles(root, tracks)
    missing_spliced_roles = [
        role
        for role in roles_requiring_splice
        if role not in spliced_roles
    ]
    if missing_required_roles or missing_spliced_roles or failing or failing_boundaries or (required_roles and not plans):
        status = "fail"
    elif warning or warning_boundaries:
        status = "warn"
    else:
        status = "pass"
    role_summary = {
        role: {
            "track_count": sum(1 for row in plans if row.get("role") == role),
            "pass_count": sum(1 for row in plans if row.get("role") == role and row.get("status") == "pass"),
            "warn_count": sum(1 for row in plans if row.get("role") == role and row.get("status") == "warn"),
            "fail_count": sum(1 for row in plans if row.get("role") == role and row.get("status") == "fail"),
            "corrected_count": sum(1 for row in plans if row.get("role") == role and row.get("correction_applied")),
        }
        for role in sorted(TIMELINE_SYNC_ROLES)
        if any(row.get("role") == role for row in plans) or role in required_roles
    }
    if status == "pass":
        operator_line = (
            "Timeline sync passed: screen, webcam, and microphone tracks are bounded to the active segment clock."
        )
    elif missing_required_roles:
        operator_line = "Timeline sync failed: required recorded roles are missing: " + ", ".join(missing_required_roles) + "."
    elif missing_spliced_roles:
        operator_line = (
            "Timeline sync failed: correction is required but spliced output is missing for "
            + ", ".join(missing_spliced_roles)
            + "."
        )
    else:
        first_failure = next((plan for plan in failing if plan.get("failures")), None)
        if first_failure:
            operator_line = (
                f"Timeline sync failed: {first_failure.get('role')} {first_failure.get('relative_path')} "
                + ", ".join(str(item) for item in first_failure.get("failures") or [])
                + "."
            )
        else:
            operator_line = "Timeline sync failed: one or more cut boundaries exceeds the sync threshold."
    segments: dict[str, dict[str, Any]] = {}
    for plan in plans:
        segment_id = str(plan.get("segment_id") or "segment_0001")
        segment = segments.setdefault(
            segment_id,
            {
                "id": segment_id,
                "index": plan.get("segment_index"),
                "expected_start_seconds": plan.get("expected_start_seconds"),
                "expected_duration_seconds": plan.get("expected_duration_seconds"),
                "roles": {},
            },
        )
        role_rows = segment["roles"].setdefault(str(plan.get("role") or "unknown"), [])
        role_rows.append(plan)
    payload = {
        "schema": TIMELINE_SYNC_RECEIPT_SCHEMA,
        "command_version": TIMELINE_SYNC_COMMAND_VERSION,
        "created_at": now_iso(),
        "status": status,
        "take_id": session.get("take_id", root.name),
        "fake_capture": fake_capture,
        "timeline_clock": {
            "authority": "recording_session_capture_started_at",
            "segment_zero_reference": "media_segment_started_at",
            "frame_budget_ms": round(TIMELINE_SYNC_FRAME_BUDGET_MS, 3),
            "warn_threshold_ms": TIMELINE_SYNC_WARN_THRESHOLD_MS,
            "fail_threshold_ms": TIMELINE_SYNC_FAIL_THRESHOLD_MS,
            "cut_policy": "trim_to_segment_window_then_front_or_end_pad",
        },
        "required_roles": required_roles,
        "missing_required_roles": missing_required_roles,
        "role_summary": role_summary,
        "track_count": len(plans),
        "failing_track_count": len(failing),
        "warning_track_count": len(warning),
        "corrected_track_count": len(corrected),
        "roles_requiring_splice": roles_requiring_splice,
        "spliced_roles": sorted(spliced_roles),
        "missing_spliced_roles": missing_spliced_roles,
        "cut_boundary_checks": boundary_checks,
        "failing_boundary_count": len(failing_boundaries),
        "warning_boundary_count": len(warning_boundaries),
        "segments": list(segments.values()),
        "tracks": plans,
        "operator_line": operator_line,
    }
    write_json(root / TIMELINE_SYNC_RECEIPT_RELATIVE_PATH, payload)
    return payload


def _segment_id_for_time(segments: list[dict[str, Any]], active_time: float) -> str | None:
    if not segments:
        return None
    for segment in segments:
        start = _timeline_seconds(segment.get("active_start_seconds"), 0.0) or 0.0
        end = _timeline_seconds(segment.get("active_end_seconds"))
        if end is None:
            continue
        if start <= active_time <= end:
            return str(segment.get("id"))
    return str(segments[-1].get("id"))


def _parse_iso_datetime(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _pause_gap_rows(session: Mapping[str, Any]) -> list[dict[str, Any]]:
    created_at = _parse_iso_datetime(session.get("created_at"))
    if created_at is None:
        return []
    raw_events = [
        event
        for event in session.get("pause_events", []) or []
        if isinstance(event, Mapping) and _parse_iso_datetime(event.get("at_iso")) is not None
    ]
    raw_events.sort(key=lambda event: _parse_iso_datetime(event.get("at_iso")) or created_at)
    rows: list[dict[str, Any]] = []
    open_pause: Mapping[str, Any] | None = None
    for event in raw_events:
        if event.get("kind") == "pause":
            open_pause = event
        elif event.get("kind") == "resume" and open_pause is not None:
            pause_at = _parse_iso_datetime(open_pause.get("at_iso"))
            resume_at = _parse_iso_datetime(event.get("at_iso"))
            if pause_at is None or resume_at is None:
                open_pause = None
                continue
            wall_t = (pause_at - created_at).total_seconds()
            active_t = video_t_seconds(wall_t, list(raw_events), pause_at.isoformat())
            rows.append({
                "id": f"pause_gap_{len(rows) + 1:04d}",
                "pause_at": pause_at.isoformat(),
                "resume_at": resume_at.isoformat(),
                "active_time_seconds": round(active_t, 3),
                "raw_duration_seconds": round(max(0.0, (resume_at - pause_at).total_seconds()), 3),
            })
            open_pause = None
    return rows


def _marker_during_pause(session: Mapping[str, Any], marker: Mapping[str, Any]) -> bool:
    marker_at = _parse_iso_datetime(marker.get("created_at"))
    if marker_at is None:
        return False
    pause_start: dt.datetime | None = None
    for event in session.get("pause_events", []) or []:
        if not isinstance(event, Mapping):
            continue
        event_at = _parse_iso_datetime(event.get("at_iso"))
        if event_at is None:
            continue
        if event.get("kind") == "pause":
            pause_start = event_at
        elif event.get("kind") == "resume" and pause_start is not None:
            if pause_start <= marker_at <= event_at:
                return True
            pause_start = None
    return bool(pause_start and marker_at >= pause_start)


def _snapped_pause_gap_active_time(gap: Mapping[str, Any], segments: list[dict[str, Any]]) -> float:
    active_time = float(gap.get("active_time_seconds") or 0.0)
    pause_at = _parse_iso_datetime(gap.get("pause_at"))
    best_time = active_time
    best_distance = 1.0
    for segment in segments:
        active_end = _timeline_seconds(segment.get("active_end_seconds"))
        raw_end = _parse_iso_datetime(segment.get("raw_ended_at"))
        if active_end is None:
            continue
        wall_distance = abs((pause_at - raw_end).total_seconds()) if pause_at and raw_end else best_distance
        timeline_distance = abs(active_time - active_end)
        distance = min(wall_distance, timeline_distance)
        if distance <= best_distance:
            best_distance = distance
            best_time = active_end
    return best_time


def _transcript_cue_rows(transcript: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, segment in enumerate(transcript.get("segments", []) or [], start=1):
        if not isinstance(segment, Mapping):
            continue
        start = _timeline_seconds(segment.get("start"))
        end = _timeline_seconds(segment.get("end"))
        if start is None or end is None:
            continue
        rows.append({
            "id": str(segment.get("id") or f"cue_{index:04d}"),
            "start": start,
            "end": end,
            "text": segment.get("text") or "",
        })
    return rows


def _nearby_transcript_cue_ids(cues: list[dict[str, Any]], active_time: float) -> list[str]:
    for cue in cues:
        start = float(cue["start"])
        end = float(cue["end"])
        if start <= active_time <= end:
            return [str(cue["id"])]
    candidates: list[tuple[float, str]] = []
    for cue in cues:
        start = float(cue["start"])
        end = float(cue["end"])
        distance = min(abs(active_time - start), abs(active_time - end))
        if distance <= 1.0:
            candidates.append((distance, str(cue["id"])))
    candidates.sort()
    return [cue_id for _, cue_id in candidates[:1]]


def _active_timeline_events(
    session: Mapping[str, Any],
    segments: list[dict[str, Any]],
    transcript: Mapping[str, Any],
) -> list[dict[str, Any]]:
    cues = _transcript_cue_rows(transcript)
    events: list[dict[str, Any]] = []
    sorted_markers = sorted(
        [marker for marker in session.get("markers", []) or [] if isinstance(marker, Mapping)],
        key=lambda marker: _timeline_seconds(marker.get("video_t_seconds"), 0.0) or 0.0,
    )
    for index, marker in enumerate(sorted_markers, start=1):
        active_time = _timeline_seconds(marker.get("video_t_seconds"), 0.0) or 0.0
        during_pause = _marker_during_pause(session, marker)
        label = clean_take_title(marker.get("label"), fallback=f"Checkpoint {index}") or f"Checkpoint {index}"
        events.append({
            "id": str(marker.get("id") or f"checkpoint_{index:04d}"),
            "kind": "checkpoint_during_pause" if during_pause else "checkpoint",
            "active_time_seconds": round(active_time, 3),
            "wall_time_seconds": _timeline_seconds(marker.get("wall_t_seconds")),
            "raw_wall_time": marker.get("created_at"),
            "segment_id": _segment_id_for_time(segments, active_time),
            "label": label,
            "source": marker.get("source") or "marker",
            "marker": dict(marker),
            "nearby_transcript_cue_ids": _nearby_transcript_cue_ids(cues, active_time),
        })
    for gap in _pause_gap_rows(session):
        active_time = _snapped_pause_gap_active_time(gap, segments)
        events.append({
            "id": gap["id"],
            "kind": "pause_gap",
            "active_time_seconds": round(active_time, 3),
            "segment_id": _segment_id_for_time(segments, active_time),
            "label": "Pause removed",
            "source": "pause_resume",
            "raw_started_at": gap["pause_at"],
            "raw_ended_at": gap["resume_at"],
            "raw_duration_seconds": gap["raw_duration_seconds"],
            "nearby_transcript_cue_ids": _nearby_transcript_cue_ids(cues, active_time),
        })
    events.sort(key=lambda event: (float(event.get("active_time_seconds") or 0.0), str(event.get("id") or "")))
    return events


def _vtt_time(seconds: float) -> str:
    millis = int(round(max(0.0, seconds) * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def _ffmetadata_escape(value: Any) -> str:
    text = str(value or "")
    text = text.replace("\\", "\\\\").replace("\n", "\\n")
    return text.replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")


def _chapter_events(events: list[dict[str, Any]], duration: float | None) -> list[dict[str, Any]]:
    chapters = [event for event in events if event.get("kind") == "checkpoint"]
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(chapters):
        start = float(event.get("active_time_seconds") or 0.0)
        if index + 1 < len(chapters):
            end = float(chapters[index + 1].get("active_time_seconds") or start)
        elif duration is not None:
            end = duration
        else:
            end = start + 1.0
        if end <= start:
            end = start + 1.0
        row = dict(event)
        row["chapter_start_seconds"] = round(start, 3)
        row["chapter_end_seconds"] = round(end, 3)
        rows.append(row)
    return rows


def _write_timeline_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )


def _write_markers_vtt(root: Path, events: list[dict[str, Any]]) -> str:
    lines = ["WEBVTT", "", "NOTE Demo Take marker and pause events", ""]
    for event in events:
        start = float(event.get("active_time_seconds") or 0.0)
        end = start + 0.5
        if event.get("kind") == "pause_gap":
            label = f"Pause removed ({float(event.get('raw_duration_seconds') or 0.0):.1f}s)"
        else:
            label = str(event.get("label") or "Checkpoint")
        lines.extend([
            str(event.get("id") or ""),
            f"{_vtt_time(start)} --> {_vtt_time(end)}",
            label,
            "",
        ])
    path = root / "render" / "markers.vtt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return relative(root, path)


def _write_chapter_sidecars(root: Path, events: list[dict[str, Any]], duration: float | None) -> dict[str, Any]:
    chapters = _chapter_events(events, duration)
    vtt_lines = ["WEBVTT", "", "NOTE Demo Take checkpoint chapters", ""]
    metadata_lines = [";FFMETADATA1"]
    for index, event in enumerate(chapters, start=1):
        start = float(event["chapter_start_seconds"])
        end = float(event["chapter_end_seconds"])
        title = str(event.get("label") or f"Checkpoint {index}")
        vtt_lines.extend([
            str(event.get("id") or f"chapter_{index:04d}"),
            f"{_vtt_time(start)} --> {_vtt_time(end)}",
            title,
            "",
        ])
        metadata_lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={int(round(start * 1000))}",
            f"END={int(round(end * 1000))}",
            f"title={_ffmetadata_escape(title)}",
        ])
    vtt_path = root / "render" / "chapters.vtt"
    metadata_path = root / "render" / "chapters.ffmetadata"
    vtt_path.parent.mkdir(parents=True, exist_ok=True)
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")
    metadata_path.write_text("\n".join(metadata_lines) + "\n", encoding="utf-8")
    return {
        "chapter_count": len(chapters),
        "chapters": chapters,
        "chapters_vtt": relative(root, vtt_path),
        "chapters_ffmetadata": relative(root, metadata_path),
    }


def _write_transcript_with_markers(
    root: Path,
    transcript: Mapping[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    if not transcript:
        return {"status": "skipped", "reason": "transcript_missing"}
    cue_events: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        for cue_id in event.get("nearby_transcript_cue_ids", []) or []:
            cue_events.setdefault(str(cue_id), []).append(event)
    segments: list[dict[str, Any]] = []
    for index, segment in enumerate(transcript.get("segments", []) or [], start=1):
        if not isinstance(segment, Mapping):
            continue
        copied = dict(segment)
        cue_id = str(copied.get("id") or f"cue_{index:04d}")
        copied["id"] = cue_id
        attached = cue_events.get(cue_id, [])
        copied["timeline_event_ids"] = [str(event.get("id")) for event in attached]
        copied["timeline_events"] = [
            {
                "id": event.get("id"),
                "kind": event.get("kind"),
                "active_time_seconds": event.get("active_time_seconds"),
                "label": event.get("label"),
            }
            for event in attached
        ]
        segments.append(copied)
    payload = {
        "schema": "demo_take_transcript_with_markers_v0",
        "take_id": root.name,
        "created_at": now_iso(),
        "status": "ready",
        "source_transcript": "transcript/transcript.json",
        "segments": segments,
        "event_count": len(events),
        "events": events,
    }
    write_json(root / "render" / "transcript_with_markers.json", payload)
    return {"status": "ready", "path": "render/transcript_with_markers.json", "segment_count": len(segments)}


def write_active_timeline_projection(
    root: Path,
    config: dict[str, Any],
    session: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str] | None = None,
) -> dict[str, Any]:
    del failures
    media_receipt = _read_json_dict(root / "render" / "media_timeline_receipt.json")
    transcript = _read_json_dict(root / "transcript" / "transcript.json")
    segments = _active_timeline_segments(root, session, tracks, media_receipt)
    active_duration = _timeline_duration_floor(root, session, tracks, media_receipt, transcript)
    segment_end = max(
        [
            float(segment.get("active_end_seconds") or 0.0)
            for segment in segments
            if segment.get("active_end_seconds") is not None
        ]
        or [0.0]
    )
    if active_duration is None or active_duration < segment_end:
        active_duration = segment_end if segment_end > 0 else active_duration
    events = _active_timeline_events(session, segments, transcript)
    timeline = {
        "schema": "demo_take_active_timeline_v0",
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "status": "ready",
        "duration_seconds": round(active_duration, 3) if active_duration is not None else None,
        "segments": segments,
        "events": events,
        "event_count": len(events),
        "checkpoint_count": len([event for event in events if event.get("kind") == "checkpoint"]),
        "pause_gap_count": len([event for event in events if event.get("kind") == "pause_gap"]),
        "sources": {
            "session": "session.json",
            "media_timeline_receipt": "render/media_timeline_receipt.json" if media_receipt else None,
            "transcript": "transcript/transcript.json" if transcript else None,
        },
    }
    write_json(root / "active_timeline.json", timeline)
    _write_timeline_jsonl(root / "timeline_events.jsonl", events)
    markers_vtt = _write_markers_vtt(root, events)
    chapter_result = _write_chapter_sidecars(root, events, active_duration)
    transcript_result = _write_transcript_with_markers(root, transcript, events)
    input_paths = ["session.json", "active_timeline.json", "timeline_events.jsonl"]
    if media_receipt:
        input_paths.append("render/media_timeline_receipt.json")
    if transcript:
        input_paths.append("transcript/transcript.json")
    receipt = {
        "schema": "demo_take_timeline_projection_receipt_v0",
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "status": "ready",
        "duration_seconds": timeline["duration_seconds"],
        "segment_count": len(segments),
        "event_count": len(events),
        "checkpoint_count": timeline["checkpoint_count"],
        "pause_gap_count": timeline["pause_gap_count"],
        "chapter_count": chapter_result["chapter_count"],
        "outputs": {
            "active_timeline": "active_timeline.json",
            "timeline_events": "timeline_events.jsonl",
            "markers_vtt": markers_vtt,
            "chapters_vtt": chapter_result["chapters_vtt"],
            "chapters_ffmetadata": chapter_result["chapters_ffmetadata"],
            "transcript_with_markers": transcript_result.get("path"),
        },
        "input_hashes": _timeline_input_hashes(root, input_paths),
    }
    write_json(root / "render" / "timeline_projection_receipt.json", receipt)
    return timeline


def finalize_capture(root: Path) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    failures: list[str] = [
        failure
        for failure in session.get("known_failures", [])
        if not _is_recomputed_review_failure(failure)
    ]
    config = session["config"]
    tracks = session.get("tracks", [])
    markers = session.get("markers", [])
    pause_events = session.get("pause_events", [])
    prepare_failure_count = len(failures)
    append_postprocess_progress(
        root,
        "prepare_media_segments",
        "running",
        "Preparing segmented screen, microphone, and webcam tracks",
    )
    tracks = prepare_segment_tracks(root, config, session, failures)
    session["tracks"] = tracks
    append_postprocess_progress(
        root,
        "prepare_media_segments",
        "warn" if len(failures) > prepare_failure_count else "pass",
        "Segmented media tracks prepared",
        {"track_count": len(tracks), "new_failure_count": len(failures) - prepare_failure_count},
    )

    append_postprocess_progress(root, "stop_ffmpeg", "running", "Stopping ffmpeg capture processes")
    stop_failure_count = len(failures)
    _backend_call("DELETE", "/api/recording/active-take")

    stop_receipts = stop_capture_processes(root, session.get("processes", []), failures)
    session["process_stop_receipts"] = stop_receipts
    append_postprocess_progress(
        root,
        "stop_ffmpeg",
        "warn" if len(failures) > stop_failure_count else "pass",
        "One or more ffmpeg processes needed SIGTERM" if len(failures) > stop_failure_count else "ffmpeg capture processes stopped",
        {"process_count": len(session.get("processes", [])), "process_stop_receipts": stop_receipts},
    )

    append_postprocess_progress(root, "quick_render", "running", "Preparing quick playback review")
    render_failure_count = len(failures)
    write_render(root, config, tracks, failures, session=session)
    write_media_timeline_receipt(root, config, session, tracks, failures)
    render_receipt = json.loads((root / "render" / "render_receipt.json").read_text(encoding="utf-8")) if (root / "render" / "render_receipt.json").exists() else {}
    append_postprocess_progress(
        root,
        "quick_render",
        "pass" if render_receipt.get("status") == "ready" else "warn",
        "Quick playback ready" if render_receipt.get("status") == "ready" else "Quick playback render unavailable",
        {"status": render_receipt.get("status"), "output": render_receipt.get("output"), "new_failure_count": len(failures) - render_failure_count},
    )
    append_postprocess_progress(root, "review_audio", "running", "Preparing MP3 audio review")
    audio_receipt = write_review_audio_mp3(root, config, tracks, failures)
    append_postprocess_progress(
        root,
        "review_audio",
        "pass" if audio_receipt.get("status") == "ready" else "warn",
        "MP3 audio review ready" if audio_receipt.get("status") == "ready" else "MP3 audio review unavailable",
        audio_receipt,
    )
    append_postprocess_progress(root, "active_timeline", "running", "Projecting active timeline markers and chapters")
    active_timeline = write_active_timeline_projection(root, config, session, tracks, failures)
    write_json(session_path, session)
    timeline_sync_receipt = write_timeline_sync_receipt(root)
    append_postprocess_progress(
        root,
        "timeline_sync_receipt",
        "pass" if timeline_sync_receipt.get("status") == "pass" else "warn",
        "Timeline sync receipt written",
        {
            "status": timeline_sync_receipt.get("status"),
            "track_count": timeline_sync_receipt.get("track_count"),
            "corrected_track_count": timeline_sync_receipt.get("corrected_track_count"),
            "failing_track_count": timeline_sync_receipt.get("failing_track_count"),
            "failing_boundary_count": timeline_sync_receipt.get("failing_boundary_count"),
            "missing_required_roles": timeline_sync_receipt.get("missing_required_roles"),
        },
    )
    calibration_receipt = write_calibration_receipt(root)
    append_postprocess_progress(
        root,
        "calibration_receipt",
        "pass" if calibration_receipt.get("status") == "pass" else "warn",
        "Observed byte-slope calibration receipt written",
        {
            "status": calibration_receipt.get("status"),
            "track_count": calibration_receipt.get("track_count"),
            "failing_track_count": calibration_receipt.get("failing_track_count"),
            "missing_required_roles": calibration_receipt.get("missing_required_roles"),
        },
    )
    write_local_storage_receipt(root, config, session)
    append_postprocess_progress(
        root,
        "active_timeline",
        "pass",
        "Active timeline projected",
        {
            "event_count": active_timeline.get("event_count"),
            "checkpoint_count": active_timeline.get("checkpoint_count"),
            "pause_gap_count": active_timeline.get("pause_gap_count"),
        },
    )
    session["known_failures"] = failures
    write_json(session_path, session)
    write_json(
        root / "manifest.json",
        manifest(
            session["take_id"],
            root,
            "review_ready",
            config,
            tracks,
            failures,
            markers=markers,
            pause_events=pause_events,
            media_segments=session.get("media_segments", []),
        ),
    )
    return {
        "takeID": session["take_id"],
        "rootPath": str(root),
        "statusLines": [
            f"Finalized {session['take_id']} for review.",
            f"Screen track: {_track_status_detail(root, tracks)['screen_track'] or 'missing'}",
            f"Audio review: {audio_receipt.get('output') or 'unavailable'}",
        ],
        "knownFailures": failures,
    }


def stop_capture_only(root: Path) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    failures: list[str] = list(dict.fromkeys(session.get("known_failures", [])))
    config = session["config"]
    tracks = session.get("tracks", [])
    markers = session.get("markers", [])
    pause_events = session.get("pause_events", [])

    append_postprocess_progress(root, "stop_capture", "running", "Stopping capture processes")
    stop_failure_count = len(failures)
    _backend_call("DELETE", "/api/recording/active-take")
    stop_receipts = stop_capture_processes(root, session.get("processes", []), failures)
    session["process_stop_receipts"] = stop_receipts

    ended_at = now_iso()
    segments = session.get("media_segments", [])
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            if segment.get("status") in {None, "recording", "paused"}:
                segment["status"] = "stopped"
            if not segment.get("ended_at"):
                segment["ended_at"] = ended_at
        session["media_segments"] = segments

    append_postprocess_progress(
        root,
        "stop_capture",
        "warn" if len(failures) > stop_failure_count else "pass",
        "One or more capture processes needed SIGTERM" if len(failures) > stop_failure_count else "Capture processes stopped",
        {"process_count": len(session.get("processes", [])), "process_stop_receipts": stop_receipts},
    )
    write_active_timeline_projection(root, config, session, tracks, failures)
    session["known_failures"] = failures
    write_json(session_path, session)
    write_json(
        root / "manifest.json",
        manifest(
            session["take_id"],
            root,
            "stopped",
            config,
            tracks,
            failures,
            markers=markers,
            pause_events=pause_events,
            media_segments=session.get("media_segments", []),
        ),
    )
    status_lines = [
        f"Stopped {session['take_id']}.",
        "Replayable review has not been prepared yet.",
    ]
    return {
        "takeID": session["take_id"],
        "rootPath": str(root),
        "statusLines": status_lines,
        "knownFailures": failures,
    }


def postprocess(root: Path) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    failures: list[str] = session.get("known_failures", [])
    config = session["config"]
    tracks = session.get("tracks", [])
    markers = session.get("markers", [])
    pause_events = session.get("pause_events", [])
    prepare_failure_count = len(failures)
    append_postprocess_progress(
        root,
        "prepare_media_segments",
        "running",
        "Preparing segmented screen, microphone, and webcam tracks",
    )
    tracks = prepare_segment_tracks(root, config, session, failures)
    append_postprocess_progress(
        root,
        "prepare_media_segments",
        "warn" if len(failures) > prepare_failure_count else "pass",
        "Segmented media tracks prepared",
        {"track_count": len(tracks), "new_failure_count": len(failures) - prepare_failure_count},
    )
    session["tracks"] = tracks
    session["known_failures"] = failures
    write_json(session_path, session)

    write_json(
        root / "manifest.json",
        manifest(
            session["take_id"],
            root,
            "postprocessing",
            config,
            tracks,
            failures,
            markers=markers,
            pause_events=pause_events,
            media_segments=session.get("media_segments", []),
        ),
    )

    append_postprocess_progress(root, "sample_frames", "running", "Sampling frame thumbnails")
    frame_failure_count = len(failures)
    frame_records = sample_frames(root, config, tracks, failures)
    checkpoint_frame_records = sample_marker_frames(root, config, tracks, markers, failures)
    frame_records.extend(checkpoint_frame_records)
    append_postprocess_progress(
        root,
        "sample_frames",
        "warn" if len(failures) > frame_failure_count else "pass",
        "Sampled frame thumbnails" if frame_records else "No frame thumbnails were sampled",
        {"frame_count": len(frame_records), "checkpoint_frame_count": len(checkpoint_frame_records)},
    )
    write_json(
        root / "visual_index.json",
        {
            "schema": "demo_take_visual_index_v0",
            "take_id": session["take_id"],
            "created_at": now_iso(),
            "frames": frame_records,
        },
    )
    append_postprocess_progress(root, "transcribe", "running", "Running local transcription")
    transcribe_result = transcribe_track(root, config, tracks, failures)
    transcribe_status = transcribe_result.get("status")
    append_postprocess_progress(
        root,
        "transcribe",
        "pass" if transcribe_status == "ready" else ("fail" if transcribe_status == "failed" else "warn"),
        "Transcript ready" if transcribe_status == "ready" else "Transcript unavailable",
        transcribe_result,
    )
    if transcribe_result.get("status") == "ready":
        append_postprocess_progress(root, "voice_scan", "running", "Scanning transcript for voice marker phrases")
        voice_result = voice_scan(root)
        append_postprocess_progress(
            root,
            "voice_scan",
            "pass" if voice_result.get("status") == "ready" else "warn",
            "Voice marker scan complete",
            voice_result,
        )
        if voice_result.get("status") == "ready" and voice_result.get("matched_count", 0):
            session = json.loads((root / "session.json").read_text(encoding="utf-8"))
            markers = session.get("markers", [])
    else:
        append_postprocess_progress(root, "voice_scan", "warn", "Skipped voice marker scan because transcript is not ready")
    append_postprocess_progress(root, "view_timeline", "running", "Building view timeline from telemetry")
    build_view_timeline(root)
    view_timeline = json.loads((root / "view_timeline.json").read_text(encoding="utf-8")) if (root / "view_timeline.json").exists() else {}
    append_postprocess_progress(
        root,
        "view_timeline",
        "pass" if view_timeline.get("status") == "ready" else "warn",
        "View timeline built",
        {"status": view_timeline.get("status"), "event_count": view_timeline.get("event_count")},
    )
    append_postprocess_progress(root, "attention_spans", "running", "Building recorded-screen attention spans")
    attention_spans = build_attention_spans(root)
    append_postprocess_progress(
        root,
        "attention_spans",
        "pass" if attention_spans.get("status") == "ready" else "warn",
        "Attention spans built" if attention_spans.get("status") == "ready" else "Attention events unavailable",
        {"status": attention_spans.get("status"), "event_count": attention_spans.get("event_count"), "span_count": attention_spans.get("span_count")},
    )
    if transcribe_result.get("status") == "ready":
        enrich_transcript_with_views(root)
        enrich_transcript_with_attention(root)
        append_postprocess_progress(root, "per_view_segments", "running", "Building per-view narration segments")
        build_per_view_segments(root)
        per_view = json.loads((root / "per_view_segments.json").read_text(encoding="utf-8")) if (root / "per_view_segments.json").exists() else {}
        append_postprocess_progress(
            root,
            "per_view_segments",
            "pass",
            "Per-view narration segments built",
            {"row_count": per_view.get("row_count")},
        )
    else:
        append_postprocess_progress(root, "per_view_segments", "warn", "Skipped per-view narration segments because transcript is not ready")
    append_postprocess_progress(root, "intent_events", "running", "Building spoken-control intent events")
    build_intent_events(root)
    intent_events = json.loads((root / "intent_events.json").read_text(encoding="utf-8")) if (root / "intent_events.json").exists() else {}
    append_postprocess_progress(
        root,
        "intent_events",
        "pass" if intent_events.get("status") in {"ready", "no_events"} else "warn",
        "Intent events built",
        {"status": intent_events.get("status"), "event_count": intent_events.get("event_count")},
    )
    append_postprocess_progress(root, "speech_blocks", "running", "Building spoken-word splice blocks")
    speech_blocks = build_speech_blocks(root)
    append_postprocess_progress(
        root,
        "speech_blocks",
        "pass" if speech_blocks.get("status") == "ready" else "warn",
        "Speech blocks built" if speech_blocks.get("status") == "ready" else "Speech blocks unavailable",
        {"status": speech_blocks.get("status"), "block_count": speech_blocks.get("block_count")},
    )
    append_postprocess_progress(root, "edl", "running", "Rebuilding marker-derived EDL")
    write_edl(root, session["take_id"], tracks, markers)
    append_postprocess_progress(root, "edl", "pass", "EDL rebuilt", {"marker_count": len(markers)})
    append_postprocess_progress(root, "otio_export", "running", "Projecting EDL to OpenTimelineIO format")
    write_edl_otio(root, session["take_id"], tracks, markers)
    otio_present = (root / "edl.otio").exists()
    append_postprocess_progress(
        root,
        "otio_export",
        "pass" if otio_present else "warn",
        "OTIO timeline written" if otio_present else "OTIO timeline missing",
        {"output": "edl.otio" if otio_present else None, "annex": "annexes/opentimelineio/repo/"},
    )
    append_postprocess_progress(root, "multimodal_index", "running", "Building editor-facing multimodal index")
    multimodal_index = build_multimodal_index(root)
    append_postprocess_progress(
        root,
        "multimodal_index",
        "pass" if multimodal_index.get("status") == "ready" else "warn",
        "Multimodal editor index built" if multimodal_index.get("status") == "ready" else "Multimodal editor index unavailable",
        {"status": multimodal_index.get("status"), "outputs": multimodal_index.get("outputs")},
    )
    append_postprocess_progress(root, "rough_render", "running", "Rendering rough screen-plus-microphone cut")
    render_failure_count = len(failures)
    write_render(root, config, tracks, failures, session=session)
    write_media_timeline_receipt(root, config, session, tracks, failures)
    append_postprocess_progress(root, "active_timeline", "running", "Projecting active timeline markers and chapters")
    active_timeline = write_active_timeline_projection(root, config, session, tracks, failures)
    timeline_sync_receipt = write_timeline_sync_receipt(root)
    append_postprocess_progress(
        root,
        "timeline_sync_receipt",
        "pass" if timeline_sync_receipt.get("status") == "pass" else "warn",
        "Timeline sync receipt written",
        {
            "status": timeline_sync_receipt.get("status"),
            "track_count": timeline_sync_receipt.get("track_count"),
            "corrected_track_count": timeline_sync_receipt.get("corrected_track_count"),
            "failing_track_count": timeline_sync_receipt.get("failing_track_count"),
            "failing_boundary_count": timeline_sync_receipt.get("failing_boundary_count"),
            "missing_required_roles": timeline_sync_receipt.get("missing_required_roles"),
        },
    )
    calibration_receipt = write_calibration_receipt(root)
    append_postprocess_progress(
        root,
        "calibration_receipt",
        "pass" if calibration_receipt.get("status") == "pass" else "warn",
        "Observed byte-slope calibration receipt written",
        {
            "status": calibration_receipt.get("status"),
            "track_count": calibration_receipt.get("track_count"),
            "failing_track_count": calibration_receipt.get("failing_track_count"),
            "missing_required_roles": calibration_receipt.get("missing_required_roles"),
        },
    )
    write_local_storage_receipt(root, config, session)
    append_postprocess_progress(
        root,
        "active_timeline",
        "pass",
        "Active timeline projected",
        {
            "event_count": active_timeline.get("event_count"),
            "checkpoint_count": active_timeline.get("checkpoint_count"),
            "pause_gap_count": active_timeline.get("pause_gap_count"),
        },
    )
    render_receipt = json.loads((root / "render" / "render_receipt.json").read_text(encoding="utf-8")) if (root / "render" / "render_receipt.json").exists() else {}
    append_postprocess_progress(
        root,
        "rough_render",
        "pass" if render_receipt.get("status") == "ready" else "warn",
        "Rough render complete" if render_receipt.get("status") == "ready" else "Rough render unavailable",
        {"status": render_receipt.get("status"), "output": render_receipt.get("output"), "new_failure_count": len(failures) - render_failure_count},
    )
    append_postprocess_progress(root, "review_audio", "running", "Preparing MP3 audio review")
    audio_receipt = write_review_audio_mp3(root, config, tracks, failures)
    append_postprocess_progress(
        root,
        "review_audio",
        "pass" if audio_receipt.get("status") == "ready" else "warn",
        "MP3 audio review ready" if audio_receipt.get("status") == "ready" else "MP3 audio review unavailable",
        audio_receipt,
    )
    if config_bool(config, "autoedit_cleanup_after_stop", False):
        append_postprocess_progress(root, "autoedit_cleanup", "running", "Running auto-editor silence cleanup on rough cut")
        autoedit_receipt = write_autoedit_cleanup(root, failures)
    else:
        autoedit_receipt = {
            "schema": "demo_take_autoedit_receipt_v0",
            "status": "skipped",
            "reason": "disabled_by_default_no_extra_proxy_storage",
            "input": render_receipt.get("output"),
            "output": None,
            "tool": "auto-editor",
            "tool_resolved": None,
            "annex_reference": "annexes/auto-editor/repo/",
        }
        write_json(root / "render" / "autoedit_receipt.json", autoedit_receipt)
    autoedit_status = autoedit_receipt.get("status")
    append_postprocess_progress(
        root,
        "autoedit_cleanup",
        "pass" if autoedit_status == "ready" else ("warn" if autoedit_status in {"unavailable", "skipped"} else "fail"),
        {
            "ready": "Auto-editor cleanup complete",
            "unavailable": "auto-editor not on PATH; install via `pip install auto-editor`",
            "skipped": "auto-editor cleanup skipped",
            "failed": "auto-editor cleanup failed; see logs/autoedit.log",
        }.get(autoedit_status, f"auto-editor stage status={autoedit_status}"),
        {"status": autoedit_status, "output": autoedit_receipt.get("output"), "tool_resolved": autoedit_receipt.get("tool_resolved")},
    )
    append_postprocess_progress(root, "semantic_proxy", "running", "Building transcript/silence semantic proxy")
    semantic_proxy = build_semantic_proxy(root)
    append_postprocess_progress(
        root,
        "semantic_proxy",
        "pass" if semantic_proxy.get("status") == "ready" else "warn",
        "Semantic inspection proxy ready" if semantic_proxy.get("status") == "ready" else "Semantic inspection proxy unavailable",
        {
            "status": semantic_proxy.get("status"),
            "section_count": semantic_proxy.get("section_count"),
            "speech_section_count": semantic_proxy.get("speech_section_count"),
            "silence_section_count": semantic_proxy.get("silence_section_count"),
        },
    )
    write_local_storage_receipt(root, config, session)
    write_json(
        root / "manifest.json",
        manifest(
            session["take_id"],
            root,
            "package_ready",
            config,
            tracks,
            failures,
            markers=markers,
            pause_events=pause_events,
            media_segments=session.get("media_segments", []),
        ),
    )
    append_postprocess_progress(root, "manifest_ready", "pass", "Manifest updated for package-ready state")
    status_lines = [f"Stopped and postprocessed {session['take_id']}."]
    if cloud_archive_after_stop(config):
        append_postprocess_progress(root, "cloud_archive", "running", "Uploading source-quality take package to cloud archive")
        archive_result = archive_originals(
            root,
            remote=cloud_archive_remote(config),
            local_retention=cloud_archive_local_retention(config),
        )
        archive_status = str(archive_result.get("status") or "failed")
        failures.extend(str(item) for item in archive_result.get("knownFailures", []) if item)
        status_lines.extend(archive_result.get("statusLines", []))
        append_postprocess_progress(
            root,
            "cloud_archive",
            "pass" if archive_status in {"ready", "skipped"} else ("warn" if archive_status == "partial" else "fail"),
            "Cloud archive completed" if archive_status in {"ready", "skipped"} else "Cloud archive did not complete cleanly",
            {
                "status": archive_status,
                "remote_take_path": archive_result.get("remoteTakePath"),
                "local_retention": archive_result.get("localRetention"),
                "manifest_sha256": archive_result.get("manifestSha256"),
            },
        )
        write_json(
            root / "manifest.json",
            manifest(
                session["take_id"],
                root,
                "package_ready",
                config,
                tracks,
                list(dict.fromkeys(failures)),
                markers=markers,
                pause_events=pause_events,
                media_segments=session.get("media_segments", []),
            ),
        )
    append_postprocess_progress(root, "package_ready", "pass", "Take package postprocess complete")
    spillway_item = enqueue_storage_spillway_after_finalize(root, failures)
    return {
        "takeID": session["take_id"],
        "rootPath": str(root),
        "statusLines": status_lines,
        "storageSpillway": spillway_item,
        "knownFailures": list(dict.fromkeys(failures)),
    }


def stop(root: Path) -> dict[str, Any]:
    finalize_capture(root)
    return postprocess(root)


NATIVE_STOP_COMPACTION_BACKENDS = {"screencapturekit", "screen_capture_kit", "native_screen"}


def should_compact_native_efficient_after_stop(config: Mapping[str, Any]) -> bool:
    if not config_bool(config, "compact_after_stop", True):
        return False
    if _is_fake_capture(dict(config)):
        return False
    backend = str(config.get("capture_backend") or "").strip().lower()
    return backend in NATIVE_STOP_COMPACTION_BACKENDS and recording_quality(dict(config)) == DEFAULT_RECORDING_QUALITY


def compact_native_efficient_after_stop(root: Path, config: Mapping[str, Any], failures: list[str]) -> dict[str, Any]:
    if not should_compact_native_efficient_after_stop(config):
        return {
            "schema": "demo_take_post_stop_compaction_result_v0",
            "status": "skipped",
            "reason": "not_native_efficient_stop_compaction",
        }
    append_postprocess_progress(
        root,
        "post_stop_storage_compaction",
        "running",
        "Compacting native capture videos to the 720p30 efficient profile",
    )
    try:
        result = compact_storage(root, prune_source_media=False, force=False)
    except Exception as exc:  # pragma: no cover - defensive stop path containment
        message = f"Post-stop 720p30 storage compaction failed: {exc}"
        failures.append(message)
        append_postprocess_progress(
            root,
            "post_stop_storage_compaction",
            "fail",
            message,
            {"error": str(exc)},
        )
        return {
            "schema": "demo_take_post_stop_compaction_result_v0",
            "status": "failed",
            "reason": "compact_storage_exception",
            "knownFailures": failures,
            "statusLines": [message],
        }
    status = str(result.get("status") or "unknown")
    progress_status = "pass" if status in {"ready", "skipped"} else "warn"
    append_postprocess_progress(
        root,
        "post_stop_storage_compaction",
        progress_status,
        "Native capture videos compacted to the 720p30 efficient profile"
        if status == "ready"
        else f"Native capture storage compaction finished with status: {status}",
        {"compact_storage": result.get("compactStorage")},
    )
    return result


def _is_fake_capture(config: dict[str, Any]) -> bool:
    backend = str(config.get("capture_backend") or "").strip().lower()
    ffmpeg = str(config.get("ffmpeg_path") or "").strip().lower()
    return backend == "fake" or ffmpeg.startswith("fake-")


def _fake_frame_records(root: Path, tracks: list[dict[str, Any]], interval: int) -> list[dict[str, Any]]:
    frame_records: list[dict[str, Any]] = []
    frames_dir = root / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for track in tracks:
        if track["role"] not in {"screen", "webcam"}:
            continue
        produced = sorted(frames_dir.glob(f"{track['id']}_*.jpg"))
        if not produced:
            first_frame = frames_dir / f"{track['id']}_000001.jpg"
            first_frame.write_bytes(b"fake frame\n")
            produced = [first_frame]
        for offset, frame in enumerate(produced):
            frame_records.append(
                {
                    "track_id": track["id"],
                    "timestamp_seconds": offset * interval,
                    "relative_path": relative(root, frame),
                }
            )
    return frame_records


def _safe_marker_frame_stem(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "marker")).strip("._")
    return text[:80] or "marker"


def sample_marker_frames(
    root: Path,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    markers: list[dict[str, Any]],
    failures: list[str],
) -> list[dict[str, Any]]:
    if not markers:
        return []
    screen = next((track for track in tracks if track.get("role") == "screen"), None)
    if not screen:
        return []

    records: list[dict[str, Any]] = []
    if _is_fake_capture(config):
        for marker in markers:
            marker_id = _safe_marker_frame_stem(marker.get("id"))
            frame = root / "frames" / f"checkpoint_{marker_id}.jpg"
            frame.parent.mkdir(parents=True, exist_ok=True)
            frame.write_bytes(b"fake checkpoint frame\n")
            records.append({
                "track_id": screen.get("id"),
                "timestamp_seconds": round(float(marker.get("video_t_seconds") or 0.0), 3),
                "relative_path": relative(root, frame),
                "source": "checkpoint_marker",
                "marker_id": marker.get("id"),
                "marker_source": marker.get("source"),
                "marker_label": marker.get("label"),
            })
        return records

    ffmpeg = config.get("ffmpeg_path")
    source = root / str(screen.get("relative_path") or "")
    if not ffmpeg or not source.exists():
        failures.append("Cannot sample checkpoint frames because the screen track or ffmpeg is missing.")
        return []

    log_path = root / "logs" / "checkpoint_frames.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    for marker in markers:
        try:
            timestamp = max(0.0, float(marker.get("video_t_seconds") or 0.0))
        except (TypeError, ValueError):
            failures.append(f"Skipping checkpoint frame for marker {marker.get('id')}: invalid video_t_seconds.")
            continue
        marker_id = _safe_marker_frame_stem(marker.get("id"))
        output = root / "frames" / f"checkpoint_{screen.get('id', 'screen')}_{marker_id}.jpg"
        command = [
            str(ffmpeg),
            "-hide_banner",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            frame_jpeg_quality(config),
            str(output),
        ]
        with log_path.open("ab") as log:
            log.write(f"=== {now_iso()} checkpoint frame: {' '.join(command)}\n".encode("utf-8"))
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        if status != 0 or not output.exists():
            failures.append(f"Could not sample checkpoint frame for marker {marker.get('id')}; see logs/checkpoint_frames.log.")
            continue
        records.append({
            "track_id": screen.get("id"),
            "timestamp_seconds": round(timestamp, 3),
            "relative_path": relative(root, output),
            "source": "checkpoint_marker",
            "marker_id": marker.get("id"),
            "marker_source": marker.get("source"),
            "marker_label": marker.get("label"),
        })
    return records


def sample_frames(root: Path, config: dict[str, Any], tracks: list[dict[str, Any]], failures: list[str]) -> list[dict[str, Any]]:
    interval = int(config["screenshot_interval_seconds"])
    if _is_fake_capture(config):
        return _fake_frame_records(root, tracks, interval)
    ffmpeg = config["ffmpeg_path"]
    frame_records: list[dict[str, Any]] = []
    for track in tracks:
        if track["role"] not in {"screen", "webcam"}:
            continue
        source = root / track["relative_path"]
        if not source.exists():
            failures.append(f"Cannot sample missing track {track['relative_path']}.")
            continue
        pattern = root / "frames" / f"{track['id']}_%06d.jpg"
        log_path = root / "logs" / f"frames_{track['id']}.log"
        frame_filter = frame_thumbnail_filter(config, interval)
        jpeg_quality = frame_jpeg_quality(config)
        with log_path.open("ab") as log:
            status = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    frame_filter,
                    "-q:v",
                    jpeg_quality,
                    str(pattern),
                ],
                stdout=log,
                stderr=log,
                check=False,
            ).returncode
        produced = sorted((root / "frames").glob(f"{track['id']}_*.jpg"))
        if status != 0 or not produced:
            first_frame = root / "frames" / f"{track['id']}_000001.jpg"
            with log_path.open("ab") as log:
                fallback_status = subprocess.run(
                    [
                        ffmpeg,
                        "-hide_banner",
                        "-y",
                        "-ss",
                        "0",
                        "-i",
                        str(source),
                        "-frames:v",
                        "1",
                        "-vf",
                        frame_thumbnail_filter(config),
                        "-q:v",
                        jpeg_quality,
                        str(first_frame),
                    ],
                    stdout=log,
                    stderr=log,
                    check=False,
                ).returncode
            produced = sorted((root / "frames").glob(f"{track['id']}_*.jpg"))
            if fallback_status != 0 or not produced:
                failures.append(f"Frame sampling failed for {track['relative_path']}.")
                continue
        if status != 0 and produced:
            # Short calibration takes can be shorter than the sampling interval.
            # The first-frame fallback is enough to seed visual_index.json.
            pass
        if not produced:
            failures.append(f"Frame sampling failed for {track['relative_path']}.")
            continue
        for offset, frame in enumerate(produced):
            frame_records.append(
                {
                    "track_id": track["id"],
                    "timestamp_seconds": offset * interval,
                    "relative_path": relative(root, frame),
                }
            )
    return frame_records


def _config_bool(config: dict[str, Any], key: str, default: bool) -> bool:
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def _track_bytes(root: Path, track: dict[str, Any] | None) -> int | None:
    if not track:
        return None
    try:
        return (root / track["relative_path"]).stat().st_size
    except (KeyError, OSError):
        return None


def _track_status_detail(root: Path, tracks: list[dict[str, Any]]) -> dict[str, Any]:
    screen = next((track for track in tracks if track.get("role") == "screen"), None)
    microphone = next((track for track in tracks if track.get("role") == "microphone"), None)
    return {
        "screen_track": screen.get("relative_path") if screen else None,
        "screen_track_bytes": _track_bytes(root, screen),
        "microphone_track": microphone.get("relative_path") if microphone else None,
        "microphone_track_bytes": _track_bytes(root, microphone),
    }


def probe_audio_signal(root: Path, config: dict[str, Any], audio_path: Path) -> dict[str, Any]:
    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg:
        return {"status": "unknown", "reason": "ffmpeg_missing", "input": relative(root, audio_path)}

    seconds = _config_int(config, "transcribe_audio_probe_seconds", 60, minimum=5, maximum=600)
    log_path = root / "logs" / "transcribe_audio_probe.log"
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-t",
        str(seconds),
        "-i",
        str(audio_path),
        "-vn",
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=max(30.0, float(seconds) + 20.0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(str(exc), encoding="utf-8")
        return {
            "status": "failed",
            "reason": "probe_error",
            "input": relative(root, audio_path),
            "log": relative(root, log_path),
        }

    probe_output = getattr(proc, "stdout", "") or ""
    log_path.write_text(probe_output, encoding="utf-8")
    mean_match = re.search(r"mean_volume:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*dB", probe_output)
    max_match = re.search(r"max_volume:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*dB", probe_output)

    def parse_db(match: re.Match[str] | None) -> float | None:
        if not match:
            return None
        value = match.group(1)
        if value == "-inf":
            return float("-inf")
        try:
            return float(value)
        except ValueError:
            return None

    mean_volume = parse_db(mean_match)
    max_volume = parse_db(max_match)
    if proc.returncode != 0:
        return {
            "status": "failed",
            "reason": f"ffmpeg_exit_{proc.returncode}",
            "input": relative(root, audio_path),
            "log": relative(root, log_path),
            "mean_volume_db": mean_volume,
            "max_volume_db": max_volume,
        }
    if max_volume is not None and max_volume <= -55.0:
        return {
            "status": "silent",
            "reason": "max_volume_below_threshold",
            "input": relative(root, audio_path),
            "log": relative(root, log_path),
            "mean_volume_db": mean_volume,
            "max_volume_db": max_volume,
            "threshold_db": -55.0,
        }
    warnings: list[str] = []
    if max_volume is not None and max_volume >= -0.5:
        warnings.append("audio_near_clipping")
    if mean_volume is not None and mean_volume >= -8.0:
        warnings.append("audio_very_hot")
    return {
        "status": "ready" if not warnings else "warn",
        "input": relative(root, audio_path),
        "log": relative(root, log_path),
        "mean_volume_db": mean_volume,
        "max_volume_db": max_volume,
        "warnings": warnings,
    }


def prepare_transcription_audio(
    root: Path,
    config: dict[str, Any],
    audio_path: Path,
) -> tuple[Path, dict[str, Any]]:
    output = root / TRANSCRIPTION_AUDIO_CACHE_RELATIVE_PATH
    if audio_path.exists():
        try:
            if audio_path.resolve() == output.resolve():
                return audio_path, {
                    "status": "ready",
                    "reason": "cached_transcription_audio_reused",
                    "input": relative(root, audio_path),
                    "output": relative(root, output),
                    "sample_rate_hz": 16000,
                    "channels": 1,
                }
        except OSError:
            pass

    if not _config_bool(config, "transcribe_preprocess_audio", True):
        return audio_path, {
            "status": "skipped",
            "reason": "disabled",
            "input": relative(root, audio_path),
            "output": None,
        }

    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg:
        return audio_path, {
            "status": "skipped",
            "reason": "ffmpeg_missing",
            "input": relative(root, audio_path),
            "output": None,
        }

    log_path = root / "logs" / "transcribe_audio_prep.log"
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-y",
        "-i",
        str(audio_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-af",
        "highpass=f=80,lowpass=f=7800,loudnorm=I=-16:TP=-1.5:LRA=11",
        str(output),
    ]
    timeout = _scaled_media_timeout_seconds(
        config,
        "transcribe_audio_prep_timeout_seconds",
        DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS,
        audio_path,
        duration_multiplier=0.25,
        overhead_seconds=120,
        maximum=3600,
    )
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            log.write(f"transcription audio prep timed out after {timeout}s\n".encode("utf-8"))
            status = 124

    if status == 0 and output.exists():
        return output, {
            "status": "ready",
            "input": relative(root, audio_path),
            "output": relative(root, output),
            "ffmpeg": str(ffmpeg),
            "filters": "highpass=f=80,lowpass=f=7800,loudnorm=I=-16:TP=-1.5:LRA=11",
            "sample_rate_hz": 16000,
            "channels": 1,
        }
    return audio_path, {
        "status": "failed",
        "reason": f"ffmpeg_exit_{status}",
        "input": relative(root, audio_path),
        "output": None,
        "ffmpeg": str(ffmpeg),
        "log": relative(root, log_path),
    }


def _annotate_transcript_metadata(
    root: Path,
    transcript_json: Path,
    *,
    provider: str,
    provider_detail: dict[str, Any],
    audio_preprocess: dict[str, Any],
    transcription_audio: Path,
) -> None:
    try:
        payload = json.loads(transcript_json.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    if payload.get("status") != "ready":
        return
    payload["provider"] = provider
    payload["provider_detail"] = provider_detail
    payload["transcription_audio"] = relative(root, transcription_audio)
    payload["audio_preprocess"] = audio_preprocess
    write_json(transcript_json, payload)


def _timestamp_string_to_seconds(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().strip("[]")
    match = re.match(r"(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:[,.](\d{1,3}))?$", text)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int((match.group(4) or "0").ljust(3, "0")[:3])
    return float(hours * 3600 + minutes * 60 + seconds) + (millis / 1000.0)


def _whisper_cpp_time_seconds(row: dict[str, Any], key: str) -> float | None:
    offsets = row.get("offsets")
    if isinstance(offsets, dict) and key in offsets:
        try:
            return float(offsets[key]) / 1000.0
        except (TypeError, ValueError):
            pass
    timestamps = row.get("timestamps")
    if isinstance(timestamps, dict) and key in timestamps:
        return _timestamp_string_to_seconds(timestamps.get(key))
    return _timestamp_string_to_seconds(row.get(key))


def _token_probability(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _whisper_cpp_words_from_tokens(tokens: list[Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    current_text = ""
    current_start: float | None = None
    current_end: float | None = None
    current_probabilities: list[float] = []

    def flush() -> None:
        nonlocal current_text, current_start, current_end, current_probabilities
        word = _clean_text(current_text).strip()
        if word and current_start is not None and current_end is not None:
            record: dict[str, Any] = {
                "word": word,
                "start": round(current_start, 3),
                "end": round(max(current_start, current_end), 3),
            }
            probability = _token_probability(current_probabilities)
            if probability is not None:
                record["probability"] = probability
            words.append(record)
        current_text = ""
        current_start = None
        current_end = None
        current_probabilities = []

    for token in tokens:
        if not isinstance(token, dict):
            continue
        raw = str(token.get("text") or token.get("token") or "")
        if not raw:
            continue
        if raw.startswith("[_") and raw.endswith("]"):
            continue
        start = _whisper_cpp_time_seconds(token, "from")
        end = _whisper_cpp_time_seconds(token, "to")
        if start is None or end is None:
            continue
        text = raw.replace("▁", " ")
        stripped = text.strip()
        if not stripped:
            continue
        if current_text and text[:1].isspace() and re.search(r"[A-Za-z0-9]", stripped):
            flush()
        if not current_text:
            current_start = start
        current_text += stripped if re.fullmatch(r"[^\w\s]+", stripped) else text
        current_end = end
        try:
            current_probabilities.append(float(token.get("p")))
        except (TypeError, ValueError):
            pass
    flush()
    return words


def _whisper_cpp_words_from_segment_text(text: Any, start: float, end: float) -> list[dict[str, Any]]:
    tokens = [match.group(0) for match in re.finditer(r"\S+", _clean_text(text))]
    if not tokens:
        return []
    bounded_end = max(start + 0.001, end)
    step = (bounded_end - start) / len(tokens)
    rows: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        word_start = start + (index * step)
        word_end = bounded_end if index == len(tokens) - 1 else start + ((index + 1) * step)
        rows.append({
            "word": token,
            "start": round(word_start, 3),
            "end": round(max(word_start, word_end), 3),
        })
    return rows


def _normalise_whisper_cpp_payload(
    root: Path,
    raw_payload: dict[str, Any],
    *,
    model: str,
    language: str | None,
    source_track: str,
    audio_preprocess: dict[str, Any],
    transcription_audio: Path,
    binary: Path,
    model_path: Path,
) -> dict[str, Any]:
    raw_segments = raw_payload.get("transcription", [])
    if not isinstance(raw_segments, list):
        raw_segments = []
    result = raw_payload.get("result") if isinstance(raw_payload.get("result"), dict) else {}
    segments: list[dict[str, Any]] = []
    words: list[dict[str, Any]] = []
    duration = 0.0
    for index, segment in enumerate(raw_segments):
        if not isinstance(segment, dict):
            continue
        start = _whisper_cpp_time_seconds(segment, "from") or 0.0
        end = _whisper_cpp_time_seconds(segment, "to")
        if end is None:
            end = start
        token_words = _whisper_cpp_words_from_tokens(segment.get("tokens", []) if isinstance(segment.get("tokens"), list) else [])
        if not token_words:
            token_words = _whisper_cpp_words_from_segment_text(segment.get("text", ""), start, end)
        duration = max(duration, end)
        segment_words: list[dict[str, Any]] = []
        for word in token_words:
            word_record = dict(word)
            word_record["transcript_segment_id"] = f"seg_{index:04d}"
            segment_words.append(word_record)
            words.append(word_record)
        segments.append(
            {
                "id": f"seg_{index:04d}",
                "start": round(start, 3),
                "end": round(max(start, end), 3),
                "text": _clean_text(segment.get("text", "")),
                "words": segment_words,
            }
        )
    return {
        "schema": "demo_take_transcript_v0",
        "status": "ready",
        "created_at": now_iso(),
        "provider": "whisper_cpp",
        "provider_detail": {
            "binary": str(binary),
            "model_path": str(model_path),
            "json_mode": "output-json-full",
        },
        "model": model,
        "language": str(result.get("language") or language or ""),
        "source_track": source_track,
        "transcription_audio": relative(root, transcription_audio),
        "audio_preprocess": audio_preprocess,
        "duration_seconds": round(duration, 3),
        "segments": segments,
        "words": words,
        "segment_count": len(segments),
        "word_count": len(words),
    }


def _srt_timestamp(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _write_srt_from_segments(path: Path, segments: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        lines.append(str(index))
        lines.append(f"{_srt_timestamp(float(segment.get('start') or 0.0))} --> {_srt_timestamp(float(segment.get('end') or 0.0))}")
        lines.append(_clean_text(segment.get("text", "")))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_ready_transcript(root: Path) -> dict[str, Any]:
    try:
        payload = json.loads((root / "transcript" / "transcript.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) and payload.get("status") == "ready" else {}


def _clear_resolved_transcript_failures(failures: list[str]) -> None:
    failures[:] = [
        failure
        for failure in failures
        if failure != MICROPHONE_TRACK_MISSING_TRANSCRIBE_FAILURE
    ]


def _retain_ready_transcript_result(
    root: Path,
    *,
    started_at: str,
    failure_reason: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    existing = _read_ready_transcript(root)
    if not existing:
        return None
    result = {
        "status": "ready",
        "reason": "existing_ready_transcript_retained",
        "retained_after": failure_reason,
        "source_track": existing.get("source_track"),
        "transcription_audio": existing.get("transcription_audio"),
        "segment_count": existing.get("segment_count") or len(existing.get("segments") or []),
        "word_count": existing.get("word_count") or len(existing.get("words") or []),
    }
    receipt_detail = dict(detail or {})
    receipt_detail["retained_transcript"] = {
        "status": "ready",
        "source_track": result.get("source_track"),
        "transcription_audio": result.get("transcription_audio"),
    }
    write_transcript_receipt(
        root,
        "ready",
        "existing_ready_transcript_retained",
        {**result, "failure_detail": receipt_detail},
        started_at=started_at,
    )
    return result


def _restore_transcript_from_whisper_cpp_cache(
    root: Path,
    config: dict[str, Any],
    *,
    source_track: str,
    started_at: str,
    reason: str,
) -> dict[str, Any] | None:
    raw_json = root / WHISPER_CPP_CACHE_RELATIVE_PATH
    if not raw_json.exists():
        return None
    try:
        raw_payload = json.loads(raw_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw_payload.get("transcription"), list) or not raw_payload.get("transcription"):
        return None

    language = config.get("transcribe_language")
    model = str(config.get("transcribe_model") or DEFAULT_TRANSCRIBE_MODEL)
    cached_audio = root / TRANSCRIPTION_AUDIO_CACHE_RELATIVE_PATH
    transcription_audio = cached_audio if cached_audio.exists() else root / source_track
    audio_preprocess = {
        "status": "ready" if cached_audio.exists() else "unavailable",
        "reason": "cached_transcription_audio_reused" if cached_audio.exists() else "source_audio_missing_but_provider_cache_available",
        "input": source_track,
        "output": relative(root, cached_audio) if cached_audio.exists() else None,
        "recovered_from": WHISPER_CPP_CACHE_RELATIVE_PATH,
    }
    binary = find_whisper_cpp_binary(config) or Path("cached-whisper-cpp-output")
    model_path = (
        find_whisper_cpp_model(config, model, language)
        or default_whisper_cpp_model_path(model, _whisper_cpp_setup_language(language))
    )
    normalized = _normalise_whisper_cpp_payload(
        root,
        raw_payload,
        model=model,
        language=language,
        source_track=source_track,
        audio_preprocess=audio_preprocess,
        transcription_audio=transcription_audio,
        binary=binary,
        model_path=model_path,
    )
    if not normalized.get("segment_count") and not normalized.get("word_count"):
        return None
    normalized["restored_from"] = WHISPER_CPP_CACHE_RELATIVE_PATH
    normalized["restore_reason"] = reason
    transcript_dir = root / "transcript"
    write_json(transcript_dir / "transcript.json", normalized)
    cached_srt = root / WHISPER_CPP_SRT_CACHE_RELATIVE_PATH
    if cached_srt.exists():
        shutil.copyfile(cached_srt, transcript_dir / "transcript.srt")
    else:
        _write_srt_from_segments(transcript_dir / "transcript.srt", normalized["segments"])
    result = {
        "status": "ready",
        "provider": "whisper_cpp",
        "reason": "whisper_cpp_cache_reused",
        "source_track": source_track,
        "transcription_audio": relative(root, transcription_audio),
        "restored_from": WHISPER_CPP_CACHE_RELATIVE_PATH,
        "segment_count": normalized.get("segment_count"),
        "word_count": normalized.get("word_count"),
    }
    write_transcript_receipt(root, "ready", "whisper_cpp_cache_reused", result, started_at=started_at)
    return result


def write_transcript_unavailable(root: Path, reason: str, *, preserve_ready: bool = True) -> bool:
    if preserve_ready and _read_ready_transcript(root):
        return False
    transcript_dir = root / "transcript"
    write_json(
        transcript_dir / "transcript.json",
        {
            "schema": "demo_take_transcript_v0",
            "status": "unavailable",
            "reason": reason,
            "created_at": now_iso(),
            "segments": [],
            "words": [],
        },
    )
    (transcript_dir / "transcript.srt").write_text(
        f"Transcript unavailable: {reason}\n",
        encoding="utf-8",
    )
    return True


def write_transcript_receipt(
    root: Path,
    status: str,
    reason: str | None = None,
    detail: dict[str, Any] | None = None,
    *,
    started_at: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema": "demo_take_transcript_receipt_v0",
        "status": status,
        "created_at": now_iso(),
    }
    if started_at:
        payload["started_at"] = started_at
    if reason:
        payload["reason"] = reason
    if detail:
        payload["detail"] = detail
    write_json(root / "transcript" / "transcript_receipt.json", payload)


def _transcribe_provider_label(provider: Any) -> str:
    value = str(provider or "").strip().lower().replace("-", "_")
    if value == "whisperkit":
        return "WhisperKit"
    if value == "whisper_cpp":
        return "whisper.cpp"
    return str(provider or "transcription provider")


def _whisper_cpp_setup_language(language: str | None) -> str | None:
    # The app's normal capture path leaves language unset; prefer the smaller
    # English ggml model for that local fallback instead of the multilingual one.
    return language or "en"


def _transcribe_attempt_failure_summary(attempt: Mapping[str, Any]) -> str:
    provider = _transcribe_provider_label(attempt.get("provider"))
    reason = str(attempt.get("reason") or attempt.get("status") or "unavailable")
    if reason == "timeout":
        timeout = attempt.get("timeout_seconds")
        return f"{provider} timed out" + (f" after {timeout}s" if timeout else "")
    if reason == "binary_missing":
        return f"{provider} binary missing"
    if reason == "model_missing":
        expected = attempt.get("default_model_path")
        return f"{provider} model file missing" + (f" (expected {expected})" if expected else "")
    if reason == "model_setup_failed":
        setup = attempt.get("setup") if isinstance(attempt.get("setup"), Mapping) else {}
        actions = setup.get("actions") if isinstance(setup, Mapping) else []
        failed_action = next((action for action in actions if isinstance(action, Mapping) and action.get("status") == "fail"), None) if isinstance(actions, list) else None
        if isinstance(failed_action, Mapping) and failed_action.get("error"):
            return f"{provider} model setup failed: {failed_action.get('error')}"
        return f"{provider} model setup failed"
    if reason == "nonzero_exit":
        return f"{provider} exited with code {attempt.get('exit_code')}"
    if reason == "json_missing_after_run":
        return f"{provider} did not write transcript JSON"
    if reason.startswith("json_decode_failed"):
        return f"{provider} wrote invalid transcript JSON"
    if reason == "provider_unknown":
        return f"{provider} is not a supported transcript provider"
    return f"{provider} {reason.replace('_', ' ')}"


def _has_explicit_config_value(config: Mapping[str, Any], key: str) -> bool:
    value = config.get(key)
    return value is not None and str(value).strip() != ""


def _declared_ffprobe_available(config: Mapping[str, Any]) -> bool:
    override = os.environ.get("FFPROBE_PATH")
    if override:
        path = Path(override)
        return path.exists() and os.access(str(path), os.X_OK)
    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg:
        return False
    sibling = Path(str(ffmpeg)).with_name("ffprobe")
    return sibling.exists() and os.access(str(sibling), os.X_OK)


def _scaled_media_timeout_seconds(
    config: dict[str, Any],
    key: str,
    default: int,
    media_path: Path,
    *,
    duration_multiplier: float,
    overhead_seconds: int,
    maximum: int,
) -> int:
    configured = _config_int(config, key, default, minimum=30, maximum=maximum)
    if _has_explicit_config_value(config, key) or not _declared_ffprobe_available(config):
        return configured
    duration = probe_media_duration_seconds(config, media_path)
    if duration is None:
        return configured
    scaled = int((duration * duration_multiplier) + overhead_seconds + 0.999)
    return max(configured, min(maximum, scaled))


def _auto_transcribe_providers(config: dict[str, Any], model: str, language: str | None) -> list[str]:
    if find_whisper_cpp_binary(config) and find_whisper_cpp_model(config, model, language):
        return ["whisper_cpp", "whisperkit"]
    return ["whisperkit", "whisper_cpp"]


def transcribe_track(
    root: Path,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str],
) -> dict[str, Any]:
    started_at = now_iso()
    transcript_dir = root / "transcript"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_json = transcript_dir / "transcript.json"
    transcript_srt = transcript_dir / "transcript.srt"

    if _is_fake_capture(config) and transcript_json.exists():
        try:
            existing = json.loads(transcript_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("status") == "ready":
            _clear_resolved_transcript_failures(failures)
            result = {
                "status": "ready",
                "provider": "fake",
                "reason": "existing_fake_transcript_reused",
                "source_track": existing.get("source_track"),
            }
            write_transcript_receipt(root, "ready", "existing_fake_transcript_reused", result, started_at=started_at)
            return result

    mic_track = next((track for track in tracks if track["role"] == "microphone"), None)
    if not mic_track:
        result = {"status": "skipped", "reason": "no_microphone_track"}
        retained = _retain_ready_transcript_result(
            root,
            started_at=started_at,
            failure_reason="no_microphone_track",
            detail=result,
        )
        if retained:
            _clear_resolved_transcript_failures(failures)
            return retained
        write_transcript_unavailable(root, "No microphone track was recorded.")
        write_transcript_receipt(root, "skipped", "no_microphone_track", result, started_at=started_at)
        return result

    source_track = str(mic_track["relative_path"])
    audio_path = root / source_track
    if not audio_path.exists():
        restored = _restore_transcript_from_whisper_cpp_cache(
            root,
            config,
            source_track=source_track,
            started_at=started_at,
            reason="source_audio_missing",
        )
        if restored:
            _clear_resolved_transcript_failures(failures)
            return restored
        cached_audio = root / TRANSCRIPTION_AUDIO_CACHE_RELATIVE_PATH
        if cached_audio.exists() and cached_audio.is_file():
            audio_path = cached_audio
        else:
            result = {"status": "skipped", "reason": "audio_missing", "source_track": source_track}
            retained = _retain_ready_transcript_result(
                root,
                started_at=started_at,
                failure_reason="audio_missing",
                detail=result,
            )
            if retained:
                _clear_resolved_transcript_failures(failures)
                return retained
            write_transcript_unavailable(root, f"Microphone track missing on disk: {source_track}.")
            failures.append(MICROPHONE_TRACK_MISSING_TRANSCRIBE_FAILURE)
            write_transcript_receipt(root, "skipped", "audio_missing", result, started_at=started_at)
            return result

    missing_source_recovered_from = None
    if relative(root, audio_path) != source_track:
        missing_source_recovered_from = relative(root, audio_path)

    model = config.get("transcribe_model", DEFAULT_TRANSCRIBE_MODEL)
    language = config.get("transcribe_language")
    audio_probe = probe_audio_signal(root, config, audio_path)
    if audio_probe.get("status") in {"failed", "silent"}:
        reason = f"Microphone track failed transcription input probe: {audio_probe.get('reason')}."
        terminal_reason = "silent_audio" if audio_probe.get("status") == "silent" else "audio_probe_failed"
        result = {"status": "skipped", "reason": terminal_reason, "audio_probe": audio_probe}
        retained = _retain_ready_transcript_result(
            root,
            started_at=started_at,
            failure_reason=terminal_reason,
            detail=result,
        )
        if retained:
            _clear_resolved_transcript_failures(failures)
            return retained
        write_transcript_unavailable(root, reason)
        failures.append(reason)
        write_transcript_receipt(root, "skipped", terminal_reason, result, started_at=started_at)
        return result
    transcription_audio, audio_preprocess = prepare_transcription_audio(root, config, audio_path)
    audio_preprocess["input_probe"] = audio_probe
    if missing_source_recovered_from:
        audio_preprocess["recovered_missing_source_track"] = source_track
        audio_preprocess["recovered_from"] = missing_source_recovered_from

    provider = str(config.get("transcribe_provider", DEFAULT_TRANSCRIBE_PROVIDER)).strip().lower().replace("-", "_")
    if provider not in TRANSCRIBE_PROVIDERS:
        provider = DEFAULT_TRANSCRIBE_PROVIDER
    providers = _auto_transcribe_providers(config, model, language) if provider == "auto" else [provider]
    attempts: list[dict[str, Any]] = []
    for candidate in providers:
        if candidate == "whisperkit":
            result = _transcribe_with_whisperkit(
                root,
                config,
                transcription_audio,
                transcript_json,
                transcript_srt,
                model=model,
                language=language,
                source_track=source_track,
                audio_preprocess=audio_preprocess,
            )
        elif candidate == "whisper_cpp":
            result = _transcribe_with_whisper_cpp(
                root,
                config,
                transcription_audio,
                transcript_json,
                transcript_srt,
                model=model,
                language=language,
                source_track=source_track,
                audio_preprocess=audio_preprocess,
                allow_model_download=_config_bool(
                    config,
                    "transcribe_auto_download_model",
                    DEFAULT_TRANSCRIBE_AUTO_DOWNLOAD_MODEL if provider == "auto" else False,
                ),
            )
        else:
            result = {"status": "skipped", "reason": "provider_unknown", "provider": candidate}
        attempts.append(dict(result))
        if result.get("status") == "ready":
            _clear_resolved_transcript_failures(failures)
            result["attempts"] = attempts
            result["audio_preprocess"] = audio_preprocess
            write_transcript_receipt(root, "ready", None, result, started_at=started_at)
            return result

    failure_reasons = "; ".join(_transcribe_attempt_failure_summary(attempt) for attempt in attempts)
    failed = next((attempt for attempt in attempts if attempt.get("status") == "failed"), None)
    if failed:
        result = {"status": "failed", "attempts": attempts, "audio_preprocess": audio_preprocess}
        retained = _retain_ready_transcript_result(
            root,
            started_at=started_at,
            failure_reason=str(failed.get("reason") or failed.get("exit_code") or "provider_failed"),
            detail=result,
        )
        if retained:
            _clear_resolved_transcript_failures(failures)
            return retained
        write_transcript_unavailable(root, f"Transcript provider unavailable: {failure_reasons}.")
        failures.append(f"Transcription failed via {failed.get('provider')} ({failed.get('reason') or failed.get('exit_code')}).")
        write_transcript_receipt(root, "failed", str(failed.get("reason") or failed.get("exit_code") or "provider_failed"), result, started_at=started_at)
        return result
    result = {"status": "skipped", "reason": "provider_unavailable", "attempts": attempts, "audio_preprocess": audio_preprocess}
    retained = _retain_ready_transcript_result(
        root,
        started_at=started_at,
        failure_reason="provider_unavailable",
        detail=result,
    )
    if retained:
        _clear_resolved_transcript_failures(failures)
        return retained
    write_transcript_unavailable(root, f"Transcript provider unavailable: {failure_reasons}.")
    write_transcript_receipt(root, "skipped", "provider_unavailable", result, started_at=started_at)
    return result


def _transcribe_with_whisperkit(
    root: Path,
    config: dict[str, Any],
    audio_path: Path,
    transcript_json: Path,
    transcript_srt: Path,
    *,
    model: str,
    language: str | None,
    source_track: str,
    audio_preprocess: dict[str, Any],
) -> dict[str, Any]:
    binary = config.get("transcribe_binary")
    if not binary:
        located = find_transcribe_binary()
        binary = str(located) if located else None
    if not binary or not Path(binary).is_file() or not os.access(str(binary), os.X_OK):
        return {"status": "skipped", "provider": "whisperkit", "reason": "binary_missing"}

    log_path = root / "logs" / "transcribe.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary,
        "--audio",
        str(audio_path),
        "--output-json",
        str(transcript_json),
        "--output-srt",
        str(transcript_srt),
        "--model",
        model,
        "--source-track",
        source_track,
    ]
    if language:
        cmd += ["--language", language]

    timeout = _scaled_media_timeout_seconds(
        config,
        "transcribe_timeout_seconds",
        DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS,
        audio_path,
        duration_multiplier=1.5,
        overhead_seconds=120,
        maximum=21600,
    )
    with log_path.open("ab") as log:
        try:
            proc = subprocess.run(cmd, stdout=log, stderr=log, check=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            log.write(f"whisperkit transcription timed out after {timeout}s\n".encode("utf-8"))
            return {"status": "failed", "provider": "whisperkit", "reason": "timeout", "timeout_seconds": timeout}
    if proc.returncode != 0:
        return {"status": "failed", "provider": "whisperkit", "reason": "nonzero_exit", "exit_code": proc.returncode}

    _annotate_transcript_metadata(
        root,
        transcript_json,
        provider="whisperkit",
        provider_detail={"binary": str(binary)},
        audio_preprocess=audio_preprocess,
        transcription_audio=audio_path,
    )
    return {"status": "ready", "provider": "whisperkit", "model": model}


def _transcribe_with_whisper_cpp(
    root: Path,
    config: dict[str, Any],
    audio_path: Path,
    transcript_json: Path,
    transcript_srt: Path,
    *,
    model: str,
    language: str | None,
    source_track: str,
    audio_preprocess: dict[str, Any],
    allow_model_download: bool = False,
) -> dict[str, Any]:
    binary = find_whisper_cpp_binary(config)
    if not binary:
        return {"status": "skipped", "provider": "whisper_cpp", "reason": "binary_missing"}
    model_path = find_whisper_cpp_model(config, model, language)
    if not model_path:
        default_model = default_whisper_cpp_model_path(model, _whisper_cpp_setup_language(language))
        if allow_model_download:
            append_postprocess_progress(
                root,
                "transcribe_setup",
                "running",
                "Downloading local whisper.cpp transcription model",
                {
                    "provider": "whisper_cpp",
                    "model": model,
                    "language": _whisper_cpp_setup_language(language),
                    "target": str(default_model),
                },
            )
            setup = setup_whisper_cpp(
                install_brew=False,
                download_model=True,
                model=model,
                language=_whisper_cpp_setup_language(language),
            )
            setup_status = "pass" if setup.get("status") == "ready" else "fail"
            append_postprocess_progress(
                root,
                "transcribe_setup",
                setup_status,
                "Local whisper.cpp transcription model ready" if setup_status == "pass" else "Local whisper.cpp transcription model setup failed",
                setup,
            )
            setup_model = setup.get("model_path")
            if setup.get("status") == "ready" and setup_model and Path(str(setup_model)).is_file():
                model_path = Path(str(setup_model))
            else:
                return {
                    "status": "skipped",
                    "provider": "whisper_cpp",
                    "reason": "model_setup_failed",
                    "default_model_path": str(default_model),
                    "setup": setup,
                }
        else:
            return {
                "status": "skipped",
                "provider": "whisper_cpp",
                "reason": "model_missing",
                "default_model_path": str(default_model),
            }
    effective_language = language or ("en" if model_path.name.endswith(".en.bin") else None)

    output_base = root / "transcript" / "whisper_cpp"
    raw_json = output_base.with_suffix(".json")
    raw_srt = output_base.with_suffix(".srt")
    log_path = root / "logs" / "transcribe_whisper_cpp.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(binary),
        "-m",
        str(model_path),
        "-f",
        str(audio_path),
        "-of",
        str(output_base),
        "-oj",
        "-ojf",
        "-osrt",
        "-ml",
        "1",
        "-sow",
        "-np",
    ]
    if effective_language:
        cmd += ["-l", effective_language]
    vad_model = config.get("whisper_cpp_vad_model")
    if vad_model and Path(str(vad_model)).expanduser().is_file():
        cmd += ["--vad", "--vad-model", str(Path(str(vad_model)).expanduser())]
    timeout = _scaled_media_timeout_seconds(
        config,
        "transcribe_timeout_seconds",
        DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS,
        audio_path,
        duration_multiplier=1.5,
        overhead_seconds=120,
        maximum=21600,
    )
    with log_path.open("ab") as log:
        try:
            proc = subprocess.run(cmd, stdout=log, stderr=log, check=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            log.write(f"whisper.cpp transcription timed out after {timeout}s\n".encode("utf-8"))
            return {"status": "failed", "provider": "whisper_cpp", "reason": "timeout", "timeout_seconds": timeout}
    if proc.returncode != 0:
        return {"status": "failed", "provider": "whisper_cpp", "reason": "nonzero_exit", "exit_code": proc.returncode}
    if not raw_json.exists():
        return {"status": "failed", "provider": "whisper_cpp", "reason": "json_missing_after_run"}

    try:
        raw_payload = json.loads(raw_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "failed", "provider": "whisper_cpp", "reason": f"json_decode_failed:{exc}"}

    normalized = _normalise_whisper_cpp_payload(
        root,
        raw_payload,
        model=model,
        language=effective_language,
        source_track=source_track,
        audio_preprocess=audio_preprocess,
        transcription_audio=audio_path,
        binary=binary,
        model_path=model_path,
    )
    write_json(transcript_json, normalized)
    if raw_srt.exists():
        shutil.copyfile(raw_srt, transcript_srt)
    else:
        _write_srt_from_segments(transcript_srt, normalized["segments"])
    return {
        "status": "ready",
        "provider": "whisper_cpp",
        "model": model,
        "model_path": str(model_path),
        "language": effective_language,
        "word_count": normalized["word_count"],
    }


def transcribe_smoke(
    *,
    provider: str = "whisper_cpp",
    model: str = DEFAULT_TRANSCRIBE_MODEL,
    language: str | None = "en",
    ffmpeg_path: str | None = None,
    text: str | None = None,
    whisper_cpp_binary: str | None = None,
    whisper_cpp_model: str | None = None,
    audio_format: str = "mp3",
) -> dict[str, Any]:
    script = text or (
        "This is a local transcription smoke test. "
        "These words should become timestamped speech blocks for editing."
    )
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_id = f"take_transcribe_smoke_{stamp}"
    takes_root = REPO_ROOT / "state" / "dissemination" / "demo_takes"
    for index in range(100):
        take_id = base_id if index == 0 else f"{base_id}_{index:02d}"
        root = takes_root / take_id
        if not root.exists():
            break
    else:
        raise RuntimeError(f"could not allocate unique smoke take id for {base_id}")
    for name in ["tracks", "transcript", "render", "review", "logs", "frames"]:
        (root / name).mkdir(parents=True, exist_ok=True)

    ffmpeg = ffmpeg_path or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    say = shutil.which("say") or "/usr/bin/say"
    audio_format = audio_format.lower()
    if audio_format not in {"mp3", "m4a", "wav"}:
        raise ValueError("audio_format must be mp3, m4a, or wav")
    source_audio = root / "tracks" / "smoke_source.aiff"
    mic_audio = root / "tracks" / f"microphone.{audio_format}"
    say_log = root / "logs" / "say_transcribe_smoke.log"
    ffmpeg_log = root / "logs" / "ffmpeg_transcribe_smoke.log"

    failures: list[str] = []
    if not Path(say).exists():
        failures.append("macOS say command missing; cannot generate spoken smoke audio.")
    else:
        try:
            say_proc = _run_logged([say, "-o", str(source_audio), script], say_log, timeout=45)
        except Exception as exc:
            say_proc = None
            failures.append(f"say_failed:{exc}")
        if say_proc is not None and say_proc.returncode != 0:
            failures.append(f"say_exit_{say_proc.returncode}")

    if not failures:
        codec_args = {
            "mp3": ["-c:a", "libmp3lame", "-b:a", "128k"],
            "m4a": ["-c:a", "aac", "-b:a", "128k"],
            "wav": ["-c:a", "pcm_s16le"],
        }[audio_format]
        try:
            ffmpeg_proc = _run_logged(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-y",
                    "-i",
                    str(source_audio),
                    "-vn",
                    *codec_args,
                    str(mic_audio),
                ],
                ffmpeg_log,
                timeout=45,
            )
        except Exception as exc:
            ffmpeg_proc = None
            failures.append(f"ffmpeg_failed:{exc}")
        if ffmpeg_proc is not None and ffmpeg_proc.returncode != 0:
            failures.append(f"ffmpeg_exit_{ffmpeg_proc.returncode}")

    tracks = [
        {
            "id": "microphone_smoke",
            "role": "microphone",
            "device_name": "synthetic_say",
            "device_index": None,
            "relative_path": relative(root, mic_audio),
        }
    ]
    config: dict[str, Any] = {
        "repo_root": str(REPO_ROOT),
        "ffmpeg_path": ffmpeg,
        "capture_backend": "synthetic_transcribe_smoke",
        "screenshot_interval_seconds": 1,
        "screens": [],
        "microphone": {"index": None, "name": "synthetic_say"},
        "webcam": None,
        "transcribe_provider": provider,
        "transcribe_model": model,
        "transcribe_language": language,
        "transcribe_preprocess_audio": True,
        "transcribe_smoke_audio_format": audio_format,
        "take_title": "Transcription Smoke",
    }
    if whisper_cpp_binary:
        config["whisper_cpp_binary"] = whisper_cpp_binary
    if whisper_cpp_model:
        config["whisper_cpp_model"] = whisper_cpp_model

    session = {
        "schema": "demo_take_session_v0",
        "take_id": take_id,
        "created_at": now_iso(),
        "config": config,
        "tracks": tracks,
        "processes": [],
        "markers": [],
        "pause_events": [],
        "known_failures": failures,
    }
    write_json(root / "session.json", session)
    write_json(root / "manifest.json", manifest(take_id, root, "package_ready", config, tracks, failures))

    transcribe_result: dict[str, Any] = {"status": "skipped", "reason": "audio_generation_failed"}
    intent_result: dict[str, Any] = {}
    speech_result: dict[str, Any] = {}
    if not failures and mic_audio.exists():
        transcribe_result = transcribe_track(root, config, tracks, failures)
        if transcribe_result.get("status") == "ready":
            intent_result = build_intent_events(root)
            speech_result = build_speech_blocks(root)

    transcript_path = root / "transcript" / "transcript.json"
    transcript = json.loads(transcript_path.read_text(encoding="utf-8")) if transcript_path.exists() else {}
    segments = transcript.get("segments", []) if isinstance(transcript.get("segments"), list) else []
    transcript_text = " ".join(_clean_text(segment.get("text", "")) for segment in segments if isinstance(segment, dict))
    word_count = int(transcript.get("word_count") or 0)
    block_count = int(speech_result.get("block_count") or 0)
    status = "ready" if transcribe_result.get("status") == "ready" and word_count > 0 and block_count > 0 else "failed"
    if status != "ready" and not failures:
        failures.append("transcribe_smoke_did_not_produce_timestamped_speech_blocks")
    session["known_failures"] = failures
    write_json(root / "session.json", session)
    write_json(root / "manifest.json", manifest(take_id, root, "package_ready", config, tracks, failures))
    receipt = {
        "schema": "demo_take_transcribe_smoke_v0",
        "created_at": now_iso(),
        "status": status,
        "take_id": take_id,
        "rootPath": str(root),
        "provider": provider,
        "model": model,
        "language": language,
        "audio_format": audio_format,
        "source_text": script,
        "transcript_text": _clean_text(transcript_text),
        "word_count": word_count,
        "block_count": block_count,
        "transcribe_result": transcribe_result,
        "intent_result": {
            "status": intent_result.get("status"),
            "event_count": intent_result.get("event_count"),
        } if intent_result else None,
        "speech_blocks": {
            "status": speech_result.get("status"),
            "block_count": speech_result.get("block_count"),
            "word_count": speech_result.get("word_count"),
        } if speech_result else None,
        "failures": failures,
        "logs": {
            "say": relative(root, say_log),
            "ffmpeg": relative(root, ffmpeg_log),
            "transcribe": "logs/transcribe_whisper_cpp.log" if provider == "whisper_cpp" else "logs/transcribe.log",
        },
    }
    write_json(root / "transcribe_smoke_receipt.json", receipt)
    return receipt


def write_edl(root: Path, take_id: str, tracks: list[dict[str, Any]], markers: list[dict[str, Any]]) -> None:
    sorted_markers = sorted(markers, key=lambda m: m.get("video_t_seconds") or 0.0)
    segments: list[dict[str, Any]] = []
    last_end = 0.0
    for index, marker in enumerate(sorted_markers):
        end_t = marker.get("video_t_seconds")
        if end_t is None:
            continue
        segments.append(
            {
                "id": f"seg_{index:04d}",
                "start_seconds": round(last_end, 3),
                "end_seconds": round(float(end_t), 3),
                "boundary_marker_id": marker["id"],
                "boundary_source": marker.get("source"),
                "boundary_label": marker.get("label"),
                "status": "candidate",
            }
        )
        last_end = float(end_t)
    write_json(
        root / "edl.json",
        {
            "schema": "demo_take_edl_v0",
            "take_id": take_id,
            "created_at": now_iso(),
            "tracks": tracks,
            "markers": sorted_markers,
            "segments": segments,
            "notes": {
                "status": "candidate_segments_from_markers" if segments else "no_markers",
                "intent": "AI rough-cut: each marker closes the previous candidate segment.",
            },
        },
    )


def write_edl_otio(
    root: Path,
    take_id: str,
    tracks: list[dict[str, Any]],
    markers: list[dict[str, Any]],
) -> None:
    rate_hz = 1000  # millisecond resolution; values stored as integer milliseconds

    def rt(seconds: float) -> dict[str, Any]:
        return {"OTIO_SCHEMA": "RationalTime.1", "rate": rate_hz, "value": int(round(seconds * rate_hz))}

    def time_range(start: float, duration: float) -> dict[str, Any]:
        return {"OTIO_SCHEMA": "TimeRange.1", "start_time": rt(start), "duration": rt(max(0.0, duration))}

    sorted_markers = sorted(markers, key=lambda m: m.get("video_t_seconds") or 0.0)
    last_end = 0.0
    seg_records: list[dict[str, float | str]] = []
    for index, marker in enumerate(sorted_markers):
        end_t = marker.get("video_t_seconds")
        if end_t is None:
            continue
        seg_records.append(
            {"id": f"seg_{index:04d}", "start": float(last_end), "end": float(end_t)}
        )
        last_end = float(end_t)

    def media_ref_for(track: dict[str, Any]) -> dict[str, Any]:
        target = track.get("relative_path") or ""
        return {
            "OTIO_SCHEMA": "ExternalReference.1",
            "target_url": target,
            "available_range": None,
        }

    def build_track_lane(role: str, kind: str) -> dict[str, Any] | None:
        source_track = next((t for t in tracks if t.get("role") == role), None)
        if source_track is None:
            return None
        clips: list[dict[str, Any]] = []
        for seg in seg_records:
            seg_id = str(seg["id"])
            seg_start = float(seg["start"])
            seg_end = float(seg["end"])
            seg_duration = max(0.0, seg_end - seg_start)
            clips.append(
                {
                    "OTIO_SCHEMA": "Clip.1",
                    "name": seg_id,
                    "metadata": {
                        "demo_take": {
                            "segment_id": seg_id,
                            "source_role": role,
                            "source_track_id": source_track.get("id"),
                            "status": "candidate",
                        }
                    },
                    "source_range": time_range(seg_start, seg_duration),
                    "media_reference": media_ref_for(source_track),
                }
            )
        return {
            "OTIO_SCHEMA": "Track.1",
            "name": f"{role}_v0",
            "kind": kind,
            "metadata": {"demo_take": {"role": role}},
            "children": clips,
        }

    children: list[dict[str, Any]] = []
    for role, kind in (("screen", "Video"), ("webcam", "Video"), ("microphone", "Audio")):
        lane = build_track_lane(role, kind)
        if lane is not None:
            children.append(lane)

    timeline = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": take_id,
        "metadata": {
            "demo_take": {
                "schema_origin": "demo_take_edl_v0",
                "take_id": take_id,
                "created_at": now_iso(),
                "rate_hz": rate_hz,
                "segment_count": len(seg_records),
                "intent": "OTIO projection of demo_take_edl_v0 segments; round-trip via the opentimelineio annex.",
                "annex_reference": "annexes/opentimelineio/repo/",
            }
        },
        "global_start_time": None,
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": take_id,
            "children": children,
        },
    }
    (root / "edl.otio").write_text(
        json.dumps(timeline, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_autoedit_cleanup(
    root: Path,
    failures: list[str],
) -> dict[str, Any]:
    rough_cut = root / "render" / "rough_cut.mp4"
    receipt_path = root / "render" / "autoedit_receipt.json"
    output = root / "render" / "rough_cut.autoedit.mp4"
    log_path = root / "logs" / "autoedit.log"

    def write_receipt(payload: dict[str, Any]) -> dict[str, Any]:
        write_json(receipt_path, payload)
        return payload

    if not rough_cut.exists():
        return write_receipt(
            {
                "schema": "demo_take_autoedit_receipt_v0",
                "status": "skipped",
                "reason": "rough_cut_missing",
                "input": None,
                "output": None,
                "tool": "auto-editor",
                "tool_resolved": None,
                "annex_reference": "annexes/auto-editor/repo/",
            }
        )

    import shutil  # local import; stdlib

    binary = shutil.which("auto-editor")
    if binary is None:
        return write_receipt(
            {
                "schema": "demo_take_autoedit_receipt_v0",
                "status": "unavailable",
                "reason": "auto_editor_not_on_path",
                "input": relative(root, rough_cut),
                "output": None,
                "tool": "auto-editor",
                "tool_resolved": None,
                "remediation": "pip install auto-editor  # then re-run postprocess",
                "annex_reference": "annexes/auto-editor/repo/",
            }
        )

    command = [
        binary,
        str(rough_cut),
        "--silent-threshold",
        "0.04",
        "--frame-margin",
        "6",
        "--no-open",
        "-o",
        str(output),
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        log.write(f"=== {now_iso()} auto-editor command: {' '.join(command)}\n".encode("utf-8"))
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"auto-editor unavailable: {exc}\n".encode("utf-8"))
            status = 1

    if status != 0 or not output.exists():
        failures.append("auto-editor cleanup failed; see logs/autoedit.log.")
        return write_receipt(
            {
                "schema": "demo_take_autoedit_receipt_v0",
                "status": "failed",
                "reason": "nonzero_exit_or_missing_output",
                "input": relative(root, rough_cut),
                "output": None,
                "tool": "auto-editor",
                "tool_resolved": str(binary),
                "exit_status": status,
                "annex_reference": "annexes/auto-editor/repo/",
            }
        )

    return write_receipt(
        {
            "schema": "demo_take_autoedit_receipt_v0",
            "status": "ready",
            "input": relative(root, rough_cut),
            "output": relative(root, output),
            "tool": "auto-editor",
            "tool_resolved": str(binary),
            "exit_status": 0,
            "annex_reference": "annexes/auto-editor/repo/",
        }
    )


def write_render(
    root: Path,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str],
    *,
    session: Mapping[str, Any] | None = None,
) -> None:
    screen = next((track for track in tracks if track["role"] == "screen"), None)
    mic = next((track for track in tracks if track["role"] == "microphone"), None)
    session = session or _read_json_dict(root / "session.json")
    output = root / "render" / "rough_cut.mp4"
    output_tmp = output.with_name("rough_cut.tmp.mp4")
    profile = storage_profile(config)
    if _is_fake_capture(config):
        output.parent.mkdir(parents=True, exist_ok=True)
        if not output.exists():
            output.write_bytes(b"fake rough cut\n")
        write_json(
            root / "render" / "render_receipt.json",
            {
                "schema": "demo_take_render_receipt_v0",
                "status": "ready",
                "output": relative(root, output),
                "known_failures": [],
                "storage_profile": profile,
                "storage_optimization": {
                    "method": "fake_capture_fixture",
                    "rough_cut_screen_hardlinked": False,
                    "video_stream_action": "synthetic_fixture",
                    "screen_track": screen["relative_path"] if screen else None,
                },
            },
        )
        return
    ffmpeg = config["ffmpeg_path"]
    if not screen:
        write_json(
            root / "render" / "render_receipt.json",
            {
                "schema": "demo_take_render_receipt_v0",
                "status": "unavailable",
                "output": None,
                "known_failures": ["No screen track was available for rough render."],
            },
        )
        return

    screen_path = root / screen["relative_path"]
    try:
        screen_bytes = screen_path.stat().st_size
    except OSError:
        screen_bytes = 0
    if screen_bytes <= 0:
        message = f"Missing screen track: {screen['relative_path']}."
        failures.append(message)
        write_json(
            root / "render" / "render_receipt.json",
            {
                "schema": "demo_take_render_receipt_v0",
                "status": "unavailable",
                "output": None,
                "known_failures": [message],
                "storage_profile": profile,
                "storage_optimization": {
                    "method": "none",
                    "rough_cut_screen_hardlinked": False,
                    "video_stream_action": "unavailable",
                    "screen_track": screen["relative_path"],
                },
            },
        )
        return

    render_warnings: list[str] = []
    if mic:
        mic_path = root / mic["relative_path"]
        try:
            mic_bytes = mic_path.stat().st_size
        except OSError:
            mic_bytes = 0
        if mic_bytes <= 0:
            render_warnings.append(
                f"Microphone track missing: {mic['relative_path']}; screen-only review video will be used."
            )
            mic = None

    screen_offset = _track_timeline_offset_seconds(screen)
    mic_offset = _track_timeline_offset_seconds(mic)

    if not mic and profile == "efficient" and screen_offset <= 0.05:
        signature = _media_build_signature(
            root,
            stage="rough_render",
            output=output,
            inputs=[screen_path],
            params={
                "profile": profile,
                "video_stream_action": "no_reencode",
                "audio_stream_action": "none",
                "screen_track": screen["relative_path"],
                "screen_timeline_offset_seconds": round(screen_offset, 6),
                "microphone_timeline_offset_seconds": None,
            },
        )
        cached = _read_matching_generated_media_receipt(root, output, signature)
        if cached:
            write_json(
                root / "render" / "render_receipt.json",
                {
                    "schema": "demo_take_render_receipt_v0",
                    "status": "ready",
                    "output": relative(root, output),
                    "known_failures": render_warnings,
                    "storage_profile": profile,
                    "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
                    "skipped": True,
                    "storage_optimization": {
                        "method": "hardlink_lossless_dedupe",
                        "rough_cut_screen_hardlinked": True,
                        "video_stream_action": "no_reencode",
                        "screen_track": screen["relative_path"],
                        "screen_timeline_offset_seconds": round(screen_offset, 6),
                    },
                },
            )
            return
        hardlinked = replace_with_hardlink(output, screen_path)
        if hardlinked:
            envelope = _generated_media_envelope(
                root,
                config,
                output,
                role="screen",
                expected_duration=None,
                video_bitrate=EFFICIENT_SCREEN_BITRATE,
                probe_container=False,
            )
            _write_generated_media_receipt(
                root,
                output,
                stage="rough_render",
                signature=signature,
                envelope=envelope,
                extra={
                    "duration_seconds": None,
                    "extra": {
                        "method": "hardlink_lossless_dedupe",
                        "screen_track": screen["relative_path"],
                    },
                },
            )
            write_json(
                root / "render" / "render_receipt.json",
                {
                    "schema": "demo_take_render_receipt_v0",
                    "status": "ready",
                    "output": relative(root, output),
                    "known_failures": render_warnings,
                    "storage_profile": profile,
                    "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
                    "skipped": False,
                    "storage_optimization": {
                        "method": "hardlink_lossless_dedupe",
                        "rough_cut_screen_hardlinked": True,
                        "video_stream_action": "no_reencode",
                        "screen_track": screen["relative_path"],
                        "screen_timeline_offset_seconds": round(screen_offset, 6),
                    },
                },
            )
            return

    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass

    video_filter = (
        f"[0:v:0]trim=start={screen_offset:.6f},setpts=PTS-STARTPTS,"
        f"{efficient_video_filter({'recording_quality': 'efficient'})},"
        "fps=30,format=yuv420p[v]"
    )
    if mic:
        audio_filter = (
            f"[1:a:0]atrim=start={mic_offset:.6f},asetpts=PTS-STARTPTS,"
            "aresample=48000[a]"
        )
        signature = _media_build_signature(
            root,
            stage="rough_render",
            output=output,
            inputs=[screen_path, root / mic["relative_path"]],
            params={
                "profile": profile,
                "video_filter": video_filter,
                "audio_filter": audio_filter,
                "video_bitrate": EFFICIENT_SCREEN_BITRATE,
                "audio_bitrate": EFFICIENT_AUDIO_BITRATE,
                "encoder": "h264_videotoolbox",
                "screen_track": screen["relative_path"],
                "microphone_track": mic["relative_path"],
                "screen_timeline_offset_seconds": round(screen_offset, 6),
                "microphone_timeline_offset_seconds": round(mic_offset, 6),
            },
        )
        cached = _read_matching_generated_media_receipt(root, output, signature)
        if cached:
            write_json(
                root / "render" / "render_receipt.json",
                {
                    "schema": "demo_take_render_receipt_v0",
                    "status": "ready",
                    "output": relative(root, output),
                    "known_failures": render_warnings,
                    "storage_profile": profile,
                    "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
                    "skipped": True,
                    "storage_optimization": {
                        "method": str(cached.get("extra", {}).get("method") or "none")
                        if isinstance(cached.get("extra"), Mapping)
                        else "none",
                        "rough_cut_screen_hardlinked": bool(
                            cached.get("extra", {}).get("rough_cut_screen_hardlinked")
                        )
                        if isinstance(cached.get("extra"), Mapping)
                        else False,
                        "video_stream_action": "trim_setpts_720p30_reencode",
                        "audio_stream_action": "trim_asetpts_aac",
                        "screen_track": screen["relative_path"],
                        "screen_timeline_offset_seconds": round(screen_offset, 6),
                        "microphone_timeline_offset_seconds": round(mic_offset, 6),
                    },
                },
            )
            return
        command = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-i",
            str(screen_path),
            "-i",
            str(root / mic["relative_path"]),
            "-filter_complex",
            f"{video_filter};{audio_filter}",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            EFFICIENT_SCREEN_BITRATE,
            "-c:a",
            "aac",
            "-b:a",
            EFFICIENT_AUDIO_BITRATE,
            "-ar",
            "48000",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_tmp),
        ]
    else:
        signature = _media_build_signature(
            root,
            stage="rough_render",
            output=output,
            inputs=[screen_path],
            params={
                "profile": profile,
                "video_filter": video_filter,
                "video_bitrate": EFFICIENT_SCREEN_BITRATE,
                "audio_bitrate": None,
                "encoder": "h264_videotoolbox",
                "screen_track": screen["relative_path"],
                "screen_timeline_offset_seconds": round(screen_offset, 6),
                "microphone_timeline_offset_seconds": None,
            },
        )
        cached = _read_matching_generated_media_receipt(root, output, signature)
        if cached:
            write_json(
                root / "render" / "render_receipt.json",
                {
                    "schema": "demo_take_render_receipt_v0",
                    "status": "ready",
                    "output": relative(root, output),
                    "known_failures": render_warnings,
                    "storage_profile": profile,
                    "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
                    "skipped": True,
                    "storage_optimization": {
                        "method": str(cached.get("extra", {}).get("method") or "none")
                        if isinstance(cached.get("extra"), Mapping)
                        else "none",
                        "rough_cut_screen_hardlinked": bool(
                            cached.get("extra", {}).get("rough_cut_screen_hardlinked")
                        )
                        if isinstance(cached.get("extra"), Mapping)
                        else False,
                        "video_stream_action": "trim_setpts_720p30_reencode",
                        "audio_stream_action": "none",
                        "screen_track": screen["relative_path"],
                        "screen_timeline_offset_seconds": round(screen_offset, 6),
                        "microphone_timeline_offset_seconds": None,
                    },
                },
            )
            return
        command = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-i",
            str(screen_path),
            "-filter_complex",
            video_filter,
            "-map",
            "[v]",
            "-an",
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            EFFICIENT_SCREEN_BITRATE,
            "-movflags",
            "+faststart",
            str(output_tmp),
        ]

    log_path = root / "logs" / "rough_render.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"rough render unavailable: {exc}\n".encode("utf-8"))
            status = 1
    envelope: dict[str, Any] | None = None
    if status == 0 and output_tmp.exists():
        expected_duration = probe_media_duration_seconds(config, screen_path)
        envelope = _generated_media_envelope(
            root,
            config,
            output_tmp,
            role="screen",
            expected_duration=expected_duration,
            video_bitrate=EFFICIENT_SCREEN_BITRATE,
            audio_bitrate=EFFICIENT_AUDIO_BITRATE if mic else None,
        )
        if envelope.get("status") == "fail":
            try:
                output_tmp.unlink()
            except OSError:
                pass
            status = 1
            failures.append(
                f"Generated media envelope failed for rough_cut.mp4: "
                f"{', '.join(str(item) for item in envelope.get('failures') or [])}."
            )
        else:
            os.replace(output_tmp, output)
    else:
        try:
            if output_tmp.exists():
                output_tmp.unlink()
        except OSError:
            pass
        if status == 0:
            status = 1

    hardlinked = False
    optimization_method = "none"
    if status == 0 and profile == "efficient":
        hardlinked = replace_with_hardlink(screen_path, output)
        if hardlinked:
            optimization_method = "hardlink_lossless_dedupe"
    if status == 0 and output.exists():
        final_signature = _media_build_signature(
            root,
            stage="rough_render",
            output=output,
            inputs=[screen_path] + ([root / mic["relative_path"]] if mic else []),
            params=dict(signature.get("params") if isinstance(signature.get("params"), Mapping) else {}),
        )
        output_duration = probe_media_duration_seconds(config, output)
        _write_generated_media_receipt(
            root,
            output,
            stage="rough_render",
            signature=final_signature,
            envelope={
                **dict(envelope or {}),
                "relative_path": relative(root, output),
                "bytes": output.stat().st_size if output.exists() else None,
            },
            extra={
                "duration_seconds": output_duration,
                "extra": {
                    "method": optimization_method,
                    "rough_cut_screen_hardlinked": hardlinked,
                },
            },
        )
    elif envelope is not None:
        _write_generated_media_receipt(
            root,
            output,
            stage="rough_render",
            signature=signature,
            envelope=envelope,
            extra={"extra": {"method": optimization_method, "rough_cut_screen_hardlinked": hardlinked}},
        )

    render_failures = render_warnings if status == 0 else [*render_warnings, "Rough render failed; see logs/rough_render.log."]
    failures.extend(render_failures)
    write_json(
        root / "render" / "render_receipt.json",
        {
            "schema": "demo_take_render_receipt_v0",
            "status": "ready" if status == 0 else "failed",
            "output": relative(root, output) if status == 0 else None,
            "known_failures": render_failures,
            "storage_profile": profile,
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)) if status == 0 else None,
            "skipped": False,
            "storage_optimization": {
                "method": optimization_method,
                "rough_cut_screen_hardlinked": hardlinked,
                "video_stream_action": "trim_setpts_720p30_reencode",
                "audio_stream_action": "trim_asetpts_aac" if mic else "none",
                "screen_track": screen["relative_path"],
                "screen_timeline_offset_seconds": round(screen_offset, 6),
                "microphone_timeline_offset_seconds": round(mic_offset, 6) if mic else None,
            },
        },
    )


def write_review_audio_mp3(
    root: Path,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str],
) -> dict[str, Any]:
    mic_candidates = [track for track in tracks if track.get("role") == "microphone" and track.get("relative_path")]
    mic = None
    source = None
    source_bytes = 0
    for candidate in mic_candidates:
        candidate_source = root / str(candidate["relative_path"])
        try:
            candidate_bytes = candidate_source.stat().st_size
        except OSError:
            candidate_bytes = 0
        if candidate_bytes > 0:
            mic = candidate
            source = candidate_source
            source_bytes = candidate_bytes
            break

    if mic is None or source is None or source_bytes <= 0:
        existing_review_audio = root / "render" / "review_audio.mp3"
        existing_stat = _safe_stat(existing_review_audio)
        if existing_stat is not None and existing_stat.st_size > 0:
            mic = {"role": "review_audio", "relative_path": "render/review_audio.mp3"}
            source = existing_review_audio
            source_bytes = existing_stat.st_size
        elif not mic_candidates:
            return {"schema": "demo_take_review_audio_v0", "status": "skipped", "reason": "no_microphone_track", "output": None}

    if mic is None or source is None or source_bytes <= 0:
        declared = ", ".join(str(track.get("relative_path")) for track in mic_candidates)
        failures.append(f"Cannot build MP3 review audio because no declared microphone track is readable: {declared}.")
        return {
            "schema": "demo_take_review_audio_v0",
            "status": "unavailable",
            "reason": "microphone_track_missing",
            "source": mic_candidates[0].get("relative_path"),
            "output": None,
        }

    ffmpeg = config.get("ffmpeg_path")
    if not ffmpeg or _is_fake_capture(config):
        return {
            "schema": "demo_take_review_audio_v0",
            "status": "skipped",
            "reason": "ffmpeg_unavailable_or_fake_capture",
            "source": mic.get("relative_path"),
            "output": None,
        }

    output = root / "render" / "review_audio.mp3"
    output_tmp = output.with_suffix(".tmp.mp3")
    log_path = root / "logs" / "review_audio.log"
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    bitrate = str(config.get("review_audio_bitrate") or DEFAULT_REVIEW_AUDIO_BITRATE).strip() or DEFAULT_REVIEW_AUDIO_BITRATE
    sample_rate = str(config.get("review_audio_sample_rate") or DEFAULT_REVIEW_AUDIO_SAMPLE_RATE).strip() or DEFAULT_REVIEW_AUDIO_SAMPLE_RATE
    signature = _media_build_signature(
        root,
        stage="review_audio_mp3",
        output=output,
        inputs=[source],
        params={
            "audio_bitrate": bitrate,
            "audio_codec": "libmp3lame",
            "audio_channels": 1,
            "audio_sample_rate": sample_rate,
            "source": mic.get("relative_path"),
        },
    )
    cached = _read_matching_generated_media_receipt(root, output, signature)
    if cached:
        return {
            "schema": "demo_take_review_audio_v0",
            "status": "ready",
            "source": mic.get("relative_path"),
            "output": relative(root, output),
            "codec": "mp3",
            "bitrate": bitrate,
            "sample_rate": sample_rate,
            "channels": 1,
            "bytes": output.stat().st_size if output.exists() else None,
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "skipped": True,
        }
    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass

    command = [
        str(ffmpeg),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-ac",
        "1",
        "-ar",
        sample_rate,
        str(output_tmp),
    ]
    timeout = _scaled_media_timeout_seconds(
        config,
        "review_audio_timeout_seconds",
        120,
        source,
        duration_multiplier=0.2,
        overhead_seconds=120,
        maximum=3600,
    )
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False, timeout=timeout).returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.write(f"review audio export failed: {exc}\n".encode("utf-8"))
            status = 124

    if status == 0 and output_tmp.exists():
        envelope = _generated_media_envelope(
            root,
            config,
            output_tmp,
            role="audio",
            expected_duration=probe_media_duration_seconds(config, source),
            video_bitrate="0",
            audio_bitrate=bitrate,
        )
        if envelope.get("status") == "fail":
            _write_generated_media_receipt(
                root,
                output,
                stage="review_audio_mp3",
                signature=signature,
                envelope=envelope,
                extra={"extra": {"source": mic.get("relative_path"), "codec": "mp3", "bitrate": bitrate, "channels": 1, "sample_rate": sample_rate}},
            )
            try:
                output_tmp.unlink()
            except OSError:
                pass
            failures.append(
                f"Generated media envelope failed for review_audio.mp3: "
                f"{', '.join(str(item) for item in envelope.get('failures') or [])}."
            )
            return {
                "schema": "demo_take_review_audio_v0",
                "status": "failed",
                "reason": "generated_media_envelope_failed",
                "source": mic.get("relative_path"),
                "output": None,
                "log": relative(root, log_path),
            }
        os.replace(output_tmp, output)
        final_signature = signature
        if source == output:
            final_signature = _media_build_signature(
                root,
                stage="review_audio_mp3",
                output=output,
                inputs=[output],
                params={
                    "audio_bitrate": bitrate,
                    "audio_codec": "libmp3lame",
                    "audio_channels": 1,
                    "audio_sample_rate": sample_rate,
                    "source": mic.get("relative_path"),
                },
            )
        _write_generated_media_receipt(
            root,
            output,
            stage="review_audio_mp3",
            signature=final_signature,
            envelope={
                **dict(envelope),
                "relative_path": relative(root, output),
                "bytes": output.stat().st_size if output.exists() else None,
            },
            extra={
                "duration_seconds": probe_media_duration_seconds(config, output),
                "extra": {"source": mic.get("relative_path"), "codec": "mp3", "bitrate": bitrate, "channels": 1, "sample_rate": sample_rate},
            },
        )
        return {
            "schema": "demo_take_review_audio_v0",
            "status": "ready",
            "source": mic.get("relative_path"),
            "output": relative(root, output),
            "codec": "mp3",
            "bitrate": bitrate,
            "sample_rate": sample_rate,
            "channels": 1,
            "bytes": output.stat().st_size if output.exists() else None,
            "generated_media_receipt": relative(root, _generated_media_receipt_path(root, output)),
            "skipped": False,
        }

    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    failures.append("MP3 review audio export failed; see logs/review_audio.log.")
    return {
        "schema": "demo_take_review_audio_v0",
        "status": "failed",
        "reason": f"ffmpeg_exit_{status}",
        "source": mic.get("relative_path"),
        "output": None,
        "log": relative(root, log_path),
    }


def _storage_file_row(root: Path, path: Path, role: str) -> dict[str, Any] | None:
    stat = _safe_stat(path)
    if stat is None or not path.is_file():
        return None
    return {
        "relative_path": relative(root, path),
        "role": role,
        "projection_state": _storage_projection_state_for_role(role),
        "bytes": stat.st_size,
        "sha256": f"sha256:{sha256_file(path)}",
    }


def _storage_role_for_path(rel_path: str, cloud_retention: str | None) -> str:
    suffix = Path(rel_path).suffix.lower()
    if rel_path.startswith("tracks/") and suffix in RAW_MEDIA_SUFFIXES:
        return "source_media"
    if rel_path == "semantic_proxy.json" or rel_path.startswith("frames/semantic/"):
        return "semantic_sidecar"
    if rel_path == "render/rough_cut.mp4":
        return "local_review_proxy" if cloud_retention == "proxy" else "local_review_video"
    if rel_path.startswith("render/proxy_") and suffix in RAW_MEDIA_SUFFIXES:
        return "local_review_proxy"
    if rel_path == "render/review_audio.mp3":
        return "local_review_audio"
    if rel_path in {"render/cloud_archive_manifest.json", "render/cloud_archive_receipt.json"}:
        return "cloud_archive_authority"
    if rel_path in {
        "render/storage_receipt.json",
        "render/local_storage_receipt.json",
        "render/proxy_review_receipt.json",
        SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH,
    }:
        return "storage_authority"
    if rel_path.startswith("frames/") or rel_path.startswith("review/"):
        return "review_thumbnail"
    if suffix in {".json", ".jsonl", ".vtt", ".srt", ".ffmetadata", ".otio"}:
        return "semantic_sidecar"
    if rel_path.startswith("logs/") or rel_path.endswith(".log"):
        return "diagnostic_log"
    if suffix in REVIEW_MEDIA_SUFFIXES:
        return "generated_media"
    return "other"


def _storage_projection_state_for_role(role: str) -> str:
    if role == "source_media":
        return "source_authority_raw"
    if role == "cloud_archive_authority":
        return "cloud_archive_authority"
    if role == "storage_authority":
        return "local_storage_authority"
    if role == "local_review_proxy":
        return "local_review_proxy"
    if role in {"local_review_video", "local_review_audio", "review_thumbnail", "generated_media"}:
        return "local_review_derivative"
    if role in {"semantic_sidecar", "diagnostic_log"}:
        return "local_control_plane"
    return "local_artifact"


def _storage_artifact_rows(root: Path, cloud_retention: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        row = _storage_file_row(root, path, _storage_role_for_path(relative(root, path), cloud_retention))
        if row:
            rows.append(row)
    return rows


def _sum_role_bytes(rows: list[dict[str, Any]], roles: set[str]) -> int:
    return sum(int(row.get("bytes") or 0) for row in rows if row.get("role") in roles)


def _cloud_prune_safe(archive_receipt: Mapping[str, Any]) -> bool:
    status = archive_receipt.get("status")
    if status == "ready":
        return True
    if status != "partial" or archive_receipt.get("local_retention") != "proxy":
        return False
    proxy_retention = archive_receipt.get("proxy_retention")
    return isinstance(proxy_retention, Mapping) and proxy_retention.get("status") in {"ready", "partial"}


def _cloud_storage_state(archive_receipt: Mapping[str, Any]) -> str:
    status = archive_receipt.get("status")
    if status == "ready":
        return "cloud_verified"
    if status == "partial":
        return "cloud_partial"
    if status == "failed":
        return "archive_failed"
    return "archive_missing"


def _proxy_review_state(root: Path, config: dict[str, Any]) -> tuple[str, Path | None, float | None]:
    proxy_path = root / "render" / "rough_cut.mp4"
    if not proxy_path.exists():
        return "proxy_missing", None, None
    duration = probe_media_duration_seconds(config, proxy_path)
    if duration is not None or _is_fake_capture(config):
        return "proxy_ready", proxy_path, duration
    return "proxy_present_unverified", proxy_path, None


def _local_raw_state(source_bytes: int, cloud_state: str, proxy_state: str, retention_policy: str) -> str:
    if source_bytes > 0:
        return "local_raw_present"
    if cloud_state in {"cloud_verified", "cloud_partial"} and proxy_state == "proxy_ready":
        if retention_policy == "review":
            return "review_local_raw_evicted"
        return "proxy_local_raw_evicted"
    if cloud_state in {"cloud_verified", "cloud_partial"}:
        return "hydrate_needed_no_proxy"
    return "raw_missing_unarchived"


def _storage_governor_state(
    *,
    cloud_state: str,
    raw_state: str,
    archive_enabled: bool,
    retention_policy: str,
) -> str:
    if cloud_state in {"cloud_verified", "cloud_partial"}:
        if raw_state == "local_raw_present":
            return "manual_source_retention" if retention_policy == "full" else "cloud_pending_raw_local"
        if retention_policy == "review":
            return "cloud_verified_review_local"
        return "cloud_verified_proxy_local"
    if cloud_state == "archive_failed":
        return "cloud_failed_raw_local_blocked"
    if raw_state == "local_raw_present" and archive_enabled:
        return "cloud_pending_raw_local"
    return "manual_source_retention"


def _storage_governor_operator_line(state: str, *, cloud_state: str, raw_state: str) -> str:
    if state == "cloud_verified_review_local":
        return (
            "Source media is archived in the cloud; local disk keeps the 720p review video "
            "and semantic inspection proxy, with heavy raw media restorable on demand."
        )
    if state == "cloud_verified_proxy_local":
        return (
            "Source media is archived in the cloud; only a small review proxy stays local "
            "and the original can be restored on demand."
        )
    if state == "cloud_failed_raw_local_blocked":
        return (
            "Cloud archive failed; the source media stays local and will not be pruned "
            "until a verified archive exists."
        )
    if state == "cloud_pending_raw_local":
        if cloud_state in {"cloud_verified", "cloud_partial"}:
            return "Cloud archive is verified but raw media is still local pending the proxy prune."
        return "Raw media exists only on this machine; the cloud archive has not completed yet."
    if raw_state == "local_raw_present":
        return "Source media is kept locally by explicit choice; nothing will be pruned automatically."
    return "No source-quality media is local and no verified cloud archive exists; custody is manual."


def _hydrate_state(local_raw_state: str, cloud_state: str) -> str:
    if local_raw_state == "local_raw_present":
        return "not_needed_raw_local"
    if cloud_state in {"cloud_verified", "cloud_partial"}:
        return "hydrate_available"
    return "hydrate_blocked_no_verified_archive"


def _restore_drill_projection(root: Path) -> dict[str, Any]:
    receipt = _read_json_dict(root / RESTORE_DRILL_RECEIPT_RELATIVE_PATH)
    if not receipt:
        return {
            "schema": "demo_take_restore_drill_projection_v0",
            "status": "missing",
        }
    status = str(receipt.get("status") or "missing")
    if status not in RESTORE_DRILL_STATUSES:
        status = "warn"
    return {
        "schema": "demo_take_restore_drill_projection_v0",
        "status": status,
        "checked_at": receipt.get("checked_at"),
        "transport_mode": receipt.get("transport_mode"),
        "source_hydrate_status": receipt.get("source_hydrate_status"),
        "sidecar_restore_status": receipt.get("sidecar_restore_status"),
        "compile_smoke_status": receipt.get("compile_smoke_status"),
        "cleanup_status": receipt.get("cleanup_status"),
        "blockers": receipt.get("blockers") if isinstance(receipt.get("blockers"), list) else [],
    }


def _source_requirement_lease_projection(root: Path) -> dict[str, Any]:
    receipt = _read_json_dict(root / SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH)
    if receipt.get("schema") != "demo_take_source_requirement_lease_v0":
        return {
            "schema": "demo_take_source_requirement_lease_projection_v0",
            "status": "missing",
            "active": False,
            "path": SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH,
        }
    status = str(receipt.get("status") or "unknown")
    prune_blocking = bool(receipt.get("prune_blocking")) and status in SOURCE_REQUIREMENT_PRUNE_BLOCKING_STATUSES
    return {
        "schema": "demo_take_source_requirement_lease_projection_v0",
        "status": status,
        "active": prune_blocking,
        "path": SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH,
        "lease_id": receipt.get("lease_id"),
        "operation": receipt.get("operation"),
        "required_source_classes": receipt.get("required_source_classes")
        if isinstance(receipt.get("required_source_classes"), list)
        else [],
        "required_source_paths": receipt.get("required_source_paths")
        if isinstance(receipt.get("required_source_paths"), list)
        else [],
        "operation_receipt": receipt.get("operation_receipt"),
        "release_condition": receipt.get("release_condition"),
        "satisfaction_status": (receipt.get("satisfaction") or {}).get("status")
        if isinstance(receipt.get("satisfaction"), Mapping)
        else None,
    }


def _generated_cache_eviction_projection(root: Path) -> dict[str, Any]:
    receipt = _read_json_dict(root / GENERATED_CACHE_EVICTION_RECEIPT_RELATIVE_PATH)
    if receipt.get("schema") != "demo_take_generated_cache_eviction_receipt_v0":
        return {
            "schema": "demo_take_generated_cache_eviction_projection_v0",
            "status": "missing",
            "receipt": GENERATED_CACHE_EVICTION_RECEIPT_RELATIVE_PATH,
        }
    return {
        "schema": "demo_take_generated_cache_eviction_projection_v0",
        "status": receipt.get("status") or "unknown",
        "receipt": GENERATED_CACHE_EVICTION_RECEIPT_RELATIVE_PATH,
        "created_at": receipt.get("created_at"),
        "dry_run": bool(receipt.get("dry_run")),
        "scope": receipt.get("scope"),
        "bytes_freed_physical": int(receipt.get("bytes_freed_physical") or 0),
        "bytes_freed_logical": int(receipt.get("bytes_freed_logical") or 0),
        "bytes_unlinked": int(receipt.get("bytes_unlinked") or 0),
        "candidate_count": int(receipt.get("candidate_count") or 0),
        "evicted_count": int(receipt.get("evicted_count") or 0),
        "blocked_count": int(receipt.get("blocked_count") or 0),
        "preservation_policy": receipt.get("preservation_policy")
        if isinstance(receipt.get("preservation_policy"), Mapping)
        else {},
    }


def _calibration_receipt_projection(root: Path) -> dict[str, Any]:
    receipt = _read_json_dict(root / CALIBRATION_RECEIPT_RELATIVE_PATH)
    if receipt.get("schema") != CALIBRATION_RECEIPT_SCHEMA:
        return {
            "schema": "demo_take_calibration_projection_v0",
            "status": "missing",
            "receipt": CALIBRATION_RECEIPT_RELATIVE_PATH,
        }
    return {
        "schema": "demo_take_calibration_projection_v0",
        "status": receipt.get("status") or "unknown",
        "receipt": CALIBRATION_RECEIPT_RELATIVE_PATH,
        "created_at": receipt.get("created_at"),
        "recording_quality": receipt.get("recording_quality"),
        "envelope_factor": receipt.get("envelope_factor"),
        "required_roles": receipt.get("required_roles") if isinstance(receipt.get("required_roles"), list) else [],
        "missing_required_roles": receipt.get("missing_required_roles")
        if isinstance(receipt.get("missing_required_roles"), list)
        else [],
        "missing_spliced_roles": receipt.get("missing_spliced_roles")
        if isinstance(receipt.get("missing_spliced_roles"), list)
        else [],
        "failing_track_count": int(receipt.get("failing_track_count") or 0),
        "track_count": int(receipt.get("track_count") or 0),
        "operator_line": receipt.get("operator_line"),
    }


def _timeline_sync_receipt_projection(root: Path) -> dict[str, Any]:
    receipt = _read_json_dict(root / TIMELINE_SYNC_RECEIPT_RELATIVE_PATH)
    if receipt.get("schema") != TIMELINE_SYNC_RECEIPT_SCHEMA:
        return {
            "schema": "demo_take_timeline_sync_projection_v0",
            "status": "missing",
            "receipt": TIMELINE_SYNC_RECEIPT_RELATIVE_PATH,
        }
    return {
        "schema": "demo_take_timeline_sync_projection_v0",
        "status": receipt.get("status") or "unknown",
        "receipt": TIMELINE_SYNC_RECEIPT_RELATIVE_PATH,
        "created_at": receipt.get("created_at"),
        "required_roles": receipt.get("required_roles") if isinstance(receipt.get("required_roles"), list) else [],
        "missing_required_roles": receipt.get("missing_required_roles")
        if isinstance(receipt.get("missing_required_roles"), list)
        else [],
        "failing_track_count": int(receipt.get("failing_track_count") or 0),
        "warning_track_count": int(receipt.get("warning_track_count") or 0),
        "corrected_track_count": int(receipt.get("corrected_track_count") or 0),
        "failing_boundary_count": int(receipt.get("failing_boundary_count") or 0),
        "track_count": int(receipt.get("track_count") or 0),
        "operator_line": receipt.get("operator_line"),
    }


def _calibration_role_from_track(track: Mapping[str, Any], role_hint: str | None = None) -> str | None:
    role = str(role_hint or track.get("role") or "").strip()
    return role if role in CALIBRATION_SOURCE_ROLES else None


def _append_calibration_track_row(
    rows: list[dict[str, Any]],
    seen: dict[tuple[str, str], dict[str, Any]],
    *,
    track: Mapping[str, Any],
    source: str,
    role_hint: str | None = None,
    rel_path: str | None = None,
) -> None:
    role = _calibration_role_from_track(track, role_hint=role_hint)
    rel = str(rel_path or track.get("relative_path") or "").strip()
    if not role or not rel:
        return
    key = (role, rel)
    existing = seen.get(key)
    if existing:
        sources = existing.setdefault("sources", [])
        if source not in sources:
            sources.append(source)
        return
    row = {
        "role": role,
        "relative_path": rel,
        "device_index": track.get("device_index"),
        "device_name": track.get("device_name"),
        "capture_engine": track.get("capture_engine"),
        "sources": [source],
        "generated_splice": rel.startswith("tracks/spliced/"),
    }
    rows.append(row)
    seen[key] = row


def _calibration_track_rows(session: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
    for track in tracks:
        if not isinstance(track, Mapping):
            continue
        _append_calibration_track_row(rows, seen, track=track, source="session_track")
        for source_rel in track.get("splice_source_tracks") or []:
            if isinstance(source_rel, str) and source_rel:
                _append_calibration_track_row(
                    rows,
                    seen,
                    track=track,
                    source="splice_source_track",
                    rel_path=source_rel,
                )
    for segment in session.get("media_segments") or []:
        if not isinstance(segment, Mapping):
            continue
        for screen_track in segment.get("screen_tracks") or []:
            if isinstance(screen_track, Mapping):
                _append_calibration_track_row(rows, seen, track=screen_track, source="media_segment")
        webcam_track = segment.get("webcam_track")
        if isinstance(webcam_track, Mapping):
            _append_calibration_track_row(rows, seen, track=webcam_track, source="media_segment")
        microphone_track = segment.get("microphone_track")
        if isinstance(microphone_track, Mapping):
            _append_calibration_track_row(rows, seen, track=microphone_track, source="media_segment")
    return rows


def _calibration_required_roles(config: Mapping[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    roles = {str(row.get("role")) for row in rows if row.get("role") in CALIBRATION_SOURCE_ROLES}
    if selected_capture_screens(config) or "screen" in roles:
        roles.add("screen")
    if config.get("microphone") or "microphone" in roles:
        roles.add("microphone")
    if config.get("webcam") or "webcam" in roles:
        roles.add("webcam")
    return sorted(role for role in roles if role in CALIBRATION_SOURCE_ROLES)


def _first_stream(probe: Mapping[str, Any], kind: str) -> Mapping[str, Any]:
    for stream in probe.get("streams") or []:
        if isinstance(stream, Mapping) and stream.get("codec_type") == kind:
            return stream
    return {}


def _calibration_track_probe(
    root: Path,
    config: Mapping[str, Any],
    row: Mapping[str, Any],
    *,
    fake_capture: bool,
) -> dict[str, Any]:
    role = str(row.get("role") or "")
    rel = str(row.get("relative_path") or "")
    path = root / rel
    stat = _safe_stat(path)
    payload: dict[str, Any] = {
        "role": role,
        "relative_path": rel,
        "sources": row.get("sources") if isinstance(row.get("sources"), list) else [],
        "generated_splice": bool(row.get("generated_splice")),
        "status": "pass",
        "failures": [],
        "warnings": [],
    }
    if stat is None or not path.is_file():
        payload["status"] = "fail"
        payload["failures"] = ["track_file_missing"]
        return payload

    payload["bytes"] = stat.st_size
    if fake_capture:
        payload.update({
            "duration_seconds": 6.0,
            "observed_bytes_per_second": round(stat.st_size / 6.0, 3),
            "observed_bytes_per_minute": round(stat.st_size / 6.0 * 60.0, 3),
            "budget_bytes_per_second": None,
            "max_allowed_bytes": None,
            "fixture": "fake_capture",
        })
        return payload

    probe = _probe_media_container(dict(config), path)
    payload["probe_status"] = probe.get("status")
    if probe.get("status") != "pass":
        payload["status"] = "fail"
        payload["failures"] = ["media_probe_failed"]
        payload["probe"] = probe
        return payload

    duration = _timeline_seconds(probe.get("duration_seconds"))
    if duration is None or duration < CALIBRATION_MIN_DURATION_SECONDS:
        payload["status"] = "fail"
        payload["failures"] = ["duration_too_short_or_unknown"]
        payload["duration_seconds"] = duration
        payload["probe"] = probe
        return payload

    budget_bps, budget_label = _calibration_budget_bytes_per_second(config, role)
    observed_bps = stat.st_size / duration
    max_allowed_bytes = int((budget_bps * duration * CALIBRATION_ENVELOPE_FACTOR) + CALIBRATION_FILE_OVERHEAD_BYTES)
    failures: list[str] = []
    warnings: list[str] = []
    if budget_bps <= 0:
        warnings.append("profile_budget_unknown")
    elif stat.st_size > max_allowed_bytes:
        failures.append("byte_slope_exceeds_profile_envelope")

    stream_kind = "audio" if role == "microphone" else "video"
    stream = _first_stream(probe, stream_kind)
    codec = str(stream.get("codec_name") or "")
    quality = recording_quality(dict(config))
    if role in {"screen", "webcam"}:
        width = _int_or_none(stream.get("width"))
        height = _int_or_none(stream.get("height"))
        payload["width"] = width
        payload["height"] = height
        if quality == "efficient":
            if codec and codec not in CALIBRATION_VIDEO_CODECS:
                failures.append("video_codec_not_h264")
            if width and width > EFFICIENT_VIDEO_MAX_WIDTH:
                failures.append("video_width_exceeds_efficient_cap")
            if height and height > EFFICIENT_VIDEO_MAX_HEIGHT:
                failures.append("video_height_exceeds_efficient_cap")
    elif role == "microphone" and quality == "efficient":
        if codec and codec not in CALIBRATION_AUDIO_CODECS:
            failures.append("audio_codec_not_aac")

    payload.update({
        "duration_seconds": round(duration, 3),
        "codec": codec or None,
        "observed_bytes_per_second": round(observed_bps, 3),
        "observed_bytes_per_minute": round(observed_bps * 60.0, 3),
        "observed_mbps": round(observed_bps * 8.0 / 1_000_000.0, 3),
        "budget_bitrate": budget_label,
        "budget_bytes_per_second": round(budget_bps, 3) if budget_bps > 0 else None,
        "budget_bytes_per_minute": round(budget_bps * 60.0, 3) if budget_bps > 0 else None,
        "max_allowed_bytes": max_allowed_bytes if budget_bps > 0 else None,
        "max_allowed_bytes_per_minute": round((max_allowed_bytes / duration) * 60.0, 3)
        if budget_bps > 0
        else None,
        "failures": failures,
        "warnings": warnings,
    })
    payload["status"] = "fail" if failures else ("warn" if warnings else "pass")
    return payload


def write_calibration_receipt(root: Path) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    rows = _calibration_track_rows(session)
    required_roles = _calibration_required_roles(config, rows)
    fake_capture = _is_fake_capture(config)
    track_results = [
        _calibration_track_probe(root, config, row, fake_capture=fake_capture)
        for row in rows
        if row.get("role") in CALIBRATION_SOURCE_ROLES
    ]
    roles_with_pass_or_warn = {
        str(row.get("role"))
        for row in track_results
        if row.get("status") in {"pass", "warn"}
    }
    missing_required_roles = [
        role
        for role in required_roles
        if role not in roles_with_pass_or_warn
    ]
    failing = [row for row in track_results if row.get("status") == "fail"]
    warning = [row for row in track_results if row.get("status") == "warn"]
    if missing_required_roles or failing or not track_results:
        status = "fail"
    elif warning:
        status = "warn"
    else:
        status = "pass"
    role_summary = {
        role: {
            "track_count": sum(1 for row in track_results if row.get("role") == role),
            "pass_count": sum(1 for row in track_results if row.get("role") == role and row.get("status") == "pass"),
            "warn_count": sum(1 for row in track_results if row.get("role") == role and row.get("status") == "warn"),
            "fail_count": sum(1 for row in track_results if row.get("role") == role and row.get("status") == "fail"),
        }
        for role in sorted(CALIBRATION_SOURCE_ROLES)
        if any(row.get("role") == role for row in track_results) or role in required_roles
    }
    if status == "pass":
        operator_line = "Calibration passed: observed track byte slopes match the configured recording profile."
    elif missing_required_roles:
        operator_line = "Calibration failed: required recorded roles are missing: " + ", ".join(missing_required_roles) + "."
    else:
        first_failure = next((row for row in failing if row.get("failures")), {})
        failures = ", ".join(str(item) for item in first_failure.get("failures") or [])
        operator_line = f"Calibration failed: {first_failure.get('relative_path')} {failures}."
    payload = {
        "schema": CALIBRATION_RECEIPT_SCHEMA,
        "command_version": CALIBRATION_COMMAND_VERSION,
        "created_at": now_iso(),
        "status": status,
        "take_id": session.get("take_id", root.name),
        "recording_quality": recording_quality(config),
        "storage_profile": storage_profile(config),
        "envelope_factor": CALIBRATION_ENVELOPE_FACTOR,
        "file_overhead_bytes": CALIBRATION_FILE_OVERHEAD_BYTES,
        "minimum_duration_seconds": CALIBRATION_MIN_DURATION_SECONDS,
        "fake_capture": fake_capture,
        "required_roles": required_roles,
        "missing_required_roles": missing_required_roles,
        "track_count": len(track_results),
        "failing_track_count": len(failing),
        "warning_track_count": len(warning),
        "role_summary": role_summary,
        "tracks": track_results,
        "operator_line": operator_line,
    }
    write_json(root / CALIBRATION_RECEIPT_RELATIVE_PATH, payload)
    return payload


def _storage_footprint_mode(*, source_bytes: int, cloud_state: str) -> str:
    if source_bytes <= 0 and cloud_state in {"cloud_verified", "cloud_partial"}:
        return "source_archived_proxy_local"
    if source_bytes <= 0:
        return "review_proxy_only"
    return "editor_package_local"


def _source_requirement_lease_payload(
    *,
    root: Path,
    take_id: str,
    operation: str,
    status: str,
    required_source_classes: list[str] | None = None,
    required_source_paths: list[str] | None = None,
    source_mode: str | None = None,
    hydrate_policy: str | None = None,
    release_condition: str | None = None,
    operation_receipt: str | None = None,
    satisfaction: Mapping[str, Any] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    existing = _read_json_dict(root / SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH)
    acquired_at = existing.get("acquired_at") if existing.get("schema") == "demo_take_source_requirement_lease_v0" else None
    now = now_iso()
    payload = {
        "schema": "demo_take_source_requirement_lease_v0",
        "lease_id": existing.get("lease_id") or f"{take_id}_{operation}",
        "take_id": take_id,
        "operation": operation,
        "status": status,
        "acquired_at": acquired_at or now,
        "updated_at": now,
        "released_at": now if status == "released" else None,
        "prune_blocking": status in SOURCE_REQUIREMENT_PRUNE_BLOCKING_STATUSES,
        "required_source_classes": sorted(set(required_source_classes or existing.get("required_source_classes") or [])),
        "required_source_paths": sorted(set(required_source_paths or existing.get("required_source_paths") or [])),
        "source_mode": source_mode or existing.get("source_mode"),
        "hydrate_policy": hydrate_policy or existing.get("hydrate_policy"),
        "release_condition": release_condition or existing.get("release_condition"),
        "operation_receipt": operation_receipt or existing.get("operation_receipt"),
        "satisfaction": dict(satisfaction or existing.get("satisfaction") or {}),
        "blockers": blockers if blockers is not None else (existing.get("blockers") if isinstance(existing.get("blockers"), list) else []),
    }
    write_json(root / SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH, payload)
    return payload


def _transition_source_requirement_lease(
    root: Path,
    *,
    status: str,
    operation_receipt: str | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any] | None:
    existing = _read_json_dict(root / SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH)
    if existing.get("schema") != "demo_take_source_requirement_lease_v0":
        return None
    payload = dict(existing)
    payload["status"] = status
    payload["updated_at"] = now_iso()
    payload["prune_blocking"] = status in SOURCE_REQUIREMENT_PRUNE_BLOCKING_STATUSES
    if status == "released":
        payload["released_at"] = payload["updated_at"]
    if operation_receipt:
        payload["operation_receipt"] = operation_receipt
    if blockers is not None:
        payload["blockers"] = blockers
    write_json(root / SOURCE_REQUIREMENT_LEASE_RELATIVE_PATH, payload)
    return payload


def _storage_prune_decision(
    *,
    source_bytes: int,
    cloud_receipt: Mapping[str, Any],
    proxy_state: str,
    active_source_requirement_lease_count: int = 0,
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if source_bytes <= 0:
        blockers.append("no_local_raw_media")
    if not _cloud_prune_safe(cloud_receipt):
        blockers.append("cloud_archive_not_verified")
    if proxy_state != "proxy_ready":
        blockers.append("local_review_proxy_not_ready")
    if active_source_requirement_lease_count > 0:
        blockers.append("active_source_requirement_lease")
    return not blockers, blockers


def _disk_policy_row(root: Path) -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(root)
        free = usage.free
    except OSError:
        free = None
    if free is None:
        status = "unknown"
    elif free < LOCAL_STORAGE_HARD_FLOOR_BYTES:
        status = "below_hard_floor"
    elif free < LOCAL_STORAGE_SOFT_FLOOR_BYTES:
        status = "below_soft_floor"
    else:
        status = "ok"
    return {
        "status": status,
        "free_bytes": free,
        "hard_floor_bytes": LOCAL_STORAGE_HARD_FLOOR_BYTES,
        "soft_floor_bytes": LOCAL_STORAGE_SOFT_FLOOR_BYTES,
        "target_free_bytes": LOCAL_STORAGE_TARGET_FREE_BYTES,
    }


def write_local_storage_receipt(
    root: Path,
    config: dict[str, Any],
    session: Mapping[str, Any],
) -> dict[str, Any]:
    archive_receipt = _read_json_dict(root / "render" / "cloud_archive_receipt.json")
    cloud_retention = archive_receipt.get("local_retention") if isinstance(archive_receipt.get("local_retention"), str) else None
    rows = _storage_artifact_rows(root, cloud_retention)
    source_bytes = _sum_role_bytes(rows, {"source_media"})
    proxy_bytes = _sum_role_bytes(rows, {"local_review_proxy", "local_review_video"})
    sidecar_bytes = _sum_role_bytes(rows, {"semantic_sidecar", "storage_authority", "cloud_archive_authority"})
    review_bytes = _sum_role_bytes(rows, {"local_review_audio", "review_thumbnail"})
    generated_media_bytes = _sum_role_bytes(rows, {"generated_media"})
    physical_bytes = directory_size_bytes(root, physical=True) if root.exists() else 0
    logical_bytes = directory_size_bytes(root, physical=False) if root.exists() else 0
    proxy_state, proxy_path, proxy_duration = _proxy_review_state(root, config)
    cloud_state = _cloud_storage_state(archive_receipt)
    retention_policy = cloud_archive_local_retention(config)
    if cloud_retention in CLOUD_ARCHIVE_LOCAL_RETENTIONS:
        retention_policy = str(cloud_retention)
    raw_state = _local_raw_state(source_bytes, cloud_state, proxy_state, retention_policy)
    source_requirement_lease = _source_requirement_lease_projection(root)
    active_source_requirement_lease_count = 1 if source_requirement_lease.get("active") else 0
    prune_allowed, prune_blockers = _storage_prune_decision(
        source_bytes=source_bytes,
        cloud_receipt=archive_receipt,
        proxy_state=proxy_state,
        active_source_requirement_lease_count=active_source_requirement_lease_count,
    )
    archive_enabled = cloud_archive_after_stop(config)
    governor_state = _storage_governor_state(
        cloud_state=cloud_state,
        raw_state=raw_state,
        archive_enabled=archive_enabled,
        retention_policy=retention_policy,
    )
    review_proxy_footprint_bytes = proxy_bytes + review_bytes + sidecar_bytes
    footprint_mode = _storage_footprint_mode(source_bytes=source_bytes, cloud_state=cloud_state)
    configured_root = take_output_root(Path(config.get("repo_root") or REPO_ROOT), config)
    active_spool = {
        "mode": "configured_external_root" if config.get("local_archive_root") else "repo_default",
        "root": str(configured_root),
        "package_root": str(root),
        "legacy_config_key": "local_archive_root" if config.get("local_archive_root") else None,
        "recipient": recipient_metadata(config),
    }
    payload = {
        "schema": "demo_take_local_storage_receipt_v1",
        "compat_schema": "demo_take_storage_receipt_v0",
        "status": "ready",
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "storage_profile": storage_profile(config),
        "recording_quality": recording_quality(config),
        "physical_bytes": physical_bytes,
        "logical_bytes": logical_bytes,
        "source_bytes": source_bytes,
        "proxy_bytes": proxy_bytes,
        "review_bytes": review_bytes,
        "semantic_sidecar_bytes": sidecar_bytes,
        "generated_media_bytes": generated_media_bytes,
        "archived_bytes": int(archive_receipt.get("total_bytes") or 0),
        "local_raw_state": raw_state,
        "cloud_state": cloud_state,
        "hydrate_state": _hydrate_state(raw_state, cloud_state),
        "proxy_state": proxy_state,
        "proxy": {
            "relative_path": relative(root, proxy_path) if proxy_path else None,
            "duration_seconds": proxy_duration,
            "bytes": proxy_path.stat().st_size if proxy_path and proxy_path.exists() else None,
        },
        "active_spool": active_spool,
        "local_archive": {
            "enabled": bool(config.get("local_archive_root")),
            "root": str(configured_root),
            "package_root": str(root),
            "recipient": recipient_metadata(config),
            "compat_note": "Legacy alias for active_spool; source-original custody is cloud_archive.",
        },
        "prune_allowed": prune_allowed,
        "prune_blockers": prune_blockers,
        "source_requirement_lease": source_requirement_lease,
        "active_source_requirement_lease_count": active_source_requirement_lease_count,
        "generated_cache_eviction": _generated_cache_eviction_projection(root),
        "calibration": _calibration_receipt_projection(root),
        "timeline_sync": _timeline_sync_receipt_projection(root),
        "footprints": {
            "schema": "demo_take_storage_footprints_v0",
            "mode": footprint_mode,
            "review_proxy_footprint_bytes": review_proxy_footprint_bytes,
            "retained_source_package_footprint_bytes": physical_bytes,
            "retained_source_delta_bytes": max(0, physical_bytes - review_proxy_footprint_bytes),
            "source_bytes": source_bytes,
            "proxy_bytes": proxy_bytes,
            "review_bytes": review_bytes,
            "semantic_sidecar_bytes": sidecar_bytes,
            "generated_media_bytes": generated_media_bytes,
            "operator_line": (
                f"Review/proxy footprint is {human_bytes(review_proxy_footprint_bytes)}; "
                f"retained local package footprint is {human_bytes(physical_bytes)}."
            ),
        },
        "storage_governor": {
            "schema": "demo_take_storage_governor_v0",
            "state": governor_state,
            "operator_line": _storage_governor_operator_line(
                governor_state,
                cloud_state=cloud_state,
                raw_state=raw_state,
            ),
            "archive_after_stop": archive_enabled,
            "local_retention_policy": retention_policy,
            "restore_drill": _restore_drill_projection(root),
        },
        "cloud_archive": {
            "status": archive_receipt.get("status") or "missing",
            "remote": archive_receipt.get("remote"),
            "remote_take_path": archive_receipt.get("remote_take_path"),
            "manifest_sha256": archive_receipt.get("manifest_sha256"),
            "local_retention": archive_receipt.get("local_retention"),
        },
        "disk_policy": _disk_policy_row(root),
        "artifact_role_counts": {
            role: sum(1 for row in rows if row.get("role") == role)
            for role in sorted({str(row.get("role")) for row in rows})
        },
        "artifacts": rows,
    }
    write_json(root / "render" / "local_storage_receipt.json", payload)
    write_json(root / "render" / "storage_receipt.json", payload)
    return payload


LOCAL_VIDEO_COMPACTION_SUFFIXES = {".mp4", ".mov", ".m4v"}


def _local_video_compaction_candidates(root: Path) -> tuple[list[Path], list[tuple[Path, Path]]]:
    candidates: list[Path] = []
    for base in (root / "tracks", root / "render"):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in LOCAL_VIDEO_COMPACTION_SUFFIXES:
                continue
            try:
                rel_parts = path.relative_to(root).parts
            except ValueError:
                rel_parts = path.parts
            if any(part.startswith(".") for part in rel_parts):
                continue
            candidates.append(path)

    primaries: list[Path] = []
    aliases: list[tuple[Path, Path]] = []
    seen: dict[tuple[int, int], Path] = {}
    for path in candidates:
        try:
            stat = path.stat()
        except OSError:
            continue
        key = (stat.st_dev, stat.st_ino)
        primary = seen.get(key)
        if primary is not None:
            aliases.append((path, primary))
            continue
        seen[key] = path
        primaries.append(path)
    return primaries, aliases


def _fraction_to_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text or text in {"0/0", "N/A"}:
        return None
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        try:
            denominator_value = float(denominator)
            if denominator_value == 0:
                return None
            return float(numerator) / denominator_value
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _video_compaction_role(source: Path) -> str:
    lowered = "/".join(part.lower() for part in source.parts)
    return "webcam" if "webcam" in lowered else "screen"


def _efficient_video_profile_rewrite_required(
    root: Path,
    config: Mapping[str, Any],
    source: Path,
    *,
    source_stat: os.stat_result | None = None,
) -> bool:
    if recording_quality(dict(config)) != DEFAULT_RECORDING_QUALITY:
        return False
    probe = _probe_media_container(dict(config), source)
    if probe.get("status") != "pass":
        return False
    stream = _first_stream(probe, "video")
    if not stream:
        return False
    codec = str(stream.get("codec_name") or "")
    if codec and codec not in CALIBRATION_VIDEO_CODECS:
        return True
    width = _int_or_none(stream.get("width"))
    height = _int_or_none(stream.get("height"))
    if width is not None and width > EFFICIENT_VIDEO_MAX_WIDTH:
        return True
    if height is not None and height > EFFICIENT_VIDEO_MAX_HEIGHT:
        return True
    frame_rate = _fraction_to_float(stream.get("avg_frame_rate")) or _fraction_to_float(stream.get("r_frame_rate"))
    if frame_rate is not None and frame_rate > 30.5:
        return True
    duration = _timeline_seconds(probe.get("duration_seconds"))
    stat = source_stat or _safe_stat(source)
    if duration is None or duration < CALIBRATION_MIN_DURATION_SECONDS or stat is None:
        return False
    budget_bps, _budget_label = _calibration_budget_bytes_per_second(
        {"recording_quality": DEFAULT_RECORDING_QUALITY},
        _video_compaction_role(source.relative_to(root) if source.is_relative_to(root) else source),
    )
    if budget_bps <= 0:
        return False
    max_allowed_bytes = int((budget_bps * duration * CALIBRATION_ENVELOPE_FACTOR) + CALIBRATION_FILE_OVERHEAD_BYTES)
    return stat.st_size > max_allowed_bytes


def _compact_video_file_720p30(root: Path, config: Mapping[str, Any], source: Path, *, force: bool = False) -> dict[str, Any]:
    source_stat = _safe_stat(source)
    if source_stat is None or source_stat.st_size <= 0:
        return {
            "status": "skipped",
            "relative_path": relative(root, source),
            "reason": "missing_or_empty",
        }

    if _is_fake_capture(config):
        return {
            "status": "skipped",
            "relative_path": relative(root, source),
            "reason": "fake_capture_fixture",
            "bytes_before": source_stat.st_size,
            "bytes_after": source_stat.st_size,
            "bytes_saved": 0,
        }

    profile_rewrite_required = _efficient_video_profile_rewrite_required(
        root,
        config,
        source,
        source_stat=source_stat,
    )
    ffmpeg = config.get("ffmpeg_path") or shutil.which("ffmpeg")
    if not ffmpeg:
        return {
            "status": "failed",
            "relative_path": relative(root, source),
            "reason": "ffmpeg_missing",
            "bytes_before": source_stat.st_size,
            "bytes_after": source_stat.st_size,
            "bytes_saved": 0,
            "profile_rewrite_required": profile_rewrite_required,
        }

    tmp = source.with_name(f".{source.stem}.720p30_tmp_{secrets.token_hex(4)}{source.suffix}")
    log_path = root / "logs" / "compact_storage.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    video_filter = efficient_video_filter({"recording_quality": "efficient"})
    commands = [
        [
            str(ffmpeg),
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            video_filter,
            "-r",
            "30",
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            EFFICIENT_SCREEN_BITRATE,
            "-c:a",
            "aac",
            "-b:a",
            EFFICIENT_AUDIO_BITRATE,
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(tmp),
        ],
        [
            str(ffmpeg),
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            video_filter,
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            EFFICIENT_SCREEN_BITRATE,
            "-c:a",
            "aac",
            "-b:a",
            EFFICIENT_AUDIO_BITRATE,
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(tmp),
        ],
    ]
    status = 1
    used_encoder = None
    with log_path.open("ab") as log:
        for command in commands:
            used_encoder = command[command.index("-c:v") + 1]
            log.write(f"=== {now_iso()} compact {relative(root, source)} encoder={used_encoder}: {' '.join(command)}\n".encode("utf-8"))
            try:
                status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
            except OSError as exc:
                log.write(f"compact unavailable: {exc}\n".encode("utf-8"))
                status = 1
            if status == 0 and tmp.exists() and tmp.stat().st_size > 0:
                break
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass

    if status != 0 or not tmp.exists() or tmp.stat().st_size <= 0:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return {
            "status": "failed",
            "relative_path": relative(root, source),
            "reason": "ffmpeg_compaction_failed",
            "bytes_before": source_stat.st_size,
            "bytes_after": source_stat.st_size,
            "bytes_saved": 0,
            "encoder": used_encoder,
        }

    tmp_size = tmp.stat().st_size
    if not force and not profile_rewrite_required and tmp_size >= source_stat.st_size:
        try:
            tmp.unlink()
        except OSError:
            pass
        return {
            "status": "skipped",
            "relative_path": relative(root, source),
            "reason": "output_not_smaller",
            "bytes_before": source_stat.st_size,
            "bytes_after": source_stat.st_size,
            "bytes_saved": 0,
            "candidate_bytes": tmp_size,
            "encoder": used_encoder,
            "profile_rewrite_required": profile_rewrite_required,
        }

    before_sha = f"sha256:{sha256_file(source)}"
    os.replace(tmp, source)
    after_size = source.stat().st_size
    return {
        "status": "ready",
        "relative_path": relative(root, source),
        "method": "in_place_720p30_compaction",
        "video_stream_action": "reencode_720p30",
        "bytes_before": source_stat.st_size,
        "bytes_after": after_size,
        "bytes_saved": max(0, source_stat.st_size - after_size),
        "before_sha256": before_sha,
        "after_sha256": f"sha256:{sha256_file(source)}",
        "encoder": used_encoder,
        "profile": "720p30_efficient",
        "profile_rewrite_required": profile_rewrite_required,
    }


def compact_storage(root: Path, *, prune_source_media: bool = False, force: bool = False) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    config = dict(session.get("config", {}))
    config["storage_profile"] = "efficient"
    config["recording_quality"] = "efficient"
    config["frame_thumbnail_width"] = _config_int(
        config,
        "frame_thumbnail_width",
        EFFICIENT_VIDEO_MAX_WIDTH,
        minimum=320,
        maximum=2560,
    )
    config["frame_jpeg_quality"] = _config_int(
        config,
        "frame_jpeg_quality",
        DEFAULT_FRAME_JPEG_QUALITY,
        minimum=2,
        maximum=12,
    )
    tracks = session.get("tracks", [])
    markers = session.get("markers", [])
    pause_events = session.get("pause_events", [])
    failures: list[str] = []
    manifest_state = "package_ready"
    try:
        existing_manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        manifest_state = str(existing_manifest.get("recording_state") or manifest_state)
    except (OSError, ValueError, TypeError):
        pass

    before_physical = directory_size_bytes(root, physical=True)
    before_logical = directory_size_bytes(root, physical=False)
    screen = next((track for track in tracks if track.get("role") == "screen"), None)
    rough_keep = root / "render" / "rough_cut.mp4"
    rough_duration: float | None = None
    rough_probe_ready = False

    video_candidates, hardlink_aliases = _local_video_compaction_candidates(root)
    compaction_records: list[dict[str, Any]] = []
    for candidate in video_candidates:
        result = _compact_video_file_720p30(root, config, candidate, force=force)
        compaction_records.append(result)
        if result.get("status") == "failed":
            failures.append(f"Could not compact {result.get('relative_path')}: {result.get('reason')}")

    alias_records: list[dict[str, Any]] = []
    for alias, primary in hardlink_aliases:
        if not primary.exists():
            continue
        rel_alias = relative(root, alias)
        rel_primary = relative(root, primary)
        before_alias = _safe_stat(alias)
        if replace_with_hardlink(alias, primary):
            after_alias = _safe_stat(alias)
            alias_records.append(
                {
                    "status": "ready",
                    "relative_path": rel_alias,
                    "hardlinked_to": rel_primary,
                    "bytes_before": before_alias.st_size if before_alias else None,
                    "bytes_after": after_alias.st_size if after_alias else None,
                }
            )
        else:
            failures.append(f"Could not restore hardlink dedupe for {rel_alias} -> {rel_primary}.")

    if rough_keep.exists():
        rough_duration = probe_media_duration_seconds(config, rough_keep)
        rough_probe_ready = rough_duration is not None or _is_fake_capture(config)

    if screen:
        frame_records = sample_frames(root, config, tracks, failures)
        if frame_records:
            write_json(
                root / "visual_index.json",
                {
                    "schema": "demo_take_visual_index_v0",
                    "take_id": session.get("take_id", root.name),
                    "created_at": now_iso(),
                    "frames": frame_records,
                    "storage_profile": "efficient",
                    "thumbnail_width": config["frame_thumbnail_width"],
                    "jpeg_quality": config["frame_jpeg_quality"],
                },
            )
    else:
        failures.append("No screen track found; imported video package did not need screen/rough-cut dedupe.")

    pruned: list[dict[str, Any]] = []
    prune_failures: list[str] = []
    prune_status = "skipped"
    if prune_source_media:
        lease = _source_requirement_lease_projection(root)
        if lease.get("active") and not force:
            prune_status = "blocked"
            prune_failures.append("active_source_requirement_lease")
        elif not rough_keep.exists():
            prune_status = "blocked"
            prune_failures.append("local_review_video_missing")
        elif not rough_probe_ready and not _is_fake_capture(config):
            prune_status = "blocked"
            prune_failures.append("local_review_video_not_verified")
        else:
            for candidate in _media_prune_candidates(root, rough_keep):
                rel = relative(root, candidate)
                try:
                    size = candidate.stat().st_size
                    candidate.unlink()
                    pruned.append({"relative_path": rel, "bytes": size})
                except OSError as exc:
                    prune_failures.append(f"Could not prune {rel}: {exc}")
            prune_status = "ready" if not prune_failures else "partial"
        failures.extend(prune_failures)

    session["config"] = config
    session["known_failures"] = list(dict.fromkeys(session.get("known_failures", []) + failures))
    write_json(session_path, session)

    if "repo_root" in config and "ffmpeg_path" in config and "screenshot_interval_seconds" in config:
        write_json(
            root / "manifest.json",
            manifest(
                session.get("take_id", root.name),
                root,
                manifest_state,
                config,
                tracks,
                session["known_failures"],
                markers=markers,
                pause_events=pause_events,
            ),
        )

    after_physical = directory_size_bytes(root, physical=True)
    after_logical = directory_size_bytes(root, physical=False)
    saved = max(0, before_physical - after_physical)
    receipt = write_local_storage_receipt(root, config, session)
    ready_count = sum(1 for row in compaction_records if row.get("status") == "ready")
    failed_count = sum(1 for row in compaction_records if row.get("status") == "failed")
    skipped_count = sum(1 for row in compaction_records if row.get("status") == "skipped")
    if failed_count:
        compact_status = "partial" if ready_count or skipped_count else "failed"
    elif video_candidates:
        compact_status = "ready"
    else:
        compact_status = "skipped"
    receipt["compact_storage"] = {
        "status": compact_status if not prune_failures else ("partial" if compact_status == "ready" else compact_status),
        "method": "in_place_720p30_video_compaction",
        "bytes_before_physical": before_physical,
        "bytes_after_physical": after_physical,
        "bytes_saved_physical": saved,
        "bytes_before_logical": before_logical,
        "bytes_after_logical": after_logical,
        "video_file_count": len(video_candidates),
        "video_files_compacted": ready_count,
        "video_files_skipped": skipped_count,
        "video_files_failed": failed_count,
        "video_compaction": compaction_records,
        "hardlink_aliases_restored": alias_records,
        "review_video": {
            "relative_path": relative(root, rough_keep) if rough_keep.exists() else None,
            "duration_seconds": rough_duration,
            "bytes": rough_keep.stat().st_size if rough_keep.exists() else None,
            "profile": "720p30_efficient",
            "video_bitrate": EFFICIENT_SCREEN_BITRATE,
            "audio_bitrate": EFFICIENT_AUDIO_BITRATE,
        },
        "proxy": None,
        "prune_source_media": bool(prune_source_media),
        "prune_status": prune_status,
        "pruned_files": pruned,
        "pruned_bytes": sum(int(row["bytes"]) for row in pruned),
        "prune_failures": prune_failures,
        "known_failures": failures,
    }
    write_json(root / "render" / "local_storage_receipt.json", receipt)
    write_json(root / "render" / "storage_receipt.json", receipt)
    line = (
        f"Optimized storage for {session.get('take_id', root.name)}: "
        f"saved {human_bytes(saved)} by compacting local videos to 720p30."
    )
    if not video_candidates:
        line = "Storage compact skipped: no local video files were found."
    return {
        "schema": "demo_take_compact_storage_result_v0",
        "status": receipt["compact_storage"]["status"],
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "bytesBefore": before_physical,
        "bytesAfter": after_physical,
        "bytesSaved": saved,
        "knownFailures": failures,
        "compactStorage": receipt["compact_storage"],
        "storageReceipt": receipt,
        "statusLines": [line],
    }


def _iter_take_roots(takes_root: Path) -> list[Path]:
    if not takes_root.exists():
        return []
    roots: list[Path] = []
    for session_path in sorted(takes_root.rglob("session.json")):
        root = session_path.parent
        if (root / "manifest.json").exists() or (root / "tracks").exists() or (root / "render").exists():
            roots.append(root)
    return roots


def compact_all_storage(
    takes_root: Path,
    *,
    prune_source_media: bool = False,
    force: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    roots = _iter_take_roots(takes_root)
    if limit is not None:
        roots = roots[: max(0, limit)]
    usage_root = disk_usage_probe_root(takes_root)
    before_free = shutil.disk_usage(usage_root).free
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    if dry_run:
        return {
            "schema": "demo_take_compact_all_storage_result_v0",
            "status": "dry_run",
            "takesRoot": str(takes_root),
            "takeCount": len(roots),
            "pruneSourceMedia": prune_source_media,
            "roots": [str(root) for root in roots],
            "freeBytesBefore": before_free,
        }
    for root in roots:
        try:
            result = compact_storage(root, prune_source_media=prune_source_media, force=force)
            results.append(result)
        except Exception as exc:  # noqa: BLE001 - batch command should continue across damaged packages.
            failures.append(f"{root}: {exc}")
            results.append({
                "schema": "demo_take_compact_storage_result_v0",
                "status": "failed",
                "rootPath": str(root),
                "knownFailures": [str(exc)],
            })
    after_free = shutil.disk_usage(usage_root).free
    saved = sum(int(result.get("bytesSaved") or 0) for result in results)
    ready_count = sum(1 for result in results if result.get("status") == "ready")
    partial_count = sum(1 for result in results if result.get("status") == "partial")
    failed_count = sum(1 for result in results if result.get("status") == "failed")
    skipped_count = sum(1 for result in results if result.get("status") == "skipped")
    status = "ready" if not failures and failed_count == 0 else ("partial" if results else "skipped")
    return {
        "schema": "demo_take_compact_all_storage_result_v0",
        "status": status,
        "takesRoot": str(takes_root),
        "takeCount": len(results),
        "readyCount": ready_count,
        "partialCount": partial_count,
        "failedCount": failed_count,
        "skippedCount": skipped_count,
        "pruneSourceMedia": prune_source_media,
        "force": force,
        "bytesSaved": saved,
        "freeBytesBefore": before_free,
        "freeBytesAfter": after_free,
        "freeBytesDelta": after_free - before_free,
        "knownFailures": failures,
        "results": results,
        "statusLines": [
            f"Compacted {ready_count}/{len(results)} take package(s); "
            f"saved {human_bytes(saved)} inside packages "
            f"({human_bytes(max(0, after_free - before_free))} free-disk delta)."
        ],
    }


def _is_generated_cache_evictable_rel(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/").lstrip("/")
    return (
        any(normalized.startswith(prefix) for prefix in GENERATED_CACHE_EVICTABLE_PREFIXES)
        or _is_generated_render_parts_cache_rel(normalized)
    )


def _is_generated_render_parts_cache_rel(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/").lstrip("/")
    parts = normalized.split("/")
    return (
        len(parts) >= 4
        and parts[0] == "render"
        and any(part.startswith(".") and part.endswith(GENERATED_RENDER_PARTS_CACHE_SUFFIX) for part in parts[1:-1])
    )


def _has_generated_splice_cache(root: Path) -> bool:
    for prefix in GENERATED_SPLICE_CACHE_EVICTABLE_PREFIXES:
        path = root / prefix
        if path.exists() and any(path.rglob("*")):
            return True
    return False


def _phrase_frame_cache_ready(root: Path) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if not (root / "phrase_cards.jsonl").exists():
        blockers.append("phrase_cards_jsonl_missing")
    receipt = _read_json_dict(root / "phrase_card_receipt.json")
    if receipt.get("schema") != "demo_take_phrase_card_receipt_v0":
        blockers.append("phrase_card_receipt_missing_or_invalid")
    return not blockers, blockers


def _generated_phrase_frame_cache_rows(root: Path, seen: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    frame_root = root / GENERATED_PHRASE_FRAME_CACHE_PREFIX
    if not frame_root.exists():
        return [], []
    ready, cache_blockers = _phrase_frame_cache_ready(root)
    rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for path in sorted(frame_root.rglob("*")):
        if not path.exists():
            continue
        try:
            normalized = relative(root, path).replace("\\", "/").lstrip("/")
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        row = {
            "relative_path": normalized,
            "kind": "phrase_card_midpoint_frame",
            "top_level_output": "phrase_cards.jsonl",
            "source_tracks": [],
            "bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
        }
        row_blockers = list(cache_blockers)
        if not _is_generated_cache_evictable_rel(normalized):
            row_blockers.append("not_generated_cache_path")
        if path.is_symlink():
            row_blockers.append("symlink_candidate_blocked")
        elif not path.is_file():
            row_blockers.append("candidate_not_file")
        try:
            path.resolve().relative_to(root.resolve())
        except (OSError, ValueError):
            row_blockers.append("candidate_outside_take_root")
        if row_blockers or not ready:
            blocked.append({**row, "status": "blocked", "blockers": row_blockers})
        else:
            rows.append({**row, "status": "ready"})
    return rows, blocked


def _render_part_cache_sibling_paths(parts_dir: Path) -> tuple[Path | None, Path]:
    name = parts_dir.name
    stem = name[1:-len(GENERATED_RENDER_PARTS_CACHE_SUFFIX)] if name.startswith(".") else name[:-len(GENERATED_RENDER_PARTS_CACHE_SUFFIX)]
    output: Path | None = None
    for suffix in (".mp4", ".mov", ".m4v"):
        candidate = parts_dir.parent / f"{stem}{suffix}"
        if candidate.exists():
            output = candidate
            break
    return output, parts_dir.parent / f"{stem}.render_receipt.json"


def _generated_render_part_cache_rows(root: Path, seen: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    render_root = root / "render"
    if not render_root.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for parts_dir in sorted(render_root.rglob(f".*{GENERATED_RENDER_PARTS_CACHE_SUFFIX}")):
        if not parts_dir.is_dir():
            continue
        output, receipt = _render_part_cache_sibling_paths(parts_dir)
        dir_blockers: list[str] = []
        if output is None:
            dir_blockers.append("final_render_output_missing")
        if not receipt.exists():
            dir_blockers.append("render_receipt_missing")
        for path in sorted(parts_dir.rglob("*")):
            if not path.exists():
                continue
            try:
                normalized = relative(root, path).replace("\\", "/").lstrip("/")
            except ValueError:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            row = {
                "relative_path": normalized,
                "kind": "render_part_cache",
                "top_level_output": relative(root, output) if output else None,
                "render_receipt": relative(root, receipt) if receipt.exists() else None,
                "source_tracks": [],
                "bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
            }
            row_blockers = list(dir_blockers)
            if not _is_generated_cache_evictable_rel(normalized):
                row_blockers.append("not_generated_cache_path")
            if path.is_symlink():
                row_blockers.append("symlink_candidate_blocked")
            elif not path.is_file():
                row_blockers.append("candidate_not_file")
            try:
                path.resolve().relative_to(root.resolve())
            except (OSError, ValueError):
                row_blockers.append("candidate_outside_take_root")
            if row_blockers:
                blocked.append({**row, "status": "blocked", "blockers": row_blockers})
            else:
                rows.append({**row, "status": "ready"})
    return rows, blocked


def _generated_cache_candidate_rows(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    edit_plan = _read_json_dict(root / "render" / "edit_plan.json")
    rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    seen: set[str] = set()
    if edit_plan.get("schema") != "demo_take_pause_splice_plan_v0":
        if _has_generated_splice_cache(root):
            blocked.append({
                "relative_path": "render/edit_plan.json",
                "status": "blocked",
                "reason": "edit_plan_missing_or_invalid",
            })
    else:
        outputs = edit_plan.get("outputs") if isinstance(edit_plan.get("outputs"), list) else []
        for output_row in outputs:
            if not isinstance(output_row, Mapping):
                continue
            output_rel = str(output_row.get("relative_path") or "")
            output_path = root / output_rel if output_rel else root / "__missing_output__"
            source_tracks = [
                str(item)
                for item in (output_row.get("source_tracks") if isinstance(output_row.get("source_tracks"), list) else [])
                if isinstance(item, str) and item
            ]
            blockers: list[str] = []
            if not output_rel or not output_path.exists():
                blockers.append("top_level_output_missing")
            for source_rel in source_tracks:
                if _is_generated_cache_evictable_rel(source_rel):
                    continue
                if not (root / source_rel).exists():
                    blockers.append(f"source_track_missing:{source_rel}")

            rels: list[tuple[str, str]] = []
            for normalization in output_row.get("normalizations") or []:
                if not isinstance(normalization, Mapping):
                    continue
                rel = normalization.get("output")
                if isinstance(rel, str) and rel:
                    rels.append((rel, "normalization_part"))
            for rel in output_row.get("placeholder_tracks") or []:
                if isinstance(rel, str) and rel:
                    rels.append((rel, "webcam_placeholder"))

            for rel_path, reason in rels:
                normalized = rel_path.replace("\\", "/").lstrip("/")
                if normalized in seen:
                    continue
                seen.add(normalized)
                path = root / normalized
                row = {
                    "relative_path": normalized,
                    "kind": reason,
                    "top_level_output": output_rel or None,
                    "source_tracks": source_tracks,
                    "bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
                }
                row_blockers = list(blockers)
                if not _is_generated_cache_evictable_rel(normalized):
                    row_blockers.append("not_generated_cache_path")
                if not path.exists():
                    row_blockers.append("candidate_missing")
                elif path.is_symlink():
                    row_blockers.append("symlink_candidate_blocked")
                elif not path.is_file():
                    row_blockers.append("candidate_not_file")
                try:
                    path.resolve().relative_to(root.resolve())
                except (OSError, ValueError):
                    row_blockers.append("candidate_outside_take_root")
                if row_blockers:
                    blocked.append({**row, "status": "blocked", "blockers": row_blockers})
                else:
                    rows.append({**row, "status": "ready"})
    frame_rows, frame_blocked = _generated_phrase_frame_cache_rows(root, seen)
    rows.extend(frame_rows)
    blocked.extend(frame_blocked)
    render_part_rows, render_part_blocked = _generated_render_part_cache_rows(root, seen)
    rows.extend(render_part_rows)
    blocked.extend(render_part_blocked)
    return rows, blocked


def _remove_empty_generated_cache_dirs(root: Path) -> list[str]:
    removed: list[str] = []
    base_dirs = [
        root / "tracks" / "spliced" / "parts",
        root / "tracks" / "spliced" / "placeholders",
        root / "frames" / "phrase_cards",
    ]
    render_root = root / "render"
    if render_root.exists():
        base_dirs.extend(path for path in render_root.rglob(f".*{GENERATED_RENDER_PARTS_CACHE_SUFFIX}") if path.is_dir())
    for base in base_dirs:
        if not base.exists():
            continue
        dirs = [path for path in sorted(base.rglob("*"), reverse=True) if path.is_dir()]
        dirs.append(base)
        for directory in dirs:
            try:
                directory.rmdir()
            except OSError:
                continue
            removed.append(relative(root, directory))
    return removed


def _generated_cache_rows_for_receipt(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    limit = GENERATED_CACHE_EVICTION_RECEIPT_ROW_LIMIT
    return rows[:limit], max(0, len(rows) - limit)


def _generated_cache_rows_by_kind(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        kind = str(row.get("kind") or "unknown")
        bucket = summary.setdefault(kind, {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += int(row.get("bytes") or 0)
    return summary


def evict_generated_cache(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    before_physical = directory_size_bytes(root, physical=True) if root.exists() else 0
    before_logical = directory_size_bytes(root, physical=False) if root.exists() else 0
    candidates, blocked = _generated_cache_candidate_rows(root)
    evicted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    removed_dirs: list[str] = []

    if not dry_run:
        for row in candidates:
            path = root / str(row["relative_path"])
            stat = _safe_stat(path)
            if stat is None or not path.is_file():
                skipped.append({**row, "status": "skipped", "reason": "candidate_disappeared"})
                continue
            try:
                path.unlink()
            except OSError as exc:
                blocked.append({**row, "status": "blocked", "blockers": [f"unlink_failed:{exc}"]})
                continue
            evicted.append({**row, "status": "evicted", "bytes": stat.st_size})
        removed_dirs = _remove_empty_generated_cache_dirs(root)

    after_physical = directory_size_bytes(root, physical=True) if root.exists() else 0
    after_logical = directory_size_bytes(root, physical=False) if root.exists() else 0
    if dry_run:
        status = "dry_run" if candidates else ("blocked" if blocked else "noop")
    elif blocked and evicted:
        status = "partial"
    elif blocked and not evicted:
        status = "blocked"
    elif evicted:
        status = "ready"
    else:
        status = "noop"
    bytes_unlinked = sum(int(row.get("bytes") or 0) for row in evicted)
    candidate_rows, candidate_omitted_count = _generated_cache_rows_for_receipt(candidates)
    blocked_rows, blocked_omitted_count = _generated_cache_rows_for_receipt(blocked)
    evicted_rows, evicted_omitted_count = _generated_cache_rows_for_receipt(evicted)
    skipped_rows, skipped_omitted_count = _generated_cache_rows_for_receipt(skipped)

    session = _read_json_dict(root / "session.json")
    receipt = {
        "schema": "demo_take_generated_cache_eviction_receipt_v0",
        "status": status,
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "dry_run": dry_run,
        "scope": "rebuildable_generated_splice_phrase_frame_and_render_part_cache_only",
        "evictable_prefixes": list(GENERATED_CACHE_EVICTABLE_PREFIXES),
        "preservation_policy": {
            "raw_source_tracks": "preserved",
            "top_level_spliced_tracks": "preserved",
            "review_deliverables": "preserved",
            "semantic_sidecars": "preserved",
            "phrase_card_attribution": "preserved_in_phrase_cards_jsonl_and_receipt",
            "phrase_card_midpoint_frames": "evicted_only_when_phrase_card_receipt_is_ready",
            "render_deliverables": "preserved",
            "render_part_cache": "evicted_only_when_sibling_output_and_render_receipt_exist",
            "diagnostic_logs": "preserved",
        },
        "bytes_before_physical": before_physical,
        "bytes_after_physical": after_physical,
        "bytes_freed_physical": max(0, before_physical - after_physical),
        "bytes_unlinked": bytes_unlinked,
        "bytes_before_logical": before_logical,
        "bytes_after_logical": after_logical,
        "bytes_freed_logical": max(0, before_logical - after_logical),
        "candidate_count": len(candidates),
        "blocked_count": len(blocked),
        "evicted_count": len(evicted),
        "skipped_count": len(skipped),
        "row_preview_limit": GENERATED_CACHE_EVICTION_RECEIPT_ROW_LIMIT,
        "row_omitted_counts": {
            "candidates": candidate_omitted_count,
            "blocked": blocked_omitted_count,
            "evicted": evicted_omitted_count,
            "skipped": skipped_omitted_count,
        },
        "candidate_summary_by_kind": _generated_cache_rows_by_kind(candidates),
        "blocked_summary_by_kind": _generated_cache_rows_by_kind(blocked),
        "evicted_summary_by_kind": _generated_cache_rows_by_kind(evicted),
        "skipped_summary_by_kind": _generated_cache_rows_by_kind(skipped),
        "candidates": candidate_rows,
        "blocked": blocked_rows,
        "evicted": evicted_rows,
        "skipped": skipped_rows,
        "removed_empty_dirs": removed_dirs,
    }
    receipt_path = root / GENERATED_CACHE_EVICTION_RECEIPT_RELATIVE_PATH
    write_json(receipt_path, receipt)

    if not dry_run:
        config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
        storage_receipt = write_local_storage_receipt(root, config, session)
        storage_receipt["generated_cache_eviction"] = {
            "status": receipt["status"],
            "receipt": GENERATED_CACHE_EVICTION_RECEIPT_RELATIVE_PATH,
            "bytes_freed_physical": receipt["bytes_freed_physical"],
            "bytes_freed_logical": receipt["bytes_freed_logical"],
            "bytes_unlinked": receipt["bytes_unlinked"],
            "evicted_count": receipt["evicted_count"],
            "blocked_count": receipt["blocked_count"],
            "preservation_policy": receipt["preservation_policy"],
        }
        write_json(root / "render" / "local_storage_receipt.json", storage_receipt)
        write_json(root / "render" / "storage_receipt.json", storage_receipt)

    line = (
        f"Evicted {len(evicted)} generated cache file(s), freeing "
        f"{human_bytes(receipt['bytes_freed_physical'])}."
    )
    if dry_run:
        line = f"Dry run: {len(candidates)} generated cache file(s) are evictable."
    elif not candidates and blocked:
        line = "Generated cache eviction blocked; see render/generated_cache_eviction_receipt.json."
    elif not candidates:
        line = "Generated cache eviction skipped: no rebuildable generated cache files were found."
    return {
        "schema": "demo_take_generated_cache_eviction_result_v0",
        "status": status,
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "receipt": GENERATED_CACHE_EVICTION_RECEIPT_RELATIVE_PATH,
        "bytesFreed": receipt["bytes_freed_physical"],
        "bytesUnlinked": receipt["bytes_unlinked"],
        "evictedCount": len(evicted),
        "blockedCount": len(blocked),
        "dryRun": dry_run,
        "statusLines": [line],
    }


def _ready_json_status(root: Path, rel_path: str, *, ready_status: str = "ready") -> bool:
    payload = _read_json_dict(root / rel_path)
    return payload.get("status") == ready_status


def _local_retention_candidate_rows(
    root: Path,
    *,
    drop_review_video: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    transcript_ready = _ready_json_status(root, "transcript/transcript.json")
    semantic_proxy_ready = _ready_json_status(root, "semantic_proxy.json")
    review_audio_ready = (root / "render" / "review_audio.mp3").is_file()
    archive_receipt = _read_json_dict(root / "render" / "cloud_archive_receipt.json")
    cloud_safe = _cloud_prune_safe(archive_receipt)
    source_requirement_lease = _source_requirement_lease_projection(root)
    source_lease_active = bool(source_requirement_lease.get("active"))

    def add(rel_path: str, role: str, blockers: list[str]) -> None:
        path = root / rel_path
        stat = _safe_stat(path)
        if stat is None or not path.is_file() or stat.st_size <= 0:
            return
        row = {
            "relative_path": rel_path,
            "role": role,
            "bytes": stat.st_size,
            "blockers": blockers,
        }
        if blockers:
            blocked.append({**row, "status": "blocked"})
        else:
            candidates.append({**row, "status": "ready"})

    add(
        "render/rough_audio.m4a",
        "redundant_split_review_audio",
        [] if review_audio_ready else ["review_audio_mp3_missing"],
    )

    if drop_review_video:
        video_blockers: list[str] = []
        if not cloud_safe:
            video_blockers.append("cloud_archive_not_verified")
        if source_lease_active:
            video_blockers.append("active_source_requirement_lease")
        if not (transcript_ready or semantic_proxy_ready):
            video_blockers.append("transcript_or_semantic_proxy_missing")
        for rel_path in [
            "render/rough_cut.mp4",
            "render/rough_cut.autoedit.mp4",
            "render/rough_video.mp4",
        ]:
            add(rel_path, "cloud_hydratable_review_video", list(video_blockers))

    return candidates, blocked


def _local_retention_summary_by_role(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        role = str(row.get("role") or "unknown")
        bucket = summary.setdefault(role, {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += int(row.get("bytes") or 0)
    return summary


def minimize_local_retention(
    root: Path,
    *,
    drop_review_video: bool = False,
    dry_run: bool = False,
    standardize_review_audio: bool = True,
) -> dict[str, Any]:
    before_physical = directory_size_bytes(root, physical=True) if root.exists() else 0
    before_logical = directory_size_bytes(root, physical=False) if root.exists() else 0
    audio_standardization: dict[str, Any] | None = None
    if standardize_review_audio and not dry_run:
        session_for_audio = _read_json_dict(root / "session.json")
        config_for_audio = dict(session_for_audio.get("config") if isinstance(session_for_audio.get("config"), Mapping) else {})
        tracks_for_audio = session_for_audio.get("tracks") if isinstance(session_for_audio.get("tracks"), list) else []
        audio_failures: list[str] = []
        audio_standardization = write_review_audio_mp3(root, config_for_audio, tracks_for_audio, audio_failures)
        if audio_failures:
            audio_standardization["known_failures"] = audio_failures

    candidates, blocked = _local_retention_candidate_rows(root, drop_review_video=drop_review_video)
    evicted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    if not dry_run:
        for row in candidates:
            path = root / str(row["relative_path"])
            stat = _safe_stat(path)
            if stat is None or not path.is_file():
                skipped.append({**row, "status": "skipped", "reason": "candidate_disappeared"})
                continue
            try:
                path.unlink()
            except OSError as exc:
                blocked.append({**row, "status": "blocked", "blockers": [f"unlink_failed:{exc}"]})
                continue
            evicted.append({**row, "status": "evicted", "bytes": stat.st_size})

    after_physical = directory_size_bytes(root, physical=True) if root.exists() else 0
    after_logical = directory_size_bytes(root, physical=False) if root.exists() else 0
    if dry_run:
        status = "dry_run" if candidates else ("blocked" if blocked else "noop")
    elif blocked and evicted:
        status = "partial"
    elif blocked and not evicted:
        status = "blocked"
    elif evicted:
        status = "ready"
    else:
        status = "noop"

    session = _read_json_dict(root / "session.json")
    receipt = {
        "schema": "demo_take_local_retention_minimize_receipt_v0",
        "status": status,
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "dry_run": dry_run,
        "drop_review_video": drop_review_video,
        "standardize_review_audio": standardize_review_audio,
        "review_audio_standardization": audio_standardization,
        "scope": "transient_transcription_audio_and_optional_cloud_hydratable_review_video",
        "preservation_policy": {
            "transcript_json": "preserved",
            "transcript_srt": "preserved",
            "transcription_audio_cache": "preserved_as_local_rebuild_anchor",
            "semantic_proxy": "preserved",
            "review_audio_mp3": "preserved",
            "section_annotations": "preserved",
            "cloud_archive_receipt": "preserved",
            "rough_cut_video": "evicted_only_with_cloud_archive_and_no_active_source_lease",
        },
        "bytes_before_physical": before_physical,
        "bytes_after_physical": after_physical,
        "bytes_freed_physical": max(0, before_physical - after_physical),
        "bytes_before_logical": before_logical,
        "bytes_after_logical": after_logical,
        "bytes_freed_logical": max(0, before_logical - after_logical),
        "bytes_unlinked": sum(int(row.get("bytes") or 0) for row in evicted),
        "candidate_count": len(candidates),
        "blocked_count": len(blocked),
        "evicted_count": len(evicted),
        "skipped_count": len(skipped),
        "candidate_summary_by_role": _local_retention_summary_by_role(candidates),
        "blocked_summary_by_role": _local_retention_summary_by_role(blocked),
        "evicted_summary_by_role": _local_retention_summary_by_role(evicted),
        "skipped_summary_by_role": _local_retention_summary_by_role(skipped),
        "candidates": candidates,
        "blocked": blocked,
        "evicted": evicted,
        "skipped": skipped,
    }

    if not dry_run:
        write_json(root / LOCAL_RETENTION_MINIMIZE_RECEIPT_RELATIVE_PATH, receipt)
        config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
        storage_receipt = write_local_storage_receipt(root, config, session)
        storage_receipt["local_retention_minimize"] = {
            "status": receipt["status"],
            "receipt": LOCAL_RETENTION_MINIMIZE_RECEIPT_RELATIVE_PATH,
            "drop_review_video": drop_review_video,
            "standardize_review_audio": standardize_review_audio,
            "bytes_freed_physical": receipt["bytes_freed_physical"],
            "bytes_unlinked": receipt["bytes_unlinked"],
            "evicted_count": receipt["evicted_count"],
            "blocked_count": receipt["blocked_count"],
            "preservation_policy": receipt["preservation_policy"],
        }
        write_json(root / "render" / "local_storage_receipt.json", storage_receipt)
        write_json(root / "render" / "storage_receipt.json", storage_receipt)

    line = (
        f"Minimized local retention for {session.get('take_id', root.name)}: "
        f"freed {human_bytes(receipt['bytes_freed_physical'])}."
    )
    if dry_run:
        preview_bytes = sum(int(row.get("bytes") or 0) for row in candidates)
        line = f"Dry run: {len(candidates)} local-retention file(s) are evictable ({human_bytes(preview_bytes)})."
    elif blocked and not evicted:
        line = "Local retention minimization blocked; see render/local_retention_minimize_receipt.json."
    elif not candidates and not evicted:
        line = "Local retention minimization skipped: no eligible transient/review files were found."
    return {
        "schema": "demo_take_local_retention_minimize_result_v0",
        "status": status,
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "receipt": None if dry_run else LOCAL_RETENTION_MINIMIZE_RECEIPT_RELATIVE_PATH,
        "dropReviewVideo": drop_review_video,
        "standardizeReviewAudio": standardize_review_audio,
        "bytesFreed": receipt["bytes_freed_physical"],
        "bytesUnlinked": receipt["bytes_unlinked"],
        "candidateCount": len(candidates),
        "evictedCount": len(evicted),
        "blockedCount": len(blocked),
        "dryRun": dry_run,
        "statusLines": [line],
    }


def minimize_all_local_retention(
    takes_root: Path,
    *,
    drop_review_video: bool = False,
    dry_run: bool = False,
    standardize_review_audio: bool = True,
    keep_recent: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    roots = _iter_take_roots(takes_root)
    if keep_recent > 0:
        roots_by_mtime = sorted(roots, key=lambda path: path.stat().st_mtime if path.exists() else 0)
        protected = {path.name for path in roots_by_mtime[len(roots_by_mtime) - keep_recent:]}
    else:
        protected = set()
    roots = [root for root in roots if root.name not in protected]
    if limit is not None:
        roots = roots[: max(0, limit)]

    usage_root = disk_usage_probe_root(takes_root)
    before_free = shutil.disk_usage(usage_root).free
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for root in roots:
        try:
            results.append(
                minimize_local_retention(
                    root,
                    drop_review_video=drop_review_video,
                    dry_run=dry_run,
                    standardize_review_audio=standardize_review_audio,
                )
            )
        except Exception as exc:  # noqa: BLE001 - batch cleanup should continue across damaged packages.
            failures.append(f"{root}: {exc}")
            results.append({
                "schema": "demo_take_local_retention_minimize_result_v0",
                "status": "failed",
                "rootPath": str(root),
                "knownFailures": [str(exc)],
            })
    after_free = shutil.disk_usage(usage_root).free
    saved = sum(int(result.get("bytesFreed") or 0) for result in results)
    unlinked = sum(int(result.get("bytesUnlinked") or 0) for result in results)
    ready_count = sum(1 for result in results if result.get("status") == "ready")
    partial_count = sum(1 for result in results if result.get("status") == "partial")
    blocked_count = sum(1 for result in results if result.get("status") == "blocked")
    failed_count = sum(1 for result in results if result.get("status") == "failed")
    dry_run_count = sum(1 for result in results if result.get("status") == "dry_run")
    noop_count = sum(1 for result in results if result.get("status") == "noop")
    if dry_run:
        status = "dry_run"
    elif failures or failed_count:
        status = "partial" if results else "failed"
    elif blocked_count and (ready_count or partial_count):
        status = "partial"
    elif blocked_count:
        status = "blocked"
    elif ready_count or partial_count:
        status = "ready"
    else:
        status = "noop"
    return {
        "schema": "demo_take_minimize_all_local_retention_result_v0",
        "status": status,
        "takesRoot": str(takes_root),
        "takeCount": len(results),
        "protectedRecentCount": len(protected),
        "dropReviewVideo": drop_review_video,
        "standardizeReviewAudio": standardize_review_audio,
        "dryRun": dry_run,
        "readyCount": ready_count,
        "partialCount": partial_count,
        "blockedCount": blocked_count,
        "failedCount": failed_count,
        "dryRunCount": dry_run_count,
        "noopCount": noop_count,
        "bytesFreed": saved,
        "bytesUnlinked": unlinked,
        "freeBytesBefore": before_free,
        "freeBytesAfter": after_free,
        "freeBytesDelta": after_free - before_free,
        "knownFailures": failures,
        "results": results,
        "statusLines": [
            f"Minimized {ready_count + partial_count}/{len(results)} take package(s); "
            f"freed {human_bytes(saved)} ({human_bytes(max(0, after_free - before_free))} free-disk delta)."
        ],
    }


def storage_status(root: Path) -> dict[str, Any]:
    session_path = root / "session.json"
    session: dict[str, Any] = {}
    if session_path.exists():
        session = json.loads(session_path.read_text(encoding="utf-8"))
    tracks = session.get("tracks", [])
    screen = next((track for track in tracks if track.get("role") == "screen"), None)
    screen_path = root / screen["relative_path"] if screen else None

    receipt_path = root / "render" / "render_receipt.json"
    receipt: dict[str, Any] = {}
    if receipt_path.exists():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except ValueError:
            receipt = {}

    rough_output = receipt.get("output") if isinstance(receipt.get("output"), str) else None
    rough_candidates: list[Path] = []
    if rough_output:
        rough_candidates.append(root / rough_output)
    rough_candidates.extend(sorted((root / "render").glob("rough_cut.*")))
    rough_path = next((candidate for candidate in rough_candidates if candidate.exists()), None)

    physical_bytes = directory_size_bytes(root, physical=True) if root.exists() else 0
    logical_bytes = directory_size_bytes(root, physical=False) if root.exists() else 0
    hardlinked = bool(screen_path and rough_path and files_are_same(screen_path, rough_path))
    dedupe_saved = max(0, logical_bytes - physical_bytes)
    can_compact = bool(screen_path and rough_path and screen_path.exists() and rough_path.exists() and not hardlinked)
    imported_video = any(track.get("role") == "external_video" for track in tracks)
    archive_receipt = _read_json_dict(root / "render" / "cloud_archive_receipt.json")
    local_storage_receipt = _read_json_dict(root / "render" / "local_storage_receipt.json")
    if not local_storage_receipt:
        local_storage_receipt = _read_json_dict(root / "render" / "storage_receipt.json")
    status = "ready" if root.exists() else "missing"
    storage_line = f"{human_bytes(physical_bytes)} disk"
    if dedupe_saved:
        storage_line += f" - {human_bytes(dedupe_saved)} deduped"
    elif can_compact:
        storage_line += " - can optimize"
    elif imported_video:
        storage_line += " - imported asset"
    else:
        storage_line += " - optimized"
    if archive_receipt.get("status") in {"ready", "partial"}:
        if archive_receipt.get("local_retention") == "proxy":
            storage_line += " - cloud archived, proxy local"
        elif archive_receipt.get("local_retention") == "review":
            storage_line += " - cloud archived, review local"
        else:
            storage_line += " - cloud archived"
    if local_storage_receipt.get("status") == "ready":
        source_bytes = int(local_storage_receipt.get("source_bytes") or 0)
        proxy_bytes = int(local_storage_receipt.get("proxy_bytes") or 0)
        footprints = local_storage_receipt.get("footprints") if isinstance(local_storage_receipt.get("footprints"), dict) else {}
        if source_bytes:
            storage_line += f" - raw {human_bytes(source_bytes)}"
        if proxy_bytes:
            storage_line += f" - proxy {human_bytes(proxy_bytes)}"
        if footprints:
            storage_line += (
                f" - review footprint {human_bytes(int(footprints.get('review_proxy_footprint_bytes') or 0))}"
                f" / retained package {human_bytes(int(footprints.get('retained_source_package_footprint_bytes') or physical_bytes))}"
            )
        if local_storage_receipt.get("hydrate_state") == "hydrate_available":
            storage_line += " - hydrate available"
    governor = local_storage_receipt.get("storage_governor")
    governor = governor if isinstance(governor, dict) else {}
    governor_state = governor.get("state")
    restore_drill = governor.get("restore_drill") if isinstance(governor.get("restore_drill"), dict) else {}
    if governor_state == "cloud_failed_raw_local_blocked":
        storage_line += " - archive failed, raw kept"
    elif governor_state == "cloud_pending_raw_local":
        storage_line += " - raw local, archive pending"
    if restore_drill.get("status") == "pass":
        storage_line += " - restore drill passed"
    elif restore_drill.get("status") in {"warn", "fail"}:
        storage_line += f" - restore drill {restore_drill.get('status')}"

    status_lines = [storage_line]
    if governor.get("operator_line"):
        status_lines.append(str(governor["operator_line"]))
    footprints = local_storage_receipt.get("footprints") if isinstance(local_storage_receipt.get("footprints"), dict) else {}
    if footprints.get("operator_line"):
        status_lines.append(str(footprints["operator_line"]))
    calibration = local_storage_receipt.get("calibration") if isinstance(local_storage_receipt.get("calibration"), dict) else {}
    if calibration.get("operator_line"):
        status_lines.append(str(calibration["operator_line"]))
    if restore_drill.get("status") == "pass" and restore_drill.get("checked_at"):
        status_lines.append(f"Restore drill passed at {restore_drill['checked_at']}.")
    elif restore_drill.get("status") in {"warn", "fail"}:
        status_lines.append(f"Restore drill {restore_drill.get('status')}: {', '.join(restore_drill.get('blockers') or [])}.")

    return {
        "schema": "demo_take_storage_status_v0",
        "status": status,
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "physicalBytes": physical_bytes,
        "logicalBytes": logical_bytes,
        "dedupeSavedBytes": dedupe_saved,
        "roughCutScreenHardlinked": hardlinked,
        "canCompact": can_compact,
        "storageLine": storage_line,
        "screenTrack": screen.get("relative_path") if screen else None,
        "roughCut": relative(root, rough_path) if rough_path else None,
        "renderStorageOptimization": receipt.get("storage_optimization"),
        "cloudArchive": {
            "status": archive_receipt.get("status") or "missing",
            "remoteTakePath": archive_receipt.get("remote_take_path"),
            "localRetention": archive_receipt.get("local_retention"),
            "manifestSha256": archive_receipt.get("manifest_sha256"),
            "transportMode": (archive_receipt.get("transport") or {}).get("mode")
            if isinstance(archive_receipt.get("transport"), dict)
            else None,
        },
        "localStorage": {
            "status": local_storage_receipt.get("status") or "missing",
            "localRawState": local_storage_receipt.get("local_raw_state"),
            "cloudState": local_storage_receipt.get("cloud_state"),
            "hydrateState": local_storage_receipt.get("hydrate_state"),
            "proxyState": local_storage_receipt.get("proxy_state"),
            "sourceBytes": local_storage_receipt.get("source_bytes"),
            "proxyBytes": local_storage_receipt.get("proxy_bytes"),
            "reviewBytes": local_storage_receipt.get("review_bytes"),
            "semanticSidecarBytes": local_storage_receipt.get("semantic_sidecar_bytes"),
            "generatedMediaBytes": local_storage_receipt.get("generated_media_bytes"),
            "footprints": footprints,
            "calibration": calibration,
            "pruneAllowed": local_storage_receipt.get("prune_allowed"),
            "pruneBlockers": local_storage_receipt.get("prune_blockers"),
        },
        "storageGovernor": {
            "state": governor_state,
            "operatorLine": governor.get("operator_line"),
            "archiveAfterStop": governor.get("archive_after_stop"),
            "localRetentionPolicy": governor.get("local_retention_policy"),
            "restoreDrill": {
                "status": restore_drill.get("status") or "missing",
                "checkedAt": restore_drill.get("checked_at"),
                "transportMode": restore_drill.get("transport_mode"),
                "sourceHydrateStatus": restore_drill.get("source_hydrate_status"),
                "sidecarRestoreStatus": restore_drill.get("sidecar_restore_status"),
                "compileSmokeStatus": restore_drill.get("compile_smoke_status"),
                "cleanupStatus": restore_drill.get("cleanup_status"),
                "blockers": restore_drill.get("blockers") or [],
            },
        },
        "statusLines": status_lines,
    }


def _read_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _playable_video_asset(root: Path, session: Mapping[str, Any]) -> Path | None:
    preferred = [
        root / "render" / "rough_cut.autoedit.mp4",
    ]
    receipt = _read_json_dict(root / "render" / "render_receipt.json")
    output = receipt.get("output")
    if isinstance(output, str):
        preferred.append(root / output)
    preferred.extend(sorted((root / "render").glob("rough_cut.*")))
    tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
    for track in tracks:
        if not isinstance(track, Mapping) or track.get("role") not in {"external_video", "screen", "webcam"}:
            continue
        rel = track.get("relative_path")
        if isinstance(rel, str):
            preferred.append(root / rel)
    for candidate in preferred:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in EXTERNAL_VIDEO_EXTENSIONS:
            return candidate
    return None


def _proxy_source_video_asset(root: Path, session: Mapping[str, Any]) -> Path | None:
    preferred: list[Path] = []
    tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
    for role in ["screen", "external_video", "webcam"]:
        for track in tracks:
            if not isinstance(track, Mapping) or track.get("role") != role:
                continue
            rel = track.get("relative_path")
            if isinstance(rel, str):
                preferred.append(root / rel)
    preferred.append(root / "render" / "rough_cut.autoedit.mp4")
    receipt = _read_json_dict(root / "render" / "render_receipt.json")
    output = receipt.get("output")
    if isinstance(output, str):
        preferred.append(root / output)
    preferred.extend(sorted((root / "render").glob("rough_cut.*")))
    for candidate in preferred:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in EXTERNAL_VIDEO_EXTENSIONS:
            return candidate
    return None


def _safe_filename_token(value: Any, fallback: str = "clip") -> str:
    token = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "").strip()).strip("-")
    return token[:96] or fallback


def _load_candidate_clip(root: Path, clip_id: str) -> dict[str, Any]:
    payload = _read_json_dict(root / "candidate_clips.json")
    clips = payload.get("clips") if isinstance(payload.get("clips"), list) else []
    for clip in clips:
        if isinstance(clip, Mapping) and str(clip.get("id") or "") == clip_id:
            return dict(clip)
    raise ValueError(f"candidate clip not found: {clip_id}")


def _range_seconds_from_clip(clip: Mapping[str, Any]) -> tuple[float, float, str]:
    safe = clip.get("safe_render_range") if isinstance(clip.get("safe_render_range"), Mapping) else {}
    start = _timeline_seconds(safe.get("start_seconds"))
    end = _timeline_seconds(safe.get("end_seconds"))
    if start is None and safe.get("start_active_us") is not None:
        start = float(safe.get("start_active_us")) / 1_000_000
    if end is None and safe.get("end_active_us") is not None:
        end = float(safe.get("end_active_us")) / 1_000_000
    if start is None:
        start = _timeline_seconds(clip.get("start_seconds"))
    if end is None:
        end = _timeline_seconds(clip.get("end_seconds"))
    if start is None or end is None or end <= start:
        raise ValueError(f"candidate clip {clip.get('id') or '<unknown>'} lacks a valid render range")
    policy = str(safe.get("policy") or "display_range_fallback")
    return start, end, policy


def _clip_proxy_source(root: Path, session: Mapping[str, Any], clip: Mapping[str, Any]) -> Path:
    source_refs = clip.get("source_refs") if isinstance(clip.get("source_refs"), list) else []
    for ref in source_refs:
        if not isinstance(ref, Mapping):
            continue
        proxy = ref.get("proxy_path")
        if isinstance(proxy, str) and proxy:
            path = root / proxy
            if path.exists():
                return path
    source = _playable_video_asset(root, session)
    if source is None:
        raise FileNotFoundError("no playable proxy/review video asset was found for clip render")
    return source


def _resolve_proxy_source(root: Path, session: Mapping[str, Any], clip_id: str) -> Path | None:
    """Resolve a proxy source for a plan item.

    Prefers the candidate clip's proxy refs when the clip exists, but an explicit
    edit plan is its own authority — so a clip_id absent from candidate_clips falls
    back to the take's playable review asset rather than blocking.
    """
    try:
        clip = _load_candidate_clip(root, clip_id)
        return _clip_proxy_source(root, session, clip)
    except (ValueError, FileNotFoundError):
        return _playable_video_asset(root, session)


def _probe_media_stream_kinds(config: Mapping[str, Any], path: Path) -> set[str] | None:
    ffprobe = _ffprobe_path(dict(config))
    if not ffprobe or not path.exists():
        return None
    command = [
        ffprobe,
        "-hide_banner",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(getattr(proc, "stdout", "") or "{}")
    except json.JSONDecodeError:
        return None
    streams = payload.get("streams")
    if not isinstance(streams, list):
        return None
    return {
        str(stream.get("codec_type"))
        for stream in streams
        if isinstance(stream, Mapping) and stream.get("codec_type")
    }


def _clip_render_command(
    ffmpeg: str,
    source: Path,
    output: Path,
    *,
    start: float,
    end: float,
    include_audio: bool,
) -> list[str]:
    video_filter = f"[0:v:0]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[v]"
    command = [ffmpeg, "-hide_banner", "-y", "-i", str(source)]
    if include_audio:
        audio_filter = f"[0:a:0]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a]"
        command += [
            "-filter_complex",
            f"{video_filter};{audio_filter}",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output),
        ]
    else:
        command += [
            "-filter_complex",
            video_filter,
            "-map",
            "[v]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(output),
        ]
    return command


def _transcript_coverage_for_range(root: Path, start: float, end: float) -> float | None:
    transcript = _read_json_dict(root / "transcript" / "transcript.json")
    segments = transcript.get("segments") if isinstance(transcript.get("segments"), list) else []
    if not segments or end <= start:
        return None
    covered = 0.0
    for segment in segments:
        if not isinstance(segment, Mapping):
            continue
        seg_start = _timeline_seconds(segment.get("start"))
        seg_end = _timeline_seconds(segment.get("end"))
        if seg_start is None or seg_end is None:
            continue
        covered += max(0.0, min(end, seg_end) - max(start, seg_start))
    return round(min(1.0, covered / max(0.001, end - start)), 6)


def _write_clip_render_index(root: Path, receipt: Mapping[str, Any]) -> None:
    index_path = root / "render" / "clips" / "index.json"
    existing = _read_json_dict(index_path)
    rows = existing.get("renders") if isinstance(existing.get("renders"), list) else []
    rows = [row for row in rows if not (isinstance(row, Mapping) and row.get("clip_id") == receipt.get("clip_id"))]
    rows.append({
        "clip_id": receipt.get("clip_id"),
        "status": receipt.get("status"),
        "output": receipt.get("output"),
        "receipt": receipt.get("receipt_path"),
        "created_at": receipt.get("created_at"),
        "duration_seconds": receipt.get("output_duration_seconds"),
    })
    write_json(
        index_path,
        {
            "schema": "demo_take_clip_render_index_v0",
            "take_id": receipt.get("take_id"),
            "updated_at": now_iso(),
            "render_count": len(rows),
            "renders": rows,
        },
    )


def render_candidate_clip(root: Path, clip_id: str, *, quality: str = "proxy") -> dict[str, Any]:
    if quality != "proxy":
        raise ValueError("only proxy clip render is implemented; final raw-shard render is not wired yet")
    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    ffmpeg = str(config.get("ffmpeg_path") or shutil.which("ffmpeg") or "").strip()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg executable not found for clip render")
    clip = _load_candidate_clip(root, clip_id)
    start, end, cut_policy = _range_seconds_from_clip(clip)
    source = _clip_proxy_source(root, session, clip)
    clip_token = _safe_filename_token(clip_id)
    output_dir = root / "render" / "clips"
    output = output_dir / f"{clip_token}_{quality}.mp4"
    output_tmp = output_dir / f".{clip_token}_{quality}.tmp.mp4"
    receipt_path = output_dir / f"{clip_token}_{quality}_receipt.json"
    log_path = root / "logs" / f"clip_render_{clip_token}_{quality}.log"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for path in (output_tmp,):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    stream_kinds = _probe_media_stream_kinds(config, source)
    include_audio = stream_kinds is None or "audio" in stream_kinds
    command = _clip_render_command(ffmpeg, source, output_tmp, start=start, end=end, include_audio=include_audio)
    known_warnings: list[str] = []
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"clip render unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status != 0 and include_audio and stream_kinds is None:
        known_warnings.append("Audio stream was not confirmed; retried as video-only.")
        include_audio = False
        command = _clip_render_command(ffmpeg, source, output_tmp, start=start, end=end, include_audio=False)
        with log_path.open("ab") as log:
            try:
                status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
            except OSError as exc:
                log.write(f"clip render unavailable on video-only retry: {exc}\n".encode("utf-8"))
                status = 1

    if status == 0 and output_tmp.exists():
        os.replace(output_tmp, output)
    else:
        try:
            if output_tmp.exists():
                output_tmp.unlink()
        except OSError:
            pass

    requested_duration = round(max(0.0, end - start), 6)
    output_duration = probe_media_duration_seconds(config, output) if output.exists() else None
    receipt = {
        "schema": "demo_take_clip_render_receipt_v0",
        "status": "ready" if status == 0 and output.exists() else "failed",
        "take_id": session.get("take_id", root.name),
        "clip_id": clip_id,
        "clip_kind": clip.get("clip_kind"),
        "created_at": now_iso(),
        "quality": quality,
        "source": relative(root, source),
        "output": relative(root, output) if output.exists() else None,
        "receipt_path": relative(root, receipt_path),
        "log": relative(root, log_path),
        "source_range": {
            "start_seconds": round(start, 6),
            "end_seconds": round(end, 6),
            "start_us": int(round(start * 1_000_000)),
            "end_us": int(round(end * 1_000_000)),
        },
        "requested_duration_seconds": requested_duration,
        "output_duration_seconds": output_duration,
        "duration_delta_seconds": (
            round(output_duration - requested_duration, 6)
            if output_duration is not None
            else None
        ),
        "transcript_coverage": _transcript_coverage_for_range(root, start, end),
        "cut_policy": cut_policy,
        "render_method": "trim_setpts_asetpts_reencode",
        "audio_stream_action": "trim_asetpts_aac" if include_audio else "video_only_no_audio_stream",
        "video_stream_action": "trim_setpts_h264",
        "ffmpeg_exit_status": status,
        "known_warnings": known_warnings,
    }
    if receipt["status"] != "ready":
        receipt["known_warnings"].append(f"Clip render failed; see {relative(root, log_path)}.")
    write_json(receipt_path, receipt)
    _write_clip_render_index(root, receipt)
    return {
        "schema": "demo_take_clip_render_result_v0",
        "status": receipt["status"],
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "clipID": clip_id,
        "output": receipt["output"],
        "outputPath": str(output) if output.exists() else None,
        "receipt": receipt["receipt_path"],
        "durationSeconds": output_duration,
        "statusLines": [
            f"Rendered {clip_id} from {start:.2f}s to {end:.2f}s using {cut_policy}."
            if receipt["status"] == "ready"
            else f"Clip render failed for {clip_id}; see {relative(root, log_path)}."
        ],
    }


# ---------------------------------------------------------------------------
# Final render compiler (Type-A-native editor/compiler)
#
# render-clip produces *proxy planning* clips. render-final is the production
# compiler: it consumes an editorial edit plan (ordered clip selection), resolves
# raw-vs-proxy source per quality profile, assembles segments timestamp-safely with
# trim+setpts / atrim+asetpts, and emits a final render receipt that proves
# duration/A-V-drift/transcript-coverage rather than mere file existence.
# ---------------------------------------------------------------------------

FINAL_RENDER_PROFILES: dict[str, dict[str, Any]] = {
    "proxy": {"scale_height": None, "fps": None, "requires_raw": False, "resolution": None},
    "source": {"scale_height": None, "fps": None, "requires_raw": True, "resolution": None},
    "720p30": {"scale_height": 720, "fps": 30, "requires_raw": True, "resolution": "1280x720"},
    "1440p60": {"scale_height": 1440, "fps": 60, "requires_raw": True, "resolution": "2560x1440"},
    "1080p30": {"scale_height": 1080, "fps": 30, "requires_raw": True, "resolution": "1920x1080"},
}
FINAL_CAPTION_FORCE_STYLE = (
    "Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
    "BorderStyle=3,Outline=1,Shadow=0,MarginV=28,Alignment=2"
)

_PRIVATE_CLIP_KINDS = {"private_reject"}
_EXCLUDED_EDITORIAL_USES = {"excluded", "private", "reject"}


def _clip_is_editorial(clip: Mapping[str, Any]) -> bool:
    """A clip belongs in a default edit plan unless it is private/excluded."""
    if str(clip.get("clip_kind") or "") in _PRIVATE_CLIP_KINDS:
        return False
    uses = clip.get("editorial_use") if isinstance(clip.get("editorial_use"), list) else []
    use_tokens = {str(u).strip().lower() for u in uses}
    if not use_tokens:
        return False
    if use_tokens & _EXCLUDED_EDITORIAL_USES:
        return False
    return True


def _sha256_or_none(path: Path) -> str | None:
    try:
        if path.exists() and path.is_file():
            return f"sha256:{sha256_file(path)}"
    except OSError:
        return None
    return None


def _raw_source_for_take(root: Path) -> tuple[Path | None, str]:
    """Resolve the local *raw* (full-res) screen source for a take, if present.

    Returns (path, tier) where tier is one of raw_local / proxy_only / missing.
    Spliced/segment screen tracks are treated as raw; rough_cut is a proxy review.
    """
    spliced = sorted((root / "tracks" / "spliced").glob("screen_*.mp4")) if (root / "tracks" / "spliced").exists() else []
    top = sorted(root.glob("tracks/screen_*.mp4"))
    for candidate in [*spliced, *top]:
        if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate, "raw_local"
    rough = root / "render" / "rough_cut.mp4"
    if rough.exists() and rough.stat().st_size > 0:
        return rough, "proxy_only"
    return None, "missing"


def _materialize_edit_plan(root: Path, session: Mapping[str, Any]) -> dict[str, Any]:
    """Build a default editorial edit plan from candidate_clips.json.

    The plan is authority Type A can hand-edit: ordered items keyed by take id +
    active-time range + source hashes + evidence refs. Excluded/private clips drop out.
    """
    candidate_path = root / "candidate_clips.json"
    payload = _read_json_dict(candidate_path)
    clips = payload.get("clips") if isinstance(payload.get("clips"), list) else []
    take_id = str(session.get("take_id") or root.name)
    items: list[dict[str, Any]] = []
    for clip in clips:
        if not isinstance(clip, Mapping) or not _clip_is_editorial(clip):
            continue
        try:
            start, end, policy = _range_seconds_from_clip(clip)
        except ValueError:
            continue
        items.append({
            "clip_id": str(clip.get("id") or ""),
            "label": str(clip.get("clip_kind") or clip.get("id") or "clip"),
            "source_take_id": take_id,
            "semantic_range_us": [int(round(start * 1_000_000)), int(round(end * 1_000_000))],
            "safe_render_range_us": [int(round(start * 1_000_000)), int(round(end * 1_000_000))],
            "render_source": str(clip.get("media_tier") or "proxy_preview_raw_final"),
            "evidence_refs": clip.get("evidence_refs") if isinstance(clip.get("evidence_refs"), list) else [],
            "cut_policy": policy,
        })
    # Stable ordering: hook -> body -> outro by kind weight, then by start.
    weight = {"hook_candidate": 0, "intro": 0, "body": 1, "outro_candidate": 2, "outro": 2}
    items.sort(key=lambda it: (weight.get(it["label"], 1), it["safe_render_range_us"][0]))
    plan = {
        "schema": "demo_take_edit_plan_v0",
        "take_id": take_id,
        "plan_id": "edit_0001",
        "created_at": now_iso(),
        "origin": "auto_from_candidate_clips",
        "inputs": {
            "candidate_clips": relative(root, candidate_path),
            "candidate_clips_sha256": _sha256_or_none(candidate_path),
        },
        "item_count": len(items),
        "items": items,
    }
    return plan


def _resolve_edit_plan(
    root: Path,
    session: Mapping[str, Any],
    edit_plan_path: Path | None,
) -> tuple[dict[str, Any], Path, bool]:
    """Return (plan, plan_path, materialized?) — load explicit plan or write a default one."""
    if edit_plan_path is not None:
        plan = _read_json_dict(edit_plan_path)
        if not plan.get("items"):
            raise ValueError(f"edit plan has no items: {edit_plan_path}")
        return plan, edit_plan_path, False
    plan = _materialize_edit_plan(root, session)
    plan_path = root / "render" / "edit_plans" / "edit_0001.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(plan_path, plan)
    write_json(
        plan_path.with_name("edit_0001_receipt.json"),
        {
            "schema": "demo_take_edit_plan_receipt_v0",
            "status": "ready" if plan.get("items") else "empty",
            "take_id": plan.get("take_id"),
            "plan": relative(root, plan_path),
            "item_count": plan.get("item_count", 0),
            "created_at": now_iso(),
        },
    )
    return plan, plan_path, True


def _edit_plan_staleness(root: Path, plan: Mapping[str, Any]) -> list[str]:
    """Return human-readable staleness reasons; empty means fresh."""
    reasons: list[str] = []
    inputs = plan.get("inputs") if isinstance(plan.get("inputs"), Mapping) else {}
    recorded = inputs.get("candidate_clips_sha256")
    if recorded:
        live = _sha256_or_none(root / "candidate_clips.json")
        if live is not None and live != recorded:
            reasons.append("candidate_clips.json changed since the edit plan was built")
    return reasons


def _probe_stream_durations(config: Mapping[str, Any], path: Path) -> dict[str, float]:
    ffprobe = _ffprobe_path(dict(config))
    out: dict[str, float] = {}
    if not ffprobe or not path.exists():
        return out
    command = [
        ffprobe, "-hide_banner", "-v", "error",
        "-show_entries", "stream=codec_type,duration",
        "-of", "json", str(path),
    ]
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return out
    if proc.returncode != 0:
        return out
    try:
        payload = json.loads(getattr(proc, "stdout", "") or "{}")
    except json.JSONDecodeError:
        return out
    for stream in payload.get("streams") or []:
        if not isinstance(stream, Mapping):
            continue
        kind = str(stream.get("codec_type") or "")
        dur = stream.get("duration")
        try:
            if kind and dur is not None:
                out[kind] = float(dur)
        except (TypeError, ValueError):
            continue
    return out


def _marker_count_in_ranges(root: Path, ranges: list[tuple[float, float]]) -> int:
    vtt = root / "render" / "markers.vtt"
    if not vtt.exists() or not ranges:
        return 0
    count = 0
    try:
        text = vtt.read_text(encoding="utf-8")
    except OSError:
        return 0
    for match in re.finditer(r"(\d\d):(\d\d):(\d\d)[.,](\d{1,3})\s*-->", text):
        h, m, s, ms = (int(match.group(i)) for i in range(1, 5))
        t = h * 3600 + m * 60 + s + ms / 1000.0
        if any(start <= t <= end for start, end in ranges):
            count += 1
    return count


def _plan_overlap_stats(resolved: list[dict[str, Any]]) -> tuple[int, float]:
    """Count overlapping same-source ranges and total duplicated seconds.

    An auto-materialized plan can select multiple candidate clips that cover the
    same footage (e.g. a hook and an outro candidate both spanning the whole take).
    Gluing those is a duplicate dump, not an edit — this surfaces it so the receipt
    can refuse to call the result a production final.
    """
    overlap_count = 0
    duplicate_seconds = 0.0
    for i in range(len(resolved)):
        for j in range(i + 1, len(resolved)):
            a, b = resolved[i], resolved[j]
            if str(a["source"]) != str(b["source"]):
                continue
            lo = max(a["start"], b["start"])
            hi = min(a["end"], b["end"])
            if hi > lo:
                overlap_count += 1
                duplicate_seconds += hi - lo
    return overlap_count, round(duplicate_seconds, 6)


def _final_segment_filter(
    video_start: float,
    video_end: float,
    *,
    include_audio: bool,
    audio_input_index: int,
    audio_start: float | None = None,
    audio_end: float | None = None,
    scale_height: int | None,
    fps: int | None,
) -> str:
    vchain = f"trim=start={video_start:.6f}:end={video_end:.6f},setpts=PTS-STARTPTS"
    if scale_height:
        vchain += f",scale=-2:{scale_height}:flags=lanczos"
    if fps:
        vchain += f",fps={fps}"
    vchain += ",format=yuv420p"
    parts = [f"[0:v:0]{vchain}[v]"]
    if include_audio:
        audio_start = video_start if audio_start is None else audio_start
        audio_end = video_end if audio_end is None else audio_end
        parts.append(
            f"[{audio_input_index}:a:0]atrim=start={audio_start:.6f}:end={audio_end:.6f},"
            "asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo[a]"
        )
    return ";".join(parts)


def _raw_audio_source_for_take(root: Path, session: Mapping[str, Any]) -> tuple[Path | None, str]:
    """Resolve a separately captured raw audio track for a take, if present."""
    tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
    role_candidates = {"microphone", "audio", "external_audio"}
    for track in tracks:
        if not isinstance(track, Mapping):
            continue
        role = str(track.get("role") or "").strip().lower()
        if role not in role_candidates:
            continue
        rel = track.get("relative_path")
        if not isinstance(rel, str) or not rel:
            continue
        candidate = root / rel
        if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate, "raw_local"
    for pattern in ("tracks/microphone*.wav", "tracks/audio*.wav", "tracks/*.m4a"):
        for candidate in sorted(root.glob(pattern)):
            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
                return candidate, "raw_local"
    return None, "missing"


def _segment_audio_available(config: Mapping[str, Any], segment: Mapping[str, Any]) -> bool:
    audio_source = segment.get("audio_source") or segment.get("source")
    if not isinstance(audio_source, Path):
        return False
    return (_probe_media_stream_kinds(config, audio_source) or {"audio"}) >= {"audio"}


def _final_caption_cues(root: Path, resolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transcript = _read_json_dict(root / "transcript" / "transcript.json")
    segments = transcript.get("segments") if isinstance(transcript.get("segments"), list) else []
    cues: list[dict[str, Any]] = []
    output_offset = 0.0
    for item in resolved:
        item_start = float(item["start"])
        item_end = float(item["end"])
        for segment in segments:
            if not isinstance(segment, Mapping):
                continue
            seg_start = _timeline_seconds(segment.get("start"))
            seg_end = _timeline_seconds(segment.get("end"))
            if seg_start is None or seg_end is None:
                continue
            overlap_start = max(item_start, seg_start)
            overlap_end = min(item_end, seg_end)
            if overlap_end - overlap_start <= 0.05:
                continue
            text = _clean_transcript_text(segment.get("text", ""))
            if not text:
                continue
            cues.append({
                "start": round(output_offset + overlap_start - item_start, 6),
                "end": round(output_offset + overlap_end - item_start, 6),
                "text": text,
            })
        output_offset += max(0.0, item_end - item_start)
    return cues


def _render_final_captions(
    *,
    root: Path,
    ffmpeg: str,
    final_dir: Path,
    output: Path,
    quality: str,
    resolved: list[dict[str, Any]],
    log_path: Path,
    caption_style: str | None,
) -> dict[str, Any]:
    cues = _final_caption_cues(root, resolved)
    srt_path = final_dir / "captions.burn.srt"
    _write_srt_from_segments(srt_path, cues)
    captioned_path = final_dir / f"final_{quality}.captioned.mp4"
    style = caption_style or FINAL_CAPTION_FORCE_STYLE
    if not cues:
        return {
            "schema": "demo_take_final_caption_render_v0",
            "status": "blocked",
            "blocker": "no_caption_cues",
            "burned": False,
            "cue_count": 0,
            "srt": relative(root, srt_path),
            "captioned_output": None,
            "force_style": style,
        }
    with log_path.open("ab") as log:
        log.write(f"final caption burn: {len(cues)} cues\n".encode("utf-8"))
        try:
            proc = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-y",
                    "-i",
                    str(output.resolve()),
                    "-vf",
                    f"subtitles={srt_path.name}:force_style='{style}'",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-c:a",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(captioned_path.resolve()),
                ],
                stdout=log,
                stderr=log,
                cwd=str(final_dir),
                check=False,
            )
            status = proc.returncode
        except OSError as exc:
            log.write(f"final caption burn unavailable: {exc}\n".encode("utf-8"))
            status = 1
    burn_ok = status == 0 and captioned_path.exists() and captioned_path.stat().st_size > 0
    return {
        "schema": "demo_take_final_caption_render_v0",
        "status": "ready" if burn_ok else "failed",
        "burned": burn_ok,
        "cue_count": len(cues),
        "srt": relative(root, srt_path),
        "captioned_output": relative(root, captioned_path) if burn_ok else None,
        "bytes": captioned_path.stat().st_size if burn_ok else None,
        "force_style": style,
        "source_output": relative(root, output),
        "render_method": "ffmpeg_subtitles_filter_reencode_video_copy_audio",
    }


def render_final_cut(
    root: Path,
    *,
    edit_plan_path: Path | None = None,
    quality: str = "720p30",
    hydrate_policy: str = "if_needed",
    allow_stale: bool = False,
    allow_proxy_fallback: bool = False,
    burn_captions: bool = False,
    caption_style: str | None = None,
) -> dict[str, Any]:
    """Compile a final video from an editorial edit plan. Returns a result dict.

    Source policy:
      - proxy profile renders from proxy planning assets (a preview, not a master).
      - source/720p30/1440p60/1080p30 REQUIRE local raw (or hydrated raw). When raw is
        absent the render is BLOCKED with a typed blocker unless --allow-proxy-fallback
        explicitly authorises an honestly-labelled proxy_degraded master.
    """
    profile = FINAL_RENDER_PROFILES.get(quality)
    if profile is None:
        raise ValueError(f"unknown render profile: {quality!r} (choices: {sorted(FINAL_RENDER_PROFILES)})")
    if hydrate_policy not in {"required", "if_needed", "never"}:
        raise ValueError(f"unknown hydrate policy: {hydrate_policy!r}")

    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    ffmpeg = str(config.get("ffmpeg_path") or shutil.which("ffmpeg") or "").strip()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg executable not found for final render")
    take_id = str(session.get("take_id") or root.name)
    takes_root = root.parent

    final_dir = root / "render" / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = final_dir / "final_render_receipt.json"
    digest_path = final_dir / "final_digest.md"
    log_path = root / "logs" / f"final_render_{quality}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _blocked(blocker: str, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        source_requirement_lease = _transition_source_requirement_lease(
            root,
            status="blocked",
            operation_receipt=relative(root, receipt_path),
            blockers=[blocker],
        )
        receipt = {
            "schema": "demo_take_final_render_receipt_v0",
            "status": "blocked",
            "blocker": blocker,
            "take_id": take_id,
            "render_profile": quality,
            "created_at": now_iso(),
            "warnings": [message],
        }
        if source_requirement_lease:
            receipt["source_requirement_lease"] = source_requirement_lease
        if extra:
            receipt.update(extra)
        write_json(receipt_path, receipt)
        if source_requirement_lease:
            write_local_storage_receipt(root, config, session)
        return {
            "schema": "demo_take_final_render_result_v0",
            "status": "blocked",
            "blocker": blocker,
            "takeID": take_id,
            "rootPath": str(root),
            "receipt": relative(root, receipt_path),
            "statusLines": [message],
        }

    plan, plan_path, materialized = _resolve_edit_plan(root, session, edit_plan_path)
    items = plan.get("items") if isinstance(plan.get("items"), list) else []
    if not items:
        return _blocked("empty_edit_plan", "Edit plan selected no clips to render.")

    stale_reasons = _edit_plan_staleness(root, plan)
    if stale_reasons and not allow_stale:
        return _blocked(
            "stale_edit_plan",
            "; ".join(stale_reasons) + " — re-materialize the plan or pass --allow-stale.",
            {"stale_reasons": stale_reasons, "edit_plan": relative(root, plan_path)},
        )

    # Resolve every segment's source + range first; decide a uniform audio policy.
    resolved: list[dict[str, Any]] = []
    source_modes: set[str] = set()
    cloud_hydration = "not_needed"
    for item in items:
        if not isinstance(item, Mapping):
            continue
        clip_id = str(item.get("clip_id") or "")
        item_take_id = str(item.get("source_take_id") or take_id)
        item_root = root if item_take_id == take_id else (takes_root / item_take_id)
        item_session = session if item_root == root else _read_json_dict(item_root / "session.json")
        safe = item.get("safe_render_range_us") if isinstance(item.get("safe_render_range_us"), list) else None
        if safe and len(safe) == 2:
            start, end = float(safe[0]) / 1_000_000, float(safe[1]) / 1_000_000
        else:
            try:
                clip = _load_candidate_clip(item_root, clip_id)
                start, end, _ = _range_seconds_from_clip(clip)
            except (ValueError, FileNotFoundError) as exc:
                return _blocked("unresolvable_clip", f"Cannot resolve range for {clip_id}: {exc}")
        if end <= start:
            return _blocked("invalid_range", f"Clip {clip_id} has a non-positive render range.")

        audio_source: Path | None = None
        audio_source_mode = "embedded_or_none"
        if profile["requires_raw"]:
            raw, tier = _raw_source_for_take(item_root)
            if tier == "raw_local" and raw is not None:
                source, source_mode = raw, "raw_local"
                stream_kinds = _probe_media_stream_kinds(config, source)
                if stream_kinds is not None and "audio" not in stream_kinds:
                    raw_audio, audio_tier = _raw_audio_source_for_take(item_root, item_session)
                    if audio_tier == "raw_local" and raw_audio is not None:
                        audio_source = raw_audio
                        audio_source_mode = "separate_raw_local"
                    else:
                        audio_source_mode = "none"
                elif stream_kinds and "audio" in stream_kinds:
                    audio_source_mode = "embedded"
            else:
                if hydrate_policy == "required":
                    return _blocked(
                        "raw_unavailable",
                        f"Profile {quality} requires raw for {clip_id} but local raw is "
                        f"{tier}; cloud hydration is not configured.",
                        {"cloud_hydration": "unavailable", "edit_plan": relative(root, plan_path)},
                    )
                if not allow_proxy_fallback:
                    return _blocked(
                        "raw_unavailable",
                        f"Profile {quality} needs raw for {clip_id} (local raw {tier}). "
                        "Pass --allow-proxy-fallback to render an honestly-labelled proxy_degraded master, "
                        "or hydrate raw first.",
                        {"cloud_hydration": "unavailable", "edit_plan": relative(root, plan_path)},
                    )
                source = _resolve_proxy_source(item_root, item_session, clip_id)
                if source is None:
                    return _blocked("no_source", f"No raw or proxy source for {clip_id}.")
                source_mode = "proxy_degraded"
                audio_source_mode = "embedded_or_none"
                cloud_hydration = "unavailable"
        else:
            source = _resolve_proxy_source(item_root, item_session, clip_id)
            if source is None:
                return _blocked("no_source", f"No proxy source for {clip_id}.")
            source_mode = "proxy"
            audio_source_mode = "embedded_or_none"
        source_modes.add(source_mode)
        video_offset_seconds = _media_timeline_offset_seconds(item_root, item_session, source)
        if audio_source is not None:
            audio_offset_seconds = _media_timeline_offset_seconds(item_root, item_session, audio_source)
        elif audio_source_mode == "embedded":
            audio_offset_seconds = video_offset_seconds
        else:
            audio_offset_seconds = 0.0
        resolved.append({
            "clip_id": clip_id,
            "source": source,
            "source_sha256": _sha256_or_none(source),
            "audio_source": audio_source,
            "audio_source_sha256": _sha256_or_none(audio_source) if audio_source is not None else None,
            "start": start,
            "end": end,
            "source_mode": source_mode,
            "audio_source_mode": audio_source_mode,
            "video_offset_seconds": video_offset_seconds,
            "audio_offset_seconds": audio_offset_seconds,
        })

    # Uniform audio policy so concat -c copy is valid across heterogeneous sources.
    include_audio = all(_segment_audio_available(config, seg) for seg in resolved)
    required_source_classes = {
        "screen_raw_media" if profile["requires_raw"] else "screen_review_proxy",
    }
    for seg in resolved:
        if seg.get("audio_source_mode") == "separate_raw_local":
            required_source_classes.add("microphone_raw_media")
        elif include_audio:
            required_source_classes.add("embedded_audio_stream")
    required_source_paths = sorted({
        relative(root, seg["source"])
        for seg in resolved
        if isinstance(seg.get("source"), Path)
    } | {
        relative(root, seg["audio_source"])
        for seg in resolved
        if isinstance(seg.get("audio_source"), Path)
    })
    source_requirement_lease = _source_requirement_lease_payload(
        root=root,
        take_id=take_id,
        operation="render-final",
        status="active",
        required_source_classes=sorted(required_source_classes),
        required_source_paths=required_source_paths,
        source_mode="pending",
        hydrate_policy=hydrate_policy,
        release_condition="final_render_receipt_written_or_blocked",
        satisfaction={"status": "pending"},
        blockers=[],
    )
    write_local_storage_receipt(root, config, session)
    warnings: list[str] = []

    # Render each segment to a uniform-profile temp, then concat-copy.
    segments_dir = final_dir / "_segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    for stale_seg in segments_dir.glob("seg_*.mp4"):
        try:
            stale_seg.unlink()
        except OSError:
            pass
    concat_list = segments_dir / "concat.txt"
    seg_paths: list[Path] = []
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        for index, seg in enumerate(resolved):
            seg_out = segments_dir / f"seg_{index:04d}.mp4"
            video_offset = float(seg.get("video_offset_seconds") or 0.0)
            audio_offset = float(seg.get("audio_offset_seconds") or 0.0)
            filter_complex = _final_segment_filter(
                _offset_start_seconds(seg["start"], video_offset),
                _offset_start_seconds(seg["end"], video_offset),
                include_audio=include_audio,
                audio_input_index=1 if seg.get("audio_source") is not None else 0,
                audio_start=_offset_start_seconds(seg["start"], audio_offset),
                audio_end=_offset_start_seconds(seg["end"], audio_offset),
                scale_height=profile["scale_height"],
                fps=profile["fps"],
            )
            command = [ffmpeg, "-hide_banner", "-y", "-i", str(seg["source"])]
            if include_audio and seg.get("audio_source") is not None:
                command += ["-i", str(seg["audio_source"])]
            command += ["-filter_complex", filter_complex, "-map", "[v]"]
            if include_audio:
                command += ["-map", "[a]", "-c:a", "aac", "-ar", "48000"]
            else:
                command += ["-an"]
            command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
            if profile["fps"]:
                command += ["-r", str(profile["fps"])]
            command += ["-movflags", "+faststart", str(seg_out)]
            try:
                status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
            except OSError as exc:
                log.write(f"final segment render unavailable: {exc}\n".encode("utf-8"))
                status = 1
            if status != 0 or not seg_out.exists() or seg_out.stat().st_size == 0:
                return _blocked("segment_render_failed", f"Segment {index} ({seg['clip_id']}) failed; see {relative(root, log_path)}.")
            seg_paths.append(seg_out)

        concat_list.write_text(
            "".join(f"file '{p.resolve()}'\n" for p in seg_paths),
            encoding="utf-8",
        )
        profile_token = quality
        output = final_dir / f"final_{profile_token}.mp4"
        output_tmp = final_dir / f".final_{profile_token}.tmp.mp4"
        if len(seg_paths) == 1:
            concat_command = [ffmpeg, "-hide_banner", "-y", "-i", str(seg_paths[0]), "-c", "copy", "-movflags", "+faststart", str(output_tmp)]
        else:
            concat_command = [ffmpeg, "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", "-movflags", "+faststart", str(output_tmp)]
        try:
            status = subprocess.run(concat_command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"final concat unavailable: {exc}\n".encode("utf-8"))
            status = 1

    if status != 0 or not output_tmp.exists() or output_tmp.stat().st_size == 0:
        try:
            if output_tmp.exists():
                output_tmp.unlink()
        except OSError:
            pass
        return _blocked("concat_failed", f"Final concat failed; see {relative(root, log_path)}.")
    os.replace(output_tmp, output)

    requested_duration = round(sum(seg["end"] - seg["start"] for seg in resolved), 6)
    stream_durations = _probe_stream_durations(config, output)
    output_duration = probe_media_duration_seconds(config, output)
    audio_duration = stream_durations.get("audio")
    video_duration = stream_durations.get("video", output_duration)
    av_drift = (
        round(abs(video_duration - audio_duration), 6)
        if (video_duration is not None and audio_duration is not None)
        else None
    )
    ranges = [(seg["start"], seg["end"]) for seg in resolved]
    coverage_num = sum(
        (_transcript_coverage_for_range(root, seg["start"], seg["end"]) or 0.0) * (seg["end"] - seg["start"])
        for seg in resolved
    )
    coverage_den = sum(seg["end"] - seg["start"] for seg in resolved)
    transcript_coverage_ratio = round(coverage_num / coverage_den, 6) if coverage_den > 0 else None
    marker_count = _marker_count_in_ranges(root, ranges)
    video_source_hashes_verified = all(seg["source_sha256"] is not None for seg in resolved)
    audio_source_hashes_verified = all(
        seg.get("audio_source") is None or seg.get("audio_source_sha256") is not None
        for seg in resolved
    )
    source_hashes_verified = video_source_hashes_verified and audio_source_hashes_verified
    separate_audio_source_count = sum(1 for seg in resolved if seg.get("audio_source") is not None)
    if not include_audio:
        source_audio_mode = "none"
    elif separate_audio_source_count == 0:
        source_audio_mode = "embedded"
    elif separate_audio_source_count == len(resolved):
        source_audio_mode = "separate_raw_local"
    else:
        source_audio_mode = "mixed"
    source_segments = [
        {
            "clip_id": seg["clip_id"],
            "source": relative(root, seg["source"]),
            "source_sha256": seg.get("source_sha256"),
            "audio_source": relative(root, seg["audio_source"]) if isinstance(seg.get("audio_source"), Path) else None,
            "audio_source_sha256": seg.get("audio_source_sha256"),
            "start_seconds": round(seg["start"], 6),
            "end_seconds": round(seg["end"], 6),
            "video_timeline_offset_seconds": round(float(seg.get("video_offset_seconds") or 0.0), 6),
            "audio_timeline_offset_seconds": round(float(seg.get("audio_offset_seconds") or 0.0), 6),
            "source_mode": seg.get("source_mode"),
            "audio_source_mode": seg.get("audio_source_mode"),
        }
        for seg in resolved
    ]
    captioned_render: dict[str, Any] = {"burned": False}
    if burn_captions:
        captioned_render = _render_final_captions(
            root=root,
            ffmpeg=ffmpeg,
            final_dir=final_dir,
            output=output,
            quality=quality,
            resolved=resolved,
            log_path=log_path,
            caption_style=caption_style,
        )
        if captioned_render.get("status") != "ready":
            warnings.append(f"Caption burn did not produce a ready output (status={captioned_render.get('status')}).")

    resolved_mode = (
        "proxy" if source_modes == {"proxy"}
        else "raw_local" if source_modes == {"raw_local"}
        else "proxy_degraded" if "proxy_degraded" in source_modes
        else "mixed"
    )
    duration_delta = round((output_duration or 0.0) - requested_duration, 6) if output_duration is not None else None
    duration_ok = duration_delta is not None and abs(duration_delta) <= max(0.5, 0.2 * requested_duration)
    av_ok = av_drift is None or av_drift <= 0.25
    if not duration_ok and output_duration is not None:
        warnings.append(f"Output duration {output_duration:.3f}s differs from requested {requested_duration:.3f}s by {duration_delta:.3f}s.")
    if not av_ok:
        warnings.append(f"A/V drift {av_drift:.3f}s exceeds 0.25s tolerance.")
    if not include_audio:
        warnings.append("No audio source was available for every final segment; output is video-only.")
    if resolved_mode in {"proxy_degraded", "proxy"} and profile["requires_raw"]:
        warnings.append("Master rendered from PROXY assets — not a raw-sourced final. Hydrate raw for a true master.")
    if stale_reasons:
        warnings.append("Rendered from a STALE edit plan (--allow-stale).")

    # ---- Production-final classification: an auto candidate dump is never a final ----
    overlap_count, duplicate_source_seconds = _plan_overlap_stats(resolved)
    plan_status = "explicit" if not materialized else "auto_draft"
    if plan_status == "explicit":
        selection_policy = "explicit_order"
    elif overlap_count == 0:
        selection_policy = "candidate_ranked_nonoverlap"
    else:
        selection_policy = "auto_overlapping_candidate_dump"
    raw_ok = not (profile["requires_raw"] and resolved_mode in {"proxy", "proxy_degraded"})
    production_ready = bool(
        plan_status == "explicit"
        and quality != "proxy"
        and overlap_count == 0
        and duplicate_source_seconds == 0.0
        and not stale_reasons
        and duration_ok
        and av_ok
        and include_audio
        and raw_ok
        and source_hashes_verified
    )
    requires_review = not production_ready
    if overlap_count:
        warnings.append(
            f"{overlap_count} overlapping same-source range(s) duplicating {duplicate_source_seconds:.3f}s — "
            "auto draft, not a production final."
        )
    if plan_status == "auto_draft":
        warnings.append(
            "Auto-materialized DRAFT plan from candidate_clips; supply an explicit edit plan for a production final."
        )
    if quality == "proxy":
        warnings.append("Proxy render is a planning/review artifact, never a production master.")

    lease_satisfaction = {
        "status": (
            "satisfied"
            if source_hashes_verified and (not profile["requires_raw"] or resolved_mode == "raw_local") and include_audio
            else "degraded"
        ),
        "source_hashes_verified": source_hashes_verified,
        "video_source_hashes_verified": video_source_hashes_verified,
        "audio_source_hashes_verified": audio_source_hashes_verified,
        "source_mode": resolved_mode,
        "source_audio_mode": source_audio_mode,
        "has_audio": include_audio,
        "cloud_hydration": cloud_hydration,
    }
    source_requirement_lease = _source_requirement_lease_payload(
        root=root,
        take_id=take_id,
        operation="render-final",
        status="released",
        required_source_classes=sorted(required_source_classes),
        required_source_paths=required_source_paths,
        source_mode=resolved_mode,
        hydrate_policy=hydrate_policy,
        release_condition="final_render_receipt_written",
        operation_receipt=relative(root, receipt_path),
        satisfaction=lease_satisfaction,
        blockers=[],
    )

    receipt = {
        "schema": "demo_take_final_render_receipt_v0",
        "status": "ready",
        "take_id": take_id,
        "render_profile": quality,
        "created_at": now_iso(),
        "source_mode": resolved_mode,
        "edit_plan": relative(root, plan_path),
        "edit_plan_sha256": _sha256_or_none(plan_path),
        "edit_plan_materialized": materialized,
        "plan_status": plan_status,
        "selection_policy": selection_policy,
        "production_ready": production_ready,
        "requires_review": requires_review,
        "source_range_count": len(resolved),
        "source_segments": source_segments,
        "overlap_count": overlap_count,
        "duplicate_source_seconds": duplicate_source_seconds,
        "expected_timeline_duration_seconds": requested_duration,
        "segment_count": len(resolved),
        "output": relative(root, output),
        "output_path": str(output),
        "bytes": output.stat().st_size if output.exists() else None,
        "resolution": profile["resolution"],
        "fps": profile["fps"],
        "requested_duration_seconds": requested_duration,
        "output_duration_seconds": round(output_duration, 6) if output_duration is not None else None,
        "audio_duration_seconds": round(audio_duration, 6) if audio_duration is not None else None,
        "av_drift_seconds": av_drift,
        "duration_delta_seconds": duration_delta,
        "transcript_coverage_ratio": transcript_coverage_ratio,
        "marker_count": marker_count,
        "video_source_hashes_verified": video_source_hashes_verified,
        "audio_source_hashes_verified": audio_source_hashes_verified,
        "source_hashes_verified": source_hashes_verified,
        "source_audio_mode": source_audio_mode,
        "separate_audio_source_count": separate_audio_source_count,
        "cloud_hydration": cloud_hydration,
        "source_requirement_lease": source_requirement_lease,
        "render_method": "trim_setpts_asetpts_segment_then_concat_copy",
        "has_audio": include_audio,
        "captioned_render": captioned_render,
        "log": relative(root, log_path),
        "warnings": warnings,
    }
    write_json(receipt_path, receipt)
    write_local_storage_receipt(root, config, session)
    _write_final_digest(digest_path, receipt)
    # Clean transient segment scratch; keep concat list for forensics-free footprint.
    for seg in seg_paths:
        try:
            seg.unlink()
        except OSError:
            pass
    try:
        concat_list.unlink()
        segments_dir.rmdir()
    except OSError:
        pass

    return {
        "schema": "demo_take_final_render_result_v0",
        "status": "ready",
        "takeID": take_id,
        "rootPath": str(root),
        "renderProfile": quality,
        "sourceMode": resolved_mode,
        "planStatus": plan_status,
        "productionReady": production_ready,
        "requiresReview": requires_review,
        "overlapCount": overlap_count,
        "output": receipt["output"],
        "outputPath": str(output),
        "receipt": relative(root, receipt_path),
        "durationSeconds": receipt["output_duration_seconds"],
        "avDriftSeconds": av_drift,
        "warnings": warnings,
        "statusLines": [
            f"Rendered {quality} {'DRAFT' if requires_review else 'production'} cut ({resolved_mode}, "
            f"{plan_status}) from {len(resolved)} clip(s): {receipt['output_duration_seconds']}s, "
            f"A/V drift {av_drift}s, overlap {overlap_count}."
        ] + (
            [f"Captioned render: {captioned_render.get('captioned_output')}"]
            if captioned_render.get("status") == "ready"
            else []
        ),
    }


def _write_final_digest(path: Path, receipt: Mapping[str, Any]) -> None:
    lines = [
        f"# Final render — {receipt.get('take_id')}",
        "",
        f"- Status: **{receipt.get('status')}**",
        f"- Production ready: **{receipt.get('production_ready')}** "
        f"(plan `{receipt.get('plan_status')}`, policy `{receipt.get('selection_policy')}`)",
        f"- Profile: `{receipt.get('render_profile')}` ({receipt.get('resolution') or 'source resolution'})",
        f"- Source mode: `{receipt.get('source_mode')}`",
        f"- Segments: {receipt.get('segment_count')} "
        f"(overlaps {receipt.get('overlap_count')}, duplicated {receipt.get('duplicate_source_seconds')}s)",
        f"- Output: `{receipt.get('output')}` ({receipt.get('bytes')} bytes)",
        f"- Duration: {receipt.get('output_duration_seconds')}s "
        f"(requested {receipt.get('requested_duration_seconds')}s)",
        f"- A/V drift: {receipt.get('av_drift_seconds')}s",
        f"- Transcript coverage: {receipt.get('transcript_coverage_ratio')}",
        f"- Markers in cut: {receipt.get('marker_count')}",
        f"- Source hashes verified: {receipt.get('source_hashes_verified')}",
        f"- Audio source mode: `{receipt.get('source_audio_mode')}` "
        f"(separate sources {receipt.get('separate_audio_source_count')})",
        f"- Cloud hydration: {receipt.get('cloud_hydration')}",
        f"- Source requirement lease: "
        f"{(receipt.get('source_requirement_lease') or {}).get('status') if isinstance(receipt.get('source_requirement_lease'), Mapping) else None}",
        f"- Render method: `{receipt.get('render_method')}`",
    ]
    captioned = receipt.get("captioned_render") if isinstance(receipt.get("captioned_render"), Mapping) else {}
    if captioned.get("burned"):
        lines.append(f"- Captioned output: `{captioned.get('captioned_output')}` ({captioned.get('cue_count')} cues)")
    warnings = receipt.get("warnings") if isinstance(receipt.get("warnings"), list) else []
    if warnings:
        lines += ["", "## Warnings", *[f"- {w}" for w in warnings]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Staleness audit — projections must not silently drift from their inputs.
#
# Critical edges use recorded sha256 (authoritative): an edit plan records
# candidate_clips_sha256; a final render points at its edit plan. Advisory edges
# use mtime ordering (a derived file older than its input is suspect). doctor-production
# blocks a production final only on a CRITICAL stale edge, never on advisory mtime alone.
# ---------------------------------------------------------------------------

_ADVISORY_STALENESS_EDGES: list[tuple[str, list[str], bool, str]] = [
    ("phrase_cards.jsonl", ["transcript/transcript.json"], False, "mtime"),
    ("observation_atlas.json", ["transcript/transcript.json", "visual_change_index.jsonl"], False, "mtime"),
    ("candidate_clips.json", ["active_timeline.json"], False, "mtime"),
    ("render/clips/index.json", ["candidate_clips.json"], False, "mtime"),
]


def _edit_plan_declared_inputs(root: Path, plan_rel: str) -> list[str]:
    plan = _read_json_dict(root / plan_rel)
    inputs = plan.get("inputs") if isinstance(plan.get("inputs"), Mapping) else {}
    rels: list[str] = []
    for key, value in inputs.items():
        if key.endswith("_sha256"):
            continue
        if isinstance(value, str) and value and not value.startswith("sha256:"):
            rels.append(value)
    if not rels and inputs.get("candidate_clips_sha256"):
        rels.append("candidate_clips.json")
    return rels


def _active_final_edit_plan_rel(root: Path) -> str:
    receipt = _read_json_dict(root / "render" / "final" / "final_render_receipt.json")
    plan_rel = receipt.get("edit_plan")
    if isinstance(plan_rel, str) and plan_rel:
        return plan_rel
    return "render/edit_plans/edit_0001.json"


def _staleness_edges(root: Path) -> list[tuple[str, list[str], bool, str]]:
    plan_rel = _active_final_edit_plan_rel(root)
    plan_inputs = _edit_plan_declared_inputs(root, plan_rel) if (root / plan_rel).exists() else ["candidate_clips.json"]
    return [
        (plan_rel, plan_inputs, True, "recorded_sha256"),
        ("render/final/final_render_receipt.json", [plan_rel], True, "recorded_sha256"),
        *_ADVISORY_STALENESS_EDGES,
    ]


def audit_take_staleness(root: Path) -> dict[str, Any]:
    """Classify each derived projection fresh / stale / unverifiable / missing.

    Returns a receipt (also written to render/staleness_receipt.json). overall_status
    is `stale` if any CRITICAL edge is stale (hash mismatch), else `fresh`. Advisory
    mtime staleness is reported but does not flip overall_status.
    """
    checks: list[dict[str, Any]] = []
    critical_stale = False
    advisory_stale = 0
    for derived_rel, input_rels, critical, signal in _staleness_edges(root):
        derived = root / derived_rel
        if not derived.exists():
            checks.append({
                "derived": derived_rel, "inputs": input_rels, "critical": critical,
                "signal": "presence", "status": "missing",
            })
            continue
        present_inputs = [r for r in input_rels if (root / r).exists()]
        status = "fresh"
        detail: dict[str, Any] = {}
        if signal == "recorded_sha256" and derived_rel.startswith("render/edit_plans/"):
            reasons = _edit_plan_staleness(root, _read_json_dict(derived))
            status = "stale" if reasons else "fresh"
            detail["reasons"] = reasons
        elif signal == "recorded_sha256":  # final render receipt
            receipt = _read_json_dict(derived)
            plan_rel = receipt.get("edit_plan")
            sub_stale_reasons: list[str] = []
            if isinstance(plan_rel, str) and (root / plan_rel).exists():
                live_plan_sha = _sha256_or_none(root / plan_rel)
                recorded_plan_sha = receipt.get("edit_plan_sha256")
                if recorded_plan_sha and live_plan_sha and recorded_plan_sha != live_plan_sha:
                    sub_stale_reasons.append("edit plan changed since final render")
                sub_stale_reasons.extend(_edit_plan_staleness(root, _read_json_dict(root / plan_rel)))
            else:
                sub_stale_reasons.append("edit plan missing")
            if sub_stale_reasons:
                status = "stale"
                detail["reasons"] = sub_stale_reasons
        else:  # mtime advisory
            if not present_inputs and input_rels:
                status = "unverifiable"
            else:
                dmt = derived.stat().st_mtime
                newer = [r for r in present_inputs if (root / r).stat().st_mtime > dmt + 1]
                if newer:
                    status = "stale"
                    detail["modified_inputs"] = newer
        if status == "stale":
            if critical:
                critical_stale = True
            else:
                advisory_stale += 1
        checks.append({
            "derived": derived_rel, "inputs": input_rels, "critical": critical,
            "signal": signal, "status": status, **({"detail": detail} if detail else {}),
        })
    overall = "stale" if critical_stale else "fresh"
    receipt = {
        "schema": "demo_take_staleness_receipt_v0",
        "status": overall,
        "take_id": root.name,
        "created_at": now_iso(),
        "critical_stale": critical_stale,
        "advisory_stale_count": advisory_stale,
        "checks": checks,
    }
    write_json(root / "render" / "staleness_receipt.json", receipt)
    return receipt


def _unique_export_path(destination_dir: Path, stem: str, suffix: str, source: Path) -> Path:
    safe_stem = take_title_slug(stem) or "demo-take"
    for index in range(100):
        suffix_text = "" if index == 0 else f"-{index + 1:02d}"
        candidate = destination_dir / f"{safe_stem}{suffix_text}{suffix}"
        if not candidate.exists() or files_are_same(candidate, source):
            return candidate
    raise RuntimeError(f"could not allocate export path for {safe_stem}{suffix}")


def _export_media_probe(config: Mapping[str, Any], path: Path) -> dict[str, Any]:
    stat = path.stat() if path.exists() else None
    stream_kinds = _probe_media_stream_kinds(config, path)
    duration = probe_media_duration_seconds(dict(config), path)
    ffprobe_status = "pass" if stream_kinds else "unavailable_or_failed"
    return {
        "schema": "demo_take_export_media_probe_v0",
        "status": "pass" if stat and stat.st_size > 0 and stream_kinds else ("warn" if stat and stat.st_size > 0 else "fail"),
        "container_suffix": path.suffix.lower(),
        "bytes": stat.st_size if stat else None,
        "sha256": f"sha256:{sha256_file(path)}" if stat else None,
        "ffprobe_status": ffprobe_status,
        "stream_kinds": sorted(stream_kinds or []),
        "duration_seconds": round(duration, 6) if duration is not None else None,
    }


def _export_transport_probe(repo_root: Path, output: Path) -> dict[str, Any]:
    export_root = (repo_root / EXPORTS_RELATIVE_ROOT).resolve()
    resolved = output.resolve()
    try:
        export_relative = resolved.relative_to(export_root)
    except ValueError:
        export_relative = None
    allowed_suffix = output.suffix.lower() in EXTERNAL_VIDEO_EXTENSIONS
    single_file = export_relative is not None and len(export_relative.parts) == 1
    asset_path = export_relative.as_posix() if export_relative and single_file and allowed_suffix else None
    return {
        "schema": "demo_take_export_transport_probe_v0",
        "status": "pass" if output.exists() and output.is_file() and asset_path else "fail",
        "export_root": relative(repo_root, export_root),
        "relative_path": relative(repo_root, output),
        "asset_path": asset_path,
        "asset_url": f"/api/demo-takes/exports/asset/{asset_path}" if asset_path else None,
        "allowed_suffix": allowed_suffix,
        "direct_child_of_exports_root": bool(single_file),
        "absolute_host_path_exposed": False,
        "range_request_header_contract": "Accept-Ranges: bytes",
    }


def _export_custody_refs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    storage_receipt = _read_json_dict(root / "render" / "storage_receipt.json")
    cloud_archive = storage_receipt.get("cloud_archive") if isinstance(storage_receipt.get("cloud_archive"), Mapping) else {}
    governor = storage_receipt.get("storage_governor") if isinstance(storage_receipt.get("storage_governor"), Mapping) else {}
    restore_drill = governor.get("restore_drill") if isinstance(governor.get("restore_drill"), Mapping) else {}
    source_authority_ref = {
        "schema": "demo_take_export_source_authority_ref_v0",
        "class": "playable_review_asset_not_source_authority",
        "cloud_archive_status": cloud_archive.get("status"),
        "cloud_archive_local_retention": cloud_archive.get("local_retention"),
        "cloud_archive_manifest_sha256": cloud_archive.get("manifest_sha256"),
        "cloud_archive_remote_take_path": cloud_archive.get("remote_take_path"),
        "restore_drill_receipt": RESTORE_DRILL_RECEIPT_RELATIVE_PATH if (root / RESTORE_DRILL_RECEIPT_RELATIVE_PATH).exists() else None,
        "render_receipt": "render/render_receipt.json" if (root / "render" / "render_receipt.json").exists() else None,
    }
    storage_governor_ref = {
        "schema": "demo_take_export_storage_governor_ref_v0",
        "state": governor.get("state"),
        "local_retention_policy": governor.get("local_retention_policy"),
        "restore_drill_status": restore_drill.get("status"),
        "source_hydrate_status": restore_drill.get("source_hydrate_status"),
        "compile_smoke_status": restore_drill.get("compile_smoke_status"),
        "checked_at": restore_drill.get("checked_at"),
    }
    return source_authority_ref, storage_governor_ref


def _export_upload_readiness(
    *,
    media_probe: Mapping[str, Any],
    transport_probe: Mapping[str, Any],
    storage_governor_ref: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if media_probe.get("status") == "fail":
        blockers.append("media_probe_failed")
    elif media_probe.get("status") == "warn":
        warnings.append("media_probe_warn")
    if transport_probe.get("status") != "pass":
        blockers.append("unsafe_or_missing_export_transport")
    if storage_governor_ref.get("state") not in {"cloud_verified_proxy_local", "manual_source_retention", None}:
        warnings.append("storage_governor_not_green_at_export_time")
    if storage_governor_ref.get("state") == "cloud_verified_proxy_local" and storage_governor_ref.get("restore_drill_status") != "pass":
        warnings.append("cloud_proxy_export_without_restore_drill_pass")
    status = "blocked" if blockers else ("ready_with_media_probe_warning" if warnings else "ready")
    return {
        "schema": "demo_take_upload_readiness_v0",
        "status": status,
        "artifact_role": "upload_export_candidate",
        "artifact_class": "review_upload_export",
        "upload_side_effects": "none",
        "provider_upload_performed": False,
        "provider_video_id": None,
        "publication_authority": "not_publication_authority",
        "publication_boundary": "no_external_upload_performed_publication_gate_required",
        "blockers": blockers,
        "warnings": warnings,
    }


def _export_mime_probe(path: Path) -> str:
    return {
        ".mp4": "video/mp4",
        ".m4v": "video/x-m4v",
        ".mov": "video/quicktime",
    }.get(path.suffix.lower(), "application/octet-stream")


def _export_handoff_attestation(
    *,
    repo_root: Path,
    output: Path,
    method: str,
    media_probe: Mapping[str, Any],
    transport_probe: Mapping[str, Any],
    source_authority_ref: Mapping[str, Any],
    storage_governor_ref: Mapping[str, Any],
    upload_readiness: Mapping[str, Any],
) -> dict[str, Any]:
    raw_hydratable_for_final = storage_governor_ref.get("source_hydrate_status") == "pass" or storage_governor_ref.get("restore_drill_status") == "pass"
    export_ready = bool(output.exists() and output.is_file() and method in {"hardlink_lossless_export", "copy"})
    media_ready = media_probe.get("status") == "pass"
    transport_ready = transport_probe.get("status") == "pass" and transport_probe.get("absolute_host_path_exposed") is False
    source_authority_refs = {
        "class": source_authority_ref.get("class"),
        "cloud_archive_status": source_authority_ref.get("cloud_archive_status"),
        "cloud_archive_manifest_sha256": source_authority_ref.get("cloud_archive_manifest_sha256"),
        "cloud_archive_remote_take_path": source_authority_ref.get("cloud_archive_remote_take_path"),
        "restore_drill_receipt": source_authority_ref.get("restore_drill_receipt"),
        "render_receipt": source_authority_ref.get("render_receipt"),
    }
    readiness_vector = {
        "export_ready": export_ready,
        "media_ready": media_ready,
        "transport_ready": transport_ready,
        "review_upload_ready": export_ready and media_ready and transport_ready and upload_readiness.get("status") == "ready",
        "provider_staging_ready": False,
        "publication_ready": False,
    }
    provider_boundary = {
        "external_upload_performed": False,
        "provider_video_id": None,
        "oauth_material_present": False,
        "publication_authority": "none",
    }
    subject = {
        "relative_path": relative(repo_root, output),
        "sha256": media_probe.get("sha256"),
        "bytes": media_probe.get("bytes"),
        "mime_probe": _export_mime_probe(output),
        "duration_seconds": media_probe.get("duration_seconds"),
    }
    return {
        "schema": "demo_take_export_handoff_attestation_v0",
        "artifact_role": "review_upload_export_candidate",
        "artifact_authority": "derived_playable_export_not_source_authority",
        "source_authority_refs": source_authority_refs,
        "custody_at_export": {
            "storage_governor_state": storage_governor_ref.get("state"),
            "local_retention_policy": storage_governor_ref.get("local_retention_policy"),
            "restore_drill_status": storage_governor_ref.get("restore_drill_status"),
            "source_hydrate_status": storage_governor_ref.get("source_hydrate_status"),
            "raw_hydratable_for_final": raw_hydratable_for_final,
        },
        "subject": subject,
        "method": {
            "kind": method,
            "video_stream_action": "no_reencode",
            "ffmpeg_probe_status": media_probe.get("ffprobe_status"),
        },
        "transport": {
            "asset_path": transport_probe.get("asset_path"),
            "asset_url": transport_probe.get("asset_url"),
            "range_request_status": "route_contract_bound",
            "absolute_path_exposed": False,
        },
        "provider_boundary": provider_boundary,
        "readiness_vector": readiness_vector,
    }


def export_video(root: Path, destination_dir: Path | None = None) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    manifest_payload = _read_json_dict(root / "manifest.json")
    config = session.get("config") if isinstance(session.get("config"), Mapping) else {}
    repo_root = Path(config.get("repo_root") or REPO_ROOT)
    source = _playable_video_asset(root, session)
    if source is None:
        raise FileNotFoundError("no playable video asset was found for export")

    title = clean_take_title(
        manifest_payload.get("title")
        or manifest_payload.get("take_title")
        or config.get("take_title")
        or root.name,
        fallback=root.name,
    ) or root.name
    destination_root = (destination_dir or (repo_root / EXPORTS_RELATIVE_ROOT)).expanduser()
    destination_root.mkdir(parents=True, exist_ok=True)
    output = _unique_export_path(destination_root, title, source.suffix.lower() or ".mp4", source)
    method = "hardlink_lossless_export"
    if not replace_with_hardlink(output, source):
        shutil.copy2(source, output)
        method = "copy"
    media_probe = _export_media_probe(config, output)
    transport_probe = _export_transport_probe(repo_root, output)
    source_authority_ref, storage_governor_ref = _export_custody_refs(root)
    upload_readiness = _export_upload_readiness(
        media_probe=media_probe,
        transport_probe=transport_probe,
        storage_governor_ref=storage_governor_ref,
    )
    handoff_attestation = _export_handoff_attestation(
        repo_root=repo_root,
        output=output,
        method=method,
        media_probe=media_probe,
        transport_probe=transport_probe,
        source_authority_ref=source_authority_ref,
        storage_governor_ref=storage_governor_ref,
        upload_readiness=upload_readiness,
    )

    receipt = {
        "schema": "demo_take_export_receipt_v0",
        "status": "ready",
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "title": title,
        "source": relative(root, source),
        "output": relative(repo_root, output),
        "output_path": str(output),
        "method": method,
        "video_stream_action": "no_reencode",
        "bytes": output.stat().st_size if output.exists() else None,
        "artifact_role": "upload_export_candidate",
        "artifact_class": "review_upload_export",
        "source_authority_ref": source_authority_ref,
        "storage_governor_ref": storage_governor_ref,
        "media_probe": media_probe,
        "transport_probe": transport_probe,
        "upload_readiness": upload_readiness,
        "handoff_attestation": handoff_attestation,
        "subject": handoff_attestation["subject"],
        "provider_boundary": handoff_attestation["provider_boundary"],
        "readiness_vector": handoff_attestation["readiness_vector"],
        "publication_boundary": {
            "status": "not_publication_authority",
            "external_upload_performed": False,
            "provider_video_id": None,
            "required_gate": "public_release_gate",
        },
    }
    write_json(root / "render" / "export_receipt.json", receipt)
    line = f"Exported upload file: {output.name} ({method.replace('_', ' ')}, no re-encode)."
    return {
        "schema": "demo_take_export_video_result_v0",
        "status": "ready",
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "source": relative(root, source),
        "exportPath": str(output),
        "exportRelativePath": relative(repo_root, output),
        "assetPath": transport_probe.get("asset_path"),
        "assetUrl": transport_probe.get("asset_url"),
        "method": method,
        "bytes": receipt["bytes"],
        "handoffAttestation": handoff_attestation,
        "readinessVector": handoff_attestation["readiness_vector"],
        "providerBoundary": handoff_attestation["provider_boundary"],
        "statusLines": [line],
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_file_rows(root: Path) -> list[dict[str, Any]]:
    skip = {
        "render/cloud_archive_manifest.json",
        "render/cloud_archive_receipt.json",
    }
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = relative(root, path)
        if rel in skip or path.name.startswith("."):
            continue
        stat = path.stat()
        role = _storage_role_for_path(rel, None)
        rows.append({
            "relative_path": rel,
            "role": role,
            "projection_state": _storage_projection_state_for_role(role),
            "bytes": stat.st_size,
            "sha256": sha256_file(path),
        })
    return rows


def build_cloud_archive_manifest(root: Path, remote_take_path: str) -> dict[str, Any]:
    rows = _archive_file_rows(root)
    payload = {
        "schema": "demo_take_cloud_archive_manifest_v0",
        "take_id": root.name,
        "created_at": now_iso(),
        "hash_algorithm": "sha256",
        "remote_take_path": remote_take_path,
        "file_count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "files": rows,
    }
    write_json(root / "render" / "cloud_archive_manifest.json", payload)
    payload["manifest_sha256"] = sha256_file(root / "render" / "cloud_archive_manifest.json")
    write_json(root / "render" / "cloud_archive_manifest.json", payload)
    return payload


def _remote_take_path(remote_root: str, take_id: str) -> str:
    return remote_root.rstrip("/") + "/" + take_id


def _remote_file_path(remote_take_path: str, relative_path: str) -> str:
    return remote_take_path.rstrip("/") + "/" + relative_path


def _json_payload_sha256(payload: Mapping[str, Any]) -> str:
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _manifest_content_sha256(manifest_payload: Mapping[str, Any]) -> str:
    without_self_hash = dict(manifest_payload)
    without_self_hash.pop("manifest_sha256", None)
    return _json_payload_sha256(without_self_hash)


def choose_archive_transport(
    manifest_rows: list[dict[str, Any]],
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pick how custody moves to the remote: whole file tree, or media-direct
    plus one indexed sidecar bundle. Drive throughput is request-shaped, so the
    trigger is file-count / small-file-count, not total bytes."""
    requested = str((config or {}).get("cloud_archive_transport") or "auto").strip().lower()
    if requested not in ARCHIVE_TRANSPORT_MODES:
        requested = "auto"
    direct_rows = [row for row in manifest_rows if row.get("role") in ARCHIVE_DIRECT_ROLES]
    bundled_rows = [row for row in manifest_rows if row.get("role") not in ARCHIVE_DIRECT_ROLES]
    small_file_count = sum(
        1 for row in manifest_rows if int(row.get("bytes") or 0) < ARCHIVE_TRANSPORT_SMALL_FILE_MAX_BYTES
    )
    file_count = len(manifest_rows)
    if requested != "auto":
        mode = requested
        reason = f"explicit_config_{requested}"
    elif not bundled_rows:
        mode = "file_tree"
        reason = "no_bundleable_sidecars"
    elif file_count >= ARCHIVE_TRANSPORT_FILE_COUNT_THRESHOLD:
        mode = "sidecar_bundle"
        reason = f"file_count {file_count} >= {ARCHIVE_TRANSPORT_FILE_COUNT_THRESHOLD}"
    elif small_file_count >= ARCHIVE_TRANSPORT_SMALL_FILE_COUNT_THRESHOLD:
        mode = "sidecar_bundle"
        reason = f"small_file_count {small_file_count} >= {ARCHIVE_TRANSPORT_SMALL_FILE_COUNT_THRESHOLD}"
    else:
        mode = "file_tree"
        reason = "below_bundle_thresholds"
    if mode == "sidecar_bundle" and not bundled_rows:
        mode = "file_tree"
        reason = "no_bundleable_sidecars"
    return {
        "schema": "demo_take_archive_transport_v0",
        "mode": mode,
        "reason": reason,
        "file_count": file_count,
        "small_file_count": small_file_count,
        "direct_file_count": len(direct_rows),
        "bundled_file_count": len(bundled_rows),
    }


def build_sidecar_bundle(
    root: Path,
    bundled_rows: list[dict[str, Any]],
    bundle_path: Path,
) -> dict[str, Any]:
    """Write the non-media package tail as one non-solid deflate zip. Members
    keep their take-relative paths so a full-tree restore is unzip-at-root."""
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for row in bundled_rows:
            rel = str(row["relative_path"])
            bundle.write(root / rel, arcname=rel)
    return {
        "remote_relative_path": ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH,
        "format": "zip_deflate",
        "archive_sha256": sha256_file(bundle_path),
        "archive_bytes": bundle_path.stat().st_size,
        "member_count": len(bundled_rows),
        "member_total_bytes": sum(int(row.get("bytes") or 0) for row in bundled_rows),
    }


def _upload_sidecar_bundle_transport(
    root: Path,
    rclone: str,
    remote_take_path: str,
    manifest_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Media files upload direct at native relative paths; everything else
    travels as one zip object; the member manifest uploads as its own object.
    Returns an upload-shaped result plus the bundle descriptor."""
    direct_rows = [row for row in manifest_rows if row.get("role") in ARCHIVE_DIRECT_ROLES]
    bundled_rows = [row for row in manifest_rows if row.get("role") not in ARCHIVE_DIRECT_ROLES]
    for row in direct_rows:
        rel = str(row["relative_path"])
        result = _run_rclone([rclone, "copyto", str(root / rel), _remote_file_path(remote_take_path, rel)])
        if result.get("status") != "pass":
            result["failed_relative_path"] = rel
            return {"status": "fail", "stage": "direct_media_upload", "rclone": result}
    with tempfile.TemporaryDirectory(prefix="demo_take_sidecar_bundle_") as scratch:
        bundle_path = Path(scratch) / "sidecars.zip"
        bundle = build_sidecar_bundle(root, bundled_rows, bundle_path)
        result = _run_rclone([
            rclone,
            "copyto",
            str(bundle_path),
            _remote_file_path(remote_take_path, ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH),
        ])
    if result.get("status") != "pass":
        return {"status": "fail", "stage": "sidecar_bundle_upload", "rclone": result, "bundle": bundle}
    manifest_result = _run_rclone([
        rclone,
        "copyto",
        str(root / "render" / "cloud_archive_manifest.json"),
        _remote_file_path(remote_take_path, "render/cloud_archive_manifest.json"),
    ])
    if manifest_result.get("status") != "pass":
        return {"status": "fail", "stage": "member_manifest_upload", "rclone": manifest_result, "bundle": bundle}
    verify = _run_rclone([
        rclone,
        "lsf",
        _remote_file_path(remote_take_path, ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH),
    ])
    return {
        "status": "pass" if verify.get("status") == "pass" else "fail",
        "stage": "complete" if verify.get("status") == "pass" else "bundle_remote_verify",
        "rclone": verify,
        "bundle": bundle,
        "direct_file_count": len(direct_rows),
    }


def _run_rclone(command: list[str], timeout: float | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "fail",
            "exit_code": None,
            "stdout_tail": "",
            "stderr_tail": str(exc)[-1200:],
        }
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1200:],
        "stderr_tail": (proc.stderr or "")[-1200:],
    }


def _rclone_copyto_remote(
    rclone: str,
    remote_source: str,
    local_target: Path,
) -> dict[str, Any]:
    local_target.parent.mkdir(parents=True, exist_ok=True)
    return _run_rclone([rclone, "copyto", remote_source, str(local_target)])


def _restore_drill_status(blockers: list[str], warnings: list[str], archive_missing: bool = False) -> str:
    if archive_missing:
        return "missing"
    if blockers:
        return "fail"
    if warnings:
        return "warn"
    return "pass"


def _safe_zip_member_name(name: str) -> bool:
    path = Path(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def _verify_sidecar_bundle(
    *,
    bundle_path: Path,
    bundled_rows: list[dict[str, Any]],
    extract_root: Path,
    expected_sha256: str | None,
) -> tuple[str, dict[str, Any], list[str]]:
    blockers: list[str] = []
    details: dict[str, Any] = {
        "remote_relative_path": ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH,
        "archive_sha256": sha256_file(bundle_path) if bundle_path.exists() else None,
        "expected_archive_sha256": expected_sha256,
        "member_count": 0,
        "verified_member_count": 0,
    }
    if expected_sha256 and details["archive_sha256"] != expected_sha256:
        blockers.append("sidecar_bundle_sha256_mismatch")
    try:
        with zipfile.ZipFile(bundle_path) as bundle:
            names = set(bundle.namelist())
            unsafe = sorted(name for name in names if not _safe_zip_member_name(name))
            if unsafe:
                blockers.append("sidecar_bundle_contains_unsafe_member_path")
                details["unsafe_members"] = unsafe[:5]
            details["member_count"] = len(names)
            missing = [str(row.get("relative_path")) for row in bundled_rows if str(row.get("relative_path")) not in names]
            if missing:
                blockers.append("sidecar_bundle_missing_manifest_members")
                details["missing_members"] = missing[:10]
            expected_names = {str(row.get("relative_path") or "") for row in bundled_rows}
            unexpected = sorted(name for name in names if name not in expected_names)
            if unexpected:
                blockers.append("sidecar_bundle_contains_unmanifested_members")
                details["unexpected_members"] = unexpected[:10]
            verified = 0
            for row in bundled_rows:
                rel = str(row.get("relative_path") or "")
                if rel not in names or not _safe_zip_member_name(rel):
                    continue
                member_sha = hashlib.sha256(bundle.read(rel)).hexdigest()
                if member_sha != row.get("sha256"):
                    blockers.append(f"sidecar_member_sha256_mismatch:{rel}")
                    continue
                verified += 1
            if not blockers:
                extract_root.mkdir(parents=True, exist_ok=True)
                bundle.extractall(extract_root)
            details["verified_member_count"] = verified
    except (OSError, zipfile.BadZipFile) as exc:
        blockers.append(f"sidecar_bundle_unreadable:{exc}")
    return ("pass" if not blockers else "fail"), details, blockers


def restore_drill(
    root: Path,
    *,
    restore_root: Path | None = None,
    rclone_path: str | None = None,
    keep_restore_root: bool = False,
) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    take_id = str(session.get("take_id") or root.name)
    receipt_path = root / "render" / "cloud_archive_receipt.json"
    archive_receipt = _read_json_dict(receipt_path)
    blockers: list[str] = []
    warnings: list[str] = []
    checked_at = now_iso()

    def finish(
        *,
        status: str | None = None,
        remote_receipt_status: str = "missing",
        remote_manifest_status: str = "missing",
        source_hydrate_status: str = "missing",
        sidecar_restore_status: str = "missing",
        compile_smoke_status: str = "missing",
        cleanup_status: str = "missing",
        transport_mode: str | None = None,
        remote_take_path: str | None = None,
        hydrated_files: list[dict[str, Any]] | None = None,
        sidecar_bundle: dict[str, Any] | None = None,
        kept_restore_root: Path | None = None,
        storage_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_status = status or _restore_drill_status(blockers, warnings)
        receipt = {
            "schema": "demo_take_restore_drill_v0",
            "status": resolved_status,
            "take_id": take_id,
            "checked_at": checked_at,
            "transport_mode": transport_mode,
            "remote_take_path": remote_take_path,
            "remote_receipt_status": remote_receipt_status,
            "remote_manifest_status": remote_manifest_status,
            "source_hydrate_status": source_hydrate_status,
            "sidecar_restore_status": sidecar_restore_status,
            "compile_smoke_status": compile_smoke_status,
            "cleanup_status": cleanup_status,
            "hydrated_files": hydrated_files or [],
            "sidecar_bundle": sidecar_bundle,
            "blockers": blockers,
            "warnings": warnings,
        }
        if kept_restore_root is not None:
            receipt["restore_root"] = str(kept_restore_root)
        write_json(root / RESTORE_DRILL_RECEIPT_RELATIVE_PATH, receipt)
        if "repo_root" in config and "ffmpeg_path" in config and "screenshot_interval_seconds" in config:
            tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
            markers = session.get("markers") if isinstance(session.get("markers"), list) else []
            pause_events = session.get("pause_events") if isinstance(session.get("pause_events"), list) else []
            media_segments = session.get("media_segments") if isinstance(session.get("media_segments"), list) else []
            existing_manifest = _read_json_dict(root / "manifest.json")
            write_json(
                root / "manifest.json",
                manifest(
                    take_id,
                    root,
                    str(existing_manifest.get("recording_state") or "package_ready"),
                    config,
                    tracks,
                    list(dict.fromkeys(session.get("known_failures", []) if isinstance(session.get("known_failures"), list) else [])),
                    markers=markers,
                    pause_events=pause_events,
                    media_segments=media_segments,
                ),
            )
        if storage_receipt is None:
            storage_receipt = write_local_storage_receipt(root, config, session)
        line = {
            "pass": f"Restore drill passed for {take_id}: source media hydrated and archive custody verified.",
            "warn": f"Restore drill warning for {take_id}: custody is mostly verified but needs review.",
            "fail": f"Restore drill failed for {take_id}: {', '.join(blockers[:3])}.",
            "missing": f"Restore drill missing for {take_id}: no verified cloud archive receipt is available.",
        }.get(resolved_status, f"Restore drill status for {take_id}: {resolved_status}.")
        return {
            "schema": "demo_take_restore_drill_result_v0",
            "status": resolved_status,
            "takeID": take_id,
            "rootPath": str(root),
            "remoteTakePath": remote_take_path,
            "receipt": receipt,
            "storageReceipt": storage_receipt,
            "statusLines": [line],
        }

    if not archive_receipt:
        blockers.append("cloud_archive_receipt_missing")
        return finish(status="missing", cleanup_status="not_started")
    archive_status = str(archive_receipt.get("status") or "missing")
    if archive_status not in {"ready", "partial"}:
        blockers.append(f"cloud_archive_not_verified:{archive_status}")
        return finish(
            status="fail",
            cleanup_status="not_started",
            transport_mode=(archive_receipt.get("transport") or {}).get("mode")
            if isinstance(archive_receipt.get("transport"), Mapping)
            else None,
            remote_take_path=archive_receipt.get("remote_take_path"),
        )
    remote_take_path = str(archive_receipt.get("remote_take_path") or "").strip()
    if not remote_take_path:
        blockers.append("remote_take_path_missing")
        return finish(status="fail", cleanup_status="not_started")

    rclone = rclone_path or os.environ.get("DEMO_TAKE_RCLONE") or shutil.which("rclone")
    if not rclone:
        blockers.append("rclone executable not found")
        return finish(
            status="fail",
            cleanup_status="not_started",
            transport_mode=(archive_receipt.get("transport") or {}).get("mode")
            if isinstance(archive_receipt.get("transport"), Mapping)
            else None,
            remote_take_path=remote_take_path,
        )

    transport = archive_receipt.get("transport") if isinstance(archive_receipt.get("transport"), Mapping) else {}
    transport_mode = str(transport.get("mode") or "file_tree")
    keep_output = keep_restore_root or restore_root is not None
    temp_context: tempfile.TemporaryDirectory[str] | None = None
    try:
        if restore_root is None:
            temp_context = tempfile.TemporaryDirectory(prefix="demo_take_restore_drill_")
            working_root = Path(temp_context.name)
        else:
            working_root = restore_root
            working_root.mkdir(parents=True, exist_ok=True)
        hydrate_root = working_root / "hydrate"
        sidecar_root = working_root / "sidecars"

        remote_receipt_target = working_root / "cloud_archive_receipt.json"
        remote_receipt = _rclone_copyto_remote(
            str(rclone),
            _remote_file_path(remote_take_path, "render/cloud_archive_receipt.json"),
            remote_receipt_target,
        )
        remote_receipt_status = "pass" if remote_receipt.get("status") == "pass" and remote_receipt_target.exists() else "fail"
        if remote_receipt_status != "pass":
            blockers.append("remote_receipt_missing")

        remote_manifest_target = working_root / "cloud_archive_manifest.json"
        remote_manifest = _rclone_copyto_remote(
            str(rclone),
            _remote_file_path(remote_take_path, str(archive_receipt.get("manifest") or "render/cloud_archive_manifest.json")),
            remote_manifest_target,
        )
        remote_manifest_status = "pass" if remote_manifest.get("status") == "pass" and remote_manifest_target.exists() else "fail"
        manifest_payload: dict[str, Any] = {}
        manifest_rows: list[dict[str, Any]] = []
        if remote_manifest_status != "pass":
            blockers.append("remote_manifest_missing")
        else:
            try:
                manifest_payload = json.loads(remote_manifest_target.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                blockers.append(f"remote_manifest_unreadable:{exc}")
                remote_manifest_status = "fail"
            else:
                declared = str(manifest_payload.get("manifest_sha256") or "")
                expected = str(archive_receipt.get("manifest_sha256") or "")
                if expected and declared != expected:
                    blockers.append("remote_manifest_receipt_sha256_mismatch")
                    remote_manifest_status = "fail"
                if declared and _manifest_content_sha256(manifest_payload) != declared:
                    blockers.append("remote_manifest_content_sha256_mismatch")
                    remote_manifest_status = "fail"
                rows = manifest_payload.get("files")
                manifest_rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

        source_rows = [row for row in manifest_rows if row.get("role") == "source_media"]
        hydrated_files: list[dict[str, Any]] = []
        if not source_rows:
            blockers.append("source_media_manifest_rows_missing")
            source_hydrate_status = "fail"
        else:
            source_hydrate_status = "pass"
            for row in source_rows:
                rel = str(row.get("relative_path") or "")
                target = hydrate_root / rel
                copy = _rclone_copyto_remote(str(rclone), _remote_file_path(remote_take_path, rel), target)
                copied = copy.get("status") == "pass" and target.exists()
                file_record = {"relative_path": rel, "status": "pass" if copied else "fail"}
                if not copied:
                    blockers.append(f"source_media_remote_missing:{rel}")
                    source_hydrate_status = "fail"
                else:
                    expected_bytes = row.get("bytes")
                    actual_bytes = target.stat().st_size
                    expected_sha = str(row.get("sha256") or "")
                    actual_sha = sha256_file(target)
                    file_record.update({"bytes": actual_bytes, "sha256": actual_sha})
                    if isinstance(expected_bytes, int) and actual_bytes != expected_bytes:
                        blockers.append(f"source_media_size_mismatch:{rel}")
                        source_hydrate_status = "fail"
                    if expected_sha and actual_sha != expected_sha:
                        blockers.append(f"source_media_sha256_mismatch:{rel}")
                        source_hydrate_status = "fail"
                hydrated_files.append(file_record)

        if transport_mode == "sidecar_bundle":
            bundle_target = working_root / "sidecars.zip"
            bundle_copy = _rclone_copyto_remote(
                str(rclone),
                _remote_file_path(remote_take_path, ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH),
                bundle_target,
            )
            if bundle_copy.get("status") != "pass" or not bundle_target.exists():
                sidecar_restore_status = "fail"
                sidecar_bundle = {"remote_relative_path": ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH}
                blockers.append("sidecar_bundle_remote_missing")
            else:
                bundled_rows = [row for row in manifest_rows if row.get("role") not in ARCHIVE_DIRECT_ROLES]
                sidecar_restore_status, sidecar_bundle, sidecar_blockers = _verify_sidecar_bundle(
                    bundle_path=bundle_target,
                    bundled_rows=bundled_rows,
                    extract_root=sidecar_root,
                    expected_sha256=(transport.get("bundle") or {}).get("archive_sha256")
                    if isinstance(transport.get("bundle"), Mapping)
                    else None,
                )
                blockers.extend(sidecar_blockers)
        else:
            sidecar_restore_status = "pass"
            sidecar_bundle = None

        if source_hydrate_status != "pass":
            compile_smoke_status = "blocked"
        elif _is_fake_capture(config):
            compile_smoke_status = "pass"
        else:
            probe_target = next(
                (hydrate_root / str(row.get("relative_path")) for row in source_rows if (hydrate_root / str(row.get("relative_path"))).exists()),
                None,
            )
            duration = probe_media_duration_seconds(config, probe_target) if probe_target is not None else None
            if duration is None:
                compile_smoke_status = "fail"
                blockers.append("hydrated_source_ffprobe_failed")
            else:
                compile_smoke_status = "pass"

        cleanup_status = "kept" if keep_output else "pass"
        return finish(
            remote_receipt_status=remote_receipt_status,
            remote_manifest_status=remote_manifest_status,
            source_hydrate_status=source_hydrate_status,
            sidecar_restore_status=sidecar_restore_status,
            compile_smoke_status=compile_smoke_status,
            cleanup_status=cleanup_status,
            transport_mode=transport_mode,
            remote_take_path=remote_take_path,
            hydrated_files=hydrated_files,
            sidecar_bundle=sidecar_bundle,
            kept_restore_root=working_root if keep_output else None,
        )
    finally:
        if temp_context is not None:
            temp_context.cleanup()


def write_local_proxy_video(root: Path, config: dict[str, Any], source: Path) -> dict[str, Any]:
    output = root / "render" / f".rough_cut.proxy_tmp_{secrets.token_hex(4)}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    source_stat = _safe_stat(source)
    source_row = {
        "relative_path": relative(root, source),
        "bytes": source_stat.st_size if source_stat else None,
        "sha256": f"sha256:{sha256_file(source)}" if source_stat else None,
        "duration_seconds": probe_media_duration_seconds(config, source),
    }
    if _is_fake_capture(config):
        shutil.copy2(source, output)
        return {
            "status": "ready",
            "source": source_row,
            "output": relative(root, output),
            "method": "copy_fake_fixture_proxy",
            "video_stream_action": "synthetic_fixture_copy",
            "bytes": output.stat().st_size if output.exists() else None,
        }

    ffmpeg = config.get("ffmpeg_path") or shutil.which("ffmpeg")
    if not ffmpeg:
        return {
            "status": "failed",
            "source": source_row,
            "output": None,
            "method": "ffmpeg_proxy",
            "video_stream_action": "reencode_proxy",
            "known_failures": ["ffmpeg executable not found for local proxy render"],
        }

    command = [
        str(ffmpeg),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-vf",
        efficient_video_filter({"recording_quality": "efficient"}),
        "-c:v",
        "h264_videotoolbox",
        "-b:v",
        EFFICIENT_SCREEN_BITRATE,
        "-c:a",
        "aac",
        "-b:a",
        EFFICIENT_AUDIO_BITRATE,
        str(output),
    ]
    log_path = root / "logs" / "cloud_archive_proxy.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        log.write(f"=== {now_iso()} local proxy command: {' '.join(command)}\n".encode("utf-8"))
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"proxy render unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status != 0 or not output.exists():
        try:
            if output.exists():
                output.unlink()
        except OSError:
            pass
        return {
            "status": "failed",
            "source": source_row,
            "output": None,
            "method": "ffmpeg_proxy",
            "video_stream_action": "reencode_proxy",
            "known_failures": ["local proxy render failed; see logs/cloud_archive_proxy.log"],
        }
    return {
        "status": "ready",
        "source": source_row,
        "output": relative(root, output),
        "method": "ffmpeg_proxy",
        "video_stream_action": "reencode_proxy",
        "bytes": output.stat().st_size,
    }


def _media_prune_candidates(root: Path, rough_keep: Path) -> list[Path]:
    candidates: list[Path] = []
    media_suffixes = {".mp4", ".mov", ".m4v", ".m4a", ".wav", ".aac"}
    for base in [root / "tracks", root / "render"]:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in media_suffixes:
                continue
            if files_are_same(path, rough_keep) or path.resolve() == rough_keep.resolve():
                continue
            if path.name.startswith("."):
                continue
            candidates.append(path)
    return candidates


def apply_proxy_local_retention(
    root: Path,
    config: dict[str, Any],
    session: Mapping[str, Any],
    *,
    archive_status: str = "ready",
    remote_take_path: str | None = None,
    manifest_sha256: str | None = None,
) -> dict[str, Any]:
    if archive_status != "ready":
        return {
            "schema": "demo_take_proxy_review_receipt_v0",
            "status": "failed",
            "known_failures": ["cloud archive must be verified before pruning local originals"],
            "prune_gate": {
                "status": "blocked",
                "cloud_archive_status": archive_status,
                "proxy_probe_status": "not_run",
                "raw_prune_allowed": False,
            },
        }
    source = _playable_video_asset(root, session)
    if source is None:
        return {
            "schema": "demo_take_proxy_review_receipt_v0",
            "status": "failed",
            "known_failures": ["no playable source video was available for local proxy retention"],
            "prune_gate": {
                "status": "blocked",
                "cloud_archive_status": archive_status,
                "proxy_probe_status": "not_run",
                "raw_prune_allowed": False,
            },
        }
    proxy = write_local_proxy_video(root, config, source)
    if proxy.get("status") != "ready" or not proxy.get("output"):
        proxy["schema"] = "demo_take_proxy_review_receipt_v0"
        proxy["prune_gate"] = {
            "status": "blocked",
            "cloud_archive_status": archive_status,
            "remote_take_path": remote_take_path,
            "manifest_sha256": manifest_sha256,
            "proxy_probe_status": "not_run",
            "raw_prune_allowed": False,
        }
        write_json(root / "render" / "proxy_review_receipt.json", proxy)
        return proxy

    proxy_path = root / str(proxy["output"])
    rough_keep = root / "render" / "rough_cut.mp4"
    if not files_are_same(proxy_path, rough_keep):
        os.replace(proxy_path, rough_keep)
    proxy_duration = probe_media_duration_seconds(config, rough_keep)
    proxy_probe_ready = proxy_duration is not None or _is_fake_capture(config)
    if not proxy_probe_ready:
        receipt = {
            "schema": "demo_take_proxy_review_receipt_v0",
            "status": "failed",
            "source": proxy.get("source"),
            "proxy": {
                "relative_path": relative(root, rough_keep),
                "bytes": rough_keep.stat().st_size if rough_keep.exists() else None,
                "duration_seconds": None,
                "video_stream_action": "reencode_proxy",
            },
            "known_failures": ["local proxy exists but could not be probed as playable; originals were kept"],
            "prune_gate": {
                "status": "blocked",
                "cloud_archive_status": archive_status,
                "remote_take_path": remote_take_path,
                "manifest_sha256": manifest_sha256,
                "proxy_probe_status": "failed",
                "raw_prune_allowed": False,
            },
        }
        write_json(root / "render" / "proxy_review_receipt.json", receipt)
        return receipt
    pruned: list[dict[str, Any]] = []
    failures: list[str] = []
    for candidate in _media_prune_candidates(root, rough_keep):
        rel = relative(root, candidate)
        try:
            size = candidate.stat().st_size
            candidate.unlink()
            pruned.append({"relative_path": rel, "bytes": size})
        except OSError as exc:
            failures.append(f"Could not prune {rel}: {exc}")

    receipt = _read_json_dict(root / "render" / "render_receipt.json")
    receipt.update({
        "schema": "demo_take_render_receipt_v0",
        "status": "ready",
        "output": relative(root, rough_keep),
        "known_failures": receipt.get("known_failures", []),
        "storage_profile": storage_profile(config),
        "storage_optimization": {
            "method": "cloud_archive_proxy_retention",
            "rough_cut_screen_hardlinked": False,
            "video_stream_action": "reencode_proxy",
            "source_video_archived_to_cloud": True,
            "local_retention": "proxy",
        },
    })
    write_json(root / "render" / "render_receipt.json", receipt)
    result = {
        "schema": "demo_take_proxy_review_receipt_v0",
        "status": "ready" if not failures else "partial",
        "source": proxy.get("source"),
        "proxy": {
            "relative_path": relative(root, rough_keep),
            "bytes": rough_keep.stat().st_size if rough_keep.exists() else None,
            "duration_seconds": proxy_duration,
            "video_stream_action": "reencode_proxy" if not _is_fake_capture(config) else "synthetic_fixture_copy",
        },
        "prune_gate": {
            "status": "pass" if not failures else "warn",
            "cloud_archive_status": archive_status,
            "remote_take_path": remote_take_path,
            "manifest_sha256": manifest_sha256,
            "proxy_probe_status": "pass",
            "raw_prune_allowed": True,
        },
        "pruned_files": pruned,
        "pruned_bytes": sum(int(row["bytes"]) for row in pruned),
        "known_failures": failures,
    }
    write_json(root / "render" / "proxy_review_receipt.json", result)
    return result


def apply_review_local_retention(
    root: Path,
    config: dict[str, Any],
    session: Mapping[str, Any],
    *,
    archive_status: str = "ready",
    remote_take_path: str | None = None,
    manifest_sha256: str | None = None,
    rclone_path: str | None = None,
) -> dict[str, Any]:
    if archive_status != "ready":
        return {
            "schema": "demo_take_review_retention_receipt_v0",
            "status": "failed",
            "known_failures": ["cloud archive must be verified before review-local pruning"],
            "prune_gate": {
                "status": "blocked",
                "cloud_archive_status": archive_status,
                "semantic_proxy_status": "not_run",
                "review_video_status": "not_run",
                "raw_prune_allowed": False,
            },
        }

    semantic_proxy = build_semantic_proxy(root)
    semantic_status = str(semantic_proxy.get("status") or "missing")
    proxy_state, review_path, review_duration = _proxy_review_state(root, config)
    if semantic_status != "ready" or proxy_state != "proxy_ready":
        blockers: list[str] = []
        if semantic_status != "ready":
            blockers.append(f"semantic_proxy_not_ready:{semantic_status}")
        if proxy_state != "proxy_ready":
            blockers.append(f"review_video_not_ready:{proxy_state}")
        result = {
            "schema": "demo_take_review_retention_receipt_v0",
            "status": "failed",
            "semantic_proxy": {
                "status": semantic_status,
                "path": "semantic_proxy.json" if (root / "semantic_proxy.json").exists() else None,
                "section_count": semantic_proxy.get("section_count"),
            },
            "review_video": {
                "relative_path": relative(root, review_path) if review_path else None,
                "duration_seconds": review_duration,
                "status": proxy_state,
            },
            "known_failures": blockers,
            "prune_gate": {
                "status": "blocked",
                "cloud_archive_status": archive_status,
                "remote_take_path": remote_take_path,
                "manifest_sha256": manifest_sha256,
                "semantic_proxy_status": semantic_status,
                "review_video_status": proxy_state,
                "raw_prune_allowed": False,
            },
        }
        write_json(root / "render" / "review_retention_receipt.json", result)
        return result

    eviction = evict_take_to_cloud(
        root,
        remote=str(config.get("cloud_archive_remote") or DEFAULT_CLOUD_ARCHIVE_REMOTE),
        rclone_path=rclone_path,
        heavy_dirs=RECLAIM_HEAVY_DIRS,
        preserve_relative_prefixes=RECLAIM_PRESERVE_RELATIVE_PREFIXES,
        dry_run=False,
        evict_only=True,
    )
    eviction_status = str(eviction.get("status") or "unknown")
    failures = [str(item) for item in eviction.get("known_failures", []) if item]
    ready_statuses = {"satisfied", "partial", "noop", "ready"}
    result = {
        "schema": "demo_take_review_retention_receipt_v0",
        "status": "ready" if eviction_status in ready_statuses and not failures else ("partial" if eviction.get("freed_bytes") else "failed"),
        "semantic_proxy": {
            "status": semantic_status,
            "path": "semantic_proxy.json",
            "section_count": semantic_proxy.get("section_count"),
            "speech_section_count": semantic_proxy.get("speech_section_count"),
            "silence_section_count": semantic_proxy.get("silence_section_count"),
        },
        "review_video": {
            "relative_path": relative(root, review_path) if review_path else None,
            "duration_seconds": review_duration,
            "status": proxy_state,
        },
        "eviction": eviction,
        "prune_gate": {
            "status": "pass" if eviction_status in ready_statuses and not failures else "warn",
            "cloud_archive_status": archive_status,
            "remote_take_path": remote_take_path,
            "manifest_sha256": manifest_sha256,
            "semantic_proxy_status": semantic_status,
            "review_video_status": proxy_state,
            "raw_prune_allowed": eviction_status in ready_statuses and not failures,
        },
        "local_retention": "review",
        "created_at": now_iso(),
        "known_failures": failures,
    }
    write_json(root / "render" / "review_retention_receipt.json", result)
    return result


def archive_originals(
    root: Path,
    *,
    remote: str | None = None,
    local_retention: str | None = None,
    rclone_path: str | None = None,
    force: bool = False,
    transport_mode: str | None = None,
) -> dict[str, Any]:
    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    take_id = str(session.get("take_id") or root.name)
    existing_receipt = _read_json_dict(root / "render" / "cloud_archive_receipt.json")
    if existing_receipt.get("status") == "ready" and not force:
        storage_receipt = write_local_storage_receipt(root, config, session)
        line = f"Cloud archive already ready for {take_id}: {existing_receipt.get('remote_take_path')}."
        return {
            "schema": "demo_take_archive_originals_result_v0",
            "status": "skipped",
            "takeID": take_id,
            "rootPath": str(root),
            "remoteTakePath": existing_receipt.get("remote_take_path"),
            "statusLines": [line],
            "receipt": existing_receipt,
            "storageReceipt": storage_receipt,
        }

    retention = (local_retention or cloud_archive_local_retention(config)).strip().lower()
    if retention not in CLOUD_ARCHIVE_LOCAL_RETENTIONS:
        raise ValueError(f"unknown local retention: {retention}")
    remote_root = (remote or cloud_archive_remote(config)).strip()
    config["cloud_archive_remote"] = remote_root
    config["cloud_archive_local_retention"] = retention
    if retention == "review":
        build_semantic_proxy(root)
    remote_take_path = _remote_take_path(remote_root, take_id)
    manifest_payload = build_cloud_archive_manifest(root, remote_take_path)

    rclone = rclone_path or os.environ.get("DEMO_TAKE_RCLONE") or shutil.which("rclone")
    failures: list[str] = []
    if not rclone:
        failures.append("rclone executable not found")
        receipt = {
            "schema": "demo_take_cloud_archive_receipt_v0",
            "status": "failed",
            "take_id": take_id,
            "created_at": now_iso(),
            "remote": remote_root,
            "remote_take_path": remote_take_path,
            "hash_algorithm": "sha256",
            "manifest": "render/cloud_archive_manifest.json",
            "manifest_sha256": manifest_payload.get("manifest_sha256"),
            "file_count": manifest_payload.get("file_count"),
            "total_bytes": manifest_payload.get("total_bytes"),
            "local_retention": "full",
            "known_failures": failures,
        }
        write_json(root / "render" / "cloud_archive_receipt.json", receipt)
        storage_receipt = write_local_storage_receipt(root, config, session)
        return {
            "schema": "demo_take_archive_originals_result_v0",
            "status": "failed",
            "takeID": take_id,
            "rootPath": str(root),
            "remoteTakePath": remote_take_path,
            "knownFailures": failures,
            "statusLines": ["Cloud archive failed: rclone executable not found."],
            "receipt": receipt,
            "storageReceipt": storage_receipt,
        }

    transport_config: Mapping[str, Any] = {**config}
    if transport_mode:
        transport_config["cloud_archive_transport"] = transport_mode
    elif retention == "review":
        # Review-local pruning verifies and removes heavy dirs by checking their
        # normal remote paths, so the default retention uses file-tree custody.
        transport_config["cloud_archive_transport"] = "file_tree"
    transport = choose_archive_transport(manifest_payload.get("files") or [], transport_config)
    bundle_descriptor: dict[str, Any] | None = None
    if transport["mode"] == "sidecar_bundle":
        bundle_upload = _upload_sidecar_bundle_transport(
            root,
            str(rclone),
            remote_take_path,
            manifest_payload.get("files") or [],
        )
        bundle_descriptor = bundle_upload.get("bundle")
        transport["bundle"] = bundle_descriptor
        upload = dict(bundle_upload.get("rclone") or {})
        upload["transport_stage"] = bundle_upload.get("stage")
        upload["status"] = bundle_upload.get("status")
    else:
        copy_command = [str(rclone), "copy", str(root), remote_take_path]
        upload = _run_rclone(copy_command)
    verification: dict[str, Any] = {
        "status": "skipped",
        "mode": "not_started",
    }
    if upload.get("status") != "pass":
        failures.append(
            "rclone copy failed"
            if transport["mode"] == "file_tree"
            else f"sidecar bundle transport failed at stage {upload.get('transport_stage')}"
        )
        receipt = {
            "schema": "demo_take_cloud_archive_receipt_v0",
            "status": "failed",
            "take_id": take_id,
            "created_at": now_iso(),
            "remote": remote_root,
            "remote_take_path": remote_take_path,
            "rclone": upload,
            "verification": verification,
            "transport": transport,
            "hash_algorithm": "sha256",
            "manifest": "render/cloud_archive_manifest.json",
            "manifest_sha256": manifest_payload.get("manifest_sha256"),
            "file_count": manifest_payload.get("file_count"),
            "total_bytes": manifest_payload.get("total_bytes"),
            "local_retention": "full",
            "known_failures": failures,
        }
        write_json(root / "render" / "cloud_archive_receipt.json", receipt)
        storage_receipt = write_local_storage_receipt(root, config, session)
        return {
            "schema": "demo_take_archive_originals_result_v0",
            "status": "failed",
            "takeID": take_id,
            "rootPath": str(root),
            "remoteTakePath": remote_take_path,
            "knownFailures": failures,
            "statusLines": [f"Cloud archive failed for {take_id}; local originals were kept."],
            "receipt": receipt,
            "storageReceipt": storage_receipt,
        }
    if transport["mode"] == "file_tree":
        verification_command = [str(rclone), "check", str(root), remote_take_path, "--one-way"]
        verification_result = _run_rclone(verification_command)
        verification = {
            "status": "pass" if verification_result.get("status") == "pass" else "fail",
            "mode": "rclone_check_one_way",
            "rclone": verification_result,
        }
    else:
        verification = {
            "status": "pass" if upload.get("status") == "pass" else "fail",
            "mode": "sidecar_bundle_lsf_plus_direct_upload",
            "rclone": upload,
        }
    if verification.get("status") != "pass":
        failures.append("rclone check failed")
        receipt = {
            "schema": "demo_take_cloud_archive_receipt_v0",
            "status": "failed",
            "take_id": take_id,
            "created_at": now_iso(),
            "remote": remote_root,
            "remote_take_path": remote_take_path,
            "rclone": upload,
            "verification": verification,
            "transport": transport,
            "hash_algorithm": "sha256",
            "manifest": "render/cloud_archive_manifest.json",
            "manifest_sha256": manifest_payload.get("manifest_sha256"),
            "file_count": manifest_payload.get("file_count"),
            "total_bytes": manifest_payload.get("total_bytes"),
            "local_retention": "full",
            "known_failures": failures,
        }
        write_json(root / "render" / "cloud_archive_receipt.json", receipt)
        storage_receipt = write_local_storage_receipt(root, config, session)
        return {
            "schema": "demo_take_archive_originals_result_v0",
            "status": "failed",
            "takeID": take_id,
            "rootPath": str(root),
            "remoteTakePath": remote_take_path,
            "knownFailures": failures,
            "statusLines": [f"Cloud archive verification failed for {take_id}; local originals were kept."],
            "receipt": receipt,
            "storageReceipt": storage_receipt,
        }

    proxy_retention: dict[str, Any] | None = None
    review_retention: dict[str, Any] | None = None
    applied_retention = "full"
    if retention == "proxy":
        proxy_retention = apply_proxy_local_retention(
            root,
            config,
            session,
            archive_status="ready",
            remote_take_path=remote_take_path,
            manifest_sha256=str(manifest_payload.get("manifest_sha256") or ""),
        )
        if proxy_retention.get("status") in {"ready", "partial"}:
            applied_retention = "proxy"
            config["cloud_archive_local_retention"] = "proxy"
            session["config"] = config
            write_json(root / "session.json", dict(session))
        else:
            failures.extend(proxy_retention.get("known_failures", ["local proxy retention failed"]))
    elif retention == "review":
        review_retention = apply_review_local_retention(
            root,
            config,
            session,
            archive_status="ready",
            remote_take_path=remote_take_path,
            manifest_sha256=str(manifest_payload.get("manifest_sha256") or ""),
            rclone_path=str(rclone),
        )
        if review_retention.get("status") in {"ready", "partial"}:
            applied_retention = "review"
            config["cloud_archive_local_retention"] = "review"
            session["config"] = config
            write_json(root / "session.json", dict(session))
        else:
            failures.extend(review_retention.get("known_failures", ["review retention failed"]))

    restore_plan: dict[str, str] = {
        "source_media": f"rclone copy {remote_take_path}/tracks <take_root>/tracks",
        "full_tree": f"rclone copy {remote_take_path} <take_root>",
    }
    if transport["mode"] == "sidecar_bundle":
        bundle_remote = _remote_file_path(remote_take_path, ARCHIVE_BUNDLE_REMOTE_RELATIVE_PATH)
        restore_plan["full_tree"] = (
            f"rclone copy {remote_take_path} <take_root> (direct media + receipts), then "
            f"unzip {bundle_remote} at <take_root> for the package sidecars"
        )
    receipt = {
        "schema": "demo_take_cloud_archive_receipt_v0",
        "status": "ready" if not failures else "partial",
        "take_id": take_id,
        "created_at": now_iso(),
        "remote": remote_root,
        "remote_take_path": remote_take_path,
        "rclone": upload,
        "rclone_command_class": "copy/check/copyto",
        "verification": verification,
        "transport": transport,
        "restore_plan": restore_plan,
        "hash_algorithm": "sha256",
        "manifest": "render/cloud_archive_manifest.json",
        "manifest_sha256": manifest_payload.get("manifest_sha256"),
        "file_count": manifest_payload.get("file_count"),
        "total_bytes": manifest_payload.get("total_bytes"),
        "local_retention": applied_retention,
        "proxy_retention": proxy_retention,
        "review_retention": review_retention,
        "known_failures": failures,
    }
    write_json(root / "render" / "cloud_archive_receipt.json", receipt)
    receipt_upload = _run_rclone([
        str(rclone),
        "copyto",
        str(root / "render" / "cloud_archive_receipt.json"),
        remote_take_path.rstrip("/") + "/render/cloud_archive_receipt.json",
    ])
    if receipt_upload.get("status") != "pass":
        failures.append("rclone receipt copy failed")
        receipt["status"] = "partial"
        receipt["known_failures"] = failures
    receipt["receipt_upload"] = receipt_upload
    write_json(root / "render" / "cloud_archive_receipt.json", receipt)

    if "repo_root" in config and "ffmpeg_path" in config and "screenshot_interval_seconds" in config:
        tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
        markers = session.get("markers") if isinstance(session.get("markers"), list) else []
        pause_events = session.get("pause_events") if isinstance(session.get("pause_events"), list) else []
        existing_manifest = _read_json_dict(root / "manifest.json")
        write_json(
            root / "manifest.json",
            manifest(
                take_id,
                root,
                str(existing_manifest.get("recording_state") or "package_ready"),
                config,
                tracks,
                list(dict.fromkeys(session.get("known_failures", []) if isinstance(session.get("known_failures"), list) else [])),
                markers=markers,
                pause_events=pause_events,
            ),
        )

    storage_receipt = write_local_storage_receipt(root, config, session)
    if applied_retention == "proxy":
        line = (
            f"Cloud archive ready: {remote_take_path}; local proxy retained "
            f"({human_bytes(int((proxy_retention or {}).get('pruned_bytes') or 0))} pruned)."
        )
    elif applied_retention == "review":
        pruned_bytes = int(((review_retention or {}).get("eviction") or {}).get("freed_bytes") or 0)
        line = (
            f"Cloud archive ready: {remote_take_path}; local 720p review + semantic proxy retained "
            f"({human_bytes(pruned_bytes)} heavy media evicted)."
        )
    else:
        line = f"Cloud archive ready: {remote_take_path}; local originals retained."
    status_lines = [line]
    if transport["mode"] == "sidecar_bundle" and bundle_descriptor:
        status_lines.append(
            f"Package sidecars travelled as one bundle: {bundle_descriptor['member_count']} files in "
            f"{human_bytes(int(bundle_descriptor.get('archive_bytes') or 0))} "
            f"({transport.get('direct_file_count')} media files uploaded direct)."
        )
    return {
        "schema": "demo_take_archive_originals_result_v0",
        "status": receipt["status"],
        "takeID": take_id,
        "rootPath": str(root),
        "remoteTakePath": remote_take_path,
        "localRetention": applied_retention,
        "transportMode": transport["mode"],
        "manifestSha256": receipt.get("manifest_sha256"),
        "fileCount": receipt.get("file_count"),
        "totalBytes": receipt.get("total_bytes"),
        "knownFailures": failures,
        "statusLines": status_lines,
        "receipt": receipt,
        "storageReceipt": storage_receipt,
    }


# Heavy, restorable directories evicted first when reclaiming local disk. The
# rendered deliverables in render/ and the small JSON sidecars stay local so a
# take remains navigable and review-able after eviction; only bulk source media,
# regenerable frames, and editing intermediates go cold to the cloud spillway.
RECLAIM_HEAVY_DIRS: tuple[str, ...] = ("tracks", "frames", "edit")
RECLAIM_PRESERVE_RELATIVE_PREFIXES: tuple[str, ...] = ("frames/semantic/",)


def _free_disk_bytes(path: Path) -> int | None:
    probe = path if path.exists() else REPO_ROOT
    try:
        return int(shutil.disk_usage(probe).free)
    except OSError:
        return None


def _tree_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for child in path.rglob("*"):
        try:
            if child.is_file() and not child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def _remove_empty_dirs(root: Path) -> None:
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            next(path.iterdir())
        except StopIteration:
            try:
                path.rmdir()
            except OSError:
                pass
        except OSError:
            pass


def evict_take_to_cloud(
    root: Path,
    *,
    remote: str | None = None,
    rclone_path: str | None = None,
    heavy_dirs: tuple[str, ...] = RECLAIM_HEAVY_DIRS,
    preserve_relative_prefixes: tuple[str, ...] = RECLAIM_PRESERVE_RELATIVE_PREFIXES,
    dry_run: bool = False,
    evict_only: bool = False,
) -> dict[str, Any]:
    """Make the cloud a superset of a take's heavy dirs, verify one-way custody,
    then evict those local bytes. Custody-gated: a directory is only deleted
    after rclone confirms every local file is present and matching on the remote.

    evict_only skips the upload and only reclaims dirs already verified on the
    remote (fast path for cold takes; never blocks on a large transfer).
    """
    session = _read_json_dict(root / "session.json")
    config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
    take_id = str(session.get("take_id") or root.name)
    rclone = rclone_path or os.environ.get("DEMO_TAKE_RCLONE") or shutil.which("rclone")
    remote_root = (remote or cloud_archive_remote(config)).strip()
    remote_take = _remote_take_path(remote_root, take_id)

    result: dict[str, Any] = {
        "schema": "demo_take_take_eviction_result_v0",
        "take_id": take_id,
        "root_path": str(root),
        "remote_take_path": remote_take,
        "dry_run": dry_run,
        "evict_only": evict_only,
        "dirs": [],
        "freed_bytes": 0,
        "status": "ready",
    }
    if not rclone:
        result["status"] = "failed"
        result["known_failures"] = ["rclone executable not found"]
        return result

    failures: list[str] = []
    freed_total = 0
    for name in heavy_dirs:
        local_sub = root / name
        if not local_sub.exists():
            continue
        preserved_prefixes = tuple(prefix for prefix in preserve_relative_prefixes if prefix.startswith(f"{name}/"))
        evictable_paths: list[Path] = []
        preserved_paths: list[Path] = []
        for path in sorted(local_sub.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = relative(root, path)
            if any(rel.startswith(prefix) for prefix in preserved_prefixes):
                preserved_paths.append(path)
            else:
                evictable_paths.append(path)
        sub_bytes = 0
        for path in evictable_paths:
            stat = _safe_stat(path)
            if stat is not None:
                sub_bytes += stat.st_size
        if sub_bytes <= 0:
            if preserved_paths:
                result["dirs"].append({
                    "dir": name,
                    "action": "preserved_only",
                    "preserved_file_count": len(preserved_paths),
                })
            continue
        remote_sub = remote_take.rstrip("/") + "/" + name
        dir_row: dict[str, Any] = {
            "dir": name,
            "local_bytes": sub_bytes,
            "preserved_file_count": len(preserved_paths),
            "preserved_prefixes": list(preserved_prefixes),
        }

        if dry_run:
            # Fast, offline preview: report the reclaimable bytes without touching
            # the network. The real run uploads + verifies custody before deleting.
            dir_row["action"] = "would_evict" if not evict_only else "would_evict_if_verified"
            freed_total += sub_bytes
            result["dirs"].append(dir_row)
            continue

        if not evict_only:
            upload = _run_rclone([
                rclone, "copy", str(local_sub), remote_sub,
                "--transfers", "4", "--checkers", "8",
            ])
            dir_row["upload_status"] = upload.get("status")
            if upload.get("status") != "pass":
                dir_row["action"] = "blocked_upload"
                dir_row["stderr_tail"] = upload.get("stderr_tail")
                failures.append(f"{name}: upload failed")
                result["dirs"].append(dir_row)
                continue

        verify = _run_rclone([rclone, "check", str(local_sub), remote_sub, "--one-way"])
        dir_row["verify_status"] = verify.get("status")
        if verify.get("status") != "pass":
            dir_row["action"] = "blocked_unverified"
            dir_row["stderr_tail"] = verify.get("stderr_tail")
            failures.append(f"{name}: cloud custody not verified; kept local")
            result["dirs"].append(dir_row)
            continue

        evicted = 0
        for path in evictable_paths:
            try:
                size = path.stat().st_size
                path.unlink()
                evicted += size
            except OSError as exc:
                failures.append(f"could not evict {relative(root, path)}: {exc}")
        _remove_empty_dirs(local_sub)
        dir_row["action"] = "evicted"
        dir_row["freed_bytes"] = evicted
        freed_total += evicted
        result["dirs"].append(dir_row)

    result["freed_bytes"] = freed_total
    if failures:
        result["known_failures"] = failures
        result["status"] = "partial" if freed_total > 0 else "blocked"
    elif freed_total == 0:
        result["status"] = "noop"

    if not dry_run and freed_total > 0:
        receipt = {
            "schema": "demo_take_local_eviction_receipt_v0",
            "take_id": take_id,
            "created_at": now_iso(),
            "remote_take_path": remote_take,
            "evicted_dirs": [row["dir"] for row in result["dirs"] if row.get("action") == "evicted"],
            "freed_bytes": freed_total,
            "restore_plan": {
                name: f"rclone copy {remote_take.rstrip('/')}/{name} <take_root>/{name}"
                for name in heavy_dirs
            },
            "known_failures": failures,
        }
        try:
            (root / "render").mkdir(parents=True, exist_ok=True)
            write_json(root / "render" / "local_eviction_receipt.json", receipt)
        except OSError as exc:
            result.setdefault("known_failures", []).append(f"could not write eviction receipt: {exc}")
    return result


def reclaim_space(
    takes_root: Path,
    *,
    target_free_bytes: int,
    remote: str | None = None,
    rclone_path: str | None = None,
    keep_recent: int = 1,
    dry_run: bool = False,
    evict_only: bool = False,
) -> dict[str, Any]:
    """Reclaim local disk by evicting cold takes to the cloud spillway, oldest
    first, until free space reaches the target or candidates run out. The newest
    `keep_recent` takes are protected so in-progress work is never evicted."""
    free_before = _free_disk_bytes(takes_root)
    result: dict[str, Any] = {
        "schema": "demo_take_reclaim_space_result_v0",
        "takes_root": str(takes_root),
        "target_free_bytes": target_free_bytes,
        "target_free_human": human_bytes(target_free_bytes),
        "free_before_bytes": free_before,
        "free_before_human": human_bytes(free_before or 0),
        "dry_run": dry_run,
        "evict_only": evict_only,
        "keep_recent": keep_recent,
        "takes": [],
    }
    if not takes_root.exists():
        result["status"] = "noop"
        result["free_after_bytes"] = free_before
        return result
    if free_before is not None and free_before >= target_free_bytes:
        result["status"] = "satisfied"
        result["free_after_bytes"] = free_before
        result["free_after_human"] = human_bytes(free_before)
        result["freed_bytes"] = 0
        return result

    takes = sorted(
        (d for d in takes_root.iterdir() if d.is_dir() and d.name.startswith("take_")),
        key=lambda d: d.stat().st_mtime,
    )
    protected = {t.name for t in takes[len(takes) - keep_recent:]} if keep_recent > 0 else set()
    evicted_total = 0
    for take in takes:
        free_now = _free_disk_bytes(takes_root)
        # In dry-run the disk never changes, so fold the previewed bytes into the
        # stop condition; in a real run free_now already reflects the evictions.
        projected_now = (free_now or 0) + (evicted_total if dry_run else 0)
        if free_now is not None and projected_now >= target_free_bytes:
            break
        if take.name in protected:
            result["takes"].append({"take_id": take.name, "action": "protected_recent"})
            continue
        if _tree_bytes(take) <= 0:
            continue
        eviction = evict_take_to_cloud(
            take,
            remote=remote,
            rclone_path=rclone_path,
            dry_run=dry_run,
            evict_only=evict_only,
        )
        result["takes"].append(eviction)
        evicted_total += int(eviction.get("freed_bytes") or 0)

    free_after = _free_disk_bytes(takes_root)
    result["free_after_bytes"] = free_after
    result["free_after_human"] = human_bytes(free_after or 0)
    # freed_bytes is the actual evicted byte total (summed from unlinked files),
    # not a disk-free delta, so concurrent writers cannot skew it.
    result["freed_bytes"] = evicted_total
    result["freed_human"] = human_bytes(max(0, evicted_total))
    if not dry_run and free_after is not None and free_after >= target_free_bytes:
        result["status"] = "satisfied"
    elif dry_run:
        result["status"] = "dry_run"
    elif evicted_total > 0:
        result["status"] = "partial"
    else:
        result["status"] = "noop"
    return result


def _fake_words(text: str, start: float, step: float = 0.18) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for index, token in enumerate(text.split()):
        word_start = start + (index * step)
        words.append({
            "word": token,
            "start": round(word_start, 3),
            "end": round(word_start + min(0.16, step), 3),
            "probability": 0.99,
        })
    return words


def fake_lifecycle(takes_root: Path, take_id: str | None = None) -> dict[str, Any]:
    """Create a deterministic local take package without macOS capture permissions."""
    resolved_take_id = take_id or "take_fake_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    root = takes_root / resolved_take_id
    if root.exists():
        raise FileExistsError(f"fake take already exists: {root}")
    for name in ["tracks", "frames", "transcript", "render", "review", "logs"]:
        (root / name).mkdir(parents=True, exist_ok=True)

    fixed_start = "2026-05-18T00:00:00+00:00"
    config = {
        "repo_root": str(REPO_ROOT),
        "ffmpeg_path": "fake-ffmpeg",
        "capture_backend": "fake",
        "screenshot_interval_seconds": 1,
        "marker_phrases": DEFAULT_MARKER_PHRASES,
        "screens": [
            {
                "index": 0,
                "id": "fake-display-1",
                "name": "Fake Main Display",
                "display_id": "fake-display-1",
                "display_name": "Fake Main Display",
                "display_bounds": {"x": 0, "y": 0, "width": 1440, "height": 900},
                "scale_factor": 2.0,
                "mapping_confidence": "fake",
            }
        ],
        "microphone": {"index": 0, "name": "Fake Microphone"},
        "webcam": None,
    }
    capture_target = _capture_target_from_config(config)
    if capture_target:
        config["capture_target"] = capture_target
    tracks = [
        {"id": "screen_0", "role": "screen", "device_name": "Fake Main Display", "device_index": 0, "relative_path": "tracks/screen_0.mp4"},
        {"id": "microphone_0", "role": "microphone", "device_name": "Fake Microphone", "device_index": 0, "relative_path": "tracks/microphone.m4a"},
    ]
    (root / "tracks" / "screen_0.mp4").write_bytes(b"fake screen track\n")
    (root / "tracks" / "microphone.m4a").write_bytes(b"fake microphone track\n")
    (root / "frames" / "screen_0_000001.jpg").write_bytes(b"fake frame\n")
    (root / "render" / "rough_cut.mp4").write_bytes(b"fake rough cut\n")

    markers = [
        {
            "id": "mark_fake_0001",
            "source": "api",
            "label": "calibration marker",
            "wall_t_seconds": 2.0,
            "video_t_seconds": 2.0,
            "created_at": "2026-05-18T00:00:02+00:00",
        },
        {
            "id": "mark_fake_0002",
            "source": "voice",
            "label": "Fake lifecycle",
            "wall_t_seconds": 6.0,
            "video_t_seconds": 5.0,
            "created_at": "2026-05-18T00:00:06+00:00",
        },
    ]
    pause_events = [
        {"kind": "pause", "at_iso": "2026-05-18T00:00:03+00:00"},
        {"kind": "resume", "at_iso": "2026-05-18T00:00:04+00:00"},
    ]
    session = {
        "schema": "demo_take_session_v0",
        "take_id": resolved_take_id,
        "created_at": fixed_start,
        "config": config,
        "tracks": tracks,
        "processes": [],
        "markers": markers,
        "pause_events": pause_events,
        "capture_target": capture_target,
        "known_failures": [],
    }
    write_json(root / "session.json", session)

    segment_0_text = "SLATE VIEW codemap MARK SHORT this is a fake calibration pass VIEW VERDICT MEDIUM VIEW DONE"
    segment_1_text = "SLATE VIEW navigation MARK CHAPTER Fake lifecycle MARK PRIVATE MARK RETAKE VIEW DONE"
    segment_0_words = _fake_words(segment_0_text, 0.0)
    segment_1_words = _fake_words(segment_1_text, 3.0)
    all_words = segment_0_words + segment_1_words
    transcript = {
        "schema": "demo_take_transcript_v0",
        "status": "ready",
        "created_at": fixed_start,
        "model": "fake",
        "language": "en",
        "source_track": "tracks/microphone.m4a",
        "duration_seconds": 6.0,
        "segments": [
            {"id": "seg_0000", "start": 0.0, "end": 2.9, "text": segment_0_text, "words": segment_0_words},
            {"id": "seg_0001", "start": 3.0, "end": 6.0, "text": segment_1_text, "words": segment_1_words},
        ],
        "words": all_words,
        "segment_count": 2,
        "word_count": len(all_words),
    }
    write_json(root / "transcript" / "transcript.json", transcript)
    (root / "transcript" / "transcript.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,900\n" + segment_0_text + "\n\n"
        "2\n00:00:03,000 --> 00:00:06,000\n" + segment_1_text + "\n",
        encoding="utf-8",
    )
    (root / "view_telemetry.jsonl").write_text(
        "\n".join([
            json.dumps({
                "at_iso": "2026-05-18T00:00:00+00:00",
                "route": "/station/codemap",
                "view_id": "codemap",
                "view_label": "Code Map",
                "pathname": "/station/codemap",
                "search": "",
                "hash": "",
                "wall_t_seconds": 0.0,
                "video_t_seconds": 0.0,
            }, sort_keys=True),
            json.dumps({
                "at_iso": "2026-05-18T00:00:04+00:00",
                "route": "/station/navigation",
                "view_id": "navigation",
                "view_label": "Navigation",
                "pathname": "/station/navigation",
                "search": "",
                "hash": "",
                "wall_t_seconds": 4.0,
                "video_t_seconds": 3.0,
            }, sort_keys=True),
        ])
        + "\n",
        encoding="utf-8",
    )
    (root / "attention_events.jsonl").write_text(
        "\n".join([
            json.dumps({
                "schema": "demo_take_attention_event_v0",
                "at_iso": "2026-05-18T00:00:00+00:00",
                "video_t_seconds": 0.0,
                "wall_t_seconds": 0.0,
                "monotonic_seconds": 0.0,
                "capture_target_id": (capture_target or {}).get("capture_target_id"),
                "display_id": "fake-display-1",
                "is_on_recorded_display": True,
                "confidence": "recorded_display_window",
                "public_safe_label": "Code Map",
                "frontmost_app": {
                    "localized_name": "Google Chrome",
                    "bundle_identifier": "com.google.Chrome",
                    "process_identifier": 101,
                },
                "window": {
                    "window_id": 11,
                    "owner_name": "Google Chrome",
                    "owner_pid": 101,
                    "public_safe_title": "AI Workflow Station - Code Map",
                    "recorded_display_overlap": 0.98,
                },
            }, sort_keys=True),
            json.dumps({
                "schema": "demo_take_attention_event_v0",
                "at_iso": "2026-05-18T00:00:04+00:00",
                "video_t_seconds": 3.0,
                "wall_t_seconds": 4.0,
                "monotonic_seconds": 4.0,
                "capture_target_id": (capture_target or {}).get("capture_target_id"),
                "display_id": "fake-display-1",
                "is_on_recorded_display": True,
                "confidence": "recorded_display_window",
                "public_safe_label": "Navigation",
                "frontmost_app": {
                    "localized_name": "Google Chrome",
                    "bundle_identifier": "com.google.Chrome",
                    "process_identifier": 101,
                },
                "window": {
                    "window_id": 11,
                    "owner_name": "Google Chrome",
                    "owner_pid": 101,
                    "public_safe_title": "AI Workflow Station - Navigation",
                    "recorded_display_overlap": 0.96,
                },
            }, sort_keys=True),
        ])
        + "\n",
        encoding="utf-8",
    )
    write_json(
        root / "visual_index.json",
        {
            "schema": "demo_take_visual_index_v0",
            "take_id": resolved_take_id,
            "created_at": fixed_start,
            "frames": [{"track_id": "screen_0", "timestamp_seconds": 0, "relative_path": "frames/screen_0_000001.jpg"}],
        },
    )
    build_view_timeline(root)
    build_attention_spans(root)
    enrich_transcript_with_views(root)
    enrich_transcript_with_attention(root)
    build_per_view_segments(root)
    build_intent_events(root)
    build_speech_blocks(root)
    write_edl(root, resolved_take_id, tracks, markers)
    write_active_timeline_projection(root, config, session, tracks, [])
    build_multimodal_index(root)
    write_timeline_sync_receipt(root)
    write_calibration_receipt(root)
    write_json(
        root / "render" / "render_receipt.json",
        {
            "schema": "demo_take_render_receipt_v0",
            "status": "ready",
            "output": "render/rough_cut.mp4",
            "known_failures": [],
        },
    )
    write_json(
        root / "manifest.json",
        manifest(
            resolved_take_id,
            root,
            "package_ready",
            config,
            tracks,
            [],
            markers=markers,
            pause_events=pause_events,
        ),
    )
    for stage in [
        "stop_ffmpeg",
        "sample_frames",
        "transcribe",
        "voice_scan",
        "view_timeline",
        "attention_spans",
        "per_view_segments",
        "intent_events",
        "speech_blocks",
        "edl",
        "multimodal_index",
        "rough_render",
        "manifest_ready",
        "package_ready",
    ]:
        append_postprocess_progress(root, stage, "pass", f"Fake lifecycle stage complete: {stage}")
    return {
        "schema": "demo_take_fake_lifecycle_result_v0",
        "status": "ready",
        "takeID": resolved_take_id,
        "rootPath": str(root),
        "sidecars": [
            "manifest.json",
            "session.json",
            "view_telemetry.jsonl",
            "view_timeline.json",
            "attention_events.jsonl",
            "attention_spans.json",
            "per_view_segments.json",
            "speech_blocks.json",
            "intent_events.json",
            "edl.json",
            "attention_editor_spans.json",
            "view_episodes.json",
            "ui_delta_index.json",
            "candidate_clips.json",
            "multimodal_index.json",
            "render/render_receipt.json",
            TIMELINE_SYNC_RECEIPT_RELATIVE_PATH,
        ],
    }


def import_video(source: Path, repo_root: Path, title: str | None = None) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"import source not found: {source}")
    extension = source.suffix.lower()
    if extension not in EXTERNAL_VIDEO_EXTENSIONS:
        raise ValueError(f"unsupported import video type: {extension or '<none>'}")

    resolved_title = clean_take_title(title, fallback=source.stem)
    take_id, root = unique_take_root(repo_root, prefix="take_import", title=resolved_title)
    for name in ["tracks", "frames", "transcript", "render", "review", "logs"]:
        (root / name).mkdir(parents=True, exist_ok=True)

    output = root / "render" / f"rough_cut{extension}"
    import_method = "hardlink_lossless_import"
    if not replace_with_hardlink(output, source):
        shutil.copy2(source, output)
        import_method = "copy"
    ffmpeg_path = shutil.which("ffmpeg") or "external-import"
    config = {
        "repo_root": str(repo_root),
        "ffmpeg_path": ffmpeg_path,
        "capture_backend": "external_import",
        "import_source_name": source.name,
        "imported_at": now_iso(),
        "screenshot_interval_seconds": 5,
        "marker_phrases": DEFAULT_MARKER_PHRASES,
        "screens": [],
        "microphone": None,
        "webcam": None,
        "take_title": resolved_title,
        "take_slug": take_title_slug(resolved_title),
    }
    tracks = [
        {
            "id": "external_video",
            "role": "external_video",
            "device_name": source.name,
            "device_index": -1,
            "relative_path": relative(root, output),
        }
    ]
    session = {
        "schema": "demo_take_session_v0",
        "take_id": take_id,
        "created_at": now_iso(),
        "config": config,
        "tracks": tracks,
        "processes": [],
        "markers": [],
        "pause_events": [],
        "known_failures": [],
    }
    write_json(root / "session.json", session)
    write_transcript_unavailable(root, "External video import has no extracted audio transcript yet.")
    write_json(
        root / "visual_index.json",
        {
            "schema": "demo_take_visual_index_v0",
            "take_id": take_id,
            "created_at": now_iso(),
            "frames": [],
        },
    )
    write_edl(root, take_id, tracks, [])
    write_json(
        root / "render" / "render_receipt.json",
        {
            "schema": "demo_take_render_receipt_v0",
            "status": "ready",
            "output": relative(root, output),
            "known_failures": [],
            "source": "external_import",
            "storage_profile": "efficient",
            "storage_optimization": {
                "method": import_method,
                "video_stream_action": "no_reencode",
            },
        },
    )
    write_json(
        root / "manifest.json",
        manifest(take_id, root, "review_ready", config, tracks, [], markers=[], pause_events=[]),
    )
    return {
        "schema": "demo_take_import_video_result_v0",
        "status": "ready",
        "takeID": take_id,
        "rootPath": str(root),
        "title": resolved_title,
        "asset": relative(root, output),
        "statusLines": [f"Imported {source.name} as {take_id}."],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    devices_parser = sub.add_parser("devices")
    devices_parser.add_argument("--ffmpeg", required=True)

    mic_test_parser = sub.add_parser("test-microphone")
    mic_test_parser.add_argument("--ffmpeg", required=True)
    mic_test_parser.add_argument("--index", type=int, required=True)
    mic_test_parser.add_argument("--name", default="")
    mic_test_parser.add_argument("--seconds", type=float, default=1.25)

    start_parser = sub.add_parser("start")
    start_parser.add_argument("--config-json", required=True)

    for name in ["pause", "resume", "stop", "stop-capture", "finalize", "postprocess"]:
        p = sub.add_parser(name)
        p.add_argument("--take-root", required=True)

    mark_parser = sub.add_parser("mark")
    mark_parser.add_argument("--take-root", required=True)
    mark_parser.add_argument(
        "--source",
        required=True,
        choices=["hotkey", "voice", "button", "api"],
    )
    mark_parser.add_argument("--label", default=None)

    list_markers_parser = sub.add_parser("list-markers")
    list_markers_parser.add_argument("--take-root", required=True)

    title_parser = sub.add_parser("set-title")
    title_parser.add_argument("--take-root", required=True)
    title_parser.add_argument("--title", default=None)

    import_parser = sub.add_parser("import-video")
    import_parser.add_argument("--source", required=True)
    import_parser.add_argument("--repo-root", default=str(REPO_ROOT))
    import_parser.add_argument("--title", default=None)

    compact_parser = sub.add_parser("compact-storage")
    compact_parser.add_argument("--take-root", required=True)
    compact_parser.add_argument("--prune-source-media", action="store_true")
    compact_parser.add_argument("--force", action="store_true")

    generated_cache_parser = sub.add_parser(
        "evict-generated-cache",
        help="Evict only rebuildable generated pause-splice cache files for one take",
    )
    generated_cache_parser.add_argument("--take-root", required=True)
    generated_cache_parser.add_argument("--dry-run", action="store_true")

    minimize_parser = sub.add_parser(
        "minimize-local-retention",
        help="Shrink one take to standard MP3 audio plus compact metadata; optionally drop cloud-hydratable review video",
    )
    minimize_parser.add_argument("--take-root", required=True)
    minimize_parser.add_argument("--drop-review-video", action="store_true")
    minimize_parser.add_argument("--dry-run", action="store_true")
    minimize_parser.add_argument("--no-standardize-review-audio", action="store_false", dest="standardize_review_audio")
    minimize_parser.set_defaults(standardize_review_audio=True)

    compact_all_parser = sub.add_parser(
        "compact-all-storage",
        help="Re-encode local take packages to 720p review proxies and optionally prune source media",
    )
    compact_all_parser.add_argument("--takes-root", default=None)
    compact_all_parser.add_argument("--prune-source-media", action="store_true")
    compact_all_parser.add_argument("--force", action="store_true")
    compact_all_parser.add_argument("--dry-run", action="store_true")
    compact_all_parser.add_argument("--limit", type=int, default=None)

    minimize_all_parser = sub.add_parser(
        "minimize-all-local-retention",
        help="Batch shrink take packages to standard MP3 audio plus compact metadata",
    )
    minimize_all_parser.add_argument("--takes-root", default=None)
    minimize_all_parser.add_argument("--drop-review-video", action="store_true")
    minimize_all_parser.add_argument("--dry-run", action="store_true")
    minimize_all_parser.add_argument("--keep-recent", type=int, default=0)
    minimize_all_parser.add_argument("--limit", type=int, default=None)
    minimize_all_parser.add_argument("--no-standardize-review-audio", action="store_false", dest="standardize_review_audio")
    minimize_all_parser.set_defaults(standardize_review_audio=True)

    storage_receipt_parser = sub.add_parser("storage-receipt")
    storage_receipt_parser.add_argument("--take-root", required=True)

    calibration_receipt_parser = sub.add_parser("calibration-receipt")
    calibration_receipt_parser.add_argument("--take-root", required=True)

    timeline_sync_receipt_parser = sub.add_parser("timeline-sync-receipt")
    timeline_sync_receipt_parser.add_argument("--take-root", required=True)

    storage_status_parser = sub.add_parser("storage-status")
    storage_status_parser.add_argument("--take-root", required=True)

    export_parser = sub.add_parser("export-video")
    export_parser.add_argument("--take-root", required=True)
    export_parser.add_argument("--destination-dir", default=None)

    render_clip_parser = sub.add_parser("render-clip")
    render_clip_parser.add_argument("--take-root", required=True)
    render_clip_parser.add_argument("--clip-id", required=True)
    render_clip_parser.add_argument("--quality", choices=["proxy"], default="proxy")

    render_final_parser = sub.add_parser("render-final", help="Compile a final video from an editorial edit plan")
    render_final_parser.add_argument("--take-root", required=True)
    render_final_parser.add_argument("--edit-plan", default=None, help="Path to an editorial edit plan; default materializes one from candidate_clips.json")
    render_final_parser.add_argument("--quality", choices=sorted(FINAL_RENDER_PROFILES), default="proxy")
    render_final_parser.add_argument("--hydrate-policy", choices=["required", "if_needed", "never"], default="if_needed")
    render_final_parser.add_argument("--allow-stale", action="store_true", help="Render even if candidate_clips changed since the plan was built")
    render_final_parser.add_argument("--allow-proxy-fallback", action="store_true", help="For raw-required profiles, render an honestly-labelled proxy_degraded master when raw is unavailable")
    render_final_parser.add_argument("--burn-captions", action="store_true", help="Burn transcript captions onto a captioned review variant beside the clean final")
    render_final_parser.add_argument("--caption-style", default=None, help="Override ffmpeg subtitles force_style for burned final captions")

    staleness_parser = sub.add_parser("audit-staleness", help="Classify derived projections fresh/stale against their inputs")
    staleness_parser.add_argument("--take-root", required=True)

    archive_parser = sub.add_parser("archive-originals")
    archive_parser.add_argument("--take-root", required=True)
    archive_parser.add_argument("--remote", default=None)
    archive_parser.add_argument("--local-retention", choices=sorted(CLOUD_ARCHIVE_LOCAL_RETENTIONS), default=None)
    archive_parser.add_argument("--rclone", default=None)
    archive_parser.add_argument("--force", action="store_true")
    archive_parser.add_argument("--transport", choices=sorted(ARCHIVE_TRANSPORT_MODES), default=None)

    reclaim_parser = sub.add_parser(
        "reclaim-space",
        help="Evict cold takes to the cloud spillway until local free disk reaches a target",
    )
    reclaim_parser.add_argument("--takes-root", default=None)
    reclaim_parser.add_argument("--target-free-gib", type=float, default=None)
    reclaim_parser.add_argument("--remote", default=None)
    reclaim_parser.add_argument("--rclone", default=None)
    reclaim_parser.add_argument("--keep-recent", type=int, default=1)
    reclaim_parser.add_argument("--dry-run", action="store_true")
    reclaim_parser.add_argument("--evict-only", action="store_true")

    restore_drill_parser = sub.add_parser("restore-drill")
    restore_drill_parser.add_argument("--take-root", required=True)
    restore_drill_parser.add_argument("--restore-root", default=None)
    restore_drill_parser.add_argument("--rclone", default=None)
    restore_drill_parser.add_argument("--keep-restore-root", action="store_true")

    setup_parser = sub.add_parser("transcribe-setup")
    setup_parser.add_argument("--install-brew", action="store_true")
    setup_parser.add_argument("--download-model", action="store_true")
    setup_parser.add_argument("--model", default=DEFAULT_TRANSCRIBE_MODEL)
    setup_parser.add_argument("--language", default="en")
    setup_parser.add_argument("--model-dir", type=Path, default=None)
    setup_parser.add_argument("--force-model", action="store_true")

    smoke_parser = sub.add_parser("transcribe-smoke")
    smoke_parser.add_argument("--provider", choices=sorted(TRANSCRIBE_PROVIDERS), default="whisper_cpp")
    smoke_parser.add_argument("--model", default=DEFAULT_TRANSCRIBE_MODEL)
    smoke_parser.add_argument("--language", default="en")
    smoke_parser.add_argument("--ffmpeg", default=None)
    smoke_parser.add_argument("--text", default=None)
    smoke_parser.add_argument("--whisper-cpp-binary", default=None)
    smoke_parser.add_argument("--whisper-cpp-model", default=None)
    smoke_parser.add_argument("--audio-format", choices=["mp3", "m4a", "wav"], default="mp3")

    transcribe_parser = sub.add_parser("transcribe")
    transcribe_parser.add_argument("--take-root", required=True)
    transcribe_parser.add_argument("--binary", help="Override transcribe binary path")
    transcribe_parser.add_argument("--model", help="Override model name")
    transcribe_parser.add_argument("--language", help="Force language code (e.g. en)")
    transcribe_parser.add_argument("--provider", choices=sorted(TRANSCRIBE_PROVIDERS), help="Transcription provider: auto, whisperkit, or whisper_cpp")
    transcribe_parser.add_argument("--whisper-cpp-binary", help="Override whisper.cpp whisper-cli path")
    transcribe_parser.add_argument("--whisper-cpp-model", help="Override whisper.cpp ggml model path")

    voice_scan_parser = sub.add_parser("voice-scan")
    voice_scan_parser.add_argument("--take-root", required=True)
    voice_scan_parser.add_argument(
        "--phrase",
        action="append",
        help="Override marker phrases (may be passed multiple times)",
    )
    voice_scan_parser.add_argument(
        "--debounce-seconds",
        type=float,
        default=2.0,
        help="Minimum seconds between voice markers",
    )

    view_timeline_parser = sub.add_parser("view-timeline")
    view_timeline_parser.add_argument("--take-root", required=True)

    active_timeline_parser = sub.add_parser("active-timeline")
    active_timeline_parser.add_argument("--take-root", required=True)

    attention_parser = sub.add_parser("attention-spans")
    attention_parser.add_argument("--take-root", required=True)

    enrich_parser = sub.add_parser("enrich-transcript")
    enrich_parser.add_argument("--take-root", required=True)

    per_view_parser = sub.add_parser("per-view-segments")
    per_view_parser.add_argument("--take-root", required=True)

    intent_parser = sub.add_parser("intent-events")
    intent_parser.add_argument("--take-root", required=True)

    speech_parser = sub.add_parser("speech-blocks")
    speech_parser.add_argument("--take-root", required=True)
    speech_parser.add_argument("--pause-gap-seconds", type=float, default=DEFAULT_SPEECH_BLOCK_PAUSE_SECONDS)
    speech_parser.add_argument("--max-block-seconds", type=float, default=DEFAULT_SPEECH_BLOCK_MAX_SECONDS)

    semantic_parser = sub.add_parser("semantic-proxy")
    semantic_parser.add_argument("--take-root", required=True)

    schedule_parser = sub.add_parser("schedule-state")
    schedule_parser.add_argument("--route", default=None)
    schedule_parser.add_argument("--capture-slug", default=None)
    schedule_parser.add_argument("--step-id", default=None)
    schedule_parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    schedule_parser.add_argument("--take-root", default=None)
    schedule_parser.add_argument(
        "--emit-progress",
        action="store_true",
        help="Append schedule_progress.jsonl in --take-root when the step changes",
    )

    fake_parser = sub.add_parser("fake-lifecycle")
    fake_parser.add_argument("--takes-root", required=True)
    fake_parser.add_argument("--take-id", default=None)

    args = parser.parse_args()
    try:
        if args.command == "devices":
            print(json.dumps(run_ffmpeg_devices(args.ffmpeg)))
        elif args.command == "test-microphone":
            print(json.dumps(test_microphone(
                args.ffmpeg,
                args.index,
                args.name,
                seconds=args.seconds,
            )))
        elif args.command == "start":
            print(json.dumps(start(json.loads(args.config_json))))
        elif args.command == "pause":
            print(json.dumps(signal_session(Path(args.take_root), signal.SIGSTOP)))
        elif args.command == "resume":
            print(json.dumps(signal_session(Path(args.take_root), signal.SIGCONT)))
        elif args.command == "stop":
            print(json.dumps(stop(Path(args.take_root))))
        elif args.command == "stop-capture":
            print(json.dumps(stop_capture_only(Path(args.take_root))))
        elif args.command == "finalize":
            root = Path(args.take_root)
            print(json.dumps(run_take_operation(root, "finalize", lambda: finalize_capture(root))))
        elif args.command == "postprocess":
            root = Path(args.take_root)
            print(json.dumps(run_take_operation(root, "postprocess", lambda: postprocess(root))))
        elif args.command == "mark":
            print(json.dumps(mark(Path(args.take_root), args.source, args.label)))
        elif args.command == "list-markers":
            print(json.dumps(list_markers(Path(args.take_root))))
        elif args.command == "set-title":
            print(json.dumps(set_take_title(Path(args.take_root), args.title)))
        elif args.command == "import-video":
            print(json.dumps(import_video(Path(args.source), Path(args.repo_root), title=args.title)))
        elif args.command == "compact-storage":
            print(json.dumps(compact_storage(
                Path(args.take_root),
                prune_source_media=args.prune_source_media,
                force=args.force,
            )))
        elif args.command == "evict-generated-cache":
            print(json.dumps(evict_generated_cache(
                Path(args.take_root),
                dry_run=args.dry_run,
            )))
        elif args.command == "minimize-local-retention":
            print(json.dumps(minimize_local_retention(
                Path(args.take_root),
                drop_review_video=args.drop_review_video,
                dry_run=args.dry_run,
                standardize_review_audio=args.standardize_review_audio,
            )))
        elif args.command == "compact-all-storage":
            takes_root = (
                Path(args.takes_root)
                if args.takes_root
                else REPO_ROOT / "state" / "dissemination" / "demo_takes"
            )
            print(json.dumps(compact_all_storage(
                takes_root,
                prune_source_media=args.prune_source_media,
                force=args.force,
                dry_run=args.dry_run,
                limit=args.limit,
            )))
        elif args.command == "minimize-all-local-retention":
            takes_root = (
                Path(args.takes_root)
                if args.takes_root
                else REPO_ROOT / "state" / "dissemination" / "demo_takes"
            )
            print(json.dumps(minimize_all_local_retention(
                takes_root,
                drop_review_video=args.drop_review_video,
                dry_run=args.dry_run,
                standardize_review_audio=args.standardize_review_audio,
                keep_recent=args.keep_recent,
                limit=args.limit,
            )))
        elif args.command == "storage-receipt":
            root = Path(args.take_root)
            session = _read_json_dict(root / "session.json")
            config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
            print(json.dumps(write_local_storage_receipt(root, config, session)))
        elif args.command == "calibration-receipt":
            print(json.dumps(write_calibration_receipt(Path(args.take_root))))
        elif args.command == "timeline-sync-receipt":
            print(json.dumps(write_timeline_sync_receipt(Path(args.take_root))))
        elif args.command == "storage-status":
            print(json.dumps(storage_status(Path(args.take_root))))
        elif args.command == "export-video":
            print(json.dumps(export_video(
                Path(args.take_root),
                destination_dir=Path(args.destination_dir) if args.destination_dir else None,
            )))
        elif args.command == "render-clip":
            print(json.dumps(render_candidate_clip(
                Path(args.take_root),
                args.clip_id,
                quality=args.quality,
            )))
        elif args.command == "render-final":
            print(json.dumps(render_final_cut(
                Path(args.take_root),
                edit_plan_path=Path(args.edit_plan) if args.edit_plan else None,
                quality=args.quality,
                hydrate_policy=args.hydrate_policy,
                allow_stale=args.allow_stale,
                allow_proxy_fallback=args.allow_proxy_fallback,
                burn_captions=args.burn_captions,
                caption_style=args.caption_style,
            )))
        elif args.command == "audit-staleness":
            print(json.dumps(audit_take_staleness(Path(args.take_root))))
        elif args.command == "archive-originals":
            print(json.dumps(archive_originals(
                Path(args.take_root),
                remote=args.remote,
                local_retention=args.local_retention,
                rclone_path=args.rclone,
                force=args.force,
                transport_mode=args.transport,
            )))
        elif args.command == "reclaim-space":
            takes_root = (
                Path(args.takes_root)
                if args.takes_root
                else REPO_ROOT / "state" / "dissemination" / "demo_takes"
            )
            target_free_bytes = (
                int(args.target_free_gib * 1024 * 1024 * 1024)
                if args.target_free_gib is not None
                else LOCAL_STORAGE_SOFT_FLOOR_BYTES
            )
            print(json.dumps(reclaim_space(
                takes_root,
                target_free_bytes=target_free_bytes,
                remote=args.remote,
                rclone_path=args.rclone,
                keep_recent=args.keep_recent,
                dry_run=args.dry_run,
                evict_only=args.evict_only,
            )))
        elif args.command == "restore-drill":
            print(json.dumps(restore_drill(
                Path(args.take_root),
                restore_root=Path(args.restore_root) if args.restore_root else None,
                rclone_path=args.rclone,
                keep_restore_root=args.keep_restore_root,
            )))
        elif args.command == "transcribe-setup":
            print(json.dumps(setup_whisper_cpp(
                install_brew=args.install_brew,
                download_model=args.download_model,
                model=args.model,
                language=args.language,
                model_dir=args.model_dir,
                force_model=args.force_model,
            )))
        elif args.command == "transcribe-smoke":
            print(json.dumps(transcribe_smoke(
                provider=args.provider,
                model=args.model,
                language=args.language,
                ffmpeg_path=args.ffmpeg,
                text=args.text,
                whisper_cpp_binary=args.whisper_cpp_binary,
                whisper_cpp_model=args.whisper_cpp_model,
                audio_format=args.audio_format,
            )))
        elif args.command == "transcribe":
            root = Path(args.take_root)
            print(json.dumps(run_take_operation(
                root,
                "transcribe",
                lambda: transcribe_existing(
                    root,
                    binary_override=args.binary,
                    model_override=args.model,
                    language_override=args.language,
                    provider_override=args.provider,
                    whisper_cpp_binary_override=args.whisper_cpp_binary,
                    whisper_cpp_model_override=args.whisper_cpp_model,
                ),
            )))
        elif args.command == "voice-scan":
            result = voice_scan(
                Path(args.take_root),
                phrases_override=args.phrase,
                debounce_seconds=args.debounce_seconds,
            )
            if result.get("status") == "ready" and result.get("matched_count", 0):
                session = json.loads((Path(args.take_root) / "session.json").read_text(encoding="utf-8"))
                tracks = session.get("tracks", [])
                markers = session.get("markers", [])
                write_edl(Path(args.take_root), session["take_id"], tracks, markers)
            print(json.dumps(result))
        elif args.command == "view-timeline":
            print(json.dumps(build_view_timeline(Path(args.take_root))))
        elif args.command == "active-timeline":
            root = Path(args.take_root)
            session = json.loads((root / "session.json").read_text(encoding="utf-8"))
            config = dict(session.get("config", {}))
            tracks = session.get("tracks") if isinstance(session.get("tracks"), list) else []
            failures = session.get("known_failures") if isinstance(session.get("known_failures"), list) else []
            timeline = write_active_timeline_projection(root, config, session, tracks, failures)
            if "repo_root" in config and "ffmpeg_path" in config and "screenshot_interval_seconds" in config:
                existing_manifest = _read_json_dict(root / "manifest.json")
                write_json(
                    root / "manifest.json",
                    manifest(
                        session.get("take_id", root.name),
                        root,
                        str(existing_manifest.get("recording_state") or "review_ready"),
                        config,
                        tracks,
                        failures,
                        markers=session.get("markers") if isinstance(session.get("markers"), list) else [],
                        pause_events=session.get("pause_events") if isinstance(session.get("pause_events"), list) else [],
                        media_segments=session.get("media_segments") if isinstance(session.get("media_segments"), list) else [],
                    ),
                )
            print(json.dumps(timeline))
        elif args.command == "attention-spans":
            print(json.dumps(build_attention_spans(Path(args.take_root))))
        elif args.command == "enrich-transcript":
            print(json.dumps(enrich_transcript_with_views(Path(args.take_root))))
        elif args.command == "per-view-segments":
            print(json.dumps(build_per_view_segments(Path(args.take_root))))
        elif args.command == "intent-events":
            print(json.dumps(build_intent_events(Path(args.take_root))))
        elif args.command == "speech-blocks":
            print(json.dumps(build_speech_blocks(
                Path(args.take_root),
                pause_gap_seconds=args.pause_gap_seconds,
                max_block_seconds=args.max_block_seconds,
            )))
        elif args.command == "semantic-proxy":
            print(json.dumps(build_semantic_proxy(Path(args.take_root))))
        elif args.command == "schedule-state":
            print(json.dumps(schedule_state(
                route=args.route,
                capture_slug=args.capture_slug,
                step_id=args.step_id,
                backend_url=args.backend_url,
                take_root=Path(args.take_root) if args.take_root else None,
                emit_progress=args.emit_progress,
            )))
        elif args.command == "fake-lifecycle":
            print(json.dumps(fake_lifecycle(Path(args.takes_root), take_id=args.take_id)))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
