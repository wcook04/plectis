from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from system.lib import navigation_trace
from system.lib.kernel.commands import embed


def _write_events(root, events):
    path = navigation_trace.events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def _minimal_attention_delta(surface="test_surface"):
    return {
        "seen_surface": surface,
        "selected_kind": "test_kind",
        "selected_band": "flag",
        "candidate_handles_seen_added": [],
        "focused_handles_added": [],
        "selected_handles_added": [],
        "trusted_authorities_added": [],
        "acted_on_handles_added": [],
        "rejected_handles_added": [],
        "stale_handles_added": [],
        "blocked_handles_added": [],
        "source_refs_added": [],
        "omissions_added": [],
        "freshness_constraints_added": [],
        "mutation_boundary": {},
        "next_legal_moves_added": [],
    }


def test_decision_hash_is_stable_for_normalized_query_and_targets() -> None:
    targets = [{"path": "codex/doctrine/paper_modules/unified_navigation_layer.md"}]

    first = navigation_trace.decision_hash(
        event_kind="docs_route",
        normalized_query=navigation_trace.normalize_query("  Navigation   Trace Binding "),
        phase_id="09_39",
        wave_id="09_39_wave_001",
        top_targets=targets,
    )
    second = navigation_trace.decision_hash(
        event_kind="docs_route",
        normalized_query=navigation_trace.normalize_query("navigation trace binding"),
        phase_id="09_39",
        wave_id="09_39_wave_001",
        top_targets=targets,
    )

    assert first == second


def test_record_event_compacts_targets_and_ignores_non_semantic_kinds(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AI_WORKFLOW_NAV_TRACE_SESSION", "test-session")
    payload = {
        "kind": "kernel.navigate",
        "routed_hits": [
            {"target_row_key": f"paper_modules:demo_{idx}:tldr", "target_source_path": f"docs/{idx}.md"}
            for idx in range(20)
        ],
    }

    event = navigation_trace.record_navigation_result(
        tmp_path,
        event_kind="navigate",
        query="navigation trace binding",
        command="kernel.py --navigate",
        payload=payload,
    )
    ignored = navigation_trace.record_navigation_event(
        tmp_path,
        event_kind="read",
        query="README.md",
        command="Read",
    )

    rows = navigation_trace.read_events(tmp_path)
    assert event is not None
    assert ignored is None
    assert len(rows) == 1
    assert rows[0]["session_id"] == "test-session"
    assert len(rows[0]["top_targets"]) == navigation_trace.MAX_EVENT_TARGETS


def test_replay_uses_salience_decay_for_recent_terms(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    base = {
        "schema_version": navigation_trace.SCHEMA_VERSION,
        "session_id": "s1",
        "event_kind": "docs_route",
        "command": "kernel.py --docs-route",
        "query": "placeholder",
        "phase": {},
        "top_targets": [],
        "payload_summary": {},
        "metadata": {},
    }
    _write_events(
        tmp_path,
        [
            {
                **base,
                "event_id": "old",
                "generated_at": (now - timedelta(days=2)).isoformat(),
                "query_normalized": "old context term",
                "lexical_terms": ["oldterm"],
                "decision_hash": "oldhash",
            },
            {
                **base,
                "event_id": "new",
                "generated_at": now.isoformat(),
                "query_normalized": "new context term",
                "lexical_terms": ["newterm"],
                "decision_hash": "newhash",
            },
        ],
    )

    replay = navigation_trace.build_replay(tmp_path, session="latest", limit=10)
    terms = replay["payload"]["top_lexical_terms"]

    assert terms[0]["value"] == "newterm"


def test_trace_cli_packets_read_trace_state(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(embed, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("AI_WORKFLOW_NAV_TRACE_SESSION", "cli-session")
    navigation_trace.record_navigation_result(
        tmp_path,
        event_kind="docs_route",
        query="navigation trace binding",
        command="kernel.py --docs-route",
        payload={
            "kind": "kernel.navigate.docs_route",
            "resolution": {"route_id": "sit_unified_navigation_layer"},
            "minimum_read_set": {
                "paths": ["codex/doctrine/paper_modules/unified_navigation_layer.md"]
            },
        },
    )
    navigation_trace.record_navigation_result(
        tmp_path,
        event_kind="docs_route",
        query="navigation trace binding",
        command="kernel.py --docs-route",
        payload={
            "kind": "kernel.navigate.docs_route",
            "resolution": {"route_id": "sit_unified_navigation_layer"},
            "minimum_read_set": {
                "paths": ["codex/doctrine/paper_modules/unified_navigation_layer.md"]
            },
        },
    )

    assert embed.cmd_navigation_trace_status() == 0
    status = json.loads(capsys.readouterr().out)
    assert status["event_count"] == 2

    assert embed.cmd_navigation_trace_replay("latest", limit=10) == 0
    replay = json.loads(capsys.readouterr().out)
    assert replay["payload"]["decision_chain"]

    assert embed.cmd_navigation_trace_convergence(last=10) == 0
    convergence = json.loads(capsys.readouterr().out)
    assert convergence["summary"]["loop_signal"] is True

    assert embed.cmd_navigation_trace_efficiency(last=10) == 0
    efficiency = json.loads(capsys.readouterr().out)
    assert efficiency["summary"]["event_count"] == 2


def test_attention_event_reduces_option_surface_lens_packet(tmp_path) -> None:
    payload = {
        "kind": "standard_owned_option_surface",
        "artifact_kind": "skills",
        "band": "card",
        "selection": {"mode": "ids", "ids": ["session_dump_assimilation"]},
        "source_refs": ["codex/doctrine/skills/skill_registry.json"],
        "lens_packet": {
            "view_profile": "option_surface_lens_packet_v0",
            "surface_id": "option_surface:skills",
            "source_payload_owner": {
                "source_refs": ["codex/doctrine/skills/skill_registry.json"],
                "source_mutation_allowed_by_this_profile": False,
            },
            "mutation_allowed_by_this_profile": False,
        },
        "rows": [
            {
                "id": "session_dump_assimilation",
                "row_id": "skills:session_dump_assimilation:card",
                "title": "Session Dump Assimilation",
                "drilldown_command": "./repo-python kernel.py --option-surface skills --band card --ids session_dump_assimilation",
            }
        ],
    }

    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_test",
        command="./repo-python kernel.py --option-surface skills --band card --ids session_dump_assimilation --attention-frame attn_test",
        payload=payload,
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_test", band="flag")

    assert event is not None
    assert event["status"] == "appended"
    assert frame["frame_id"] == "attn_test"
    assert frame["status"] == "ok"
    assert frame["summary"]["event_count"] == 1
    assert frame["seen_surfaces"] == ["option_surface:skills"]
    assert event["attention_delta"]["handle_source"] == "fallback_inference"
    assert frame["focused_handles"][0]["handle"] == "skill:session_dump_assimilation"
    assert frame["selected_handles"] == []
    assert frame["resumability"]["resume_command"] == "./repo-python kernel.py --attention-state attn_test --band flag"


def test_attention_cluster_rows_are_candidates_not_selected(tmp_path) -> None:
    payload = {
        "kind": "standard_owned_option_surface",
        "artifact_kind": "skills",
        "band": "cluster_flag",
        "selection": {"mode": "all"},
        "lens_packet": {
            "view_profile": "option_surface_lens_packet_v0",
            "surface_id": "option_surface:skills",
            "source_payload_owner": {"source_refs": ["codex/doctrine/skills/skill_registry.json"]},
        },
        "rows": [
            {
                "id": "session_dump_assimilation",
                "title": "Session Dump Assimilation",
                "drilldown_command": "./repo-python kernel.py --option-surface skills --band card --ids session_dump_assimilation",
            },
            {
                "id": "raw_seed_navigation",
                "title": "Raw Seed Navigation",
                "drilldown_command": "./repo-python kernel.py --option-surface skills --band card --ids raw_seed_navigation",
            },
        ],
    }

    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_candidates",
        command="./repo-python kernel.py --option-surface skills --band cluster_flag --attention-frame attn_candidates",
        payload=payload,
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_candidates", band="flag")

    assert event is not None
    candidates = {row["handle"] for row in frame["candidate_handles_seen"]}
    assert {"skill:session_dump_assimilation", "skill:raw_seed_navigation"} <= candidates
    assert frame["focused_handles"] == []
    assert frame["selected_handles"] == []


def test_attention_card_by_id_focuses_not_selects(tmp_path) -> None:
    payload = {
        "kind": "standard_owned_option_surface",
        "artifact_kind": "skills",
        "band": "card",
        "selection": {"mode": "ids", "ids": ["session_dump_assimilation"]},
        "lens_packet": {
            "view_profile": "option_surface_lens_packet_v0",
            "surface_id": "option_surface:skills",
            "source_payload_owner": {"source_refs": ["codex/doctrine/skills/skill_registry.json"]},
        },
        "rows": [
            {
                "canonical_handle": "skill:session_dump_assimilation",
                "id": "session_dump_assimilation",
                "title": "Session Dump Assimilation",
            }
        ],
    }

    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_focus",
        command="./repo-python kernel.py --option-surface skills --band card --ids session_dump_assimilation --attention-frame attn_focus",
        payload=payload,
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_focus", band="flag")

    assert event is not None
    assert event["attention_delta"]["handle_source"] == "canonical_handle"
    assert frame["candidate_handles_seen"] == []
    assert frame["focused_handles"][0]["handle"] == "skill:session_dump_assimilation"
    assert frame["selected_handles"] == []


def test_attention_explicit_selected_event_populates_selected_handles(tmp_path) -> None:
    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_selected",
        event_type="handle_selected",
        command="kernel.py --attention-select skill:session_dump_assimilation",
        attention_delta={
            "seen_surface": "operator_selection",
            "selected_kind": "skills",
            "selected_band": "selection",
            "candidate_handles_seen_added": [],
            "focused_handles_added": [],
            "selected_handles_added": [{"handle": "skill:session_dump_assimilation"}],
            "trusted_authorities_added": [],
            "acted_on_handles_added": [],
            "rejected_handles_added": [],
            "stale_handles_added": [],
            "blocked_handles_added": [],
            "source_refs_added": [],
            "omissions_added": [],
            "freshness_constraints_added": [],
            "mutation_boundary": {},
            "next_legal_moves_added": [],
        },
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_selected", band="flag")

    assert frame["selected_handles"] == [{"handle": "skill:session_dump_assimilation"}]


def test_attention_state_cli_reads_reduced_frame(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(embed, "REPO_ROOT", tmp_path)
    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_cli",
        command="kernel.py --option-surface standards --band card --ids std_skill --attention-frame attn_cli",
        payload={
            "kind": "standard_owned_option_surface",
            "artifact_kind": "standards",
            "band": "card",
            "selection": {"mode": "ids", "ids": ["std_skill"]},
            "lens_packet": {
                "view_profile": "option_surface_lens_packet_v0",
                "surface_id": "option_surface:standards",
                "source_payload_owner": {"source_refs": ["codex/standards/std_skill.json"]},
            },
            "rows": [{"id": "std_skill", "title": "Skill Standard"}],
        },
    )

    assert embed.cmd_attention_state("attn_cli", band="flag") == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["frame_id"] == "attn_cli"
    assert payload["focused_handles"][0]["handle"] == "standard:std_skill"
    assert payload["selected_handles"] == []
    assert payload["source_payload_owner"]["events_path"] == "state/navigation_trace/attention_events.jsonl"


def test_attention_state_latest_does_not_create_empty_frame(tmp_path) -> None:
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="latest", band="flag")

    assert frame["status"] == "no_attention_frame"
    assert frame["frame_id"] is None
    assert frame["summary"]["event_count"] == 0
    assert frame["resumability"]["event_append_hint"].endswith("--attention-frame new")
    assert not navigation_trace.latest_attention_frame_path(tmp_path).exists()


def test_attention_frame_bound_records_identity_without_selection(tmp_path) -> None:
    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_bound",
        event_type="attention_frame_bound",
        command="./repo-python kernel.py --entry 'bind frame' --attention-frame attn_bound",
        payload={
            "binding": {
                "task_frame_id": "task_frame_demo",
                "phase_id": "09_52",
                "work_item_id": "navigation_attention_frame_persistence",
                "actor_session_id": "session_demo",
                "entry_event_id": "entry_demo",
                "created_by_surface": "entry",
            },
            "entry_packet": {
                "selected_lane": {"lane_id": "navigation_enforcement"},
                "next_action": {"command": "./repo-python kernel.py --navigation-metabolism 'bind frame'"},
                "entry_surface_diagnostics": {"count": 0},
            },
        },
    )

    assert event is not None
    assert event["event_type"] == "attention_frame_bound"
    assert event["binding"]["task_frame_id"] == "task_frame_demo"
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_bound", band="flag")
    by_task = navigation_trace.build_attention_frame(tmp_path, frame_id="task_frame:task_frame_demo", band="flag")
    by_workitem = navigation_trace.build_attention_frame(
        tmp_path,
        frame_id="work_item:navigation_attention_frame_persistence",
        band="flag",
    )

    assert frame["binding"]["task_frame_id"] == "task_frame_demo"
    assert frame["binding"]["phase_id"] == "09_52"
    assert frame["seen_surfaces"] == ["entry"]
    assert frame["selected_kinds"] == ["task_frame"]
    assert frame["candidate_handles_seen"] == []
    assert frame["focused_handles"] == []
    assert frame["selected_handles"] == []
    assert by_task["frame_id"] == "attn_bound"
    assert by_workitem["frame_id"] == "attn_bound"
    assert frame["resumability"]["binding_resume_commands"]
    assert "rows" not in frame
    assert len(json.dumps(frame)) < 4000


def test_task_frame_alias_resolution_is_exact_and_append_safe(tmp_path) -> None:
    bind = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_exact",
        event_type="attention_frame_bound",
        payload={
            "binding": {
                "task_frame_id": "task_frame_exact",
                "phase_id": "09_52",
                "actor_session_id": "session_exact",
                "created_by_surface": "entry",
            },
            "entry_packet": {},
        },
    )
    assert bind is not None

    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="task_frame:task_frame_exact", band="flag")

    assert frame["frame_id"] == "attn_exact"
    assert frame["binding_resolution"]["status"] == "exact"
    assert frame["binding_resolution"]["candidate_count"] == 1
    assert frame["binding_resolution"]["append_safe"] is True
    assert frame["binding_resolution"]["resolved_by"] == "task_frame_id"


def test_phase_alias_resolution_reports_ambiguous_latest(tmp_path) -> None:
    first = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_phase_old",
        event_type="attention_frame_bound",
        payload={"binding": {"task_frame_id": "task_frame_old", "phase_id": "09_52"}, "entry_packet": {}},
    )
    second = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_phase_new",
        event_type="attention_frame_bound",
        payload={"binding": {"task_frame_id": "task_frame_new", "phase_id": "09_52"}, "entry_packet": {}},
    )
    assert first is not None
    assert second is not None

    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="phase:09_52", band="flag")

    assert frame["frame_id"] == "attn_phase_new"
    assert frame["binding_resolution"]["status"] == "ambiguous_latest"
    assert frame["binding_resolution"]["candidate_count"] == 2
    assert frame["binding_resolution"]["selected_policy"] == "latest_event_at"
    assert frame["binding_resolution"]["append_safe"] is False
    assert frame["selected_handles"] == []


def test_ambiguous_broad_alias_append_fails_visibly(tmp_path) -> None:
    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_phase_a",
        event_type="attention_frame_bound",
        payload={"binding": {"task_frame_id": "task_frame_a", "phase_id": "09_52"}, "entry_packet": {}},
    )
    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_phase_b",
        event_type="attention_frame_bound",
        payload={"binding": {"task_frame_id": "task_frame_b", "phase_id": "09_52"}, "entry_packet": {}},
    )

    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="phase:09_52",
        command="kernel.py --option-surface skills --attention-frame phase:09_52",
        attention_delta=_minimal_attention_delta("option_surface:skills"),
        return_error=True,
    )

    assert event is not None
    assert event["status"] == "failed"
    assert event["error_class"] == "AmbiguousAttentionFrameBinding"
    assert event["frame_id_requested"] == "phase:09_52"
    assert len(navigation_trace.read_attention_events(tmp_path)) == 2


def test_task_frame_alias_append_preserves_empty_selection(tmp_path) -> None:
    bind = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="new",
        event_type="attention_frame_bound",
        payload={"binding": {"task_frame_id": "task_frame_append", "phase_id": "09_52"}, "entry_packet": {}},
    )
    assert bind is not None
    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="task_frame:task_frame_append",
        attention_delta=_minimal_attention_delta("option_surface:skills"),
        return_error=True,
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="task_frame:task_frame_append", band="flag")

    assert event is not None
    assert event["status"] == "appended"
    assert event["frame_id"] == bind["frame_id"]
    assert frame["summary"]["event_count"] == 2
    assert frame["selected_handles"] == []


def test_work_item_alias_append_safe_only_when_unambiguous(tmp_path) -> None:
    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_work_item_one",
        event_type="attention_frame_bound",
        payload={
            "binding": {
                "task_frame_id": "task_frame_work_item_one",
                "work_item_id": "attention_frame_binding_resolution_safety",
            },
            "entry_packet": {},
        },
    )
    frame = navigation_trace.build_attention_frame(
        tmp_path,
        frame_id="work_item:attention_frame_binding_resolution_safety",
        band="flag",
    )
    assert frame["binding_resolution"]["status"] == "unambiguous"
    assert frame["binding_resolution"]["append_safe"] is True

    appended = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="work_item:attention_frame_binding_resolution_safety",
        attention_delta=_minimal_attention_delta("option_surface:task_ledger"),
        return_error=True,
    )
    assert appended is not None
    assert appended["status"] == "appended"

    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_work_item_two",
        event_type="attention_frame_bound",
        payload={
            "binding": {
                "task_frame_id": "task_frame_work_item_two",
                "work_item_id": "attention_frame_binding_resolution_safety",
            },
            "entry_packet": {},
        },
    )
    ambiguous = navigation_trace.build_attention_frame(
        tmp_path,
        frame_id="work_item:attention_frame_binding_resolution_safety",
        band="flag",
    )
    failed = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="work_item:attention_frame_binding_resolution_safety",
        attention_delta=_minimal_attention_delta("option_surface:task_ledger"),
        return_error=True,
    )

    assert ambiguous["binding_resolution"]["status"] == "ambiguous_latest"
    assert ambiguous["binding_resolution"]["candidate_count"] == 2
    assert ambiguous["binding_resolution"]["append_safe"] is False
    assert failed is not None
    assert failed["status"] == "failed"
    assert failed["error_class"] == "AmbiguousAttentionFrameBinding"


def test_attention_event_failure_is_visible_when_requested(monkeypatch, tmp_path) -> None:
    def explode(_payload, **_kwargs):
        raise RuntimeError("simulated reducer failure")

    monkeypatch.setattr(navigation_trace, "_attention_delta_from_payload", explode)

    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_fail",
        command="kernel.py --option-surface skills --attention-frame attn_fail",
        payload={"artifact_kind": "skills"},
        return_error=True,
    )

    assert event is not None
    assert event["status"] == "failed"
    assert event["frame_id_requested"] == "attn_fail"
    assert event["error_class"] == "RuntimeError"
    assert "simulated reducer failure" in event["error"]
    assert not navigation_trace.attention_events_path(tmp_path).exists()


def test_attention_frame_replaces_giant_semantic_entry_replay(tmp_path) -> None:
    skill_payload = {
        "kind": "standard_owned_option_surface",
        "artifact_kind": "skills",
        "band": "card",
        "selection": {"mode": "ids", "ids": ["session_dump_assimilation"]},
        "lens_packet": {
            "view_profile": "option_surface_lens_packet_v0",
            "surface_id": "option_surface:skills",
            "source_payload_owner": {"source_refs": ["codex/doctrine/skills/skill_registry.json"]},
            "mutation_allowed_by_this_profile": False,
        },
        "rows": [
            {
                "id": "session_dump_assimilation",
                "title": "Session Dump Assimilation",
                "drilldown_command": "./repo-python kernel.py --option-surface skills --band card --ids session_dump_assimilation",
            }
        ],
    }
    standard_payload = {
        "kind": "standard_owned_option_surface",
        "artifact_kind": "standards",
        "band": "card",
        "selection": {"mode": "ids", "ids": ["std_skill"]},
        "lens_packet": {
            "view_profile": "option_surface_lens_packet_v0",
            "surface_id": "option_surface:standards",
            "source_payload_owner": {"source_refs": ["codex/standards/std_skill.json"]},
            "mutation_allowed_by_this_profile": False,
        },
        "rows": [
            {
                "id": "std_skill",
                "title": "Skill Standard",
                "drilldown_command": "./repo-python kernel.py --option-surface standards --band card --ids std_skill",
            }
        ],
    }

    first = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="new",
        command="./repo-python kernel.py --option-surface skills --band card --ids session_dump_assimilation --attention-frame new",
        payload=skill_payload,
    )
    assert first is not None
    frame_id = first["frame_id"]
    navigation_trace.record_attention_event(
        tmp_path,
        frame_id=frame_id,
        command="./repo-python kernel.py --option-surface standards --band card --ids std_skill --attention-frame latest",
        payload=standard_payload,
    )

    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="latest", band="flag")
    handles = {row["handle"] for row in frame["focused_handles"]}

    assert frame["status"] == "ok"
    assert frame["frame_id"] == frame_id
    assert frame["summary"]["event_count"] == 2
    assert {"skill:session_dump_assimilation", "standard:std_skill"} <= handles
    assert frame["selected_handles"] == []
    assert frame["mutation_boundary"]["mutation_allowed_by_this_profile"] is False
    assert frame["resumability"]["resume_command"] == f"./repo-python kernel.py --attention-state {frame_id} --band flag"
    assert "rows" not in frame
    assert len(json.dumps(frame)) < 4000


def _mission_transaction_attention_payload(**overrides):
    payload = {
        "schema": "mission_transaction_landing_preflight_v0",
        "inputs": {"target_ids": ["navigation_attention_frame_persistence"]},
        "git": {"staged_path_count": 0, "staged_paths": []},
        "landing_decision": {
            "status": "watch",
            "reason": "working_tree_dirty_but_index_empty",
            "recommended_lane": "scoped_commit_private_index",
        },
        "shared_index_quarantine": {
            "schema": "shared_index_quarantine_v0",
            "status": "clear",
            "next_action": "none",
            "staged_path_count": 0,
            "normal_git_commit_allowed": True,
            "private_index_scoped_commit_allowed": False,
        },
        "work_ledger": {"status": "clear"},
        "transaction_candidate": {
            "claim_requirements": {
                "claim_required": False,
                "status": "not_required",
            },
            "finalizers": {
                "work_ledger_append_or_exempt": {"status": "not_required"},
                "task_ledger_execution_receipt": {"status": "pending", "command": "record receipt"},
                "staged_index_empty": {"status": "satisfied", "staged_path_count": 0},
                "generated_outputs_fresh": {"status": "satisfied"},
            },
        },
        "transaction_convergence": {
            "schema": "transaction_convergence_v0",
            "status": "watch",
            "next_action": "record_task_ledger_execution_receipt",
            "authority": {
                "task_ledger_authority": "state/task_ledger/events.jsonl",
                "work_ledger_authority": "codex/ledger/09_52/work_ledger.jsonl",
                "runtime_authority": "state/work_ledger/runtime_status.json",
            },
            "summary": {"stale_work_ledger_sessions": 0},
            "recent_transactions": [],
        },
        "transaction_convergence_reconcile": {
            "schema": "transaction_convergence_reconcile_v0",
            "status": "clear",
            "next_action": "none",
        },
        "dirty_tree_classification": {"schema": "dirty_tree_classification_v0", "status": "watch"},
        "derived_state_bloat_governor": {
            "workspace_bloat_pressure": {"schema": "workspace_bloat_pressure_v0", "status": "watch"},
            "github_push_bloat_gate": {"schema": "github_push_bloat_gate_v1", "status": "watch"},
        },
        "generated_projection_registry": {"kind": "generated_projection_registry"},
    }
    payload.update(overrides)
    return payload


def test_mutation_boundary_event_updates_boundary_not_selection(tmp_path) -> None:
    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_boundary",
        event_type="mutation_boundary_observed",
        command="./repo-python tools/meta/control/mission_transaction_preflight.py --attention-frame attn_boundary",
        payload=_mission_transaction_attention_payload(),
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_boundary", band="flag")

    assert event is not None
    assert event["event_type"] == "mutation_boundary_observed"
    assert event["attention_delta"]["selected_handles_added"] == []
    assert frame["selected_handles"] == []
    assert frame["mutation_boundary"]["landing_decision"] == "watch"
    assert frame["mutation_boundary"]["recommended_lane"] == "scoped_commit_private_index"
    assert frame["mutation_boundary"]["execution_receipt_status"] == "pending"
    authority_handles = {row["handle"] for row in frame["trusted_authorities"]}
    assert {"authority:git_index", "authority:task_ledger", "authority:work_ledger"} <= authority_handles
    assert frame["next_legal_moves"]
    assert "rows" not in frame
    assert len(json.dumps(frame)) < 4000


def test_mutation_boundary_appends_to_bound_frame_without_selection(tmp_path) -> None:
    bind = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="new",
        event_type="attention_frame_bound",
        payload={
            "binding": {
                "task_frame_id": "task_frame_boundary",
                "phase_id": "09_52",
                "actor_session_id": "session_boundary",
                "created_by_surface": "entry",
            },
            "entry_packet": {
                "selected_lane": {"lane_id": "navigation_enforcement"},
                "next_action": {"command": "./repo-python tools/meta/control/mission_transaction_preflight.py"},
            },
        },
    )
    assert bind is not None
    frame_id = bind["frame_id"]
    event = navigation_trace.record_attention_event(
        tmp_path,
        frame_id="task_frame:task_frame_boundary",
        event_type="mutation_boundary_observed",
        payload=_mission_transaction_attention_payload(),
        return_error=True,
    )

    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="task_frame:task_frame_boundary", band="flag")

    assert event is not None
    assert event["status"] == "appended"
    assert event["frame_id"] == frame_id
    assert frame["frame_id"] == frame_id
    assert frame["summary"]["event_count"] == 2
    assert frame["binding_resolution"]["status"] == "exact"
    assert frame["binding_resolution"]["append_safe"] is True
    assert frame["binding"]["task_frame_id"] == "task_frame_boundary"
    assert frame["selected_handles"] == []
    assert frame["mutation_boundary"]["landing_decision"] == "watch"


def test_mutation_boundary_blocks_do_not_select_handles(tmp_path) -> None:
    payload = _mission_transaction_attention_payload(
        landing_decision={
            "status": "blocked",
            "reason": "work_ledger_claim_collision",
            "recommended_lane": "release_or_wait_for_conflicting_claim",
        },
        transaction_candidate={
            "claim_requirements": {
                "claim_required": True,
                "status": "required_missing_session",
            },
            "finalizers": {
                "work_ledger_append_or_exempt": {"status": "blocked_missing_session"},
                "task_ledger_execution_receipt": {"status": "pending", "command": "record receipt"},
                "staged_index_empty": {"status": "blocked", "staged_path_count": 1},
                "generated_outputs_fresh": {"status": "satisfied"},
            },
        },
    )

    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_blocked",
        event_type="mutation_boundary_observed",
        payload=payload,
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_blocked", band="card")

    blocked_handles = {row["handle"] for row in frame["blocked_handles"]}
    assert "mutation_boundary:landing_decision" in blocked_handles
    assert "mutation_boundary:claim_requirements" in blocked_handles
    assert "mutation_boundary:finalizer:work_ledger_append_or_exempt" in blocked_handles
    assert "mutation_boundary:finalizer:staged_index_empty" in blocked_handles
    assert frame["selected_handles"] == []


def test_mutation_boundary_acted_on_requires_commit_and_recorded_receipt(tmp_path) -> None:
    transaction = {
        "transaction_id": "mtx_demo",
        "commit_refs": ["50a128aa709a9f5e243399b3c2278d5982c6cf15"],
        "task_ledger_execution_receipt": {"status": "recorded"},
    }
    missing_receipt_transaction = {
        "transaction_id": "mtx_no_receipt",
        "commit_refs": ["db839c7d8"],
        "task_ledger_execution_receipt": {"status": "missing"},
    }
    payload = _mission_transaction_attention_payload(
        transaction_convergence={
            "schema": "transaction_convergence_v0",
            "status": "clear",
            "next_action": "safe_to_continue_sibling_agents",
            "summary": {"stale_work_ledger_sessions": 0},
            "recent_transactions": [transaction, missing_receipt_transaction],
        },
    )

    navigation_trace.record_attention_event(
        tmp_path,
        frame_id="attn_acted",
        event_type="mutation_boundary_observed",
        payload=payload,
    )
    frame = navigation_trace.build_attention_frame(tmp_path, frame_id="attn_acted", band="card")

    acted_handles = {row["handle"] for row in frame["acted_on_handles"]}
    assert acted_handles == {"transaction:mtx_demo"}
    assert frame["selected_handles"] == []
