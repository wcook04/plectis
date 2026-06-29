"""
Public macro-tool imports used by Microcosm organs.

[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: None beyond import-time package markers.
- Reads: call arguments, module constants, imported helpers.
- Writes: return values and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""

__all__ = [
    "agent_execution_trace",
    "agent_session_attribution",
    "bridge_resume",
    "command_output_projection",
    "command_output_sidecar",
    "continuation_packet",
    "controller_heartbeat",
    "finance_eval_spine",
    "lab_evolve_replay",
    "mission_transaction_preflight",
    "pattern_route_readiness",
    "work_landing",
    "work_landing_control_spine",
]
