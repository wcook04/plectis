# Classify undeclared library symbols

> **In plain terms.** A proof attempt may lean on a library fact that was never declared as allowed. This component is given records of proof attempts, each listing the library names used, the facts allowed and the facts cited, plus an index of known facts. Citing a fact outside the allowed list counts as a budget violation and takes priority; otherwise a known full library name on neither list counts as undeclared. Each record gets a label and a review outcome, showing someone which attempts leaned on facts nobody had listed. The labels depend on the supplied index and the names pulled from each proof, and are advice rather than proof checking.

This classifier compares qualified symbols in public observations with a premise index and each observation’s allowed and cited premise IDs. It records a classification and review outcome for each row.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.undeclared_library_prior_symbol_classifier run \
  --input fixtures/first_wave/undeclared_library_prior_symbol_classifier/input \
  --out .microcosm/component-guides/undeclared_library_prior_symbol_classifier \
  --acceptance-out .microcosm/component-guides/undeclared_library_prior_symbol_classifier/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

A cited unallowed premise takes precedence as a premise-budget violation; otherwise a known qualified symbol absent from both lists is classified as an undeclared library prior. Unqualified names are handled separately. A row that omits escalation for a known undeclared symbol is rejected.

## Limits

The result depends on the supplied index and extracted symbols. It is advisory metadata, not proof checking or a claim that an unqualified name resolves to a particular declaration.

## Verification

Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/undeclared_library_prior_symbol_classifier.py) · [Example input](../fixtures/first_wave/undeclared_library_prior_symbol_classifier/input/) · [Tests](../tests/test_undeclared_library_prior_symbol_classifier.py) · [Historical sample result](../receipts/first_wave/undeclared_library_prior_symbol_classifier/undeclared_library_prior_symbol_classifier_result.json) · [JSON record](undeclared_library_prior_classifier.json)

Background: [Mathlib overview](https://leanprover-community.github.io/mathlib-overview.html).
