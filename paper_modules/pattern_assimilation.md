# Pattern assimilation closeout check

Checks whether each landed component in an input set has a linked, same-lane closeout decision and writes a validation receipt.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.validators.acceptance validate-assimilation-bundle --input examples/pattern_assimilation_step/exported_assimilation_bundle --out .microcosm/component-guides/pattern_assimilation
```

Inspect the status and findings in `.microcosm/component-guides/`; the linked result below is a historical sample.

## What it checks

A decision can point to a refinement receipt naming an owner and artifact, or to a `nothing_to_refine` receipt with stewardship, next-lane and re-entry checks. The validator resolves those references and checks duplicate IDs. It rejects a landed row with a missing closeout or a dead receipt reference; a local refinement cannot claim global doctrine authority.

## Limits

The check establishes the recorded closeout contract for supplied rows. It does not establish that a refinement improved the system or that every lesson has been found.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported assimilation bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/validators/acceptance.py) and [focused tests](../tests/test_pattern_assimilation_step.py)
- [Example input](../examples/pattern_assimilation_step/exported_assimilation_bundle) and [historical sample result](../receipts/first_wave/pattern_assimilation_receipt.json)
- [Component JSON record](./pattern_assimilation.json) and [canonical capsule](../core/paper_module_capsules.json)

For context see [Hillside patterns](https://hillside.net/patterns/) and [W3C PROV](https://www.w3.org/TR/prov-overview/).
