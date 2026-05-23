from __future__ import annotations

from typing import Any


SOURCE_OPEN_BODY_POLICY = (
    "source_open_except_secret_credential_provider_account_session_and_live_access_payloads"
)

EXCLUDED_PUBLIC_PAYLOAD_CLASSES = [
    "secrets",
    "api_keys",
    "credentials",
    "cookies",
    "account_session_state",
    "provider_payload_bodies",
    "browser_or_hud_live_access_material",
    "recipient_send_state",
    "credential_equivalent_payloads",
]


def public_payload_boundary(
    *,
    boundary_id: str,
    command: str,
    surface_ref: str | None = None,
    legacy_schema_compat_present: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "microcosm_public_payload_boundary_v1",
        "boundary_id": boundary_id,
        "command": command,
        "surface_ref": surface_ref,
        "source_open_default": True,
        "body_policy": SOURCE_OPEN_BODY_POLICY,
        "unsafe_payload_bodies_in_receipt": False,
        "non_secret_macro_substrate_expected": True,
        "metadata_only_standin_authorized": False,
        "synthetic_fixture_policy": "negative_case_or_regression_harness_only",
        "public_refs_are_drilldowns_not_replacements": True,
        "excluded_public_payload_classes": EXCLUDED_PUBLIC_PAYLOAD_CLASSES,
        "secrets_exported": False,
        "credential_equivalent_payloads_exported": False,
        "provider_payload_bodies_exported": False,
        "account_session_state_exported": False,
        "browser_or_hud_live_access_exported": False,
        "recipient_send_state_exported": False,
        "legacy_schema_compat_present": legacy_schema_compat_present,
    }
