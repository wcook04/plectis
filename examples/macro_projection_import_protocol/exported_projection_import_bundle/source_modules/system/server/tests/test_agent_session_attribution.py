from __future__ import annotations

from datetime import datetime, timedelta, timezone

from system.lib.agent_session_attribution import (
    ATTRIBUTION_STATUS_ATS_ONLY,
    ATTRIBUTION_STATUS_INFRASTRUCTURE,
    ATTRIBUTION_STATUS_MATCHED,
    ATTRIBUTION_STATUS_UNATTRIBUTABLE,
    ATTRIBUTION_STATUS_WORKLEDGER_ONLY,
    LIVENESS_LIVE,
    LIVENESS_RECENT,
    LIVENESS_STALE,
    SCHEMA_VERSION,
    attribute_sessions,
    find_session_by_cwd,
    find_session_by_title,
    identify_self_session,
)


NOW = datetime(2026, 4, 25, 6, 30, 0, tzinfo=timezone.utc)


def _ts(seconds_ago: int) -> str:
    return (NOW - timedelta(seconds=seconds_ago)).isoformat(timespec="milliseconds")


def _ats(session_id: str, **overrides):
    base = {
        "session_id": session_id,
        "source_runtime": "claude_code",
        "last_observed_at": _ts(60),
        "last_activity_at": _ts(60),
        "last_canonical_type": "tool.completed",
        "title": None,
        "current_activity": None,
        "cwd": None,
        "transcript_path": None,
        "touched_files": [],
    }
    base.update(overrides)
    return base


def _wl(session_id: str, **overrides):
    base = {
        "session_id": session_id,
        "actor": "claude_code",
        "phase_id": "09_44",
        "family_id": "09",
        "last_activity_at": _ts(120),
        "stale": False,
        "stale_reason": None,
        "claims": [],
        "touched_td_ids": [],
    }
    base.update(overrides)
    return base


def test_direct_uuid_match_yields_matched_with_phase_attribution():
    ats = [_ats("uuid-A", title="fix concurrent agent warning data surfacing")]
    wl = {"sessions": {"uuid-A": _wl("uuid-A", phase_id="09_44")}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    assert view["schema_version"] == SCHEMA_VERSION
    sessions = view["sessions"]
    assert len(sessions) == 1
    s = sessions[0]
    assert s["attribution_status"] == ATTRIBUTION_STATUS_MATCHED
    assert s["phase_id"] == "09_44"
    assert s["actor"] == "claude_code"
    assert s["match_strategy"] == "direct_session_id"
    assert s["title"] == "fix concurrent agent warning data surfacing"


def test_codex_prefix_normalization_matches_across_stores():
    ats = [_ats("019dc1ab-cdef-7000-aaaa-000000000000", source_runtime="codex_app")]
    wl = {"sessions": {"codex:019dc1ab-cdef-7000-aaaa-000000000000": _wl(
        "codex:019dc1ab-cdef-7000-aaaa-000000000000", actor="codex",
    )}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["attribution_status"] == ATTRIBUTION_STATUS_MATCHED
    assert s["match_strategy"] == "codex_prefix_added"
    assert s["actor"] == "codex"


def test_ats_only_when_workledger_has_no_row():
    ats = [_ats("uuid-orphan")]
    wl = {"sessions": {}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["attribution_status"] == ATTRIBUTION_STATUS_ATS_ONLY
    assert s["phase_id"] is None


def test_workledger_only_session_appears_when_recent():
    ats = []
    wl = {"sessions": {"uuid-X": _wl("uuid-X", last_activity_at=_ts(120))}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    assert any(
        s["session_id"] == "uuid-X"
        and s["attribution_status"] == ATTRIBUTION_STATUS_WORKLEDGER_ONLY
        for s in view["sessions"]
    )


def test_workledger_only_stale_sessions_dropped_by_default():
    ats = []
    wl = {"sessions": {"uuid-old": _wl("uuid-old", last_activity_at=_ts(86400))}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    assert all(s["session_id"] != "uuid-old" for s in view["sessions"])

    audit = attribute_sessions(
        ats_active_sessions=ats,
        work_ledger_status=wl,
        now=NOW,
        include_stale_workledger_only=True,
    )
    stale = [s for s in audit["sessions"] if s["session_id"] == "uuid-old"][0]
    assert stale["liveness"] == LIVENESS_STALE
    assert stale["currently_live"] is False


def test_codex_app_stream_bucket_is_unattributable():
    ats = [_ats("codex_app", source_runtime="codex_app",
                last_canonical_type="session.snapshot")]
    wl = {"sessions": {}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["attribution_status"] == ATTRIBUTION_STATUS_UNATTRIBUTABLE
    assert s["match_strategy"] == "codex_stream_bucket"


def test_metabolism_source_is_classified_as_infrastructure():
    ats = [_ats("metabolism", source_runtime="metabolism",
                last_canonical_type="runtime.event")]
    wl = {"sessions": {}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["attribution_status"] == ATTRIBUTION_STATUS_INFRASTRUCTURE


def test_currently_live_excludes_session_end_events():
    ats = [_ats("uuid-A", last_canonical_type="session.end",
                last_observed_at=_ts(30))]
    wl = {"sessions": {"uuid-A": _wl("uuid-A")}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["liveness"] == LIVENESS_LIVE
    assert s["currently_live"] is False
    assert s["mid_turn"] is False


def test_mid_turn_set_when_live_and_in_tool_call():
    ats = [_ats("uuid-A", last_canonical_type="tool.proposed",
                last_observed_at=_ts(10))]
    wl = {"sessions": {"uuid-A": _wl("uuid-A")}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["currently_live"] is True
    assert s["mid_turn"] is True


def test_between_turn_marker_keeps_alive_but_not_mid_turn():
    ats = [_ats("uuid-A", last_canonical_type="turn.completed",
                last_observed_at=_ts(10))]
    wl = {"sessions": {"uuid-A": _wl("uuid-A")}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["currently_live"] is True
    assert s["mid_turn"] is False


def test_recent_window_keeps_session_alive_but_not_mid_turn():
    ats = [_ats("uuid-A", last_canonical_type="tool.completed",
                last_observed_at=_ts(900), last_activity_at=_ts(900))]
    wl = {"sessions": {"uuid-A": _wl("uuid-A", last_activity_at=_ts(900))}}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    s = view["sessions"][0]
    assert s["liveness"] == LIVENESS_RECENT
    assert s["currently_live"] is True
    assert s["mid_turn"] is False


def test_summary_counts_both_axes():
    ats = [
        _ats("uuid-A", title="A", last_canonical_type="tool.proposed",
             last_observed_at=_ts(5)),
        _ats("uuid-B", last_canonical_type="session.end",
             last_observed_at=_ts(5)),
        _ats("metabolism", source_runtime="metabolism"),
    ]
    wl = {"sessions": {
        "uuid-A": _wl("uuid-A"),
        "uuid-B": _wl("uuid-B"),
    }}

    view = attribute_sessions(
        ats_active_sessions=ats, work_ledger_status=wl, now=NOW,
    )

    by_status = view["summary"]["by_attribution_status"]
    assert by_status[ATTRIBUTION_STATUS_MATCHED] == 2
    assert by_status[ATTRIBUTION_STATUS_INFRASTRUCTURE] == 1


def test_find_session_by_title_picks_most_recent_match():
    sessions = [
        _ats("old-uuid", title="fix concurrent agent warning data surfacing",
             last_observed_at=_ts(3600), last_activity_at=_ts(3600)),
        _ats("new-uuid", title="fix concurrent agent warning data surfacing",
             last_observed_at=_ts(60), last_activity_at=_ts(60)),
        _ats("other-uuid", title="something else",
             last_observed_at=_ts(120), last_activity_at=_ts(120)),
    ]

    match = find_session_by_title(
        sessions, title_query="concurrent agent warning",
    )
    assert match is not None
    assert match["session_id"] == "new-uuid"


def test_find_session_by_title_searches_current_activity_too():
    sessions = [
        _ats("uuid-A", title=None, current_activity="Reading file foo.py"),
    ]
    match = find_session_by_title(sessions, title_query="reading file foo")
    assert match is not None
    assert match["session_id"] == "uuid-A"


def test_find_session_by_cwd_handles_path_prefix():
    sessions = [
        _ats("uuid-A", cwd="/Users/willcook/src/ai_workflow"),
        _ats("uuid-B", cwd="/Users/willcook/Desktop/ai_workflow",
             last_observed_at=_ts(30)),
    ]

    match = find_session_by_cwd(
        sessions, cwd="/Users/willcook/src/ai_workflow",
    )
    assert match is not None
    assert match["session_id"] == "uuid-A"

    deeper = find_session_by_cwd(
        sessions, cwd="/Users/willcook/src/ai_workflow/system/lib",
    )
    assert deeper is not None
    assert deeper["session_id"] == "uuid-A"


def test_identify_self_session_falls_back_from_title_to_cwd():
    sessions = [
        _ats("uuid-A", cwd="/Users/willcook/src/ai_workflow"),
    ]
    match = identify_self_session(
        sessions,
        title_fragment="this never appears",
        cwd="/Users/willcook/src/ai_workflow",
    )
    assert match is not None
    assert match["session_id"] == "uuid-A"
