"""
Resolve authored provider/model profiles from the compute provider registry.

[PURPOSE]
- Teleology: Keep provider model choices in one authored control-plane file
  instead of scattering model IDs across harness code.
- Mechanism: Read codex/doctrine/compute/provider_registry.json, resolve named
  model profiles and local proxy settings, and render local runtime config.
- Non-goal: This module does not call model providers or store API secrets.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REL = "codex/doctrine/compute/provider_registry.json"
FREE_CLAUDE_CODE_REPO_REL = "annexes/free-claude-code/repo"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _repo_env_value(repo_root: Path, key: str) -> str:
    env_path = repo_root / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == key:
            return value.strip().strip("\"'")
    return ""


def load_provider_registry(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    return _read_json(repo_root / REGISTRY_REL)


def provider_row(provider_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    providers = load_provider_registry(repo_root).get("providers") or {}
    row = providers.get(provider_id) if isinstance(providers, Mapping) else {}
    return dict(row) if isinstance(row, Mapping) else {}


def nvidia_model_profile(
    profile_id: str = "default_chat",
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    profiles = provider_row("nvidia_nim", repo_root).get("model_profiles") or {}
    profile = profiles.get(profile_id) if isinstance(profiles, Mapping) else {}
    return dict(profile) if isinstance(profile, Mapping) else {}


def nvidia_model_id(
    profile_id: str = "default_chat",
    *,
    repo_root: Path = REPO_ROOT,
    fallback: str = "",
) -> str:
    return _string(nvidia_model_profile(profile_id, repo_root).get("model_id")) or fallback


def free_claude_code_profile(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    row = provider_row("free_claude_code_proxy", repo_root)
    runtime = dict(row.get("runtime") or {})
    mapping_profile = dict(row.get("model_mapping_profile") or {})
    provider_id = _string(mapping_profile.get("provider")) or "nvidia_nim"
    model_refs = dict(mapping_profile.get("model_refs") or {})

    model_mappings: dict[str, str] = {}
    for env_name, ref_name in {
        "MODEL_OPUS": model_refs.get("opus"),
        "MODEL_SONNET": model_refs.get("sonnet"),
        "MODEL_HAIKU": model_refs.get("haiku"),
        "MODEL": model_refs.get("fallback"),
    }.items():
        ref = _string(ref_name)
        if not ref:
            continue
        model_id = nvidia_model_id(ref, repo_root=repo_root)
        if model_id:
            model_mappings[env_name] = f"{provider_id}/{model_id}"

    return {
        "provider_id": "free_claude_code_proxy",
        "downstream_provider": provider_id,
        "base_url": os.environ.get("FREE_CLAUDE_CODE_BASE_URL")
        or _string(runtime.get("base_url"))
        or "http://127.0.0.1:8082",
        "auth_token": os.environ.get(_string(runtime.get("auth_token_env")) or "FREE_CLAUDE_CODE_AUTH_TOKEN")
        or _string(runtime.get("default_auth_token"))
        or "freecc",
        "port": int(runtime.get("port") or 8082),
        "host": _string(runtime.get("host")) or "127.0.0.1",
        "claude_code_model_alias": _string(mapping_profile.get("claude_code_model_alias"))
        or "sonnet",
        "enable_thinking": bool(mapping_profile.get("enable_thinking", False)),
        "model_mapping_profile_id": _string(mapping_profile.get("profile_id")),
        "model_mappings": model_mappings,
    }


def build_free_claude_code_env(repo_root: Path = REPO_ROOT) -> str:
    profile = free_claude_code_profile(repo_root)
    nvidia_key = os.environ.get("NVIDIA_API_KEY") or _repo_env_value(repo_root, "NVIDIA_API_KEY")
    mappings = dict(profile.get("model_mappings") or {})
    lines = [
        "# Generated from codex/doctrine/compute/provider_registry.json.",
        "# Do not edit model choices here; update the registry model profile instead.",
        f'NVIDIA_NIM_API_KEY="{nvidia_key}"',
        'OPENROUTER_API_KEY=""',
        'LM_STUDIO_BASE_URL="http://localhost:1234/v1"',
        'LLAMACPP_BASE_URL="http://localhost:8080/v1"',
        f'MODEL_OPUS="{mappings.get("MODEL_OPUS", "")}"',
        f'MODEL_SONNET="{mappings.get("MODEL_SONNET", "")}"',
        f'MODEL_HAIKU="{mappings.get("MODEL_HAIKU", "")}"',
        f'MODEL="{mappings.get("MODEL", "")}"',
        f'ENABLE_THINKING={str(bool(profile.get("enable_thinking"))).lower()}',
        "PROVIDER_RATE_LIMIT=40",
        "PROVIDER_RATE_WINDOW=60",
        "PROVIDER_MAX_CONCURRENCY=2",
        "HTTP_READ_TIMEOUT=120",
        "HTTP_WRITE_TIMEOUT=10",
        "HTTP_CONNECT_TIMEOUT=2",
        f'ANTHROPIC_AUTH_TOKEN="{profile.get("auth_token")}"',
        'MESSAGING_PLATFORM="telegram"',
        "MESSAGING_RATE_LIMIT=1",
        "MESSAGING_RATE_WINDOW=1",
        "VOICE_NOTE_ENABLED=false",
        'WHISPER_DEVICE="cpu"',
        'WHISPER_MODEL="base"',
        'HF_TOKEN=""',
        'TELEGRAM_BOT_TOKEN=""',
        'ALLOWED_TELEGRAM_USER_ID=""',
        'DISCORD_BOT_TOKEN=""',
        'ALLOWED_DISCORD_CHANNELS=""',
        f'CLAUDE_WORKSPACE="{repo_root}"',
        f'ALLOWED_DIR="{repo_root}"',
        "FAST_PREFIX_DETECTION=true",
        "ENABLE_NETWORK_PROBE_MOCK=true",
        "ENABLE_TITLE_GENERATION_SKIP=true",
        "ENABLE_SUGGESTION_MODE_SKIP=true",
        "ENABLE_FILEPATH_EXTRACTION_MOCK=true",
        f'HOST="{profile.get("host")}"',
        f'PORT={profile.get("port")}',
        'LOG_FILE="free-claude-code.log"',
    ]
    return "\n".join(lines) + "\n"


def write_free_claude_code_env(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    env_path = repo_root / FREE_CLAUDE_CODE_REPO_REL / ".env"
    env_path.write_text(build_free_claude_code_env(repo_root), encoding="utf-8")
    env_path.chmod(0o600)
    profile = free_claude_code_profile(repo_root)
    return {
        "path": str(env_path.relative_to(repo_root)),
        "profile": {
            key: value
            for key, value in profile.items()
            if key not in {"auth_token"}
        },
        "auth_token_present": bool(profile.get("auth_token")),
        "nvidia_key_present": bool(os.environ.get("NVIDIA_API_KEY") or _repo_env_value(repo_root, "NVIDIA_API_KEY")),
    }
