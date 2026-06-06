#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
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
TRANSCRIBE_PROVIDERS = {"auto", "whisperkit", "whisper_cpp"}
WHISPER_CPP_MODEL_DIR = REPO_ROOT / "state" / "whisper"
WHISPER_CPP_MODEL_URL_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
EXTERNAL_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
DEFAULT_STORAGE_PROFILE = "efficient"
STORAGE_PROFILES = {"efficient", "source"}
DEFAULT_FRAME_THUMBNAIL_WIDTH = 1280
DEFAULT_FRAME_JPEG_QUALITY = 5
EXPORTS_RELATIVE_ROOT = Path("state") / "dissemination" / "demo_exports"
TITLE_SLUG_RE = re.compile(r"[^a-z0-9]+")


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
) -> dict[str, Any]:
    def maybe(rel_path: str) -> str | None:
        return rel_path if (root / rel_path).exists() else None

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
        "marker_phrases": config.get("marker_phrases", DEFAULT_MARKER_PHRASES),
        "sources": {
            "screens": config.get("screens", []),
            "microphone": config.get("microphone"),
            "webcam": config.get("webcam"),
        },
        "tracks": tracks,
        "marker_count": len(markers or []),
        "pause_event_count": len(pause_events or []),
        "transcript": maybe("transcript/transcript.json"),
        "visual_index": maybe("visual_index.json"),
        "edl": maybe("edl.json"),
        "view_telemetry": maybe("view_telemetry.jsonl"),
        "view_timeline": maybe("view_timeline.json"),
        "per_view_segments": maybe("per_view_segments.json"),
        "speech_blocks": maybe("speech_blocks.json"),
        "schedule_progress": maybe("schedule_progress.jsonl"),
        "intent_events": maybe("intent_events.json"),
        "render_receipt": maybe("render/render_receipt.json"),
        "edl_otio": maybe("edl.otio"),
        "autoedit_receipt": maybe("render/autoedit_receipt.json"),
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
    take_id, root = unique_take_root(repo_root, prefix="take", title=title)
    tracks_dir = root / "tracks"
    logs_dir = root / "logs"
    for name in ["tracks", "frames", "transcript", "render", "review", "logs"]:
        (root / name).mkdir(parents=True, exist_ok=True)

    ffmpeg = config["ffmpeg_path"]
    tracks: list[dict[str, Any]] = []
    processes: list[dict[str, Any]] = []
    failures: list[str] = []

    for screen in config.get("screens", []):
        role = f"screen_{screen['index']}"
        output = tracks_dir / f"{role}.mp4"
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
                "6000k",
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
                "3500k",
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
        output = tracks_dir / "microphone.m4a"
        proc = launch_ffmpeg(
            ffmpeg,
            [
                "-hide_banner",
                "-y",
                "-f",
                "avfoundation",
                "-i",
                f"none:{microphone['index']}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
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


def signal_session(root: Path, sig: signal.Signals) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    sent: list[str] = []
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
    count = _append_marker_record(root, session, record, "recording")
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


def _span_for_time(spans: list[dict[str, Any]], t: float) -> dict[str, Any] | None:
    for span in spans:
        if span["start_video_t"] <= t < span["end_video_t"]:
            return span
    if spans and t >= spans[-1]["end_video_t"]:
        return spans[-1]
    return None


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
    tracks = session.get("tracks", [])
    failures: list[str] = []
    result = transcribe_track(root, config, tracks, failures)
    return {"result": result, "knownFailures": failures}


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


def finalize_capture(root: Path) -> dict[str, Any]:
    session_path = root / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    failures: list[str] = session.get("known_failures", [])
    config = session["config"]
    tracks = session.get("tracks", [])
    markers = session.get("markers", [])
    pause_events = session.get("pause_events", [])

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
    render_receipt = json.loads((root / "render" / "render_receipt.json").read_text(encoding="utf-8")) if (root / "render" / "render_receipt.json").exists() else {}
    append_postprocess_progress(
        root,
        "quick_render",
        "pass" if render_receipt.get("status") == "ready" else "warn",
        "Quick playback ready" if render_receipt.get("status") == "ready" else "Quick playback render unavailable",
        {"status": render_receipt.get("status"), "output": render_receipt.get("output"), "new_failure_count": len(failures) - render_failure_count},
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
        ),
    )
    return {
        "takeID": session["take_id"],
        "rootPath": str(root),
        "statusLines": [f"Finalized {session['take_id']} for review."],
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
        ),
    )

    append_postprocess_progress(root, "sample_frames", "running", "Sampling frame thumbnails")
    frame_failure_count = len(failures)
    frame_records = sample_frames(root, config, tracks, failures)
    append_postprocess_progress(
        root,
        "sample_frames",
        "warn" if len(failures) > frame_failure_count else "pass",
        "Sampled frame thumbnails" if frame_records else "No frame thumbnails were sampled",
        {"frame_count": len(frame_records)},
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
    if transcribe_result.get("status") == "ready":
        enrich_transcript_with_views(root)
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
    append_postprocess_progress(root, "rough_render", "running", "Rendering rough screen-plus-microphone cut")
    render_failure_count = len(failures)
    write_render(root, config, tracks, failures)
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
        ),
    )
    append_postprocess_progress(root, "manifest_ready", "pass", "Manifest updated for package-ready state")
    append_postprocess_progress(root, "package_ready", "pass", "Take package postprocess complete")
    return {
        "takeID": session["take_id"],
        "rootPath": str(root),
        "statusLines": [f"Stopped and postprocessed {session['take_id']}."],
        "knownFailures": failures,
    }


def stop(root: Path) -> dict[str, Any]:
    finalize_capture(root)
    return postprocess(root)


def sample_frames(root: Path, config: dict[str, Any], tracks: list[dict[str, Any]], failures: list[str]) -> list[dict[str, Any]]:
    ffmpeg = config["ffmpeg_path"]
    interval = int(config["screenshot_interval_seconds"])
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
    with log_path.open("ab") as log:
        status = subprocess.run(command, stdout=log, stderr=log, check=False).returncode

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


def transcribe_track(
    root: Path,
    config: dict[str, Any],
    tracks: list[dict[str, Any]],
    failures: list[str],
) -> dict[str, Any]:
    transcript_dir = root / "transcript"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_json = transcript_dir / "transcript.json"
    transcript_srt = transcript_dir / "transcript.srt"

    mic_track = next((track for track in tracks if track["role"] == "microphone"), None)
    if not mic_track:
        write_transcript_unavailable(root, "No microphone track was recorded.")
        return {"status": "skipped", "reason": "no_microphone_track"}

    audio_path = root / mic_track["relative_path"]
    if not audio_path.exists():
        write_transcript_unavailable(root, f"Microphone track missing on disk: {mic_track['relative_path']}.")
        failures.append("Microphone track missing on disk; cannot transcribe.")
        return {"status": "skipped", "reason": "audio_missing"}

    model = config.get("transcribe_model", DEFAULT_TRANSCRIBE_MODEL)
    language = config.get("transcribe_language")
    transcription_audio, audio_preprocess = prepare_transcription_audio(root, config, audio_path)

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
            return result

    failure_reasons = ", ".join(
        str(attempt.get("reason") or f"{attempt.get('provider')}={attempt.get('status')}")
        for attempt in attempts
    )
    write_transcript_unavailable(root, f"Transcript provider unavailable: {failure_reasons}.")
    failed = next((attempt for attempt in attempts if attempt.get("status") == "failed"), None)
    if failed:
        failures.append(f"Transcription failed via {failed.get('provider')} ({failed.get('reason') or failed.get('exit_code')}).")
        return {"status": "failed", "attempts": attempts, "audio_preprocess": audio_preprocess}
    return {"status": "skipped", "reason": "provider_unavailable", "attempts": attempts, "audio_preprocess": audio_preprocess}


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

    with log_path.open("ab") as log:
        proc = subprocess.run(cmd, stdout=log, stderr=log, check=False)
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
    with log_path.open("ab") as log:
        proc = subprocess.run(cmd, stdout=log, stderr=log, check=False)
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
    ffmpeg = config["ffmpeg_path"]
    screen = next((track for track in tracks if track["role"] == "screen"), None)
    mic = next((track for track in tracks if track["role"] == "microphone"), None)
    output = root / "render" / "rough_cut.mp4"
    output_tmp = output.with_name("rough_cut.tmp.mp4")
    profile = storage_profile(config)
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
    if not mic and profile == "efficient":
        hardlinked = replace_with_hardlink(output, screen_path)
        if hardlinked:
            write_json(
                root / "render" / "render_receipt.json",
                {
                    "schema": "demo_take_render_receipt_v0",
                    "status": "ready",
                    "output": relative(root, output),
                    "known_failures": [],
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

    render_failures = [] if status == 0 else ["Rough render failed; see logs/rough_render.log."]
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
    receipt = {
        "schema": "demo_take_storage_receipt_v0",
        "status": "ready" if screen and not failures else ("partial" if screen else "skipped"),
        "take_id": session.get("take_id", root.name),
        "created_at": now_iso(),
        "storage_profile": "efficient",
        "bytes_before_physical": before_physical,
        "bytes_after_physical": after_physical,
        "bytes_saved_physical": saved,
        "bytes_before_logical": before_logical,
        "bytes_after_logical": after_logical,
        "known_failures": failures,
    }
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
        "statusLines": [storage_line],
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


def _unique_export_path(destination_dir: Path, stem: str, suffix: str, source: Path) -> Path:
    safe_stem = take_title_slug(stem) or "demo-take"
    for index in range(100):
        suffix_text = "" if index == 0 else f"-{index + 1:02d}"
        candidate = destination_dir / f"{safe_stem}{suffix_text}{suffix}"
        if not candidate.exists() or files_are_same(candidate, source):
            return candidate
    raise RuntimeError(f"could not allocate export path for {safe_stem}{suffix}")


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
        "method": method,
        "bytes": receipt["bytes"],
        "statusLines": [line],
    }


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
        "screens": [{"index": 0, "name": "Fake Main Display"}],
        "microphone": {"index": 0, "name": "Fake Microphone"},
        "webcam": None,
    }
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
    enrich_transcript_with_views(root)
    build_per_view_segments(root)
    build_intent_events(root)
    build_speech_blocks(root)
    write_edl(root, resolved_take_id, tracks, markers)
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
        "per_view_segments",
        "intent_events",
        "speech_blocks",
        "edl",
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
            "per_view_segments.json",
            "speech_blocks.json",
            "intent_events.json",
            "edl.json",
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

    storage_status_parser = sub.add_parser("storage-status")
    storage_status_parser.add_argument("--take-root", required=True)

    export_parser = sub.add_parser("export-video")
    export_parser.add_argument("--take-root", required=True)
    export_parser.add_argument("--destination-dir", default=None)

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
        elif args.command == "storage-status":
            print(json.dumps(storage_status(Path(args.take_root))))
        elif args.command == "export-video":
            print(json.dumps(export_video(
                Path(args.take_root),
                destination_dir=Path(args.destination_dir) if args.destination_dir else None,
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
