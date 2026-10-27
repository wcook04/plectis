# Pattern binding validation

Checks pattern rows and their source, reference and authority-chain records, producing a validation result and related receipts.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.pattern_binding_contract validate --input fixtures/first_wave/pattern_binding_contract/input --out .microcosm/component-guides/pattern_binding_contract --card
```

Inspect the status and findings in `.microcosm/component-guides/`; the linked result below is a historical sample.

## What it checks

A pattern binding links a pattern ID to its governing standard, source references and limits. In the fixture, `pb_valid_synthetic_binding` points to `capsule.synthetic_pattern_contract`, a provenance record for the regression harness. The validator checks required fields, reference resolution, duplicate conflicts and private-body markers. It rejects missing references, conflicting duplicate patterns, private source bodies and public claims that exceed their evidence. A separate route-readiness bundle checks whether selector rows resolve through their owning routes.

## Limits

A passing binding is a consistent record under these checks; it does not prove that the pattern is useful or that copied source is correct.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported substrate bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/pattern_binding_contract.py) and [focused tests](../tests/test_pattern_binding_contract.py)
- [Example input](../fixtures/first_wave/pattern_binding_contract/input/patterns.jsonl) and [historical sample result](../receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json)
- [Component JSON record](./pattern_binding_contract.json) and [canonical capsule](../core/paper_module_capsules.json)
- [Supporting implementation](../src/microcosm_core/macro_tools/pattern_route_readiness.py)

Related provenance frameworks include [in-toto](https://in-toto.io/), [SLSA](https://slsa.dev/spec/) and [W3C PROV](https://www.w3.org/TR/prov-overview/).
