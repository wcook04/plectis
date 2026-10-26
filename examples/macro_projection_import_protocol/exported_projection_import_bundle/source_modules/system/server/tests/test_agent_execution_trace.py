"""Tests for the agent-execution-trace pipeline.

Each test builds its own synthetic JSONL fixture on `tmp_path` so the runtime
can be exercised without depending on live `~/.claude` or `~/.codex` state.

Coverage:
1. Claude span pairing + duration_ms from timestamp deltas
2. Codex span pairing via call_id (function_call -> function_call_output)
2a. Codex session-control calls classify into actionable span kinds
3. route_compliance = 1.0 when kernel flag precedes any grep/read
4. anti_pattern_grep_before_kernel detection when grep fires before first kernel
5. anti_pattern_read_bomb / paper_module_skip / cold_boot_missing_info shapes
6. anti_pattern_loop_detected when same command fires 3x in the window
7. anti_pattern_stall_detected when a gap exceeds the configured threshold
8. Aggregate bottleneck percentiles per action_kind
9. Output contract: ledger, audit, summary, patterns, navigation_cache shape
10. Kernel route output shape for --process-audit, --process-bottlenecks, --process-trace
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.meta.factory import build_agent_execution_trace as trace_cli
from system.lib import agent_execution_trace as trace_lib
from system.lib import process_bottlenecks_status
from system.lib.kernel.commands import navigate
from system.lib.agent_execution_trace import (
    build_process_trace_route_packet,
    build_process_summary_route_packet,
    build_agent_execution_trace,
    build_trace_compactness_levels,
    compare_agents,
    discover_codex_sessions,
    render_trace_tape,
    _bash_action_kind,
    _extract_kernel_flags,
    _kernel_route_reason_by_flag,
    load_trace_rules,
    select_session,
)
from tools.meta.agent_telemetry.extract import classify_bash_command

REPO_ROOT = Path(__file__).resolve().parents[3]


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _write_claude_session(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _write_codex_session(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _claude_project_slug_for(repo_root: Path) -> str:
    return "-" + str(repo_root).replace("/", "-").lstrip("-").replace("_", "-")


def _seed_rules(repo_root: Path, *, overrides: dict | None = None) -> None:
    base_rules_path = REPO_ROOT / "codex/doctrine/process/trace_rules.json"
    payload = json.loads(base_rules_path.read_text(encoding="utf-8"))
    if overrides:
        payload.update(overrides)
    out = repo_root / "codex/doctrine/process/trace_rules.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_agent_execution_trace_cli_check_json_preserves_check_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def fake_build_agent_execution_trace(**_: object) -> dict:
        return {
            "audit": {
                "kind": "agent_execution_trace_audit",
                "summary": {"error_count": 0, "warning_count": 0},
            },
            "summary": {
                "kind": "agent_execution_trace_summary",
                "summary": {"error_count": 0, "warning_count": 0},
            },
        }

    monkeypatch.setattr(trace_cli, "build_agent_execution_trace", fake_build_agent_execution_trace)

    rc = trace_cli.main(["--repo-root", str(tmp_path), "--home", str(tmp_path), "--check", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["kind"] == "agent_execution_trace_summary"
    assert payload["summary"]["error_count"] == 0
    assert "sources" not in payload


def test_process_summary_missing_cache_returns_pressure_safe_status(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    standard = tmp_path / "codex/standards/std_agent_execution_trace.json"
    standard.parent.mkdir(parents=True, exist_ok=True)
    standard.write_text("{}", encoding="utf-8")

    code, payload = build_process_summary_route_packet(
        repo_root=tmp_path,
        request="codex:latest",
    )

    assert code == 0
    assert payload["summary"]["status"] == "missing_cached_summary"
    assert payload["summary"]["authority"] == "status_only_no_live_rollout_parse"
    assert payload["source_freshness"]["status"] == "missing_or_malformed_summary"
    assert payload["source_freshness"]["refresh_command"] == (
        "./repo-python tools/meta/factory/build_agent_execution_trace.py"
    )
    assert payload["payload"]["output_economy"]["profile"] == "compact_missing_read_model_status"
    assert payload["payload"]["output_economy"]["live_rollout_parse_started"] is False
    assert payload["next"][0]["command"] == (
        "./repo-python kernel.py --latency-seed-digest --latency-seed-no-git"
    )
    assert payload["next"][3]["command"] == (
        "./repo-python tools/meta/factory/build_agent_execution_trace.py"
    )
    assert "--summary" not in json.dumps(payload)


def test_cached_summary_action_kind_filter_selects_before_limit(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    standard = tmp_path / "codex/standards/std_agent_execution_trace.json"
    standard.parent.mkdir(parents=True, exist_ok=True)
    standard.write_text("{}", encoding="utf-8")
    summary_path = tmp_path / "codex/hologram/process/summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "summary": {"session_count": 4},
                "top_bottlenecks": [
                    {"action_kind": "repo_tool_command", "count": 10},
                    {"action_kind": "bash_cat", "count": 8},
                    {"action_kind": "read_file", "count": 6},
                ],
                "top_output_producers": [
                    {"action_kind": "bash_cat", "span_count": 3},
                    {"action_kind": "read_file", "span_count": 2},
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = trace_lib.load_process_bottleneck_summary_cache(
        repo_root=tmp_path,
        limit=1,
        action_kinds=["read_file"],
    )

    assert payload["query"] == {"limit": 1, "action_kinds": ["read_file"]}
    assert payload["summary"]["row_count"] == 1
    assert payload["summary"]["filtered_action_kind_count"] == 1
    assert payload["payload"]["top_bottlenecks"] == [{"action_kind": "read_file", "count": 6}]
    assert payload["payload"]["top_output_producers"] == [
        {"action_kind": "read_file", "span_count": 2}
    ]
    action_filter = payload["payload"]["action_kind_filter"]
    assert action_filter["requested"] == ["read_file"]
    assert action_filter["matched"] == ["read_file"]
    assert action_filter["missing"] == []
    assert action_filter["source_top_bottleneck_count"] == 3
    assert payload["refresh"]["cache_check_command"].endswith(
        "--cached-summary --limit 1 --action-kind read_file"
    )


def test_cached_summary_cli_action_kind_filter_compacts_cards(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    _seed_rules(tmp_path)
    standard = tmp_path / "codex/standards/std_agent_execution_trace.json"
    standard.parent.mkdir(parents=True, exist_ok=True)
    standard.write_text("{}", encoding="utf-8")
    summary_path = tmp_path / "codex/hologram/process/summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "summary": {"session_count": 2},
                "top_bottlenecks": [
                    {"action_kind": "repo_tool_command", "count": 10},
                    {
                        "action_kind": "bash_cat",
                        "count": 8,
                        "repair_hints": [{"hint_id": "replace_git_shell_chain"}],
                    },
                ],
                "top_output_producers": [
                    {"action_kind": "repo_tool_command", "span_count": 5},
                    {"action_kind": "bash_cat", "span_count": 3},
                ],
            }
        ),
        encoding="utf-8",
    )

    rc = trace_cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "--cached-summary",
            "--limit",
            "2",
            "--action-kind",
            "bash_cat",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["query"]["action_kinds"] == ["bash_cat"]
    assert payload["summary"]["filtered_action_kind_count"] == 1
    assert payload["action_kind_filter"]["matched"] == ["bash_cat"]
    assert payload["top_bottleneck_cards"] == [
        {
            "action_kind": "bash_cat",
            "count": 8,
            "repair_hint_cards": [{"hint_id": "replace_git_shell_chain"}],
        }
    ]
    assert payload["top_output_producer_cards"] == [{"action_kind": "bash_cat"}]
    assert payload["output_economy"]["profile"] == "compact_cached_summary_action_kind_filter"
    assert "--action-kind bash_cat" in payload["safe_commands"]["full_cached_summary_command"]

    rc = trace_cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "--cached-summary",
            "--check",
            "--limit",
            "2",
            "--action-kind",
            "missing_kind",
        ]
    )
    check_payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert check_payload["summary"]["filtered_action_kind_count"] == 0
    assert check_payload["action_kind_filter"]["missing"] == ["missing_kind"]
    assert (
        check_payload["output_economy"]["profile"]
        == "compact_cached_summary_check_action_kind_filter"
    )


def test_process_summary_followups_preserve_explicit_window(monkeypatch, tmp_path: Path) -> None:
    session_id = "2026-06-01T19-31-09-019e8474-37b4-7923-b25b-13958c6212cb"
    since_ts = "2026-06-01T00:00:00+00:00"

    def fake_build_agent_execution_trace(*, repo_root, since_ts: str | None, session_limit: int, **_: object) -> dict:
        assert repo_root == tmp_path.resolve()
        assert since_ts == "2026-06-01T00:00:00+00:00"
        assert session_limit == 80
        return {
            "summary": {"generated_at": "2026-06-02T00:00:00+00:00"},
            "ledger": {
                "sessions": [
                    {
                        "session_id": session_id,
                        "agent": "codex",
                        "span_count": 1,
                        "duration_ms": 1,
                        "ended_at": "2026-06-02T00:00:00+00:00",
                        "route_compliance": {"score": 1.0, "ladder_position": 3},
                        "summary_thought_trace": {
                            "schema_version": "summary_thought_trace_v1",
                            "boundary": "observable_actions_only_not_hidden_chain_of_thought",
                        },
                    }
                ]
            },
            "audit": {
                "summary": {"warning_count": 0, "error_count": 0, "finding_count": 0},
                "findings": [],
                "patterns": [],
                "bottlenecks": {},
                "context_yield_attribution": {"rows": []},
                "parse_failures": [],
            },
        }

    monkeypatch.setattr(trace_lib, "build_agent_execution_trace", fake_build_agent_execution_trace)

    code, payload = trace_lib.build_process_summary_route_packet(
        repo_root=tmp_path,
        request=session_id,
        since_ts=since_ts,
        session_limit=80,
        force_live=True,
    )

    expected_command = (
        f"./repo-python kernel.py --process-summary {session_id} --force "
        f"--after {since_ts} --limit 80"
    )
    assert code == 0
    assert payload["source_freshness"]["requested_window"] == {
        "since": since_ts,
        "session_limit": 80,
    }
    assert payload["source_freshness"]["force_live_command"] == expected_command
    assert payload["payload"]["output_economy"]["full_authority_commands"][1] == expected_command
    assert payload["next"][1]["command"] == expected_command


def _claude_tool_use_pair(
    *,
    use_id: str,
    tool_name: str,
    start: datetime,
    end: datetime,
    input_body: dict,
    is_error: bool = False,
    content: str | list[dict] = "ok",
) -> list[dict]:
    return [
        {
            "type": "assistant",
            "timestamp": _iso(start),
            "uuid": use_id + "-use",
            "parentUuid": "",
            "cwd": str(REPO_ROOT),
            "message": {
                "model": "claude-opus-4-7",
                "content": [
                    {"type": "tool_use", "id": use_id, "name": tool_name, "input": input_body}
                ],
            },
        },
        {
            "type": "user",
            "timestamp": _iso(end),
            "uuid": use_id + "-res",
            "parentUuid": use_id + "-use",
            "cwd": str(REPO_ROOT),
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": use_id,
                        "content": content,
                        "is_error": is_error,
                    }
                ]
            },
        },
    ]


@pytest.fixture
def claude_fixture(tmp_path: Path) -> tuple[Path, str]:
    _seed_rules(tmp_path)
    # Fixture repo_root IS tmp_path (so cwd match succeeds).
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    # Ladder-climb session: kernel first, then Read, then Edit.
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_01A",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=2),
        input_body={"command": "./repo-python kernel.py --pulse"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_02A",
        tool_name="Bash",
        start=t0 + timedelta(seconds=3),
        end=t0 + timedelta(seconds=5),
        input_body={"command": "./repo-python kernel.py --paper-module bridge_runtime"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_03A",
        tool_name="Read",
        start=t0 + timedelta(seconds=6),
        end=t0 + timedelta(seconds=7),
        input_body={"file_path": "/tmp/a.py"},
    )
    # Fix cwd on each record so parser accepts as repo-match.
    for rec in records:
        rec["cwd"] = str(tmp_path)
    file_path = project_dir / "session_good.jsonl"
    _write_claude_session(file_path, records)
    return file_path, slug


def test_claude_span_pairing_and_duration(claude_fixture, tmp_path: Path) -> None:
    file_path, _ = claude_fixture
    home = tmp_path / "home_claude"
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=home,
        session_files_codex=[],
        session_limit=5,
    )
    assert result["ledger"]["summary"]["session_count"] == 1
    session = result["ledger"]["sessions"][0]
    assert session["span_count"] == 3
    summary_trace = session["summary_thought_trace"]
    assert summary_trace["schema_version"] == "summary_thought_trace_v1"
    assert summary_trace["boundary"] == "observable_actions_only_not_hidden_chain_of_thought"
    assert summary_trace["route_trace"]["score"] == 1.0
    assert summary_trace["counters"]["top_command_count"] == 2
    assert summary_trace["candidate_signals"]
    # All three spans have durations > 0
    spans = result["spans_by_session"][session["session_id"]]
    durations = [sp["duration_ms"] for sp in spans]
    assert all(d > 0 for d in durations)
    assert durations[0] == 2000  # 2s
    assert durations[1] == 2000
    assert durations[2] == 1000


def test_trace_compactness_levels_show_command_output_and_edit_diff(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_kernel",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": "./repo-python kernel.py --pulse"},
        content="pulse output\nnext line",
    )
    records += _claude_tool_use_pair(
        use_id="toolu_edit",
        tool_name="Edit",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={
            "file_path": str(tmp_path / "demo.py"),
            "old_string": "alpha\nremove_me\nomega\n",
            "new_string": "alpha\nadd_me\nomega\n",
        },
        content="edited",
    )
    records += _claude_tool_use_pair(
        use_id="toolu_read",
        tool_name="Read",
        start=t0 + timedelta(seconds=4),
        end=t0 + timedelta(seconds=5),
        input_body={"file_path": str(tmp_path / "demo.py")},
        content="     1→alpha\n     2→add_me\n     3→omega\n",
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "compact_trace.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
        session_limit=5,
    )

    session = result["ledger"]["sessions"][0]
    spans = result["spans_by_session"][session["session_id"]]
    outline = session["chronological_trace_outline"]
    assert outline["level"] == "outline"
    assert outline["row_count"] == 0
    edit_span = spans[1]
    assert edit_span["edit_summary"]["added_line_count"] == 1
    assert edit_span["edit_summary"]["removed_line_count"] == 1

    levels = build_trace_compactness_levels(
        spans,
        session_id=session["session_id"],
        selected_level="tape+diff",
    )
    compact_rows = levels["levels"]["tape+diff"]["rows"]
    assert compact_rows[1]["command"].endswith("demo.py")
    assert compact_rows[0]["output"]["preview"] == ["pulse output"]
    assert compact_rows[1]["edit"]["plus"] == 1
    assert compact_rows[1]["edit"]["minus"] == 1
    assert "+add_me" in compact_rows[1]["edit"]["preview"]
    assert "-remove_me" in compact_rows[1]["edit"]["preview"]
    assert compact_rows[2]["output"]["preview"] == ["alpha"]

    tape = render_trace_tape(spans, session=session, selected_level="tape+diff", max_chars=4000)
    assert "T1 cmdx" in tape
    assert "000 $ ./repo-python kernel.py --pulse" in tape
    assert "ok 1.0s | 22b/2l: pulse output" in tape
    assert "diff +1 -1" in tape
    assert "+add_me" in tape
    assert "-remove_me" in tape
    assert "002 read Read demo.py" in tape
    assert "alpha" in tape
    assert "1→" not in tape


def test_process_trace_closeout_level_summarizes_work_and_drilldowns() -> None:
    session = {
        "session_id": "session_closeout_123",
        "agent": "codex",
        "turn_count": 1,
        "total_output_bytes": 4096,
    }
    spans = [
        {
            "sequence_index": 0,
            "turn_index": 1,
            "action_kind": "kernel_command",
            "normalized_command": "./repo-python kernel.py --entry trace",
            "duration_ms": 120,
            "outcome": "ok",
            "output_byte_count": 180,
            "output_line_count": 4,
            "output_preview": ["entry packet"],
        },
        {
            "sequence_index": 1,
            "turn_index": 1,
            "action_kind": "edit_file",
            "normalized_command": "Edit system/lib/agent_execution_trace.py",
            "target_paths": ["system/lib/agent_execution_trace.py"],
            "duration_ms": 50,
            "outcome": "ok",
            "edit_summary": {
                "target_paths": ["system/lib/agent_execution_trace.py"],
                "added_line_count": 4,
                "removed_line_count": 1,
                "preview": ["+closeout level", "-outline only"],
            },
        },
        {
            "sequence_index": 2,
            "turn_index": 1,
            "action_kind": "exec_command",
            "normalized_command": "./repo-pytest system/server/tests/test_agent_execution_trace.py",
            "duration_ms": 900,
            "outcome": "ok",
            "output_byte_count": 1200,
            "output_line_count": 12,
            "output_preview": ["1 passed"],
        },
    ]

    tape = render_trace_tape(spans, session=session, selected_level="closeout", max_chars=4000)
    assert "level=closeout" in tape
    assert "exact_closeout=./repo-python tools/meta/observability/cli_prompt_trace.py" in tape
    assert "--format thread-closeouts" in tape
    assert "worked_on system/lib/agent_execution_trace.py" in tape
    assert "changed +4/-1 system/lib/agent_execution_trace.py" in tape
    assert "validation" in tape
    assert "./repo-pytest system/server/tests/test_agent_execution_trace.py" in tape
    assert "recent" in tape
    assert "--process-trace session_closeout_123 --process-trace-level <level>" in tape

    levels = build_trace_compactness_levels(
        spans,
        session_id=session["session_id"],
        selected_level="closeout",
        session=session,
    )
    assert "closeout" in [row["level"] for row in levels["available_levels"]]
    assert levels["closeout_summary"]["exact_closeout_message"]["command"].endswith(
        "--format thread-closeouts --allow-ambiguous"
    )


def test_process_trace_route_rejects_unknown_compactness_level(tmp_path: Path) -> None:
    code, payload = build_process_trace_route_packet(repo_root=tmp_path, trace_level="maximal")

    assert code == 2
    assert payload["available_levels"] == ["outline", "closeout", "tape", "tape+diff", "audit", "raw"]


def test_latest_trace_alias_prefers_non_empty_session() -> None:
    ledger = {
        "sessions": [
            {"session_id": "empty", "agent": "codex", "span_count": 0},
            {"session_id": "use-me", "agent": "codex", "span_count": 3},
            {"session_id": "claude-use-me", "agent": "claude_code", "span_count": 2},
        ]
    }

    assert select_session(ledger, "latest")["session_id"] == "use-me"
    assert select_session(ledger, "codex:latest")["session_id"] == "use-me"
    assert select_session(ledger, "claude:latest")["session_id"] == "claude-use-me"


def test_discover_codex_sessions_uses_bounded_newest_date_dirs(tmp_path: Path) -> None:
    home = tmp_path / "home_codex"
    sessions_dir = home / ".codex" / "sessions"
    latest_a = sessions_dir / "2026" / "05" / "19" / "rollout-latest-a.jsonl"
    latest_b = sessions_dir / "2026" / "05" / "19" / "rollout-latest-b.jsonl"
    older = sessions_dir / "2026" / "05" / "18" / "rollout-older.jsonl"
    oldest = sessions_dir / "2026" / "05" / "17" / "rollout-oldest.jsonl"
    for index, path in enumerate([oldest, older, latest_a, latest_b], start=1):
        _write_codex_session(path, [{"timestamp": "2026-05-19T00:00:00Z"}])
        os.utime(path, (index, index))

    discovered = discover_codex_sessions(home=home, since_ts=None, limit=2)

    assert discovered == [latest_b, latest_a]
    assert older not in discovered
    assert oldest not in discovered


def test_route_compliance_full_when_kernel_precedes_read(claude_fixture, tmp_path: Path) -> None:
    file_path, _ = claude_fixture
    home = tmp_path / "home_claude"
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=home,
        session_files_codex=[],
        session_limit=5,
    )
    session = result["ledger"]["sessions"][0]
    rc = session["route_compliance"]
    assert rc["score"] == 1.0
    assert rc["first_kernel_span_index"] == 0
    # --pulse + --paper-module hit; ladder_position >= 3 (pulse rung=2, paper-module rung=3)
    assert rc["ladder_position"] >= 3
    assert "--pulse" in rc["ladder_rungs_hit"]
    assert "--paper-module" in rc["ladder_rungs_hit"]


def test_anti_pattern_grep_before_kernel(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    # grep fires first
    records += _claude_tool_use_pair(
        use_id="toolu_grep",
        tool_name="Grep",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"pattern": "foo"},
    )
    # then kernel
    records += _claude_tool_use_pair(
        use_id="toolu_kernel",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={"command": "./repo-python kernel.py --paper-module"},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "bad.jsonl", records)
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
        session_limit=5,
    )
    session = result["ledger"]["sessions"][0]
    pattern_ids = {ap["pattern_id"] for ap in session["anti_patterns"]}
    assert "anti_pattern_grep_before_kernel" in pattern_ids
    assert session["route_compliance"]["score"] < 1.0


def test_preflight_counts_as_cold_boot_prelude(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_preflight",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": "./repo-python kernel.py --preflight"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_entry",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={"command": './repo-python kernel.py --entry "demo" --context-budget 12000'},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "preflight_boot.jsonl", records)
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
        session_limit=5,
    )

    session = result["ledger"]["sessions"][0]
    pattern_ids = {ap["pattern_id"] for ap in session["anti_patterns"]}
    spans = result["spans_by_session"][session["session_id"]]
    assert "anti_pattern_cold_boot_missing_info" not in pattern_ids
    assert "positive_kernel_ladder_climb" in pattern_ids
    assert spans[0]["kernel_flags"] == ["--preflight"]
    assert "--preflight" in session["route_compliance"]["intended_sequence"]
    assert "--preflight" in session["route_compliance"]["ladder_rungs_hit"]
    assert session["route_compliance"]["ladder_position"] >= 2


def test_route_lease_mode_control_flags_kernel_bloat_before_direct_action(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_entry",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": './repo-python kernel.py --entry "route lease" --context-budget 12000'},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_info",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=4),
        input_body={"command": "./repo-python kernel.py --info 2>&1 | head -150"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_rg",
        tool_name="Bash",
        start=t0 + timedelta(seconds=5),
        end=t0 + timedelta(seconds=6),
        input_body={"command": "rg route_lease system/lib/agent_execution_trace.py"},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "lease_mode.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    session = result["ledger"]["sessions"][0]
    mode = session["route_lease_mode_control"]
    assert mode["direct_action_after_lease"] is True
    assert mode["signal_counts"]["entry_lease_issued"] == 1
    assert mode["signal_counts"]["full_output_kernel_bloat"] == 1
    assert result["audit"]["mode_control"]["signal_counts"]["full_output_kernel_bloat"] == 1
    assert any(
        finding.get("signal_id") == "full_output_kernel_bloat"
        for finding in result["audit"]["findings"]
    )


def test_coverage_enforcement_matrix_is_legitimate_route_lease_return(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = _claude_project_slug_for(tmp_path)
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_entry",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": './repo-python kernel.py --entry "routing repair" --context-budget 12000'},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_metabolism",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={
            "command": (
                './repo-python kernel.py --navigation-metabolism "routing repair" '
                "--metabolism-profile quick --context-budget 12000"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_matrix",
        tool_name="Bash",
        start=t0 + timedelta(seconds=4),
        end=t0 + timedelta(seconds=5),
        input_body={
            "command": (
                './repo-python kernel.py --coverage-enforcement-matrix "routing repair" '
                "--context-budget 12000"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_direct",
        tool_name="Bash",
        start=t0 + timedelta(seconds=6),
        end=t0 + timedelta(seconds=7),
        input_body={"command": "rg coverage-enforcement system/lib/agent_execution_trace.py"},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "lease_coverage_matrix.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    session = result["ledger"]["sessions"][0]
    mode = session["route_lease_mode_control"]
    assert mode["direct_action_after_lease"] is True
    assert mode["signal_counts"]["legitimate_return_to_kernel"] == 2
    assert "second_kernel_call_before_direct_action" not in mode["signal_counts"]
    assert "full_output_kernel_bloat" not in mode["signal_counts"]
    assert not any(
        finding.get("signal_id") == "second_kernel_call_before_direct_action"
        for finding in result["audit"]["findings"]
    )


def test_route_lease_reason_map_is_standard_backed() -> None:
    _kernel_route_reason_by_flag.cache_clear()
    standard_path = REPO_ROOT / "codex/standards/std_agent_execution_trace.json"
    route_control = json.loads(standard_path.read_text(encoding="utf-8"))["types"][
        "RouteLeaseModeControl"
    ]
    standard_map = route_control["kernel_route_reason_by_flag"]
    runtime_map = _kernel_route_reason_by_flag()

    assert standard_map
    assert {flag: runtime_map.get(flag) for flag in standard_map} == standard_map
    assert standard_map["--entry"] == "route"
    assert standard_map["--session-diagnostics"] == "diagnostic"
    assert standard_map["--raw-seed-ideas"] == "authority"
    for flag, reason in route_control["legitimate_return_reason_map"].items():
        assert standard_map[flag] == reason


def test_duplicate_broad_route_warning_points_to_repeat_witness(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = _claude_project_slug_for(tmp_path)
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    command = "./repo-python kernel.py --agent-operating-packet --band card"
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_entry",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": './repo-python kernel.py --entry "routing witness" --context-budget 12000'},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_first_packet",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={"command": command},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_repeat_packet",
        tool_name="Bash",
        start=t0 + timedelta(seconds=4),
        end=t0 + timedelta(seconds=5),
        input_body={"command": command},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_direct",
        tool_name="Bash",
        start=t0 + timedelta(seconds=6),
        end=t0 + timedelta(seconds=7),
        input_body={"command": "rg agent-operating-packet system/lib/agent_execution_trace.py"},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "lease_repeat_witness.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    session = result["ledger"]["sessions"][0]
    mode = session["route_lease_mode_control"]
    warning = next(
        signal
        for signal in mode["signals"]
        if signal["signal_id"] == "broad_route_repeated_without_new_authority_question"
    )

    assert mode["signal_counts"]["legitimate_return_to_kernel"] == 2
    assert mode["signal_counts"]["broad_route_repeated_without_new_authority_question"] == 1
    assert warning["normalized_command"] == command
    assert warning["repeated_count"] == 2
    assert warning["first_sequence_index"] < warning["sequence_index"]
    assert warning["first_span_id"] != warning["span_id"]


def test_session_diagnostics_and_raw_seed_are_legitimate_route_lease_returns(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = _claude_project_slug_for(tmp_path)
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_entry",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": './repo-python kernel.py --entry "routing axioms" --context-budget 12000'},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_session_diagnostics",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={
            "command": (
                "./repo-python kernel.py --session-diagnostics --lens all "
                "--last 30 --store both --json 2>&1"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_raw_seed_ideas",
        tool_name="Bash",
        start=t0 + timedelta(seconds=4),
        end=t0 + timedelta(seconds=5),
        input_body={
            "command": (
                './repo-python kernel.py --raw-seed-ideas 09 --query '
                '"axioms principles concepts mechanisms skills standards substrate"'
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_direct",
        tool_name="Bash",
        start=t0 + timedelta(seconds=6),
        end=t0 + timedelta(seconds=7),
        input_body={"command": "rg raw-seed-ideas system/lib/agent_execution_trace.py"},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "lease_session_diagnostics_raw_seed.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    session = result["ledger"]["sessions"][0]
    mode = session["route_lease_mode_control"]
    assert mode["direct_action_after_lease"] is True
    assert mode["signal_counts"]["legitimate_return_to_kernel"] == 2
    assert "second_kernel_call_before_direct_action" not in mode["signal_counts"]
    assert "full_output_kernel_bloat" not in mode["signal_counts"]
    reasons = [
        signal["kernel_call_reason"]
        for signal in mode["signals"]
        if signal["signal_id"] == "legitimate_return_to_kernel"
    ]
    assert reasons == ["diagnostic", "authority"]
    assert not any(
        finding.get("signal_id") == "second_kernel_call_before_direct_action"
        for finding in result["audit"]["findings"]
    )


def test_loop_detection(tmp_path: Path) -> None:
    _seed_rules(tmp_path, overrides={"loop_threshold_count": 3, "loop_window_ms": 60000})
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(4):
        records += _claude_tool_use_pair(
            use_id=f"toolu_loop_{i}",
            tool_name="Bash",
            start=t0 + timedelta(seconds=i * 5),
            end=t0 + timedelta(seconds=i * 5 + 1),
            input_body={"command": "grep -r foo /tmp"},
        )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "looped.jsonl", records)
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )
    session = result["ledger"]["sessions"][0]
    pattern_ids = {ap["pattern_id"] for ap in session["anti_patterns"]}
    assert "anti_pattern_loop_detected" in pattern_ids


def test_stall_detected(tmp_path: Path) -> None:
    _seed_rules(tmp_path, overrides={"stall_inactivity_threshold_ms": 5000})
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_before",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": "./repo-python kernel.py --pulse"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_after",
        tool_name="Bash",
        start=t0 + timedelta(seconds=30),
        end=t0 + timedelta(seconds=31),
        input_body={"command": "./repo-python kernel.py --info"},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "stall.jsonl", records)
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )
    session = result["ledger"]["sessions"][0]
    pattern_ids = {ap["pattern_id"] for ap in session["anti_patterns"]}
    assert "anti_pattern_stall_detected" in pattern_ids


def test_codex_span_pairing(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    codex_dir = tmp_path / "home_codex" / ".codex" / "sessions" / "2026" / "04" / "21"
    codex_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = [
        {"type": "session_meta", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
        {"type": "turn_context", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
        {
            "type": "response_item",
            "timestamp": _iso(t0 + timedelta(seconds=1)),
            "payload": {
                "type": "function_call",
                "call_id": "call_1",
                "name": "exec_command",
                "arguments": json.dumps({"cmd": "./repo-python kernel.py --pulse"}),
            },
        },
        {
            "type": "response_item",
            "timestamp": _iso(t0 + timedelta(seconds=2)),
            "payload": {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": json.dumps({"success": True, "content": "ok"}),
            },
        },
    ]
    path = codex_dir / "rollout-2026-04-21T20-00-00-abc.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_codex",
        session_files_claude=[],
    )
    assert result["ledger"]["summary"]["codex_count"] == 1
    session = result["ledger"]["sessions"][0]
    assert session["span_count"] == 1
    assert session["agent"] == "codex"
    span = result["spans_by_session"][session["session_id"]][0]
    assert span["output_byte_count"] == 2
    assert span["output_line_count"] == 1


def test_codex_trace_can_skip_output_previews_for_summary_fast_path(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    codex_dir = tmp_path / "home_codex" / ".codex" / "sessions" / "2026" / "04" / "21"
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    path = codex_dir / "rollout-2026-04-21T20-00-00-fast.jsonl"
    output = "first line\nsecond line\n"
    _write_codex_session(
        path,
        [
            {"type": "session_meta", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {"type": "turn_context", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=1)),
                "payload": {
                    "type": "function_call",
                    "call_id": "call_fast",
                    "name": "exec_command",
                    "arguments": json.dumps({"cmd": "./repo-python kernel.py --pulse"}),
                },
            },
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=2)),
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_fast",
                    "output": json.dumps({"success": True, "content": output}),
                },
            },
        ],
    )

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_codex",
        session_files_claude=[],
        include_output_previews=False,
    )

    session = result["ledger"]["sessions"][0]
    span = result["spans_by_session"][session["session_id"]][0]
    assert span["output_byte_count"] == len(output.encode("utf-8"))
    assert span["output_line_count"] == 2
    assert "output_preview" not in span


def test_command_shape_tag_cache_returns_fresh_lists() -> None:
    first = trace_lib._command_shape_tags("bash_cat", "git diff", [])
    first.append("caller_mutation")

    second = trace_lib._command_shape_tags("bash_cat", "git diff", [])

    assert "global_raw_diff" in second
    assert "caller_mutation" not in second


def test_repo_git_rev_parse_gets_git_state_snapshot_hint() -> None:
    command = "./repo-git rev-parse HEAD"

    tags = trace_lib._command_shape_tags("bash_cat", command, [])
    assert "git_state_shell_chain" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "bash_cat",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )

    assert hints[0]["hint_id"] == "replace_git_shell_chain_with_state_snapshot"
    assert hints[0]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action git_state_shell_chain"
    )
    assert hints[0]["owner_surface"] == (
        "./repo-python tools/meta/control/git_state_snapshot.py --scope <path> --path-limit 40 "
        "--recent-limit 3 --skip-git-metadata-write-probe --compact"
    )


def test_inline_python_data_probe_gets_specific_bottleneck_hint() -> None:
    command = (
        "cd /Users/operator/src/ai_workflow/microcosm-substrate && "
        "python3 -c \"import json; "
        "cov=json.load(open('core/doctrine_lattice_coverage.json')); "
        "atlas=json.load(open('core/organ_atlas.json')); print(len(cov), len(atlas))\""
    )

    tags = trace_lib._command_shape_tags(
        "bash_other",
        command,
        ["core/doctrine_lattice_coverage.json", "core/organ_atlas.json"],
    )
    assert "python_inline" in tags
    assert "inline_python_data_probe" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "bash_other",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )
    hint_ids = [row["hint_id"] for row in hints]
    assert hint_ids[0] == "replace_inline_python_data_probe_with_owner_tool"
    inline_hint = hints[0]
    assert inline_hint["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage "
        "--action-kind bash_other"
    )
    assert inline_hint["replacement_commands"][0] == inline_hint["preferred_next"]
    assert inline_hint["replacement_commands"][1] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_other --scope <path-or-owner>"
    )
    assert inline_hint["replacement_commands"][2] == (
        "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>"
    )
    assert inline_hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>"
    )


def test_focused_test_target_hint_precedes_suite_wide_guidance() -> None:
    hints = trace_lib._bottleneck_repair_hints(
        "test_or_build_command",
        [
            {
                "normalized_command": "./repo-pytest system/server/tests/test_agent_execution_trace.py",
                "target_paths": ["system/server/tests/test_agent_execution_trace.py"],
                "command_shape_tags": ["focused_test_target", "output_limited"],
            },
            {
                "normalized_command": "./repo-pytest",
                "command_shape_tags": ["suite_wide_pytest"],
            },
        ],
    )

    hint_ids = [row["hint_id"] for row in hints]
    assert hint_ids[:2] == [
        "route_focused_validation_through_action_quote",
        "scope_tests_before_full_suite",
    ]
    assert hints[0]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action test_or_build_command "
        "--scope <path-or-node> --session-id <work-ledger-session>"
    )
    assert hints[0]["concrete_preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action test_or_build_command "
        "--scope system/server/tests/test_agent_execution_trace.py"
    )
    assert hints[0]["replacement_commands"] == [hints[0]["concrete_preferred_next"]]


def test_python_heredoc_data_probe_gets_specific_bottleneck_hint() -> None:
    command = (
        "python3 - <<'PY'\n"
        "import json, subprocess, time\n"
        "from pathlib import Path\n"
        "repo = Path('/Users/operator/src/ai_workflow')\n"
        "print(json.dumps({'repo': str(repo)}))\n"
        "PY"
    )

    tags = trace_lib._command_shape_tags("bash_cat", command, [])
    assert "python_inline" in tags
    assert "inline_python_data_probe" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "bash_cat",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )
    assert hints[0]["hint_id"] == "replace_inline_python_data_probe_with_owner_tool"
    assert hints[0]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage "
        "--action-kind bash_cat"
    )


def test_unclassified_bash_other_gets_action_quote_fallback_hint() -> None:
    hints = trace_lib._bottleneck_repair_hints(
        "bash_other",
        [
            {
                "normalized_command": "printf '%s\\n' \"$SOME_LOCAL_STATE\"",
                "command_shape_tags": [],
            }
        ],
    )

    assert hints == [
        {
            "hint_id": "route_unclassified_bash_output_through_action_quote",
            "reason": "Output-heavy shell examples did not match a narrower command-shape owner.",
            "preferred_next": "./repo-python tools/meta/control/action_quote.py --action bash_other --scope <path-or-owner>",
            "quote_surface": "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>",
            "replacement_commands": [
                "./repo-python tools/meta/control/action_quote.py --action bash_other --scope <path-or-owner>",
                "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>",
                "./repo-python kernel.py --command-profile <owner-surface>",
            ],
        }
    ]


def test_unknown_tool_wait_hint_uses_exact_action_quote_alias() -> None:
    hints = trace_lib._bottleneck_repair_hints("unknown_tool", [{"command_shape_tags": []}])

    assert hints[0]["hint_id"] == "replace_long_tool_wait_with_process_summary"
    assert hints[0]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action unknown_tool "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert hints[0]["replacement_commands"][0] == hints[0]["preferred_next"]
    assert hints[0]["owner_surface"] == "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"


def test_python_module_cli_output_limiter_gets_compact_mode_hint() -> None:
    command = "PYTHONPATH=src python3 -m microcosm_core circuit-attribution 2>&1 | tail -55"

    tags = trace_lib._command_shape_tags("bash_cat", command, [])
    assert "output_limited" in tags
    assert "python_module_cli" in tags
    assert "python_module_cli_output_limited" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "bash_cat",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )
    hint_ids = [row["hint_id"] for row in hints]
    assert hint_ids[0] == "replace_python_module_tail_with_compact_cli_mode"
    assert hint_ids.index("replace_python_module_tail_with_compact_cli_mode") < hint_ids.index(
        "replace_shell_limiter_with_compact_packet"
    )
    module_hint = next(
        row for row in hints if row["hint_id"] == "replace_python_module_tail_with_compact_cli_mode"
    )
    assert module_hint["preferred_next"] == (
        "PYTHONPATH=microcosm-substrate/src ./repo-python -m microcosm_core circuit-attribution --card"
    )
    assert module_hint["replacement_commands"][0] == (
        "PYTHONPATH=microcosm-substrate/src ./repo-python -m microcosm_core circuit-attribution --card"
    )
    assert module_hint["replacement_commands"][1] == (
        "./repo-python tools/meta/control/action_quote.py --action command_surface --scope <module-or-command>"
    )
    assert "--card route" in module_hint["specific_replacement_reason"]
    assert module_hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>"
    )


def test_codex_namespaced_exec_command_classifies_kernel_shape(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    codex_dir = tmp_path / "home_codex" / ".codex" / "sessions" / "2026" / "04" / "21"
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    path = codex_dir / "rollout-2026-04-21T20-00-01-abc.jsonl"
    _write_codex_session(
        path,
        [
            {"type": "session_meta", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {"type": "turn_context", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=1)),
                "payload": {
                    "type": "function_call",
                    "call_id": "call_namespaced_exec",
                    "name": "functions.exec_command",
                    "arguments": json.dumps({"cmd": "./repo-python kernel.py --pulse"}),
                },
            },
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=2)),
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_namespaced_exec",
                    "output": json.dumps({"success": True, "content": "ok"}),
                },
            },
        ],
    )
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_codex",
        session_files_claude=[],
    )

    session = result["ledger"]["sessions"][0]
    span = result["spans_by_session"][session["session_id"]][0]
    assert session["action_kind_counts"]["kernel_command"] == 1
    assert "unknown_tool" not in session["action_kind_counts"]
    assert span["tool_name"] == "functions.exec_command"
    assert span["is_kernel_shape"] is True
    assert span["kernel_flags"] == ["--pulse"]
    assert span["output_byte_count"] == 2
    assert span["output_line_count"] == 1


def test_command_output_body_is_not_persisted_by_default(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    codex_dir = tmp_path / "home_codex" / ".codex" / "sessions" / "2026" / "04" / "21"
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    secret_output = "super-secret-token-value\nsecond line"
    path = codex_dir / "rollout-2026-04-21T20-00-01-privacy.jsonl"
    _write_codex_session(
        path,
        [
            {"type": "session_meta", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {"type": "turn_context", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=1)),
                "payload": {
                    "type": "function_call",
                    "call_id": "call_private_output",
                    "name": "functions.exec_command",
                    "arguments": json.dumps({"cmd": "./repo-python kernel.py --info"}),
                },
            },
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=2)),
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_private_output",
                    "output": json.dumps({"success": True, "content": secret_output}),
                },
            },
        ],
    )
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_codex",
        session_files_claude=[],
    )

    session = result["ledger"]["sessions"][0]
    span = result["spans_by_session"][session["session_id"]][0]
    assert span["output_byte_count"] == len(secret_output.encode("utf-8"))
    assert span["output_line_count"] == 2
    assert secret_output not in json.dumps(result, ensure_ascii=False)


def test_codex_session_io_and_control_tools_are_not_unknown(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    codex_dir = tmp_path / "home_codex" / ".codex" / "sessions" / "2026" / "04" / "21"
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    path = codex_dir / "rollout-2026-04-21T20-00-02-abc.jsonl"
    wait_output = "Chunk ID: eee23a\nWall time: 89.9827 seconds\nProcess exited with code 0\n"
    _write_codex_session(
        path,
        [
            {"type": "session_meta", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {"type": "turn_context", "timestamp": _iso(t0), "payload": {"cwd": str(tmp_path)}},
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=1)),
                "payload": {
                    "type": "function_call",
                    "call_id": "call_wait",
                    "name": "write_stdin",
                    "arguments": json.dumps({
                        "session_id": 70016,
                        "chars": "",
                        "yield_time_ms": 120000,
                        "max_output_tokens": 12000,
                    }),
                },
            },
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=91)),
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_wait",
                    "output": wait_output,
                },
            },
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=92)),
                "payload": {
                    "type": "function_call",
                    "call_id": "call_plan",
                    "name": "update_plan",
                    "arguments": json.dumps({"plan": [{"step": "Inspect", "status": "completed"}]}),
                },
            },
            {
                "type": "response_item",
                "timestamp": _iso(t0 + timedelta(seconds=93)),
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_plan",
                    "output": "Plan updated",
                },
            },
        ],
    )
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_codex",
        session_files_claude=[],
    )

    session = result["ledger"]["sessions"][0]
    assert session["action_kind_counts"]["exec_session_io"] == 1
    assert session["action_kind_counts"]["task_tool"] == 1
    assert "unknown_tool" not in session["action_kind_counts"]
    wait_span = result["spans_by_session"][session["session_id"]][0]
    assert wait_span["duration_ms"] == 90000
    assert wait_span["normalized_command"] == "write_stdin session_id=70016 yield_time_ms=120000 chars_len=0"
    assert wait_span["output_byte_count"] == len(wait_output.encode("utf-8"))
    assert wait_span["output_line_count"] == 3
    assert "exec_session_poll" in wait_span["shape_tags"]
    assert result["audit"]["bottlenecks"]["exec_session_io"]["slow_count"] == 1
    assert result["audit"]["bottlenecks"]["exec_session_io"]["actionability_class"] == "wait_state_polling"
    assert result["audit"]["bottlenecks"]["exec_session_io"]["optimization_priority_score"] == 35
    wait_hint = result["audit"]["bottlenecks"]["exec_session_io"]["repair_hints"][0]
    assert wait_hint["hint_id"] == "inspect_preceding_exec_or_add_status_surface"
    assert wait_hint["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action exec_session_io "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert wait_hint["owner_surface"] == "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"
    assert wait_hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action exec_session_io "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert wait_hint["replacement_commands"][0] == (
        "./repo-python tools/meta/control/action_quote.py --action exec_session_io "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert (
        "./repo-python tools/meta/control/action_quote.py --action process_summary_status "
        "--scope <session_id|claude:latest|codex:latest>"
    ) in wait_hint["replacement_commands"]
    assert "./repo-python kernel.py --process-trace <session_id>" in wait_hint["replacement_commands"]
    assert "raw task-output bodies" in wait_hint["privacy_boundary"]


def test_configured_exec_waits_rank_below_direct_command_bottlenecks() -> None:
    configured_wait = {
        "action_kind": "exec_session_io",
        "p95_ms": 180000,
        "slow_count": 12,
        "total_duration_ms": 900000,
        **trace_lib._bottleneck_actionability(
            "exec_session_io",
            [{"command_shape_tags": ["exec_session_poll", "configured_wait"]}],
        ),
    }
    repo_tool = {
        "action_kind": "repo_tool_command",
        "p95_ms": 30000,
        "slow_count": 2,
        "total_duration_ms": 60000,
        **trace_lib._bottleneck_actionability("repo_tool_command", [{"command_shape_tags": ["factory_builder"]}]),
    }

    rows = sorted(
        [configured_wait, repo_tool],
        key=trace_lib._bottleneck_summary_sort_key,
        reverse=True,
    )

    assert rows[0]["action_kind"] == "repo_tool_command"
    assert rows[1]["actionability_class"] == "wait_state_polling"
    assert rows[1]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action exec_session_io "
        "--scope <session_id|claude:latest|codex:latest>"
    )


def test_repo_python_module_invocations_classify_by_primary_tool() -> None:
    repo_python = str(REPO_ROOT / "repo-python")

    assert _bash_action_kind(f"{repo_python} kernel.py --pulse") == "kernel_command"
    assert _extract_kernel_flags(f"{repo_python} kernel.py --pulse") == ["--pulse"]
    assert (
        _bash_action_kind(
            f"{repo_python} -m tools.meta.observability.station_render render "
            "--view agent_observability 2>&1 | cat"
        )
        == "repo_tool_command"
    )
    assert _bash_action_kind("cat /tmp/x.txt") == "bash_cat"

    histogram = classify_bash_command(
        f"{repo_python} -m tools.meta.observability.station_render render "
        "--view agent_observability 2>&1 | head -20",
        repo_root=str(REPO_ROOT),
    )
    assert histogram["repo_native_commands"] == 1
    assert "./repo-python -m tools.meta.observability.station_render" in histogram["command_patterns"]
    assert "./repo-python:module:tools.meta.observability.station_render" in histogram["python_modes"]


def test_bottleneck_aggregation(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = []
    # Fast kernel command
    records += _claude_tool_use_pair(
        use_id="toolu_fast",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": "./repo-python kernel.py --pulse"},
    )
    # Slow bash_cat (30s, well over 5s threshold)
    records += _claude_tool_use_pair(
        use_id="toolu_slow",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=32),
        input_body={"command": "cat /tmp/x.txt"},
    )
    # A second cat span keeps the aggregate honest: cross-session audit must use
    # real span durations, not repeat a session max for every span in the kind.
    records += _claude_tool_use_pair(
        use_id="toolu_medium",
        tool_name="Bash",
        start=t0 + timedelta(seconds=33),
        end=t0 + timedelta(seconds=43),
        input_body={
            "command": (
                "git status --short 2>&1 | head -30; "
                "git diff 2>&1 | head -40; "
                "git log -1 --oneline"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_python_tail",
        tool_name="Bash",
        start=t0 + timedelta(seconds=43),
        end=t0 + timedelta(seconds=113),
        input_body={"command": "PYTHONPATH=src python3 -m microcosm_core circuit-attribution 2>&1 | tail -55"},
    )
    # Output-limited test/build and repo-tool pipelines should be attributed to
    # the primary command, not to the trailing grep/head/tail limiter.
    records += _claude_tool_use_pair(
        use_id="toolu_pytest_tail",
        tool_name="Bash",
        start=t0 + timedelta(seconds=114),
        end=t0 + timedelta(seconds=234),
        input_body={
            "command": (
                "./repo-python -m pytest system/server/tests/test_x.py -q 2>&1 | "
                "python3 -c \"import sys; print(sys.stdin.read()[:200])\""
            )
        },
        content="pytest line\n" * 25,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_factory_grep",
        tool_name="Bash",
        start=t0 + timedelta(seconds=235),
        end=t0 + timedelta(seconds=295),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py rebuild "
                "--ignore-host-pressure 2>&1 | tail -20"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_task_ledger_capture",
        tool_name="Bash",
        start=t0 + timedelta(seconds=295),
        end=t0 + timedelta(seconds=417),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
                "--title 'slow capture' --statement-file tmp/capture.md"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_task_output_read",
        tool_name="Read",
        start=t0 + timedelta(seconds=418),
        end=t0 + timedelta(seconds=478),
        input_body={"file_path": "/private/tmp/claude-501/-Users-example-src-ai_workflow/session/tasks/b123.output"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_find_head",
        tool_name="Bash",
        start=t0 + timedelta(seconds=479),
        end=t0 + timedelta(seconds=524),
        input_body={"command": "find . -name '*.py' 2>/dev/null | head -20"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_recursive_grep",
        tool_name="Bash",
        start=t0 + timedelta(seconds=525),
        end=t0 + timedelta(seconds=570),
        input_body={"command": "grep -rli -E \"clob-endpoint|orderbook\" tools/ system/ 2>/dev/null | head -20"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_background_poll",
        tool_name="Bash",
        start=t0 + timedelta(seconds=571),
        end=t0 + timedelta(seconds=691),
        input_body={
            "command": (
                "until grep -q -E \"(Test Files|Error:)\" "
                "/private/tmp/claude-501/-Users-example-src-ai_workflow/session/tasks/b456.output; "
                "do sleep 2; done"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_doc_read",
        tool_name="Read",
        start=t0 + timedelta(seconds=692),
        end=t0 + timedelta(seconds=747),
        input_body={"file_path": str(tmp_path / "AGENTS.md")},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_task_wait",
        tool_name="Task",
        start=t0 + timedelta(seconds=748),
        end=t0 + timedelta(seconds=878),
        input_body={"description": "long worker", "prompt": "summarize the subsystem"},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "bottleneck.jsonl", records)
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )
    audit = result["audit"]
    kinds = set(audit["bottlenecks"].keys())
    assert "bash_cat" in kinds
    assert "kernel_command" in kinds
    assert "test_or_build_command" in kinds
    assert "repo_tool_command" in kinds
    assert "task_tool" in kinds
    assert audit["bottlenecks"]["bash_cat"]["count"] == 3
    assert audit["bottlenecks"]["bash_cat"]["p50_ms"] == 30000
    assert audit["bottlenecks"]["bash_cat"]["slow_count"] == 3
    assert audit["bottlenecks"]["bash_cat"]["example_spans"][0]["duration_ms"] == 70000
    assert audit["bottlenecks"]["bash_cat"]["example_spans"][0]["session_id"]
    cat_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["bash_cat"]["repair_hints"]}
    assert audit["bottlenecks"]["bash_cat"]["repair_hints"][0]["hint_id"] == "replace_shell_limiter_with_compact_packet"
    assert "replace_git_shell_chain_with_state_snapshot" in cat_hint_ids
    assert "replace_global_raw_diff_with_diff_review_context" in cat_hint_ids
    cat_hints = {
        row["hint_id"]: row for row in audit["bottlenecks"]["bash_cat"]["repair_hints"]
    }
    assert cat_hints["replace_git_shell_chain_with_state_snapshot"]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action git_state_shell_chain"
    )
    assert cat_hints["replace_git_shell_chain_with_state_snapshot"]["owner_surface"] == (
        "./repo-python tools/meta/control/git_state_snapshot.py --scope <path> --path-limit 40 "
        "--recent-limit 3 --skip-git-metadata-write-probe --compact"
    )
    assert (
        "./repo-python tools/meta/control/git_state_snapshot.py --scope <path> "
        "--path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact"
        in cat_hints["replace_git_shell_chain_with_state_snapshot"]["replacement_commands"]
    )
    assert cat_hints["replace_global_raw_diff_with_diff_review_context"]["preferred_next"] == (
        "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --path-limit 40 "
        "--recent-limit 3 --skip-git-metadata-write-probe --compact"
    )
    assert cat_hints["replace_shell_limiter_with_compact_packet"]["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>"
    )
    assert any(
        "global_raw_diff" in row["command_shape_tags"]
        for row in audit["bottlenecks"]["bash_cat"]["example_spans"]
    )
    assert audit["bottlenecks"]["test_or_build_command"]["count"] == 1
    assert audit["bottlenecks"]["test_or_build_command"]["max_ms"] == 120000
    assert audit["bottlenecks"]["test_or_build_command"]["total_output_bytes"] == len(("pytest line\n" * 25).encode("utf-8"))
    assert audit["bottlenecks"]["test_or_build_command"]["example_spans"][0]["output_line_count"] == 25
    assert "output_limited" in audit["bottlenecks"]["test_or_build_command"]["example_spans"][0]["command_shape_tags"]
    assert "focused_test_target" in audit["bottlenecks"]["test_or_build_command"]["example_spans"][0]["command_shape_tags"]
    test_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["test_or_build_command"]["repair_hints"]}
    assert "avoid_tail_masked_test_runs" in test_hint_ids
    assert "route_focused_validation_through_action_quote" in test_hint_ids
    assert audit["bottlenecks"]["test_or_build_command"]["repair_hints"][0]["hint_id"] == (
        "route_focused_validation_through_action_quote"
    )
    assert audit["bottlenecks"]["test_or_build_command"]["repair_hints"][0]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action test_or_build_command "
        "--scope <path-or-node> --session-id <work-ledger-session>"
    )
    assert audit["bottlenecks"]["test_or_build_command"]["repair_hints"][0]["concrete_preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action test_or_build_command "
        "--scope system/server/tests/test_x.py"
    )
    assert audit["bottlenecks"]["task_tool"]["count"] == 1
    assert audit["bottlenecks"]["task_tool"]["max_ms"] == 130000
    task_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["task_tool"]["repair_hints"]}
    assert "replace_long_tool_wait_with_process_summary" in task_hint_ids
    task_hints = {
        row["hint_id"]: row for row in audit["bottlenecks"]["task_tool"]["repair_hints"]
    }
    assert task_hints["replace_long_tool_wait_with_process_summary"]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action task_tool "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert task_hints["replace_long_tool_wait_with_process_summary"]["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action process_summary_status "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert audit["bottlenecks"]["repo_tool_command"]["count"] == 2
    assert audit["bottlenecks"]["repo_tool_command"]["max_ms"] == 122000
    repo_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["repo_tool_command"]["repair_hints"]}
    repo_hints = {
        row["hint_id"]: row for row in audit["bottlenecks"]["repo_tool_command"]["repair_hints"]
    }
    assert "use_task_ledger_rebuild_check_before_full_rebuild" in repo_hint_ids
    assert repo_hints["use_task_ledger_rebuild_check_before_full_rebuild"]["preferred_next"] == (
        "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress"
    )
    assert (
        "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress"
        in repo_hints["use_task_ledger_rebuild_check_before_full_rebuild"][
            "replacement_commands"
        ]
    )
    assert (
        "./repo-python tools/meta/factory/task_ledger_apply.py drain-deferred-rebuilds --limit 1 --quiet-progress"
        in repo_hints["use_task_ledger_rebuild_check_before_full_rebuild"][
            "replacement_commands"
        ]
    )
    assert "append_task_ledger_capture_before_projection_rebuild" in repo_hint_ids
    assert repo_hints["append_task_ledger_capture_before_projection_rebuild"]["preferred_next"] == (
        "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
        "--projection-rebuild-policy off ..."
    )
    assert (
        "./repo-python tools/meta/factory/task_ledger_apply.py drain-deferred-rebuilds --limit 1 --quiet-progress"
        in repo_hints["append_task_ledger_capture_before_projection_rebuild"][
            "replacement_commands"
        ]
    )
    assert "prefer_check_or_targeted_builder_mode" in repo_hint_ids
    assert repo_hints["prefer_check_or_targeted_builder_mode"]["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>"
    )
    assert "task_output_file" in audit["bottlenecks"]["read_file"]["example_spans"][0]["command_shape_tags"]
    assert "tmp_artifact_file" in audit["bottlenecks"]["read_file"]["example_spans"][0]["command_shape_tags"]
    read_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["read_file"]["repair_hints"]}
    assert "replace_output_file_read_with_status_surface" in read_hint_ids
    assert "prefer_card_or_section_before_full_doc_read" in read_hint_ids
    read_hints = {
        row["hint_id"]: row for row in audit["bottlenecks"]["read_file"]["repair_hints"]
    }
    assert read_hints["replace_output_file_read_with_status_surface"]["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action process_summary_status "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert read_hints["replace_tmp_file_read_with_structured_summary"]["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action process_summary_status "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    doc_hint = next(
        row
        for row in audit["bottlenecks"]["read_file"]["repair_hints"]
        if row["hint_id"] == "prefer_card_or_section_before_full_doc_read"
    )
    assert doc_hint["owner_surface"] == './repo-python kernel.py --entry "<task>" --context-budget 12000'
    assert doc_hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action read_file --scope <path-or-topic>"
    )
    assert (
        "./repo-python tools/meta/control/action_quote.py --action read_file --scope <path-or-topic>"
        in doc_hint["replacement_commands"]
    )
    assert './repo-python kernel.py --context-pack "<task>" --context-budget 12000' in doc_hint["replacement_commands"]
    assert "./repo-python kernel.py --docs-route <query-or-path>" in doc_hint["replacement_commands"]
    assert "./repo-python kernel.py --option-surface <kind_id> --band card --ids <row_id>" in doc_hint["replacement_commands"]
    assert "full prose" in doc_hint["privacy_boundary"]
    find_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["bash_find"]["repair_hints"]}
    assert "replace_find_scan_with_rg_files_or_option_surface" in find_hint_ids
    find_hint = next(
        row
        for row in audit["bottlenecks"]["bash_find"]["repair_hints"]
        if row["hint_id"] == "replace_find_scan_with_rg_files_or_option_surface"
    )
    assert find_hint["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <term-or-root>"
    )
    assert find_hint["owner_surface"] == trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE
    assert find_hint["quote_surface"].endswith("--action bash_find --scope <term-or-root>")
    assert find_hint["replacement_commands"][0] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <term-or-root>"
    )
    assert "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>" in find_hint["replacement_commands"]
    assert (
        "./repo-python tools/meta/control/action_quote.py --action artifact_discovery_inventory --scope <term-or-root>"
        in find_hint["replacement_commands"]
    )
    assert "rg --files <known-roots> | rg '<name-or-term>'" in find_hint["replacement_commands"]
    assert "metadata only" in find_hint["privacy_boundary"]
    assert "background_poll" in audit["bottlenecks"]["bash_grep"]["example_spans"][0]["command_shape_tags"]
    grep_hints = audit["bottlenecks"]["bash_grep"]["repair_hints"]
    grep_hint_order = [row["hint_id"] for row in grep_hints]
    grep_hint_ids = {row["hint_id"] for row in grep_hints}
    assert grep_hint_order.index("replace_raw_search_scan_with_owner_route") < grep_hint_order.index(
        "replace_tmp_artifact_scan_with_owner_summary"
    )
    assert grep_hint_order.index("replace_tmp_artifact_scan_with_owner_summary") < grep_hint_order.index(
        "replace_shell_limiter_with_compact_packet"
    )
    assert grep_hint_order.index("replace_raw_search_scan_with_owner_route") < grep_hint_order.index(
        "replace_shell_limiter_with_compact_packet"
    )
    polling_hint = next(row for row in grep_hints if row["hint_id"] == "replace_polling_with_status_surface")
    assert polling_hint["preferred_next"] == "./repo-python kernel.py --process-summary claude:latest"
    assert polling_hint["owner_surface"] == "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"
    assert polling_hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action process_summary_status "
        "--scope <session_id|claude:latest|codex:latest>"
    )
    assert "./repo-python kernel.py --process-trace <session_id>" in polling_hint["replacement_commands"]
    assert "raw task-output bodies" in polling_hint["privacy_boundary"]
    assert "replace_raw_search_scan_with_owner_route" in grep_hint_ids
    raw_search_hint = next(row for row in grep_hints if row["hint_id"] == "replace_raw_search_scan_with_owner_route")
    assert raw_search_hint["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
    )
    assert raw_search_hint["owner_surface"] == trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE
    assert "pre_action_card" not in raw_search_hint
    assert "drop common glue words" in raw_search_hint["scope_narrowing"]
    assert raw_search_hint["quote_surface"].endswith("--action bash_grep --scope <term-or-root>")
    assert (
        raw_search_hint["replacement_commands"][0]
        == "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
    )
    assert "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>" in raw_search_hint["replacement_commands"]
    assert (
        "./repo-python tools/meta/control/action_quote.py --action artifact_discovery_inventory --scope <term-or-root>"
        in raw_search_hint["replacement_commands"]
    )
    assert './repo-python kernel.py --command-card "broad discovery inventory"' not in raw_search_hint["replacement_commands"]
    assert './repo-python kernel.py --entry "<task>" --context-budget 12000' in raw_search_hint["replacement_commands"]
    assert "metadata only" in raw_search_hint["privacy_boundary"]
    assert result["summary"]["top_output_producers"][0]["action_kind"] == "test_or_build_command"
    assert result["summary"]["summary"]["total_output_bytes"] >= audit["bottlenecks"]["test_or_build_command"]["total_output_bytes"]
    # Confirm slow_action_shape finding fired
    rules = {f["rule"] for f in audit["findings"]}
    assert "slow_action_shape" in rules


def test_host_filesystem_find_bottleneck_prefers_host_quote(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = _claude_project_slug_for(tmp_path)
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = _claude_tool_use_pair(
        use_id="toolu_host_find",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=45),
        input_body={
            "command": (
                "find /Users/operator -maxdepth 4 -type d "
                "\\( -iname '*Google Drive*' -o -iname '*GoogleDrive*' "
                "-o -iname '*googledrive*' \\) -print | head -20"
            )
        },
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "host-find.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    hints = result["audit"]["bottlenecks"]["bash_find"]["repair_hints"]
    assert hints[0]["hint_id"] == "replace_host_find_scan_with_host_filesystem_quote"
    assert hints[0]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_find "
        "--scope <host-path-or-term>"
    )
    assert hints[0]["owner_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action host_filesystem_discovery "
        "--scope <host-path-or-term>"
    )
    assert "mdfind -onlyin \"$HOME\" '<name predicate>' | head -20" in hints[0]["replacement_commands"]
    assert hints[0]["pre_action_card"]["status"] == "host_filesystem_scope_first"
    assert "does not walk host paths" in hints[0]["privacy_boundary"]
    hint_ids = {row["hint_id"] for row in hints}
    assert "replace_find_scan_with_rg_files_or_option_surface" in hint_ids


def test_git_object_find_bottleneck_prefers_git_maintenance(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = _claude_project_slug_for(tmp_path)
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = _claude_tool_use_pair(
        use_id="toolu_git_object_find",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=31),
        input_body={
            "command": (
                "top_objects=$(find .git/objects -type f -path '.git/objects/??/*' "
                "-exec stat -f '%z %N' {} + | sort -nr | head -40)"
            )
        },
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "git-object-find.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    hints = result["audit"]["bottlenecks"]["bash_find"]["repair_hints"]
    assert hints[0]["hint_id"] == "replace_git_object_find_scan_with_gc_maintenance_check"
    assert hints[0]["preferred_next"] == (
        "./repo-python tools/meta/control/git_gc_maintenance.py --check"
    )
    assert hints[0]["pre_action_card"]["status"] == "git_object_status_first"
    assert hints[0]["replacement_commands"][0] == (
        "./repo-python tools/meta/control/git_gc_maintenance.py --check"
    )
    assert "replace_find_scan_with_rg_files_or_option_surface" in {
        row["hint_id"] for row in hints
    }


def test_read_file_bottleneck_generic_hint_for_unclassified_source_reads(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = _claude_project_slug_for(tmp_path)
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    source_path = tmp_path / "system/lib/example.py"
    records = _claude_tool_use_pair(
        use_id="toolu_source_read",
        tool_name="Read",
        start=t0,
        end=t0 + timedelta(seconds=12),
        input_body={"file_path": str(source_path)},
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "source-read.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    read_row = result["audit"]["bottlenecks"]["read_file"]
    assert read_row["example_spans"][0]["command_shape_tags"] == []
    hint = next(
        row
        for row in read_row["repair_hints"]
        if row["hint_id"] == "prefer_bounded_read_or_identifier_search"
    )
    assert hint["owner_surface"] == "known_path_bounded_read"
    assert hint["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py --action read_file --scope <path-or-topic>"
    )
    assert hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action read_file --scope <path-or-topic>"
    )
    assert (
        hint["replacement_commands"][0]
        == "./repo-python tools/meta/control/action_quote.py --action read_file --scope <path-or-topic>"
    )
    assert "rg -n '<symbol-or-error>' <known-path-or-root>" in hint["replacement_commands"]
    assert "sed -n '<start>,<end>p' <known-path>" in hint["replacement_commands"]
    assert hint["replacement_commands"][-1] == './repo-python kernel.py --context-pack "<task>" --context-budget 12000'
    assert "full file bodies" in hint["privacy_boundary"]


def test_kernel_command_by_kernel_flag_aggregation(tmp_path: Path) -> None:
    """kernel_command.by_kernel_flag decomposes the aggregate by primary route flag,
    and top_kernel_command_flags surfaces on summary independent of top_bottlenecks cutoff.

    Aggregation key invariant: every kernel_flag value is a stable --flag-name token,
    never a raw command, normalized_command, session id, tmp path, or other unbounded
    high-cardinality value (see OpenTelemetry semantic-convention / Prometheus naming).
    """
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records: list[dict] = []
    # Three --entry spans with distinct query strings; all must aggregate under --entry
    # (NOT the unique normalized commands / queries / session ids).
    for idx, query in enumerate([
        "explore slow commands",
        "find the worst latency offender today 2026-04-21",
        "context pack 'agent concurrency, work item spine, scoping commits' x42",
    ]):
        records += _claude_tool_use_pair(
            use_id=f"toolu_entry_{idx}",
            tool_name="Bash",
            start=t0 + timedelta(seconds=10 * idx),
            end=t0 + timedelta(seconds=10 * idx + 1 + idx),
            input_body={
                "command": f"./repo-python kernel.py --entry \"{query}\" --context-budget 12000"
            },
        )
    # One slow --paper-module-coverage span — should land on its own flag row.
    records += _claude_tool_use_pair(
        use_id="toolu_pmc_slow",
        tool_name="Bash",
        start=t0 + timedelta(seconds=120),
        end=t0 + timedelta(seconds=300),
        input_body={"command": "./repo-python kernel.py --paper-module-coverage"},
    )
    # One --session-diagnostics span with output redirect (high-cardinality tmp path
    # appears in the command but must NOT become an aggregation key).
    records += _claude_tool_use_pair(
        use_id="toolu_diag_redirect",
        tool_name="Bash",
        start=t0 + timedelta(seconds=310),
        end=t0 + timedelta(seconds=440),
        input_body={
            "command": (
                "./repo-python kernel.py --session-diagnostics --lens all --last 50 "
                "--store both --json > /tmp/probe_ab12cd34.json"
            )
        },
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "kernel_flags.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )
    bottlenecks = result["audit"]["bottlenecks"]
    assert "kernel_command" in bottlenecks
    kc_row = bottlenecks["kernel_command"]
    assert kc_row["repair_hints"][0]["hint_id"] == "route_kernel_flag_through_command_surface"
    assert kc_row["repair_hints"][0]["kernel_flag"] == "--paper-module-coverage"
    assert kc_row["repair_hints"][0]["concrete_preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action kernel_command --scope paper-module-coverage"
    )
    by_flag = kc_row.get("by_kernel_flag") or []
    flag_names = {row["kernel_flag"] for row in by_flag}
    assert "--entry" in flag_names
    assert "--paper-module-coverage" in flag_names
    assert "--session-diagnostics" in flag_names
    entry_row = next(row for row in by_flag if row["kernel_flag"] == "--entry")
    assert entry_row["count"] == 3, "three distinct --entry queries must collapse to one flag row"
    pmc_row = next(row for row in by_flag if row["kernel_flag"] == "--paper-module-coverage")
    assert pmc_row["max_ms"] == 180000
    assert pmc_row["slow_count"] >= 1

    # Aggregation-key cardinality invariant: kernel_flag values are bounded --flag
    # tokens, not raw commands / queries / tmp paths / session ids.
    forbidden_substrings = (
        "/tmp/",
        "./repo-python",
        "kernel.py",
        "explore slow",
        " ",
        "probe_ab12cd34",
    )
    for row in by_flag:
        flag = row["kernel_flag"]
        assert flag.startswith("--"), f"kernel_flag {flag!r} must be a --flag token"
        assert len(flag) <= 64, f"kernel_flag {flag!r} too long for a bounded key"
        for needle in forbidden_substrings:
            assert needle not in flag, (
                f"kernel_flag {flag!r} contains high-cardinality fragment {needle!r}"
            )

    # top_kernel_command_flags must surface on summary artifact independent of whether
    # kernel_command made the top_bottlenecks cutoff. Verify presence and value
    # equivalence to the by_kernel_flag rows.
    summary = result["summary"]
    top_flags = summary.get("top_kernel_command_flags") or []
    assert top_flags, "summary.top_kernel_command_flags must be present when kernel spans exist"
    summary_flag_names = {row["kernel_flag"] for row in top_flags}
    assert "--paper-module-coverage" in summary_flag_names
    assert "--session-diagnostics" in summary_flag_names
    assert "--entry" in summary_flag_names


def test_context_yield_attribution_classifies_known_motifs(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 5, 14, 1, 0, 0, tzinfo=timezone.utc)
    long_entry_packet = "entry packet section\n" * 2500
    long_overlap_packet = "PACKET v=3.2 title cargo handle\n" * 500
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_entry_packet",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=2),
        input_body={"command": './repo-python kernel.py --entry "context economy" --context-budget 12000'},
        content=long_entry_packet,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_global_diff",
        tool_name="Bash",
        start=t0 + timedelta(seconds=3),
        end=t0 + timedelta(seconds=4),
        input_body={"command": "./repo-git diff"},
        content="diff --git a/system/lib/x.py b/system/lib/x.py\n" * 200,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_broad_raw_search",
        tool_name="Bash",
        start=t0 + timedelta(seconds=4),
        end=t0 + timedelta(seconds=5),
        input_body={
            "command": (
                'rg -n "cap_census|cap_cartography" '
                "system/lib/task_ledger_events.py system/lib/standard_option_surface.py"
            )
        },
        content="system/lib/task_ledger_events.py:1:cap_census\n" * 200,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_scoped_raw_search",
        tool_name="Bash",
        start=t0 + timedelta(seconds=5),
        end=t0 + timedelta(seconds=6),
        input_body={"command": 'rg -n "def _coerce_id_list" system/lib/task_ledger_events.py'},
        content="system/lib/task_ledger_events.py:10:def _coerce_id_list(value):\n",
    )
    records += _claude_tool_use_pair(
        use_id="toolu_overlap_preflight",
        tool_name="Bash",
        start=t0 + timedelta(seconds=7),
        end=t0 + timedelta(seconds=9),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-id s --path system/lib/agent_execution_trace.py --full"
            )
        },
        content=long_overlap_packet,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_compact_preflight",
        tool_name="Bash",
        start=t0 + timedelta(seconds=9),
        end=t0 + timedelta(seconds=10),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-id s --path system/lib/agent_execution_trace.py"
            )
        },
        content="compact preflight row\n" * 300,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_tool_result_read",
        tool_name="Read",
        start=t0 + timedelta(seconds=10),
        end=t0 + timedelta(seconds=11),
        input_body={"file_path": "/tmp/tool-results/abc.txt"},
        content="tool-result payload\n" * 400,
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "context_yield.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    attribution = result["audit"]["context_yield_attribution"]
    assert attribution["kind"] == "context_yield_attribution_packet"
    assert attribution["schema_version"] == "context_yield_attribution_packet_v0"
    motifs = {row["motif"]: row for row in attribution["rows"]}
    assert "entry_over_admission" in motifs
    assert "raw_global_diff" in motifs
    assert "raw_body_before_selection" in motifs
    assert "metadata_cargo" in motifs
    assert "tool_result_carryover" in motifs
    assert attribution["summary"]["known_motif_coverage"] == {
        "entry_over_admission": True,
        "raw_global_diff": True,
        "metadata_cargo": True,
    }
    assert motifs["raw_global_diff"]["existing_route"].endswith("--diff-review --compact")
    raw_body = motifs["raw_body_before_selection"]
    assert raw_body["governance_status_counts"]["governed_route_available_but_not_used"] >= 1
    assert raw_body["governance_status_counts"]["accepted_required_context"] >= 1
    assert raw_body["governance_status_bytes"]["governed_route_available_but_not_used"] > 0
    assert raw_body["governance_status_bytes"]["accepted_required_context"] > 0
    assert raw_body["active_bytes"] > raw_body["actionable_active_bytes"]
    assert raw_body["actionable_span_count"] >= 1
    assert raw_body["decision"]["rank_basis"]["actionable_active_bytes"] == raw_body["actionable_active_bytes"]
    assert raw_body["decision"]["rank_basis"]["sort_order"] == (
        "actionable_active_bytes_then_total_active_bytes_then_span_count"
    )
    assert raw_body["owner_coverage"]["route_available"] is True
    assert raw_body["owner_coverage"]["route_used"] is False
    assert raw_body["owner_coverage"]["route_gap"] == "route_available_but_not_used_for_active_examples"
    assert raw_body["decision"]["patch_owner_surface"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action artifact_discovery_inventory --scope <term-or-root>"
    )
    steering = raw_body["steering"]
    assert steering["point_of_use_surface"] == "./repo-python kernel.py --process-bottlenecks --force"
    assert steering["replacement_route"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action artifact_discovery_inventory --scope <term-or-root>"
    )
    assert steering["preferred_quote_route"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
    )
    assert (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
        in steering["quote_routes"]
    )
    assert steering["applies_to_status"] == "governed_route_available_but_not_used"
    assert steering["applies_to_count"] >= 1
    assert "accepted_required_context" in steering["does_not_apply_to"]
    assert "false_positive" in steering["does_not_apply_to"]
    assert "Scoped low-output rg/find" in steering["accepted_case_guard"]
    assert "object-specific terms" in steering["scope_narrowing"]
    assert steering["pre_action_card"]["status"] == "route_first_for_broad_discovery"
    assert steering["pre_action_card"]["first_route"].endswith("--action bash_grep --scope <term-or-root>")
    assert "drop glue words" in steering["pre_action_card"]["scope_rule"]
    assert steering["command_shape_clusters"]["status"] == "governed_route_available_but_not_used"
    assert steering["command_shape_clusters"]["tag_counts"]["raw_search_scan"] >= 1
    assert steering["command_shape_clusters"]["action_kind_counts"]["bash_grep"] >= 1
    assert sum(steering["command_shape_clusters"]["targeting"].values()) >= 1
    assert raw_body["recency_boundary"]["oldest_example_at"]
    assert raw_body["examples"][0]["governance_status"] in raw_body["governance_status_counts"]
    assert motifs["metadata_cargo"]["span_count"] == 1
    assert "raw command output bodies" in motifs["metadata_cargo"]["omission_receipt"]["omitted"]
    tool_result = motifs["tool_result_carryover"]
    assert tool_result["governance_status_counts"]["governed_route_available_but_not_used"] >= 1
    assert tool_result["governance_status_counts"]["needs_owner_patch"] == 0
    assert tool_result["owner_coverage"]["route_gap"] == "route_available_but_not_used_for_active_examples"
    assert tool_result["steering"]["replacement_route"].endswith("--process-summary <session_id|claude:latest|codex:latest>")
    assert "process-summary first" in tool_result["steering"]["accepted_case_guard"]
    session = result["ledger"]["sessions"][0]
    assert session["task_result_reads"]["count"] == 1
    assert session["task_result_reads"]["total_output_bytes"] > 0
    assert session["task_result_reads"]["top_reads"][0]["target_kind"] == "tool_results"
    assert session["task_result_reads"]["raw_reopen_route"].endswith(session["session_id"])
    assert result["summary"]["context_yield_attribution"]["summary"]["top_motif"] in motifs
    assert attribution["summary"]["top_actionable_bytes"] == attribution["rows"][0]["actionable_active_bytes"]
    assert attribution["summary"]["rank_basis"] == "actionable_active_bytes_then_total_active_bytes_then_span_count"
    rank_keys = [
        (row["actionable_active_bytes"], row["active_bytes"], row["span_count"])
        for row in attribution["rows"]
    ]
    assert rank_keys == sorted(rank_keys, reverse=True)


def test_context_yield_attribution_ignores_small_diagnostic_packets(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 5, 14, 2, 0, 0, tzinfo=timezone.utc)
    records = _claude_tool_use_pair(
        use_id="toolu_small_diagnostic_packet",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": "./repo-python kernel.py --process-bottlenecks --force"},
        content="small owner packet\n" * 20,
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "context_yield_small_diagnostic.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    motifs = {row["motif"]: row for row in result["audit"]["context_yield_attribution"]["rows"]}
    assert "diagnostic_packet_over_budget" not in motifs


def test_context_yield_attribution_accepts_bounded_diagnostic_owner_packets(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 5, 14, 2, 5, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_bounded_process_bottlenecks",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": "./repo-python kernel.py --process-bottlenecks --force"},
        content="bounded owner packet\n" * 2100,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_large_process_bottlenecks",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={"command": "./repo-python kernel.py --process-bottlenecks --force"},
        content="oversized owner packet\n" * 2600,
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "context_yield_bounded_diagnostic.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    motifs = {row["motif"]: row for row in result["audit"]["context_yield_attribution"]["rows"]}
    diagnostic = motifs["diagnostic_packet_over_budget"]
    assert diagnostic["governance_status_counts"]["accepted_required_context"] == 1
    assert diagnostic["governance_status_counts"]["needs_owner_patch"] == 1
    assert diagnostic["owner_coverage"]["route_used"] is True
    assert diagnostic["actionable_span_count"] == 1
    assert diagnostic["actionable_active_bytes"] > 0
    accepted_example = next(
        example
        for example in diagnostic["examples"]
        if example["span_id"].endswith("toolu_bounded_process_bottlenecks")
    )
    assert accepted_example["governance_status"] == "accepted_required_context"


def test_context_yield_attribution_ignores_in_budget_route_packets(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 5, 14, 2, 15, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_in_budget_entry_packet",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": './repo-python kernel.py --entry "context economy" --context-budget 12000'},
        content="entry packet section\n" * 800,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_in_budget_context_pack",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={"command": './repo-python kernel.py --context-pack "context economy" --context-budget 12000'},
        content="context pack selected row\n" * 900,
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "context_yield_in_budget_route_packets.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    motifs = {row["motif"]: row for row in result["audit"]["context_yield_attribution"]["rows"]}
    assert "entry_over_admission" not in motifs
    assert "context_pack_selected_rows" not in motifs


def test_context_yield_attribution_accepts_bounded_context_pack_packets(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 5, 14, 2, 20, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_bounded_context_pack",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={"command": './repo-python kernel.py --context-pack "context economy"'},
        content="bounded context pack\n" * 2100,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_large_context_pack",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={"command": './repo-python kernel.py --context-pack "context economy"'},
        content="oversized context pack\n" * 2600,
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "context_yield_bounded_context_pack.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    motifs = {row["motif"]: row for row in result["audit"]["context_yield_attribution"]["rows"]}
    context_pack = motifs["context_pack_selected_rows"]
    assert context_pack["governance_status_counts"]["accepted_required_context"] == 1
    assert context_pack["governance_status_counts"]["needs_owner_patch"] == 1
    assert context_pack["owner_coverage"]["route_used"] is True
    assert context_pack["actionable_span_count"] == 1
    accepted_example = next(
        example
        for example in context_pack["examples"]
        if example["span_id"].endswith("toolu_bounded_context_pack")
    )
    assert accepted_example["governance_status"] == "accepted_required_context"


def test_context_yield_attribution_accepts_bounded_compact_preflight_packets(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 5, 14, 2, 25, 0, tzinfo=timezone.utc)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_bounded_compact_preflight",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=1),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-id s --path system/lib/agent_execution_trace.py"
            )
        },
        content="bounded compact preflight row\n" * 1500,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_large_compact_preflight",
        tool_name="Bash",
        start=t0 + timedelta(seconds=2),
        end=t0 + timedelta(seconds=3),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-id s --path system/lib/agent_execution_trace.py"
            )
        },
        content="oversized compact preflight row\n" * 2600,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_full_preflight",
        tool_name="Bash",
        start=t0 + timedelta(seconds=4),
        end=t0 + timedelta(seconds=5),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-id s --path system/lib/agent_execution_trace.py --full"
            )
        },
        content="full preflight row\n" * 1500,
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "context_yield_bounded_preflight.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    motifs = {row["motif"]: row for row in result["audit"]["context_yield_attribution"]["rows"]}
    metadata = motifs["metadata_cargo"]
    assert metadata["governance_status_counts"]["accepted_required_context"] == 1
    assert metadata["governance_status_counts"]["needs_owner_patch"] == 2
    assert metadata["owner_coverage"]["route_used"] is True
    assert metadata["actionable_span_count"] == 2
    accepted_example = next(
        example
        for example in metadata["examples"]
        if example["span_id"].endswith("toolu_bounded_compact_preflight")
    )
    assert accepted_example["governance_status"] == "accepted_required_context"


def test_process_audit_after_window_filters_old_spans_inside_fresh_session(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 5, 14, 1, 0, 0, tzinfo=timezone.utc)
    cutoff = t0 + timedelta(minutes=30)
    records = []
    records += _claude_tool_use_pair(
        use_id="toolu_old_full_preflight",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=2),
        input_body={
            "command": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-id s --path system/lib/agent_execution_trace.py --full"
            )
        },
        content="PACKET v=3.2 title cargo handle\n" * 500,
    )
    records += _claude_tool_use_pair(
        use_id="toolu_new_entry",
        tool_name="Bash",
        start=cutoff + timedelta(seconds=1),
        end=cutoff + timedelta(seconds=3),
        input_body={"command": './repo-python kernel.py --entry "context economy" --context-budget 12000'},
        content="entry packet section\n" * 1200,
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "after_window.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
        since_ts=cutoff.isoformat(),
    )

    attribution = result["audit"]["context_yield_attribution"]
    motifs = {row["motif"]: row for row in attribution["rows"]}
    assert "entry_over_admission" in motifs
    assert "metadata_cargo" not in motifs
    assert result["audit"]["summary"]["total_span_count"] == 1


def test_frontend_vitest_bottleneck_routes_to_action_quote(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = "-" + str(tmp_path).replace("/", "-").lstrip("-").replace("_", "-")
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = _claude_tool_use_pair(
        use_id="toolu_frontend_vitest",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=130),
        input_body={
            "command": (
                "npx vitest run src/pages/__tests__/RootNavigator.test.tsx "
                "2>&1 > /tmp/rootnavigator.txt; grep -E 'Test Files|Tests |FAIL' /tmp/rootnavigator.txt"
            )
        },
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "frontend_vitest.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    hints = result["audit"]["bottlenecks"]["test_or_build_command"]["repair_hints"]
    hint_ids = {row["hint_id"] for row in hints}
    assert "route_frontend_vitest_through_action_quote" in hint_ids
    quote_hint = next(row for row in hints if row["hint_id"] == "route_frontend_vitest_through_action_quote")
    assert "frontend_vitest_validation" in quote_hint["preferred_next"]


def test_paper_module_output_limiter_bottleneck_routes_to_action_quote(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    slug = _claude_project_slug_for(tmp_path)
    project_dir = tmp_path / "home_claude" / ".claude" / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    t0 = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)
    records = _claude_tool_use_pair(
        use_id="toolu_paper_module_sed",
        tool_name="Bash",
        start=t0,
        end=t0 + timedelta(seconds=120),
        input_body={
            "command": "./repo-python kernel.py --paper-module mathematics_mission_pipeline 2>&1 | sed -n '1,150p'"
        },
    )
    for rec in records:
        rec["cwd"] = str(tmp_path)
    _write_claude_session(project_dir / "paper_module_sed.jsonl", records)

    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "home_claude",
        session_files_codex=[],
    )

    hints = result["audit"]["bottlenecks"]["kernel_command"]["repair_hints"]
    hint_ids = {row["hint_id"] for row in hints}
    assert "route_paper_module_output_through_action_quote" in hint_ids
    quote_hint = next(row for row in hints if row["hint_id"] == "route_paper_module_output_through_action_quote")
    assert "paper_module_index" in quote_hint["preferred_next"]


def test_kernel_context_pack_limiter_gets_selected_lens_hint() -> None:
    command = './repo-python kernel.py --context-pack "speed refinement" --context-budget 12000 2>&1 | head -80'

    tags = trace_lib._command_shape_tags("kernel_command", command, [])
    assert "output_limited" in tags
    assert "context_pack" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "kernel_command",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )
    hint_ids = [row["hint_id"] for row in hints]
    assert hint_ids[0] == "replace_context_pack_limiter_with_selected_lens"
    assert hint_ids.index("replace_context_pack_limiter_with_selected_lens") < hint_ids.index(
        "replace_kernel_output_limiter_with_compact_mode"
    )
    limiter_hint = next(row for row in hints if row["hint_id"] == "replace_kernel_output_limiter_with_compact_mode")
    assert limiter_hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action kernel_command --scope <task-or-route>"
    )
    assert limiter_hint["replacement_commands"][0].endswith("--action kernel_command --scope <task-or-route>")
    lens_hint = hints[0]
    assert lens_hint["replacement_commands"][-1] == (
        "./repo-python kernel.py --row <kind_id>:<row_id> --band card"
    )


def test_kernel_entry_limiter_gets_bounded_entry_hint() -> None:
    command = './repo-python kernel.py --entry "assess current speed surface" 2>&1 | head -80'

    tags = trace_lib._command_shape_tags("kernel_command", command, [])
    assert "output_limited" in tags
    assert "entry_packet" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "kernel_command",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )
    hint_ids = [row["hint_id"] for row in hints]
    assert hint_ids[0] == "replace_entry_limiter_with_bounded_entry_or_context_pack"
    assert hint_ids.index("replace_entry_limiter_with_bounded_entry_or_context_pack") < hint_ids.index(
        "replace_kernel_output_limiter_with_compact_mode"
    )
    entry_hint = hints[0]
    assert entry_hint["quote_surface"] == (
        "./repo-python tools/meta/control/action_quote.py --action kernel_command --scope <task-or-route>"
    )
    assert (
        "./repo-python tools/meta/control/action_quote.py --action kernel_command --scope <task-or-route>"
        in entry_hint["replacement_commands"]
    )


def test_kernel_host_pressure_packet_gets_compact_recheck_hint() -> None:
    command = (
        "./repo-python kernel.py --host-pressure --host-pressure-no-processes "
        "--host-pressure-compact --host-pressure-event-limit 500"
    )

    tags = trace_lib._command_shape_tags("kernel_command", command, [])
    assert "host_pressure_packet" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "kernel_command",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )
    hint_ids = [row["hint_id"] for row in hints]
    assert hint_ids[0] == "replace_host_pressure_full_packet_with_compact_recheck"
    host_hint = hints[0]
    assert host_hint["replacement_commands"][0].endswith("--host-pressure-event-limit 100")


def test_kernel_inventory_limiter_gets_cluster_or_card_hint() -> None:
    command = "./repo-python kernel.py --kind-atlas 2>&1 | head -80"

    tags = trace_lib._command_shape_tags("kernel_command", command, [])
    assert "output_limited" in tags
    assert "kind_atlas_packet" in tags

    hints = trace_lib._bottleneck_repair_hints(
        "kernel_command",
        [{"normalized_command": command, "command_shape_tags": tags}],
    )
    hint_ids = [row["hint_id"] for row in hints]
    assert hint_ids[0] == "replace_inventory_limiter_with_cluster_or_card_band"
    inventory_hint = hints[0]
    assert inventory_hint["replacement_commands"][0] == (
        "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag"
    )


def test_output_contract_shapes(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    result = build_agent_execution_trace(
        repo_root=tmp_path,
        rules_path=tmp_path / "codex/doctrine/process/trace_rules.json",
        home=tmp_path / "empty_home",
        session_files_claude=[],
        session_files_codex=[],
    )
    ledger = result["ledger"]
    audit = result["audit"]
    summary = result["summary"]
    patterns = result["patterns"]
    nav = result["navigation_cache"]
    assert ledger["kind"] == "agent_execution_trace_ledger"
    assert ledger["schema_version"].startswith("agent_execution_trace_ledger_")
    for field in ("summary", "sessions", "sources", "generated_at"):
        assert field in ledger
    assert audit["kind"] == "agent_execution_trace_audit"
    for field in ("findings", "bottlenecks", "patterns", "summary", "mode_control"):
        assert field in audit
    assert summary["kind"] == "agent_execution_trace_summary"
    assert patterns["kind"] == "agent_execution_trace_patterns"
    assert nav["kind"] == "agent_execution_trace_navigation_cache"


def test_select_session_aliases() -> None:
    ledger = {
        "sessions": [
            {"session_id": "s_claude_0", "agent": "claude_code"},
            {"session_id": "s_codex_0", "agent": "codex"},
        ]
    }
    assert select_session(ledger, "latest")["session_id"] == "s_claude_0"
    assert select_session(ledger, "claude:latest")["session_id"] == "s_claude_0"
    assert select_session(ledger, "codex:latest")["session_id"] == "s_codex_0"
    assert select_session(ledger, "s_codex_0")["session_id"] == "s_codex_0"
    assert select_session(ledger, "unknown") is None


def test_compare_agents_contract() -> None:
    ledger = {
        "sessions": [
            {
                "session_id": "s1",
                "agent": "claude_code",
                "span_count": 10,
                "action_kind_counts": {"kernel_command": 2, "grep_tool": 1},
                "route_compliance": {"score": 0.8},
                "anti_patterns": [{"pattern_id": "anti_pattern_grep_before_kernel"}],
            },
            {
                "session_id": "s2",
                "agent": "codex",
                "span_count": 20,
                "action_kind_counts": {"kernel_command": 5, "bash_grep": 2},
                "route_compliance": {"score": 1.0},
                "anti_patterns": [],
            },
        ]
    }
    buckets = compare_agents(ledger)
    assert buckets["claude_code"]["sessions"] == 1
    assert buckets["codex"]["sessions"] == 1
    assert buckets["claude_code"]["avg_route_compliance"] == 0.8
    assert buckets["codex"]["avg_route_compliance"] == 1.0
    assert buckets["claude_code"]["anti_pattern_counts"]["anti_pattern_grep_before_kernel"] == 1


def test_kernel_route_process_audit_shape() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-audit"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_audit"
    assert payload["output_profile"] in {
        "compact_process_audit_default",
        "compact_process_audit_missing_read_model",
    }
    assert "summary" in payload
    assert "payload" in payload
    assert "findings" in payload["payload"]
    assert "bottlenecks" in payload["payload"]
    assert "patterns" in payload["payload"]
    assert "mode_control" in payload["payload"]
    assert payload["payload"]["output_economy"]["full_payload_command"] == (
        "./repo-python kernel.py --process-audit --full"
    )
    assert payload["payload"]["output_economy"]["target_bytes"] == 30_000
    assert len(payload["payload"]["findings"]) <= 5
    assert len(payload["payload"]["patterns"]) <= 5
    assert len(payload["payload"]["bottlenecks"]) <= 4
    assert payload["payload"]["context_yield_attribution"]["rows_returned"] <= 3
    for row in payload["payload"]["bottlenecks"].values():
        assert "example_spans" not in row
    assert len(result.stdout.encode()) < 30_000


def test_process_audit_cache_freshness_marks_stale_static_sources(tmp_path: Path) -> None:
    cache = tmp_path / "codex/hologram/process/audit.json"
    source = tmp_path / "system/lib/agent_execution_trace.py"
    cache.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    cache.write_text("{}", encoding="utf-8")
    source.write_text("# changed\n", encoding="utf-8")
    os.utime(cache, ns=(100, 100))
    os.utime(source, ns=(200, 200))

    freshness = navigate._process_audit_cache_freshness(cache, [source])

    assert freshness["status"] == "stale_static_sources"
    assert freshness["static_source_status"] == "source_newer_than_cached_audit"
    assert freshness["patch_selection_policy"] == (
        "refresh_or_force_live_before_selecting_process_audit_patch"
    )
    assert freshness["authoritative_decision_command"] == (
        "./repo-python kernel.py --process-bottlenecks --force"
    )
    assert freshness["stale_source_count"] == 1


def test_process_audit_stale_cache_next_commands_start_with_live_decision() -> None:
    next_commands = navigate._process_audit_next_commands(
        {
            "status": "stale_static_sources",
            "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
            "refresh_command": "./repo-python tools/meta/factory/build_agent_execution_trace.py",
        }
    )

    assert next_commands[0]["command"] == "./repo-python kernel.py --process-bottlenecks --force"
    assert next_commands[1]["command"] == (
        "./repo-python tools/meta/factory/build_agent_execution_trace.py"
    )


def test_kernel_command_profile_process_audit_shape() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--command-profile", "process-audit"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "command_profile"
    assert payload["surface"] == "process-audit"
    phases = {phase["phase"]: phase for phase in payload["phases"]}
    assert phases["process_audit_status_packet"]["output_bytes"] < 30_000
    assert phases["process_audit_status_packet"]["source_mode"] in {
        "cached_audit",
        "live_in_memory",
    }
    assert "process_audit_output_shape" in phases


def test_kernel_route_process_audit_full_shape() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-audit", "--full"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_audit"
    assert payload["output_profile"] == "full_process_audit"
    assert isinstance(payload["payload"]["findings"], list)
    assert isinstance(payload["payload"]["bottlenecks"], dict)
    assert isinstance(payload["payload"]["patterns"], list)
    assert isinstance(payload["payload"]["mode_control"], dict)


def test_kernel_route_process_audit_after_window_shape() -> None:
    result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--process-audit",
            "--after",
            "2999-01-01T00:00:00Z",
            "--limit",
            "3",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_audit"
    assert payload["query"]["after"] == "2999-01-01T00:00:00Z"
    assert payload["query"]["limit"] == 3
    assert payload["summary"]["window"]["since"] == "2999-01-01T00:00:00Z"
    assert payload["summary"]["window"]["session_limit"] == 3
    assert payload["summary"]["session_count"] == 0
    assert payload["payload"]["patterns"] == []


def test_kernel_route_process_patterns_after_window_shape() -> None:
    result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--process-patterns",
            "--after",
            "2999-01-01T00:00:00Z",
            "--limit",
            "3",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_patterns"
    assert payload["query"]["after"] == "2999-01-01T00:00:00Z"
    assert payload["query"]["limit"] == 3
    assert payload["payload"]["patterns"] == []


def test_kernel_route_process_patterns_default_uses_cached_read_model() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-patterns"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_patterns"
    assert payload["schema_version"] == "process_patterns_v1"
    assert payload["source_freshness"]["mode"] == "cached_patterns"
    assert payload["query"]["after"] is None
    assert payload["query"]["limit"] is None
    assert isinstance(payload["payload"]["patterns"], list)
    assert payload["payload"]["output_economy"]["profile"] == "compact_process_patterns_default_v0"
    for pattern in payload["payload"]["patterns"]:
        assert "session_id_hits" not in pattern
        if pattern.get("session_id_hit_count"):
            assert len(pattern["session_id_hits_preview"]) <= 5
            assert pattern["session_id_hits_omitted"] == max(0, pattern["session_id_hit_count"] - 5)


def test_kernel_route_process_bottlenecks_after_window_shape() -> None:
    result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--process-bottlenecks",
            "--after",
            "2999-01-01T00:00:00Z",
            "--limit",
            "3",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_bottlenecks"
    assert payload["query"]["after"] == "2999-01-01T00:00:00Z"
    assert payload["query"]["limit"] == 3
    assert payload["payload"]["top_bottlenecks"] == []
    assert payload["payload"]["top_output_producers"] == []
    context_yield = payload["payload"]["context_yield_attribution"]
    if context_yield:
        assert context_yield["output_profile"] == "compact_context_yield_status"
        assert context_yield["rows_returned"] == 0


def test_kernel_route_navigation_mechanism_factory_shape() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--navigation-mechanism-factory", "--limit", "10"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.navigation_mechanism_factory"
    assert payload["payload"]["schema_version"] == "navigation_mechanism_projection_ledger_v0"
    assert payload["payload"]["summary"]["provider_mutation_authority"] is False
    assert payload["payload"]["projection_claims"]
    assert payload["payload"]["provider_receipt_skeleton"]["mutation_authority"] is False


def test_kernel_route_navigation_mechanism_replay_shape() -> None:
    result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--navigation-mechanism-replay",
            "replay_skill_find_first_contact",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.navigation_mechanism_replay"
    assert payload["summary"]["authority_posture"] == "fitness_probe_not_acceptance"
    results = payload["payload"]["route_replay_results"]
    assert len(results) == 1
    assert results[0]["schema_version"] == "navigation_route_replay_result_v0"
    assert results[0]["passed"] is True


def test_navigation_mechanism_validator_cli_passes() -> None:
    result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "tools/meta/factory/validate_navigation_mechanism_facets.py",
            "--limit",
            "5",
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["counts"]["projection_claims"] >= 1


def test_kernel_route_process_summary_shape() -> None:
    process_window = ["--limit", "1"]
    trace_result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--process-trace",
            "latest",
            "--process-trace-format",
            "json",
            *process_window,
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    tape_result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--process-trace",
            "latest",
            "--process-trace-max-chars",
            "3000",
            *process_window,
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    audit_result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-audit", *process_window],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    summary_result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--process-summary",
            "latest",
            "--force",
            *process_window,
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    trace_payload = json.loads(trace_result.stdout)
    payload = json.loads(summary_result.stdout)
    assert payload["kind"] == "kernel.navigate.process_summary"
    assert payload["schema_version"] == "process_summary_v1"
    assert payload["query"]["force_live"] is True
    assert payload["source_freshness"]["mode"] == "live_in_memory"
    assert payload["source_freshness"]["dynamic_rollout_status"] == "revalidated_live_in_memory"
    assert payload["source_freshness"]["requested_window"]["session_limit"] == 1
    assert payload["identity_scope"]["schema_version"] == "process_summary_identity_scope_v1"
    assert payload["identity_scope"]["selection_basis"] == "latest_ended_session"
    assert payload["identity_scope"]["current_session_claim"] == "not_claimed"
    assert payload["warnings"][0]["warning_id"] == "process_summary_latest_alias_not_self_identity"
    assert payload["payload"]["session"]["session_id"]
    assert payload["payload"]["session"]["summary_thought_trace"]["schema_version"] == "summary_thought_trace_v1"
    assert payload["payload"]["session"]["summary_thought_trace"]["boundary"] == "observable_actions_only_not_hidden_chain_of_thought"
    assert len(payload["payload"]["session"]["summary_thought_trace"].get("candidate_signals", [])) <= 2
    assert "task_result_reads" in payload["payload"]["session"]
    assert "count" in payload["payload"]["session"]["task_result_reads"]
    assert payload["payload"]["session"]["chronological_trace_outline"] == {
        "omitted": True,
        "reason": "process_summary_default_uses_trace_drilldown_for_ordered_outline",
        "drilldown": (
            f"./repo-python kernel.py --process-trace "
            f"{payload['payload']['session']['session_id']}"
        ),
    }
    assert "audit_summary" in payload["payload"]
    assert payload["payload"]["output_economy"]["profile"] == "compact_owner_route"
    assert payload["payload"]["output_economy"]["default_target_bytes"] == 16_000
    assert payload["payload"]["output_economy"]["raw_bodies_omitted"] is True
    assert "session.spans" in payload["payload"]["output_economy"]["omitted_fields"]
    assert "session.chronological_trace_outline.rows" in payload["payload"]["output_economy"]["omitted_fields"]
    assert "spans" not in payload["payload"]["session"]
    assert "turns" not in payload["payload"]["session"]
    assert "findings" not in payload["payload"]["audit_summary"]
    assert len(summary_result.stdout.encode()) <= 16_000
    assert len(summary_result.stdout) < len(trace_result.stdout) + len(audit_result.stdout)
    assert tape_result.stdout.startswith("trace ")
    assert "\n000" in tape_result.stdout
    tape_lines = tape_result.stdout.splitlines()[1:]
    assert any("|ok" in line or " ok " in line for line in tape_lines)
    assert len(tape_result.stdout.encode()) <= 3600


def test_kernel_route_process_bottlenecks_shape() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-bottlenecks"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_bottlenecks"
    assert payload["schema_version"] == "process_bottlenecks_v1"
    assert payload["query"]["force_live"] is False
    source_mode = payload["source_freshness"]["mode"]
    assert source_mode in {
        "cached_summary",
        "deferred_missing_read_model",
        "speedboard_embedded_summary",
        "live_in_memory",
    }
    if source_mode == "deferred_missing_read_model":
        assert payload["source_freshness"]["status"] == "missing_read_model"
        assert payload["summary"]["ranking_status"] == "unavailable_missing_read_model"
        assert payload["decision_authority"]["safe_first_command"].endswith(
            "build_agent_execution_trace.py --cached-summary --limit 6"
        )
        assert (
            payload["payload"]["summary"]["source"]
            == "missing_process_bottleneck_read_model"
        )
    assert isinstance(payload["payload"]["top_bottlenecks"], list)
    assert isinstance(payload["payload"]["top_output_producers"], list)
    output_economy = payload["payload"]["output_economy"]
    assert output_economy["profile"] in {
        "compact_owner_status",
        "compact_missing_read_model_status",
    }
    if output_economy["profile"] == "compact_owner_status":
        assert output_economy["target_bytes"] == 22_000
        assert output_economy["row_limits"] == {
            "top_bottlenecks": 4,
            "top_output_producers": 2,
            "context_yield_rows": 2,
            "examples_per_bottleneck": 1,
        }
        assert len(payload["payload"]["top_bottlenecks"]) <= 4
        assert len(payload["payload"]["top_output_producers"]) <= 2
    if payload["payload"]["top_bottlenecks"]:
        assert "example_spans" in payload["payload"]["top_bottlenecks"][0]
        assert "repair_hints" in payload["payload"]["top_bottlenecks"][0]
        for row in payload["payload"]["top_bottlenecks"]:
            assert len(row.get("example_spans") or []) <= 1
    context_yield = payload["payload"]["context_yield_attribution"]
    assert context_yield["output_profile"] == "compact_context_yield_status"
    assert context_yield["rows_returned"] <= 2
    assert context_yield["rows_available"] >= context_yield["rows_returned"]
    assert "./repo-python kernel.py --process-audit" in context_yield["full_payload_routes"]
    for row in context_yield["rows"]:
        assert "example_count" in row
        assert "actionable_active_bytes" in row
        assert "actionable_span_count" in row
        assert "omission_receipt" not in row
        assert row.get("examples") in (None, [])
    assert len(result.stdout.encode()) <= 22_000


def test_process_bottlenecks_action_kind_filter_compacts_to_requested_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "repo_tool_command",
                        "count": 10,
                        "p95_ms": 30_000,
                        "example_spans": [{"normalized_command": "task ledger rebuild"}],
                        "repair_hints": [{"hint_id": "task_ledger_status"}],
                    },
                    {
                        "action_kind": "bash_cat",
                        "count": 8,
                        "p95_ms": 8_000,
                        "example_spans": [{"normalized_command": "git status chain"}],
                        "by_kernel_flag": [
                            {"kernel_flag": "--one", "count": 8},
                            {"kernel_flag": "--two", "count": 7},
                            {"kernel_flag": "--three", "count": 6},
                            {"kernel_flag": "--four", "count": 5},
                        ],
                        "repair_hints": [
                            {
                                "hint_id": "replace_git_shell_chain_with_state_snapshot",
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action git_state_shell_chain"
                                ),
                            }
                        ],
                    },
                ],
                "top_output_producers": [
                    {"action_kind": "repo_tool_command", "span_count": 4},
                    {"action_kind": "bash_cat", "span_count": 3},
                ],
                "context_yield_attribution": {
                    "rows": [
                        {"motif": "raw_body_before_selection", "active_bytes": 2_000_000},
                        {"motif": "tool_result_carryover", "active_bytes": 100_000},
                    ]
                },
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["bash_cat"])

    assert payload["query"]["action_kinds"] == ["bash_cat"]
    assert [row["action_kind"] for row in payload["payload"]["top_bottlenecks"]] == ["bash_cat"]
    assert [row["action_kind"] for row in payload["payload"]["top_output_producers"]] == ["bash_cat"]
    action_filter = payload["payload"]["action_kind_filter"]
    assert action_filter["requested"] == ["bash_cat"]
    assert action_filter["matched"] == ["bash_cat"]
    assert action_filter["filtered_top_bottleneck_count"] == 1
    assert payload["payload"]["top_bottlenecks"][0]["example_spans"] == []
    assert [
        row["kernel_flag"]
        for row in payload["payload"]["top_bottlenecks"][0]["by_kernel_flag"]
    ] == ["--one", "--two", "--three"]
    assert payload["payload"]["context_yield_attribution"]["rows_returned"] == 0
    output_economy = payload["payload"]["output_economy"]
    assert output_economy["target_bytes"] == 12_000
    assert output_economy["row_limits"]["context_yield_rows"] == 0
    assert output_economy["row_limits"]["examples_per_bottleneck"] == 0
    assert payload["source_freshness"]["cache_check_command"].endswith(
        "--cached-summary --limit 6 --action-kind bash_cat"
    )
    assert payload["decision_authority"]["cache_check_command"].endswith(
        "--cached-summary --limit 6 --action-kind bash_cat"
    )
    assert payload["next"][0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py --action git_state_shell_chain"
    )


def test_process_bottlenecks_action_kind_filter_promotes_template_repair_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "bash_grep",
                        "count": 12,
                        "example_spans": [{"normalized_command": "grep -r term state codex"}],
                        "repair_hints": [
                            {
                                "hint_id": "replace_raw_search_scan_with_owner_route",
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action bash_grep --scope <term-or-root>"
                                ),
                            }
                        ],
                    }
                ],
                "top_output_producers": [{"action_kind": "bash_grep", "span_count": 4}],
                "context_yield_attribution": {
                    "rows": [{"motif": "raw_body_before_selection", "active_bytes": 2_000_000}]
                },
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["bash_grep"])

    assert payload["next"][0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action bash_grep --scope <term-or-root>"
    )
    assert "replace_raw_search_scan_with_owner_route" in payload["next"][0]["reason"]
    assert payload["payload"]["context_yield_attribution"]["rows_returned"] == 0


def test_process_bottlenecks_action_kind_filter_promotes_concrete_repair_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    concrete_next = (
        "./repo-python tools/meta/control/action_quote.py --action test_or_build_command "
        "--scope system/server/tests/test_agent_execution_trace.py"
    )

    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "test_or_build_command",
                        "count": 12,
                        "example_spans": [],
                        "repair_hints": [
                            {
                                "hint_id": "route_focused_validation_through_action_quote",
                                "concrete_preferred_next": concrete_next,
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action test_or_build_command --scope <path-or-node> "
                                    "--session-id <work-ledger-session>"
                                ),
                            }
                        ],
                    }
                ],
                "top_output_producers": [{"action_kind": "test_or_build_command", "span_count": 4}],
                "context_yield_attribution": {
                    "rows": [{"motif": "raw_body_before_selection", "active_bytes": 2_000_000}]
                },
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["test_or_build_command"])

    assert (
        payload["payload"]["top_bottlenecks"][0]["repair_hints"][0]["concrete_preferred_next"]
        == concrete_next
    )
    assert payload["next"][0]["command"] == concrete_next
    assert "route_focused_validation_through_action_quote" in payload["next"][0]["reason"]


def test_process_bottlenecks_action_kind_filter_promotes_output_repair_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "bash_grep",
                        "count": 12,
                        "example_spans": [{"normalized_command": "grep -r term state codex"}],
                        "repair_hints": [],
                    }
                ],
                "top_output_producers": [
                    {
                        "action_kind": "bash_grep",
                        "span_count": 4,
                        "output_repair_hints": [
                            {
                                "hint_id": "replace_raw_search_scan_with_owner_route",
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action bash_grep --scope <term-or-root>"
                                ),
                            }
                        ],
                    }
                ],
                "context_yield_attribution": {
                    "rows": [{"motif": "raw_body_before_selection", "active_bytes": 2_000_000}]
                },
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["bash_grep"])

    assert payload["payload"]["top_bottlenecks"][0]["repair_hints"] == []
    assert payload["payload"]["top_output_producers"][0]["repair_hints"][0]["hint_id"] == (
        "replace_raw_search_scan_with_owner_route"
    )
    assert payload["next"][0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action bash_grep --scope <term-or-root>"
    )
    assert "output producer" in payload["next"][0]["reason"]
    assert payload["payload"]["context_yield_attribution"]["rows_returned"] == 0


def test_process_bottlenecks_prefers_host_find_repair_hint() -> None:
    host_hint = {
        "hint_id": "replace_host_find_scan_with_host_filesystem_quote",
        "preferred_next": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action bash_find --scope <host-path-or-term>"
        ),
        "owner_surface": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action host_filesystem_discovery --scope <host-path-or-term>"
        ),
    }
    generic_hint = {
        "hint_id": "replace_find_scan_with_rg_files_or_option_surface",
        "preferred_next": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action bash_find --scope <term-or-root>"
        ),
    }

    compact = process_bottlenecks_status._compact_process_output_producers(
        [
            {
                "action_kind": "bash_find",
                "span_count": 12,
                "repair_hints": [generic_hint, host_hint],
            }
        ],
        limit=1,
    )

    assert compact[0]["repair_hints"] == [host_hint]


def test_process_summary_compacts_kernel_flag_bottleneck_rows() -> None:
    compact = trace_lib._summary_compact_process_bottlenecks(
        {
            "kernel_command": {
                "count": 3,
                "total_duration_ms": 6000,
                "optimization_priority_score": 100,
                "by_kernel_flag": [
                    {
                        "kernel_flag": "--process-bottlenecks",
                        "count": 2,
                        "p95_ms": 3000,
                        "total_duration_ms": 5000,
                        "slow_count": 1,
                        "max_output_bytes": 9000,
                    },
                    {
                        "kernel_flag": "--session-diagnostics",
                        "count": 1,
                        "p95_ms": 2000,
                        "total_duration_ms": 1000,
                        "slow_count": 0,
                    },
                    {
                        "kernel_flag": "--entry",
                        "count": 1,
                        "p95_ms": 1000,
                        "total_duration_ms": 1000,
                        "slow_count": 0,
                    },
                ],
            }
        },
        limit=1,
        example_limit=0,
    )

    row = compact["kernel_command"]
    assert "by_kernel_flag" not in row
    assert row["by_kernel_flag_count"] == 3
    assert row["by_kernel_flag_omitted"] == 1
    assert row["by_kernel_flag_top"] == [
        {
            "kernel_flag": "--process-bottlenecks",
            "count": 2,
            "p95_ms": 3000,
            "total_duration_ms": 5000,
            "slow_count": 1,
        },
        {
            "kernel_flag": "--session-diagnostics",
            "count": 1,
            "p95_ms": 2000,
            "total_duration_ms": 1000,
            "slow_count": 0,
        },
    ]


def test_process_bottlenecks_action_kind_filter_derives_kernel_flag_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "kernel_command",
                        "count": 86,
                        "p95_ms": 30_140,
                        "example_spans": [],
                        "repair_hints": [],
                        "by_kernel_flag": [
                            {"kernel_flag": "--session-diagnostics", "count": 86},
                            {"kernel_flag": "--process-bottlenecks", "count": 28},
                        ],
                    }
                ],
                "top_output_producers": [{"action_kind": "kernel_command", "span_count": 86}],
                "context_yield_attribution": {
                    "rows": [{"motif": "raw_body_before_selection", "active_bytes": 2_000_000}]
                },
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["kernel_command"])

    hints = payload["payload"]["top_bottlenecks"][0]["repair_hints"]
    assert hints[0]["hint_id"] == "route_session_diagnostics_through_command_surface"
    assert hints[0]["preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action command_surface_inventory --scope session-diagnostics"
    )
    assert payload["next"][0]["command"] == hints[0]["preferred_next"]


def test_process_bottlenecks_action_kind_filter_derives_generic_kernel_flag_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "kernel_command",
                        "count": 86,
                        "p95_ms": 30_140,
                        "example_spans": [],
                        "repair_hints": [],
                        "by_kernel_flag": [
                            {"kernel_flag": "--agent-operating-packet", "count": 2},
                            {"kernel_flag": "--route-refresh", "count": 1},
                        ],
                    }
                ],
                "top_output_producers": [{"action_kind": "kernel_command", "span_count": 86}],
                "context_yield_attribution": {
                    "rows": [{"motif": "raw_body_before_selection", "active_bytes": 2_000_000}]
                },
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["kernel_command"])

    hints = payload["payload"]["top_bottlenecks"][0]["repair_hints"]
    assert hints[0]["hint_id"] == "route_kernel_flag_through_command_surface"
    assert hints[0]["kernel_flag"] == "--agent-operating-packet"
    assert hints[0]["concrete_preferred_next"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action kernel_command --scope agent-operating-packet"
    )
    assert payload["next"][0]["command"] == hints[0]["concrete_preferred_next"]


def test_process_bottlenecks_bottleneck_rows_prioritize_raw_search_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "bash_grep",
                        "count": 34,
                        "p95_ms": 64_540,
                        "example_spans": [],
                        "repair_hints": [
                            {
                                "hint_id": "replace_python_module_tail_with_compact_cli_mode",
                                "preferred_next": "Use a compact module mode.",
                            },
                            {
                                "hint_id": "replace_raw_search_scan_with_owner_route",
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action bash_grep --scope <term-or-root>"
                                ),
                                "owner_surface": (
                                    "./repo-python kernel.py "
                                    "--artifact-discovery-inventory <term-or-root>"
                                ),
                            },
                        ],
                    }
                ],
                "top_output_producers": [],
                "context_yield_attribution": {"rows": []},
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["bash_grep"])

    hints = payload["payload"]["top_bottlenecks"][0]["repair_hints"]
    assert hints[0]["hint_id"] == "replace_raw_search_scan_with_owner_route"
    assert payload["next"][0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action bash_grep --scope <term-or-root>"
    )


def test_process_bottlenecks_output_producer_inherits_kernel_flag_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "kernel_command",
                        "count": 86,
                        "p95_ms": 30_140,
                        "example_spans": [],
                        "repair_hints": [],
                        "by_kernel_flag": [
                            {"kernel_flag": "--session-diagnostics", "count": 86},
                        ],
                    }
                ],
                "top_output_producers": [
                    {
                        "action_kind": "kernel_command",
                        "span_count": 86,
                        "total_output_bytes": 1_600_000,
                    }
                ],
                "context_yield_attribution": {"rows": []},
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet()

    output_hints = payload["payload"]["top_output_producers"][0]["repair_hints"]
    assert output_hints == [
        {
            "hint_id": "route_session_diagnostics_through_command_surface",
            "preferred_next": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action command_surface_inventory --scope session-diagnostics"
            ),
            "owner_surface": (
                "./repo-python kernel.py --session-diagnostics "
                "--lens all --last 10 --store both --json --diagnostics-summary"
            ),
        }
    ]


def test_process_bottlenecks_output_producer_prefers_specific_bash_other_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_process_build(**_: object) -> dict:
        return {
            "summary": {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "bash_other",
                        "count": 86,
                        "p95_ms": 4_200,
                        "example_spans": [],
                        "repair_hints": [
                            {
                                "hint_id": "replace_inline_python_data_probe_with_owner_tool",
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action process_bottleneck_triage --action-kind bash_other"
                                ),
                            }
                        ],
                    }
                ],
                "top_output_producers": [
                    {
                        "action_kind": "bash_other",
                        "span_count": 86,
                        "total_output_bytes": 1_600_000,
                        "output_repair_hints": [
                            {
                                "hint_id": "route_unclassified_bash_output_through_action_quote",
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action bash_other --scope <path-or-owner>"
                                ),
                            }
                        ],
                        "repair_hints": [
                            {
                                "hint_id": "replace_inline_python_data_probe_with_owner_tool",
                                "preferred_next": (
                                    "./repo-python tools/meta/control/action_quote.py "
                                    "--action process_bottleneck_triage --action-kind bash_other"
                                ),
                            }
                        ],
                    }
                ],
                "context_yield_attribution": {"rows": []},
            }
        }

    monkeypatch.setattr(navigate, "_process_build", fake_process_build)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(
        force_live=True,
        action_kinds=["bash_other"],
    )

    output_hints = payload["payload"]["top_output_producers"][0]["repair_hints"]
    assert output_hints[0]["hint_id"] == "replace_inline_python_data_probe_with_owner_tool"
    assert payload["next"][0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action process_bottleneck_triage --action-kind bash_other"
    )


def test_process_bottlenecks_kernel_flag_hint_precedes_generic_kernel_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_summary(**_: object) -> tuple[dict, dict]:
        return (
            {
                "kind": "agent_execution_trace_summary",
                "summary": {"session_count": 4, "window": {"session_limit": 20}},
                "top_bottlenecks": [
                    {
                        "action_kind": "kernel_command",
                        "count": 86,
                        "p95_ms": 30_140,
                        "example_spans": [],
                        "repair_hints": [
                            {
                                "hint_id": "replace_kernel_output_limiter_with_compact_mode",
                                "preferred_next": "Use a compact kernel mode.",
                            }
                        ],
                        "by_kernel_flag": [
                            {"kernel_flag": "--session-diagnostics", "count": 86},
                        ],
                    }
                ],
                "top_output_producers": [{"action_kind": "kernel_command", "span_count": 86}],
                "context_yield_attribution": {"rows": []},
            },
            {"mode": "cached_summary", "status": "fresh"},
        )

    monkeypatch.setattr(navigate, "_load_process_bottleneck_summary_cache", fake_load_summary)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(action_kinds=["kernel_command"])

    hints = payload["payload"]["top_bottlenecks"][0]["repair_hints"]
    assert hints[0]["hint_id"] == "route_session_diagnostics_through_command_surface"
    assert payload["next"][0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action command_surface_inventory --scope session-diagnostics"
    )


def test_process_bottleneck_next_commands_start_with_top_context_route() -> None:
    context_yield = {
        "rows": [
            {
                "motif": "raw_body_before_selection",
                "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                "existing_route": "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
                "steering": {
                    "preferred_quote_route": (
                        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
                    ),
                    "pre_action_card": {
                        "first_route": (
                            "./repo-python tools/meta/control/action_quote.py "
                            "--action bash_grep --scope <term-or-root>"
                        ),
                    },
                },
            }
        ]
    }

    next_commands = navigate._process_bottleneck_next_commands(context_yield)

    assert next_commands[0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
    )
    assert "raw_body_before_selection" in next_commands[0]["reason"]
    assert not next_commands[0]["command"].startswith("{")
    assert next_commands[1]["command"] == trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE
    assert next_commands[2]["command"] == "./repo-python kernel.py --process-audit"
    assert next_commands[3]["command"] == "./repo-python kernel.py --process-bottlenecks --force"


def test_context_yield_next_commands_use_concrete_scope_hint() -> None:
    upstream_steering = trace_lib._context_yield_steering(
        motif="raw_body_before_selection",
        status_counts={"governed_route_available_but_not_used": 1},
        meta={"existing_route": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE},
        raw_row={
            "examples": [
                {
                    "governance_status": "governed_route_available_but_not_used",
                    "target_paths": ["system/lib/kernel/commands/navigate.py"],
                }
            ],
            "governance_status_tag_counts": {},
            "governance_status_action_counts": {
                "governed_route_available_but_not_used": {"bash_grep": 1}
            },
            "governance_status_target_counts": {},
        },
    )
    assert upstream_steering["concrete_preferred_quote_route"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep "
        "--scope system/lib/kernel/commands/navigate.py"
    )
    upstream_from_counts = trace_lib._context_yield_steering(
        motif="raw_body_before_selection",
        status_counts={"governed_route_available_but_not_used": 2},
        meta={"existing_route": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE},
        raw_row={
            "examples": [],
            "governance_status_tag_counts": {},
            "governance_status_action_counts": {
                "governed_route_available_but_not_used": {"bash_grep": 2}
            },
            "governance_status_target_counts": {},
            "governance_status_path_counts": {
                "governed_route_available_but_not_used": {
                    "system/lib/kernel/commands/navigate.py": 2
                }
            },
        },
    )
    assert upstream_from_counts["scope_hint"] == "system/lib/kernel/commands/navigate.py"
    compact_from_upstream = navigate._compact_context_yield_attribution(
        {
            "rows": [
                {
                    "motif": "raw_body_before_selection",
                    "active_bytes": 2_000_000,
                    "actionable_active_bytes": 2_000_000,
                    "span_count": 24,
                    "actionable_span_count": 24,
                    "next_wave_score": "high",
                    "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                    "steering": upstream_from_counts,
                    "examples": [],
                }
            ]
        },
        row_limit=1,
        example_limit=0,
    )
    assert compact_from_upstream["rows"][0]["steering"]["concrete_replacement_route"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action artifact_discovery_inventory --scope system/lib/kernel/commands/navigate.py"
    )

    context_yield = {
        "rows": [
            {
                "motif": "raw_body_before_selection",
                "active_bytes": 2_000_000,
                "actionable_active_bytes": 2_000_000,
                "span_count": 24,
                "actionable_span_count": 24,
                "next_wave_score": "high",
                "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                "steering": {
                    "replacement_route": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                    "preferred_quote_route": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action bash_grep --scope <term-or-root>"
                    ),
                    "pre_action_card": {
                        "first_route": (
                            "./repo-python tools/meta/control/action_quote.py "
                            "--action bash_grep --scope <term-or-root>"
                        ),
                    },
                },
                "examples": [
                    {
                        "action_kind": "bash_grep",
                        "governance_status": "governed_route_available_but_not_used",
                        "target_paths": ["system/lib/kernel/commands/navigate.py"],
                        "normalized_command": "rg process_bottleneck system/lib/kernel/commands/navigate.py",
                    }
                ],
            }
        ]
    }

    compact = navigate._compact_context_yield_attribution(
        context_yield,
        row_limit=1,
        example_limit=0,
    )
    row = compact["rows"][0]
    steering = row["steering"]

    assert row.get("examples") in (None, [])
    assert steering["scope_hint"] == "system/lib/kernel/commands/navigate.py"
    assert steering["concrete_preferred_quote_route"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep "
        "--scope system/lib/kernel/commands/navigate.py"
    )
    assert steering["concrete_replacement_route"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action artifact_discovery_inventory --scope system/lib/kernel/commands/navigate.py"
    )

    next_commands = navigate._process_bottleneck_next_commands(compact)

    assert next_commands[0]["command"] == steering["concrete_preferred_quote_route"]
    assert next_commands[1]["command"] == steering["concrete_replacement_route"]


def test_process_bottleneck_next_commands_promote_concrete_top_repair() -> None:
    context_yield = {
        "rows": [
            {
                "motif": "raw_body_before_selection",
                "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                "steering": {
                    "preferred_quote_route": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action bash_grep --scope <term-or-root>"
                    ),
                },
            }
        ]
    }
    top_bottlenecks = [
        {
            "action_kind": "test_or_build_command",
            "repair_hints": [
                {
                    "hint_id": "route_focused_validation_through_action_quote",
                    "concrete_preferred_next": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action test_or_build_command --scope system/server/tests/test_agent_execution_trace.py"
                    ),
                    "preferred_next": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action test_or_build_command --scope <path-or-node>"
                    ),
                }
            ],
        },
        {
            "action_kind": "kernel_command",
            "repair_hints": [
                {
                    "hint_id": "replace_process_diagnostic_limiter_with_status_packet",
                    "preferred_next": "./repo-python kernel.py --process-bottlenecks",
                }
            ],
        },
        {
            "action_kind": "bash_cat",
            "repair_hints": [
                {
                    "hint_id": "replace_git_shell_chain_with_state_snapshot",
                    "preferred_next": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action git_state_shell_chain"
                    ),
                }
            ],
        },
    ]

    next_commands = navigate._process_bottleneck_next_commands(
        context_yield,
        top_bottlenecks=top_bottlenecks,
    )

    assert next_commands[0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action test_or_build_command --scope system/server/tests/test_agent_execution_trace.py"
    )
    assert "route_focused_validation_through_action_quote" in next_commands[0]["reason"]
    assert next_commands[1]["command"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
    )
    assert next_commands[2]["command"] == (
        trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE
    )


def test_process_bottleneck_next_commands_also_promote_output_repair() -> None:
    top_bottlenecks = [
        {
            "action_kind": "kernel_command",
            "repair_hints": [
                {
                    "hint_id": "route_session_diagnostics_through_command_surface",
                    "preferred_next": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action command_surface_inventory --scope session-diagnostics"
                    ),
                }
            ],
        }
    ]
    top_output_producers = [
        {
            "action_kind": "bash_other",
            "repair_hints": [
                {
                    "hint_id": "replace_git_shell_chain_with_state_snapshot",
                    "preferred_next": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action git_state_shell_chain"
                    ),
                }
            ],
        }
    ]

    next_commands = navigate._process_bottleneck_next_commands(
        {},
        top_bottlenecks=top_bottlenecks,
        top_output_producers=top_output_producers,
    )

    assert next_commands[0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py "
        "--action command_surface_inventory --scope session-diagnostics"
    )
    assert "top process bottleneck" in next_commands[0]["reason"]
    assert next_commands[1]["command"] == (
        "./repo-python tools/meta/control/action_quote.py --action git_state_shell_chain"
    )
    assert "top process output producer" in next_commands[1]["reason"]


def test_process_bottleneck_next_commands_defer_status_probe_repair() -> None:
    context_yield = {
        "rows": [
            {
                "motif": "raw_body_before_selection",
                "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                "steering": {
                    "preferred_quote_route": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action bash_grep --scope <term-or-root>"
                    ),
                },
            }
        ]
    }
    top_bottlenecks = [
        {
            "action_kind": "repo_tool_command",
            "repair_hints": [
                {
                    "hint_id": "use_task_ledger_rebuild_check_before_full_rebuild",
                    "preferred_next": (
                        "./repo-python tools/meta/factory/task_ledger_apply.py "
                        "rebuild --status-only --quiet-progress"
                    ),
                    "replacement_commands": [
                        (
                            "./repo-python tools/meta/factory/task_ledger_apply.py "
                            "rebuild --status-only --quiet-progress"
                        ),
                        (
                            "./repo-python tools/meta/factory/task_ledger_apply.py "
                            "drain-deferred-rebuilds --limit 1 --quiet-progress"
                        ),
                    ],
                },
                {
                    "hint_id": "append_task_ledger_capture_before_projection_rebuild",
                    "preferred_next": (
                        "./repo-python tools/meta/factory/task_ledger_apply.py "
                        "quick-capture --projection-rebuild-policy off ..."
                    ),
                }
            ],
        }
    ]

    next_commands = navigate._process_bottleneck_next_commands(
        context_yield,
        top_bottlenecks=top_bottlenecks,
    )

    assert next_commands[0]["command"] == (
        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
    )
    assert next_commands[1]["command"] == (
        trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE
    )
    assert next_commands[2]["command"] == (
        "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress"
    )
    assert "status/projection guard-rail" in next_commands[2]["reason"]
    assert all("..." not in row["command"] for row in next_commands)


def test_process_bottleneck_next_commands_keep_one_status_probe_after_non_probe() -> None:
    concrete_next = (
        "./repo-python tools/meta/control/action_quote.py --action test_or_build_command "
        "--scope tests/test_task_ledger_events_projection.py"
    )
    top_bottlenecks = [
        {
            "action_kind": "test_or_build_command",
            "repair_hints": [
                {
                    "hint_id": "route_focused_validation_through_action_quote",
                    "concrete_preferred_next": concrete_next,
                    "preferred_next": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action test_or_build_command --scope <path-or-node>"
                    ),
                }
            ],
        },
        {
            "action_kind": "repo_tool_command",
            "repair_hints": [
                {
                    "hint_id": "use_task_ledger_rebuild_check_before_full_rebuild",
                    "preferred_next": (
                        "./repo-python tools/meta/factory/task_ledger_apply.py "
                        "rebuild --status-only --quiet-progress"
                    ),
                    "replacement_commands": [
                        (
                            "./repo-python tools/meta/factory/task_ledger_apply.py "
                            "drain-deferred-rebuilds --limit 1 --quiet-progress"
                        )
                    ],
                }
            ],
        },
    ]

    next_commands = navigate._process_bottleneck_next_commands(
        {},
        top_bottlenecks=top_bottlenecks,
    )

    assert next_commands[0]["command"] == concrete_next
    assert next_commands[1]["command"] == (
        "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress"
    )
    assert "status/projection guard-rail" in next_commands[1]["reason"]
    assert all(
        "drain-deferred-rebuilds" not in row["command"]
        for row in next_commands
    )


def test_process_bottleneck_live_build_skips_output_previews(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = {}

    def fake_build_agent_execution_trace(**kwargs):
        observed.update(kwargs)
        return {"summary": {"summary": {"session_count": 0}}}

    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)
    monkeypatch.setattr(navigate, "build_agent_execution_trace", fake_build_agent_execution_trace)

    payload = navigate._process_build(since_ts="2026-01-01T00:00:00+00:00", session_limit=6)

    assert payload["summary"]["summary"]["session_count"] == 0
    assert observed["since_ts"] == "2026-01-01T00:00:00+00:00"
    assert observed["session_limit"] == 6
    assert observed["include_output_previews"] is False
    assert observed["include_context_yield_attribution"] is True
    assert observed["aggregate_action_kinds"] is None
    assert observed["parse_codex_output_payloads"] is True
    assert observed["build_profile"] == "full"


def test_process_bottlenecks_force_uses_fast_ranking_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = {}

    def fake_process_build(**kwargs: object) -> dict:
        observed.update(kwargs)
        return {
            "summary": {
                "kind": "agent_execution_trace_summary",
                "summary": {
                    "session_count": 4,
                    "window": {"session_limit": 20},
                    "codex_output_payload_mode": "raw_payload_fast_metrics",
                    "build_profile": "bottleneck_rankings",
                },
                "top_bottlenecks": [
                    {
                        "action_kind": "kernel_command",
                        "count": 3,
                        "p95_ms": 15_000,
                        "example_spans": [],
                        "repair_hints": [],
                    }
                ],
                "top_output_producers": [],
                "context_yield_attribution": {
                    "kind": "context_yield_attribution_packet",
                    "schema_version": "context_yield_attribution_packet_v0",
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "summary": {
                        "session_count": 4,
                        "span_count": 20,
                        "motif_count": 0,
                        "computation_status": "skipped",
                        "skip_reason": (
                            "caller_requested_bottleneck_rankings_without_context_yield_rows"
                        ),
                    },
                    "rows": [],
                },
            }
        }

    monkeypatch.setattr(navigate, "_process_build", fake_process_build)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(force_live=True)

    assert observed["include_context_yield_attribution"] is False
    assert observed["aggregate_action_kinds"] is None
    assert observed["parse_codex_output_payloads"] is False
    assert observed["build_profile"] == "bottleneck_rankings"
    assert payload["payload"]["context_yield_attribution"]["rows_returned"] == 0
    assert payload["payload"]["context_yield_attribution"]["summary"]["computation_status"] == "skipped"
    assert payload["payload"]["output_economy"]["profile"] == "force_live_authoritative_rankings_fast_metrics"
    assert payload["payload"]["output_economy"]["row_limits"]["context_yield_rows"] == 0


def test_kernel_route_process_bottlenecks_force_compacts_owner_packet() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-bottlenecks", "--force"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_bottlenecks"
    assert payload["query"]["force_live"] is True
    output_economy = payload["payload"]["output_economy"]
    assert output_economy["profile"] == "force_live_authoritative_rankings_fast_metrics"
    assert output_economy["target_bytes"] == 30_000
    assert output_economy["row_limits"] == {
        "top_bottlenecks": 6,
        "top_output_producers": 5,
        "context_yield_rows": 0,
        "examples_per_bottleneck": 1,
    }
    assert "raw top-bottleneck example rows" in output_economy["omitted_fields"]
    assert "raw top output-producer rows" in output_economy["omitted_fields"]
    assert len(payload["payload"]["top_bottlenecks"]) <= 6
    assert len(payload["payload"]["top_output_producers"]) <= 5
    for row in payload["payload"]["top_bottlenecks"]:
        assert len(row.get("example_spans") or []) <= 1
    context_yield = payload["payload"]["context_yield_attribution"]
    assert context_yield["output_profile"] == "compact_context_yield_status"
    assert context_yield["rows_returned"] == 0
    assert context_yield["summary"]["computation_status"] == "skipped"
    assert context_yield["summary"]["skip_reason"] == (
        "caller_requested_bottleneck_rankings_without_context_yield_rows"
    )
    assert len(result.stdout.encode()) < 30_000


def test_process_bottlenecks_filtered_force_skips_context_yield_attribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = {}

    def fake_process_build(**kwargs: object) -> dict:
        observed.update(kwargs)
        return {
            "summary": {
                "kind": "agent_execution_trace_summary",
                "summary": {
                    "session_count": 4,
                    "window": {"session_limit": 20},
                    "codex_output_payload_mode": "raw_payload_fast_metrics",
                },
                "top_bottlenecks": [
                    {
                        "action_kind": "repo_tool_command",
                        "count": 12,
                        "p95_ms": 12_000,
                        "example_spans": [],
                        "repair_hints": [],
                    }
                ],
                "top_output_producers": [],
                "context_yield_attribution": {
                    "kind": "context_yield_attribution_packet",
                    "schema_version": "context_yield_attribution_packet_v0",
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "summary": {
                        "session_count": 4,
                        "span_count": 20,
                        "motif_count": 0,
                        "computation_status": "skipped",
                        "skip_reason": (
                            "caller_requested_bottleneck_rankings_without_context_yield_rows"
                        ),
                    },
                    "rows": [],
                },
            }
        }

    monkeypatch.setattr(navigate, "_process_build", fake_process_build)
    monkeypatch.setattr(navigate.state, "REPO_ROOT", REPO_ROOT, raising=False)

    payload = navigate._build_process_bottlenecks_packet(
        force_live=True,
        action_kinds=["repo_tool_command"],
    )

    assert observed["include_context_yield_attribution"] is False
    assert observed["aggregate_action_kinds"] == ["repo_tool_command"]
    assert observed["parse_codex_output_payloads"] is False
    assert observed["build_profile"] == "bottleneck_rankings"
    assert payload["payload"]["context_yield_attribution"]["rows_returned"] == 0
    assert payload["payload"]["context_yield_attribution"]["summary"]["computation_status"] == "skipped"
    assert payload["payload"]["output_economy"]["row_limits"]["context_yield_rows"] == 0
    assert payload["payload"]["summary"]["codex_output_payload_mode"] == "raw_payload_fast_metrics"


def test_process_output_producer_compaction_keeps_first_repair_hint() -> None:
    rows = [
        {
            "action_kind": "bash_grep",
            "span_count": 3,
            "total_output_bytes": 120_000,
            "max_output_bytes": 90_000,
            "p95_output_bytes": 85_000,
            "example_spans": [
                {"normalized_command": "rg -n thing system codex state"},
            ],
            "repair_hints": [
                {
                    "hint_id": "replace_polling_with_status_surface",
                    "owner_surface": "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>",
                },
                {
                    "hint_id": "replace_raw_search_scan_with_owner_route",
                    "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                    "scope_narrowing": "Use rare object terms before inventory.",
                },
                {"hint_id": "second_hint_stays_behind_full_row"},
            ],
        }
    ]

    compact = navigate._compact_process_output_producers(rows)

    assert compact == [
        {
            "action_kind": "bash_grep",
            "span_count": 3,
            "total_output_bytes": 120_000,
            "max_output_bytes": 90_000,
            "p95_output_bytes": 85_000,
            "repair_hints": [
                {
                    "hint_id": "replace_raw_search_scan_with_owner_route",
                    "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                    "scope_narrowing": "Use rare object terms before inventory.",
                }
            ],
        }
    ]


def test_process_summary_compact_repair_hints_prioritize_concrete_owner_routes() -> None:
    compact = trace_lib._summary_compact_repair_hints(
        [
            {
                "hint_id": "replace_python_module_tail_with_compact_cli_mode",
                "preferred_next": "Use a compact module mode.",
            },
            {
                "hint_id": "replace_global_raw_diff_with_diff_review_context",
                "preferred_next": "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
            },
            {
                "hint_id": "replace_raw_search_scan_with_owner_route",
                "preferred_next": "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>",
                "owner_surface": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
            },
            {
                "hint_id": "replace_shell_limiter_with_compact_packet",
                "preferred_next": "Use a compact packet.",
            },
        ],
        limit=2,
    )

    assert [row["hint_id"] for row in compact] == [
        "replace_raw_search_scan_with_owner_route",
        "replace_global_raw_diff_with_diff_review_context",
    ]
    assert compact[0]["owner_surface"] == (
        trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE
    )


def test_process_output_producer_compaction_prefers_output_specific_hints() -> None:
    rows = [
        {
            "action_kind": "bash_other",
            "span_count": 6,
            "total_output_bytes": 160_000,
            "max_output_bytes": 95_000,
            "p95_output_bytes": 90_000,
            "repair_hints": [
                {
                    "hint_id": "replace_shell_limiter_with_compact_packet",
                    "preferred_next": "generic compact packet",
                }
            ],
            "output_repair_hints": [
                {
                    "hint_id": "replace_shell_limiter_with_compact_packet",
                    "preferred_next": "generic compact packet",
                },
                {
                    "hint_id": "replace_git_shell_chain_with_state_snapshot",
                    "preferred_next": (
                        "./repo-python tools/meta/control/action_quote.py "
                        "--action git_state_shell_chain"
                    ),
                    "owner_surface": (
                        "./repo-python tools/meta/control/git_state_snapshot.py "
                        "--scope <path> --path-limit 40 --recent-limit 3 "
                        "--skip-git-metadata-write-probe --compact"
                    ),
                },
            ],
        }
    ]

    compact = navigate._compact_process_output_producers(rows)

    assert compact[0]["repair_hints"] == [
        {
            "hint_id": "replace_git_shell_chain_with_state_snapshot",
            "preferred_next": (
                "./repo-python tools/meta/control/action_quote.py --action git_state_shell_chain"
            ),
            "owner_surface": (
                "./repo-python tools/meta/control/git_state_snapshot.py "
                "--scope <path> --path-limit 40 --recent-limit 3 "
                "--skip-git-metadata-write-probe --compact"
            ),
        }
    ]


def test_process_output_producer_compaction_uses_kernel_flag_hints() -> None:
    rows = [
        {
            "action_kind": "kernel_command",
            "span_count": 86,
            "total_output_bytes": 1_600_000,
            "max_output_bytes": 40_160,
            "p95_output_bytes": 40_159,
            "repair_hints": [
                {
                    "hint_id": "replace_inventory_limiter_with_cluster_or_card_band",
                    "preferred_next": (
                        "./repo-python kernel.py --option-surface <kind_id> "
                        "--band cluster_flag"
                    ),
                }
            ],
            "by_kernel_flag": [
                {
                    "kernel_flag": "--session-diagnostics",
                    "count": 86,
                    "p95_ms": 30_140,
                    "max_ms": 30_490,
                }
            ],
        }
    ]

    compact = navigate._compact_process_output_producers(rows)

    assert compact[0]["repair_hints"] == [
        {
            "hint_id": "route_session_diagnostics_through_command_surface",
            "preferred_next": (
                "./repo-python tools/meta/control/action_quote.py "
                "--action command_surface_inventory --scope session-diagnostics"
            ),
            "owner_surface": (
                "./repo-python kernel.py --session-diagnostics "
                "--lens all --last 10 --store both --json --diagnostics-summary"
            ),
        }
    ]


def test_context_yield_compaction_preserves_raw_discovery_steering_fields() -> None:
    compact = navigate._compact_context_yield_attribution(
        {
            "kind": "context_yield_attribution_packet",
            "schema_version": "context_yield_attribution_packet_v0",
            "rows": [
                {
                    "motif": "raw_body_before_selection",
                    "active_bytes": 100_000,
                    "actionable_active_bytes": 90_000,
                    "span_count": 4,
                    "actionable_span_count": 3,
                    "governance_status_counts": {
                        "governed_route_available_but_not_used": 3,
                    },
                    "steering": {
                        "replacement_route": trace_lib.ARTIFACT_DISCOVERY_OWNER_SURFACE,
                        "preferred_quote_route": "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>",
                        "quote_routes": [
                            "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>",
                            "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <term-or-root>",
                        ],
                        "scope_narrowing": "Use object-specific terms.",
                        "applies_to_status": "governed_route_available_but_not_used",
                        "applies_to_count": 3,
                    },
                }
            ],
        },
        row_limit=1,
        example_limit=0,
    )

    steering = compact["rows"][0]["steering"]
    assert steering["scope_narrowing"] == "Use object-specific terms."
    assert steering["preferred_quote_route"].endswith("--action bash_grep --scope <term-or-root>")
    assert steering["quote_routes"] == [
        "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>",
        "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <term-or-root>",
    ]


def test_context_yield_compaction_keeps_lower_row_routes_without_diagnostics() -> None:
    rows = [
        {
            "motif": "raw_body_before_selection",
            "active_bytes": 200_000 - index,
            "actionable_active_bytes": 100_000 - index,
            "span_count": 5,
            "actionable_span_count": 4,
            "steering": {
                "replacement_route": (
                    "./repo-python tools/meta/control/action_quote.py "
                    f"--action artifact_discovery_inventory --scope term-{index}"
                ),
                "preferred_quote_route": (
                    f"./repo-python tools/meta/control/action_quote.py --action bash_grep --scope term-{index}"
                ),
                "quote_routes": [
                    f"./repo-python tools/meta/control/action_quote.py --action bash_grep --scope term-{index}",
                ],
                "pre_action_card": {
                    "first_route": f"./repo-python tools/meta/control/action_quote.py --action bash_grep --scope term-{index}",
                    "scope_rule": "Use rare terms.",
                },
                "scope_narrowing": "Use object-specific terms.",
                "applies_to_status": "governed_route_available_but_not_used",
                "applies_to_count": 4,
                "accepted_case_guard": "Scoped low-output discovery remains accepted.",
                "command_shape_clusters": {
                    "status": "governed_route_available_but_not_used",
                    "tag_counts": {"raw_search_scan": 4},
                    "action_kind_counts": {"bash_grep": 4},
                },
            },
        }
        for index in range(2)
    ]

    compact = navigate._compact_context_yield_attribution(
        {
            "kind": "context_yield_attribution_packet",
            "schema_version": "context_yield_attribution_packet_v0",
            "rows": rows,
        },
        row_limit=2,
        example_limit=0,
    )

    first_steering = compact["rows"][0]["steering"]
    second_steering = compact["rows"][1]["steering"]
    assert "pre_action_card" in first_steering
    assert "command_shape_clusters" in first_steering
    assert second_steering["replacement_route"].endswith("term-1")
    assert second_steering["preferred_quote_route"].endswith("--scope term-1")
    assert second_steering["scope_narrowing"] == "Use object-specific terms."
    assert "pre_action_card" not in second_steering
    assert "accepted_case_guard" not in second_steering
    assert "command_shape_clusters" not in second_steering
    assert compact["steering_compaction"] == {
        "full_steering_rows": 1,
        "route_only_steering_rows": 1,
        "route_fields_preserved_on_all_rows": True,
    }


def test_kernel_route_process_trace_rejects_unknown() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-trace", "nonexistent_session_id_xyz"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.process_trace"
    assert "error" in payload
    assert "alternatives" in payload


def test_kernel_route_agent_wake_packet_shape() -> None:
    result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--agent-wake-packet",
            "--agent-wake-limit",
            "1",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=35,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.agent_wake_packet"
    assert payload["schema_version"] == "agent_wake_packet_v1"
    assert payload["payload"]["command_budget"]["replaces_commands"]
    assert payload["payload"]["phase"]["phase_id"]
    assert "view_graph_check" in payload["payload"]
    assert "raw_seed_projection_coverage" in payload["payload"]
    assert "work_ledger_overview" in payload["payload"]
    assert "workitem_backlog_health" in payload["payload"]
    assert "workitem_phase_freshness" in payload["payload"]
    assert "workitem_concurrency_attention" in payload["payload"]
    assert "workitem_subphase_runtime_attention" in payload["payload"]
    assert "workitem_strict_json_artifact_attention" in payload["payload"]
    assert payload["payload"]["workitem_backlog_health"]["recommended_next_workitem_ids"] is not None
    assert payload["payload"]["workitem_phase_freshness"]["freshness_status"] in {
        "current",
        "conflicting",
        "stale",
        "unknown",
    }
    assert payload["payload"]["workitem_concurrency_attention"]["safe_parallelism_status"] in {
        "safe",
        "watch",
        "blocked",
        "unknown",
    }
    assert payload["payload"]["workitem_subphase_runtime_attention"]["runtime_status"] in {
        "ready",
        "watch",
        "blocked",
    }
    assert "execution_menu_ids" in payload["payload"]["workitem_subphase_runtime_attention"]
    assert "workitem_execution_menu_count" in payload["summary"]
    assert "workitem_phase_freshness_status" in payload["summary"]
    assert "workitem_safe_parallelism_status" in payload["summary"]
    assert "workitem_subphase_runtime_status" in payload["summary"]
    assert "workitem_subphase_id" in payload["summary"]
    assert "workitem_active_claim_count" in payload["summary"]
    assert "workitem_claim_collision_count" in payload["summary"]
    assert "workitem_strict_json_status" in payload["summary"]
    assert "workitem_strict_json_checked_count" in payload["summary"]
    assert payload["payload"]["workitem_strict_json_artifact_attention"]["top_commands"]
    assert len(json.dumps(payload)) < 80_000


def test_agent_wake_projection_coverage_reads_materialized_summary(monkeypatch, tmp_path: Path) -> None:
    projection_dir = tmp_path / "codex/hologram/raw_seed_projection"
    projection_dir.mkdir(parents=True)
    (projection_dir / "summary.json").write_text(
        json.dumps(
            {
                "kind": "raw_seed_projection_coverage_summary",
                "schema_version": "raw_seed_projection_coverage_summary_v1",
                "generated_at": "2026-05-11T00:00:00Z",
                "summary": {"theme_count": 1, "gap_state_counts": {"covered": 1}},
                "top_themes": [
                    {
                        "theme_id": "theme_agent_execution_trace_visibility",
                        "gap_state": "covered",
                        "recommended_next_action": "nothing_to_refine",
                    }
                ],
                "top_gaps": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(navigate.state, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(
        navigate,
        "build_raw_seed_projection_coverage",
        lambda **_: pytest.fail("wake packet must not rebuild raw-seed projection coverage"),
    )

    packet, warnings = navigate._agent_wake_projection_coverage()

    assert warnings == []
    assert packet["status"] == "materialized"
    assert packet["summary"]["theme_count"] == 1
    assert packet["themes"][0]["theme_id"] == "theme_agent_execution_trace_visibility"


def test_kernel_route_phase_summary_modes_stay_bounded() -> None:
    default_result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--phase",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    default_payload = json.loads(default_result.stdout)

    assert default_payload["kind"] == "kernel.navigate.phase"
    assert default_payload["mode"] == "summary"
    assert default_payload["payload"]["view_profile"] == "phase_agent_control_packet_v0"
    assert default_payload["payload"]["source_payload_owner"]["primary_surface"].endswith("--full")
    assert default_payload["payload"]["view_owner"]["owner_id"] == "phase_agent_control_packet_v0"
    assert "--full" in default_payload["payload"]["full_payload_hint"]["command"]
    assert default_payload["payload"]["omitted_sections"]
    assert "phase_card" not in default_payload["payload"]
    assert len(json.dumps(default_payload)) < 12_000

    summary_result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--phase",
            "--summary",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    summary_payload = json.loads(summary_result.stdout)

    assert summary_payload["kind"] == "kernel.navigate.phase"
    assert summary_payload["mode"] == "summary"
    assert summary_payload["payload"]["view_profile"] == "phase_agent_control_packet_v0"
    assert summary_payload["payload"]["phase"]["phase_id"]
    assert "phase_card" not in summary_payload["payload"]
    assert "active_wave" in summary_payload["payload"]
    assert len(json.dumps(summary_payload)) < 12_000

    full_result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--phase",
            "--full",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    full_payload = json.loads(full_result.stdout)

    assert full_payload["kind"] == "kernel.navigate.phase"
    assert "mode" not in full_payload
    assert full_payload["payload"]["phase"]["phase_id"] == default_payload["payload"]["phase"]["phase_id"]
    assert "phase_card" in full_payload["payload"]
    assert "family" in full_payload["payload"]
    assert "derived_index" in full_payload["payload"]
    assert "active_synth" in full_payload["payload"]

    warnings_result = subprocess.run(
        [
            str(REPO_ROOT / "repo-python"),
            "kernel.py",
            "--phase",
            "--warnings-only",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    warnings_payload = json.loads(warnings_result.stdout)

    assert warnings_payload["kind"] == "kernel.navigate.phase"
    assert warnings_payload["mode"] == "warnings_only"
    assert "warning_count" in warnings_payload["payload"]
    assert "active_wave" not in warnings_payload["payload"]
    assert len(json.dumps(warnings_payload)) < 7_000
