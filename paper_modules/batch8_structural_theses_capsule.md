# Test a structural-thesis family with losses and controls

> **In plain terms.** A report on investment ideas can look better than it is when it shows only the ideas that worked. This check uses copied finance code to build made-up market claims, including winners, losers and a comparison case that should not count as a success. A validator rejects a set with only winners, and it flags a failed pattern promoted into the ideas to pursue and a comparison case relabeled as a confirmed claim. The output is a status with named findings, which shows whether the rules catch one-sided evidence.

This fixture builds a family of synthetic market theses using copied finance code and validates the resulting record. It includes winning and losing claims and a negative control, so the validator can check whether failed claims and controls remain visible in the sample.

A survivor-only family is rejected with findings including `SURVIVORSHIP_SAMPLE`, `NO_LOSER_FLOWED_THROUGH`, and `NO_NEGATIVE_CONTROL`. Separate mutations promote a refuted pattern into forward candidates or mark a control as a confirmed claim; the validator reports `FORWARD_GATE_BREACH` or `CONTROL_LEAK`, respectively.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_structural_theses_capsule run \
  --input fixtures/first_wave/batch8_structural_theses_capsule/input \
  --out .microcosm/component-guides/batch8_structural_theses_capsule \
  --acceptance-out .microcosm/component-guides/batch8_structural_theses_capsule/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

Tests of synthetic thesis records do not formally prove the finance algorithm or its predictions. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

Runs a synthetic thesis family through loss, control and forward-gate checks, rejecting a survivor-only sample, a promoted refuted pattern and a confirmed negative control.

## Sources

[src/microcosm_core/organs/batch8_structural_theses_capsule.py](../src/microcosm_core/organs/batch8_structural_theses_capsule.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/batch8_structural_theses_capsule/input/), [tests](../tests/test_batch8_structural_theses_capsule.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch8_structural_theses_capsule_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). For background on survivorship bias, see [Brown, Goetzmann, Ibbotson and Ross](https://terpconnect.umd.edu/~wermers/ftpsite/FAME/Brown_Goetzmann_Ibbotson_Ross.pdf).
