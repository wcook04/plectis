# Validate a registry of reusable reasoning procedures

> **In plain terms.** A list of reusable reasoning procedures can mark an entry as active without any record that it ever changed a decision. This check reads descriptions of each procedure, with a status, and the use records cited for the active ones. It checks each entry has the required fields and a recognised status, and that every active entry's use record cites evidence that can be found. It writes a result and a summary sheet, so a maintainer can find unsupported entries before presenting them as tested.

`cognitive_operator_registry` checks JSON descriptions of reasoning procedures and the records cited for their use. An entry marked `active` must include a use record with resolvable references to the claimed change in a decision. This helps a registry maintainer find unsupported entries before presenting them as tested procedures.

## Run the example

From the repository root, with Python 3.11 or later:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.cognitive_operator_registry run \
  --input fixtures/first_wave/cognitive_operator_registry/input \
  --out .microcosm/component-guides/cognitive_operator_registry \
  --acceptance-out .microcosm/component-guides/cognitive_operator_registry/acceptance.json
```

The output includes a result, a summary board and a validation record. A passing run means the supplied positive records satisfy the validator and the required negative cases produce their expected errors.

## What this checks

The validator requires descriptive fields and recognised statuses, resolves active entries' use records, and checks the references in `cognition_delta_evidence`. A test replaces one reference with `cognition_delta_evidence://fabricated/not-present`; the run then blocks with `COGOP_COGNITION_DELTA_EVIDENCE_UNRESOLVABLE`. Other cases exercise duplicate entries, missing use records and unsupported permission claims. Source-copy manifests are checked by digest.

## Limits

Resolving a record establishes that its cited reference exists, not that the procedure caused an improvement or is generally correct. The fixture does not execute the listed procedures. Its content scan uses configured exclusions; it is not a guarantee that every secret can be detected.

## Verification

The direct example does not invoke the shared gate. In `make component-replays`, this component’s registered route passes through the [Dafny replay admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement over host-supplied observations. It does not prove this component’s algorithm.

## Sources

- [Implementation](../src/microcosm_core/organs/cognitive_operator_registry.py), [inputs](../fixtures/first_wave/cognitive_operator_registry/input) and [tests](../tests/test_cognitive_operator_registry.py).
- [Historical result](../receipts/first_wave/cognitive_operator_registry/cognitive_operator_registry_result.json) and [canonical component descriptions](../core/paper_module_capsules.json).
- [W3C PROV](https://www.w3.org/TR/prov-overview/) describes provenance records; it does not certify these procedures.
