"""
[PURPOSE]
- Teleology: Provide a minimal hosted NVIDIA NIM client for low-cost internal chat and embedding tasks such as routing, retrieval, and background "metabolism" work without introducing a new orchestration runtime.
- Mechanism: Reads NVIDIA_* environment defaults, sends Bearer-authenticated JSON requests to NVIDIA's hosted chat and retrieval endpoints, and returns normalized text or embedding vectors.

[INTERFACE]
- Exports: chat_completion, embed_texts, list_models, runtime_status, DEFAULT_* constants.
- Reads: NVIDIA_API_KEY plus optional NVIDIA_CHAT_MODEL, NVIDIA_EMBED_MODEL, NVIDIA_CODE_EMBED_MODEL, NVIDIA_CHAT_BASE_URL, NVIDIA_EMBEDDINGS_URL from process env.
- Writes: None directly; performs outbound HTTPS requests only.

[FLOW]
- Resolve auth/model/url defaults from config or env -> build OpenAI-compatible chat or retrieval payload -> POST to NVIDIA hosted endpoint -> normalize response into plain text or embedding vectors.
- When-needed: Open when the repo needs a cheap hosted provider for internal non-production work, or when routing/retrieval code needs the exact NIM endpoint contract.
- Escalates-to: system/lib/agent_providers.py::ask_nvidia

[DEPENDENCIES]
- os: Read API key and model defaults from env.
- requests: Execute HTTPS POST calls against NVIDIA hosted endpoints.
- threading: Observe the shared cancellation event contract used by local provider wrappers.

[CONSTRAINTS]
- Guarantee: chat_completion() returns plain assistant text; embed_texts() returns one vector per input item in response order.
- Non-goal: This module does not self-host downloadable NIM containers and does not introduce a new repo-wide worker type.
- Scope: Intended for internal development/prototyping paths, not customer-facing production routing.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

import requests

from system.lib import model_profile_registry


DEFAULT_CHAT_BASE_URL = "https://integrate.api.nvidia.com"
DEFAULT_EMBEDDINGS_URL = "https://integrate.api.nvidia.com/v1/embeddings"
DEFAULT_RERANKINGS_URL = "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking"
DEFAULT_CHAT_MODEL = model_profile_registry.nvidia_model_id(
    "default_chat",
    fallback="deepseek-ai/deepseek-v4-pro",
)
DEFAULT_ROUTING_AUDIT_MODEL = "moonshotai/kimi-k2-thinking"
DEFAULT_EMBED_MODEL = model_profile_registry.nvidia_model_id(
    "embed_general",
    fallback="nvidia/nv-embed-v1",
)
DEFAULT_CODE_EMBED_MODEL = model_profile_registry.nvidia_model_id(
    "embed_code",
    fallback="nvidia/nv-embedcode-7b-v1",
)
DEFAULT_RERANK_MODEL = model_profile_registry.nvidia_model_id(
    "rerank_pairs",
    fallback="nvidia/nv-rerankqa-mistral-4b-v3",
)
DEFAULT_CHAT_TIMEOUT_S = 120
DEFAULT_EMBED_TIMEOUT_S = 120
DEFAULT_RERANK_TIMEOUT_S = 120
DEFAULT_ASSUMED_RATE_LIMIT_RPM = 40

REPO_ROOT = Path(__file__).resolve().parents[2]
_DOTENV_LOADED = False
_RATE_LIMIT_HEADER_TOKENS = ("rate", "limit", "quota", "retry")


def _ensure_env_loaded() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env")


def _config_value(config: Mapping[str, Any] | None, key: str, env_var: str, default: Any) -> Any:
    if config and key in config and config[key] not in (None, ""):
        return config[key]
    _ensure_env_loaded()
    value = os.environ.get(env_var)
    return value if value not in (None, "") else default


def _resolve_api_key(config: Mapping[str, Any] | None) -> str:
    token = _config_value(config, "api_key", "NVIDIA_API_KEY", "")
    api_key = str(token or "").strip()
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is not configured")
    return api_key


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _raise_cancelled(cancel: threading.Event | None) -> None:
    if cancel and cancel.is_set():
        raise InterruptedError("Cancelled by stop event")


def _request_json(
    *,
    url: str,
    payload: Mapping[str, Any],
    timeout_s: int,
    api_key: str,
    cancel: threading.Event | None,
) -> dict[str, Any]:
    _raise_cancelled(cancel)
    try:
        response = requests.post(
            url,
            headers=_headers(api_key),
            json=payload,
            timeout=timeout_s,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            body = (exc.response.text or "").strip()
        detail = body[:500] if body else str(exc)
        raise RuntimeError(f"NVIDIA NIM request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"NVIDIA NIM request failed: {exc}") from exc
    _raise_cancelled(cancel)
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("NVIDIA NIM returned a non-object JSON response")
    return data


def _request_json_get(
    *,
    url: str,
    timeout_s: int,
    api_key: str,
    cancel: threading.Event | None,
) -> dict[str, Any]:
    _raise_cancelled(cancel)
    try:
        response = requests.get(
            url,
            headers=_headers(api_key),
            timeout=timeout_s,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            body = (exc.response.text or "").strip()
        detail = body[:500] if body else str(exc)
        raise RuntimeError(f"NVIDIA NIM request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"NVIDIA NIM request failed: {exc}") from exc
    _raise_cancelled(cancel)
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("NVIDIA NIM returned a non-object JSON response")
    return data


def _request_models_payload(
    *,
    base_url: str,
    timeout_s: int,
    api_key: str,
    cancel: threading.Event | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    _raise_cancelled(cancel)
    try:
        response = requests.get(
            f"{base_url}/v1/models",
            headers=_headers(api_key),
            timeout=timeout_s,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            body = (exc.response.text or "").strip()
        detail = body[:500] if body else str(exc)
        raise RuntimeError(f"NVIDIA NIM request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"NVIDIA NIM request failed: {exc}") from exc
    _raise_cancelled(cancel)
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("NVIDIA NIM returned a non-object JSON response")
    headers: dict[str, str] = {}
    for key, value in response.headers.items():
        lowered = str(key).lower()
        if any(token in lowered for token in _RATE_LIMIT_HEADER_TOKENS):
            headers[str(key)] = str(value)
    return data, headers


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    token = str(value or "").strip()
    if token.isdigit():
        parsed = int(token)
        return parsed if parsed > 0 else None
    return None


def _resolve_rate_limit_rpm(config: Mapping[str, Any] | None) -> tuple[int, str]:
    if config:
        parsed = _positive_int(config.get("rate_limit_rpm"))
        if parsed is not None:
            return parsed, "config:rate_limit_rpm"
    _ensure_env_loaded()
    for env_var in ("NVIDIA_RATE_LIMIT_RPM", "NVIDIA_REQUESTS_PER_MINUTE"):
        parsed = _positive_int(os.environ.get(env_var))
        if parsed is not None:
            return parsed, f"env:{env_var}"
    return DEFAULT_ASSUMED_RATE_LIMIT_RPM, "assumed_default"


def _normalize_model_id(model: str) -> str:
    token = str(model or "").strip()
    normalized = token.lower()
    aliases = {
        "glm4.7": "z-ai/glm4.7",
        "glm-4.7": "z-ai/glm4.7",
        "z-ai/glm-4.7": "z-ai/glm4.7",
        "glm5": "z-ai/glm5",
        "glm-5": "z-ai/glm5",
        "z-ai/glm-5": "z-ai/glm5",
        "glm5.1": "z-ai/glm-5.1",
        "glm-5.1": "z-ai/glm-5.1",
        "deepseek-v4": "deepseek-ai/deepseek-v4-pro",
        "deepseek-v4-pro": "deepseek-ai/deepseek-v4-pro",
        "deepseek-v4-flash": "deepseek-ai/deepseek-v4-flash",
        "minimax-m2.7": "minimaxai/minimax-m2.7",
        "minimax-m2.5": "minimaxai/minimax-m2.5",
        "kimi-k2": "moonshotai/kimi-k2-instruct",
        "kimi-k2-instruct": "moonshotai/kimi-k2-instruct",
        "kimi-k2-instruct-0905": "moonshotai/kimi-k2-instruct-0905",
        "kimi-k2.5": "moonshotai/kimi-k2.5",
        "kimi-k2-5": "moonshotai/kimi-k2.5",
        # K2.6 dropped on Moonshot's own platform 2026-04-13 but is not yet
        # on NVIDIA NIM's /v1/models endpoint (probe confirmed 2026-04-20).
        # Alias points to kimi-k2-thinking as the highest-capability
        # NIM-available fallback; flip to "moonshotai/kimi-k2.6" once NVIDIA
        # ships the endpoint. Direct-to-Moonshot access would need its own
        # api client module (not added here — scope creep vs NVIDIA path).
        "kimi-k2.6": "moonshotai/kimi-k2-thinking",
        "kimi-k2-6": "moonshotai/kimi-k2-thinking",
        "kimi-k2-thinking": "moonshotai/kimi-k2-thinking",
        "nv-embed-v1": "nvidia/nv-embed-v1",
        "nv-embedcode-7b-v1": "nvidia/nv-embedcode-7b-v1",
        "nv-rerankqa-mistral-4b-v3": "nvidia/nv-rerankqa-mistral-4b-v3",
        "rerank-qa-mistral-4b": "nvidia/rerank-qa-mistral-4b",
    }
    return aliases.get(normalized, token)


def _normalize_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                token = item.strip()
                if token:
                    chunks.append(token)
                continue
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
        return "\n".join(chunks).strip()
    return str(content or "").strip()


def list_models(
    query: str | None = None,
    config: Mapping[str, Any] | None = None,
    cancel: threading.Event | None = None,
) -> list[str]:
    """
    [ACTION]
    - Teleology: Fetch the hosted model ids visible to the current NVIDIA API key so callers can select real, account-scoped ids instead of guessing from marketing names.
    - Mechanism: Calls `GET /v1/models`, extracts model ids, and optionally applies a case-insensitive substring filter.
    - Guarantee: Returns model ids in server order, optionally filtered by `query`.
    - Fails: Raises RuntimeError for missing auth, HTTP/transport failures, or malformed JSON payloads.
    - When-needed: Open when model naming or availability is uncertain and the repo needs the live account-scoped source of truth.
    - Escalates-to: docs/nvidia_nim_backend.md
    """
    cfg = dict(config or {})
    api_key = _resolve_api_key(cfg)
    base_url = str(_config_value(cfg, "base_url", "NVIDIA_CHAT_BASE_URL", DEFAULT_CHAT_BASE_URL)).rstrip("/")
    timeout_s = int(_config_value(cfg, "timeout_s", "NVIDIA_CHAT_TIMEOUT_S", DEFAULT_CHAT_TIMEOUT_S))
    data, _headers = _request_models_payload(
        base_url=base_url,
        timeout_s=timeout_s,
        api_key=api_key,
        cancel=cancel,
    )
    rows = data.get("data")
    if not isinstance(rows, list):
        raise RuntimeError("NVIDIA NIM models response did not include data")
    ids: list[str] = []
    needle = str(query or "").strip().lower()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        model_id = str(row.get("id") or "").strip()
        if not model_id:
            continue
        if needle and needle not in model_id.lower():
            continue
        ids.append(model_id)
    return ids


def runtime_status(
    config: Mapping[str, Any] | None = None,
    *,
    probe_live: bool = False,
    cancel: threading.Event | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project the hosted NVIDIA lane into one status payload that controllers can use to decide whether the lane is configured, what RPM assumption is active, and whether the live API exposes rate-limit headers.
    - Mechanism: Resolves env/config defaults, applies an explicit RPM override contract (`rate_limit_rpm` or `NVIDIA_RATE_LIMIT_RPM`), and optionally probes `GET /v1/models` to sample live model visibility and rate-limit headers.
    - Guarantee: Returns a JSON-serializable dict and does not require the caller to read process env directly.
    - Fails: Missing auth is reported in `live_probe` rather than raising unless the caller invokes chat/embeddings separately.
    - When-needed: Open when wiring NVIDIA into a larger runtime and the controller needs an honest status/limit packet before dispatch.
    - Escalates-to: docs/nvidia_nim_backend.md
    """
    cfg = dict(config or {})
    api_key_present = bool(str(_config_value(cfg, "api_key", "NVIDIA_API_KEY", "") or "").strip())
    chat_base_url = str(_config_value(cfg, "base_url", "NVIDIA_CHAT_BASE_URL", DEFAULT_CHAT_BASE_URL)).rstrip("/")
    embeddings_url = str(
        _config_value(cfg, "embeddings_url", "NVIDIA_EMBEDDINGS_URL", DEFAULT_EMBEDDINGS_URL)
    ).strip()
    chat_model = _normalize_model_id(
        str(_config_value(cfg, "model", "NVIDIA_CHAT_MODEL", DEFAULT_CHAT_MODEL)).strip()
    )
    embed_model = _normalize_model_id(
        str(_config_value(cfg, "embed_model", "NVIDIA_EMBED_MODEL", DEFAULT_EMBED_MODEL)).strip()
    )
    code_embed_model = _normalize_model_id(
        str(_config_value(cfg, "code_embed_model", "NVIDIA_CODE_EMBED_MODEL", DEFAULT_CODE_EMBED_MODEL)).strip()
    )
    rerankings_url = str(
        _config_value(cfg, "rerankings_url", "NVIDIA_RERANKINGS_URL", DEFAULT_RERANKINGS_URL)
    ).strip()
    rerank_model = _normalize_model_id(
        str(_config_value(cfg, "rerank_model", "NVIDIA_RERANK_MODEL", DEFAULT_RERANK_MODEL)).strip()
    )
    chat_timeout_s = int(_config_value(cfg, "timeout_s", "NVIDIA_CHAT_TIMEOUT_S", DEFAULT_CHAT_TIMEOUT_S))
    embed_timeout_s = int(_config_value(cfg, "embed_timeout_s", "NVIDIA_EMBED_TIMEOUT_S", DEFAULT_EMBED_TIMEOUT_S))
    rerank_timeout_s = int(_config_value(cfg, "rerank_timeout_s", "NVIDIA_RERANK_TIMEOUT_S", DEFAULT_RERANK_TIMEOUT_S))
    rate_limit_rpm, rate_limit_source = _resolve_rate_limit_rpm(cfg)

    payload: dict[str, Any] = {
        "configured": {
            "api_key_present": api_key_present,
            "chat_base_url": chat_base_url,
            "embeddings_url": embeddings_url,
            "chat_model": chat_model,
            "embed_model": embed_model,
            "code_embed_model": code_embed_model,
            "rerankings_url": rerankings_url,
            "rerank_model": rerank_model,
            "chat_timeout_s": chat_timeout_s,
            "embed_timeout_s": embed_timeout_s,
            "rerank_timeout_s": rerank_timeout_s,
        },
        "limits": {
            "effective_rate_limit_rpm": rate_limit_rpm,
            "rate_limit_source": rate_limit_source,
            "recommended_min_interval_seconds": round(60.0 / float(rate_limit_rpm), 3),
            "api_headers_expose_rate_limits": None,
            "notes": [
                "The hosted /v1 API does not currently expose rate-limit headers reliably in this repo's probe path. Override with NVIDIA_RATE_LIMIT_RPM if your account differs."
            ]
            if rate_limit_source == "assumed_default"
            else [],
        },
    }
    if not probe_live:
        payload["live_probe"] = {
            "status": "not_run",
            "reason": "probe_live_disabled",
        }
        return payload

    if not api_key_present:
        payload["live_probe"] = {
            "status": "not_configured",
            "reason": "NVIDIA_API_KEY is not configured",
        }
        return payload

    try:
        api_key = _resolve_api_key(cfg)
        data, headers = _request_models_payload(
            base_url=chat_base_url,
            timeout_s=chat_timeout_s,
            api_key=api_key,
            cancel=cancel,
        )
        rows = data.get("data")
        model_ids: list[str] = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                model_id = str(row.get("id") or "").strip()
                if model_id:
                    model_ids.append(model_id)
        payload["limits"]["api_headers_expose_rate_limits"] = bool(headers)
        if headers:
            payload["limits"]["rate_limit_headers"] = headers
        payload["live_probe"] = {
            "status": "ok",
            "models_count": len(model_ids),
            "models_sample": model_ids[:10],
            "rate_limit_headers": headers,
            "api_headers_expose_rate_limits": bool(headers),
        }
    except RuntimeError as exc:
        payload["live_probe"] = {
            "status": "error",
            "error": str(exc),
        }
    return payload


def chat_completion(
    prompt: str,
    config: Mapping[str, Any] | None = None,
    cancel: threading.Event | None = None,
) -> str:
    """
    [ACTION]
    - Teleology: Send one prompt through NVIDIA's hosted OpenAI-compatible chat endpoint and normalize the assistant reply into plain text.
    - Mechanism: Builds a minimal messages payload, applies config/env model defaults, posts to `/v1/chat/completions`, and extracts the first choice's message content.
    - Guarantee: Returns stripped assistant text for successful responses.
    - Fails: Raises RuntimeError for missing auth, HTTP/transport failures, or malformed JSON payloads; raises InterruptedError if the shared cancel event is set.
    - When-needed: Open when a local provider path wants a cheap hosted chat model for internal non-production work without using the browser bridge.
    - Escalates-to: system/lib/agent_providers.py::ask_nvidia
    """
    cfg = dict(config or {})
    api_key = _resolve_api_key(cfg)
    base_url = str(_config_value(cfg, "base_url", "NVIDIA_CHAT_BASE_URL", DEFAULT_CHAT_BASE_URL)).rstrip("/")
    model = _normalize_model_id(
        str(_config_value(cfg, "model", "NVIDIA_CHAT_MODEL", DEFAULT_CHAT_MODEL)).strip()
    )
    timeout_s = int(_config_value(cfg, "timeout_s", "NVIDIA_CHAT_TIMEOUT_S", DEFAULT_CHAT_TIMEOUT_S))

    messages = cfg.get("messages")
    if messages is None:
        messages = []
        system_prompt = cfg.get("system_prompt")
        if system_prompt:
            messages.append({"role": "system", "content": str(system_prompt)})
        messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if model.startswith("z-ai/glm") and "chat_template_kwargs" not in cfg:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    # Wave 11: NVIDIA NIM supports JSON-Schema-constrained outputs via the
    # `nvext` extension to the OpenAI chat-completion body
    # (nvext.guided_json: <schema>). Forward it from cfg so callers that
    # carry typed-output schema requirements actually transmit them.
    for key in ("max_tokens", "temperature", "top_p", "seed", "response_format", "nvext"):
        if key in cfg and cfg[key] is not None:
            payload[key] = cfg[key]
    overrides = cfg.get("payload_overrides")
    if isinstance(overrides, Mapping):
        payload.update(overrides)

    data = _request_json(
        url=f"{base_url}/v1/chat/completions",
        payload=payload,
        timeout_s=timeout_s,
        api_key=api_key,
        cancel=cancel,
    )
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("NVIDIA NIM chat response did not include choices")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise RuntimeError("NVIDIA NIM chat response choice is malformed")
    message = first.get("message")
    if not isinstance(message, Mapping):
        raise RuntimeError("NVIDIA NIM chat response did not include a message")
    text = _normalize_message_content(message.get("content"))
    if not text:
        text = _normalize_message_content(message.get("reasoning_content"))
    if not text:
        raise RuntimeError("NVIDIA NIM chat response was empty")
    return text


def embed_texts(
    texts: Sequence[str],
    config: Mapping[str, Any] | None = None,
    cancel: threading.Event | None = None,
) -> list[list[float]]:
    """
    [ACTION]
    - Teleology: Create hosted NVIDIA embeddings for text or code chunks that can drive semantic routing or retrieval inside this repo.
    - Mechanism: Sends the input list plus model/input_type metadata to NVIDIA's retrieval endpoint and extracts the returned embedding vectors in order.
    - Guarantee: Returns one float-vector per returned data row.
    - Fails: Raises RuntimeError for missing auth, HTTP/transport failures, or malformed embedding payloads; raises InterruptedError if cancelled before/after the request.
    - When-needed: Open when low-cost semantic routing or corpus indexing needs an external embedding service rather than a local embedding model.
    - Escalates-to: docs/nvidia_nim_backend.md
    """
    cfg = dict(config or {})
    if not texts:
        return []

    api_key = _resolve_api_key(cfg)
    url = str(
        _config_value(
            cfg,
            "embeddings_url",
            "NVIDIA_EMBEDDINGS_URL",
            DEFAULT_EMBEDDINGS_URL,
        )
    ).strip()
    model = _normalize_model_id(
        str(_config_value(cfg, "model", "NVIDIA_EMBED_MODEL", DEFAULT_EMBED_MODEL)).strip()
    )
    timeout_s = int(_config_value(cfg, "timeout_s", "NVIDIA_EMBED_TIMEOUT_S", DEFAULT_EMBED_TIMEOUT_S))
    input_type = _config_value(cfg, "input_type", "NVIDIA_EMBED_INPUT_TYPE", "passage")

    payload: dict[str, Any] = {
        "model": model,
        "input": [str(item) for item in texts],
        "encoding_format": "float",
    }
    if input_type:
        payload["input_type"] = str(input_type)
    if "truncate" in cfg and cfg["truncate"] is not None:
        payload["truncate"] = cfg["truncate"]

    data = _request_json(
        url=url,
        payload=payload,
        timeout_s=timeout_s,
        api_key=api_key,
        cancel=cancel,
    )
    rows = data.get("data")
    if not isinstance(rows, list):
        raise RuntimeError("NVIDIA NIM embeddings response did not include data")

    embeddings: list[list[float]] = []
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("embedding"), list):
            raise RuntimeError("NVIDIA NIM embeddings response row is malformed")
        embeddings.append([float(value) for value in row["embedding"]])
    return embeddings


def rerank_passages(
    query: str,
    passages: Sequence[str],
    config: Mapping[str, Any] | None = None,
    cancel: threading.Event | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Call NVIDIA's retrieval reranking endpoint for query/passage
      candidate selection before an LLM route judge spends tokens.
    - Mechanism: Sends a query object plus up to 512 passage objects to
      `/v1/retrieval/nvidia/reranking` and normalizes common response shapes
      into `{index, score, text}` rows.
    - Guarantee: Returns rows sorted by provider order when the endpoint is
      available; callers must treat scores as retrieval hints, not route truth.
    - Fails: Raises RuntimeError for missing auth, endpoint/transport failures,
      or malformed response payloads.
    """
    cfg = dict(config or {})
    if not passages:
        return []

    api_key = _resolve_api_key(cfg)
    url = str(
        _config_value(
            cfg,
            "rerankings_url",
            "NVIDIA_RERANKINGS_URL",
            DEFAULT_RERANKINGS_URL,
        )
    ).strip()
    model = _normalize_model_id(
        str(_config_value(cfg, "model", "NVIDIA_RERANK_MODEL", DEFAULT_RERANK_MODEL)).strip()
    )
    timeout_s = int(_config_value(cfg, "timeout_s", "NVIDIA_RERANK_TIMEOUT_S", DEFAULT_RERANK_TIMEOUT_S))

    payload: dict[str, Any] = {
        "model": model,
        "query": {"text": str(query)},
        "passages": [{"text": str(item)} for item in passages[:512]],
    }
    if "truncate" in cfg and cfg["truncate"] is not None:
        payload["truncate"] = cfg["truncate"]

    data = _request_json(
        url=url,
        payload=payload,
        timeout_s=timeout_s,
        api_key=api_key,
        cancel=cancel,
    )
    rows = data.get("rankings") or data.get("data") or data.get("results")
    if not isinstance(rows, list):
        raise RuntimeError("NVIDIA NIM reranking response did not include ranking rows")

    normalized: list[dict[str, Any]] = []
    for position, row in enumerate(rows):
        if not isinstance(row, Mapping):
            continue
        index = _positive_int(row.get("index"))
        if index is None:
            index = _positive_int(row.get("passage_index"))
        if index is None:
            index = _positive_int(row.get("document_index"))
        if index is None:
            index = position
        score_value = row.get("score")
        if score_value is None:
            score_value = row.get("relevance_score")
        if score_value is None:
            score_value = row.get("logit")
        try:
            score = float(score_value)
        except (TypeError, ValueError):
            score = 0.0
        normalized.append(
            {
                "index": int(index),
                "score": score,
                "text": passages[int(index)] if int(index) < len(passages) else "",
                "raw": dict(row),
            }
        )
    return normalized
