"""
Guarded OpenRouter metadata, quota, and explicit chat smoke runtime.

[PURPOSE]
- Teleology: Let the repo discover current OpenRouter free-model capacity
  and perform bounded, explicit inference smoke calls without turning
  OpenRouter into an ungoverned paid provider.
- Mechanism: Read repo-local OPENROUTER_* config, call metadata/key-status
  endpoints, filter models to zero-cost/free-router surfaces, derive a
  conservative throughput envelope from OpenRouter's published free limits,
  and expose a chat/completions helper that defaults to no-spend/free-model
  posture unless the caller passes an explicit paid-call gate.

[CONSTRAINTS]
- Guarantee: Metadata/status probes never call inference endpoints.
- Safety: Chat calls are explicit, free-only by default, and reject paid model
  ids unless `allow_paid` is true and `free_only` is false for that call.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "https://openrouter.ai"
DEFAULT_STATE_ROOT = "state/openrouter_free_runtime"
DEFAULT_TOP_N = 20
DEFAULT_CHAT_MODEL = FREE_ROUTER_MODEL_ID = "openrouter/free"
DEFAULT_CHAT_MAX_TOKENS = 64
DEFAULT_CHAT_TIMEOUT_S = 60
LONG_CONTEXT_THRESHOLD = 128_000
FREE_MODEL_BURST_RPM = 20
FREE_TIER_REQUESTS_PER_DAY = 50
PAID_HISTORY_FREE_REQUESTS_PER_DAY = 1000

HttpGet = Callable[[str, Mapping[str, str], int], Mapping[str, Any]]
HttpPost = Callable[[str, Mapping[str, str], Mapping[str, Any], int], Mapping[str, Any]]
_DOTENV_LOADED = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    if config and config.get(key) not in (None, ""):
        return config[key]
    _ensure_env_loaded()
    value = os.environ.get(env_var)
    return value if value not in (None, "") else default


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _positive_int(value: Any, *, default: int = DEFAULT_TOP_N) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value if value > 0 else default
    token = str(value or "").strip()
    if token.isdigit():
        parsed = int(token)
        return parsed if parsed > 0 else default
    return default


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _default_http_get(url: str, headers: Mapping[str, str], timeout_s: int) -> Mapping[str, Any]:
    try:
        response = requests.get(url, headers=dict(headers), timeout=timeout_s)
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            body = (exc.response.text or "").strip()
        detail = body[:500] if body else str(exc)
        raise RuntimeError(f"OpenRouter metadata request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenRouter metadata request failed: {exc}") from exc
    data = response.json()
    if not isinstance(data, Mapping):
        raise RuntimeError("OpenRouter returned a non-object JSON response")
    return data


def _default_http_post(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout_s: int,
) -> Mapping[str, Any]:
    try:
        response = requests.post(
            url,
            headers=dict(headers),
            json=dict(payload),
            timeout=timeout_s,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            body = (exc.response.text or "").strip()
        detail = body[:500] if body else str(exc)
        raise RuntimeError(f"OpenRouter chat request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenRouter chat request failed: {exc}") from exc
    data = response.json()
    if not isinstance(data, Mapping):
        raise RuntimeError("OpenRouter returned a non-object JSON response")
    return data


def _headers(api_key: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "ai_workflow-openrouter-free-probe/1.0",
    }
    token = str(api_key or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _chat_headers(api_key: str, config: Mapping[str, Any] | None = None) -> dict[str, str]:
    headers = _headers(api_key)
    headers["Content-Type"] = "application/json"
    site_url = str(_config_value(config, "site_url", "OPENROUTER_SITE_URL", "") or "").strip()
    app_title = str(_config_value(config, "app_title", "OPENROUTER_APP_TITLE", "ai_workflow") or "").strip()
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_title:
        headers["X-Title"] = app_title
    return headers


def _resolve_api_key(config: Mapping[str, Any] | None) -> str:
    token = _config_value(config, "api_key", "OPENROUTER_API_KEY", "")
    api_key = str(token or "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    return api_key


def _pricing_zero(pricing: Any) -> bool:
    if not isinstance(pricing, Mapping):
        return False
    checked = False
    for key, value in pricing.items():
        if key in {"internal_reasoning", "discount"}:
            continue
        parsed = _as_float(value)
        if parsed is None:
            continue
        checked = True
        if parsed != 0.0:
            return False
    return checked


def _model_is_free(row: Mapping[str, Any]) -> bool:
    model_id = str(row.get("id") or "").strip()
    if model_id == FREE_ROUTER_MODEL_ID:
        return True
    if model_id.endswith(":free"):
        return True
    return _pricing_zero(row.get("pricing"))


def _model_score(row: Mapping[str, Any]) -> tuple[int, int, int, int, str]:
    supported = row.get("supported_parameters")
    supported_count = len(supported) if isinstance(supported, list) else 0
    context = int(_as_float(row.get("context_length")) or 0)
    created = int(_as_float(row.get("created")) or 0)
    model_id = str(row.get("id") or "")
    suffix_bonus = 1 if model_id.endswith(":free") else 0
    router_bonus = 1 if model_id == FREE_ROUTER_MODEL_ID else 0
    return (router_bonus, suffix_bonus, supported_count, context + created, model_id)


def _model_outputs_text(row: Mapping[str, Any]) -> bool:
    architecture = row.get("architecture") if isinstance(row.get("architecture"), Mapping) else {}
    output_modalities = architecture.get("output_modalities")
    if not isinstance(output_modalities, list):
        return True
    return "text" in output_modalities


def _supports_any(row: Mapping[str, Any], names: set[str]) -> bool:
    supported = row.get("supported_parameters")
    if not isinstance(supported, list):
        return False
    return bool(names.intersection(str(item) for item in supported))


def _price_per_million_tokens(pricing: Mapping[str, Any], key: str) -> float:
    value = _as_float(pricing.get(key))
    if value is None:
        return 0.0
    return round(value * 1_000_000, 6)


def _pricing_per_million(row: Mapping[str, Any]) -> dict[str, float]:
    pricing = row.get("pricing") if isinstance(row.get("pricing"), Mapping) else {}
    prompt = _price_per_million_tokens(pricing, "prompt")
    completion = _price_per_million_tokens(pricing, "completion")
    return {
        "prompt": prompt,
        "completion": completion,
        "one_m_input_plus_one_m_output": round(prompt + completion, 6),
        "internal_reasoning": _price_per_million_tokens(pricing, "internal_reasoning"),
        "input_cache_read": _price_per_million_tokens(pricing, "input_cache_read"),
        "input_cache_write": _price_per_million_tokens(pricing, "input_cache_write"),
    }


def _pricing_unit_costs(row: Mapping[str, Any]) -> dict[str, float]:
    pricing = row.get("pricing") if isinstance(row.get("pricing"), Mapping) else {}
    return {
        "request": _as_float(pricing.get("request")) or 0.0,
        "image": _as_float(pricing.get("image")) or 0.0,
        "web_search": _as_float(pricing.get("web_search")) or 0.0,
    }


def _model_blended_text_cost(row: Mapping[str, Any]) -> tuple[float, float, float, str]:
    pricing = _pricing_per_million(row)
    return (
        pricing["one_m_input_plus_one_m_output"],
        pricing["completion"],
        pricing["prompt"],
        str(row.get("id") or ""),
    )


def _paid_text_model(row: Mapping[str, Any]) -> bool:
    if _model_is_free(row) or not _model_outputs_text(row):
        return False
    pricing = _pricing_per_million(row)
    return pricing["prompt"] > 0.0 or pricing["completion"] > 0.0


def _model_id_shape_is_free(model_id: str) -> bool:
    token = str(model_id or "").strip()
    return token == FREE_ROUTER_MODEL_ID or token.endswith(":free")


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


def _chat_messages(prompt: str, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_messages = cfg.get("messages")
    if isinstance(raw_messages, list):
        return [dict(item) for item in raw_messages if isinstance(item, Mapping)]
    messages: list[dict[str, Any]] = []
    system_prompt = cfg.get("system_prompt")
    if system_prompt:
        messages.append({"role": "system", "content": str(system_prompt)})
    messages.append({"role": "user", "content": str(prompt)})
    return messages


def _chat_cache_key(
    *,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    temperature: Any,
    schema_version: str = "openrouter_chat_completion_v1",
) -> str:
    material = {
        "schema_version": schema_version,
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    return hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _paid_gate(cfg: Mapping[str, Any], model: str) -> dict[str, Any]:
    free_only = _bool_value(_config_value(cfg, "free_only", "OPENROUTER_FREE_ONLY", "true"), default=True)
    allow_paid = _bool_value(_config_value(cfg, "allow_paid", "OPENROUTER_ALLOW_PAID", "false"), default=False)
    model_free = _model_id_shape_is_free(model)
    if model_free:
        return {
            "free_only": free_only,
            "allow_paid": allow_paid,
            "model_id_shape": "free",
            "paid_call_authorized": False,
        }
    if free_only or not allow_paid:
        raise RuntimeError(
            "OpenRouter paid model call blocked: pass allow_paid=true and free_only=false for this explicit call"
        )
    return {
        "free_only": free_only,
        "allow_paid": allow_paid,
        "model_id_shape": "paid_or_unknown",
        "paid_call_authorized": True,
    }


def _compact_market_model(row: Mapping[str, Any]) -> dict[str, Any]:
    model_id = str(row.get("id") or "").strip()
    architecture = row.get("architecture") if isinstance(row.get("architecture"), Mapping) else {}
    top_provider = row.get("top_provider") if isinstance(row.get("top_provider"), Mapping) else {}
    pricing = row.get("pricing") if isinstance(row.get("pricing"), Mapping) else {}
    return {
        "id": model_id,
        "name": str(row.get("name") or model_id),
        "context_length": row.get("context_length"),
        "created": row.get("created"),
        "pricing_zero": _pricing_zero(pricing),
        "free": _model_is_free(row),
        "pricing_usd_per_million_tokens": _pricing_per_million(row),
        "pricing_usd_per_unit": _pricing_unit_costs(row),
        "capability_flags": {
            "tools": _supports_any(row, {"tools"}),
            "structured_output": _supports_any(row, {"structured_outputs", "response_format"}),
            "reasoning": _supports_any(row, {"reasoning", "include_reasoning"}),
            "image_input": "image" in (architecture.get("input_modalities") or []),
            "file_input": "file" in (architecture.get("input_modalities") or []),
            "audio_input": "audio" in (architecture.get("input_modalities") or []),
            "video_input": "video" in (architecture.get("input_modalities") or []),
        },
        "top_provider": {
            "context_length": top_provider.get("context_length"),
            "max_completion_tokens": top_provider.get("max_completion_tokens"),
            "is_moderated": top_provider.get("is_moderated"),
        },
    }


def _rank_by_price(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            *_model_blended_text_cost(row),
            -(int(_as_float(row.get("context_length")) or 0)),
        ),
    )


def _rank_free_capable(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -int(_as_float(row.get("context_length")) or 0),
            -len(row.get("supported_parameters") if isinstance(row.get("supported_parameters"), list) else []),
            str(row.get("id") or ""),
        ),
    )


def _model_opportunity_snapshot(
    model_rows: list[Mapping[str, Any]],
    *,
    top_n: int = DEFAULT_TOP_N,
) -> dict[str, Any]:
    limit = max(int(top_n), 0)
    text_rows = [row for row in model_rows if _model_outputs_text(row)]
    free_rows = [row for row in text_rows if _model_is_free(row)]
    paid_rows = [row for row in text_rows if _paid_text_model(row)]
    tool_structured = [
        row
        for row in paid_rows
        if _supports_any(row, {"tools"}) and _supports_any(row, {"structured_outputs", "response_format"})
    ]
    free_tool_structured = [
        row
        for row in free_rows
        if _supports_any(row, {"tools"}) and _supports_any(row, {"structured_outputs", "response_format"})
    ]
    long_context = [
        row
        for row in paid_rows
        if int(_as_float(row.get("context_length")) or 0) >= LONG_CONTEXT_THRESHOLD
    ]
    return {
        "schema_version": "openrouter_model_opportunities_v1",
        "authority": "metadata_only_no_inference",
        "pricing_units": {
            "token_prices": "USD per million tokens derived from OpenRouter per-token model metadata",
            "unit_prices": "USD per request/image/web_search unit when present",
            "blended_sort": "one million prompt tokens plus one million completion tokens",
        },
        "counts": {
            "models_seen": len(model_rows),
            "text_output_models_seen": len(text_rows),
            "free_text_output_models_seen": len(free_rows),
            "paid_text_output_models_seen": len(paid_rows),
        },
        "limits": {
            "top_n": limit,
            "long_context_threshold": LONG_CONTEXT_THRESHOLD,
        },
        "free_tool_structured_long_context": [
            _compact_market_model(row) for row in _rank_free_capable(free_tool_structured)[:limit]
        ],
        "cheapest_paid_text": [
            _compact_market_model(row) for row in _rank_by_price(paid_rows)[:limit]
        ],
        "cheapest_paid_tool_structured": [
            _compact_market_model(row) for row in _rank_by_price(tool_structured)[:limit]
        ],
        "cheapest_paid_long_context": [
            _compact_market_model(row) for row in _rank_by_price(long_context)[:limit]
        ],
        "interpretation_notes": [
            "This packet ranks metadata, price, context, and parameter support only; it is not a quality benchmark.",
            "Use OpenRouter provider.sort=price or the :floor shortcut only inside an explicit chat/task packet with paid-call gating.",
            "Free model daily quota is account-tier scoped, so do not assume the free shortlist can be multiplied by model count.",
        ],
    }


def _compact_model(row: Mapping[str, Any]) -> dict[str, Any]:
    model_id = str(row.get("id") or "").strip()
    pricing = row.get("pricing") if isinstance(row.get("pricing"), Mapping) else {}
    architecture = row.get("architecture") if isinstance(row.get("architecture"), Mapping) else {}
    top_provider = row.get("top_provider") if isinstance(row.get("top_provider"), Mapping) else {}
    return {
        "id": model_id,
        "name": str(row.get("name") or model_id),
        "context_length": row.get("context_length"),
        "created": row.get("created"),
        "pricing_zero": _pricing_zero(pricing),
        "free_suffix": model_id.endswith(":free"),
        "free_router": model_id == FREE_ROUTER_MODEL_ID,
        "input_modalities": architecture.get("input_modalities"),
        "output_modalities": architecture.get("output_modalities"),
        "supported_parameters": row.get("supported_parameters") or [],
        "pricing_usd_per_million_tokens": _pricing_per_million(row),
        "pricing_usd_per_unit": _pricing_unit_costs(row),
        "capability_flags": {
            "tools": _supports_any(row, {"tools"}),
            "structured_output": _supports_any(row, {"structured_outputs", "response_format"}),
            "reasoning": _supports_any(row, {"reasoning", "include_reasoning"}),
            "image_input": "image" in (architecture.get("input_modalities") or []),
            "file_input": "file" in (architecture.get("input_modalities") or []),
            "audio_input": "audio" in (architecture.get("input_modalities") or []),
            "video_input": "video" in (architecture.get("input_modalities") or []),
        },
        "top_provider": {
            "context_length": top_provider.get("context_length"),
            "max_completion_tokens": top_provider.get("max_completion_tokens"),
            "is_moderated": top_provider.get("is_moderated"),
        },
    }


def _sanitize_key_info(raw: Mapping[str, Any]) -> dict[str, Any]:
    data = raw.get("data") if isinstance(raw.get("data"), Mapping) else raw
    if not isinstance(data, Mapping):
        return {}
    keep = (
        "limit",
        "limit_reset",
        "limit_remaining",
        "include_byok_in_limit",
        "usage",
        "usage_daily",
        "usage_weekly",
        "usage_monthly",
        "byok_usage",
        "byok_usage_daily",
        "byok_usage_weekly",
        "byok_usage_monthly",
        "is_free_tier",
    )
    sanitized = {key: data.get(key) for key in keep if key in data}
    if "limit" in sanitized:
        sanitized["credit_limit_usd"] = sanitized.get("limit")
    if "limit_remaining" in sanitized:
        sanitized["credit_limit_remaining_usd"] = sanitized.get("limit_remaining")
    sanitized["limit_field_interpretation"] = (
        "OpenRouter /api/v1/key `limit` is the API-key credit limit, not the daily free-model request cap."
    )
    return sanitized


def _derive_throughput(key_info: Mapping[str, Any] | None) -> dict[str, Any]:
    info = dict(key_info or {})
    is_free_tier = info.get("is_free_tier")
    if is_free_tier is False:
        daily_limit = PAID_HISTORY_FREE_REQUESTS_PER_DAY
        daily_source = "openrouter_docs_paid_history_free_variant_limit"
    else:
        daily_limit = FREE_TIER_REQUESTS_PER_DAY
        daily_source = "openrouter_docs_free_tier_default"
    safe_interval = 86400.0 / float(max(daily_limit, 1))
    return {
        "free_model_burst_requests_per_minute": FREE_MODEL_BURST_RPM,
        "free_model_daily_request_limit": daily_limit,
        "daily_limit_source": daily_source,
        "recommended_sustained_requests_per_minute": round(daily_limit / 1440.0, 4),
        "recommended_min_interval_seconds_for_always_on": round(safe_interval, 3),
        "daily_cap_binds_before_burst_cap": True,
        "scope_notes": [
            "OpenRouter documents free :free variants as 20 rpm with a daily account-tier cap.",
            "`/api/v1/key.limit` is the key credit limit in dollars; do not read it as the free-model daily request cap.",
            "Additional accounts or API keys do not increase global rate limits.",
            "Different free models may still experience independent upstream 429s, so rotate on provider errors but do not assume per-model daily quota multiplication.",
        ],
    }


def runtime_status(
    config: Mapping[str, Any] | None = None,
    *,
    probe_live: bool = False,
    include_models: bool = False,
    top_n: int = DEFAULT_TOP_N,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    cfg = dict(config or {})
    _ensure_env_loaded()
    api_key = str(_config_value(cfg, "api_key", "OPENROUTER_API_KEY", "") or "").strip()
    management_key = str(
        _config_value(cfg, "management_key", "OPENROUTER_MANAGEMENT_KEY", "") or ""
    ).strip()
    free_only = _bool_value(_config_value(cfg, "free_only", "OPENROUTER_FREE_ONLY", "true"), default=True)
    allow_paid = _bool_value(_config_value(cfg, "allow_paid", "OPENROUTER_ALLOW_PAID", "false"), default=False)
    base_url = str(_config_value(cfg, "base_url", "OPENROUTER_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
    timeout_s = _positive_int(_config_value(cfg, "timeout_s", "OPENROUTER_TIMEOUT_S", "30"), default=30)
    payload: dict[str, Any] = {
        "kind": "openrouter_free_runtime_status",
        "schema_version": "openrouter_free_runtime_status_v1",
        "generated_at": _utc_now(),
        "configured": {
            "api_key_present": bool(api_key),
            "management_key_present": bool(management_key),
            "base_url": base_url,
            "free_only": free_only,
            "allow_paid": allow_paid,
            "timeout_s": timeout_s,
        },
        "policy": {
            "status": "guarded_runtime_with_explicit_chat_gate",
            "no_spend_default": True,
            "allowed_model_id_shapes": [FREE_ROUTER_MODEL_ID, "*:free"],
            "forbidden_by_default": [
                "paid model ids unless allow_paid=true and free_only=false for the call",
                "private repo payloads",
                "ungoverned chat/completions without a typed task or smoke packet",
            ],
            "chat_completion": {
                "enabled": True,
                "default_model": DEFAULT_CHAT_MODEL,
                "default_max_tokens": DEFAULT_CHAT_MAX_TOKENS,
                "paid_gate": "paid/unknown model ids require allow_paid=true and free_only=false",
            },
        },
        "limits": _derive_throughput(None),
        "live_probe": {"status": "not_run", "reason": "probe_live_disabled"},
    }
    if not probe_live and not include_models:
        return payload

    getter = http_get or _default_http_get
    key_info: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    if probe_live and api_key:
        try:
            key_payload = getter(
                f"{base_url}/api/v1/key",
                _headers(api_key),
                timeout_s,
            )
            key_info = _sanitize_key_info(key_payload)
        except Exception as exc:
            errors.append({"endpoint": "/api/v1/key", "error": f"{type(exc).__name__}: {exc}"})
    if key_info:
        payload["key_info"] = key_info
        payload["limits"] = _derive_throughput(key_info)

    model_rows: list[Mapping[str, Any]] = []
    if include_models or probe_live:
        try:
            models_payload = getter(
                f"{base_url}/api/v1/models",
                _headers(None),
                timeout_s,
            )
            rows = models_payload.get("data")
            if isinstance(rows, list):
                model_rows = [row for row in rows if isinstance(row, Mapping)]
        except Exception as exc:
            errors.append({"endpoint": "/api/v1/models", "error": f"{type(exc).__name__}: {exc}"})
    free_rows = [row for row in model_rows if _model_is_free(row)]
    if free_only and not allow_paid:
        ranked_rows = free_rows
    else:
        ranked_rows = model_rows
    ranked_rows = sorted(ranked_rows, key=_model_score, reverse=True)
    payload["models"] = {
        "total_models_seen": len(model_rows),
        "free_models_seen": len(free_rows),
        "ranked_free_models": [_compact_model(row) for row in ranked_rows[: max(int(top_n), 0)]],
        "ranking_rule": "free-router/free-suffix first, then supported-parameter count, context length, creation timestamp",
        "free_filter": "model id is openrouter/free, ends with :free, or all numeric pricing fields are zero",
        "opportunity_snapshot": _model_opportunity_snapshot(model_rows, top_n=top_n),
    }
    payload["live_probe"] = {
        "status": "error" if errors else "ok",
        "errors": errors,
        "key_status_checked": bool(api_key),
        "models_checked": bool(model_rows),
    }
    return payload


def chat_completion_packet(
    prompt: str,
    config: Mapping[str, Any] | None = None,
    *,
    http_post: HttpPost | None = None,
) -> dict[str, Any]:
    """
    Run one explicit OpenRouter chat completion and return a redacted receipt packet.

    The default model is `openrouter/free`. Paid/unknown model ids are blocked
    unless the caller sets `allow_paid=true` and `free_only=false` in config or
    the corresponding environment variables for this call.
    """
    cfg = dict(config or {})
    api_key = _resolve_api_key(cfg)
    base_url = str(_config_value(cfg, "base_url", "OPENROUTER_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
    model = str(_config_value(cfg, "model", "OPENROUTER_CHAT_MODEL", DEFAULT_CHAT_MODEL) or "").strip()
    if not model:
        model = DEFAULT_CHAT_MODEL
    timeout_s = _positive_int(_config_value(cfg, "timeout_s", "OPENROUTER_CHAT_TIMEOUT_S", DEFAULT_CHAT_TIMEOUT_S), default=DEFAULT_CHAT_TIMEOUT_S)
    max_tokens = _positive_int(cfg.get("max_tokens"), default=DEFAULT_CHAT_MAX_TOKENS)
    temperature = cfg.get("temperature", 0)
    gate = _paid_gate(cfg, model)
    messages = _chat_messages(prompt, cfg)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    for key in (
        "top_p",
        "seed",
        "response_format",
        "stop",
        "tools",
        "tool_choice",
        "provider",
        "reasoning",
        "include_reasoning",
        "max_completion_tokens",
        "verbosity",
    ):
        if key in cfg and cfg[key] is not None:
            payload[key] = cfg[key]
    overrides = cfg.get("payload_overrides")
    if isinstance(overrides, Mapping):
        payload.update(overrides)

    cache_key = _chat_cache_key(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    poster = http_post or _default_http_post
    started_at = _utc_now()
    data = poster(
        f"{base_url}/api/v1/chat/completions",
        _chat_headers(api_key, cfg),
        payload,
        timeout_s,
    )
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenRouter chat response did not include choices")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise RuntimeError("OpenRouter chat response choice is malformed")
    message = first.get("message")
    if not isinstance(message, Mapping):
        raise RuntimeError("OpenRouter chat response did not include a message")
    text = _normalize_message_content(message.get("content"))
    if not text:
        text = _normalize_message_content(message.get("reasoning_content"))
    if not text:
        text = _normalize_message_content(message.get("reasoning"))
    empty_response = not bool(text)

    return {
        "kind": "openrouter_chat_completion",
        "schema_version": "openrouter_chat_completion_packet_v1",
        "status": "ok",
        "generated_at": _utc_now(),
        "started_at": started_at,
        "base_url": base_url,
        "model": data.get("model") or model,
        "requested_model": model,
        "free_or_paid_gate": gate,
        "cache_key": cache_key,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "usage": data.get("usage") if isinstance(data.get("usage"), Mapping) else {},
        "choices_seen": len(choices),
        "finish_reason": first.get("finish_reason"),
        "empty_response": empty_response,
        "message_keys": sorted(str(key) for key in message.keys()),
        "response_text": text,
    }


def chat_completion(
    prompt: str,
    config: Mapping[str, Any] | None = None,
    *,
    http_post: HttpPost | None = None,
) -> str:
    """Return only the assistant text for callers that use ask_ai-style providers."""
    return str(chat_completion_packet(prompt, config, http_post=http_post)["response_text"])


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_named_receipt(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    state_root: str = DEFAULT_STATE_ROOT,
    latest_name: str,
    ledger_name: str,
) -> dict[str, str]:
    root = Path(repo_root) / state_root
    latest = root / latest_name
    ledger = root / ledger_name
    _atomic_write_json(latest, dict(payload))
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "latest": str(latest.relative_to(repo_root)),
        "ledger": str(ledger.relative_to(repo_root)),
    }


def write_probe_receipt(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    state_root: str = DEFAULT_STATE_ROOT,
) -> dict[str, str]:
    refs = _write_named_receipt(
        repo_root,
        payload,
        state_root=state_root,
        latest_name="latest_probe.json",
        ledger_name="probe_ledger.jsonl",
    )
    return {
        "latest_probe": refs["latest"],
        "probe_ledger": refs["ledger"],
    }


def write_opportunities_receipt(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    state_root: str = DEFAULT_STATE_ROOT,
) -> dict[str, str]:
    refs = _write_named_receipt(
        repo_root,
        payload,
        state_root=state_root,
        latest_name="latest_opportunities.json",
        ledger_name="opportunities_ledger.jsonl",
    )
    return {
        "latest_opportunities": refs["latest"],
        "opportunities_ledger": refs["ledger"],
    }


def write_chat_receipt(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    state_root: str = DEFAULT_STATE_ROOT,
) -> dict[str, str]:
    refs = _write_named_receipt(
        repo_root,
        payload,
        state_root=state_root,
        latest_name="latest_chat_smoke.json",
        ledger_name="chat_smoke_ledger.jsonl",
    )
    return {
        "latest_chat_smoke": refs["latest"],
        "chat_smoke_ledger": refs["ledger"],
    }


def smoke_openrouter_chat(
    repo_root: Path,
    *,
    prompt: str = "Reply with exactly OPENROUTER_OK.",
    write: bool = False,
    config: Mapping[str, Any] | None = None,
    http_post: HttpPost | None = None,
) -> dict[str, Any]:
    payload = chat_completion_packet(prompt, config=config, http_post=http_post)
    payload["smoke_completed_at"] = _utc_now()
    if write:
        payload["artifact_refs"] = write_chat_receipt(repo_root, payload)
    return payload


def probe_openrouter_free_models(
    repo_root: Path,
    *,
    top_n: int = DEFAULT_TOP_N,
    write: bool = False,
    config: Mapping[str, Any] | None = None,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    payload = runtime_status(
        config=config,
        probe_live=True,
        include_models=True,
        top_n=top_n,
        http_get=http_get,
    )
    payload["probe_completed_at"] = _utc_now()
    payload["docs_assumptions"] = {
        "consulted_at": time.strftime("%Y-%m-%d", time.gmtime()),
        "free_variant_rpm": FREE_MODEL_BURST_RPM,
        "free_tier_daily_requests": FREE_TIER_REQUESTS_PER_DAY,
        "paid_history_free_variant_daily_requests": PAID_HISTORY_FREE_REQUESTS_PER_DAY,
    }
    if write:
        payload["artifact_refs"] = write_probe_receipt(repo_root, payload)
    return payload


def probe_openrouter_model_opportunities(
    repo_root: Path,
    *,
    top_n: int = DEFAULT_TOP_N,
    write: bool = False,
    config: Mapping[str, Any] | None = None,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    status = runtime_status(
        config=config,
        probe_live=True,
        include_models=True,
        top_n=top_n,
        http_get=http_get,
    )
    models = status.get("models") if isinstance(status.get("models"), Mapping) else {}
    payload: dict[str, Any] = {
        "kind": "openrouter_model_opportunities",
        "schema_version": "openrouter_model_opportunities_packet_v1",
        "generated_at": _utc_now(),
        "configured": status.get("configured") or {},
        "policy": status.get("policy") or {},
        "limits": status.get("limits") or {},
        "live_probe": status.get("live_probe") or {},
        "key_info": status.get("key_info") or {},
        "model_opportunities": models.get("opportunity_snapshot") or {},
        "docs_assumptions": {
            "consulted_at": time.strftime("%Y-%m-%d", time.gmtime()),
            "free_variant_rpm": FREE_MODEL_BURST_RPM,
            "free_tier_daily_requests": FREE_TIER_REQUESTS_PER_DAY,
            "paid_history_free_variant_daily_requests": PAID_HISTORY_FREE_REQUESTS_PER_DAY,
        },
    }
    if write:
        payload["artifact_refs"] = write_opportunities_receipt(repo_root, payload)
    return payload
