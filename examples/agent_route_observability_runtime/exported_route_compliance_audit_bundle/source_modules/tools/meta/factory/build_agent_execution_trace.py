#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Project local Claude Code + Codex CLI session rollouts into the
  agent-execution-trace hologram (`codex/hologram/process/*.json`) plus the
  bulk per-session span artifacts under `state/agent_telemetry/process/`.
- Mechanism: Delegate to `system.lib.agent_execution_trace.build_agent_execution_trace`
  for in-memory trace assembly; delegate to `write_agent_execution_trace` for
  live writes; support `--check` / `--summary` / `--json` preview modes.

[STRICT BOUNDARY]
- Read-only on `~/.claude` and `~/.codex`. Writes only under `codex/hologram/process/`
  and `state/agent_telemetry/process/<ts>/`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from system.lib.agent_execution_trace import (  # noqa: E402
    DEFAULT_STATE_DIR,
    REPO_ROOT,
    TRACE_RULES_PATH,
    build_agent_execution_trace,
    load_process_bottleneck_summary_cache,
    write_agent_execution_trace,
)


def _cached_summary_card(row: object) -> dict:
    if not isinstance(row, dict):
        return {}
    card = {
        "action_kind": row.get("action_kind"),
        "count": row.get("count"),
        "p50_ms": row.get("p50_ms"),
        "p95_ms": row.get("p95_ms"),
        "max_ms": row.get("max_ms"),
        "slow_count": row.get("slow_count"),
        "threshold_ms": row.get("threshold_ms"),
        "total_duration_ms": row.get("total_duration_ms"),
        "total_output_bytes": row.get("total_output_bytes"),
        "max_output_bytes": row.get("max_output_bytes"),
        "p95_output_bytes": row.get("p95_output_bytes"),
        "first_hint": row.get("first_hint"),
        "actionability_class": row.get("actionability_class"),
        "optimization_priority_score": row.get("optimization_priority_score"),
    }
    repair_hints = row.get("repair_hints")
    if isinstance(repair_hints, list):
        hint_cards = []
        for hint in repair_hints[:3]:
            if not isinstance(hint, dict):
                continue
            hint_card = {
                "hint_id": hint.get("hint_id"),
                "preferred_next": hint.get("preferred_next"),
                "owner_surface": hint.get("owner_surface"),
                "quote_surface": hint.get("quote_surface"),
            }
            hint_cards.append(
                {key: value for key, value in hint_card.items() if value is not None}
            )
        if hint_cards:
            card["repair_hint_cards"] = hint_cards
    return {key: value for key, value in card.items() if value is not None}


def _cached_summary_full_command(refresh: dict) -> object:
    full_command = refresh.get("cache_check_command")
    if isinstance(full_command, str) and "--full" not in full_command.split():
        return f"{full_command} --full"
    return full_command


def _cached_summary_cli_compact_payload(payload: dict) -> dict:
    """Return the default first-contact packet for --cached-summary."""
    decision = payload.get("decision_authority")
    decision = decision if isinstance(decision, dict) else {}
    refresh = payload.get("refresh")
    refresh = refresh if isinstance(refresh, dict) else {}
    summary = payload.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    payload_body = payload.get("payload")
    payload_body = payload_body if isinstance(payload_body, dict) else {}
    top_bottlenecks = payload_body.get("top_bottlenecks")
    top_bottlenecks = top_bottlenecks if isinstance(top_bottlenecks, list) else []
    top_output_producers = payload_body.get("top_output_producers")
    top_output_producers = top_output_producers if isinstance(top_output_producers, list) else []
    action_kind_filter = payload_body.get("action_kind_filter")
    action_kind_filter = action_kind_filter if isinstance(action_kind_filter, dict) else None
    full_command = _cached_summary_full_command(refresh)
    return {
        "kind": "agent_execution_trace_cached_bottleneck_summary",
        "schema_version": "process_bottleneck_summary_cache_cli_compact_v0",
        "full_schema_version": payload.get("schema_version"),
        "generated_at": payload.get("generated_at"),
        "ok": bool(payload.get("ok")),
        "probe_ok": bool(payload.get("probe_ok")),
        "probe": payload.get("probe"),
        "status": payload.get("status"),
        "decision_authority": decision,
        "query": payload.get("query") or {},
        "summary": {
            "row_count": summary.get("row_count", 0),
            "source_row_count": summary.get("source_row_count", 0),
            "session_count": summary.get("session_count", 0),
            "wall_ms": summary.get("wall_ms"),
            "static_source_status": summary.get("static_source_status"),
            "dynamic_rollout_status": summary.get("dynamic_rollout_status"),
            **(
                {"filtered_action_kind_count": summary.get("filtered_action_kind_count", 0)}
                if action_kind_filter
                else {}
            ),
        },
        **({"action_kind_filter": action_kind_filter} if action_kind_filter else {}),
        "top_bottleneck_cards": [_cached_summary_card(row) for row in top_bottlenecks],
        "top_output_producer_cards": [
            _cached_summary_card(row) for row in top_output_producers
        ],
        "safe_commands": {
            "full_cached_summary_command": full_command,
            "host_pressure_check_command": refresh.get("host_pressure_check_command"),
            "pressure_safe_fallback_command": refresh.get("pressure_safe_fallback_command"),
            "materialize_when_pressure_allows_command": refresh.get(
                "bounded_materialize_read_model_command"
            ),
            "status_after_materialize_command": refresh.get("bounded_status_command"),
            "authoritative_decision_command": refresh.get("force_live_kernel_command"),
        },
        "output_economy": {
            "profile": (
                "compact_cached_summary_action_kind_filter"
                if action_kind_filter
                else "compact_cached_summary_default"
            ),
            "full_payload_command": full_command,
            "omitted": [
                "payload.top_bottlenecks.example_spans",
                "payload.top_output_producers.example_spans",
                "payload.source_summary",
                "source_hash_receipt",
                "refresh.full_command_map",
            ],
            "reason": (
                "--cached-summary is a pressure-safe first-contact packet; use --full "
                "when the full cached read-model rows or source receipts are required."
            ),
        },
        "warnings": payload.get("warnings") or [],
    }


def _cached_summary_check_payload(payload: dict) -> dict:
    """Return the compact probe packet for --cached-summary --check."""
    decision = payload.get("decision_authority")
    decision = decision if isinstance(decision, dict) else {}
    refresh = payload.get("refresh")
    refresh = refresh if isinstance(refresh, dict) else {}
    summary = payload.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    payload_body = payload.get("payload")
    payload_body = payload_body if isinstance(payload_body, dict) else {}
    action_kind_filter = payload_body.get("action_kind_filter")
    action_kind_filter = action_kind_filter if isinstance(action_kind_filter, dict) else None
    return {
        "kind": "agent_execution_trace_cached_bottleneck_summary_check",
        "schema_version": "process_bottleneck_summary_cache_check_v0",
        "generated_at": payload.get("generated_at"),
        "ok": bool(payload.get("ok")),
        "probe_ok": bool(payload.get("probe_ok")),
        "probe": payload.get("probe"),
        "status": payload.get("status"),
        "decision_authority": decision,
        "query": payload.get("query") or {},
        "summary": {
            "row_count": summary.get("row_count", 0),
            "source_row_count": summary.get("source_row_count", 0),
            "session_count": summary.get("session_count", 0),
            "wall_ms": summary.get("wall_ms"),
            "static_source_status": summary.get("static_source_status"),
            "dynamic_rollout_status": summary.get("dynamic_rollout_status"),
            **(
                {"filtered_action_kind_count": summary.get("filtered_action_kind_count", 0)}
                if action_kind_filter
                else {}
            ),
        },
        **({"action_kind_filter": action_kind_filter} if action_kind_filter else {}),
        "safe_commands": {
            "full_cached_summary_command": _cached_summary_full_command(refresh),
            "host_pressure_check_command": refresh.get("host_pressure_check_command"),
            "pressure_safe_fallback_command": refresh.get("pressure_safe_fallback_command"),
            "materialize_when_pressure_allows_command": refresh.get(
                "bounded_materialize_read_model_command"
            ),
            "status_after_materialize_command": refresh.get("bounded_status_command"),
            "authoritative_decision_command": refresh.get("force_live_kernel_command"),
        },
        "output_economy": {
            "profile": (
                "compact_cached_summary_check_action_kind_filter"
                if action_kind_filter
                else "compact_cached_summary_check"
            ),
            "full_payload_command": _cached_summary_full_command(refresh),
            "omitted": [
                "payload.top_bottlenecks",
                "payload.top_output_producers",
                "payload.source_summary",
                "source_hash_receipt",
                "refresh.full_command_map",
            ],
            "reason": (
                "--cached-summary --check is a cheap admission/probe lane; full bottleneck "
                "rows remain behind the non-check cached-summary command."
            ),
        },
        "warnings": payload.get("warnings") or [],
    }


def _live_summary_cli_compact_payload(payload: dict, *, check: bool) -> dict:
    """Return the default compact packet for --summary / --check."""
    summary_payload = payload.get("summary")
    summary_payload = summary_payload if isinstance(summary_payload, dict) else {}
    summary_counts = summary_payload.get("summary")
    summary_counts = summary_counts if isinstance(summary_counts, dict) else {}
    top_bottlenecks = summary_payload.get("top_bottlenecks")
    top_bottlenecks = top_bottlenecks if isinstance(top_bottlenecks, list) else []
    top_output_producers = summary_payload.get("top_output_producers")
    top_output_producers = top_output_producers if isinstance(top_output_producers, list) else []
    top_patterns = summary_payload.get("top_patterns")
    top_patterns = top_patterns if isinstance(top_patterns, list) else []
    context_yield = summary_payload.get("context_yield_attribution")
    context_yield = context_yield if isinstance(context_yield, dict) else {}
    context_yield_summary = context_yield.get("summary")
    context_yield_summary = context_yield_summary if isinstance(context_yield_summary, dict) else {}
    return {
        "kind": summary_payload.get("kind") or "agent_execution_trace_summary",
        "schema_version": "agent_execution_trace_summary_cli_compact_v0",
        "full_schema_version": summary_payload.get("schema_version"),
        "generated_at": summary_payload.get("generated_at"),
        "check": check,
        "summary": summary_counts,
        "top_bottleneck_cards": [_cached_summary_card(row) for row in top_bottlenecks[:4]],
        "top_output_producer_cards": [
            _cached_summary_card(row) for row in top_output_producers[:3]
        ],
        "top_pattern_cards": [
            {
                "pattern_id": row.get("pattern_id"),
                "severity": row.get("severity"),
                "instances": row.get("instances"),
                "session_hits": row.get("session_hits"),
            }
            for row in top_patterns[:5]
            if isinstance(row, dict)
        ],
        "context_yield_summary": context_yield_summary,
        "safe_commands": {
            "full_summary_command": (
                "./repo-python tools/meta/factory/build_agent_execution_trace.py "
                "--check --summary --full"
                if check
                else "./repo-python tools/meta/factory/build_agent_execution_trace.py --summary --full"
            ),
            "cached_summary_command": (
                "./repo-python tools/meta/factory/build_agent_execution_trace.py "
                "--cached-summary --limit 6"
            ),
            "process_bottlenecks_command": "./repo-python kernel.py --process-bottlenecks",
        },
        "output_economy": {
            "profile": (
                "compact_live_summary_check" if check else "compact_live_summary_default"
            ),
            "full_payload_command": (
                "./repo-python tools/meta/factory/build_agent_execution_trace.py "
                "--check --summary --full"
                if check
                else "./repo-python tools/meta/factory/build_agent_execution_trace.py --summary --full"
            ),
            "omitted": [
                "top_bottlenecks.example_spans",
                "top_output_producers.example_spans",
                "context_yield_attribution.rows",
                "source_summary",
                "raw trace bodies",
            ],
            "reason": (
                "--summary and --check are first-contact validation packets; use --full "
                "when row examples or full attribution details are required."
            ),
        },
    }


def _resolve_path(repo_root: Path, raw: str | None) -> Path | None:
    if raw is None:
        return None
    path = Path(raw)
    return path if path.is_absolute() else (repo_root / path).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build codex/hologram/process audit surfaces. Parses Claude Code and Codex "
            "session JSONL rollouts into span/trace records with durations, bottleneck "
            "percentiles, anti-pattern detections, and navigation-route compliance."
        )
    )
    parser.add_argument("--repo-root", default=None, help="Override repository root.")
    parser.add_argument(
        "--rules",
        default=str(TRACE_RULES_PATH.relative_to(REPO_ROOT)),
        help="Path to trace_rules.json (navigation ladder, thresholds, anti-pattern severities).",
    )
    parser.add_argument(
        "--home",
        default=None,
        help="Override $HOME for session discovery (defaults to Path.home()).",
    )
    parser.add_argument(
        "--since",
        default=None,
        metavar="ISO8601",
        help="Only ingest sessions whose mtime is >= since (default: all).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Limit number of sessions per agent (default: trace_rules.ingest.default_session_lookback_count).",
    )
    parser.add_argument(
        "--claude-only",
        action="store_true",
        help="Skip Codex sessions; ingest only Claude.",
    )
    parser.add_argument(
        "--codex-only",
        action="store_true",
        help="Skip Claude sessions; ingest only Codex.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full audit JSON to stdout instead of writing to disk.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print only the summary JSON (counts + top bottlenecks + top patterns).",
    )
    parser.add_argument(
        "--cached-summary",
        action="store_true",
        help="Read codex/hologram/process/summary.json directly; does not parse rollout files.",
    )
    parser.add_argument(
        "--action-kind",
        dest="action_kinds",
        action="append",
        default=[],
        metavar="ACTION_KIND",
        help=(
            "With --cached-summary: emit only matching bottleneck/output rows. "
            "Repeatable."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "With --cached-summary or --summary/--check: emit full read-model rows "
            "instead of compact cards."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build in memory; print summary; exit non-zero if any finding severity is 'error'.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors when combined with --check.",
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help=f"Override state dir for bulk span artifacts (default: {DEFAULT_STATE_DIR}).",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    rules_path = _resolve_path(repo_root, args.rules)
    home_path = Path(args.home).resolve() if args.home else None
    state_dir = _resolve_path(repo_root, args.state_dir)

    claude_override: list[Path] | None = None
    codex_override: list[Path] | None = None
    if args.codex_only:
        claude_override = []
    if args.claude_only:
        codex_override = []

    if args.cached_summary:
        payload = load_process_bottleneck_summary_cache(
            repo_root=repo_root,
            limit=args.limit,
            action_kinds=args.action_kinds,
        )
        if args.check:
            output_payload = _cached_summary_check_payload(payload)
        elif args.full:
            output_payload = payload
        else:
            output_payload = _cached_summary_cli_compact_payload(payload)
        print(json.dumps(output_payload, indent=2, ensure_ascii=False))
        if args.check and not payload.get("ok"):
            return 1
        return 0

    build_kwargs = {
        "repo_root": repo_root,
        "rules_path": rules_path,
        "home": home_path,
        "session_files_claude": claude_override,
        "session_files_codex": codex_override,
        "since_ts": args.since,
        "session_limit": args.limit,
    }

    if args.check or args.summary:
        payload = build_agent_execution_trace(**build_kwargs)
        summary = payload["audit"].get("summary") or {}
        error_count = int(summary.get("error_count") or 0)
        warning_count = int(summary.get("warning_count") or 0)
        output_payload = (
            payload["summary"]
            if args.full
            else _live_summary_cli_compact_payload(payload, check=bool(args.check))
        )
        print(json.dumps(output_payload, indent=2, ensure_ascii=False))
        if args.check:
            if error_count > 0 or (args.strict and warning_count > 0):
                return 1
        return 0

    if args.json:
        payload = build_agent_execution_trace(**build_kwargs)
        print(json.dumps(payload["audit"], indent=2, ensure_ascii=False))
        return 0

    receipt = write_agent_execution_trace(
        **build_kwargs,
        write_state_dir=state_dir,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
