#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
DEFAULT_TRANSCRIBE_MODEL = "openai_whisper-base"
DEFAULT_TRANSCRIBE_PROVIDER = "auto"
DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS = 180
TRANSCRIBE_PROVIDERS = {"auto", "whisperkit", "whisper_cpp"}
WHISPER_CPP_MODEL_DIR = REPO_ROOT / "state" / "whisper"
WHISPER_CPP_MODEL_URL_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
EXTERNAL_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
DEFAULT_STORAGE_PROFILE = "efficient"
STORAGE_PROFILES = {"efficient", "source"}
DEFAULT_RECORDING_QUALITY = "source"
RECORDING_QUALITY_PROFILES = {"efficient", "source"}
RECORDING_QUALITY_SETTINGS = {
    "efficient": {
        "screen_bitrate": "6000k",
        "webcam_bitrate": "3500k",
        "audio_bitrate": "192k",
        "audio_codec": "aac",
        "audio_extension": ".m4a",
        "audio_sample_rate": "48000",
    },
    "source": {
        "screen_bitrate": "24000k",
        "webcam_bitrate": "8000k",
        "audio_bitrate": "256k",
        "audio_codec": "pcm_s24le",
        "audio_extension": ".wav",
        "audio_sample_rate": "48000",
    },
}
DEFAULT_FRAME_THUMBNAIL_WIDTH = 1280
DEFAULT_FRAME_JPEG_QUALITY = 5
EXPORTS_RELATIVE_ROOT = Path("state") / "dissemination" / "demo_exports"
DEFAULT_CLOUD_ARCHIVE_REMOTE = "memeister_drive:aiw-cold-spillway/demo_takes"
CLOUD_ARCHIVE_LOCAL_RETENTIONS = {"full", "proxy"}
# Source fidelity is a custody class, not a local-retention class: once a verified
# cloud archive exists, the default local footprint is the review proxy.
DEFAULT_CLOUD_ARCHIVE_LOCAL_RETENTION = "proxy"
LOCAL_STORAGE_HARD_FLOOR_BYTES = 10 * 1024 * 1024 * 1024
LOCAL_STORAGE_SOFT_FLOOR_BYTES = 35 * 1024 * 1024 * 1024
LOCAL_STORAGE_TARGET_FREE_BYTES = 50 * 1024 * 1024 * 1024
STORAGE_GOVERNOR_STATES = {
    "cloud_verified_proxy_local",
    "cloud_pending_raw_local",
    "cloud_failed_raw_local_blocked",
    "manual_source_retention",
}
RESTORE_DRILL_STATUSES = {"pass", "warn", "fail", "missing"}
RESTORE_DRILL_RECEIPT_RELATIVE_PATH = "render/restore_drill_receipt.json"
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


def _config_int(config: dict[str, Any], key: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(config.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def storage_profile(config: dict[str, Any]) -> str:
    profile = str(config.get("storage_profile", DEFAULT_STORAGE_PROFILE)).strip().lower()
    return profile if profile in STORAGE_PROFILES else DEFAULT_STORAGE_PROFILE


def recording_quality(config: dict[str, Any]) -> str:
    quality = str(config.get("recording_quality", DEFAULT_RECORDING_QUALITY)).strip().lower()
    return quality if quality in RECORDING_QUALITY_PROFILES else DEFAULT_RECORDING_QUALITY


def recording_quality_settings(config: dict[str, Any]) -> dict[str, str]:
    return RECORDING_QUALITY_SETTINGS[recording_quality(config)]


def config_bool(config: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


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
    return config_bool(config, "cloud_archive_after_stop", False)


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


def estimated_spool_bytes_per_second(config: Mapping[str, Any]) -> float:
    settings = recording_quality_settings(dict(config))
    screen_count = max(1, len(config.get("screens") or [])) if isinstance(config.get("screens"), list) else 1
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
    try:
        free_bytes: int | None = shutil.disk_usage(spool_root).free
    except OSError:
        free_bytes = None
    bytes_per_second = estimated_spool_bytes_per_second(config)
    payload: dict[str, Any] = {
        "schema": "demo_take_storage_governor_preflight_v0",
        "free_bytes": free_bytes,
        "hard_floor_bytes": LOCAL_STORAGE_HARD_FLOOR_BYTES,
        "soft_floor_bytes": LOCAL_STORAGE_SOFT_FLOOR_BYTES,
        "estimated_spool_bytes_per_second": int(bytes_per_second),
        "estimated_spool_bytes_per_minute": int(bytes_per_second * 60),
    }
    if free_bytes is None:
        payload["status"] = "warn"
        payload["operator_line"] = "Local spool budget unknown: free disk space could not be read."
        return payload
    budget_line = f"Local spool budget: about {human_bytes(int(bytes_per_second * 60))}/minute at this quality"
    if bytes_per_second > 0:
        minutes_to_hard_floor = max(0.0, (free_bytes - LOCAL_STORAGE_HARD_FLOOR_BYTES) / bytes_per_second / 60.0)
        payload["minutes_until_hard_floor"] = round(minutes_to_hard_floor, 1)
        budget_line += f"; roughly {_human_minutes(minutes_to_hard_floor)} of recording before the local disk floor"
    if free_bytes < LOCAL_STORAGE_HARD_FLOOR_BYTES:
        payload["status"] = "fail"
        payload["known_failures"] = [
            f"free disk {human_bytes(free_bytes)} is below the {human_bytes(LOCAL_STORAGE_HARD_FLOOR_BYTES)} hard floor for a new local spool"
        ]
        payload["operator_line"] = (
            f"Recording blocked: only {human_bytes(free_bytes)} free locally, below the "
            f"{human_bytes(LOCAL_STORAGE_HARD_FLOOR_BYTES)} floor. Reclaim space by archiving "
            "cold takes to the cloud and evicting them locally: "
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
    screens = config.get("screens", [])
    if not isinstance(screens, list) or not screens:
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


def human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(0, value))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024


def unique_take_root(repo_root: Path, *, prefix: str, title: Any = None) -> tuple[str, Path]:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = take_title_slug(title)
    base_id = f"{prefix}_{stamp}" + (f"_{slug}" if slug else "")
    takes_root = repo_root / "state" / "dissemination" / "demo_takes"
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
    screens = [] if native_capture else [screen for screen in config.get("screens", []) if isinstance(screen, Mapping)]
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

    review_video = maybe("render/rough_cut.mp4") or first_existing_track({"external_video", "screen", "webcam"})
    timeline_projection = _read_json_dict(root / "render" / "timeline_projection_receipt.json")

    payload = {
        "schema": "demo_take_manifest_v0",
        "take_id": take_id,
        "created_at": now_iso(),
        "recording_state": state,
        "repo_root": config["repo_root"],
        "output_root": str(Path(config["repo_root"]) / "state" / "dissemination" / "demo_takes"),
        "ffmpeg_path": config["ffmpeg_path"],
        "screenshot_interval_seconds": config["screenshot_interval_seconds"],
        "storage_profile": storage_profile(config),
        "recording_quality": recording_quality(config),
        "marker_phrases": config.get("marker_phrases", DEFAULT_MARKER_PHRASES),
        "sources": {
            "screens": config.get("screens", []),
            "microphone": config.get("microphone"),
            "webcam": config.get("webcam"),
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
        "schedule_progress": maybe("schedule_progress.jsonl"),
        "intent_events": maybe("intent_events.json"),
        "view_episodes": maybe("view_episodes.json"),
        "ui_delta_index": maybe("ui_delta_index.json"),
        "candidate_clips": maybe("candidate_clips.json"),
        "multimodal_index": maybe("multimodal_index.json"),
        "render_receipt": maybe("render/render_receipt.json"),
        "clip_render_index": maybe("render/clips/index.json"),
        "media_timeline_receipt": maybe("render/media_timeline_receipt.json"),
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


def launch_ffmpeg(ffmpeg: str, args: list[str], log_path: Path) -> subprocess.Popen[Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("ab")
    return subprocess.Popen(
        [ffmpeg, *args],
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def start(config: dict[str, Any]) -> dict[str, Any]:
    repo_root = Path(config["repo_root"])
    config["storage_profile"] = storage_profile(config)
    config["recording_quality"] = recording_quality(config)
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
    governor_preflight = storage_governor_preflight(config, spool_root=repo_root)
    config["storage_governor_preflight"] = governor_preflight
    if governor_preflight.get("status") == "fail":
        raise RuntimeError(
            governor_preflight.get("operator_line")
            or "Storage governor preflight failed: local disk is below the recording floor."
        )
    take_id, root = unique_take_root(repo_root, prefix="take", title=title)
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
                "-c:v",
                "h264_videotoolbox",
                "-b:v",
                quality_settings["screen_bitrate"],
                "-pix_fmt",
                "yuv420p",
                str(output),
            ],
            logs_dir / f"{role}.log",
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
        processes.append({"id": role, "pid": proc.pid, "log": relative(root, logs_dir / f"{role}.log")})

    webcam = config.get("webcam")
    if webcam:
        role = f"webcam_{webcam['index']}"
        output = tracks_dir / "webcam.mp4"
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
                "-c:v",
                "h264_videotoolbox",
                "-b:v",
                quality_settings["webcam_bitrate"],
                "-pix_fmt",
                "yuv420p",
                str(output),
            ],
            logs_dir / f"{role}.log",
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
        processes.append({"id": role, "pid": proc.pid, "log": relative(root, logs_dir / f"{role}.log")})

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
                logs_dir / f"{role}.log",
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
            processes.append({"id": role, "pid": proc.pid, "log": relative(root, logs_dir / f"{role}.log")})

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


def signal_capture_process(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return
    except OSError:
        os.kill(pid, sig)


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
_INTENT_CONTROL_SOURCE = (
    r"(?:slate\s+(?:block|view|short|long|retake)|"
    r"mark\s+(?:good|retake|cut\s+this|chapter|note|private|redact|do\s+not\s+publish|"
    r"confusing|too\s+much|needs\s+(?:example|visual)|short(?:\s+only)?|long(?:\s+only)?|"
    r"skip\s+view|uncertain)|(?:view|you)\s+(?:verdict|done))"
)
_INTENT_PAYLOAD_BOUNDARY_RE = re.compile(rf"\b{_INTENT_CONTROL_SOURCE}\b", re.IGNORECASE)
_INTENT_LABEL_CAPTURE = rf"(?P<label>.+?)(?=\s*(?:[.?!;\n]|\b{_INTENT_CONTROL_SOURCE}\b|$))"
_INTENT_LABEL_AFTER_SPACE = rf"\s+(?!{_INTENT_CONTROL_SOURCE}\b){_INTENT_LABEL_CAPTURE}"
_INTENT_RULES: list[dict[str, Any]] = [
    {"kind": "slate_block", "command": "SLATE BLOCK", "pattern": re.compile(rf"\bslate\s+block{_INTENT_LABEL_AFTER_SPACE}", re.IGNORECASE)},
    {"kind": "slate_view", "command": "SLATE VIEW", "pattern": re.compile(rf"\b(?:slate\s+view|you(?!\s+(?:verdict|done)\b)){_INTENT_LABEL_AFTER_SPACE}", re.IGNORECASE)},
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


def _normalize_word(text: str) -> str:
    return _WORD_NORMALIZE_RE.sub("", text.lower())


def _clean_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


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
    for segment in transcript.get("segments", []):
        if not isinstance(segment, dict):
            continue
        text = _clean_text(segment.get("text", ""))
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
    tracks = prepare_segment_tracks(root, config, session, failures)
    session["tracks"] = tracks
    result = transcribe_track(root, config, tracks, failures)
    write_media_timeline_receipt(root, config, session, tracks, failures)
    write_active_timeline_projection(root, config, session, tracks, failures)
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


def _is_recomputed_review_failure(message: Any) -> bool:
    text = str(message)
    return (
        text == "Rough render failed; see logs/rough_render.log."
        or text.startswith("Cannot build MP3 review audio because ")
        or text == "MP3 review audio export failed; see logs/review_audio.log."
        or "screen-only review video will be used" in text
        or text.startswith("Paused recording segment splice failed for ")
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
    ffmpeg = config.get("ffmpeg_path")
    if ffmpeg:
        sibling = Path(str(ffmpeg)).with_name("ffprobe")
        if sibling.exists() and os.access(str(sibling), os.X_OK):
            return str(sibling)
    return shutil.which("ffprobe")


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
    mic_track = segment.get("microphone_track")
    mic_path = _segment_track_path(root, mic_track if isinstance(mic_track, Mapping) else None)
    if mic_path:
        mic_duration = probe_media_duration_seconds(config, mic_path)
        if mic_duration:
            return mic_duration, "microphone_duration"
    wall_duration = _segment_wall_duration_seconds(segment)
    if wall_duration:
        return wall_duration, "segment_wall_clock"
    screen_tracks = segment.get("screen_tracks", []) or []
    for track in screen_tracks:
        screen_path = _segment_track_path(root, track if isinstance(track, Mapping) else None)
        if screen_path:
            screen_duration = probe_media_duration_seconds(config, screen_path)
            if screen_duration:
                return screen_duration, "screen_duration"
    return None, "unknown"


def _video_normalization_filter(raw_duration: float | None, expected_duration: float) -> tuple[str, dict[str, Any]]:
    scale = 1.0
    if raw_duration and raw_duration > 0 and raw_duration < expected_duration * 0.80:
        scale = expected_duration / raw_duration
    scaled_duration = (raw_duration or 0.0) * scale
    pad_duration = max(0.0, expected_duration - scaled_duration)
    filter_text = (
        f"setpts=(PTS-STARTPTS)*{scale:.8f},"
        "fps=30,"
        f"tpad=stop_mode=clone:stop_duration={pad_duration:.6f},"
        f"trim=duration={expected_duration:.6f},"
        "setpts=PTS-STARTPTS,"
        "format=yuv420p"
    )
    return filter_text, {
        "raw_duration_seconds": raw_duration,
        "expected_duration_seconds": expected_duration,
        "pts_scale": scale,
        "pad_duration_seconds": pad_duration,
    }


def _normalize_video_segment(
    root: Path,
    config: dict[str, Any],
    source: Path,
    output: Path,
    *,
    expected_duration: float,
    raw_duration: float | None,
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
    video_filter, receipt = _video_normalization_filter(raw_duration, expected_duration)
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
        f"{expected_duration:.6f}",
        "-c:v",
        "mpeg4",
        "-q:v",
        "3",
        str(output_tmp),
    ]
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"video segment normalization unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status == 0 and output_tmp.exists():
        os.replace(output_tmp, output)
        normalized_duration = probe_media_duration_seconds(config, output)
        return {
            **receipt,
            "source": relative(root, source),
            "output": relative(root, output),
            "normalized_duration_seconds": normalized_duration,
        }

    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass
    failures.append(f"Video segment normalization failed for {source.name}; see logs/{log_name}.")
    return None


def _concat_timeline_video_segments(
    root: Path,
    config: dict[str, Any],
    entries: list[tuple[dict[str, Any], Path, float, str]],
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
    for index, (_track, path, expected_duration, expected_source) in enumerate(entries, start=1):
        raw_duration = probe_media_duration_seconds(config, path)
        part_output = parts_dir / f"screen_{suffix}_{index:04d}.mp4"
        result = _normalize_video_segment(
            root,
            config,
            path,
            part_output,
            expected_duration=expected_duration,
            raw_duration=raw_duration,
            log_name=f"normalize_screen_{suffix}_{index:04d}.log",
            failures=failures,
        )
        if result is None:
            return None
        result["expected_duration_source"] = expected_source
        normalized_paths.append(part_output)
        normalizations.append(result)

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
            log_name=f"splice_screen_{suffix}.log",
            failures=failures,
        )
    if not concat_ready:
        return None
    return {
        "normalizations": normalizations,
        "expected_duration_seconds": round(sum(item[2] for item in entries), 3),
        "output_duration_seconds": probe_media_duration_seconds(config, output),
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

    screen_groups: dict[str, list[tuple[dict[str, Any], Path, float, str]]] = {}
    for segment in segments:
        expected_duration, expected_source = _segment_expected_duration_seconds(root, config, segment)
        if not expected_duration:
            continue
        for track in segment.get("screen_tracks", []) or []:
            if not isinstance(track, Mapping):
                continue
            path = _segment_track_path(root, track)
            if not path:
                continue
            key = str(track.get("device_index") if track.get("device_index") is not None else track.get("id") or "screen")
            screen_groups.setdefault(key, []).append((dict(track), path, expected_duration, expected_source))

    for key, entries in screen_groups.items():
        if len(entries) < 1:
            continue
        first_track, first_path, expected_duration, _source = entries[0]
        raw_duration = probe_media_duration_seconds(config, first_path)
        needs_timeline_output = (
            len(entries) > 1
            or raw_duration is None
            or raw_duration < expected_duration * 0.80
            or raw_duration > expected_duration * 1.20
        )
        if not needs_timeline_output:
            continue
        device_index = first_track.get("device_index")
        suffix = str(device_index if device_index is not None else key)
        output = root / "tracks" / "spliced" / f"screen_{suffix}.mp4"
        result = _concat_timeline_video_segments(root, config, entries, output, suffix=suffix, failures=failures)
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
                "normalizations": result.get("normalizations", []),
            })

    mic_entries: list[tuple[dict[str, Any], Path]] = []
    for segment in segments:
        mic_track = segment.get("microphone_track")
        if not isinstance(mic_track, Mapping):
            continue
        path = _segment_track_path(root, mic_track)
        if path:
            mic_entries.append((dict(mic_track), path))
    if len(mic_entries) >= 2:
        first_track = mic_entries[0][0]
        output = root / "tracks" / "spliced" / "microphone.wav"
        paths = [path for _, path in mic_entries]
        if _concat_media_segments(root, config, paths, output, log_name="splice_microphone.log", failures=failures):
            track = dict(first_track)
            track["id"] = "microphone_spliced"
            track["relative_path"] = relative(root, output)
            track["splice_source_tracks"] = [relative(root, path) for path in paths]
            track["capture_engine"] = track.get("capture_engine") or "avfoundation_native"
            spliced_tracks.append(track)
            plan["outputs"].append({
                "role": "microphone",
                "relative_path": track["relative_path"],
                "source_tracks": track["splice_source_tracks"],
            })

    if not spliced_tracks:
        plan["status"] = "unavailable"
    write_json(root / "render" / "edit_plan.json", plan)

    if not spliced_tracks:
        return tracks
    spliced_paths = {track.get("relative_path") for track in spliced_tracks}
    remaining = [track for track in tracks if track.get("relative_path") not in spliced_paths]
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
        screen_path = _segment_track_path(root, screen_track)
        mic_path = _segment_track_path(root, mic_track)
        segment_rows.append({
            "id": segment.get("id"),
            "index": segment.get("index"),
            "expected_duration_seconds": round(expected, 3) if expected else None,
            "expected_duration_source": expected_source,
            "screen_path": relative(root, screen_path) if screen_path else None,
            "screen_probe_duration_seconds": probe_media_duration_seconds(config, screen_path) if screen_path else None,
            "mic_path": relative(root, mic_path) if mic_path else None,
            "mic_probe_duration_seconds": probe_media_duration_seconds(config, mic_path) if mic_path else None,
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
        }
        rows.append(row)
        active_cursor += active_duration or 0.0

    if rows:
        return rows

    duration = _timeline_duration_floor(root, session, tracks, media_receipt, transcript={})
    screen_track = next((track for track in tracks if track.get("role") == "screen"), None)
    mic_track = next((track for track in tracks if track.get("role") == "microphone"), None)
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
    tracks = prepare_segment_tracks(root, config, session, failures)
    session["tracks"] = tracks

    append_postprocess_progress(root, "stop_ffmpeg", "running", "Stopping ffmpeg capture processes")
    stop_failure_count = len(failures)
    _backend_call("DELETE", "/api/recording/active-take")

    for proc in session.get("processes", []):
        pid = int(proc["pid"])
        if pid_alive(pid):
            signal_capture_process(pid, signal.SIGCONT)
            signal_capture_process(pid, signal.SIGINT)

    deadline = time.time() + 15
    while time.time() < deadline:
        if not any(pid_alive(int(proc["pid"])) for proc in session.get("processes", [])):
            break
        time.sleep(0.25)

    for proc in session.get("processes", []):
        pid = int(proc["pid"])
        if pid_alive(pid):
            signal_capture_process(pid, signal.SIGCONT)
            signal_capture_process(pid, signal.SIGTERM)
            failures.append(f"{proc['id']} did not stop after SIGINT; SIGTERM sent.")

    deadline = time.time() + 3
    while time.time() < deadline:
        if not any(pid_alive(int(proc["pid"])) for proc in session.get("processes", [])):
            break
        time.sleep(0.25)

    for proc in session.get("processes", []):
        pid = int(proc["pid"])
        if pid_alive(pid):
            signal_capture_process(pid, signal.SIGKILL)
            failures.append(f"{proc['id']} did not stop after SIGTERM; SIGKILL sent.")
    append_postprocess_progress(
        root,
        "stop_ffmpeg",
        "warn" if len(failures) > stop_failure_count else "pass",
        "One or more ffmpeg processes needed SIGTERM" if len(failures) > stop_failure_count else "ffmpeg capture processes stopped",
        {"process_count": len(session.get("processes", []))},
    )

    append_postprocess_progress(root, "quick_render", "running", "Preparing quick playback review")
    render_failure_count = len(failures)
    write_render(root, config, tracks, failures)
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


def postprocess(root: Path) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    failures: list[str] = session.get("known_failures", [])
    config = session["config"]
    tracks = session.get("tracks", [])
    markers = session.get("markers", [])
    pause_events = session.get("pause_events", [])
    tracks = prepare_segment_tracks(root, config, session, failures)
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
    write_render(root, config, tracks, failures)
    write_media_timeline_receipt(root, config, session, tracks, failures)
    append_postprocess_progress(root, "active_timeline", "running", "Projecting active timeline markers and chapters")
    active_timeline = write_active_timeline_projection(root, config, session, tracks, failures)
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
    append_postprocess_progress(root, "autoedit_cleanup", "running", "Running auto-editor silence cleanup on rough cut")
    autoedit_receipt = write_autoedit_cleanup(root, failures)
    autoedit_status = autoedit_receipt.get("status")
    append_postprocess_progress(
        root,
        "autoedit_cleanup",
        "pass" if autoedit_status == "ready" else ("warn" if autoedit_status in {"unavailable", "skipped"} else "fail"),
        {
            "ready": "Auto-editor cleanup complete",
            "unavailable": "auto-editor not on PATH; install via `pip install auto-editor`",
            "skipped": "auto-editor skipped because rough cut is missing",
            "failed": "auto-editor cleanup failed; see logs/autoedit.log",
        }.get(autoedit_status, f"auto-editor stage status={autoedit_status}"),
        {"status": autoedit_status, "output": autoedit_receipt.get("output"), "tool_resolved": autoedit_receipt.get("tool_resolved")},
    )
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
    return {
        "takeID": session["take_id"],
        "rootPath": str(root),
        "statusLines": status_lines,
        "knownFailures": list(dict.fromkeys(failures)),
    }


def stop(root: Path) -> dict[str, Any]:
    finalize_capture(root)
    return postprocess(root)


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

    output = root / "transcript" / "audio_for_transcribe.wav"
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
    timeout = _config_int(
        config,
        "transcribe_audio_prep_timeout_seconds",
        DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS,
        minimum=30,
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


def write_transcript_unavailable(root: Path, reason: str) -> None:
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
        write_transcript_unavailable(root, "No microphone track was recorded.")
        result = {"status": "skipped", "reason": "no_microphone_track"}
        write_transcript_receipt(root, "skipped", "no_microphone_track", result, started_at=started_at)
        return result

    audio_path = root / mic_track["relative_path"]
    if not audio_path.exists():
        write_transcript_unavailable(root, f"Microphone track missing on disk: {mic_track['relative_path']}.")
        failures.append("Microphone track missing on disk; cannot transcribe.")
        result = {"status": "skipped", "reason": "audio_missing", "source_track": mic_track["relative_path"]}
        write_transcript_receipt(root, "skipped", "audio_missing", result, started_at=started_at)
        return result

    model = config.get("transcribe_model", DEFAULT_TRANSCRIBE_MODEL)
    language = config.get("transcribe_language")
    audio_probe = probe_audio_signal(root, config, audio_path)
    if audio_probe.get("status") in {"failed", "silent"}:
        reason = f"Microphone track failed transcription input probe: {audio_probe.get('reason')}."
        write_transcript_unavailable(root, reason)
        failures.append(reason)
        terminal_reason = "silent_audio" if audio_probe.get("status") == "silent" else "audio_probe_failed"
        result = {"status": "skipped", "reason": terminal_reason, "audio_probe": audio_probe}
        write_transcript_receipt(root, "skipped", terminal_reason, result, started_at=started_at)
        return result
    transcription_audio, audio_preprocess = prepare_transcription_audio(root, config, audio_path)
    audio_preprocess["input_probe"] = audio_probe

    provider = str(config.get("transcribe_provider", DEFAULT_TRANSCRIBE_PROVIDER)).strip().lower().replace("-", "_")
    if provider not in TRANSCRIBE_PROVIDERS:
        provider = DEFAULT_TRANSCRIBE_PROVIDER
    providers = ["whisperkit", "whisper_cpp"] if provider == "auto" else [provider]
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
                source_track=mic_track["relative_path"],
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
                source_track=mic_track["relative_path"],
                audio_preprocess=audio_preprocess,
            )
        else:
            result = {"status": "skipped", "reason": "provider_unknown", "provider": candidate}
        attempts.append(dict(result))
        if result.get("status") == "ready":
            result["attempts"] = attempts
            result["audio_preprocess"] = audio_preprocess
            write_transcript_receipt(root, "ready", None, result, started_at=started_at)
            return result

    failure_reasons = ", ".join(
        str(attempt.get("reason") or f"{attempt.get('provider')}={attempt.get('status')}")
        for attempt in attempts
    )
    write_transcript_unavailable(root, f"Transcript provider unavailable: {failure_reasons}.")
    failed = next((attempt for attempt in attempts if attempt.get("status") == "failed"), None)
    if failed:
        failures.append(f"Transcription failed via {failed.get('provider')} ({failed.get('reason') or failed.get('exit_code')}).")
        result = {"status": "failed", "attempts": attempts, "audio_preprocess": audio_preprocess}
        write_transcript_receipt(root, "failed", str(failed.get("reason") or failed.get("exit_code") or "provider_failed"), result, started_at=started_at)
        return result
    result = {"status": "skipped", "reason": "provider_unavailable", "attempts": attempts, "audio_preprocess": audio_preprocess}
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

    timeout = _config_int(config, "transcribe_timeout_seconds", DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS, minimum=30, maximum=3600)
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
) -> dict[str, Any]:
    binary = find_whisper_cpp_binary(config)
    if not binary:
        return {"status": "skipped", "provider": "whisper_cpp", "reason": "binary_missing"}
    model_path = find_whisper_cpp_model(config, model, language)
    if not model_path:
        return {"status": "skipped", "provider": "whisper_cpp", "reason": "model_missing"}
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
    timeout = _config_int(config, "transcribe_timeout_seconds", DEFAULT_TRANSCRIBE_TIMEOUT_SECONDS, minimum=30, maximum=3600)
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


def write_render(root: Path, config: dict[str, Any], tracks: list[dict[str, Any]], failures: list[str]) -> None:
    screen = next((track for track in tracks if track["role"] == "screen"), None)
    mic = next((track for track in tracks if track["role"] == "microphone"), None)
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

    if not mic and profile == "efficient":
        hardlinked = replace_with_hardlink(output, screen_path)
        if hardlinked:
            write_json(
                root / "render" / "render_receipt.json",
                {
                    "schema": "demo_take_render_receipt_v0",
                    "status": "ready",
                    "output": relative(root, output),
                    "known_failures": render_warnings,
                    "storage_profile": profile,
                    "storage_optimization": {
                        "method": "hardlink_lossless_dedupe",
                        "rough_cut_screen_hardlinked": True,
                        "video_stream_action": "no_reencode",
                        "screen_track": screen["relative_path"],
                    },
                },
            )
            return

    try:
        if output_tmp.exists():
            output_tmp.unlink()
    except OSError:
        pass

    command = [ffmpeg, "-hide_banner", "-y", "-i", str(screen_path)]
    if mic:
        command += [
            "-i",
            str(root / mic["relative_path"]),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_tmp),
        ]
    else:
        command += ["-c", "copy", str(output_tmp)]

    log_path = root / "logs" / "rough_render.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode
        except OSError as exc:
            log.write(f"rough render unavailable: {exc}\n".encode("utf-8"))
            status = 1
    if status == 0 and output_tmp.exists():
        os.replace(output_tmp, output)
    else:
        try:
            if output_tmp.exists():
                output_tmp.unlink()
        except OSError:
            pass

    hardlinked = False
    optimization_method = "none"
    if status == 0 and profile == "efficient":
        hardlinked = replace_with_hardlink(screen_path, output)
        if hardlinked:
            optimization_method = "hardlink_lossless_dedupe"

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
            "storage_optimization": {
                "method": optimization_method,
                "rough_cut_screen_hardlinked": hardlinked,
                "video_stream_action": "copy",
                "screen_track": screen["relative_path"],
            },
        },
    )


def write_review_audio_mp3(
    root: Path,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str],
) -> dict[str, Any]:
    mic = next((track for track in tracks if track.get("role") == "microphone"), None)
    if not mic:
        return {"schema": "demo_take_review_audio_v0", "status": "skipped", "reason": "no_microphone_track", "output": None}

    source = root / mic["relative_path"]
    try:
        source_bytes = source.stat().st_size
    except OSError:
        source_bytes = 0
    if source_bytes <= 0:
        failures.append(f"Cannot build MP3 review audio because {mic['relative_path']} is missing or empty.")
        return {
            "schema": "demo_take_review_audio_v0",
            "status": "unavailable",
            "reason": "microphone_track_missing",
            "source": mic.get("relative_path"),
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
        "192k",
        str(output_tmp),
    ]
    with log_path.open("ab") as log:
        try:
            status = subprocess.run(command, stdout=log, stderr=log, check=False, timeout=120).returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.write(f"review audio export failed: {exc}\n".encode("utf-8"))
            status = 124

    if status == 0 and output_tmp.exists():
        os.replace(output_tmp, output)
        return {
            "schema": "demo_take_review_audio_v0",
            "status": "ready",
            "source": mic.get("relative_path"),
            "output": relative(root, output),
            "codec": "mp3",
            "bitrate": "192k",
            "bytes": output.stat().st_size if output.exists() else None,
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
    if rel_path == "render/rough_cut.mp4":
        return "local_review_proxy" if cloud_retention == "proxy" else "local_review_video"
    if rel_path.startswith("render/proxy_") and suffix in RAW_MEDIA_SUFFIXES:
        return "local_review_proxy"
    if rel_path == "render/review_audio.mp3":
        return "local_review_audio"
    if rel_path in {"render/cloud_archive_manifest.json", "render/cloud_archive_receipt.json"}:
        return "cloud_archive_authority"
    if rel_path in {"render/storage_receipt.json", "render/local_storage_receipt.json", "render/proxy_review_receipt.json"}:
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


def _local_raw_state(source_bytes: int, cloud_state: str, proxy_state: str) -> str:
    if source_bytes > 0:
        return "local_raw_present"
    if cloud_state in {"cloud_verified", "cloud_partial"} and proxy_state == "proxy_ready":
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
        return "cloud_verified_proxy_local"
    if cloud_state == "archive_failed":
        return "cloud_failed_raw_local_blocked"
    if raw_state == "local_raw_present" and archive_enabled:
        return "cloud_pending_raw_local"
    return "manual_source_retention"


def _storage_governor_operator_line(state: str, *, cloud_state: str, raw_state: str) -> str:
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


def _storage_prune_decision(
    *,
    source_bytes: int,
    cloud_receipt: Mapping[str, Any],
    proxy_state: str,
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if source_bytes <= 0:
        blockers.append("no_local_raw_media")
    if not _cloud_prune_safe(cloud_receipt):
        blockers.append("cloud_archive_not_verified")
    if proxy_state != "proxy_ready":
        blockers.append("local_review_proxy_not_ready")
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
    physical_bytes = directory_size_bytes(root, physical=True) if root.exists() else 0
    logical_bytes = directory_size_bytes(root, physical=False) if root.exists() else 0
    proxy_state, proxy_path, proxy_duration = _proxy_review_state(root, config)
    cloud_state = _cloud_storage_state(archive_receipt)
    raw_state = _local_raw_state(source_bytes, cloud_state, proxy_state)
    prune_allowed, prune_blockers = _storage_prune_decision(
        source_bytes=source_bytes,
        cloud_receipt=archive_receipt,
        proxy_state=proxy_state,
    )
    archive_enabled = cloud_archive_after_stop(config)
    retention_policy = cloud_archive_local_retention(config)
    governor_state = _storage_governor_state(
        cloud_state=cloud_state,
        raw_state=raw_state,
        archive_enabled=archive_enabled,
        retention_policy=retention_policy,
    )
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
        "prune_allowed": prune_allowed,
        "prune_blockers": prune_blockers,
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


def compact_storage(root: Path) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    config = dict(session.get("config", {}))
    config["storage_profile"] = "efficient"
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
    if screen:
        write_render(root, config, tracks, failures)

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
    receipt["compact_storage"] = {
        "status": "ready" if screen and not failures else ("partial" if screen else "skipped"),
        "bytes_before_physical": before_physical,
        "bytes_after_physical": after_physical,
        "bytes_saved_physical": saved,
        "bytes_before_logical": before_logical,
        "bytes_after_logical": after_logical,
        "known_failures": failures,
    }
    write_json(root / "render" / "local_storage_receipt.json", receipt)
    write_json(root / "render" / "storage_receipt.json", receipt)
    line = (
        f"Optimized storage for {session.get('take_id', root.name)}: "
        f"saved {human_bytes(saved)} without re-encoding video."
    )
    if not screen:
        line = "Storage already compact: no local screen track duplicate was found."
    return {
        "schema": "demo_take_compact_storage_result_v0",
        "status": receipt["status"],
        "takeID": session.get("take_id", root.name),
        "rootPath": str(root),
        "bytesBefore": before_physical,
        "bytesAfter": after_physical,
        "bytesSaved": saved,
        "knownFailures": failures,
        "statusLines": [line],
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
        else:
            storage_line += " - cloud archived"
    if local_storage_receipt.get("status") == "ready":
        source_bytes = int(local_storage_receipt.get("source_bytes") or 0)
        proxy_bytes = int(local_storage_receipt.get("proxy_bytes") or 0)
        if source_bytes:
            storage_line += f" - raw {human_bytes(source_bytes)}"
        if proxy_bytes:
            storage_line += f" - proxy {human_bytes(proxy_bytes)}"
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
    "1440p60": {"scale_height": 1440, "fps": 60, "requires_raw": True, "resolution": "2560x1440"},
    "1080p30": {"scale_height": 1080, "fps": 30, "requires_raw": True, "resolution": "1920x1080"},
}

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


def _final_segment_filter(start: float, end: float, *, include_audio: bool, scale_height: int | None, fps: int | None) -> str:
    vchain = f"trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS"
    if scale_height:
        vchain += f",scale=-2:{scale_height}:flags=lanczos"
    if fps:
        vchain += f",fps={fps}"
    vchain += ",format=yuv420p"
    parts = [f"[0:v:0]{vchain}[v]"]
    if include_audio:
        parts.append(f"[0:a:0]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo[a]")
    return ";".join(parts)


def render_final_cut(
    root: Path,
    *,
    edit_plan_path: Path | None = None,
    quality: str = "proxy",
    hydrate_policy: str = "if_needed",
    allow_stale: bool = False,
    allow_proxy_fallback: bool = False,
) -> dict[str, Any]:
    """Compile a final video from an editorial edit plan. Returns a result dict.

    Source policy:
      - proxy profile renders from proxy planning assets (a preview, not a master).
      - source/1440p60/1080p30 REQUIRE local raw (or hydrated raw). When raw is
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
        receipt = {
            "schema": "demo_take_final_render_receipt_v0",
            "status": "blocked",
            "blocker": blocker,
            "take_id": take_id,
            "render_profile": quality,
            "created_at": now_iso(),
            "warnings": [message],
        }
        if extra:
            receipt.update(extra)
        write_json(receipt_path, receipt)
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

        if profile["requires_raw"]:
            raw, tier = _raw_source_for_take(item_root)
            if tier == "raw_local" and raw is not None:
                source, source_mode = raw, "raw_local"
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
                cloud_hydration = "unavailable"
        else:
            source = _resolve_proxy_source(item_root, item_session, clip_id)
            if source is None:
                return _blocked("no_source", f"No proxy source for {clip_id}.")
            source_mode = "proxy"
        source_modes.add(source_mode)
        resolved.append({
            "clip_id": clip_id,
            "source": source,
            "source_sha256": _sha256_or_none(source),
            "start": start,
            "end": end,
            "source_mode": source_mode,
        })

    # Uniform audio policy so concat -c copy is valid across heterogeneous sources.
    include_audio = all(
        (_probe_media_stream_kinds(config, seg["source"]) or {"audio"}) >= {"audio"}
        for seg in resolved
    )

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
    warnings: list[str] = []
    with log_path.open("ab") as log:
        for index, seg in enumerate(resolved):
            seg_out = segments_dir / f"seg_{index:04d}.mp4"
            filter_complex = _final_segment_filter(
                seg["start"], seg["end"],
                include_audio=include_audio,
                scale_height=profile["scale_height"],
                fps=profile["fps"],
            )
            command = [ffmpeg, "-hide_banner", "-y", "-i", str(seg["source"]), "-filter_complex", filter_complex, "-map", "[v]"]
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
    source_hashes_verified = all(seg["source_sha256"] is not None for seg in resolved)

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

    receipt = {
        "schema": "demo_take_final_render_receipt_v0",
        "status": "ready",
        "take_id": take_id,
        "render_profile": quality,
        "created_at": now_iso(),
        "source_mode": resolved_mode,
        "edit_plan": relative(root, plan_path),
        "edit_plan_materialized": materialized,
        "plan_status": plan_status,
        "selection_policy": selection_policy,
        "production_ready": production_ready,
        "requires_review": requires_review,
        "source_range_count": len(resolved),
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
        "source_hashes_verified": source_hashes_verified,
        "cloud_hydration": cloud_hydration,
        "render_method": "trim_setpts_asetpts_segment_then_concat_copy",
        "has_audio": include_audio,
        "log": relative(root, log_path),
        "warnings": warnings,
    }
    write_json(receipt_path, receipt)
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
        ],
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
        f"- Cloud hydration: {receipt.get('cloud_hydration')}",
        f"- Render method: `{receipt.get('render_method')}`",
    ]
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

# (derived_relpath, [input_relpaths], critical, signal)
_STALENESS_EDGES: list[tuple[str, list[str], bool, str]] = [
    ("render/edit_plans/edit_0001.json", ["candidate_clips.json"], True, "recorded_sha256"),
    ("render/final/final_render_receipt.json", ["candidate_clips.json", "render/edit_plans/edit_0001.json"], True, "recorded_sha256"),
    ("phrase_cards.jsonl", ["transcript/transcript.json"], False, "mtime"),
    ("observation_atlas.json", ["transcript/transcript.json", "visual_change_index.jsonl"], False, "mtime"),
    ("candidate_clips.json", ["active_timeline.json"], False, "mtime"),
    ("render/clips/index.json", ["candidate_clips.json"], False, "mtime"),
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
    for derived_rel, input_rels, critical, signal in _STALENESS_EDGES:
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
                sub_stale_reasons = _edit_plan_staleness(root, _read_json_dict(root / plan_rel))
            candidate = root / "candidate_clips.json"
            mtime_newer = candidate.exists() and candidate.stat().st_mtime > derived.stat().st_mtime + 1
            if sub_stale_reasons or mtime_newer:
                status = "stale"
                detail["reasons"] = sub_stale_reasons + (["candidate_clips.json modified after final render"] if mtime_newer else [])
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
        "scale=w='min(1280,iw)':h=-2",
        "-c:v",
        "h264_videotoolbox",
        "-b:v",
        "2500k",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
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

    transport_config: Mapping[str, Any] = (
        {**config, "cloud_archive_transport": transport_mode} if transport_mode else config
    )
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

    proxy_retention: dict[str, Any] | None = None
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
        "transport": transport,
        "restore_plan": restore_plan,
        "hash_algorithm": "sha256",
        "manifest": "render/cloud_archive_manifest.json",
        "manifest_sha256": manifest_payload.get("manifest_sha256"),
        "file_count": manifest_payload.get("file_count"),
        "total_bytes": manifest_payload.get("total_bytes"),
        "local_retention": applied_retention,
        "proxy_retention": proxy_retention,
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
        sub_bytes = _tree_bytes(local_sub)
        if sub_bytes <= 0:
            continue
        remote_sub = remote_take.rstrip("/") + "/" + name
        dir_row: dict[str, Any] = {"dir": name, "local_bytes": sub_bytes}

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
        for path in sorted(local_sub.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
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

    for name in ["pause", "resume", "stop", "finalize", "postprocess"]:
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

    storage_receipt_parser = sub.add_parser("storage-receipt")
    storage_receipt_parser.add_argument("--take-root", required=True)

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
        elif args.command == "finalize":
            print(json.dumps(finalize_capture(Path(args.take_root))))
        elif args.command == "postprocess":
            print(json.dumps(postprocess(Path(args.take_root))))
        elif args.command == "mark":
            print(json.dumps(mark(Path(args.take_root), args.source, args.label)))
        elif args.command == "list-markers":
            print(json.dumps(list_markers(Path(args.take_root))))
        elif args.command == "set-title":
            print(json.dumps(set_take_title(Path(args.take_root), args.title)))
        elif args.command == "import-video":
            print(json.dumps(import_video(Path(args.source), Path(args.repo_root), title=args.title)))
        elif args.command == "compact-storage":
            print(json.dumps(compact_storage(Path(args.take_root))))
        elif args.command == "storage-receipt":
            root = Path(args.take_root)
            session = _read_json_dict(root / "session.json")
            config = dict(session.get("config") if isinstance(session.get("config"), Mapping) else {})
            print(json.dumps(write_local_storage_receipt(root, config, session)))
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
            print(json.dumps(transcribe_existing(
                Path(args.take_root),
                binary_override=args.binary,
                model_override=args.model,
                language_override=args.language,
                provider_override=args.provider,
                whisper_cpp_binary_override=args.whisper_cpp_binary,
                whisper_cpp_model_override=args.whisper_cpp_model,
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
