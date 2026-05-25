from __future__ import annotations

from system.lib.controller_heartbeat import (
    CONTROLLER_HEARTBEAT_FIELDS,
    ControllerHeartbeatDeduper,
    build_controller_heartbeat,
    count_sentences,
    controller_heartbeat_event_id,
    validate_controller_heartbeat,
    wrap_response_schema_with_heartbeat_ref,
)


def _build_heartbeat() -> dict[str, object]:
    return build_controller_heartbeat(
        family_id="09",
        family_dir="obsidian/workstream/09 - Live Family",
        phase_id="09_35",
        phase_title="Phase 09.35 - Active Runtime",
        phase_dir="obsidian/workstream/09 - Live Family/09.35 - Active Runtime",
        wave_id="09_35_wave_002",
        execution_mode="hybrid",
        objective="Land the controller heartbeat proof lane.",
        bounded_question="What is the smallest bounded bridge proof?",
        next_step_posture="the next bounded live proof",
        updated_at="2026-04-20T03:20:00+00:00",
        family_charter_path="obsidian/workstream/09 - Live Family/family_charter.json",
        autonomous_seed_path="obsidian/workstream/09 - Live Family/autonomous_seed.json",
        synth_seed_path="obsidian/workstream/09 - Live Family/09.35 - Active Runtime/synth_seed.json",
    )


def test_build_controller_heartbeat_emits_exactly_five_sentences_per_field() -> None:
    heartbeat = _build_heartbeat()

    errors = validate_controller_heartbeat(heartbeat)

    assert errors == []
    for field in CONTROLLER_HEARTBEAT_FIELDS:
        assert count_sentences(heartbeat[field]) == 5
    assert heartbeat["event_id"] == controller_heartbeat_event_id(heartbeat)


def test_validate_controller_heartbeat_rejects_under_and_over_count_cases() -> None:
    heartbeat = _build_heartbeat()
    heartbeat["problem"] = "One. Two. Three. Four."
    heartbeat["action"] = "One. Two. Three. Four. Five. Six."

    errors = validate_controller_heartbeat(heartbeat)

    assert "problem must contain exactly 5 sentences (found 4)." in errors
    assert "action must contain exactly 5 sentences (found 6)." in errors


def test_controller_heartbeat_event_id_ignores_updated_at_but_detects_semantic_changes() -> None:
    heartbeat = _build_heartbeat()
    newer = dict(heartbeat, updated_at="2026-04-20T03:21:00+00:00")
    changed = dict(heartbeat, wave_id="09_35_wave_003")

    assert controller_heartbeat_event_id(newer) == heartbeat["event_id"]
    assert controller_heartbeat_event_id(changed) != heartbeat["event_id"]

    changed["event_id"] = heartbeat["event_id"]
    errors = validate_controller_heartbeat(changed)
    assert "event_id does not match the canonical controller heartbeat identity." in errors


def test_controller_heartbeat_deduper_suppresses_repeats_with_ttl_and_lru_budget() -> None:
    heartbeat = _build_heartbeat()
    deduper = ControllerHeartbeatDeduper(ttl_seconds=10, max_entries=2)

    first = deduper.register(heartbeat, now=100.0)
    second = deduper.register(heartbeat, now=105.0)
    expired = deduper.register(heartbeat, now=116.0)
    deduper.register("manual_event_1", now=117.0)
    final = deduper.register("manual_event_2", now=118.0)

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert expired["duplicate"] is False
    assert final["seen_count"] == 2


def test_wrap_response_schema_with_heartbeat_ref_envelopes_payload_once() -> None:
    wrapped = wrap_response_schema_with_heartbeat_ref(
        {
            "type": "object",
            "required": ["shards"],
            "properties": {
                "shards": {"type": "array"},
            },
        }
    )

    assert wrapped["required"] == ["heartbeat_ref", "payload"]
    assert wrapped["properties"]["payload"]["required"] == ["shards"]
    assert wrap_response_schema_with_heartbeat_ref(wrapped) == wrapped
