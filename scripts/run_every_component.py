# SPDX-FileCopyrightText: 2026 Will Cook
# SPDX-License-Identifier: CC-BY-4.0
"""Run every registered component and report the complete outcome breakdown.

The paper's ``What the collection contains`` section reports an inventory: how
many components exist and how their evidence is routed.  It does not report what
happens when every one of them is actually run.  This script produces that
figure.

Design notes that matter for reading the result:

* The component set is *the whole registry*, not a sample.  There is no
  selection step, so there is nothing for the author to have selected.
* Every component's registered ``validator_command`` writes its receipts into
  the repository by default.  This script redirects ``--out`` and
  ``--acceptance-out`` into a scratch directory so a run cannot overwrite the
  stored receipts it is being compared against, and then verifies that the
  checkout is unchanged afterwards.
* Outcomes are classified by a rule fixed before the run (see ``classify``).
  A component that exits non-zero is not automatically a defect: a declared
  refusal is also a non-zero exit for several components.  The two are
  separated by inspecting the acceptance record rather than the exit code
  alone.

Usage::

    PYTHONPATH=src python3 scripts/run_every_component.py --out-dir /tmp/plectis-runall
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "core" / "organ_registry.json"

# Outcome vocabulary, fixed before the run.
PASS = "pass"
DECLARED_REFUSAL = "declared_refusal"
BLOCKED = "blocked"
ERROR = "error"
UNRUNNABLE = "unrunnable"


def load_components() -> list[dict]:
    registry = json.loads(REGISTRY.read_text())
    return list(registry["implemented_organs"])


def redirect(command: str, scratch: Path, organ_id: str) -> str:
    """Point every output flag at a per-component scratch directory."""
    target = scratch / organ_id
    target.mkdir(parents=True, exist_ok=True)
    command = re.sub(
        r"--out\s+\S+", f"--out {shlex.quote(str(target))}", command, count=1
    )
    command = re.sub(
        r"--acceptance-out\s+\S+",
        f"--acceptance-out {shlex.quote(str(target / 'acceptance.json'))}",
        command,
        count=1,
    )
    return command


def read_verdict(target: Path) -> tuple[dict, str]:
    """Find the component's own recorded verdict.

    Only 46 of the 88 components take an ``--acceptance-out`` flag.  The other
    42 record their verdict in a result or validation-receipt file written into
    the ``--out`` directory instead.  An earlier version of this script read
    only ``acceptance.json`` and therefore scored every non-zero exit from
    those 42 as an error, including components that had correctly *declared* a
    refusal.  That was a defect in this harness, not in the components, and it
    inflated the error count substantially.  Read whichever record the
    component actually wrote.
    """
    acceptance = target / "acceptance.json"
    if acceptance.exists():
        try:
            return json.loads(acceptance.read_text()), "acceptance.json"
        except json.JSONDecodeError:
            return {}, "acceptance.json (unparsable)"

    # Prefer an explicit result file, then a validation receipt, then any JSON
    # in the output directory that carries a top-level status field.
    candidates = sorted(target.glob("*_result.json")) + sorted(
        target.glob("*_validation_receipt.json")
    )
    candidates += [p for p in sorted(target.glob("*.json")) if p not in candidates]
    for path in candidates:
        try:
            record = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(record, dict) and ("status" in record or "accepted" in record):
            return record, path.name
    return {}, "no verdict record"


def classify(returncode: int, target: Path) -> tuple[str, str]:
    """Assign one outcome label. Returns (label, evidence)."""
    record, source = read_verdict(target)

    status = str(record.get("status", "")).lower()
    accepted = record.get("accepted")

    if status in {"refused", "refusal", "declared_refusal"}:
        return DECLARED_REFUSAL, f"exit {returncode}; status={status} ({source})"
    if status == "blocked" or accepted is False:
        return BLOCKED, f"exit {returncode}; status={status or 'accepted=false'} ({source})"
    if returncode == 0 and (accepted is True or status in {"accepted", "pass", "ok"}):
        return PASS, f"exit 0; status={status or 'n/a'} ({source})"
    if returncode == 0:
        return PASS, f"exit 0; status={status or 'n/a'} ({source})"
    return ERROR, f"exit {returncode}; status={status or 'none'} ({source})"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/tmp/plectis-runall")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--only", default=None, help="substring filter on organ_id")
    args = parser.parse_args()

    scratch = Path(args.out_dir)
    scratch.mkdir(parents=True, exist_ok=True)

    before = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout

    components = load_components()
    if args.only:
        components = [c for c in components if args.only in c["organ_id"]]

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO / "src")

    results = []
    for index, component in enumerate(components, start=1):
        organ_id = component["organ_id"]
        command = component.get("validator_command", "")
        target = scratch / organ_id

        if not command.startswith("python -m"):
            results.append(
                {
                    "organ_id": organ_id,
                    "outcome": UNRUNNABLE,
                    "evidence": "registry supplies no `python -m` validator command",
                    "seconds": 0.0,
                    "command": command,
                }
            )
            print(f"[{index:>2}/{len(components)}] {organ_id}: {UNRUNNABLE}")
            continue

        run_command = redirect(command, scratch, organ_id)
        run_command = run_command.replace("python -m", f"{sys.executable} -m", 1)

        start = time.time()
        try:
            proc = subprocess.run(
                run_command,
                shell=True,
                cwd=REPO,
                env=env,
                capture_output=True,
                text=True,
                timeout=args.timeout,
            )
            returncode, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            returncode, stdout, stderr = 124, "", "timeout"
        elapsed = time.time() - start

        outcome, evidence = classify(returncode, target)
        if returncode == 124:
            outcome, evidence = ERROR, f"timed out after {args.timeout}s"

        results.append(
            {
                "organ_id": organ_id,
                "evidence_class": component.get("evidence_class"),
                "evidence_strength_rank": component.get("evidence_strength_rank"),
                "outcome": outcome,
                "evidence": evidence,
                "returncode": returncode,
                "seconds": round(elapsed, 2),
                "command": run_command,
                "stderr_tail": stderr.strip()[-600:],
                "stdout_tail": stdout.strip()[-400:],
            }
        )
        print(f"[{index:>2}/{len(components)}] {organ_id}: {outcome} ({elapsed:.1f}s)")

    after = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout

    summary: dict[str, int] = {}
    for record in results:
        summary[record["outcome"]] = summary.get(record["outcome"], 0) + 1

    report = {
        "component_count": len(results),
        "summary": summary,
        "checkout_unchanged": before == after,
        "checkout_diff": "" if before == after else after,
        "python": sys.version.split()[0],
        "results": results,
    }
    report_path = scratch / "run_every_component.json"
    report_path.write_text(json.dumps(report, indent=2))

    print()
    print(f"components run : {len(results)}")
    for label in (PASS, DECLARED_REFUSAL, BLOCKED, ERROR, UNRUNNABLE):
        if label in summary:
            print(f"  {label:<18} {summary[label]}")
    print(f"checkout unchanged: {report['checkout_unchanged']}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
