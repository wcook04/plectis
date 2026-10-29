# Exercise governance and compiler checks

> **In plain terms.** Rules for which changes and releases are allowed only help if they really refuse bad requests. Its input is sample plans and requests, some deliberately broken, plus copies of the rule-checking code. It runs each rule on them, refusing for example a malformed plan for observing then changing something and a choice of what to publish that breaks a hard exclusion, and checks each copy against its record. The output lists each check and its outcome so someone can see which rules behave as intended. One check, which sizes interface lanes, stays blocked as the test expects, and matching copies do not show the copied logic is correct.

This capsule runs bounded examples of governance and compiler logic against public fixtures. The checks include mutation intent, observe/apply plans, release blockers, publication path contracts, receipt reuse, dependency waves and time horizons. It records source-copy digest and anchor checks alongside computed negative-case results.

For example, a malformed observe/apply artifact and a publication selector that violates a hard exclusion are rejected by their respective checks. One check of a solver that assigns widths to interface lanes remains blocked: its exercise still needs to be bound to the existing Batch 9 source. The test expects that deferral while the other listed mechanisms pass. The run does not approve a release, mutate a live ledger or establish whole-system correctness. Source-copy identity is distinct from correctness of the copied logic.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch10_governance_compilers_capsule \
  run --input fixtures/first_wave/batch10_governance_compilers_capsule/input \
  --out .microcosm/component-guides/batch10_governance_compilers_capsule/output \
  --acceptance-out .microcosm/component-guides/batch10_governance_compilers_capsule/acceptance.json
```

The result lists the individual mechanism checks and the deferred binding under `exercise`. It is written under `.microcosm/component-guides/batch10_governance_compilers_capsule/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the governance exercises and source-digest checks; they do not formally prove the governance algorithms. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported governance bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/batch10_governance_compilers_capsule.py) · [fixture input](../fixtures/first_wave/batch10_governance_compilers_capsule/input/) · [tests](../tests/test_batch10_governance_compilers_capsule.py) · [sample result (historical)](../receipts/first_wave/batch10_governance_compilers_capsule/batch10_governance_compilers_capsule_result.json) · [JSON record](batch10_governance_compilers_capsule.json).

[Open Policy Agent](https://www.openpolicyagent.org/docs/latest) is related work on policy evaluation.
