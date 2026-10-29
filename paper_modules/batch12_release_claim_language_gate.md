# Test a release claim-language gate

> **In plain terms.** Before a project is released, its documents need checking for risky claims about what the project is or can do. It writes two short sample documents, one warning against claiming the project is open source (its code shared openly) and one plainly claiming it is ready for real-world use. It runs a simplified public stand-in for the original gate, which looks for listed risky phrases in both, and records which phrases matched and what the gate decided. The readiness claim is blocked, so someone can check that the gate catches that kind of wording.

This fixture writes two sample documents in temporary directories: one warns against an open-source claim, while the other affirmatively claims production readiness. It runs the declared public fallback claim-language gate against both. The result records matched phrase IDs, gate status and the assert-clear exit code.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch12_release_claim_language_gate run \
  --input fixtures/first_wave/batch12_release_claim_language_gate/input \
  --out .microcosm/component-guides/batch12_release_claim_language_gate/result \
  --acceptance-out .microcosm/component-guides/batch12_release_claim_language_gate/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

The affirmative production-ready claim is blocked; the assert-clear path returns exit code 2. The fixture also checks a public-facing private-control-plane claim and rejects unsafe fixture filenames. A phrase match is a limited rule-based check, not a general review of every claim.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

Runs the declared public fallback claim-language gate, which this checkout uses in place of the original source, on two sample documents and rejects the one claiming production readiness; an undeclared missing source blocks the check.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch12_release_claim_language_gate.py), [fixture input](../fixtures/first_wave/batch12_release_claim_language_gate/input/release_gate_fixture.json), and [focused tests](../tests/test_batch12_release_claim_language_gate.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch12_release_claim_language_gate_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch12_release_claim_language_gate.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

The FTC’s [advertising substantiation statement](https://www.ftc.gov/legal-library/browse/ftc-policy-statement-regarding-advertising-substantiation) is background, not a claim that this tool establishes legal compliance.
