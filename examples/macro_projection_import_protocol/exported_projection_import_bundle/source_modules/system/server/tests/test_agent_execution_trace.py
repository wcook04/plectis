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


def test_process_summary_missing_cache_points_to_writing_refresh(tmp_path: Path) -> None:
    _seed_rules(tmp_path)
    standard = tmp_path / "codex/standards/std_agent_execution_trace.json"
    standard.parent.mkdir(parents=True, exist_ok=True)
    standard.write_text("{}", encoding="utf-8")

    code, payload = build_process_summary_route_packet(
        repo_root=tmp_path,
        request="codex:latest",
    )

    assert code == 1
    assert payload["source_freshness"]["status"] == "missing_or_malformed_summary"
    assert payload["source_freshness"]["refresh_command"] == (
        "./repo-python tools/meta/factory/build_agent_execution_trace.py"
    )
    assert payload["next"][1]["command"] == (
        "./repo-python tools/meta/factory/build_agent_execution_trace.py"
    )
    assert "--summary" not in json.dumps(payload)


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


def test_process_trace_route_rejects_unknown_compactness_level(tmp_path: Path) -> None:
    code, payload = build_process_trace_route_packet(repo_root=tmp_path, trace_level="maximal")

    assert code == 2
    assert payload["available_levels"] == ["outline", "tape", "tape+diff", "audit", "raw"]


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
    wait_hint = result["audit"]["bottlenecks"]["exec_session_io"]["repair_hints"][0]
    assert wait_hint["hint_id"] == "inspect_preceding_exec_or_add_status_surface"
    assert wait_hint["preferred_next"] == (
        "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"
    )
    assert wait_hint["owner_surface"] == "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"
    assert "./repo-python kernel.py --process-trace <session_id>" in wait_hint["replacement_commands"]
    assert "raw task-output bodies" in wait_hint["privacy_boundary"]


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
    # Output-limited test/build and repo-tool pipelines should be attributed to
    # the primary command, not to the trailing grep/head/tail limiter.
    records += _claude_tool_use_pair(
        use_id="toolu_pytest_tail",
        tool_name="Bash",
        start=t0 + timedelta(seconds=44),
        end=t0 + timedelta(seconds=164),
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
        start=t0 + timedelta(seconds=165),
        end=t0 + timedelta(seconds=225),
        input_body={"command": "./repo-python tools/meta/factory/build_paper_module_index.py 2>&1 | grep -E \"modules|status\""},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_task_output_read",
        tool_name="Read",
        start=t0 + timedelta(seconds=226),
        end=t0 + timedelta(seconds=286),
        input_body={"file_path": "/private/tmp/claude-501/-Users-willcook-src-ai_workflow/session/tasks/b123.output"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_find_head",
        tool_name="Bash",
        start=t0 + timedelta(seconds=287),
        end=t0 + timedelta(seconds=332),
        input_body={"command": "find . -name '*.py' 2>/dev/null | head -20"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_recursive_grep",
        tool_name="Bash",
        start=t0 + timedelta(seconds=333),
        end=t0 + timedelta(seconds=378),
        input_body={"command": "grep -rli -E \"clob-endpoint|orderbook\" tools/ system/ 2>/dev/null | head -20"},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_background_poll",
        tool_name="Bash",
        start=t0 + timedelta(seconds=379),
        end=t0 + timedelta(seconds=499),
        input_body={
            "command": (
                "until grep -q -E \"(Test Files|Error:)\" "
                "/private/tmp/claude-501/-Users-willcook-src-ai_workflow/session/tasks/b456.output; "
                "do sleep 2; done"
            )
        },
    )
    records += _claude_tool_use_pair(
        use_id="toolu_doc_read",
        tool_name="Read",
        start=t0 + timedelta(seconds=500),
        end=t0 + timedelta(seconds=555),
        input_body={"file_path": str(tmp_path / "AGENTS.md")},
    )
    records += _claude_tool_use_pair(
        use_id="toolu_task_wait",
        tool_name="Task",
        start=t0 + timedelta(seconds=556),
        end=t0 + timedelta(seconds=686),
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
    assert audit["bottlenecks"]["bash_cat"]["count"] == 2
    assert audit["bottlenecks"]["bash_cat"]["p50_ms"] == 20000
    assert audit["bottlenecks"]["bash_cat"]["slow_count"] == 2
    assert audit["bottlenecks"]["bash_cat"]["example_spans"][0]["duration_ms"] == 30000
    assert audit["bottlenecks"]["bash_cat"]["example_spans"][0]["session_id"]
    cat_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["bash_cat"]["repair_hints"]}
    assert "replace_git_shell_chain_with_state_snapshot" in cat_hint_ids
    assert "replace_global_raw_diff_with_diff_review_context" in cat_hint_ids
    cat_hints = {
        row["hint_id"]: row for row in audit["bottlenecks"]["bash_cat"]["repair_hints"]
    }
    assert cat_hints["replace_git_shell_chain_with_state_snapshot"]["preferred_next"] == (
        "./repo-python tools/meta/control/git_state_snapshot.py --path-limit 40 "
        "--recent-limit 3 --skip-git-metadata-write-probe --compact"
    )
    assert cat_hints["replace_global_raw_diff_with_diff_review_context"]["preferred_next"] == (
        "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --path-limit 40 "
        "--recent-limit 3 --skip-git-metadata-write-probe --compact"
    )
    assert "global_raw_diff" in audit["bottlenecks"]["bash_cat"]["example_spans"][1]["command_shape_tags"]
    assert audit["bottlenecks"]["test_or_build_command"]["count"] == 1
    assert audit["bottlenecks"]["test_or_build_command"]["max_ms"] == 120000
    assert audit["bottlenecks"]["test_or_build_command"]["total_output_bytes"] == len(("pytest line\n" * 25).encode("utf-8"))
    assert audit["bottlenecks"]["test_or_build_command"]["example_spans"][0]["output_line_count"] == 25
    assert "output_limited" in audit["bottlenecks"]["test_or_build_command"]["example_spans"][0]["command_shape_tags"]
    assert "focused_test_target" in audit["bottlenecks"]["test_or_build_command"]["example_spans"][0]["command_shape_tags"]
    test_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["test_or_build_command"]["repair_hints"]}
    assert "avoid_tail_masked_test_runs" in test_hint_ids
    assert "route_focused_validation_through_action_quote" in test_hint_ids
    assert audit["bottlenecks"]["task_tool"]["count"] == 1
    assert audit["bottlenecks"]["task_tool"]["max_ms"] == 130000
    task_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["task_tool"]["repair_hints"]}
    assert "replace_long_tool_wait_with_process_summary" in task_hint_ids
    assert audit["bottlenecks"]["repo_tool_command"]["count"] == 1
    assert audit["bottlenecks"]["repo_tool_command"]["max_ms"] == 60000
    repo_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["repo_tool_command"]["repair_hints"]}
    assert "prefer_check_or_targeted_builder_mode" in repo_hint_ids
    assert "task_output_file" in audit["bottlenecks"]["read_file"]["example_spans"][0]["command_shape_tags"]
    assert "tmp_artifact_file" in audit["bottlenecks"]["read_file"]["example_spans"][0]["command_shape_tags"]
    read_hint_ids = {row["hint_id"] for row in audit["bottlenecks"]["read_file"]["repair_hints"]}
    assert "replace_output_file_read_with_status_surface" in read_hint_ids
    assert "prefer_card_or_section_before_full_doc_read" in read_hint_ids
    doc_hint = next(
        row
        for row in audit["bottlenecks"]["read_file"]["repair_hints"]
        if row["hint_id"] == "prefer_card_or_section_before_full_doc_read"
    )
    assert doc_hint["owner_surface"] == './repo-python kernel.py --entry "<task>" --context-budget 12000'
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
    assert find_hint["preferred_next"].startswith("./repo-python kernel.py --artifact-discovery-inventory")
    assert find_hint["owner_surface"].endswith("--artifact-discovery-inventory <term-or-root>")
    assert "rg --files <known-roots> | rg '<name-or-term>'" in find_hint["replacement_commands"]
    assert "metadata only" in find_hint["privacy_boundary"]
    assert "background_poll" in audit["bottlenecks"]["bash_grep"]["example_spans"][0]["command_shape_tags"]
    grep_hints = audit["bottlenecks"]["bash_grep"]["repair_hints"]
    grep_hint_ids = {row["hint_id"] for row in grep_hints}
    polling_hint = next(row for row in grep_hints if row["hint_id"] == "replace_polling_with_status_surface")
    assert polling_hint["preferred_next"] == "./repo-python kernel.py --process-summary claude:latest"
    assert polling_hint["owner_surface"] == "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"
    assert "./repo-python kernel.py --process-trace <session_id>" in polling_hint["replacement_commands"]
    assert "raw task-output bodies" in polling_hint["privacy_boundary"]
    assert "replace_raw_search_scan_with_owner_route" in grep_hint_ids
    raw_search_hint = next(row for row in grep_hints if row["hint_id"] == "replace_raw_search_scan_with_owner_route")
    assert raw_search_hint["preferred_next"].startswith(
        "./repo-python kernel.py --artifact-discovery-inventory"
    )
    assert raw_search_hint["owner_surface"].endswith("--artifact-discovery-inventory <term-or-root>")
    assert './repo-python kernel.py --entry "<task>" --context-budget 12000' in raw_search_hint["replacement_commands"]
    assert "metadata only" in raw_search_hint["privacy_boundary"]
    assert result["summary"]["top_output_producers"][0]["action_kind"] == "test_or_build_command"
    assert result["summary"]["summary"]["total_output_bytes"] >= audit["bottlenecks"]["test_or_build_command"]["total_output_bytes"]
    # Confirm slow_action_shape finding fired
    rules = {f["rule"] for f in audit["findings"]}
    assert "slow_action_shape" in rules


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
    assert raw_body["decision"]["patch_owner_surface"].endswith("--artifact-discovery-inventory <term-or-root>")
    steering = raw_body["steering"]
    assert steering["point_of_use_surface"] == "./repo-python kernel.py --process-bottlenecks --force"
    assert steering["replacement_route"].endswith("--artifact-discovery-inventory <term-or-root>")
    assert steering["applies_to_status"] == "governed_route_available_but_not_used"
    assert steering["applies_to_count"] >= 1
    assert "accepted_required_context" in steering["does_not_apply_to"]
    assert "false_positive" in steering["does_not_apply_to"]
    assert "Scoped low-output rg/find" in steering["accepted_case_guard"]
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
    assert "summary" in payload
    assert "payload" in payload
    assert "findings" in payload["payload"]
    assert "bottlenecks" in payload["payload"]
    assert "patterns" in payload["payload"]
    assert "mode_control" in payload["payload"]


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
    trace_result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-trace", "latest", "--process-trace-format", "json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    tape_result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-trace", "latest", "--process-trace-max-chars", "3000"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    audit_result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-audit"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    summary_result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--process-summary", "latest", "--force"],
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
    assert "audit_summary" in payload["payload"]
    assert payload["payload"]["output_economy"]["profile"] == "compact_owner_route"
    assert payload["payload"]["output_economy"]["default_target_bytes"] == 20_000
    assert payload["payload"]["output_economy"]["raw_bodies_omitted"] is True
    assert "session.spans" in payload["payload"]["output_economy"]["omitted_fields"]
    assert "spans" not in payload["payload"]["session"]
    assert "turns" not in payload["payload"]["session"]
    assert "findings" not in payload["payload"]["audit_summary"]
    assert len(summary_result.stdout.encode()) <= 20_000
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
    assert payload["source_freshness"]["mode"] in {
        "cached_summary",
        "speedboard_embedded_summary",
        "live_in_memory",
    }
    assert isinstance(payload["payload"]["top_bottlenecks"], list)
    assert isinstance(payload["payload"]["top_output_producers"], list)
    if payload["payload"]["top_bottlenecks"]:
        assert "example_spans" in payload["payload"]["top_bottlenecks"][0]
        assert "repair_hints" in payload["payload"]["top_bottlenecks"][0]
    context_yield = payload["payload"]["context_yield_attribution"]
    assert context_yield["output_profile"] == "compact_context_yield_status"
    assert context_yield["rows_returned"] <= 4
    assert context_yield["rows_available"] >= context_yield["rows_returned"]
    assert "./repo-python kernel.py --process-audit" in context_yield["full_payload_routes"]
    for row in context_yield["rows"]:
        assert "example_count" in row
        assert "actionable_active_bytes" in row
        assert "actionable_span_count" in row
        assert "omission_receipt" not in row
        assert row.get("examples") in (None, [])
    assert len(result.stdout.encode()) < 35_000


def test_process_bottleneck_next_commands_start_with_top_context_route() -> None:
    context_yield = {
        "rows": [
            {
                "motif": "raw_body_before_selection",
                "owner_surface": "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
                "existing_route": "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
            }
        ]
    }

    next_commands = navigate._process_bottleneck_next_commands(context_yield)

    assert next_commands[0]["command"] == "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>"
    assert "raw_body_before_selection" in next_commands[0]["reason"]
    assert next_commands[1]["command"] == "python3 kernel.py --process-audit"
    assert next_commands[2]["command"] == "python3 kernel.py --process-bottlenecks --force"


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
    assert output_economy["profile"] == "force_live_authoritative_rankings_compact_context_yield"
    assert output_economy["target_bytes"] == 30_000
    assert output_economy["row_limits"] == {
        "top_bottlenecks": 6,
        "top_output_producers": 5,
        "context_yield_rows": 4,
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
    assert context_yield["rows_returned"] <= 4
    for row in context_yield["rows"]:
        assert "example_count" in row
        assert "actionable_active_bytes" in row
        assert "actionable_span_count" in row
        assert "omission_receipt" not in row
        assert row.get("examples") in (None, [])
    assert len(result.stdout.encode()) < 30_000


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
                    "owner_surface": "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
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
                    "owner_surface": "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>",
                }
            ],
        }
    ]


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
