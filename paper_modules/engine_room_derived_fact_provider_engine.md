# Derive facts from declared sources

This engine reads a fact registry and evaluates each declared provider against a root directory. Supported examples include reading a JSON pointer, counting glob matches and calling selected Git-index counters. It returns a fact ledger and an audit with provider errors, rather than silently substituting a value when a provider fails.

## Run the example

From the repository root, with Python 3.11 or newer and Git available:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.derived_fact_provider_engine evaluate-fixtures \
  --input fixtures/first_wave/engine_room_derived_fact_provider_engine/input --json
```

The fixture matrix builds temporary roots and compares observed results with expectations. An unknown provider produces an error row and a degraded registry result; the matrix can still pass because that degradation was expected. The Git counters use tracked files in the index, not all files in the working directory.

The output is derived from the declared inputs and provider implementations. It does not establish that the source data is true or that the registry represents every relevant fact. [OpenLineage](https://openlineage.io/) is related background on recording data lineage.

## Verification

The focused tests check individual providers and error rows. This helper has no registered component replay route and no component-specific formal proof in this repository. Successful fixture checks do not prove the provider implementations or the truth of their inputs.

## Source and evidence

- [Implementation](../src/microcosm_core/engine_room/derived_fact_provider_engine.py) and [focused tests](../tests/test_engine_room_derived_fact_provider_engine.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_derived_fact_provider_engine/input/); [historical Engine Room composition result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) (summary, not a detailed result for this individual fixture).
- [JSON record](../paper_modules/engine_room_derived_fact_provider_engine.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
