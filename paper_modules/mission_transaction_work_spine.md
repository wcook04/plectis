# Work-landing transaction replay

> **In plain terms.** Workers saving changes to one project can claim the same files or build on an outdated version. This component reads a made-up example of workers' claims on files, the project version each expected, which tasks wait on which, and rules for a limited save. It lists the active claims, compares each with its files and expected version, and tests whether finished tasks unlock waiting ones and the save rules are met. The output is a verdict with findings, and it rejects a claim built on an outdated version or two claims on one file. It uses supplied records only, never the live private work record, and passing is not permission to save or release.

Validates a public work-transaction fixture containing path claims, dependencies, preflight and checkpoint policy, and writes receipts.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.mission_transaction_work_spine run --input fixtures/first_wave/mission_transaction_work_spine/input --out /tmp/plectis-component-guides/mission_transaction_work_spine/out
```

Inspect the status and findings under `/tmp/plectis-component-guides/mission_transaction_work_spine/out`. The command also writes a preflight receipt under `/tmp/plectis-component-guides/mission_transaction_work_spine/receipts/preflight/`; the linked result below is a historical sample.

## What it checks

The replay reconstructs an active-claims snapshot using imported public-safe Work Ledger code. It checks claims against paths and expected parent state, dependency unlocks and scoped checkpoint policy. Tests change a same-path conflict to a disjoint claim and change an expected parent to check that the verdict follows the input. A stale expected parent or conflicting claim is rejected.

## Limits

The replay checks supplied snapshots and policies. It does not operate the live private ledger or establish that a commit landed. A preflight result is not permission to commit or release.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported work-transaction bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/mission_transaction_work_spine.py) and [focused tests](../tests/test_mission_transaction_work_spine.py)
- [Example input](../fixtures/first_wave/mission_transaction_work_spine/input) and [historical sample result](../receipts/first_wave/mission_transaction_work_spine/claim_preflight_result.json)
- [Component JSON record](./mission_transaction_work_spine.json) and [canonical capsule](../core/paper_module_capsules.json)
