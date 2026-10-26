"""
[PURPOSE]
- Teleology: Execute the compiled observe plan by checkpointing pipeline state around the bridge-session dispatch boundary.
- Mechanism: Resolve launch-profile/runtime settings, optionally emit a manual-dispatch preview, and otherwise invoke `run_observe_plan.run_once()` while recording cycle events and observe-manifest metadata.

[INTERFACE]
- Exports: execute_observe.
- Reads: The compiled `observe_plan.json`, runtime launch defaults, and controller state for the active cycle.
- Writes: Dispatch boundary state fields, cycle event records, and observe-session/manifest metadata; may launch bridge work through the observe runner.

[FLOW]
- Resolve the compiled plan and launch profile -> checkpoint the dispatch boundary -> either emit manual-dispatch guidance or call the observe runner -> persist returned observe session metadata for later processing.

[DEPENDENCIES]
- Couples: `system.lib.pipeline.stage_extract` supplies cycle timeline/event helpers that make the dispatch boundary recoverable.
- Couples: `system.lib.pipeline.stage_select._resolve_observe_record_path` resolves the authoritative observe-manifest path after dispatch.
- Couples: `tools.meta.apply.run_observe_plan` owns the actual observe-session execution once this stage hands off.

[CONSTRAINTS]
- Guarantee: The pipeline state is checkpointed to `observe_dispatched` before the long-running observe dispatch, so later recovery surfaces can resume from disk.
- Non-goal: This module does not compile the plan or process receipts; it only launches or previews stage-5 observe execution.
- When-needed: Open when a pipeline loop needs the exact dispatch boundary between a compiled observe plan and the long-running observe session runner.
- Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/pipeline/stage_process.py; system/lib/pipeline_recovery.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from system.lib.pipeline.stage_extract import (
    _cycle_dir_rel,
    _cycle_timeline_rel,
    _phase_id_from_state,
    _record_cycle_event,
)
from system.lib.pipeline.stage_select import _resolve_observe_record_path


# ---------------------------------------------------------------------------
# Stage 5: Execute observe plan
# ---------------------------------------------------------------------------
def execute_observe(
    state: dict,
    *,
    bridge_enabled: bool = False,
    provider: str = "chatgpt",
    launch_profile: str | None = None,
    state_path: Path | None = None,
) -> dict | None:
    """
    [ACTION]
    - Teleology: Launch or preview execution of the currently compiled observe plan for the active cycle.
    - Mechanism: Resolve the plan path and launch profile, checkpoint dispatch metadata, optionally print a manual-dispatch command when bridge is disabled, and otherwise call `run_once()` from the observe runner.
    - Reads: `state["observe_plan_path"]`, pipeline runtime config, and the compiled observe plan JSON.
    - Writes: Pipeline state checkpoints, cycle event log entries, and observe-session metadata; may spawn the long-running observe runner.
    - Guarantee: Returns the observe-runner result when dispatch occurs and otherwise leaves a recoverable `observe_dispatched` checkpoint on disk.
    - Fails: Import failures for the observe runner return `None`; subprocess/runtime failures from `run_once()` propagate through its result path rather than being handled here.
    - When-needed: Open when a caller needs the stage-5 observe execution contract, including the manual-dispatch fallback and checkpoint timing.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/pipeline/stage_process.py::process_results; system/lib/pipeline_recovery.py
    - Navigation-group: kernel_lib
    """
    from seed_pipeline import REPO_ROOT, _utc_now, _log, save_state, save_state_if_not_stale
    from pipeline_control import normalize_launch_profile, pipeline_runtime_config

    plan_path = REPO_ROOT / state["observe_plan_path"]

    runtime_cfg = pipeline_runtime_config(REPO_ROOT)
    effective_launch_profile = normalize_launch_profile(
        launch_profile,
        default=str(runtime_cfg["default_launch_profile"]),
    )

    if not bridge_enabled:
        print("[INFO] Bridge not enabled. Observe plan compiled at:", plan_path)
        print(
            "[INFO] To dispatch: python3 run_observe.py --plan",
            state["observe_plan_path"],
            "--bridge --provider",
            provider,
            "--launch-profile",
            effective_launch_profile,
        )
        state["stage"] = "observe_dispatched"
        state["current_cycle_timeline_path"] = _cycle_timeline_rel(state)
        _record_cycle_event(
            state,
            "observe_dispatch_skipped",
            provider=provider,
            launch_profile=effective_launch_profile,
            reason="bridge_disabled",
            observe_plan_path=state.get("observe_plan_path"),
        )
        _log(state, "execute_observe", "Plan compiled but bridge not enabled. Manual dispatch needed.")
        if state_path is not None:
            save_state_if_not_stale(state, state_path)
        return None

    # Import the observe machinery
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from tools.meta.apply.run_observe_plan import run_once
    except ImportError as e:
        print(f"[ERROR] Cannot import observe machinery: {e}", file=sys.stderr)
        state["stage"] = "observe_dispatched"
        _log(state, "execute_observe", f"Import failed: {e}")
        return None

    # Build paths for run_once
    plan = json.loads(plan_path.read_text())
    result_note_path = plan.get("result_note_path", str(Path(state["phase_dir"]) / f"Pass {state['cycle'] + 1} Observe Result.md"))

    # Ensure dump_dir exists before dispatch
    dump_dir = plan.get("dump_dir", f"tools/meta/apply/observe_dumps/{_phase_id_from_state(state)}_cycle_{state['cycle']}")
    (REPO_ROOT / dump_dir).mkdir(parents=True, exist_ok=True)

    print(f"[BRIDGE] Dispatching observe plan via {provider}...")
    print(f"[BRIDGE] Dump dir: {dump_dir}")
    print(f"[BRIDGE] This may take several minutes per probe group.")

    # Persist the dispatch boundary before the long-running bridge call
    state["stage"] = "observe_dispatched"
    state["observe_session_id"] = None
    state["observe_manifest_path"] = None
    state["observe_dispatch_started_at"] = _utc_now()
    state["current_cycle_timeline_path"] = _cycle_timeline_rel(state)
    _record_cycle_event(
        state,
        "observe_dispatch_started",
        provider=provider,
        launch_profile=effective_launch_profile,
        observe_plan_path=state.get("observe_plan_path"),
        dump_dir=dump_dir,
        bridge_workers="auto",
    )
    _log(state, "execute_observe", f"Bridge dispatch started via {provider}")
    if state_path is not None:
        save_state(state, state_path)

    # Execute with run_once
    result = run_once(
        repo_root=REPO_ROOT,
        plan_path=plan_path,
        result_path=REPO_ROOT / result_note_path,
        history_dir=REPO_ROOT / "tools/meta/apply/observe_history",
        sentence_count=None,
        sticky_dump_dir=False,
        bridge_enabled=True,
        bridge_provider=provider,
        bridge_max_chars=400000,
        bridge_timeout_s=360.0,
        bridge_workers="auto",
        launch_profile=effective_launch_profile,
        cancel_event=threading.Event(),
    )

    if result:
        state["observe_session_id"] = result.get("observe_id")
        state["observe_manifest_path"] = _resolve_observe_record_path(state, result=result)

    state["stage"] = "observe_dispatched"
    _record_cycle_event(
        state,
        "observe_dispatch_checkpointed",
        observe_session_id=result.get("observe_id") if result else None,
        observe_manifest_path=state.get("observe_manifest_path"),
        dump_dir=dump_dir,
    )
    _log(state, "execute_observe", f"Session dispatched: {result.get('observe_id', 'unknown')}")
    if state_path is not None:
        save_state_if_not_stale(state, state_path)
    return result
