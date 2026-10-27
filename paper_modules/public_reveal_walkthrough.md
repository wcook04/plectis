# Check a public walkthrough against its evidence

The walkthrough validator checks audience-specific claim rows and their links to public evidence, including runtime and source references. It produces a board and findings to help a reader follow a claim to supporting material.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.public_reveal_walkthrough run \
  --input fixtures/first_wave/public_reveal_walkthrough/input \
  --out .microcosm/component-guides/public_reveal_walkthrough \
  --acceptance-out .microcosm/component-guides/public_reveal_walkthrough/acceptance.json
```

Inspect `.microcosm/component-guides/public_reveal_walkthrough/public_reveal_walkthrough_result.json` for the result and findings.

The fixture includes deliberate overclaims and missing-evidence examples. A passing fixture result means those checks observed the expected failures, not that every input row was accepted.

## What the result means

A walkthrough that claims a capability without a matching evidence route is rejected. A passing walkthrough does not establish private-system equivalence or authorize a release.

Related reading: [Command Line Interface Guidelines](https://clig.dev/), [progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/), [W3C PROV](https://www.w3.org/TR/prov-overview/), [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/).

## Verification

`validate_walkthrough` passes the observed budget and normalized steps to the [proved walkthrough core](../formal/components/walkthrough_validation/README.md). It accepts exactly when the declared budget is positive and at most ten minutes, there are at least five steps, four distinct commands and four distinct evidence references, and each step has a command, an inspect reference and an evidence reference. Python supplies the normalized inputs; separate host checks cover optional time intervals and reference locations. The proof concerns the declared budget, not elapsed time, and does not establish that references substantiate their claims.

The example uses that core. `make component-replays` separately applies the shared [replay admission check](../formal/replay/README.md) to the exported bundle.

## Source

[Implementation](../src/microcosm_core/organs/public_reveal_walkthrough.py) · [input](../fixtures/first_wave/public_reveal_walkthrough/input) · [tests](../tests/test_public_reveal_walkthrough.py) · [historical sample result](../receipts/acceptance/first_wave/public_reveal_walkthrough_fixture_acceptance.json) · [component record](../core/paper_module_capsules.json).
