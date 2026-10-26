"""
[PURPOSE]
- Teleology: Canonicalize authored mission dispatch-policy metadata into one
  runtime helper that separates backlog cohort sizing from in-flight wave width
  and enforces provider ceilings from bridge capabilities.
- Mechanism: Read mission-pack dispatch_policy metadata plus
  `tools/meta/bridge/provider_capabilities.json`, expose summary helpers, and
  resolve operator-requested wave widths into either an allowed effective width
  or a structured pre-dispatch rejection payload.
- Non-goal: Selecting backlog cohorts or launching any bridge work. This module
  only owns dispatch-policy interpretation and provider-ceiling enforcement.

[INTERFACE]
- Exports capability loading, ceiling summaries, dispatch-policy summaries, and resolve_dispatch_policy.
- Returns effective_wave_width or a structured rejection with provider_ceiling and status.

[FLOW]
- Mechanism: Normalize requested width, read provider ceiling, resolve auto from mission defaults, and reject invalid or over-ceiling explicit widths.

[DEPENDENCIES]
- Reads: tools/meta/bridge/provider_capabilities.json and caller-supplied mission dispatch_policy.

[CONSTRAINTS]
- Writes: None; no work is launched.
- Fails: Bad width and ceiling violations return typed policy envelopes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROVIDER_CAPABILITIES_REL = "tools/meta/bridge/provider_capabilities.json"


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_provider_capabilities_path(provider_capabilities_path: str | Path | None = None) -> Path:
    token = Path(provider_capabilities_path or DEFAULT_PROVIDER_CAPABILITIES_REL)
    if not token.is_absolute():
        token = REPO_ROOT / token
    return token.resolve()


def load_provider_capabilities(
    provider_capabilities_path: str | Path | None = None,
) -> dict[str, Any]:
    return _load_json(_resolve_provider_capabilities_path(provider_capabilities_path))


def provider_ceiling_summary(
    provider_capabilities_path: str | Path | None = None,
) -> dict[str, int]:
    capabilities = load_provider_capabilities(provider_capabilities_path)
    providers = capabilities.get("providers") if isinstance(capabilities.get("providers"), Mapping) else {}
    ceilings: dict[str, int] = {}
    for provider, payload in providers.items():
        if not isinstance(payload, Mapping):
            continue
        value = payload.get("safe_parallelism")
        if isinstance(value, int) and value > 0:
            ceilings[_string(provider) or str(provider)] = value
    return ceilings


def provider_ceiling_for_provider(
    provider: str,
    provider_capabilities_path: str | Path | None = None,
) -> int | None:
    ceilings = provider_ceiling_summary(provider_capabilities_path)
    token = _string(provider).strip()
    if not token:
        return None
    value = ceilings.get(token)
    if isinstance(value, int) and value > 0:
        return value
    return None


def _extract_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    token = _string(value).strip()
    if token.isdigit():
        parsed = int(token)
        return parsed if parsed > 0 else None
    return None


def _policy_default(
    mission_dispatch_policy: Mapping[str, Any] | None,
    field_name: str,
) -> int | None:
    if not isinstance(mission_dispatch_policy, Mapping):
        return None
    value = mission_dispatch_policy.get(field_name)
    direct = _extract_positive_int(value)
    if direct is not None:
        return direct
    if not isinstance(value, Mapping):
        return None
    for key in ("default_for_this_mission", "default", "value"):
        parsed = _extract_positive_int(value.get(key))
        if parsed is not None:
            return parsed
    return None


def _policy_text(
    mission_dispatch_policy: Mapping[str, Any] | None,
    field_name: str,
    key: str,
) -> str | None:
    if not isinstance(mission_dispatch_policy, Mapping):
        return None
    field = mission_dispatch_policy.get(field_name)
    if not isinstance(field, Mapping):
        return None
    token = _string(field.get(key)).strip()
    return token or None


def summarize_dispatch_policy(
    *,
    mission_dispatch_policy: Mapping[str, Any] | None,
    provider_capabilities_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_capabilities_path = _resolve_provider_capabilities_path(provider_capabilities_path)
    try:
        capabilities_rel = resolved_capabilities_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        capabilities_rel = resolved_capabilities_path.as_posix()
    return {
        "mission_id": _string(
            (mission_dispatch_policy or {}).get("mission_id")
        ).strip()
        or None,
        "cohort_size_default": _policy_default(mission_dispatch_policy, "cohort_size"),
        "mission_default_wave_width": _policy_default(mission_dispatch_policy, "wave_width"),
        "operator_soft_cap_recommendation": (
            _policy_text(mission_dispatch_policy, "wave_width", "operator_soft_cap_recommendation")
            or _string((mission_dispatch_policy or {}).get("operator_soft_cap_recommendation")).strip()
            or None
        ),
        "contract_note": _string((mission_dispatch_policy or {}).get("contract_note")).strip() or None,
        "frontend_surface_note": _string(
            (mission_dispatch_policy or {}).get("frontend_surface_note")
        ).strip()
        or None,
        "provider_ceiling_source": capabilities_rel,
        "provider_ceilings": provider_ceiling_summary(resolved_capabilities_path),
    }


def resolve_dispatch_policy(
    *,
    mission_dispatch_policy: Mapping[str, Any] | None,
    provider: str,
    requested_wave_width: Any,
    provider_capabilities_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_provider = _string(provider).strip() or "chatgpt"
    resolved_capabilities_path = _resolve_provider_capabilities_path(provider_capabilities_path)
    try:
        capabilities_rel = resolved_capabilities_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        capabilities_rel = resolved_capabilities_path.as_posix()

    mission_default_wave_width = _policy_default(mission_dispatch_policy, "wave_width")
    provider_ceiling = provider_ceiling_for_provider(
        resolved_provider,
        resolved_capabilities_path,
    )
    if provider_ceiling is None:
        provider_ceiling = mission_default_wave_width or 1

    requested = requested_wave_width
    if isinstance(requested, str) and requested.strip().lower() == "auto":
        requested = "auto"
    elif requested in (None, ""):
        requested = "auto"

    if requested == "auto":
        resolved_wave_width = mission_default_wave_width or provider_ceiling
    else:
        resolved_wave_width = _extract_positive_int(requested)
        if resolved_wave_width is None:
            return {
                "requested_wave_width": requested_wave_width,
                "effective_wave_width": None,
                "provider_ceiling": int(provider_ceiling),
                "status": "rejected",
                "error_code": "invalid_wave_width",
                "mission_default_wave_width": mission_default_wave_width,
                "operator_soft_cap_recommendation": (
                    _policy_text(mission_dispatch_policy, "wave_width", "operator_soft_cap_recommendation")
                    or None
                ),
                "mission_id": _string((mission_dispatch_policy or {}).get("mission_id")).strip() or None,
                "provider": resolved_provider,
                "provider_ceiling_source": capabilities_rel,
            }

    if resolved_wave_width > provider_ceiling:
        return {
            "requested_wave_width": requested_wave_width,
            "effective_wave_width": None,
            "provider_ceiling": int(provider_ceiling),
            "status": "rejected",
            "error_code": "wave_width_exceeds_provider_ceiling",
            "mission_default_wave_width": mission_default_wave_width,
            "operator_soft_cap_recommendation": (
                _policy_text(mission_dispatch_policy, "wave_width", "operator_soft_cap_recommendation")
                or None
            ),
            "mission_id": _string((mission_dispatch_policy or {}).get("mission_id")).strip() or None,
            "provider": resolved_provider,
            "provider_ceiling_source": capabilities_rel,
        }

    return {
        "requested_wave_width": requested_wave_width,
        "effective_wave_width": int(resolved_wave_width),
        "provider_ceiling": int(provider_ceiling),
        "status": "ok",
        "error_code": None,
        "mission_default_wave_width": mission_default_wave_width,
        "operator_soft_cap_recommendation": (
            _policy_text(mission_dispatch_policy, "wave_width", "operator_soft_cap_recommendation")
            or None
        ),
        "mission_id": _string((mission_dispatch_policy or {}).get("mission_id")).strip() or None,
        "provider": resolved_provider,
        "provider_ceiling_source": capabilities_rel,
    }
