# Exercise four copied tooling primitives

> **In plain terms.** Small helper tools can fail on odd input, so they need trying on known cases. This check loads four copied helpers and gives them small example inputs. It divides the labels from two evidence lists into shared, missed and extra ones, edits a temporary document, tidies names, and notes a badly formed entry as a gap when reading sample files. The result is a status with findings, and only the step that divides the labels is checked by a mathematical proof against written rules, with the rest of the component outside that proof. These examples do not show that the inputs are true, that edits are right in meaning, or that predictions will succeed.

This fixture loads four copied modules and checks their output on small inputs. The observer diff divides evidence IDs into overlap, missed and extra sets and compares prediction rows; malformed rows without the required key are skipped. A patch helper applies `set`, `merge` and `append` to a temporary document. An identity helper normalizes lane names and derives IDs. A parser records coverage for synthetic miner, spine and prediction artifacts.

The negative cases check, among other things, that traversing a scalar during a patch raises an error, a stock record without its identity is refused, and a malformed tuple appears as a parser coverage gap.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_tools_tail_primitives_capsule run \
  --input fixtures/first_wave/batch8_tools_tail_primitives_capsule/input \
  --out .microcosm/component-guides/batch8_tools_tail_primitives_capsule \
  --acceptance-out .microcosm/component-guides/batch8_tools_tail_primitives_capsule/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

The evidence-ID exercise calls a [Dafny-verified partition core](../formal/components/evidence_diff/README.md). For the supplied finite ID sequences, it identifies IDs present in either or both inputs and the last occurrence in each. Python normalizes IDs, sorts and projects rows; prediction comparison and the other three primitives are outside this proof.

The direct fixture calls this core. Separately, `make component-replays` applies the [shared admission check](../formal/replay/README.md) to the component replay’s captured observations.

## Limits

These are fixture-level checks of the functions, not evidence that the input observations are true, edits are semantically correct, or predictions will succeed. The patch helper’s operations should not be assumed to implement all of JSON Patch.

## Sources

[src/microcosm_core/organs/batch8_tools_tail_primitives_capsule.py](../src/microcosm_core/organs/batch8_tools_tail_primitives_capsule.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/batch8_tools_tail_primitives_capsule/input/), [tests](../tests/test_batch8_tools_tail_primitives_capsule.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch8_tools_tail_primitives_capsule_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). For comparison, see [RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902).
