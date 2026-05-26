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
        payload = load_process_bottleneck_summary_cache(repo_root=repo_root, limit=args.limit)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get("ok") else 1

    payload = build_agent_execution_trace(
        repo_root=repo_root,
        rules_path=rules_path,
        home=home_path,
        session_files_claude=claude_override,
        session_files_codex=codex_override,
        since_ts=args.since,
        session_limit=args.limit,
    )
    summary = payload["audit"].get("summary") or {}
    error_count = int(summary.get("error_count") or 0)
    warning_count = int(summary.get("warning_count") or 0)

    if args.check or args.summary:
        print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    elif args.json:
        print(json.dumps(payload["audit"], indent=2, ensure_ascii=False))
    else:
        receipt = write_agent_execution_trace(
            repo_root=repo_root,
            rules_path=rules_path,
            home=home_path,
            session_files_claude=claude_override,
            session_files_codex=codex_override,
            since_ts=args.since,
            session_limit=args.limit,
            write_state_dir=state_dir,
        )
        print(json.dumps(receipt, indent=2, ensure_ascii=False))

    if args.check:
        if error_count > 0 or (args.strict and warning_count > 0):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
