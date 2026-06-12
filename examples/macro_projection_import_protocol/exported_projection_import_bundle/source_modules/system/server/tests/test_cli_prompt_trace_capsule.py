import json
import os
import sqlite3
from pathlib import Path

from tools.meta.observability import cli_prompt_trace as trace
from tools.meta.observability.cli_prompt_trace import (
    ToolEvent,
    Turn,
    merge_full_thread,
    render_thread_closeout_report,
    render_trace_capsule_text,
)


def _event(index: int, cmd: str, exit_code: int, output_text: str = "") -> ToolEvent:
    return ToolEvent(
        index=index,
        name="exec_command",
        input={"cmd": cmd},
        tool_call_id=None,
        started_at=None,
        completed_at=None,
        duration_ms=None,
        is_error=exit_code != 0,
        output_text=output_text,
        output_char_count=len(output_text),
        output_sha256_16="",
        exit_code=exit_code,
    )


def _apply_patch_event(index: int, patch: str) -> ToolEvent:
    return ToolEvent(
        index=index,
        name="apply_patch",
        input={"_raw_input": patch},
        tool_call_id=None,
        started_at=None,
        completed_at=None,
        duration_ms=None,
        is_error=False,
        output_text="Success. Updated the following files:\nM tools/agent_trace_structurer/README.md\n",
        output_char_count=72,
        output_sha256_16="",
        exit_code=0,
    )


def _turn(
    events: list[ToolEvent],
    *,
    turn_index: int = 1,
    prompt_text: str = "test prompt",
    assistant_text: str = "done",
    session_file: str = "/tmp/session.jsonl",
) -> Turn:
    return Turn(
        provider="codex",
        session_id="session-for-test",
        session_file=session_file,
        turn_id=f"turn-for-test-{turn_index}",
        turn_index=turn_index,
        cwd=None,
        started_at=None,
        completed_at=f"2026-05-24T00:0{turn_index}:00+00:00",
        prompt_text=prompt_text,
        prompt_char_count=len(prompt_text),
        prompt_sha256_16=f"promptsha{turn_index}",
        tool_events=events,
        assistant_text=assistant_text,
        is_complete=True,
    )


def test_prompt_derived_old_title_does_not_mark_operator_retired(tmp_path) -> None:
    session_file = tmp_path / "claude-session.jsonl"
    session_file.write_text("{}\n", encoding="utf-8")

    fact = trace._row_title_authority_fact(
        provider="claude_code",
        session_id="claude-session",
        session_file=session_file,
        title="old prompt asks for parser repair",
        title_source="claude_first_prompt_preview",
        title_aliases={},
        codex_thread_records={},
        claude_desktop_titles={},
        prompt_preview="old prompt asks for parser repair",
    )

    assert fact["title_marker"] == "none"
    assert fact["source_title"] == ""
    assert fact["operator_alias"] == ""


def test_operator_alias_old_title_marks_operator_retired(tmp_path) -> None:
    session_file = tmp_path / "codex-session.jsonl"
    session_file.write_text("{}\n", encoding="utf-8")

    fact = trace._row_title_authority_fact(
        provider="codex",
        session_id="codex-session",
        session_file=session_file,
        title="old archived by operator",
        title_source="operator_alias",
        title_aliases={"codex:codex-session": "old archived by operator"},
        codex_thread_records={},
        claude_desktop_titles={},
        prompt_preview="recent prompt",
    )

    assert fact["title_marker"] == "old_prefix"
    assert fact["operator_alias"] == "old archived by operator"


def test_trace_capsule_includes_collapsed_codex_subagent_rollup(monkeypatch) -> None:
    monkeypatch.setattr(trace, "_codex_subagent_sidechain_summaries", lambda parent_session_id, limit=24: [])
    event = ToolEvent(
        index=1,
        name="spawn_agent",
        input={"agent_type": "explorer", "message": "Survey parser lifecycle edge cases."},
        tool_call_id="call_spawn",
        started_at="2026-05-24T00:00:00+00:00",
        completed_at="2026-05-24T00:00:03+00:00",
        duration_ms=3000,
        is_error=False,
        output_text='{"agent_id":"child-session-123","nickname":"Scout"}',
        output_char_count=52,
        output_sha256_16="",
        exit_code=None,
    )

    text, meta = trace.render_trace_capsule_text(
        _turn([event], prompt_text="Deploy a helper and summarize it."),
        title="Subagent Rollup",
        source_window="selected_turn",
    )

    assert "subagents: count=1 linked=0 visible=1 collapsed_under_parent=true" in text
    assert "SUBAGENTS" in text
    assert "S001 completed deployment_only" in text
    assert "tool=spawn_agent" in text
    assert meta["subagent_count"] == 1
    assert meta["subagent_deployments"][0]["agent_id"] == "child-session-123"


def test_trace_capsule_header_scopes_totality_and_diff_contract() -> None:
    turn = _turn(
        [
            _event(
                1,
                "./repo-python tools/meta/control/scoped_commit.py full-paths --path tools/example.py --message \"Add state model\"",
                0,
                '{"new_commit":"abc1234def5678"}',
            )
        ],
        assistant_text="Committed abc1234 Add state model",
    )
    text, meta = render_trace_capsule_text(
        turn,
        title="Trace State Contract",
        source_window="selected_turn",
    )

    assert "trace_scope: copy_scope=selected_turn thread_totality=selected_turn_only" in text
    assert "full_thread_available=false selected_window_only=true" in text
    assert "copy_policy: consumer=type_b_continue selected_scope=selected_turn" in text
    assert "stats_source: capsule_turn=#" in text
    assert "operator_interventions: selected_window_count=0" in text
    assert "diff_contract: substrate_diff=missing_exact_plus_minus" in text
    assert "copy_readiness: state=red blockers=commit_without_exact_diff" in text
    assert "diff_reconciler: status=commit_without_exact_diff severity=red" in text
    assert "evidence_tier: selected=tier_1_trace_capsule_projection" in text
    assert "type_b_handoff_lint: result=block no_edits_sentence_allowed=false" in text
    assert "terminal_validation_priority: state=not_captured" in text
    assert "episode_graph: schema=agent_episode_graph_v1 composition_root=agent_episode_graph" in text
    assert "type_b_rule: no_unqualified_no_edits_unless_full_thread_coverage_and_no_edit_claim_allowed" in text
    assert "thread_total_edits=has_edit_or_commit_evidence" in text
    assert "no_edit_claim_allowed=false" in text
    assert meta["thread_totality"] == "selected_turn_only"
    assert meta["diff_state"] == "missing_exact_plus_minus"
    assert meta["copy_readiness"]["state"] == "red"
    assert meta["diff_reconciler"]["status"] == "commit_without_exact_diff"
    assert meta["type_b_handoff_lint"]["result"] == "block"
    assert meta["type_b_handoff_lint"]["no_edits_sentence_allowed"] is False
    assert meta["agent_episode_graph"]["composition_root"] == "agent_episode_graph"
    assert meta["evidence_tier"]["provider_byte_lossless"] is False
    assert meta["operator_intervention_selected_window_count"] == 0
    assert meta["artifact_stats_source"]["source_window"] == "selected_turn"
    assert meta["commit_diff_missing"] is True


def test_trace_capsule_separates_final_delta_from_edit_event_log(monkeypatch) -> None:
    commit = "abc1234def5678"

    def fake_final_delta(**_kwargs):
        return {
            "schema_version": "agent_trace_final_delta_v1",
            "attached": True,
            "state": "git_show_commit_attached",
            "source": "git_show_commit",
            "authority": "final_substrate_delta",
            "commit": commit,
            "pathspecs": ["tools/agent_trace_structurer/README.md"],
            "paths": ["tools/agent_trace_structurer/README.md"],
            "line_count": 5,
            "omitted_lines": 0,
            "truncated_sha16": "",
            "command": "git show --stat --patch --no-ext-diff --unified=3",
            "lines": [
                f"commit {commit}",
                "diff --git a/tools/agent_trace_structurer/README.md b/tools/agent_trace_structurer/README.md",
                "@@ -1 +1 @@",
                "-old",
                "+new",
            ],
            "reason": "attached",
        }

    monkeypatch.setattr(trace, "_capsule_final_delta_for_trace", fake_final_delta)
    turn = _turn(
        [
            _apply_patch_event(
                1,
                "*** Begin Patch\n"
                "*** Update File: tools/agent_trace_structurer/README.md\n"
                "@@\n"
                "-old\n"
                "+new\n"
                "*** End Patch\n",
            ),
            _event(
                2,
                "./repo-python tools/meta/control/scoped_commit.py full-paths --path tools/agent_trace_structurer/README.md --message \"Update trace docs\"",
                0,
                json.dumps({"new_commit": commit}),
            ),
        ],
        assistant_text=f"Committed {commit} Update trace docs.",
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Final Delta Contract",
        source_window="selected_turn",
    )

    assert "FINAL_DELTA\n" in text
    assert "final_delta_summary: attached=true state=git_show_commit_attached source=git_show_commit" in text
    assert "diff_authority: final_substrate_delta patch_attempts_are_not_final_state=true final_substrate_delta_attached=true" in text
    assert "EDIT_EVENT_LOG\n" in text
    assert "edit_event_log_summary: files=1 rows=1" in text
    assert "patch_attempts_are_not_final_state=true" in text
    assert "DIFFS\n" not in text
    assert text.index("FINAL_DELTA") < text.index("EDIT_EVENT_LOG")
    assert "diff_contract: substrate_diff=exact_hunks_attached" in text
    assert "final_delta_attached=true edit_event_log_attached=true patch_attempts_are_not_final_state=true" in text
    assert "diff_reconciler: status=aligned_exact_substrate_diff severity=green" in text
    assert meta["diff_state"] == "exact_hunks_attached"
    assert meta["commit_diff_missing"] is False
    assert meta["final_delta_attached"] is True
    assert meta["edit_event_log"]["patch_attempts_are_not_final_state"] is True
    assert meta["diff_reconciler"]["final_delta"]["attached"] is True
    assert meta["diff_reconciler"]["edit_event_log"]["row_count"] == 1


def test_trace_capsule_changed_summary_scopes_no_edit_selected_turn() -> None:
    text, meta = render_trace_capsule_text(
        _turn([], assistant_text="Validation only; no edits captured in this source window."),
        title="Selected Turn Validation Receipt",
        source_window="selected_turn",
    )

    assert "trace_scope: copy_scope=selected_turn thread_totality=selected_turn_only" in text
    assert "changed: no edits captured in this source window" in text
    assert "changed: none captured" not in text
    assert meta["thread_totality"] == "selected_turn_only"
    assert meta["type_b_handoff_lint"]["no_edits_sentence_allowed"] is False


def test_trace_capsule_promotes_file_read_outputs_to_source_excerpts() -> None:
    turn = _turn(
        [
            _event(
                1,
                "sed -n '10,12p' tools/example.py",
                0,
                "def alpha():\n    return 1\n\n",
            )
        ],
        assistant_text="Prepared Type B handoff from source evidence.",
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Source Excerpt Contract",
        source_window="latest_prompt_cycle",
    )

    assert "source_excerpts: count=1 lines=2 paths=1 omitted=0 source=agent_requested_or_prompt_file_refs_or_trace_read_outputs" in text
    assert "carrier=saved_latest_response_bundle" in text
    assert "practical_budget=~150KB" in text
    assert "reference_modes=message_text|full_small_bodies|path_line_shards|standard_projections" in text
    assert "SOURCE_EXCERPTS" in text
    assert "source_excerpt_summary: count=1 lines=2 paths=1 omitted=0 agent_requested_refs=0 prompt_file_refs=0 source=agent_requested_or_prompt_file_refs_or_trace_read_outputs" in text
    assert "S001 C001 path=tools/example.py range=10-11 command=sed" in text
    assert "| L10 def alpha():" in text
    assert "| L11     return 1" in text
    assert meta["source_excerpt_count"] == 1
    assert meta["source_excerpt_line_count"] == 2
    assert meta["source_excerpt_paths"] == ["tools/example.py"]


def test_trace_capsule_promotes_agent_requested_source_excerpts_from_same_file(tmp_path) -> None:
    source = tmp_path / "module.py"
    source.write_text(
        "def before():\n"
        "    return 0\n"
        "\n"
        "class Box:\n"
        "    def target(self):\n"
        "        return 2\n"
        "\n"
        "def after():\n"
        "    return 3\n",
        encoding="utf-8",
    )
    first_excerpt, first_meta = trace.render_type_b_source_excerpt(
        cwd=tmp_path,
        source_path=str(source),
        line_range="1-2",
    )
    second_excerpt, second_meta = trace.render_type_b_source_excerpt(
        cwd=tmp_path,
        source_path=str(source),
        symbol="Box.target",
    )
    assert first_meta["selection"] == "line_range"
    assert second_meta["selection"] == "python_symbol"

    turn = _turn(
        [
            _event(
                1,
                f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {source} --line-range 1-2",
                0,
                first_excerpt + "\n",
            ),
            _event(
                2,
                f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {source} --symbol Box.target",
                0,
                second_excerpt + "\n",
            ),
        ],
        assistant_text="Prepared Type B handoff source excerpts.",
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Agent Requested Source Excerpts",
        source_window="latest_prompt_cycle",
    )

    assert "source_excerpt_summary: count=2" in text
    assert "agent_requested_refs=2" in text
    assert f"S001 C001 path={source} range=1-2 command=type_b_source_excerpt" in text
    assert f"S002 C002 path={source} range=5-6 command=type_b_source_excerpt" in text
    assert "| L1 def before():" in text
    assert "| L5     def target(self):" in text
    assert meta["source_excerpt_count"] == 2
    assert meta["source_excerpt_agent_requested_count"] == 2
    assert meta["source_excerpt_paths"] == [str(source)]


def test_trace_capsule_promotes_agent_requested_source_excerpts_from_trace_carrier_sidecar(tmp_path) -> None:
    source = tmp_path / "quiet.py"
    source.write_text(
        "def quiet_target():\n"
        "    return 'carried, not printed'\n",
        encoding="utf-8",
    )
    _excerpt, excerpt_meta = trace.render_type_b_source_excerpt(
        cwd=tmp_path,
        source_path=str(source),
        line_range="1-2",
    )
    payload = trace._type_b_source_excerpt_carrier_payload(excerpt_meta)
    sidecar = tmp_path / "carrier with spaces.json"
    sidecar.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = trace.render_type_b_source_excerpt_trace_carrier_receipt(excerpt_meta, sidecar)
    assert "quiet_target" not in receipt
    assert "carried, not printed" not in receipt

    turn = _turn(
        [
            _event(
                1,
                f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --trace-carrier --source-path {source} --line-range 1-2",
                0,
                receipt + "\n",
            )
        ],
        assistant_text="Prepared Type B handoff; use Copy Latest Trace.",
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Agent Requested Source Excerpt Carrier",
        source_window="latest_prompt_cycle",
    )

    assert "SOURCE_EXCERPTS" in text
    assert "source_excerpt_summary: count=1" in text
    assert "agent_requested_seen=1 agent_requested_emitted=1 agent_requested_omitted=0" in text
    assert "requested_excerpt_survival: status=all_emitted seen=1 emitted=1 omitted=0" in text
    assert f"S001 C001 path={source} range=1-2 command=type_b_source_excerpt" in text
    assert "| L1 def quiet_target():" in text
    assert "| L2     return 'carried, not printed'" in text
    assert "requested_excerpt_dropped:" not in text
    assert meta["source_excerpt_agent_requested_seen_count"] == 1
    assert meta["source_excerpt_agent_requested_emitted_count"] == 1
    assert meta["source_excerpt_agent_requested_omitted_count"] == 0
    assert meta["requested_excerpt_survival_status"] == "all_emitted"


def test_trace_capsule_prioritizes_agent_requested_source_excerpts_under_saturation(tmp_path) -> None:
    prompt_refs: list[str] = []
    for index in range(8):
        prompt_file = tmp_path / f"prompt_{index}.txt"
        prompt_file.write_text(f"prompt line {index}\n", encoding="utf-8")
        prompt_refs.append(f"## Pasted text.txt: {prompt_file}")

    events: list[ToolEvent] = []
    requested_sources: list[Path] = []
    for index in range(3):
        source = tmp_path / f"requested_{index}.py"
        source.write_text(
            f"def requested_{index}():\n"
            f"    return {index}\n",
            encoding="utf-8",
        )
        requested_sources.append(source)
        excerpt, _meta = trace.render_type_b_source_excerpt(
            cwd=tmp_path,
            source_path=str(source),
            line_range="1-2",
        )
        events.append(
            _event(
                index + 1,
                f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {source} --line-range 1-2",
                0,
                excerpt + "\n",
            )
        )

    text, meta = render_trace_capsule_text(
        _turn(
            events,
            prompt_text="\n".join(prompt_refs),
            assistant_text="I used the affordance and selected exact source for Type B.",
        ),
        title="Agent Requested Source Excerpt Saturation",
        source_window="latest_prompt_cycle",
    )

    assert "source_excerpt_summary: count=8" in text
    assert "agent_requested_seen=3 agent_requested_emitted=3 agent_requested_omitted=0" in text
    assert "requested_excerpt_survival: status=all_emitted seen=3 emitted=3 omitted=0" in text
    assert (
        f"requested_excerpt_paths: path_count=3 emitted=3 omitted=0 rows={requested_sources[0]}=>S001;"
        f"{requested_sources[1]}=>S002;{requested_sources[2]}=>S003"
    ) in text
    assert f"S001 C001 path={requested_sources[0]} range=1-2 command=type_b_source_excerpt" in text
    assert f"S002 C002 path={requested_sources[1]} range=1-2 command=type_b_source_excerpt" in text
    assert f"S003 C003 path={requested_sources[2]} range=1-2 command=type_b_source_excerpt" in text
    assert f"requested_excerpt_row: row_id=S001 command_id=C001 path={requested_sources[0]} range=1-2 selector=line_range" in text
    assert "S004 P001" in text
    assert meta["source_excerpt_agent_requested_seen_count"] == 3
    assert meta["source_excerpt_agent_requested_emitted_count"] == 3
    assert meta["source_excerpt_agent_requested_omitted_count"] == 0
    assert meta["source_excerpt_agent_requested_path_count"] == 3
    assert meta["source_excerpt_agent_requested_paths"][0]["row_ids"] == ["S001"]
    assert meta["source_excerpt_agent_requested_rows"][0]["path"] == str(requested_sources[0])
    assert meta["requested_excerpt_survival_status"] == "all_emitted"
    assert meta["type_b_handoff_lint"]["source_excerpt_survival"]["agent_requested_seen_count"] == 3
    assert meta["type_b_handoff_lint"]["source_excerpt_survival"]["agent_requested_emitted_count"] == 3
    assert meta["type_b_handoff_lint"]["source_excerpt_survival"]["agent_requested_path_count"] == 3


def test_trace_capsule_requested_excerpt_identity_ledger_names_docs_and_skill(tmp_path) -> None:
    readme = tmp_path / "tools" / "agent_trace_structurer" / "README.md"
    skill = tmp_path / "codex" / "doctrine" / "skills" / "doctrine" / "agent_trace_structurer.md"
    readme.parent.mkdir(parents=True)
    skill.parent.mkdir(parents=True)
    readme.write_text("README line 1\nREADME line 2\n", encoding="utf-8")
    skill.write_text("skill line 1\nskill line 2\n", encoding="utf-8")

    readme_excerpt, _readme_meta = trace.render_type_b_source_excerpt(
        cwd=tmp_path,
        source_path=str(readme),
        line_range="1-2",
    )
    skill_excerpt, _skill_meta = trace.render_type_b_source_excerpt(
        cwd=tmp_path,
        source_path=str(skill),
        line_range="1-2",
    )
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {readme} --line-range 1-2",
                    0,
                    readme_excerpt + "\n",
                ),
                _event(
                    2,
                    f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {skill} --line-range 1-2",
                    0,
                    skill_excerpt + "\n",
                ),
            ],
            assistant_text="I used the affordance and selected README and skill source for Type B.",
        ),
        title="Requested Excerpt Identity Ledger",
        source_window="latest_prompt_cycle",
    )

    assert f"requested_excerpt_paths: path_count=2 emitted=2 omitted=0 rows={readme}=>S001;{skill}=>S002" in text
    assert f"requested_excerpt_row: row_id=S001 command_id=C001 path={readme} range=1-2 selector=line_range" in text
    assert f"requested_excerpt_row: row_id=S002 command_id=C002 path={skill} range=1-2 selector=line_range" in text
    assert f"S001 C001 path={readme} range=1-2 command=type_b_source_excerpt" in text
    assert f"S002 C002 path={skill} range=1-2 command=type_b_source_excerpt" in text
    assert meta["source_excerpt_agent_requested_path_count"] == 2
    assert meta["source_excerpt_agent_requested_paths"] == [
        {
            "path": str(readme),
            "row_ids": ["S001"],
            "ranges": ["1-2"],
            "selectors": ["line_range"],
            "emitted_count": 1,
        },
        {
            "path": str(skill),
            "row_ids": ["S002"],
            "ranges": ["1-2"],
            "selectors": ["line_range"],
            "emitted_count": 1,
        },
    ]
    assert meta["source_excerpt_agent_requested_rows"][0]["row_id"] == "S001"
    assert meta["type_b_handoff_lint"]["source_excerpt_survival"]["emitted_paths"][1]["path"] == str(skill)


def test_trace_capsule_warns_when_closeout_claims_requested_source_but_none_emit(tmp_path) -> None:
    source = tmp_path / "missing_output.py"
    source.write_text("def target():\n    return 1\n", encoding="utf-8")
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {source} --line-range 1-2",
                    0,
                    "",
                )
            ],
            assistant_text="I used the affordance; the latest bundle should include SOURCE_EXCERPTS.",
        ),
        title="Missing Requested Source Excerpt",
        source_window="latest_prompt_cycle",
    )

    assert "requested_excerpt_survival: status=dropped_with_reasons seen=1 emitted=0 omitted=1" in text
    assert "requested_excerpt_dropped: command_id=C001" in text
    assert "reason=requested_excerpt_output_missing" in text
    assert "warnings=requested_excerpt_dropped,contradictory_closeout_requested_source_missing" in text
    assert "type_b_handoff_lint: result=warn" in text
    assert "contradictory_closeout_requested_source_missing" in meta["copy_readiness"]["warnings"]
    assert meta["source_excerpt_agent_requested_seen_count"] == 1
    assert meta["source_excerpt_agent_requested_emitted_count"] == 0
    assert meta["source_excerpt_agent_requested_omitted_count"] == 1
    assert meta["contradictory_closeout_requested_source_missing"] is True


def test_trace_capsule_surfaces_type_b_source_excerpt_affordance_with_source_context_warning() -> None:
    turn = _turn(
        [
            _apply_patch_event(
                1,
                "*** Begin Patch\n"
                "*** Update File: tools/agent_trace_structurer/README.md\n"
                "@@\n"
                "-old handoff text\n"
                "+new Type B source excerpt affordance text\n"
                "*** End Patch\n",
            )
        ],
        assistant_text="Updated Type B handoff affordance text.",
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Type B Source Excerpt Affordance",
        source_window="latest_prompt_cycle",
    )

    assert "type_b_source_excerpt_affordance: status=available suggested=true mandatory=false" in text
    assert "policy=optional_until_source_context_demand" in text
    assert "demand_state=required_by_claim" in text
    assert "copy_readiness_effect=amber_source_insufficient" in text
    assert "source_context_readiness: overall=amber demand=required_by_claim" in text
    assert "affordance=type_b_source_excerpt_available" in text
    assert "copy_readiness: state=amber blockers=none warnings=edit_event_log_without_final_delta" in text
    assert "type_b_handoff_lint: result=warn" in text
    assert "type_b_source_excerpt_available" not in meta["copy_readiness"]["warnings"]
    assert meta["type_b_source_excerpt_affordance"]["status"] == "available"
    assert meta["type_b_source_excerpt_affordance"]["suggested"] is True
    assert meta["type_b_source_excerpt_affordance"]["mandatory"] is False
    assert meta["type_b_source_excerpt_affordance"]["copy_readiness_effect"] == "amber_source_insufficient"
    assert meta["source_context_readiness"]["overall"] == "amber"
    assert meta["source_excerpt_agent_requested_count"] == 0


def test_trace_capsule_marks_type_b_source_excerpt_affordance_used(tmp_path) -> None:
    source = trace.REPO_ROOT / "tools" / "agent_trace_structurer" / "README.md"
    excerpt, _meta = trace.render_type_b_source_excerpt(
        cwd=trace.REPO_ROOT,
        source_path=str(source),
        line_range="1-2",
    )
    turn = _turn(
        [
            _apply_patch_event(
                1,
                "*** Begin Patch\n"
                "*** Update File: tools/agent_trace_structurer/README.md\n"
                "@@\n"
                "-old handoff text\n"
                "+new Type B source excerpt affordance text\n"
                "*** End Patch\n",
            ),
            _event(
                2,
                f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {source} --line-range 1-2",
                0,
                excerpt + "\n",
            ),
        ],
        assistant_text="Updated Type B handoff affordance text and selected exact source for Type B.",
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Type B Source Excerpt Affordance Used",
        source_window="latest_prompt_cycle",
    )

    assert "type_b_source_excerpt_affordance: status=used suggested=false mandatory=false" in text
    assert "copy_readiness_effect=none" in text
    assert "source_context_readiness: overall=green demand=required_by_type_b_decision" in text
    assert "command=type_b_source_excerpt" in text
    assert meta["type_b_source_excerpt_affordance"]["status"] == "used"
    assert meta["type_b_source_excerpt_affordance"]["suggested"] is False
    assert meta["source_excerpt_agent_requested_count"] == 1
    assert meta["source_context_readiness"]["overall"] == "green"


def test_trace_capsule_evidence_manifest_classifies_carrier_sufficiency(tmp_path) -> None:
    source = tmp_path / "owner.py"
    source.write_text("def selected_owner():\n    return 1\n", encoding="utf-8")
    excerpt, _meta = trace.render_type_b_source_excerpt(
        cwd=tmp_path,
        source_path=str(source),
        line_range="1-2",
    )
    turn = _turn(
        [
            _apply_patch_event(
                1,
                "*** Begin Patch\n"
                "*** Update File: tools/agent_trace_structurer/README.md\n"
                "@@\n"
                "-old handoff text\n"
                "+new evidence manifest text\n"
                "*** End Patch\n",
            ),
            _event(
                2,
                f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {source} --line-range 1-2",
                0,
                excerpt + "\n",
            ),
        ],
        assistant_text=(
            "Updated tools/agent_trace_structurer/README.md, selected exact source, "
            "and mentioned docs/passive_only.md."
        ),
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Evidence Manifest Carrier Sufficiency",
        source_window="latest_prompt_cycle",
    )

    assert "EVIDENCE_MANIFEST" in text
    assert "evidence_manifest_summary:" in text
    assert "requested_source_excerpt=1" in text
    assert "diff_hunk=0" in text
    assert "edit_event_hunk=1" in text
    assert "passive_mention=1" in text
    assert "path=tools/agent_trace_structurer/README.md carried_as=edit_event_hunk:E001" in text
    assert "sufficient_for=edit_attempt_chronology insufficient_for=final_substrate_state" in text
    assert f"path={source} " in text
    assert "requested_source_excerpt:S001" in text
    assert (
        "path=docs/passive_only.md carried_as=passive_mention "
        "sufficient_for=none insufficient_for=evidence_not_carried"
    ) in text
    assert "passive_mentions_without_evidence" in meta["copy_readiness"]["warnings"]
    manifest = meta["evidence_manifest"]
    assert manifest["class_counts"]["requested_source_excerpt"] == 1
    assert manifest["class_counts"]["diff_hunk"] == 0
    assert manifest["class_counts"]["edit_event_hunk"] == 1
    assert manifest["class_counts"]["passive_mention"] == 1
    readme_row = next(row for row in manifest["rows"] if row["path"] == "tools/agent_trace_structurer/README.md")
    assert readme_row["carried_as"] == ["edit_event_hunk:E001"]
    assert readme_row["sufficient_for"] == ["edit_attempt_chronology"]
    assert readme_row["insufficient_for"] == ["final_substrate_state"]


def test_trace_capsule_promotes_prompt_file_refs_to_source_excerpts(tmp_path) -> None:
    evidence = tmp_path / "paste.txt"
    evidence.write_text("alpha\nbeta\n", encoding="utf-8")
    turn = _turn(
        [],
        prompt_text=f"## Pasted text.txt: {evidence}\n\nRun the supplied evidence.",
        assistant_text="Prepared Type A handoff from supplied file evidence.",
    )

    text, meta = render_trace_capsule_text(
        turn,
        title="Prompt File Ref Contract",
        source_window="latest_prompt_cycle",
    )

    assert "source_excerpt_summary: count=1 lines=2 paths=1 omitted=0 agent_requested_refs=0 prompt_file_refs=1" in text
    assert "carrier=saved_latest_response_bundle" in text
    assert f"S001 P001 path={evidence} range=1-2 command=prompt_file_ref" in text
    assert "| L1 alpha" in text
    assert "| L2 beta" in text
    assert meta["source_excerpt_count"] == 1
    assert meta["source_excerpt_paths"] == [str(evidence)]


def test_trace_capsule_read_only_git_show_without_edits_warns_instead_of_blocking() -> None:
    turn = _turn(
        [_event(1, "git show --stat abc1234", 0, "commit abc1234\n1 file changed, 2 insertions(+)\n")],
        assistant_text="Inspected the existing commit and made no source edits.",
    )
    text, meta = render_trace_capsule_text(
        turn,
        title="Read-only commit observation",
        source_window="selected_turn",
    )

    assert "copy_readiness: state=amber blockers=none warnings=no_edits_captured_in_scoped_window" in text
    assert "diff_reconciler: status=no_edits_captured_in_scoped_window severity=amber" in text
    assert "thread_total_edits=unknown_not_full_thread" in text
    assert meta["commit_count"] == 0
    assert meta["commit_diff_missing"] is False
    assert meta["copy_readiness"]["state"] == "amber"
    assert meta["copy_readiness"]["blockers"] == []
    assert meta["diff_reconciler"]["status"] == "no_edits_captured_in_scoped_window"
    assert meta["type_b_handoff_lint"]["result"] == "warn"


def test_selected_trace_capsule_knows_full_thread_exists() -> None:
    turns = [
        _turn([_event(1, "date", 0, "ok")], turn_index=1, prompt_text="first long prompt " * 5),
        _turn([_event(1, "git diff -- file.py", 0, "+line")], turn_index=2, prompt_text="continue"),
    ]

    selected = trace.select_trace_window(
        turns,
        turn_arg=2,
        active=False,
        allow_partial=False,
        prompt_cycle=False,
        full_thread=False,
        threshold_words=trace.SHORT_PROMPT_CHAIN_WORD_THRESHOLD,
    )
    text, meta = render_trace_capsule_text(
        selected,
        title="Selected window with known full thread",
        source_window="selected_turn",
    )

    assert "full_thread_available=true selected_window_only=true" in text
    assert "recommended_scope=full_thread" in text
    assert "copy_readiness: state=amber" in text
    assert "copy_readiness_vector: overall=amber scope=amber" in text
    assert "latest_selection=green" in text
    assert "global_none_claims=green" in text
    assert "scope_semantics: status_label=selected_turn_complete" in text
    assert "latest_selection: selected_turn=2 selected_is_thread_tail=true selected_is_latest_completed_response=true" in text
    assert "LATEST_SELECTION_RECEIPT" in text
    assert "selected_is_latest_completed_response=true" in text
    assert "reader_latest: status=latest_completed_response" in text
    assert "reader_context: status=selected_window_only_context_deficit" in text
    assert "reader_next_action: use_bundle_for_latest_tail_claims; request_full_thread_only_for_global_absence_or_context" in text
    assert "open_product_residuals_selected_window: none" in text
    assert "open_product_residuals_global: not_claimed" in text
    assert "open_product_residuals: none" not in text
    assert "open_selected_window: none captured" in text
    assert "open_global: not_claimed" in text
    assert "open: none captured" not in text
    assert meta["full_thread_available"] is True
    assert meta["thread_totality"] == "selected_turn_only"
    assert meta["scope_semantics"]["unsafe_global_none_claims_blocked"] is True
    assert meta["copy_readiness"]["state"] == "amber"
    assert meta["latest_selection_receipt"]["selected_is_latest_completed_response"] is True
    assert meta["copy_readiness_vector"]["latest_selection"] == "green"
    assert meta["copy_readiness_vector"]["scope"] == "amber"
    assert meta["copy_readiness_vector"]["global_none_claims"] == "green"
    assert "selected_window_only_full_thread_available" in meta["copy_readiness"]["warnings"]


def test_trace_capsule_cut_receipt_detects_selected_window_behind_full_thread() -> None:
    selected = _turn([_event(1, "date", 0, "ok")], turn_index=1, prompt_text="first long prompt " * 5)
    selected.source_ref = {
        "full_thread_trace_window": {
            "mode": "full_thread",
            "start_turn_index": 1,
            "end_turn_index": 2,
            "turn_count": 2,
        },
    }
    text, meta = render_trace_capsule_text(
        selected,
        title="Selected window behind full thread",
        source_window="selected_turn",
    )

    assert "TRACE_CUT_RECEIPT" in text
    assert "consistency=stale_selected_window_not_latest_thread_turn" in text
    assert "selected_window=1-1 selected_count=1 full_thread=1-2 full_count=2 tail_state=not_thread_tail" in text
    assert "selected_is_latest_completed_response=false" in text
    assert "reader_next_action: request_latest_response_bundle_or_full_thread_tail" in text
    assert meta["trace_cut_receipt"]["cut_consistency"] == "stale_selected_window_not_latest_thread_turn"
    assert meta["trace_cut_receipt"]["provider_plane"]["tail_state"] == "not_thread_tail"
    assert meta["latest_selection_receipt"]["selected_is_latest_completed_response"] is False
    assert meta["copy_readiness_vector"]["latest_selection"] == "red"


def test_trace_capsule_emits_provenance_claim_map_and_self_parse_receipts() -> None:
    text, meta = render_trace_capsule_text(
        _turn([_event(1, "./repo-pytest system/server/tests/test_docs_route.py", 0, "1 passed")]),
        title="Trace Capsule Provenance Contract",
        source_window="selected_turn",
    )

    assert "READER_DECISION_CARD" in text
    assert "TRACE_PROVENANCE_ATTESTATION" in text
    assert "computed_after_render" not in text
    assert "subject_hash_mode=artifact_envelope_after_write" in text
    assert "LATEST_SELECTION_RECEIPT" in text
    assert "TITLE_AUTHORITY" in text
    assert "CLAIM_SOURCE_MAP" in text
    assert "EVIDENCE_NODE_GRAPH" in text
    assert "DEFEATER_REGISTER" in text
    assert "ASSURANCE_CASE_GRAPH" in text
    assert "TRACE_SELF_PARSE_RECEIPT" in text
    assert "BUDGET_SOLVER_PROOF_SET" in text
    assert "claim=status" in text
    assert "claim=status" in text and "evidence=EV.turn_completion_state,EV.trace_scope" in text
    assert "claim=final_validation" in text
    assert "claim=open_product_residuals_selected_window" in text
    assert "claim_source_map_complete=true" in text
    assert "downstream_parser_mjs_roundtrip=pending_artifact_write" in text
    assert meta["trace_provenance_attestation"]["schema_version"] == "agent_trace_provenance_attestation_v1"
    assert meta["trace_provenance_attestation"]["subject"]["sha16"] == "artifact_envelope_subject"
    assert meta["trace_provenance_attestation"]["subject"]["hash_mode"] == "artifact_envelope_after_write"
    assert meta["latest_selection_receipt"]["schema_version"] == "agent_trace_latest_selection_receipt_v1"
    assert meta["title_authority"]["schema_version"] == "agent_trace_title_authority_v1"
    assert meta["claim_source_map"]["schema_version"] == "agent_trace_claim_source_map_v1"
    assert set(meta["claim_source_map"]["covered_summary_claims"]) >= {
        "status",
        "changed",
        "final_validation",
        "open_product_residuals_selected_window",
        "open_selected_window",
    }
    status_row = next(row for row in meta["claim_source_map"]["rows"] if row["claim"] == "status")
    assert status_row["evidence"] == "EV.turn_completion_state,EV.trace_scope"
    assert meta["evidence_node_graph"]["schema_version"] == "agent_trace_evidence_node_graph_v1"
    assert meta["defeater_register"]["schema_version"] == "agent_trace_defeater_register_v1"
    assert meta["assurance_case_graph"]["schema_version"] == "agent_trace_assurance_case_graph_v1"
    assert any(row["id"] == "DTR.scope_deficit" for row in meta["defeater_register"]["rows"])
    assert meta["trace_self_parse_receipt"]["round_trip_status"] == "producer_pass_downstream_pending"
    assert meta["budget_solver_receipt"]["proof_set_before_route_context"] is True
    assert meta["budget_solver_receipt"]["proof_obligations_missing"] == 0


def test_trace_capsule_warns_and_falls_back_for_numeric_title() -> None:
    text, meta = render_trace_capsule_text(
        _turn([], prompt_text="Fix the demo tape recording latest bundle selector."),
        title="2",
        source_window="selected_turn",
    )

    assert "title: Fix the demo tape recording latest bundle selector." in text
    assert "raw_title: 2" in text
    assert "title_authority_warning: ordinal_title_not_semantic raw=2 source=title_numeric_token" in text
    assert "TITLE_AUTHORITY" in text
    assert 'raw_title="2"' in text
    assert "display_title_source=current_turn_prompt_title" in text
    assert meta["title_authority"]["raw_title"] == "2"
    assert meta["title_authority"]["display_title"] == "Fix the demo tape recording latest bundle selector."
    assert meta["title_authority"]["warning"].startswith("ordinal_title_not_semantic")
    assert any(row["id"] == "DTR.title_authority" and row["status"] == "active" for row in meta["defeater_register"]["rows"])


def test_trace_capsule_budget_solver_names_high_regret_omissions(tmp_path) -> None:
    source = tmp_path / "missing.py"
    source.write_text("def target():\n    return 1\n", encoding="utf-8")
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    f"./repo-python tools/meta/observability/cli_prompt_trace.py --type-b-source-excerpt --source-path {source} --line-range 1-2",
                    0,
                    "",
                )
            ],
            assistant_text="I used the affordance; the latest bundle should include SOURCE_EXCERPTS.",
        ),
        title="Budget Regret",
        source_window="latest_prompt_cycle",
    )

    assert "budget_regret_high=1" in text
    assert "top_omitted_decision_refs=C001:requested_excerpt_output_missing" in text
    assert meta["budget_solver_receipt"]["budget_regret_high"] == 1
    assert meta["budget_solver_receipt"]["top_omitted_decision_refs"] == ["C001:requested_excerpt_output_missing"]
    assert any(
        row["id"] == "DTR.budget_high_regret_omission" and row["status"] == "active"
        for row in meta["defeater_register"]["rows"]
    )


def test_trace_capsule_source_context_requires_type_b_exact_source_demand() -> None:
    patch = """*** Begin Patch
*** Update File: tools/meta/observability/cli_prompt_trace.py
@@
-old source context
+new source context
*** End Patch
"""
    text, meta = render_trace_capsule_text(
        _turn(
            [_apply_patch_event(1, patch)],
            prompt_text="Type B needs exact code and current source for the latest response bundle.",
            assistant_text="Implemented the source context ABI for the Trace Capsule.",
        ),
        title="Source Context ABI",
        source_window="selected_turn",
    )

    assert "SOURCE_CONTEXT_DEMAND" in text
    assert "SOURCE_SLICE_REQUESTS" in text
    assert "SOURCE_CONTEXT_DEFICIT" in text
    assert "SOURCE_CONTEXT_READINESS" in text
    assert "state=required_by_type_b_decision" in text
    assert "copy_readiness_effect=amber_source_insufficient" in text
    assert meta["source_context_demand"]["state"] == "required_by_type_b_decision"
    assert meta["source_context_readiness"]["overall"] == "amber"
    assert meta["source_context_readiness"]["high_regret_missing"] >= 1
    assert meta["type_b_source_excerpt_affordance"]["demand_state"] == "required_by_type_b_decision"
    assert meta["type_b_source_excerpt_affordance"]["copy_readiness_effect"] == "amber_source_insufficient"
    assert meta["source_slice_requests"]["rows"][0]["status"] == "deficit"
    assert meta["source_context_deficit"]["rows"][0]["fallback_used"] == "raw_sidecar_not_type_b_portable"
    assert meta["type_b_source_closeout_lint"]["result"] == "warn"


def test_trace_capsule_source_context_manifest_binds_explicit_slice_before_prompt_refs() -> None:
    parser_path = (trace.REPO_ROOT / "tools/agent_trace_structurer/parser.mjs").resolve()
    patch = """*** Begin Patch
*** Update File: tools/meta/observability/cli_prompt_trace.py
@@
-old source context
+new source context
*** End Patch
"""
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-python tools/meta/observability/cli_prompt_trace.py "
                    "--type-b-source-excerpt --source-path tools/meta/observability/cli_prompt_trace.py "
                    "--line-range 1-2",
                    0,
                    "1 import argparse\n2 import ast\n",
                ),
                _apply_patch_event(2, patch),
            ],
            prompt_text=(
                "Type B needs exact code and current source.\n"
                f"## Pasted text.txt: {parser_path}"
            ),
            assistant_text="Implemented the source context ABI and selected source excerpts.",
        ),
        title="Source Context Manifest",
        source_window="selected_turn",
    )

    assert "requested_excerpt_row: row_id=S001" in text
    assert "source_slice_manifest_row: slice_id=S001 request_id=SSR001" in text
    assert meta["source_excerpt_agent_requested_rows"][0]["row_id"] == "S001"
    assert meta["source_excerpt_prompt_file_ref_count"] >= 1
    assert meta["source_slice_requests"]["rows"][0]["status"] == "emitted"
    assert meta["source_slice_requests"]["rows"][0]["carrier"] == "S001"
    assert meta["source_slice_manifest"]["slices"][0]["slice_id"] == "S001"
    assert meta["source_slice_manifest"]["slices"][0]["request_id"] == "SSR001"
    assert meta["source_context_readiness"]["overall"] == "green"


def test_trace_capsule_source_context_not_required_for_status_only_closeout() -> None:
    text, meta = render_trace_capsule_text(
        _turn(
            [],
            prompt_text="Status only: what happened in the current trace?",
            assistant_text="No edits captured in this source window.",
        ),
        title="Status Only",
        source_window="selected_turn",
    )

    assert "SOURCE_CONTEXT_DEMAND" in text
    assert "source_context_demand_summary: state=none" in text
    assert "source_slice_requests_summary: rows=0" in text
    assert "source_context_readiness: overall=green demand=none" in text
    assert meta["source_context_demand"]["state"] == "none"
    assert meta["source_slice_requests"]["row_count"] == 0
    assert meta["source_context_deficit"]["active_count"] == 0
    assert meta["source_context_readiness"]["copy_readiness_effect"] == "none"


def test_trace_capsule_evidence_manifest_keeps_queries_out_of_path_field() -> None:
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "rg -n 'def target' tools/example.py",
                    0,
                    "tools/example.py:1:def target():\n",
                ),
                _event(
                    2,
                    "rg -n '^(TRACE_CUT_RECEIPT|TRACE_PROVENANCE_ATTESTATION)'",
                    0,
                    "tools/meta/observability/cli_prompt_trace.py:1:TRACE_CUT_RECEIPT\n",
                ),
            ],
            assistant_text="Reviewed rg query 'def target' in tools/example.py.",
        ),
        title="Evidence Node Paths",
        source_window="selected_turn",
    )

    assert "EVIDENCE_NODE_GRAPH" in text
    for row in meta["evidence_manifest"]["rows"]:
        assert "def target" not in row["path"]
        assert "TRACE_CUT_RECEIPT|TRACE_PROVENANCE_ATTESTATION" not in row["path"]
        assert not row["path"].startswith("/")
    assert any(row["path"] == "search_results" for row in meta["evidence_manifest"]["rows"])
    assert "query_regex_never_goes_in_path_field" in meta["evidence_node_graph"]["locator_rule"]


def test_trace_capsule_artifact_records_copied_source_watermark(monkeypatch, tmp_path) -> None:
    session_file = tmp_path / "session.jsonl"
    session_file.write_text("session source v1\n", encoding="utf-8")
    turn = _turn(
        [_event(1, "./repo-python -m pytest focused", 0, "1 passed\n")],
        session_file=str(session_file),
    )
    variant_dir = tmp_path / "Variant Artifacts"
    raw_dir = tmp_path / "Raw Sources"

    monkeypatch.setattr(trace, "TRACE_STRUCTURER_VARIANT_ARTIFACTS", variant_dir)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_RAW", raw_dir)
    monkeypatch.setattr(trace, "_write_variant_index_entry", lambda *args, **kwargs: None)
    monkeypatch.setattr(trace, "_resolve_session_title", lambda *args, **kwargs: ("Watermark Thread", "test"))

    receipt = trace.write_trace_capsule_artifact(turn, source_window="selected_turn")

    copied = receipt["copied_source_watermark"]
    assert copied["schema_version"] == "agent_trace_source_watermark_v1"
    assert copied["session_file"] == str(session_file)
    assert copied["watermark_id"]
    assert copied["tail_sha16"] == trace._file_tail_sha16(session_file)
    artifact = receipt["variant_artifact"]
    assert artifact["copied_source_watermark"]["watermark_id"] == copied["watermark_id"]
    assert artifact["window_anchor"]["source_watermark_id"] == copied["watermark_id"]
    assert artifact["trace_counts"]["trace_provenance_attestation"]["subject"]["sha16"] == artifact["sha16"]
    assert artifact["trace_counts"]["trace_provenance_attestation"]["subject"]["bytes"] == artifact["bytes"]
    assert artifact["trace_counts"]["latest_selection_receipt"]["selected_is_latest_completed_response"] is True
    assert artifact["trace_counts"]["downstream_parse_receipt"]["status"] == "pass"
    assert artifact["trace_counts"]["trace_self_parse_receipt"]["downstream_parser_mjs_roundtrip"] == "pass"
    assert artifact["trace_counts"]["trace_self_parse_receipt"]["round_trip_status"] == "pass"


def test_structurer_clip_history_records_copied_source_watermark(monkeypatch, tmp_path) -> None:
    session_file = tmp_path / "session.jsonl"
    session_file.write_text("session source v1\n", encoding="utf-8")
    turn = _turn(
        [_event(1, "./repo-python -m pytest focused", 0, "1 passed\n")],
        session_file=str(session_file),
    )
    raw_dir = tmp_path / "Raw Sources"
    captures_dir = tmp_path / "Captures"
    clips_dir = tmp_path / "Clips"
    exports_dir = tmp_path / "Exports"
    history_path = tmp_path / "clipboard_history.json"

    def parser_stub(raw_path: Path, capture_path: Path, thin_path: Path) -> dict:
        capture_path.write_text('{"schema":"full"}', encoding="utf-8")
        thin_path.write_text('{"schema":"thin"}', encoding="utf-8")
        return {
            "ok": True,
            "input_lines": len(raw_path.read_text(encoding="utf-8").splitlines()),
            "source_chunks": 1,
            "trace_blocks": 1,
            "artifacts": 0,
            "entities": 0,
            "sections": 1,
        }

    monkeypatch.setattr(trace, "TRACE_STRUCTURER_RAW", raw_dir)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_CAPTURES", captures_dir)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_CLIPS", clips_dir)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_EXPORTS", exports_dir)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_HISTORY", history_path)
    monkeypatch.setattr(trace, "_build_thin_clip_via_node", parser_stub)
    monkeypatch.setattr(trace, "_resolve_session_title", lambda *args, **kwargs: ("Watermark Thread", "test"))

    receipt = trace.write_structurer_clip(turn)

    copied = receipt["copied_source_watermark"]
    history = json.loads(history_path.read_text(encoding="utf-8"))
    history_cpt = history[0]["cli_prompt_trace"]
    assert copied["schema_version"] == "agent_trace_source_watermark_v1"
    assert history[0]["copied_source_watermark"]["watermark_id"] == copied["watermark_id"]
    assert history_cpt["copied_source_watermark"]["watermark_id"] == copied["watermark_id"]


def test_artifact_freshness_uses_source_watermark_mismatch() -> None:
    clip_watermark = trace._source_watermark_from_meta({
        "provider": "codex",
        "session_id": "session-for-test",
        "session_file": "/tmp/session.jsonl",
        "mtime_ns": 1000,
        "mtime_epoch": 1,
        "size_bytes": 10,
        "tail_sha16": "oldtail",
    })
    current_watermark = trace._source_watermark_from_meta({
        "provider": "codex",
        "session_id": "session-for-test",
        "session_file": "/tmp/session.jsonl",
        "mtime_ns": 2000,
        "mtime_epoch": 2,
        "size_bytes": 20,
        "tail_sha16": "newtail",
    })

    freshness = trace._classify_artifact_freshness(
        {"prompt_sha16": "promptsha", "turn_index": 3},
        {"prompt_sha16": "promptsha", "turn_index": 3, "source_watermark": clip_watermark},
        {"current_source_watermark": current_watermark},
    )

    assert freshness["state"] == "stale"
    assert freshness["reason"] == "source_watermark_mismatch"
    assert freshness["clip_source_watermark_id"] == clip_watermark["watermark_id"]
    assert freshness["current_source_watermark_id"] == current_watermark["watermark_id"]


def test_mission_index_goal_roster_refresh_overlays_cached_rows(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    conn.execute(
        """
        insert into thread_goals
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "codex-thread-1",
            "goal-1",
            "Keep refining the goal infrastructure from live trace evidence.",
            "active",
            None,
            42,
            9,
            1779980000000,
            1779981000000,
        ),
    )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779982000.0, 1779982000.0))

    session_index = tmp_path / "session_index.jsonl"
    session_index.write_text(
        '{"id":"codex-thread-1","thread_name":"<goal_context>","updated_at":"2026-05-28T16:00:00Z"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    monkeypatch.setattr(trace, "CODEX_SESSION_INDEX", session_index)

    cached_active = {
        "provider": "codex",
        "session_id": "codex-thread-1",
        "display_title": "<goal_context>",
        "title": "<goal_context>",
    }
    cached_rows = [dict(cached_active)]
    index = {
        "schema": "prompt_trace_mission_index_v3",
        "generated_at": "2026-05-28T15:33:46+00:00",
        "goal_authority": {
            "schema": "codex_thread_goal_authority_v1",
            "path": str(goals_db),
            "available": True,
            "row_count": 1,
            "status_counts": {"active": 1},
            "mtime_ms": 1779981000000,
        },
        "active_rows": [cached_active],
        "inactive_rows": [],
        "rows": cached_rows,
    }

    refreshed = trace._refresh_mission_index_goal_roster(index)

    assert refreshed["goal_thread_count"] == 1
    assert refreshed["active_goal_thread_count"] == 1
    assert refreshed["goal_fleet_state"]["thread_count"] == 1
    assert refreshed["goal_fleet_state"]["status_counts"] == {"active": 1}
    assert refreshed["goal_fleet_state"]["decision_counts"] == {"leave_alone": 1}
    assert refreshed["goal_fleet_state"]["controller_decision_receipt"]["active_threads_left_alone"] == [
        "codex-thread-1"
    ]
    assert refreshed["mission_goal_count"] == 1
    assert refreshed["active_mission_goal_count"] == 1
    assert refreshed["goal_authority"]["row_count"] == 1
    assert refreshed["goal_roster_refresh"]["mode"] == "cached_mission_index_overlay"
    assert refreshed["goal_roster_refresh"]["preserved_generated_at"] == "2026-05-28T15:33:46+00:00"
    assert refreshed["goal_roster_refresh"]["goal_authority_stale_before_refresh"] is True
    assert refreshed["goal_roster_refresh"]["previous_goal_authority_mtime_ms"] == 1779981000000
    assert refreshed["goal_roster_refresh"]["current_goal_authority_mtime_ms"] == 1779982000000
    assert refreshed["goal_roster_refresh"]["goal_authority_lag_ms"] == 1000000
    assert refreshed["active_rows"][0]["has_goal"] is True
    assert refreshed["active_rows"][0]["goal_status"] == "active"
    assert refreshed["active_rows"][0]["goal_sort_priority"] == 40
    assert refreshed["rows"][0]["has_goal"] is True
    roster_row = refreshed["goal_threads"][0]
    assert roster_row["thread_id"] == "codex-thread-1"
    assert roster_row["goal_fleet_control"]["observed_status"] == "active"
    assert roster_row["goal_fleet_control"]["next_allowed_action"] == "leave_alone"
    assert roster_row["goal_fleet_control"]["restart_policy"] == "do_not_reprompt_active_thread"
    assert roster_row["mission_index"]["state"] == "active_row"
    assert roster_row["mission_index"]["title"].startswith("Keep refining the goal infrastructure")


def test_mission_index_sort_keeps_recent_finished_rows_visible() -> None:
    rows = [
        {
            "session_id": "older-goal",
            "goal_sort_priority": 40,
            "latest_completed_turn": {"completed_at": "2026-05-31T18:00:00+00:00"},
            "last_activity_at": "2026-05-31T18:00:00+00:00",
            "mtime_utc": "2026-05-31T19:30:00+00:00",
        },
        {
            "session_id": "recent-finished",
            "goal_sort_priority": 0,
            "latest_completed_turn": {"completed_at": "2026-05-31T19:00:00+00:00"},
            "last_activity_at": "2026-05-31T19:00:00+00:00",
        },
        {
            "session_id": "active-now",
            "goal_sort_priority": 0,
            "active_turn": {"status": "in_flight", "started_at": "2026-05-31T17:00:00+00:00"},
            "last_activity_at": "2026-05-31T17:00:00+00:00",
        },
    ]

    assert [row["session_id"] for row in trace._sort_mission_index_rows(rows)] == [
        "active-now",
        "recent-finished",
        "older-goal",
    ]


def test_mission_index_sort_treats_active_goals_as_live() -> None:
    rows = [
        {
            "session_id": "recent-finished",
            "latest_completed_turn": {"completed_at": "2026-05-31T19:00:00+00:00"},
            "last_activity_at": "2026-05-31T19:00:00+00:00",
        },
        {
            "session_id": "older-active-goal",
            "goal_status": "active",
            "goal": {"status": "active"},
            "last_activity_at": "2026-05-31T15:00:00+00:00",
        },
    ]

    assert [row["session_id"] for row in trace._sort_mission_index_rows(rows)] == [
        "older-active-goal",
        "recent-finished",
    ]


def test_mission_index_soft_stale_cache_uses_source_mtime_as_activity(monkeypatch, tmp_path) -> None:
    thread_id = "stale-cache-thread"
    session_file = tmp_path / "rollout-stale-cache-thread.jsonl"
    session_file.write_text('{"type":"session_meta"}\n{"type":"newer_event"}\n', encoding="utf-8")
    current_epoch = 1770170400.0
    os.utime(session_file, (current_epoch, current_epoch))
    stat = session_file.stat()
    current_mtime_utc = trace._iso_from_epoch(stat.st_mtime)
    old_completed_at = "2026-02-04T01:00:00+00:00"
    current_meta = trace._session_file_meta("codex", thread_id, session_file)
    old_meta = dict(current_meta)
    old_meta["mtime_ns"] = 1
    old_meta["mtime_epoch"] = 1.0
    old_meta["size_bytes"] = 1
    stale_summary = {
        "turn_count": 1,
        "completed_turn_count": 1,
        "latest_turn_index": 1,
        "source_last_event_at": old_completed_at,
        "latest_completed_turn": {
            "turn_index": 1,
            "turn_id": "turn-1",
            "completed_at": old_completed_at,
            "started_at": "2026-02-04T00:59:00+00:00",
            "last_event_at": old_completed_at,
            "tool_count": 1,
            "prompt_sha16": "oldprompt",
            "prompt_title": "Old completed response",
            "prompt_preview": "Old completed response",
            "is_complete": True,
        },
        "preferred_trace_turn": {
            "turn_index": 1,
            "turn_id": "turn-1",
            "completed_at": old_completed_at,
            "last_event_at": old_completed_at,
            "prompt_sha16": "oldprompt",
            "prompt_title": "Old completed response",
            "prompt_preview": "Old completed response",
            "is_complete": True,
        },
    }
    cache = {
        "schema": trace.MISSION_SUMMARY_CACHE_SCHEMA,
        "entries": {
            trace._mission_summary_cache_key("codex", thread_id, session_file): {
                "source": old_meta,
                "summary": stale_summary,
            }
        },
    }

    def candidate():
        return {
            "provider": "codex",
            "session_id": thread_id,
            "session_file": str(session_file),
            "mtime_epoch": stat.st_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "mtime_utc": current_mtime_utc,
            "size_bytes": stat.st_size,
        }

    monkeypatch.setattr(trace, "_enumerate_candidates", lambda _provider, _cwd: [candidate()])
    monkeypatch.setattr(trace, "_load_codex_thread_title_records", lambda: {
        thread_id: {"thread_name": "Stale cache thread", "updated_at": "2026-02-04T00:58:00Z"}
    })
    monkeypatch.setattr(trace, "_load_title_aliases", lambda: {})
    monkeypatch.setattr(trace, "_load_claude_desktop_titles", lambda: {})
    monkeypatch.setattr(trace, "_load_codex_thread_goals", lambda: {})
    monkeypatch.setattr(trace, "_latest_clipboard_entry_for", lambda _session_id: None)
    monkeypatch.setattr(trace, "_load_mission_summary_cache", lambda: cache)
    monkeypatch.setattr(trace, "_write_mission_summary_cache", lambda _cache: None)
    monkeypatch.setattr(trace, "MISSION_INDEX_STALE_REPARSE_BUDGET", 0)
    monkeypatch.setattr(
        trace,
        "_latest_completed_turn_summary",
        lambda _provider, _path: (_ for _ in ()).throw(
            AssertionError("should not reparse when stale fallback is selected")
        ),
    )

    index = trace.build_mission_index(cwd=tmp_path, limit=10)

    row = index["rows"][0]
    assert row["trace_summary_cache_state"] == "soft_stale"
    assert row["latest_completed_turn"]["completed_at"] == old_completed_at
    assert row["last_activity_at"] == current_mtime_utc
    assert row["source_freshness"]["state"] == "source_newer_than_index"
    assert row["source_freshness"]["current_mtime_utc"] == current_mtime_utc
    assert row["source_freshness"]["source_last_event_at"] == current_mtime_utc
    assert row["source_freshness"]["requires_refresh_before_copy"] is True


def test_mission_index_forces_active_goal_threads_into_candidates(monkeypatch, tmp_path) -> None:
    thread_id = "019e6cf1-dc6e-74d2-ac8b-845d1771a238"
    sessions_root = tmp_path / "sessions"
    session_file = sessions_root / "2026/05/28" / f"rollout-2026-05-28T05-57-30-{thread_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text(
        json.dumps({
            "type": "session_meta",
            "payload": {
                "id": thread_id,
                "cwd": "/Users/example/src/ai_workflow",
                "timestamp": "2026-05-28T05:57:30Z",
            },
        })
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(trace, "CODEX_SESSIONS_ROOT", sessions_root)

    merged = trace._ensure_active_goal_candidates(
        [],
        {
            thread_id: {"status": "active"},
            "complete-thread": {"status": "complete"},
        },
    )

    assert [row["session_id"] for row in merged] == [thread_id]
    assert merged[0]["mission_index_forced_goal_thread"] is True
    assert merged[0]["session_file"] == str(session_file)


def test_mission_index_backfills_codex_title_visible_threads(monkeypatch, tmp_path) -> None:
    thread_id = "019e935d-dcc3-7a52-a85f-7b96c0b742d5"
    sessions_root = tmp_path / "sessions"
    session_file = sessions_root / "2026/06/04" / f"rollout-2026-06-04T17-01-02-{thread_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text(
        json.dumps({
            "type": "session_meta",
            "payload": {
                "id": thread_id,
                "cwd": str(tmp_path),
                "timestamp": "2026-06-04T17:01:02Z",
            },
        })
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(trace, "CODEX_SESSIONS_ROOT", sessions_root)
    monkeypatch.setattr(trace, "_enumerate_candidates", lambda _provider, _cwd: [])
    monkeypatch.setattr(trace, "_load_codex_thread_title_records", lambda: {
        thread_id: {"thread_name": "15", "updated_at": "2026-06-05T01:20:00Z"}
    })
    monkeypatch.setattr(trace, "_load_title_aliases", lambda: {})
    monkeypatch.setattr(trace, "_load_claude_desktop_titles", lambda: {})
    monkeypatch.setattr(trace, "_load_codex_thread_goals", lambda: {})
    monkeypatch.setattr(trace, "_latest_clipboard_entry_for", lambda _session_id: None)
    monkeypatch.setattr(trace, "_load_mission_summary_cache", lambda: {"schema": trace.MISSION_SUMMARY_CACHE_SCHEMA, "entries": {}})
    monkeypatch.setattr(trace, "_write_mission_summary_cache", lambda _cache: None)
    monkeypatch.setattr(trace, "_latest_completed_turn_summary", lambda _provider, _path: {
        "turn_count": 1,
        "completed_turn_count": 1,
        "latest_turn_index": 1,
        "latest_completed_turn": {
            "turn_index": 1,
            "turn_id": "turn-1",
            "completed_at": "2026-06-05T01:16:20+00:00",
            "started_at": "2026-06-05T01:15:00+00:00",
            "last_event_at": "2026-06-05T01:16:20+00:00",
            "tool_count": 0,
            "prompt_sha16": "promptsha",
            "prompt_title": "Fallback prompt title",
            "prompt_preview": "Fallback prompt title",
            "trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
            "full_thread_trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
            "full_thread_turn_count": 1,
            "trace_variant_size_estimates": {},
            "is_complete": True,
        },
        "preferred_trace_turn": {
            "turn_index": 1,
            "turn_id": "turn-1",
            "completed_at": "2026-06-05T01:16:20+00:00",
            "prompt_sha16": "promptsha",
            "prompt_title": "Fallback prompt title",
            "prompt_preview": "Fallback prompt title",
            "trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
            "full_thread_trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
            "full_thread_turn_count": 1,
            "trace_variant_size_estimates": {},
            "is_complete": True,
        },
    })

    index = trace.build_mission_index(cwd=tmp_path, limit=10)

    rows_by_id = {row["session_id"]: row for row in index["rows"]}
    assert set(rows_by_id) == {thread_id}
    row = rows_by_id[thread_id]
    assert row["title"] == "15"
    assert row["display_title"] == "15"
    assert row["source_title"] == "15"
    assert row["title_source"] == "codex_thread_name"
    assert row["mission_index_forced_codex_title_record"] is True
    assert row["session_file"] == str(session_file)
    assert index["active_rows"][0]["session_id"] == thread_id
    assert index["perf"]["summary_cache"]["forced_codex_title_records"] == 1


def test_mission_index_keeps_codex_child_threads_selectable(monkeypatch, tmp_path) -> None:
    parent_id = "parent-thread-123"
    child_id = "child-thread-456"
    parent_file = tmp_path / "rollout-parent.jsonl"
    child_file = tmp_path / "rollout-child.jsonl"
    parent_file.write_text("{}\n", encoding="utf-8")
    child_file.write_text("{}\n", encoding="utf-8")

    def candidate(path, session_id, **extra):
        stat = path.stat()
        return {
            "provider": "codex",
            "session_id": session_id,
            "session_file": str(path),
            "mtime_epoch": stat.st_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "mtime_utc": trace._iso_from_epoch(stat.st_mtime),
            "size_bytes": stat.st_size,
            **extra,
        }

    def summary_for(provider, path):
        title = "Child prompt title" if Path(path).name.endswith("child.jsonl") else "Parent prompt title"
        return {
            "turn_count": 1,
            "completed_turn_count": 1,
            "latest_turn_index": 1,
            "latest_completed_turn": {
                "turn_index": 1,
                "turn_id": "turn-1",
                "completed_at": "2026-06-02T03:20:00+00:00",
                "started_at": "2026-06-02T03:10:00+00:00",
                "last_event_at": "2026-06-02T03:20:00+00:00",
                "tool_count": 1,
                "prompt_sha16": "promptsha",
                "prompt_title": title,
                "prompt_preview": title,
                "trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
                "full_thread_trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
                "full_thread_turn_count": 1,
                "trace_variant_size_estimates": {},
                "is_complete": True,
            },
            "preferred_trace_turn": {
                "turn_index": 1,
                "turn_id": "turn-1",
                "completed_at": "2026-06-02T03:20:00+00:00",
                "prompt_sha16": "promptsha",
                "prompt_title": title,
                "prompt_preview": title,
                "trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
                "full_thread_trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
                "full_thread_turn_count": 1,
                "trace_variant_size_estimates": {},
                "is_complete": True,
            },
        }

    monkeypatch.setattr(trace, "_enumerate_candidates", lambda _provider, _cwd: [
        candidate(parent_file, parent_id),
        candidate(
            child_file,
            child_id,
            thread_source="subagent",
            parent_thread_id=parent_id,
            agent_role="explorer",
            agent_nickname="Scout",
        ),
    ])
    monkeypatch.setattr(trace, "_ensure_active_goal_candidates", lambda candidates, _goals: candidates)
    monkeypatch.setattr(trace, "_load_mission_summary_cache", lambda: {"schema": trace.MISSION_SUMMARY_CACHE_SCHEMA, "entries": {}})
    monkeypatch.setattr(trace, "_write_mission_summary_cache", lambda _cache: None)
    monkeypatch.setattr(trace, "_load_codex_thread_title_records", lambda: {
        parent_id: {"thread_name": "Parent Mission", "updated_at": "2026-06-02T03:00:00Z"},
        child_id: {"thread_name": "Child Mission", "updated_at": "2026-06-02T03:01:00Z"},
    })
    monkeypatch.setattr(trace, "_load_title_aliases", lambda: {})
    monkeypatch.setattr(trace, "_load_claude_desktop_titles", lambda: {})
    monkeypatch.setattr(trace, "_load_codex_thread_goals", lambda: {})
    monkeypatch.setattr(trace, "_latest_clipboard_entry_for", lambda _session_id: None)
    monkeypatch.setattr(trace, "_latest_completed_turn_summary", summary_for)

    index = trace.build_mission_index(cwd=tmp_path, limit=10)

    rows_by_id = {row["session_id"]: row for row in index["rows"]}
    assert set(rows_by_id) == {parent_id, child_id}
    child = rows_by_id[child_id]
    assert child["thread_source"] == "subagent"
    assert child["parent_session_id"] == parent_id
    assert child["thread_relationship"]["kind"] == "codex_child_thread"
    assert child["thread_relationship"]["parent_title"] == "Parent Mission"
    assert child["thread_relationship"]["selectable_child_trace"] is True
    assert index["perf"]["summary_cache"]["indexed_codex_subagent_children"] == 1
    assert index["perf"]["summary_cache"]["collapsed_codex_subagent_children"] == 0


def test_subagent_child_trace_carries_selectable_identity() -> None:
    sidechain = {
        "schema": "agent_trace_subagent_sidechain_v1",
        "provider": "codex",
        "session_id": "child-session",
        "parent_session_id": "parent-session",
        "agent_id": "child-session",
        "prompt_title": "Child route audit",
        "session_file": "/tmp/child.jsonl",
        "status": "completed",
    }

    dep = trace._sidechain_only_deployment(sidechain, 1)

    assert dep["linked_child_trace"] is True
    assert dep["child_trace"]["provider"] == "codex"
    assert dep["child_trace"]["session_id"] == "child-session"
    assert dep["child_trace"]["parent_session_id"] == "parent-session"


def test_mission_index_force_reparses_first_recent_oversize_stale_goal_summary(monkeypatch, tmp_path) -> None:
    session_file = tmp_path / "rollout-recent-goal.jsonl"
    session_file.write_text("{}\n", encoding="utf-8")
    now = 1_779_980_000.0
    os.utime(session_file, (now, now))
    stat = session_file.stat()
    current_size = trace.MISSION_INDEX_STALE_REPARSE_MAX_BYTES + 1024
    candidate = {
        "provider": "codex",
        "session_id": "goal-thread-long",
        "session_file": str(session_file),
        "mtime_epoch": now,
        "mtime_ns": stat.st_mtime_ns + 1000,
        "mtime_utc": trace._iso_from_epoch(now),
        "size_bytes": current_size,
    }
    stale_source = {
        "provider": "codex",
        "session_id": "goal-thread-long",
        "session_file": str(session_file),
        "mtime_ns": stat.st_mtime_ns,
        "mtime_epoch": now - 60,
        "size_bytes": current_size - 10,
    }
    stale_summary = {
        "turn_count": 1,
        "completed_turn_count": 1,
        "latest_turn_index": 1,
        "latest_completed_turn": {
            "turn_index": 1,
            "turn_id": "turn-1",
            "completed_at": "2026-05-31T17:00:00+00:00",
            "started_at": "2026-05-31T16:00:00+00:00",
            "last_event_at": "2026-05-31T17:00:00+00:00",
            "tool_count": 164,
            "prompt_sha16": "oldprompt",
            "prompt_preview": "old one-turn cache",
            "trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
            "full_thread_trace_window": {"start_turn_index": 1, "end_turn_index": 1, "turn_count": 1},
            "full_thread_turn_count": 1,
            "trace_variant_size_estimates": {
                "trace_capsule": {
                    "latest_prompt_cycle": {"bytes": 391_000, "exact": True},
                    "full_thread": {"bytes": 391_000, "exact": True},
                }
            },
            "is_complete": True,
        },
    }
    refreshed_summary = {
        "turn_count": 3,
        "completed_turn_count": 3,
        "latest_turn_index": 3,
        "latest_completed_turn": {
            "turn_index": 3,
            "turn_id": "turn-3",
            "completed_at": "2026-05-31T17:10:00+00:00",
            "started_at": "2026-05-31T17:05:00+00:00",
            "last_event_at": "2026-05-31T17:10:00+00:00",
            "tool_count": 42,
            "prompt_sha16": "newprompt",
            "prompt_preview": "newly completed response",
            "trace_window": {"start_turn_index": 3, "end_turn_index": 3, "turn_count": 1},
            "full_thread_trace_window": {"start_turn_index": 1, "end_turn_index": 3, "turn_count": 3},
            "full_thread_turn_count": 3,
            "is_complete": True,
        },
    }
    cache_key = trace._mission_summary_cache_key("codex", "goal-thread-long", session_file)
    cache = {"schema": trace.MISSION_SUMMARY_CACHE_SCHEMA, "entries": {
        cache_key: {"source": stale_source, "summary": stale_summary}
    }}
    parsed_paths = []

    monkeypatch.setattr(trace, "_enumerate_candidates", lambda _provider, _cwd: [candidate])
    monkeypatch.setattr(trace, "_load_mission_summary_cache", lambda: cache)
    monkeypatch.setattr(trace, "_write_mission_summary_cache", lambda _cache: None)
    monkeypatch.setattr(trace, "_load_codex_thread_title_records", lambda: {})
    monkeypatch.setattr(trace, "_load_title_aliases", lambda: {})
    monkeypatch.setattr(trace, "_load_claude_desktop_titles", lambda: {})
    monkeypatch.setattr(trace, "_load_codex_thread_goals", lambda: {
        "goal-thread-long": {"status": "active", "objective_preview": "Long Goal thread"}
    })
    monkeypatch.setattr(trace, "_latest_clipboard_entry_for", lambda _session_id: None)
    monkeypatch.setattr(trace, "_resolve_session_title", lambda *args, **kwargs: ("Thread 4 long goal repair", "codex_thread_name"))
    monkeypatch.setattr(trace, "_latest_completed_turn_summary", lambda _provider, path: parsed_paths.append(str(path)) or refreshed_summary)
    monkeypatch.setattr(trace, "_mission_source_recently_changed", lambda _meta, now_epoch=None: True)

    index = trace.build_mission_index(cwd=tmp_path, limit=5)

    row = index["rows"][0]
    assert row["session_id"] == "goal-thread-long"
    assert row["trace_summary_cache_state"] == "refreshed_recent_stale"
    assert row["latest_turn_index"] == 3
    assert row["turn_count_hint"] == 3
    assert row["source_freshness"]["state"] == "current"
    assert parsed_paths == [str(session_file)]
    assert index["perf"]["summary_cache"].get("recent_stale_oversize_forced", 0) == 1
    assert index["perf"]["summary_cache"].get("oversize_stale_deferred_budget", 0) == 0


def test_mission_index_defers_additional_recent_oversize_stale_summaries(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(trace, "MISSION_INDEX_RECENT_STALE_OVERSIZE_REPARSE_BUDGET", 1)
    now = 1_779_980_000.0
    current_size = trace.MISSION_INDEX_STALE_REPARSE_MAX_BYTES + 1024
    candidates = []
    cache_entries = {}
    for index, session_id in enumerate(("goal-thread-long-a", "goal-thread-long-b"), start=1):
        session_file = tmp_path / f"rollout-recent-goal-{index}.jsonl"
        session_file.write_text("{}\n", encoding="utf-8")
        os.utime(session_file, (now, now))
        stat = session_file.stat()
        candidate = {
            "provider": "codex",
            "session_id": session_id,
            "session_file": str(session_file),
            "mtime_epoch": now,
            "mtime_ns": stat.st_mtime_ns + 1000,
            "mtime_utc": trace._iso_from_epoch(now),
            "size_bytes": current_size,
        }
        stale_source = {
            "provider": "codex",
            "session_id": session_id,
            "session_file": str(session_file),
            "mtime_ns": stat.st_mtime_ns,
            "mtime_epoch": now - 60,
            "size_bytes": current_size - 10,
        }
        stale_summary = {
            "turn_count": 1,
            "completed_turn_count": 1,
            "latest_turn_index": 1,
            "latest_completed_turn": {
                "turn_index": 1,
                "turn_id": f"turn-{index}",
                "completed_at": "2026-05-31T17:00:00+00:00",
                "last_event_at": "2026-05-31T17:00:00+00:00",
                "tool_count": 100,
                "prompt_preview": f"stale goal {index}",
                "is_complete": True,
            },
        }
        candidates.append(candidate)
        cache_entries[
            trace._mission_summary_cache_key("codex", session_id, session_file)
        ] = {"source": stale_source, "summary": stale_summary}

    refreshed_summary = {
        "turn_count": 5,
        "completed_turn_count": 5,
        "latest_turn_index": 5,
        "latest_completed_turn": {
            "turn_index": 5,
            "turn_id": "turn-5",
            "completed_at": "2026-05-31T23:02:24+00:00",
            "last_event_at": "2026-05-31T23:02:24+00:00",
            "tool_count": 731,
            "prompt_preview": "new full goal turn",
            "is_complete": True,
        },
    }
    parsed_paths = []

    def parse_summary(_provider, path):
        parsed_paths.append(str(path))
        return refreshed_summary

    monkeypatch.setattr(trace, "_enumerate_candidates", lambda _provider, _cwd: candidates)
    monkeypatch.setattr(trace, "_load_mission_summary_cache", lambda: {"schema": trace.MISSION_SUMMARY_CACHE_SCHEMA, "entries": cache_entries})
    monkeypatch.setattr(trace, "_write_mission_summary_cache", lambda _cache: None)
    monkeypatch.setattr(trace, "_load_codex_thread_title_records", lambda: {})
    monkeypatch.setattr(trace, "_load_title_aliases", lambda: {})
    monkeypatch.setattr(trace, "_load_claude_desktop_titles", lambda: {})
    monkeypatch.setattr(trace, "_load_codex_thread_goals", lambda: {})
    monkeypatch.setattr(trace, "_latest_clipboard_entry_for", lambda _session_id: None)
    monkeypatch.setattr(trace, "_resolve_session_title", lambda provider, session_id, *args, **kwargs: (session_id, "codex_thread_name"))
    monkeypatch.setattr(trace, "_latest_completed_turn_summary", parse_summary)
    monkeypatch.setattr(trace, "_mission_source_recently_changed", lambda _meta, now_epoch=None: True)

    index = trace.build_mission_index(cwd=tmp_path, limit=5)
    rows_by_id = {row["session_id"]: row for row in index["rows"]}

    assert parsed_paths == [str(tmp_path / "rollout-recent-goal-1.jsonl")]
    assert rows_by_id["goal-thread-long-a"]["trace_summary_cache_state"] == "refreshed_recent_stale"
    assert rows_by_id["goal-thread-long-a"]["latest_turn_index"] == 5
    assert rows_by_id["goal-thread-long-b"]["trace_summary_cache_state"] == "soft_stale"
    assert rows_by_id["goal-thread-long-b"]["latest_turn_index"] == 1
    assert index["perf"]["summary_cache"].get("recent_stale_oversize_forced", 0) == 1
    assert index["perf"]["summary_cache"]["oversize_stale_deferred_budget"] == 1


def test_goal_fleet_state_classifies_controller_actions() -> None:
    goals = {
        "active-thread": {
            "goal_id": "goal-active",
            "status": "active",
            "objective_preview": "Keep building safely.",
            "objective_sha16": "active-sha",
            "tokens_used": 12,
            "updated_at_ms": 1779981000000,
        },
        "complete-thread": {
            "goal_id": "goal-complete",
            "status": "complete",
            "objective_preview": "Landed the first ratchet.",
            "objective_sha16": "complete-sha",
            "tokens_used": 44,
            "updated_at_ms": 1779982000000,
        },
        "blocked-thread": {
            "goal_id": "goal-blocked",
            "status": "blocked",
            "objective_preview": "Needs collision resolution.",
            "objective_sha16": "blocked-sha",
            "tokens_used": 8,
            "updated_at_ms": 1779983000000,
        },
    }
    rows = [
        {"provider": "codex", "session_id": "active-thread", "display_title": "Active lane"},
        {
            "provider": "codex",
            "session_id": "complete-thread",
            "display_title": "Finished lane",
            "inactive_reason": "archived",
        },
    ]

    roster = trace._goal_thread_roster(goals, rows, {})
    state = trace._goal_fleet_state(roster, {"content_sha16": "authority-sha"})

    assert state["schema"] == "goal_fleet_state_v1"
    assert state["goal_authority_content_sha16"] == "authority-sha"
    assert state["thread_count"] == 3
    assert state["status_counts"] == {
        "active": 1,
        "idle_complete": 1,
        "idle_blocked": 1,
    }
    assert state["decision_counts"] == {
        "leave_alone": 1,
        "fan_in_or_reprompt_with_terminal_evidence": 1,
        "capture_or_reroute_blocker": 1,
    }
    assert state["fan_in_needed_count"] == 2
    receipt = state["controller_decision_receipt"]
    assert receipt["mode"] == "state_projection_no_prompt_sent"
    assert receipt["active_threads_left_alone"] == ["active-thread"]
    assert receipt["idle_threads_needing_fan_in"] == ["complete-thread"]
    assert receipt["blocked_threads_needing_capture"] == ["blocked-thread"]
    rows_by_id = {row["thread_id"]: row for row in roster}
    assert rows_by_id["complete-thread"]["goal_fleet_control"]["restart_policy"] == (
        "reprompt_only_with_latest_terminal_evidence"
    )
    assert rows_by_id["blocked-thread"]["mission_index"]["state"] == "missing_from_recent_window"


def test_goal_fleet_action_receipt_records_no_prompt_actions() -> None:
    state = {
        "schema": "goal_fleet_state_v1",
        "thread_count": 2,
        "status_counts": {"active": 1, "operator_owned": 1},
        "decision_counts": {"leave_alone": 1, "ask_operator": 1},
        "fan_in_needed_count": 0,
        "threads": [
            {
                "thread_id": "active-thread",
                "goal_id": "goal-active",
                "goal_status": "active",
                "observed_status": "active",
                "next_allowed_action": "leave_alone",
                "restart_policy": "do_not_reprompt_active_thread",
                "current_goal_digest": "active-sha",
                "title_or_alias": "Active lane",
                "mission_index_state": "active_row",
                "updated_at_ms": 1779981000000,
            },
            {
                "thread_id": "paused-thread",
                "goal_id": "goal-paused",
                "goal_status": "paused",
                "observed_status": "operator_owned",
                "next_allowed_action": "ask_operator",
                "restart_policy": "operator_instruction_required",
                "current_goal_digest": "paused-sha",
                "title_or_alias": "Paused lane",
                "mission_index_state": "active_row",
                "updated_at_ms": 1779982000000,
            },
        ],
    }

    receipt = trace._goal_fleet_action_receipt_from_state(
        state,
        observed_goal_fleet_state_ref={
            "schema": "observed_goal_fleet_state_ref_v1",
            "goal_thread_count": 2,
        },
        collision_check_ref="wlr_collision_check",
        workitem_refs=["cap_goal_fleet_governance_repo_native_projection"],
    )

    assert receipt["schema"] == "goal_fleet_action_receipt_v1"
    assert receipt["action"] == "mixed:ask_operator,leave_alone"
    assert receipt["selected_threads"][0]["thread_id"] == "paused-thread"
    assert receipt["provider_thread_receipt"]["status"] == "not_required_no_prompt_sent"
    assert receipt["provider_thread_receipt"]["send_message_count"] == 0
    assert receipt["provider_thread_receipt"]["create_thread_count"] == 0
    assert receipt["controller_mode_hint"] == {
        "schema": "goal_fleet_controller_mode_hint_v1",
        "mode": "projection_no_send",
        "allowed_next_action": "stop_or_refresh_roster_before_new_provider_action",
        "reason": "All projected actions are side-effect-free controller decisions.",
        "action_count": 2,
        "side_effect_required": False,
    }
    assert receipt["admission_guard"]["status"] == "non_mutating_projection_only"
    assert receipt["admission_guard"]["collision_check_ref"] == "wlr_collision_check"
    assert receipt["fleet_admission_snapshot"] == {
        "schema": "fleet_admission_snapshot_v1",
        "status": "not_supplied",
        "host_pressure": {
            "schema": "host_resource_pressure_packet_v0",
            "status": "not_supplied",
            "source_command": "./repo-python -m system.lib.resource_pressure --compact",
        },
        "work_ledger_capacity": {
            "schema": "work_ledger_capacity_snapshot_v1",
            "status": "not_supplied",
            "source_command": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12 --json",
        },
        "authority_boundary": (
            "Direct unit construction did not read live host/claim state; live CLI receipts "
            "populate this from resource_pressure and Work Ledger."
        ),
    }
    assert receipt["uptake_confirmed"] == "not_applicable_no_prompt_sent"
    assert receipt["fan_in_due_at_or_stop_policy"] == "stop_after_non_mutating_controller_decision"
    assert receipt["workitem_refs_touched"] == [
        "cap_goal_fleet_governance_repo_native_projection"
    ]
    by_action = {group["action"]: group for group in receipt["action_groups"]}
    assert by_action["leave_alone"]["provider_thread_receipt"] == "not_required_no_prompt_sent"
    assert by_action["leave_alone"]["thread_impact_card_floor"]["status"] == (
        "not_required_for_non_mutating_controller_decision"
    )
    assert by_action["ask_operator"]["fan_in_due_at_or_stop_policy"] == (
        "stop_until_operator_instruction"
    )
    assert receipt["side_effecting_thread_action_taken"] is False


def test_goal_fleet_action_receipt_requires_impact_card_floor_before_mutation() -> None:
    state = {
        "schema": "goal_fleet_state_v1",
        "thread_count": 2,
        "status_counts": {"idle_complete": 1, "idle_blocked": 1},
        "decision_counts": {
            "fan_in_or_reprompt_with_terminal_evidence": 1,
            "capture_or_reroute_blocker": 1,
        },
        "fan_in_needed_count": 2,
        "threads": [
            {
                "thread_id": "complete-thread",
                "goal_id": "goal-complete",
                "goal_status": "complete",
                "observed_status": "idle_complete",
                "next_allowed_action": "fan_in_or_reprompt_with_terminal_evidence",
                "restart_policy": "reprompt_only_with_latest_terminal_evidence",
                "current_goal_digest": "complete-sha",
                "title_or_alias": "Complete lane",
                "mission_index_state": "inactive_row",
                "updated_at_ms": 1779981000000,
            },
            {
                "thread_id": "blocked-thread",
                "goal_id": "goal-blocked",
                "goal_status": "blocked",
                "observed_status": "idle_blocked",
                "next_allowed_action": "capture_or_reroute_blocker",
                "restart_policy": "do_not_blind_reprompt_capture_blocker_first",
                "current_goal_digest": "blocked-sha",
                "title_or_alias": "Blocked lane",
                "mission_index_state": "active_row",
                "updated_at_ms": 1779982000000,
            },
        ],
    }

    fleet_admission = {
        "schema": "fleet_admission_snapshot_v1",
        "status": "watch_capacity_pressure",
        "host_pressure": {
            "schema": "host_resource_pressure_packet_v0",
            "status": "attention",
            "admission": "pressure_aware",
            "normal_work_allowed": True,
        },
        "work_ledger_capacity": {
            "schema": "work_ledger_capacity_snapshot_v1",
            "status": "available",
            "effective_active_sessions": 6,
            "active_claims": 17,
            "claim_collisions": 0,
            "risk_level": "watch",
        },
    }

    receipt = trace._goal_fleet_action_receipt_from_state(
        state,
        fleet_admission_snapshot=fleet_admission,
    )

    assert receipt["controller_mode_hint"]["mode"] == "watch_or_fan_in_before_mutation"
    assert receipt["controller_mode_hint"]["side_effect_required"] is True
    assert receipt["fleet_admission_snapshot"] == fleet_admission
    assert receipt["admission_guard"]["status"] == "blocked_until_live_admission_packet"
    assert receipt["admission_guard"]["collision_check_ref"] == (
        "required_before_provider_thread_mutation"
    )
    assert "fresh Work Ledger session/claim collision check" in (
        receipt["admission_guard"]["requires_before_provider_thread_mutation"]
    )
    assert "ThreadImpactCard fields for each steered thread" in (
        receipt["admission_guard"]["requires_before_provider_thread_mutation"]
    )
    assert "stale counts" in receipt["admission_guard"]["non_overfit_boundary"]

    by_action = {group["action"]: group for group in receipt["action_groups"]}
    for action in ("fan_in_or_reprompt_with_terminal_evidence", "capture_or_reroute_blocker"):
        floor = by_action[action]["thread_impact_card_floor"]
        assert floor["schema"] == "goal_fleet_thread_impact_card_floor_v1"
        assert floor["status"] == "required_before_provider_thread_mutation"
        assert floor["required_fields"] == [
            "actual_target_or_gate",
            "claimed_paths_or_claim_ref",
            "proof_landed_or_validation_ref",
            "proof_missing_or_next_validation",
            "launch_shape",
            "fan_in_or_reentry_condition",
        ]


def test_goal_roster_refresh_receipt_sidecar_is_compact(monkeypatch, tmp_path) -> None:
    receipt_path = tmp_path / "goal_roster_receipt.json"
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_BASE", tmp_path)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", tmp_path / "mission_index.json")
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    receipt = trace._write_goal_roster_refresh_receipt({
        "generated_at": "2026-05-28T15:33:46+00:00",
        "goal_authority": {"row_count": 1, "mtime_ms": 1779982000000},
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
        "mission_goal_count": 1,
        "active_mission_goal_count": 1,
        "goal_fleet_state": {
            "schema": "goal_fleet_state_v1",
            "thread_count": 1,
            "status_counts": {"active": 1},
            "decision_counts": {"leave_alone": 1},
            "fan_in_needed_count": 0,
            "threads": [{"thread_id": "codex-thread-1"}],
        },
        "goal_roster_refresh": {
            "schema": "prompt_trace_mission_index_goal_roster_refresh_v1",
            "goal_authority_stale_before_refresh": True,
            "goal_authority_lag_ms": 1000000,
        },
        "rows": [{"large": "mission rows stay in mission_index.json"}],
    })

    written = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "prompt_trace_mission_index_goal_roster_refresh_receipt_v1"
    assert written["mission_index_path"].endswith("mission_index.json")
    assert written["refresh"]["goal_authority_stale_before_refresh"] is True
    assert written["refresh"]["goal_authority_lag_ms"] == 1000000
    assert written["goal_authority"]["mtime_ms"] == 1779982000000
    assert written["goal_fleet_state"]["decision_counts"] == {"leave_alone": 1}
    assert "threads" not in written["goal_fleet_state"]
    assert "rows" not in written


def test_goal_roster_status_reports_current_authority_lag(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    for idx in range(2):
        conn.execute(
            "insert into thread_goals values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"codex-thread-{idx}",
                f"goal-{idx}",
                f"Keep refining goal infrastructure {idx}.",
                "active",
                None,
                10 + idx,
                1,
                1779980000000,
                1779983000000 + idx,
            ),
        )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779983000.0, 1779983000.0))

    mission_index = tmp_path / "mission_index.json"
    receipt_path = tmp_path / "goal_roster_receipt.json"
    cached = {
        "goal_authority": {"mtime_ms": 1779982000000, "row_count": 1},
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
    }
    mission_index.write_text(json.dumps({"generated_at": "2026-05-28T15:33:46+00:00", **cached}))
    receipt_path.write_text(json.dumps({"recorded_at": "2026-05-28T16:00:00+00:00", **cached}))

    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", mission_index)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    status = trace._goal_roster_status(cwd=tmp_path)

    assert status["schema"] == "prompt_trace_mission_index_goal_roster_status_v1"
    assert status["staleness"]["status"] == "stale"
    assert status["staleness"]["kind"] == "roster_count_delta"
    assert status["staleness"]["refresh_recommended"] is True
    assert status["staleness"]["refresh_action"] == "refresh_now"
    assert status["staleness"]["refresh_priority"] == "high"
    assert status["staleness"]["count_delta_present"] is True
    assert status["staleness"]["metadata_lag_only"] is False
    assert status["staleness"]["counts_aligned"] is False
    assert status["staleness"]["full_mission_index_rewrite_required_for_count_accuracy"] is True
    assert status["staleness"]["refresh_recommendation"] == {
        "action": "refresh_now",
        "priority": "high",
        "reason": "goal roster counts, content, or projection anchors are stale",
        "counts_aligned": False,
        "metadata_lag_only": False,
        "content_delta_present": False,
        "full_mission_index_rewrite_required_for_count_accuracy": True,
    }
    assert "goal_authority_mtime_lag" in status["staleness"]["reasons"]
    assert "mission_index_goal_thread_count_delta" in status["staleness"]["reasons"]
    assert status["staleness"]["goal_authority_lag_ms"] == 1000000
    assert status["staleness"]["goal_thread_count_delta"] == 1
    assert status["current"]["goal_thread_count"] == 2
    assert status["mission_index"]["goal_thread_count"] == 1
    assert "rows" not in json.dumps(status)


def test_goal_roster_status_marks_mtime_only_lag(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    conn.execute(
        "insert into thread_goals values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "codex-thread-1",
            "goal-1",
            "Keep refining goal infrastructure.",
            "active",
            None,
            10,
            1,
            1779980000000,
            1779983000000,
        ),
    )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779983000.0, 1779983000.0))

    mission_index = tmp_path / "mission_index.json"
    receipt_path = tmp_path / "goal_roster_receipt.json"
    cached = {
        "goal_authority": {"mtime_ms": 1779982000000, "row_count": 1},
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
    }
    mission_index.write_text(json.dumps({"generated_at": "2026-05-28T15:33:46+00:00", **cached}))
    receipt_path.write_text(json.dumps({"recorded_at": "2026-05-28T16:00:00+00:00", **cached}))

    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", mission_index)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    status = trace._goal_roster_status(cwd=tmp_path)

    assert status["staleness"]["status"] == "stale"
    assert status["staleness"]["kind"] == "metadata_lag"
    assert status["staleness"]["refresh_recommended"] is True
    assert status["staleness"]["refresh_action"] == "refresh_when_metadata_freshness_matters"
    assert status["staleness"]["refresh_priority"] == "low"
    assert status["staleness"]["metadata_lag_only"] is True
    assert status["staleness"]["count_delta_present"] is False
    assert status["staleness"]["availability_issue_present"] is False
    assert status["staleness"]["counts_aligned"] is True
    assert status["staleness"]["full_mission_index_rewrite_required_for_count_accuracy"] is False
    assert status["staleness"]["refresh_recommendation"] == {
        "action": "refresh_when_metadata_freshness_matters",
        "priority": "low",
        "reason": "goal roster counts are aligned; only authority metadata mtime lags",
        "counts_aligned": True,
        "metadata_lag_only": True,
        "content_delta_present": False,
        "full_mission_index_rewrite_required_for_count_accuracy": False,
    }
    assert status["staleness"]["reasons"] == ["goal_authority_mtime_lag"]
    assert status["staleness"]["goal_thread_count_delta"] == 0
    assert status["staleness"]["goal_authority_lag_ms"] == 1000000


def test_goal_roster_status_ignores_mtime_lag_when_content_signature_matches(monkeypatch, tmp_path) -> None:
    goals_db = tmp_path / "goals.sqlite"
    conn = sqlite3.connect(goals_db)
    conn.execute(
        """
        create table thread_goals (
            thread_id text primary key,
            goal_id text not null,
            objective text not null,
            status text not null,
            token_budget integer,
            tokens_used integer not null,
            time_used_seconds integer not null,
            created_at_ms integer not null,
            updated_at_ms integer not null
        )
        """
    )
    conn.execute(
        "insert into thread_goals values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "codex-thread-1",
            "goal-1",
            "Keep refining goal infrastructure.",
            "active",
            None,
            10,
            1,
            1779980000000,
            1779983000000,
        ),
    )
    conn.commit()
    conn.close()
    os.utime(goals_db, (1779983000.0, 1779983000.0))

    mission_index = tmp_path / "mission_index.json"
    receipt_path = tmp_path / "goal_roster_receipt.json"
    monkeypatch.setattr(trace, "CODEX_GOALS_DB", goals_db)
    current_goals = trace._load_codex_thread_goals()
    cached_authority = trace._goal_authority_sources(current_goals)
    cached_authority["mtime_ms"] = 1779982000000
    cached = {
        "goal_authority": cached_authority,
        "goal_thread_count": 1,
        "active_goal_thread_count": 1,
    }
    mission_index.write_text(json.dumps({"generated_at": "2026-05-28T15:33:46+00:00", **cached}))
    receipt_path.write_text(json.dumps({"recorded_at": "2026-05-28T16:00:00+00:00", **cached}))

    monkeypatch.setattr(trace, "TRACE_STRUCTURER_MISSION_INDEX", mission_index)
    monkeypatch.setattr(trace, "TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT", receipt_path)

    status = trace._goal_roster_status(cwd=tmp_path)

    assert status["staleness"]["status"] == "fresh"
    assert status["staleness"]["kind"] == "fresh"
    assert status["staleness"]["refresh_recommended"] is False
    assert status["staleness"]["reasons"] == []
    assert status["staleness"]["mtime_lag_without_content_delta"] is True
    assert status["staleness"]["content_delta_present"] is False
    assert status["staleness"]["goal_authority_lag_ms"] == 1000000


def test_trace_capsule_final_validation_uses_terminal_validation_rows() -> None:
    repeated = "./repo-pytest system/server/tests/test_example.py"
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, repeated, 1),
                _event(2, repeated, 0),
                _event(3, "python -m py_compile tools/example.py", 0),
            ]
        ),
        title="terminal validation test",
    )

    assert "final_validation: passed" in text
    assert "checks: pass=2 fail=1 other=0 total=3" in text
    assert "terminal_checks: pass=2 fail=0 other=0 total=2" in text
    assert meta["terminal_validation_count"] == 2
    assert meta["terminal_validation_fail_count"] == 0


def test_trace_capsule_keeps_needs_review_when_terminal_row_fails() -> None:
    repeated = "./repo-pytest system/server/tests/test_example.py"
    text, meta = render_trace_capsule_text(
        _turn([_event(1, repeated, 0), _event(2, repeated, 1)]),
        title="terminal validation fail test",
    )

    assert "final_validation: needs_review" in text
    assert "checks: pass=1 fail=1 other=0 total=2" in text
    assert "terminal_checks: pass=0 fail=1 other=0 total=1" in text
    assert meta["terminal_validation_fail_count"] == 1


def test_trace_capsule_stale_window_failure_superseded_by_later_aggregate_proof() -> None:
    early_demo = (
        "PYTHONPATH=src python3 -m microcosm_core.cli crown-jewel-demo run "
        "--out /tmp/aiw_crown_jewel_demo_early"
    )
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    early_demo,
                    1,
                    '{"status":"blocked","organ_failures":["agent_closeout_faithfulness_audit"]}',
                ),
                _event(2, "make ci", 0, "123 passed in 287.66s"),
            ],
            assistant_text="make ci passed at 123 passed; delivery blockers none.",
        ),
        title="stale window terminal failure test",
    )

    assert "final_validation: passed" in text
    assert "terminal_validation_priority: state=terminal_recovered_failures_present" in text
    assert "terminal_failure_classes: current_terminal_failure=0 recovered_failure=0 stale_window_failure=1 not_validated=0 contradictory_closeout=0" in text
    assert "validation_semantics: owner_scope_validation=pass" in text
    assert "stale_window_failures=1" in text
    assert meta["final_validation"] == "passed"
    assert meta["terminal_validation_fail_count"] == 1
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["raw_blocking_terminal_failure_count"] == 1
    assert meta["stale_window_failure_count"] == 1
    assert meta["terminal_failure_classes"]["stale_window_failure"] == 1


def test_trace_capsule_expected_guarded_refusal_is_nonblocking_receipt() -> None:
    guard_command = (
        "PYTHONPATH=microcosm-substrate/src ./repo-python -m "
        "microcosm_core.validators.substrate_substitution_ledger "
        "--root microcosm-substrate --write --write-scope name_promise "
        "--confirm-rebuild-drift"
    )
    guard_output = json.dumps({
        "schema_version": "microcosm_substrate_substitution_write_result_v1",
        "status": "blocked_unrelated_rebuild_drift",
        "write_performed": False,
        "writer_guard": "rebuild_drift_classified_before_mutation",
        "writer_drift": {
            "schema_version": "microcosm_substrate_substitution_writer_drift_v1",
            "status": "blocked_unrelated_rebuild_drift",
            "write_scope": "name_promise",
            "changed_path_count": 437,
            "axis_counts": {"claim_ceiling": 3, "digest_relation": 434},
            "unrelated_axes": ["claim_ceiling", "digest_relation"],
        },
        "reentry_condition": "settle digest_relation and claim_ceiling drift before scoped write",
    })
    commit = "1234567890abcdef1234567890abcdef12345678"
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, "./repo-python -m py_compile tools/meta/observability/cli_prompt_trace.py", 0),
                _event(2, guard_command, 1, guard_output),
                _event(
                    3,
                    './repo-python tools/meta/control/scoped_commit.py full-paths --message "Guarded refusal semantics"',
                    0,
                    json.dumps({"new_commit": commit}),
                ),
                _event(
                    4,
                    "git diff -- microcosm-substrate/core/substrate_substitution_ledger.json",
                    0,
                    "",
                ),
            ],
            assistant_text=(
                "Scoped commit landed; the substrate ledger writer guard deliberately refused "
                "the unrelated rebuild drift and write_performed remained false."
            ),
        ),
        title="expected guarded refusal receipt test",
    )

    assert "final_validation: pass_with_guarded_refusal_receipt" in text
    assert "owner_scope_validation: pass_with_guarded_refusal_receipt" in text
    assert "source_landing: source_scope_landed_with_guarded_residual" in text
    assert "terminal_validation_priority: state=terminal_expected_guarded_refusal_present" in text
    assert "expected_guard_refusals: 1" in text
    assert "guarded_refusal_residuals: classified_rebuild_drift_pending_settlement" in text
    assert "terminal_failure_classes: current_terminal_failure=0" in text
    assert "expected_guard_refusal=1" in text
    assert "write_performed" in text
    assert meta["final_validation"] == "pass_with_guarded_refusal_receipt"
    assert meta["owner_scope_validation"] == "pass_with_guarded_refusal_receipt"
    assert meta["source_landing"] == "source_scope_landed_with_guarded_residual"
    assert meta["expected_guard_refusal_count"] == 1
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["nonblocking_terminal_failure_count"] == 1
    assert meta["guarded_refusal_residuals"] == ["classified_rebuild_drift_pending_settlement"]
    assert meta["validation_class_counts"]["expected_guarded_refusal"] == 1
    assert meta["terminal_failure_classes"]["expected_guard_refusal"] == 1


def test_trace_capsule_prose_only_green_closeout_does_not_supersede_terminal_failure() -> None:
    early_demo = (
        "PYTHONPATH=src python3 -m microcosm_core.cli crown-jewel-demo run "
        "--out /tmp/aiw_crown_jewel_demo_early"
    )
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    early_demo,
                    1,
                    '{"status":"blocked","organ_failures":["agent_closeout_faithfulness_audit"]}',
                ),
            ],
            assistant_text="Crown jewel demo and make ci passed; delivery blockers none.",
        ),
        title="prose only green closeout test",
    )

    assert "final_validation: needs_review" in text
    assert "terminal_validation_priority: state=terminal_failures_present" in text
    assert "terminal_failure_classes: current_terminal_failure=1 recovered_failure=0 stale_window_failure=0 not_validated=1 contradictory_closeout=1" in text
    assert "contradictory_closeouts=1" in text
    assert meta["final_validation"] == "needs_review"
    assert meta["blocking_terminal_failure_count"] == 1
    assert meta["stale_window_failure_count"] == 0
    assert meta["contradictory_closeout_count"] == 1


def test_trace_capsule_separates_owner_pass_from_ambient_warnings() -> None:
    task_ledger_warning = (
        '{"validation_status":"valid_with_warnings",'
        '"error_count": 0,'
        '"warning_count": 36,'
        '"warning_classes":["historical_evidence_durability_backlog"]}'
    )
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, "./repo-pytest system/server/tests/test_root_readme_entry_orientation.py", 0, "3 passed"),
                _event(2, "./repo-python tools/meta/factory/task_ledger_apply.py validate", 1, task_ledger_warning),
            ]
        ),
        title="ambient warning validation test",
    )

    assert "final_validation: pass_with_external_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "ambient_validation: valid_with_warnings" in text
    assert "ambient_warning_class: historical_evidence_durability_backlog" in text
    assert "release_authority: none" in text
    assert meta["final_validation"] == "pass_with_external_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["ambient_warning_classes"] == ["historical_evidence_durability_backlog"]
    assert meta["external_terminal_warning_count"] == 1
    assert meta["blocking_terminal_failure_count"] == 0


def test_trace_capsule_demotes_git_maintenance_admission_blocker_to_external_warning() -> None:
    commit = "1234567890abcdef1234567890abcdef12345678"
    git_maintenance_blocker = json.dumps({
        "schema": "git_gc_maintenance_v0",
        "status": "blocked",
        "object_store_status": "attention",
        "maintenance_admission": "blocked_git_lockfile_or_process",
        "repair_status": "blocked_recent_tmp_objects",
        "blocking_git_processes": [{"verb": "add", "blocking": True}],
        "tmp_objects": {
            "recent_count": 2,
            "retry_after_seconds": 112,
        },
        "repair_reentry": {
            "schema": "git_gc_maintenance_reentry_v0",
            "status": "blocked",
            "ready_to_repair": False,
            "blocked_by": [
                "blocking_git_processes",
                "recent_tmp_objects",
            ],
            "wait_ready_repair_command": (
                "./repo-python tools/meta/control/git_gc_maintenance.py "
                "--repair --min-tmp-age-seconds 120 --wait-ready-seconds 300"
            ),
        },
    })
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-pytest system/server/tests/test_storage_doctor.py -q",
                    0,
                    "23 passed in 97.39s",
                ),
                _event(
                    2,
                    "./repo-python tools/meta/control/git_gc_maintenance.py --check",
                    1,
                    git_maintenance_blocker,
                ),
                _event(
                    3,
                    './repo-python tools/meta/control/scoped_commit.py full-paths --message "Storage proof"',
                    0,
                    json.dumps({"new_commit": commit}),
                ),
            ],
            assistant_text=(
                "Storage Doctor owner tests passed and the scoped commit landed. "
                "Git maintenance is blocked by admission and has a wait-ready repair command."
            ),
        ),
        title="git maintenance admission residual",
    )

    assert "final_validation: pass_with_external_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "source_landing: source_scope_landed_with_residuals" in text
    assert "ambient_warning_class: git_maintenance_admission_residual" in text
    assert "nonblocking_terminal_failures=1" in text
    assert "scoped_failures=0" in text
    assert meta["final_validation"] == "pass_with_external_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["source_landing"] == "source_scope_landed_with_residuals"
    assert meta["ambient_warning_classes"] == ["git_maintenance_admission_residual"]
    assert meta["external_terminal_warning_count"] == 1
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["nonblocking_terminal_failure_count"] == 1
    assert meta["validation_class_counts"]["ambient_validation_warning"] == 1


def test_trace_capsule_preserves_task_ledger_projection_assimilation_receipt() -> None:
    projection_receipt = json.dumps({
        "ok": True,
        "status": "authority_appended_projection_rebuild_deferred",
        "visibility_receipt": {
            "projection_assimilation_state": {
                "schema": "task_ledger_projection_assimilation_state_v1",
                "authority_status": "authority_appended",
                "projection_rebuild": {
                    "status": "deferred",
                    "queued": True,
                },
            }
        },
    })
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --title projection-assimilation",
                    0,
                    projection_receipt,
                ),
            ]
        ),
        title="projection assimilation receipt test",
    )

    assert "receipt_assimilation: projection_deferred_queued" in text
    assert "receipt_assimilation=projection_deferred_queued" in text
    assert "receipt_assimilation: none" not in text
    assert "task_ledger_projection_deferred_queued=1" in text
    assert meta["receipt_assimilation"] == "projection_deferred_queued"
    assert meta["validation_class_counts"]["task_ledger_projection_deferred_queued"] == 1


def test_trace_capsule_types_landed_publication_held_receipt_pending() -> None:
    task_ledger_warning = (
        '{"validation_status":"valid_with_warnings",'
        '"error_count": 0,'
        '"warning_count": 36,'
        '"warning_classes":["historical_evidence_durability_backlog"]}'
    )
    push_watch = (
        '{"status":"watch",'
        '"direct_push_allowed": false,'
        '"next_safe_command": null,'
        '"ahead": 1145,'
        '"behind": 72}'
    )
    receipt_pending = (
        '{"ok": true,'
        '"status": "intake_replaced_pending",'
        '"request_id": "closeout_terminal_claim_guard_operationalization_0e21de2",'
        '"request_path": "state/task_ledger_intake/pending/closeout_terminal_claim_guard_operationalization_0e21de2.json",'
        '"request": {"state": "pending", "refs": {"commit_refs": ["0e21de204e6d0cdcfed2fe5224ff56ce12c6445b"]}}}'
    )
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, "./repo-python -m py_compile system/lib/egress_compliance.py .claude/hooks/runtime_hook.py", 0, ""),
                _event(
                    2,
                    "./repo-pytest --host-pressure-policy=warn system/server/tests/test_egress_compliance.py system/server/tests/test_action_autonomy_stop_hook.py",
                    0,
                    "74 passed in 7.59s",
                ),
                _event(3, "./repo-python tools/meta/factory/task_ledger_apply.py validate", 1, task_ledger_warning),
                _event(4, "./repo-python run_git.py audit push --json", 0, push_watch),
                _event(
                    5,
                    "./repo-python tools/meta/factory/task_ledger_apply.py enqueue-execution-receipt --request-id closeout_terminal_claim_guard_operationalization_0e21de2",
                    0,
                    receipt_pending,
                ),
            ],
            assistant_text=(
                "Source guard landed at 0e21de204e6d0cdcfed2fe5224ff56ce12c6445b; "
                "publication remains held and the execution receipt is queued in intake."
            ),
        ),
        title="closeout guard landed with receipt pending",
    )

    assert "final_validation: pass_with_publication_held_and_receipt_pending" in text
    assert "owner_scope_validation: pass" in text
    assert "source_landing: source_scope_passed" in text
    assert "publication_state: held" in text
    assert "receipt_assimilation: pending_or_claim_blocked" in text
    assert "ambient_validation: valid_with_warnings" in text
    assert "classes=" in text
    assert "publication_hold=1" in text
    assert "receipt_intake_pending=1" in text
    assert meta["final_validation"] == "pass_with_publication_held_and_receipt_pending"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["source_landing"] == "source_scope_passed"
    assert meta["publication_state"] == "held"
    assert meta["receipt_assimilation"] == "pending_or_claim_blocked"
    assert meta["validation_class_counts"]["publication_hold"] == 1
    assert meta["validation_class_counts"]["receipt_intake_pending"] == 1
    assert meta["blocking_terminal_failure_count"] == 0


def test_trace_capsule_buckets_residual_mentions_by_state(monkeypatch) -> None:
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        "microcosm_dogfood_paper_module_sidecar_claim": {
            "id": "microcosm_dogfood_paper_module_sidecar_claim",
            "state": "captured",
            "title": "Paper-module sidecar claim blocks clean Microcosm dogfood doctrine landing",
            "tags": ["microcosm", "paper_module_index"],
        },
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561": {
            "id": "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561",
            "state": "done",
            "title": "Trace capsule closeout report command leakage test failure",
            "tags": ["trace_capsule", "validation"],
        },
        "cap_finance_hourly_market_feed_schedule": {
            "id": "cap_finance_hourly_market_feed_schedule",
            "state": "signoff",
            "title": "Finance hourly market feed schedule",
            "tags": ["finance", "metabolismd", "scheduler"],
        },
        "cap_finance_next_natural_market_fire_schedule_observation": {
            "id": "cap_finance_next_natural_market_fire_schedule_observation",
            "state": "blocked",
            "title": "Observe next natural Oracle/Evolve finance market-fire schedule",
            "statement": "Observe the next natural market-clock fire after scheduler parity.",
            "tags": ["finance", "metabolismd", "scheduler", "residual_observation"],
            "satisfaction_contract": {
                "reentry_condition": "Next eligible natural market fire after scheduler parity."
            },
        },
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274": {
            "id": "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274",
            "state": "captured",
            "title": "Focused combined pytest wrapper hung after printing pass",
            "tags": ["validation_process", "pytest_wrapper", "trace_capsule"],
        },
    })
    receipt_text = "\n".join([
        "state/task_ledger/views/cap_cartography.json",
        "microcosm_dogfood_paper_module_sidecar_claim",
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561",
        "cap_finance_hourly_market_feed_schedule",
        "cap_finance_next_natural_market_fire_schedule_observation",
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274",
    ])

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_root_readme_entry_orientation.py", 0, "3 passed"),
            _event(2, "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --subject-id residuals", 0, receipt_text),
        ]),
        title="residual taxonomy test",
    )

    assert "open_product_residuals: microcosm_dogfood_paper_module_sidecar_claim" in text
    assert "open_validation_process_residuals: cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274" in text
    assert "cap_finance_hourly_market_feed_schedule" in text
    assert "closed_residuals_seen: cap_finance_hourly_market_feed_schedule,cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561" in text
    assert "blocked_external_observation_residuals: cap_finance_next_natural_market_fire_schedule_observation" in text
    assert "projection_or_view_artifacts_seen: cap_cartography.json" in text
    assert meta["open_product_residuals"] == ["microcosm_dogfood_paper_module_sidecar_claim"]
    assert meta["open_validation_process_residuals"] == [
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274"
    ]
    assert meta["closed_residuals_seen"] == [
        "cap_finance_hourly_market_feed_schedule",
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561"
    ]
    assert meta["blocked_external_observation_residuals"] == [
        "cap_finance_next_natural_market_fire_schedule_observation"
    ]
    assert meta["projection_or_view_artifacts_seen"] == ["cap_cartography.json"]


def test_trace_capsule_treats_signed_off_finance_caps_as_closed(monkeypatch) -> None:
    hourly_cap = "cap_finance_hourly_market_feed_schedule"
    body_floor_cap = "cap_microcosm_finance_eval_full_body_floor_gap"
    natural_fire_cap = "cap_finance_next_natural_market_fire_schedule_observation"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        hourly_cap: {
            "id": hourly_cap,
            "state": "signoff",
            "title": "Finance hourly market feed schedule",
            "tags": ["finance", "scheduler"],
        },
        body_floor_cap: {
            "id": body_floor_cap,
            "state": "signed_off",
            "title": "Microcosm finance eval body floor should cover the full macro finance spine",
            "tags": ["finance", "microcosm"],
        },
        natural_fire_cap: {
            "id": natural_fire_cap,
            "state": "blocked",
            "title": "Observe next natural Oracle/Evolve finance market-fire schedule",
            "statement": "Blocked on wall-clock evidence for the next natural market fire.",
            "tags": ["finance", "scheduler", "residual_observation"],
        },
    })
    receipt_text = "\n".join([
        hourly_cap,
        body_floor_cap,
        natural_fire_cap,
    ])

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-python tools/meta/factory/task_ledger_apply.py validate", 0, receipt_text),
        ]),
        title="finance readout hygiene test",
    )

    assert "open_product_residuals_selected_window: none" in text
    assert "open_product_residuals_global: not_claimed" in text
    assert f"closed_residuals_seen: {hourly_cap},{body_floor_cap}" in text
    assert f"blocked_external_observation_residuals: {natural_fire_cap}" in text
    assert meta["open_product_residuals"] == []
    assert meta["closed_residuals_seen"] == [hourly_cap, body_floor_cap]
    assert meta["blocked_external_observation_residuals"] == [natural_fire_cap]


def test_trace_capsule_validation_process_warning_does_not_block_owner_scope(monkeypatch) -> None:
    process_cap = "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        process_cap: {
            "id": process_cap,
            "state": "captured",
            "title": "Focused combined pytest wrapper hung after printing pass",
            "tags": ["validation_process", "pytest_wrapper", "trace_capsule"],
        },
    })
    wrapper_output = f"15 passed in 0.66s\nwrapper hung after printing pass\n{process_cap}"

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_cli_prompt_trace_capsule.py", 0, "6 passed"),
            _event(2, "./repo-pytest system/server/tests/test_cli_prompt_trace_capsule.py tests/test_microcosm_cold_entry_dogfood.py", 1, wrapper_output),
        ]),
        title="validation process warning test",
    )

    assert "final_validation: pass_with_validation_process_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "validation_process=needs_review" in text
    assert meta["final_validation"] == "pass_with_validation_process_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["validation_process_terminal_warning_count"] == 1
    assert meta["open_validation_process_residuals"] == [process_cap]


def test_trace_capsule_pvr_gate_with_closed_stdin_tempfail_is_public_release_blocked() -> None:
    commit = "cc48633a949938166dfe45cd09aa346a03c9930b"
    pvr_receipt = json.dumps({
        "schema_version": "microcosm_github_private_vulnerability_reporting_receipt_v0",
        "status": "blocked",
        "target_repository": "wcook04/microcosm-substrate",
        "target_repository_url": "https://github.com/wcook04/microcosm-substrate",
        "private_vulnerability_reporting": {
            "api_endpoint": "repos/wcook04/microcosm-substrate/private-vulnerability-reporting",
            "checked": False,
            "enabled": False,
        },
        "release_effect": "blocks_public_release_until_public_repo_exists_and_github_pvr_is_enabled",
        "release_blockers": [
            {
                "id": "public_repository_absent",
                "status": "blocked",
                "reason": "GitHub repository wcook04/microcosm-substrate is not visible to the configured GitHub token.",
            }
        ],
        "advisories": [
            {
                "id": "no_public_repo_mutation_performed",
                "status": "informational",
            }
        ],
    })

    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-pytest tools/meta/dissemination/tests/test_github_private_vulnerability_reporting_receipt.py tools/meta/dissemination/tests/test_microcosm_release_candidate_gate.py",
                    0,
                    "18 passed",
                ),
                _event(
                    2,
                    "./repo-pytest",
                    1,
                    "write_stdin failed: stdin is closed",
                ),
                _event(
                    3,
                    "./repo-python tools/meta/dissemination/github_private_vulnerability_reporting_receipt.py --repo wcook04/microcosm-substrate --write --check --require-pass",
                    2,
                    pvr_receipt,
                ),
                _event(
                    4,
                    './repo-python tools/meta/control/scoped_commit.py full-paths --message "Bind Microcosm private vulnerability intake gate"',
                    0,
                    json.dumps({"new_commit": commit}),
                ),
                _event(5, f"git merge-base --is-ancestor {commit} HEAD && echo ancestor", 0, "ancestor"),
            ],
            assistant_text=(
                f"Implemented and landed commit {commit}. Owner-scope PVR and release gate tests passed. "
                "The broad pytest wrapper hit a closed stdin transport failure after the owner checks, "
                "and public release remains blocked by public_repository_absent / GitHub PVR not green. "
                "No public repository was created, no visibility changed, and no public release action was taken."
            ),
        ),
        title="PVR public release blocked validation semantics",
    )

    assert "final_validation: pass_with_public_release_blocked" in text
    assert "owner_scope_validation: pass" in text
    assert "public_release_authorization: not_authorized_by_operator" in text
    assert "source_landing: source_scope_landed_with_residuals" in text
    assert "release_candidate_gate: public_release_blocked" in text
    assert "validation_process=needs_review" in text
    assert "scoped_failures=0" in text
    assert "nonblocking_terminal_failures=1" in text
    assert meta["final_validation"] == "pass_with_public_release_blocked"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["public_release_authorization"] == "not_authorized_by_operator"
    assert meta["source_landing"] == "source_scope_landed_with_residuals"
    assert meta["release_candidate_gate_decision"] == "public_release_blocked"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["raw_blocking_terminal_failure_count"] == 1
    assert meta["nonblocking_terminal_failure_count"] == 1
    assert meta["validation_process_terminal_warning_count"] == 1
    assert meta["validation_class_counts"]["validation_process_warning"] == 1


def test_trace_capsule_task_ledger_validate_does_not_reopen_residual_noise(monkeypatch) -> None:
    closed_cap = "cap_goal_fleet_governance_repo_skill_catalog_command_card_residual"
    open_cap = "cap_unrelated_open_lane"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        closed_cap: {
            "id": closed_cap,
            "state": "retired",
            "title": "Goal fleet governance repo skill catalog command card residual",
            "tags": ["goal_fleet_governance"],
        },
        open_cap: {
            "id": open_cap,
            "state": "captured",
            "title": "Unrelated open lane",
            "tags": ["unrelated"],
        },
    })
    task_ledger_validation_output = json.dumps({
        "validation_status": "valid_with_warnings",
        "error_count": 0,
        "warning_count": 1,
        "warning_classes": ["historical_evidence_durability_backlog"],
        "sample_rows": [
            {"id": closed_cap, "state": "retired"},
            {"id": open_cap, "state": "captured"},
        ],
    })

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_docs_route.py", 0, "1 passed"),
            _event(
                2,
                "./repo-python tools/meta/factory/task_ledger_apply.py validate",
                1,
                task_ledger_validation_output,
            ),
        ]),
        title="task ledger validation residual noise test",
    )

    assert "final_validation: pass_with_external_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "open_product_residuals_selected_window: none" in text
    assert "open_product_residuals_global: not_claimed" in text
    assert "closed_residuals_seen: none" in text
    assert meta["open_product_residuals"] == []
    assert meta["closed_residuals_seen"] == []
    assert meta["captured_residual_ids"] == []


def test_trace_capsule_diagnostic_cap_mentions_do_not_reopen_residuals(monkeypatch) -> None:
    open_cap = "cap_incidental_doc_mention"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        open_cap: {
            "id": open_cap,
            "state": "captured",
            "title": "Incidental doc mention",
            "tags": ["trace_capsule"],
        },
    })

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_docs_route.py", 0, "1 passed"),
            _event(
                2,
                "sed -n '1,120p' docs/example.md",
                0,
                f"A diagnostic read mentions {open_cap}, but it is not a receipt.",
            ),
        ]),
        title="diagnostic residual mention hygiene test",
    )

    assert "final_validation: passed" in text
    assert "owner_scope_validation: pass" in text
    assert "open_product_residuals_selected_window: none" in text
    assert "open_product_residuals_global: not_claimed" in text
    assert meta["open_product_residuals"] == []
    assert meta["captured_residual_ids"] == []


def test_trace_capsule_self_error_capture_is_process_not_product_residual(monkeypatch) -> None:
    self_error_cap = "cap_quick_closeout_ordering_self_error"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        self_error_cap: {
            "id": self_error_cap,
            "state": "captured",
            "title": "Closeout ordering self-error",
            "tags": ["self_error", "work_ledger", "serial_mutation"],
        },
    })

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_docs_route.py", 0, "1 passed"),
            _event(
                2,
                "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --created-by codex",
                0,
                json.dumps({"subject_id": self_error_cap, "state": "captured"}),
            ),
        ]),
        title="self error residual taxonomy test",
    )

    assert "final_validation: pass_with_validation_process_warnings" in text
    assert "open_product_residuals_selected_window: none" in text
    assert "open_product_residuals_global: not_claimed" in text
    assert f"open_validation_process_residuals: {self_error_cap}" in text
    assert meta["open_product_residuals"] == []
    assert meta["open_validation_process_residuals"] == [self_error_cap]


def test_trace_capsule_scoped_commit_landed_with_residual_dirty_state(monkeypatch) -> None:
    self_error_cap = "cap_quick_self_error_incomplete_frontend_projectio_b3a06eaa8ed2"
    commit = "0dcd84dec1f412299330efb75495b10c8be5c9f8"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        self_error_cap: {
            "id": self_error_cap,
            "state": "captured",
            "title": "Self-error: incomplete frontend projection test syntax before validation rerun",
            "tags": ["self_error", "live_projection", "frontend_validation"],
        },
    })
    host_pressure_block = json.dumps({
        "kind": "frontend_vitest_host_pressure_admission_blocked",
        "admission_consumer": {
            "status": "blocked",
            "current_status": "host_pressure_queue_until_pressure_clears",
            "recommendation": "queue_validation_until_host_pressure_clears",
            "new_work_admitted": False,
            "tempfail_exit_code": 75,
        },
    })

    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, "./repo-python -m py_compile system/server/live_projection.py system/server/main.py", 0, "Success"),
                _event(
                    2,
                    "./repo-pytest system/server/tests/test_live_projection.py",
                    0,
                    "25 passed in 11.12s",
                ),
                _event(3, "npm run test -- src/__tests__/api.projection.test.ts", 75, host_pressure_block),
                _event(
                    4,
                    "./repo-python tools/meta/testing/frontend_vitest.py --host-pressure-policy=warn -- --reporter=basic src/__tests__/api.projection.test.ts",
                    1,
                    "ERROR: Expected ')' but found end of file",
                ),
                _event(
                    5,
                    "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --created-by codex",
                    0,
                    json.dumps({"subject_id": self_error_cap, "status": "appended"}),
                ),
                _event(
                    6,
                    "./repo-python tools/meta/testing/frontend_vitest.py --host-pressure-policy=warn -- --reporter=basic src/__tests__/api.projection.test.ts",
                    0,
                    "Test Files 1 passed (1)\nTests 2 passed (2)",
                ),
                _event(
                    7,
                    './repo-python tools/meta/control/scoped_commit.py patch --path system/server/ui/src/api.ts --message "Migrate events to live projection cache"',
                    0,
                    json.dumps({"new_commit": commit}),
                ),
                _event(
                    8,
                    "git status --short -- system/server/ui/src/api.ts state/task_ledger/events.jsonl",
                    0,
                    " M system/server/ui/src/api.ts\n M state/task_ledger/events.jsonl",
                ),
                _event(9, f"git merge-base --is-ancestor {commit} HEAD && echo ancestor", 0, "ancestor"),
            ],
            assistant_text=(
                f"Implemented and landed commit {commit}. It is now an ancestor of HEAD. "
                "Focused backend tests, projection Vitest, API type check, and bounded api.ts "
                "typecheck passed. Remaining workspace dirt is unrelated same-file api.ts work and "
                f"Task Ledger authority append {self_error_cap}; projection visibility is deferred."
            ),
        ),
        title="scoped commit landed with residual dirty state",
    )

    assert "final_validation: pass_with_validation_process_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "source_landing: source_scope_landed_with_residuals" in text
    assert "open_product_residuals_selected_window: none" in text
    assert "open_product_residuals_global: not_claimed" in text
    assert f"open_validation_process_residuals: {self_error_cap}" in text
    assert "terminal_failure_classes: current_terminal_failure=0 recovered_failure=1" in text
    assert "validation_process=needs_review" in text
    assert "scoped_failures=0" in text
    assert "nonblocking_terminal_failures=1" in text
    assert meta["final_validation"] == "pass_with_validation_process_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["source_landing"] == "source_scope_landed_with_residuals"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["nonblocking_terminal_failure_count"] == 1
    assert meta["recovered_check_failures"] == 1
    assert meta["open_product_residuals"] == []
    assert meta["open_validation_process_residuals"] == [self_error_cap]


def test_trace_capsule_release_candidate_gate_ready_supersedes_historical_failure() -> None:
    release_receipt = """
    {
      "status": "pass",
      "authority_receipt": {
        "release_authorized": false,
        "wheel_install_supported": false
      },
      "projection_freshness_receipt": {"status": "pass"},
      "release_candidate_packet": {
        "candidate_state": "validated_release_candidate_pending_explicit_authorization",
        "candidate_identity": {
          "source": {
            "git_head": "3073d4dda1bbd50210fc7b8b34742e11d6fe95fa",
            "source_tree_state_kind": "git_head_clean",
            "dirty_source_path_count": 0
          },
          "artifact": {
            "artifact_payload_hash_sha256": "ac4a0c729be7feb91b3f107d28da48f34d08b89e404fce49d9f26e1f6bde92f1",
            "file_count": 2332,
            "payload_bytes": 84553842
          }
        },
        "release_authorization_gate_decision": {
          "decision": "ready_pending_operator_authorization",
          "release_authorization_allowed_now": false
        },
        "validation_summary": {
          "projection_freshness_status": "pass",
          "blocking_codes": []
        }
      }
    }
    """
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-pytest microcosm-substrate/tests/test_runtime_shell.py -q -k status_card",
                    1,
                    "AttributeError: missing project observe state write proof helper",
                ),
                _event(
                    2,
                    "PYTHONPATH=src python3 -m microcosm_core.release_export --root . --out /tmp/out --force",
                    0,
                    release_receipt,
                ),
            ],
            assistant_text=(
                "Validated clean-source release candidate; gate decision "
                "ready_pending_operator_authorization; release_authorized remains false."
            ),
        ),
        title="release candidate gate-ready status semantics test",
    )

    assert "final_validation: ready_pending_operator_authorization" in text
    assert "owner_scope_validation: pass" in text
    assert "internal_authorization: pending_operator_authorization" in text
    assert "public_release_authorization: pending_operator_authorization" in text
    assert "release_candidate_gate: ready_pending_operator_authorization" in text
    assert "historical_terminal_failures_superseded: 1" in text
    assert meta["final_validation"] == "ready_pending_operator_authorization"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["internal_authorization"] == "pending_operator_authorization"
    assert meta["public_release_authorization"] == "pending_operator_authorization"
    assert meta["release_candidate_gate_decision"] == "ready_pending_operator_authorization"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["raw_blocking_terminal_failure_count"] == 1


def test_trace_capsule_private_authorization_public_blocked_splits_gate_semantics() -> None:
    release_receipt = """
    {
      "status": "pass",
      "authority_receipt": {
        "release_authorized": false,
        "wheel_install_supported": false
      },
      "projection_freshness_receipt": {"status": "pass"},
      "source_tree_state_kind": "git_head_clean",
      "dirty_source_path_count": 0,
      "projection_freshness_status": "pass",
      "closeout_state": "systembar_slice_internal_authorization_satisfied_public_blocked",
      "release_authorization_gate_decision": {
        "decision": "ready_pending_operator_authorization",
        "release_authorization_allowed_now": false
      }
    }
    """
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(
                    1,
                    "./repo-pytest system/server/tests/test_example.py",
                    1,
                    "AssertionError: historical pre-settlement failure",
                ),
                _event(
                    2,
                    "./repo-python tools/agent_trace_structurer/systembar_contract_test.py",
                    0,
                    "ok\nProcess exited with code 0",
                ),
                _event(
                    3,
                    "./repo-python tools/meta/factory/task_ledger_apply.py execution-receipt --work-item cap",
                    0,
                    release_receipt,
                ),
            ],
            assistant_text=(
                "Internal authorization satisfied for private/local/internal settlement; "
                "release gate text still says ready_pending_operator_authorization from an old projection. "
                "Public release remains blocked and no public push, deploy, release toggle, or external action was taken."
            ),
        ),
        title="private authorization public release blocked semantics test",
    )

    assert "final_validation: pass_with_public_release_blocked" in text
    assert "final_validation: ready_pending_operator_authorization" not in text
    assert "owner_scope_validation: pass" in text
    assert "internal_authorization: satisfied" in text
    assert "public_release_authorization: not_authorized_by_operator" in text
    assert "release_candidate_gate: public_release_blocked" in text
    assert "historical_terminal_failures_superseded: 1" in text
    assert "no public push" in text
    assert meta["final_validation"] == "pass_with_public_release_blocked"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["internal_authorization"] == "satisfied"
    assert meta["public_release_authorization"] == "not_authorized_by_operator"
    assert meta["release_candidate_gate_decision"] == "public_release_blocked"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["raw_blocking_terminal_failure_count"] == 1


def test_thread_closeout_report_omits_tools_and_interns_repeated_prompts() -> None:
    prompt = "same autonomous seed prompt"
    merged = merge_full_thread([
        _turn([_event(1, "./repo-pytest tests/test_one.py", 0)], turn_index=1, prompt_text=prompt, assistant_text="Wave one landed."),
        _turn([_event(1, "./repo-pytest tests/test_two.py", 0)], turn_index=2, prompt_text=prompt, assistant_text="Wave two landed."),
    ])

    text = render_thread_closeout_report(
        merged,
        title="Two autonomous seeds",
        intern_repeated_prompts=True,
    )

    assert "# Two autonomous seeds — Closeout Report" in text
    assert "`prompt_001`" in text
    assert "Wave one landed." in text
    assert "Wave two landed." in text
    assert "Exact closeout message" in text
    assert "./repo-pytest tests/test_one.py" not in text
