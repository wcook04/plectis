#!/usr/bin/env python3
"""Emit the read-only mission transaction landing preflight packet."""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import shlex
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.mission_transaction_landing_preflight import (  # noqa: E402
    CONTROL_SUMMARY_SETTLEMENT_DEFERRED_REASON,
    DEFAULT_CONTROL_SUMMARY_SUBJECT_ID,
    DEFAULT_COMPACT_SETTLEMENT_DEFERRED_REASON,
    LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON,
    WORKSPACE_BLOAT_PRESSURE_SETTLEMENT_DEFERRED_REASON,
    build_explore_execute_review_runtime_closeout,
    build_mission_transaction_landing_preflight,
    build_shared_index_quarantine_fast,
    compact_mission_transaction_landing_preflight,
    command_artifact_contract,
    load_autonomous_seed_payload,
    mission_transaction_control_summary,
)
from system.lib.git_state_snapshot import (  # noqa: E402
    build_closeout_git_state_conditions,
)
from system.lib.landing_bankruptcy import build_landing_bankruptcy_summary  # noqa: E402
from system.lib.navigation_trace import record_attention_event  # noqa: E402


STATUS_SEVERITY = {
    "clear": 0,
    "watch": 1,
    "review": 2,
    "blocked": 3,
    "hard_stop": 4,
}


DEFAULT_COMPACT_PREFLIGHT_TIMEOUT_SECONDS = 20


ZSH_PATH_SHADOWING_NOTE = (
    "Shell note: when looping over --owned-path values in zsh, do not name "
    "the loop variable 'path'. zsh treats lowercase 'path' as the array that "
    "backs PATH, so shadowing it can make repo-python, git, or repo-git "
    "unresolvable inside the same command. Use a variable such as "
    "'owned_path' or 'relpath' instead."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=ZSH_PATH_SHADOWING_NOTE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to inspect. Defaults to the current ai_workflow checkout.",
    )
    parser.add_argument(
        "--owned-path",
        action="append",
        default=[],
        help="Repo-relative path owned by this mission. Repeatable.",
    )
    parser.add_argument(
        "--accepted-organ-companion-path",
        action="append",
        default=[],
        help=(
            "Repo-relative Microcosm accepted-organ companion path checked as "
            "proof-only; repeatable and not part of the write set."
        ),
    )
    parser.add_argument(
        "--write-profile",
        action="append",
        default=[],
        help="Work Ledger write profile name to include in the declared write set. Repeatable.",
    )
    parser.add_argument(
        "--target-id",
        action="append",
        default=[],
        help="WorkItem/cap/td target id for the mission card and td-claim collision scan. Repeatable.",
    )
    parser.add_argument(
        "--td-id",
        action="append",
        default=[],
        help="Alias for --target-id when the target is a Work Ledger td_id. Repeatable.",
    )
    parser.add_argument(
        "--subject-id",
        action="append",
        default=[],
        help="Alias for --target-id when the target is a Task Ledger cap/WorkItem id. Repeatable.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "Current Work Ledger session id; matching active claims are treated as owned, "
            "not collisions. Use 'auto' to bind the single relevant active-claim session "
            "when the requested target/path set has exactly one candidate owner."
        ),
    )
    parser.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Classify overlapping Work Ledger path claims as blockers instead of watch pressure.",
    )
    parser.add_argument(
        "--fail-on-status",
        choices=tuple(STATUS_SEVERITY),
        default=None,
        help="Exit nonzero when landing_decision.status is at least this severity. Output remains JSON.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility no-op; mission transaction preflight output is always JSON.",
    )
    parser.add_argument(
        "--attention-frame",
        default=None,
        help="Append a mutation_boundary_observed AttentionEvent to this frame id, or use 'new'/'latest'.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Emit the complete preflight packet, including full dirty-path, classification, Work Ledger, registry, and guard detail.",
    )
    parser.add_argument(
        "--preflight-timeout-seconds",
        type=float,
        default=None,
        help=(
            "Bound the core preflight builder. Compact/local preflight defaults to "
            f"{DEFAULT_COMPACT_PREFLIGHT_TIMEOUT_SECONDS}s; use 0 to disable. "
            "Explicit full/heavy drilldowns default to no timeout unless this is set."
        ),
    )
    parser.add_argument(
        "--convergence",
        action="store_true",
        help="Emit only transaction_convergence_v0 from the read-only preflight packet.",
    )
    parser.add_argument(
        "--reconcile-plan",
        action="store_true",
        help="Emit only transaction_convergence_reconcile_v0 from the read-only preflight packet.",
    )
    parser.add_argument(
        "--staged-index-quarantine",
        action="store_true",
        help="Emit only shared_index_quarantine_v0 from the read-only preflight packet.",
    )
    parser.add_argument(
        "--control-summary",
        action="store_true",
        help="Emit transaction_control_plane_summary_v0 for entry, phase, and operator HUD surfaces.",
    )
    parser.add_argument(
        "--autonomous-edit-gate",
        action="store_true",
        help="Emit only autonomous_edit_gate_v0, the pre-mutation gate for autonomous feature work.",
    )
    parser.add_argument(
        "--landing-bankruptcy-summary",
        action="store_true",
        help="Emit fast read-only rescue-ref/landing insolvency summary without ledger rebuild or generated-state settlement.",
    )
    parser.add_argument(
        "--bloat-governor",
        action="store_true",
        help="Emit only derived_state_bloat_governor_v0 from the read-only preflight packet.",
    )
    parser.add_argument(
        "--workspace-bloat-pressure",
        action="store_true",
        help="Emit only workspace_bloat_pressure_v0 from the derived-state bloat governor.",
    )
    parser.add_argument(
        "--runtime-artifact-lifecycle",
        action="store_true",
        help="Emit only runtime_artifact_lifecycle_v0, a read-only dry-run classifier for dirty state/runs artifacts.",
    )
    parser.add_argument(
        "--github-push-bloat-gate",
        action="store_true",
        help="Emit only github_push_bloat_gate_v1 from the derived-state bloat governor.",
    )
    parser.add_argument(
        "--closeout-git-state",
        action="store_true",
        help="Emit the cheap closeout_git_state_conditions packet for entry/pulse/statusline consumers.",
    )
    parser.add_argument(
        "--derived-artifact-policy",
        action="store_true",
        help="Emit only derived_artifact_policy_v1 from the derived-state bloat governor.",
    )
    parser.add_argument(
        "--explore-execute-review",
        action="store_true",
        help="Emit only explore_execute_review_runtime_closeout_v0 for autonomous seed runtime closeout.",
    )
    parser.add_argument(
        "--external-pattern-seed",
        default=None,
        help="Autonomous seed id or JSON path to compose into --explore-execute-review.",
    )
    parser.add_argument(
        "--selector-surface",
        default=None,
        help="Selector command/source label to record in --explore-execute-review output.",
    )
    parser.add_argument(
        "--blocked-primary-receipt-json",
        default=None,
        help=(
            "JSON object carrying the blocked-primary continuation receipt to validate "
            "inside --explore-execute-review."
        ),
    )
    parser.add_argument(
        "--blocked-primary-receipt-file",
        default=None,
        help=(
            "Path to a JSON object carrying the blocked-primary continuation receipt "
            "to validate inside --explore-execute-review."
        ),
    )
    return parser


def _load_json_object(value: str, *, source: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{source} must decode to a JSON object")
    return parsed


def _load_blocked_primary_receipt(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.blocked_primary_receipt_json and args.blocked_primary_receipt_file:
        raise ValueError("use only one of --blocked-primary-receipt-json or --blocked-primary-receipt-file")
    if args.blocked_primary_receipt_json:
        return _load_json_object(
            str(args.blocked_primary_receipt_json),
            source="--blocked-primary-receipt-json",
        )
    if args.blocked_primary_receipt_file:
        path = Path(args.blocked_primary_receipt_file)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"--blocked-primary-receipt-file could not be read: {exc}") from exc
        return _load_json_object(text, source="--blocked-primary-receipt-file")
    return None


def _resolve_preflight_timeout_seconds(
    args: argparse.Namespace,
    *,
    compact_timeout_default: bool,
) -> float:
    if args.preflight_timeout_seconds is not None:
        return max(0.0, float(args.preflight_timeout_seconds))
    if compact_timeout_default:
        return float(DEFAULT_COMPACT_PREFLIGHT_TIMEOUT_SECONDS)
    return 0.0


def _command_string(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _reentry_lane(
    *,
    lane_id: str,
    purpose: str,
    argv: list[str],
    mutation_class: str,
) -> dict[str, Any]:
    command = _command_string(argv)
    return {
        "lane_id": lane_id,
        "purpose": purpose,
        "argv": argv,
        "command": command,
        "command_contract": command_artifact_contract(command, argv=argv),
        "mutation_class": mutation_class,
    }


def _preflight_timeout_reentry_lanes(
    args: argparse.Namespace,
    *,
    target_ids: list[str],
) -> list[dict[str, Any]]:
    base_args: list[str] = [
        "./repo-python",
        "tools/meta/control/mission_transaction_preflight.py",
    ]
    for owned_path in args.owned_path or []:
        base_args.extend(["--owned-path", str(owned_path)])
    for companion_path in args.accepted_organ_companion_path or []:
        base_args.extend(["--accepted-organ-companion-path", str(companion_path)])
    for write_profile in args.write_profile or []:
        base_args.extend(["--write-profile", str(write_profile)])
    for target_id in target_ids:
        base_args.extend(["--target-id", str(target_id)])
    if args.session_id:
        base_args.extend(["--session-id", str(args.session_id)])
    if args.require_exclusive:
        base_args.append("--require-exclusive")

    lanes: list[dict[str, Any]] = [
        _reentry_lane(
            lane_id="rerun_unbounded_preflight",
            purpose="Debug the slow core preflight builder intentionally.",
            argv=[*base_args, "--preflight-timeout-seconds", "0"],
            mutation_class="read_only_drilldown",
        ),
        _reentry_lane(
            lane_id="staged_index_quarantine_fast_path",
            purpose="Check only staged-index safety without invoking the slow core builder.",
            argv=[*base_args, "--staged-index-quarantine"],
            mutation_class="read_only_fast_path",
        ),
    ]
    if args.owned_path:
        mutation_check_argv = [
            "./repo-python",
            "tools/meta/factory/work_ledger.py",
            "mutation-check",
        ]
        for owned_path in args.owned_path or []:
            mutation_check_argv.extend(["--path", str(owned_path)])
        mutation_check_argv.append("--require-exclusive")
        lanes.append(
            _reentry_lane(
                lane_id="work_ledger_claim_recheck",
                purpose="Recheck same-path ownership before pivoting or landing.",
                argv=mutation_check_argv,
                mutation_class="read_only_claim_check",
            )
        )
    if args.owned_path and args.session_id:
        scoped_commit_argv = [
            "./repo-python",
            "tools/meta/control/scoped_commit.py",
            "full-paths",
            "--dry-run",
            "--allow-multi-hunk-full-paths",
            "--work-ledger-session-id",
            str(args.session_id),
            "--message",
            "preflight-timeout follow-up",
        ]
        for owned_path in args.owned_path or []:
            scoped_commit_argv.extend(["--path", str(owned_path)])
        lanes.append(
            _reentry_lane(
                lane_id="scoped_commit_guard_dry_run",
                purpose="If focused owner validation is already green, prove the claimed owned paths can land without broad staging.",
                argv=scoped_commit_argv,
                mutation_class="private_index_dry_run",
            )
        )
    return lanes


def _build_preflight_timeout_payload(
    args: argparse.Namespace,
    *,
    target_ids: list[str],
    timeout_seconds: float,
    elapsed_seconds: float,
    child_process: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "mission_transaction_landing_preflight_timeout_v0",
        "repo_root": str(Path(args.repo_root).resolve()),
        "mode": "read_only",
        "output_profile": "compact",
        "inputs": {
            "owned_paths": list(args.owned_path or []),
            "accepted_organ_companion_paths": list(
                args.accepted_organ_companion_path or []
            ),
            "write_profiles": list(args.write_profile or []),
            "target_ids": list(target_ids or []),
            "session_id": args.session_id,
            "require_exclusive": bool(args.require_exclusive),
        },
        "timeout": {
            "status": "timed_out",
            "surface": "build_mission_transaction_landing_preflight",
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "child_process": child_process,
        },
        "landing_decision": {
            "status": "blocked",
            "reason": "mission_transaction_preflight_timeout",
            "recommended_lane": "inspect_preflight_child_process_or_rerun_explicit_full_drilldown",
            "reentry_condition": (
                "Rerun after resolving the slow preflight child process, or use "
                "--preflight-timeout-seconds 0 for an intentional unbounded drilldown."
            ),
        },
        "reentry_lanes": _preflight_timeout_reentry_lanes(args, target_ids=target_ids),
        "work_ledger": {
            "status": "unknown",
            "reason": "core_preflight_builder_timed_out_before_work_ledger_packet",
        },
        "git": {
            "status": "unknown",
            "reason": "core_preflight_builder_timed_out_before_git_packet",
        },
        "dirty_tree_classification": {
            "status": "unknown",
            "reason": "core_preflight_builder_timed_out_before_dirty_tree_classification",
        },
    }


def _call_preflight_builder(
    args: argparse.Namespace,
    *,
    target_ids: list[str],
    include_push_bloat_gate: bool,
    include_generated_projection_settlement: bool,
    generated_projection_settlement_deferred_reason: str,
) -> dict[str, Any]:
    return build_mission_transaction_landing_preflight(
        Path(args.repo_root),
        owned_paths=list(args.owned_path or []),
        accepted_organ_companion_paths=list(args.accepted_organ_companion_path or []),
        write_profiles=list(args.write_profile or []),
        target_ids=target_ids,
        session_id=args.session_id,
        require_exclusive=bool(args.require_exclusive),
        include_push_bloat_gate=include_push_bloat_gate,
        include_generated_projection_settlement=include_generated_projection_settlement,
        generated_projection_settlement_deferred_reason=generated_projection_settlement_deferred_reason,
    )


def _preflight_builder_worker(result_path: str, kwargs: dict[str, Any]) -> None:
    try:
        result = {"status": "ok", "payload": _call_preflight_builder(**kwargs)}
    except BaseException as exc:  # pragma: no cover - defensive process boundary
        result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    Path(result_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def _build_preflight_with_timeout(
    args: argparse.Namespace,
    *,
    target_ids: list[str],
    include_push_bloat_gate: bool,
    include_generated_projection_settlement: bool,
    generated_projection_settlement_deferred_reason: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    builder_kwargs = {
        "args": args,
        "target_ids": target_ids,
        "include_push_bloat_gate": include_push_bloat_gate,
        "include_generated_projection_settlement": include_generated_projection_settlement,
        "generated_projection_settlement_deferred_reason": generated_projection_settlement_deferred_reason,
    }
    if timeout_seconds <= 0:
        return _call_preflight_builder(**builder_kwargs)

    started = time.monotonic()
    context = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else mp.get_context()
    result_file = tempfile.NamedTemporaryFile(
        prefix="mission_preflight_builder_",
        suffix=".json",
        delete=False,
    )
    result_path = Path(result_file.name)
    result_file.close()
    process = context.Process(target=_preflight_builder_worker, args=(str(result_path), builder_kwargs))
    process.start()
    try:
        process.join(timeout_seconds)
        if process.is_alive():
            child_process = {
                "pid": process.pid,
                "exitcode_before_stop": process.exitcode,
                "terminate_sent": True,
                "kill_sent": False,
                "stopped": False,
                "exitcode_after_stop": None,
            }
            process.terminate()
            process.join(2)
            if process.is_alive():  # pragma: no cover - best-effort hard stop
                child_process["kill_sent"] = True
                process.kill()
                process.join(2)
            child_process["stopped"] = not process.is_alive()
            child_process["exitcode_after_stop"] = process.exitcode
            return _build_preflight_timeout_payload(
                args,
                target_ids=target_ids,
                timeout_seconds=timeout_seconds,
                elapsed_seconds=time.monotonic() - started,
                child_process=child_process,
            )

        if not result_path.exists() or result_path.stat().st_size == 0:
            raise RuntimeError("preflight builder exited without returning a packet")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") == "error":
            raise RuntimeError(str(result.get("error") or "preflight builder failed"))
        payload = result.get("payload")
        if not isinstance(payload, dict):
            raise RuntimeError("preflight builder returned a non-object packet")
        return payload
    finally:
        result_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(raw_argv)
    try:
        blocked_primary_receipt = _load_blocked_primary_receipt(args)
    except ValueError as exc:
        parser.error(str(exc))
    if args.closeout_git_state:
        output = build_closeout_git_state_conditions(Path(args.repo_root), path_limit=10, recent_limit=2)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0 if output.get("status") != "unknown" else 1
    if args.landing_bankruptcy_summary:
        output = build_landing_bankruptcy_summary(Path(args.repo_root))
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    staged_index_quarantine_fast_path = bool(args.staged_index_quarantine) and not (
        args.full
        or args.convergence
        or args.reconcile_plan
        or args.control_summary
        or args.autonomous_edit_gate
        or args.bloat_governor
        or args.workspace_bloat_pressure
        or args.runtime_artifact_lifecycle
        or args.github_push_bloat_gate
        or args.derived_artifact_policy
        or args.explore_execute_review
    )
    if staged_index_quarantine_fast_path:
        output = build_shared_index_quarantine_fast(
            Path(args.repo_root),
            owned_paths=list(args.owned_path or []),
            write_profiles=list(args.write_profile or []),
        )
        payload = {
            "schema": "mission_transaction_landing_preflight_staged_index_fast_path_v0",
            "repo_root": str(Path(args.repo_root).resolve()),
            "mode": "read_only",
            "shared_index_quarantine": output,
            "landing_decision": {"status": output.get("status") or "clear"},
        }
    else:
        output = None
        payload = None
    local_owned_path_preflight = bool(args.owned_path) and not (
        args.full
        or args.bloat_governor
        or args.github_push_bloat_gate
        or args.runtime_artifact_lifecycle
    )
    control_summary_fast_path = bool(args.control_summary) and not (
        args.full
        or args.bloat_governor
        or args.github_push_bloat_gate
        or args.derived_artifact_policy
        or args.workspace_bloat_pressure
        or args.runtime_artifact_lifecycle
    )
    workspace_bloat_pressure_fast_path = bool(args.workspace_bloat_pressure) and not (
        args.full
        or args.bloat_governor
        or args.github_push_bloat_gate
        or args.derived_artifact_policy
        or args.explore_execute_review
        or args.runtime_artifact_lifecycle
        or args.convergence
        or args.reconcile_plan
        or args.control_summary
        or args.autonomous_edit_gate
        or args.staged_index_quarantine
    )
    autonomous_edit_gate_fast_path = bool(args.autonomous_edit_gate) and not (
        args.full
        or args.bloat_governor
        or args.github_push_bloat_gate
        or args.derived_artifact_policy
        or args.explore_execute_review
        or args.runtime_artifact_lifecycle
        or args.convergence
        or args.reconcile_plan
        or args.control_summary
        or args.workspace_bloat_pressure
        or args.staged_index_quarantine
    )
    default_compact_fast_path = not (
        args.full
        or args.bloat_governor
        or args.workspace_bloat_pressure
        or args.runtime_artifact_lifecycle
        or args.github_push_bloat_gate
        or args.derived_artifact_policy
        or args.explore_execute_review
        or args.convergence
        or args.reconcile_plan
        or args.control_summary
        or args.autonomous_edit_gate
        or args.staged_index_quarantine
    )
    defer_generated_projection_settlement = (
        local_owned_path_preflight
        or control_summary_fast_path
        or workspace_bloat_pressure_fast_path
        or autonomous_edit_gate_fast_path
        or args.runtime_artifact_lifecycle
        or default_compact_fast_path
    )
    target_ids = [
        *list(args.target_id or []),
        *list(args.td_id or []),
        *list(args.subject_id or []),
    ]
    if args.control_summary and not target_ids:
        target_ids = [DEFAULT_CONTROL_SUMMARY_SUBJECT_ID]
    if payload is None:
        include_push_bloat_gate = not (
            local_owned_path_preflight
            or control_summary_fast_path
            or workspace_bloat_pressure_fast_path
            or autonomous_edit_gate_fast_path
            or args.runtime_artifact_lifecycle
            or default_compact_fast_path
        )
        include_generated_projection_settlement = not defer_generated_projection_settlement
        generated_projection_settlement_deferred_reason = (
            CONTROL_SUMMARY_SETTLEMENT_DEFERRED_REASON
            if control_summary_fast_path
            else WORKSPACE_BLOAT_PRESSURE_SETTLEMENT_DEFERRED_REASON
            if workspace_bloat_pressure_fast_path
            or args.runtime_artifact_lifecycle
            else LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON
            if local_owned_path_preflight
            else DEFAULT_COMPACT_SETTLEMENT_DEFERRED_REASON
        )
        timeout_seconds = _resolve_preflight_timeout_seconds(
            args,
            compact_timeout_default=(
                local_owned_path_preflight
                or control_summary_fast_path
                or workspace_bloat_pressure_fast_path
                or autonomous_edit_gate_fast_path
                or args.runtime_artifact_lifecycle
                or default_compact_fast_path
            ),
        )
        if argv is not None and args.preflight_timeout_seconds is None:
            timeout_seconds = 0.0
        payload = _build_preflight_with_timeout(
            args,
            target_ids=target_ids,
            include_push_bloat_gate=include_push_bloat_gate,
            include_generated_projection_settlement=include_generated_projection_settlement,
            generated_projection_settlement_deferred_reason=generated_projection_settlement_deferred_reason,
            timeout_seconds=timeout_seconds,
        )
    if output is not None:
        pass
    elif args.reconcile_plan:
        output = payload.get("transaction_convergence_reconcile") or {}
    elif args.control_summary:
        output = mission_transaction_control_summary(payload, consumer_surface="cli")
    elif args.autonomous_edit_gate:
        output = payload.get("autonomous_edit_gate") or {}
    elif args.staged_index_quarantine:
        output = payload.get("shared_index_quarantine") or {}
    elif args.convergence:
        output = payload.get("transaction_convergence") or {}
    elif args.workspace_bloat_pressure:
        governor = payload.get("derived_state_bloat_governor") or {}
        output = governor.get("workspace_bloat_pressure") if isinstance(governor, dict) else {}
    elif args.runtime_artifact_lifecycle:
        output = payload.get("runtime_artifact_lifecycle") or {}
    elif args.github_push_bloat_gate:
        governor = payload.get("derived_state_bloat_governor") or {}
        output = governor.get("github_push_bloat_gate") if isinstance(governor, dict) else {}
    elif args.derived_artifact_policy:
        governor = payload.get("derived_state_bloat_governor") or {}
        output = governor.get("derived_artifact_policy") if isinstance(governor, dict) else {}
    elif args.explore_execute_review:
        seed_payload = load_autonomous_seed_payload(Path(args.repo_root), args.external_pattern_seed)
        output = build_explore_execute_review_runtime_closeout(
            payload,
            seed_payload=seed_payload,
            seed_id=args.external_pattern_seed,
            selector_surface=args.selector_surface,
            blocked_primary_continuation_receipt=blocked_primary_receipt,
        )
    elif args.bloat_governor:
        output = payload.get("derived_state_bloat_governor") or {}
    elif payload.get("schema") == "mission_transaction_landing_preflight_timeout_v0":
        output = payload
    else:
        output = payload if args.full else compact_mission_transaction_landing_preflight(payload)
    if args.attention_frame:
        command = " ".join(
            shlex.quote(part)
            for part in [
                "./repo-python",
                "tools/meta/control/mission_transaction_preflight.py",
                *raw_argv,
            ]
        )
        attention_event = record_attention_event(
            Path(args.repo_root),
            frame_id=args.attention_frame,
            event_type="mutation_boundary_observed",
            command=command,
            payload=payload,
            metadata={"surface_command": "mission_transaction_preflight"},
            return_error=True,
        )
        if isinstance(output, dict) and attention_event:
            output = dict(output)
            frame_id = attention_event.get("frame_id")
            output["attention_event"] = {
                "schema_version": attention_event.get("schema_version"),
                "status": attention_event.get("status") or "unknown",
                "event_id": attention_event.get("event_id"),
                "frame_id": frame_id,
                "frame_id_requested": attention_event.get("frame_id_requested"),
                "surface_id": attention_event.get("surface_id"),
                "event_type": attention_event.get("event_type"),
                "error_class": attention_event.get("error_class"),
                "error": attention_event.get("error"),
                "attention_state_command": f"./repo-python kernel.py --attention-state {frame_id} --band flag"
                if frame_id
                else None,
            }
            output["attention_delta"] = attention_event.get("attention_delta") or {}
    compact_default_output = (
        not args.full
        and not any(
            (
                args.convergence,
                args.reconcile_plan,
                args.staged_index_quarantine,
                args.control_summary,
                args.autonomous_edit_gate,
                args.landing_bankruptcy_summary,
                args.bloat_governor,
                args.workspace_bloat_pressure,
                args.runtime_artifact_lifecycle,
                args.github_push_bloat_gate,
                args.closeout_git_state,
                args.derived_artifact_policy,
                args.explore_execute_review,
            )
        )
        and isinstance(output, dict)
        and output.get("output_profile") == "compact"
    )
    if compact_default_output:
        print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    if args.fail_on_status:
        status = str((payload.get("landing_decision") or {}).get("status") or "")
        if STATUS_SEVERITY.get(status, -1) >= STATUS_SEVERITY[args.fail_on_status]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
