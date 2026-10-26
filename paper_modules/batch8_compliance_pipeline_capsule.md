# Check copied compliance and pipeline helpers

This fixture checks six groups of copied compliance and pipeline code. It combines source-contract checks with selected executed helper exercises. For example, a pipeline helper summarizes a long seed into a short text digest. The exercise puts a directive among many low-signal lines and checks that the summary retains it for later processing; it also checks shard-status normalization and selection diversity.

The registry, bounded compliance check and baseline companion rows in this public implementation inspect copied-source contracts. The bounded-check row reports `standalone_copied_source_contract`; it does **not** run the parent repository’s ledger subprocess. A negative exercise removes a directive marker from a copied source and checks the resulting failure.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_compliance_pipeline_capsule run \
  --input fixtures/first_wave/batch8_compliance_pipeline_capsule/input \
  --out .microcosm/component-guides/batch8_compliance_pipeline_capsule \
  --acceptance-out .microcosm/component-guides/batch8_compliance_pipeline_capsule/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

Source-contract checks and helper exercises do not formally prove the compliance or pipeline algorithms. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

A passing fixture is evidence about these specific source contracts and helper inputs, not a fresh full compliance ledger or permission to dispatch a pipeline.

## Sources

[src/microcosm_core/organs/batch8_compliance_pipeline_capsule.py](../src/microcosm_core/organs/batch8_compliance_pipeline_capsule.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/batch8_compliance_pipeline_capsule/input/), [tests](../tests/test_batch8_compliance_pipeline_capsule.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch8_compliance_pipeline_capsule_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). Related background: [NIST SP 800-53](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final).
