"""Card calibration gate -- public one-line claims stay isomorphic to evidence.

Reader-belief parity: a fast public reader's belief after scanning a component's
one-line must not be materially stronger OR weaker than its evidence class
warrants. This is the durable guard installed by the 2026-06-14 calibration wave
(commits fe224427a0 + 15431bef31). It is not generic word-policing -- it binds a
small set of unambiguous execution verbs to the evidence class that licenses
them, in both directions.

* OVERSELL guard: an ``algorithmic_projection`` organ does projection /
  consistency checks over recorded or synthetic data -- it performs no real
  runtime action on a live target. Its one-line must not assert an unqualified
  real-runtime verb (recomputes / authorizes / proves / compiles). Such a verb
  is permitted only when a qualifier (recorded / synthetic / declared / replay /
  fixture / copied ...) marks it as acting over recorded data, not a live target.
  This is the exact failure the wave corrected (e.g. "recomputes benchmark
  verdicts", "proves each change ... before it was allowed to run").

* UNDERSELL guard: a real-execution class (``bounded_runtime_computation`` /
  ``external_subprocess_witness``) must signal that real work happens (runs /
  imports / executes / compiles / measures / replays ...), so a sharp reader
  does not misfile a real engine with the thin projection linters. This is the
  inverse failure the wave corrected (e.g. a real work-ledger engine or a live
  Lean probe whose one-line read like a passive fixture check).

If either guard fails, fix the SOURCE one-line in
``core/component_public_synopses.json`` (or correct the organ's evidence class if
the code genuinely changed) -- do not weaken this gate.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

PROJECTION_ONLY = {"algorithmic_projection"}
REAL_EXECUTION = {"bounded_runtime_computation", "external_subprocess_witness"}

# Verbs that assert a real runtime action a projection-only organ cannot perform.
OVERCLAIM_VERBS = ("recomputes", "authorizes", "proves", "compiles")
# Markers that defuse an overclaim verb by scoping it to recorded/synthetic data.
QUALIFIERS = (
    "recorded", "declared", "synthetic", "replay", "fixture",
    "copied", "make-believe", "stated", "projection",
)
# Any of these in a real-execution one-line signals the real work to a reader.
EXEC_SIGNALS = (
    "runs", "imports", "executes", "compiles", "recomputes", "measures",
    "computes", "replays", "records", "drafts", "binds", "lean",
    "gridworld", "forward pass",
)


def _load() -> tuple[dict[str, str], dict[str, dict]]:
    syn = json.loads((CORE / "component_public_synopses.json").read_text())["synopses"]
    reg = {
        row["organ_id"]: row
        for row in json.loads((CORE / "organ_registry.json").read_text())["implemented_organs"]
    }
    return syn, reg


def test_projection_one_lines_make_no_unqualified_execution_claim() -> None:
    """OVERSELL guard: projection-only cards must not claim live execution."""
    syn, reg = _load()
    violations = []
    for organ_id, line in syn.items():
        if reg.get(organ_id, {}).get("evidence_class") not in PROJECTION_ONLY:
            continue
        low = line.lower()
        hits = [verb for verb in OVERCLAIM_VERBS if verb in low]
        if hits and not any(q in low for q in QUALIFIERS):
            violations.append(f"  {organ_id} {hits}: {line}")
    assert not violations, (
        "algorithmic_projection one-lines assert unqualified real-runtime verbs; "
        "add a qualifier (recorded/synthetic/...) or soften the verb:\n"
        + "\n".join(violations)
    )


def test_real_execution_one_lines_signal_the_real_work() -> None:
    """UNDERSELL guard: real-execution cards must name the real work."""
    syn, reg = _load()
    violations = []
    for organ_id, line in syn.items():
        if reg.get(organ_id, {}).get("evidence_class") not in REAL_EXECUTION:
            continue
        if not any(sig in line.lower() for sig in EXEC_SIGNALS):
            violations.append(f"  {organ_id} [{reg[organ_id]['evidence_class']}]: {line}")
    assert not violations, (
        "real-execution organs hide their work in the one-line; "
        "name the execution (runs/imports/executes/measures/...):\n"
        + "\n".join(violations)
    )
