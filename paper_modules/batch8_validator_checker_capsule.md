# Inspect validator source and available checker exercises

> **In plain terms.** A pass from a project's checking program means little until someone knows what it was able to check where it ran. This component is given a copy of that checking program's written code. It reports on six groups of checks, such as required markers in the code, and runs the checkers themselves only when the larger system the code was copied from is present. In a public copy it confirms only the required markers and labels the other groups as source-only, so a reader can tell which results come from running checkers.

This fixture examines a copied validator module and reports six checker groups, including source anchors, status policy, private-boundary scanning, specimen checks, release-gate checks and an entrypoint witness. What a passing row means depends on the available runtime.

With the parent macro state available and a non-bundle fixture, the evaluator runs the checker exercises. For an exported bundle or a public checkout without that state, it checks the source anchor matrix and marks the other rows `public_runtime_source_only`: those rows provide source-anchor and digest evidence, not executed checker results. Removing a required validator source or anchor is a negative case.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_validator_checker_capsule run \
  --input fixtures/first_wave/batch8_validator_checker_capsule/input \
  --out .microcosm/component-guides/batch8_validator_checker_capsule \
  --acceptance-out .microcosm/component-guides/batch8_validator_checker_capsule/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

Source checks and available checker exercises do not formally prove the validator algorithms. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

Checks the copied checker sources' anchors and digests and rejects a missing validator source or a bypassed entry point; the other five checker groups run only when the parent runtime state is available.

## Sources

[src/microcosm_core/organs/batch8_validator_checker_capsule.py](../src/microcosm_core/organs/batch8_validator_checker_capsule.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/batch8_validator_checker_capsule/input/), [tests](../tests/test_batch8_validator_checker_capsule.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch8_validator_checker_capsule_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). Related context: [JSON Schema](https://json-schema.org/).
