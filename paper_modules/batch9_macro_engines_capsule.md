# Exercise ten workflow checks

This fixture checks ten workflow mechanisms on bounded public examples: lineage, approval claims, Python AST indexing, mission-graph compilation, dependency pins, configuration authority, host pressure, doctrine enrichment, worker gates and milestone accounting. It records each exercise and checks the source manifest and required anchors. Some exercises call copied functions; the mission-graph example instead runs a local topology calculation conditioned on anchors in the copied graph source.

The negative fixtures include a mission graph with a missing target, a changed dependency pin, and a worker request touching a forbidden surface. They also test that a self-loop in lineage is pruned and that a syntax error becomes an indexing gap. The tests perturb copied bodies and inputs to check that several verdicts depend on execution rather than labels alone.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch9_macro_engines_capsule run \
  --input fixtures/first_wave/batch9_macro_engines_capsule/input \
  --out .microcosm/component-guides/batch9_macro_engines_capsule \
  --acceptance-out .microcosm/component-guides/batch9_macro_engines_capsule/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

Fixture exercises and source-anchor checks do not formally prove the workflow algorithms. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

These examples test selected copied functions and source-backed local logic. They do not establish live deployment safety, complete coverage, or correctness for arbitrary repositories.

## Sources

[src/microcosm_core/organs/batch9_macro_engines_capsule.py](../src/microcosm_core/organs/batch9_macro_engines_capsule.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/batch9_macro_engines_capsule/input/), [tests](../tests/test_batch9_macro_engines_capsule.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch9_macro_engines_capsule_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json).
