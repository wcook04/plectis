from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from microcosm_core.macro_tools.agent_observability_classification import (
    PASS,
    build_public_agent_observability_classification_view,
    body_import_verification,
    classify_telemetry_quality,
    main,
    noisy_session_ids_from_classes,
)


NOW = datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc)


def _auth_failure_events() -> list[dict[str, object]]:
    return [
        {
            "seq": 1,
            "source_runtime": "claude_code",
            "canonical_type": "message.assistant",
            "session_id": "sdk-loop",
            "cwd": "/tmp/.claude-mem/observer-sessions/run-a",
            "observed_at": "2026-05-31T08:59:00+00:00",
            "payload": {
                "content": (
                    "Failed to authenticate request: 401 authentication_error."
                )
            },
        },
        {
            "seq": 2,
            "source_runtime": "claude_code",
            "canonical_type": "message.assistant",
            "session_id": "sdk-loop",
            "cwd": "/tmp/.claude-mem/observer-sessions/run-a",
            "observed_at": "2026-05-31T08:59:20+00:00",
            "payload": {
                "content": (
                    "Failed to authenticate request: 401 authentication_error."
                )
            },
        },
        {
            "seq": 3,
            "source_runtime": "codex_app",
            "canonical_type": "tool.completed",
            "session_id": "useful-session",
            "cwd": "/repo",
            "observed_at": "2026-05-31T08:59:40+00:00",
            "payload": {"tool_name": "Bash"},
        },
    ]


def test_public_classifier_preserves_auth_failure_and_stale_source_contract() -> None:
    quality = classify_telemetry_quality(
        events=_auth_failure_events(),
        source_status=[
            {
                "source_runtime": "claude_code",
                "last_observed_at": "2026-05-31T08:30:00+00:00",
                "event_count": 12,
            }
        ],
        now=NOW,
        stale_source_after_s=60,
    )

    assert quality["schema_version"] == "agent_observability_classification_v0"
    assert quality["noise_classes"][0]["class_id"] == "auth_failure_loop"
    assert noisy_session_ids_from_classes(quality["noise_classes"]) == {"sdk-loop"}
    assert quality["stale_sources"] == [
        {
            "source_runtime": "claude_code",
            "last_observed_at": "2026-05-31T08:30:00+00:00",
            "lag_s": 1800.0,
            "event_count": 12,
            "stale_after_s": 60,
        }
    ]
    assert quality["canonical_type_counts"]["message.assistant"] == 2


def test_public_view_reports_projection_warnings_without_reading_live_state() -> None:
    view = build_public_agent_observability_classification_view(
        {
            "bundle_manifest": {
                "bundle_id": "public-observability-classification-fixture",
                "generated_at": "2026-05-31T09:00:00+00:00",
            },
            "public_agent_events": {"events": _auth_failure_events()},
            "source_status": {
                "source_status": [
                    {
                        "source_runtime": "codex_app",
                        "last_observed_at": "2026-05-31T08:59:00+00:00",
                        "event_count": 3,
                    }
                ],
                "persistence_status": {
                    "error_count": 1,
                    "last_error": "permission denied",
                },
                "gap_count": 1,
                "dropped_count": 2,
                "history_limit_used": 200,
            },
            "telemetry_policy": {
                "public_metadata_only": True,
                "stale_source_after_s": 60,
                "now": "2026-05-31T09:00:00+00:00",
            },
        }
    )

    assert view["status"] == PASS
    assert view["metadata_envelope_only"] is True
    assert view["live_home_session_logs_read"] is False
    assert view["provider_payload_exported"] is False
    assert view["noisy_session_ids"] == ["sdk-loop"]
    warning_kinds = {
        row["kind"] for row in view["telemetry_quality"]["projection_warnings"]
    }
    assert warning_kinds == {"persistence_errors", "events_dropped", "stream_gaps"}
    assert view["telemetry_quality"]["history_limit_used"] == 200


def test_public_view_blocks_private_payload_keys() -> None:
    view = build_public_agent_observability_classification_view(
        {
            "public_agent_events": {
                "events": [
                    {
                        "seq": 1,
                        "source_runtime": "codex_app",
                        "canonical_type": "message.assistant",
                        "session_id": "private-row",
                        "cwd": "/repo",
                        "observed_at": "2026-05-31T09:00:00+00:00",
                        "payload": {"provider_payload": {"secret": "body"}},
                    }
                ]
            },
            "source_status": {"source_status": []},
            "telemetry_policy": {"public_metadata_only": True},
        },
        now=NOW,
    )

    assert view["status"] == "blocked"
    assert view["forbidden_payload_keys"] == ["provider_payload"]
    assert {
        finding["error_code"] for finding in view["findings"]
    } == {"AGENT_OBSERVABILITY_CLASSIFICATION_FORBIDDEN_PAYLOAD_KEY"}


def test_public_cli_validates_bundle(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    (tmp_path / "bundle_manifest.json").write_text(
        json.dumps(
            {
                "bundle_id": "public-observability-classification-cli-fixture",
                "generated_at": "2026-05-31T09:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "public_agent_events.json").write_text(
        json.dumps({"events": _auth_failure_events()}),
        encoding="utf-8",
    )
    (tmp_path / "source_status.json").write_text(
        json.dumps({"source_status": []}),
        encoding="utf-8",
    )
    (tmp_path / "telemetry_policy.json").write_text(
        json.dumps({"public_metadata_only": True}),
        encoding="utf-8",
    )

    assert main(["validate-public-bundle", "--input", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "public_agent_observability_classification"
    assert payload["status"] == PASS


def test_body_import_verification_cites_private_source_and_public_target() -> None:
    verification = body_import_verification()

    assert verification["source_ref"] == "system/lib/agent_observability_classification.py"
    assert (
        verification["target_ref"]
        == "microcosm-substrate/src/microcosm_core/macro_tools/"
        "agent_observability_classification.py"
    )
    assert verification["body_in_receipt"] is False
