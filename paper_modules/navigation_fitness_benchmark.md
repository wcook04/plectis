# Route-packet fitness benchmark

Scores supplied route packets against task-specific expected IDs and rules, then checks whether each computed verdict matches its fixture expectation. A packet records the choices returned for a task: the first command, selected artifacts, summary and elapsed time.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.navigation_fitness_benchmark run --input fixtures/first_wave/navigation_fitness_benchmark/input --out .microcosm/component-guides/navigation_fitness_benchmark --acceptance-out .microcosm/component-guides/navigation_fitness_benchmark/acceptance.json --json
```

Inspect the status and findings in `.microcosm/component-guides/`; the linked result below is a historical sample.

## What it checks

The evaluator calculates recall and precision for expected artifacts, checks forbidden first routes, checks how many task-specific cue words appear in the packet summary and compares elapsed time with a budget. The fixture calls those cue words scent terms. A budget overrun is latency debt and is recorded separately from whether the selected artifacts are sufficient. A packet missing an expected stable ID or selecting a forbidden first route is rejected when it claims to pass.

## Limits

These curated cases measure supplied packets against their task definitions. They are not a general navigation benchmark, embedding evaluation or live private-kernel measurement.

## Verification

The fixture evaluator calls the [proved navigation-metrics core](../formal/components/navigation_metrics/README.md). For normalized IDs, the core counts matched expected patterns and relevant selected IDs separately, then applies the specified failure and latency priorities. Python supplies the observations and calculates the ratios.

The example uses that core. `make component-replays` additionally applies the shared [replay admission check](../formal/replay/README.md) to the registered fixture route.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/navigation_fitness_benchmark.py) and [focused tests](../tests/test_engine_room_navigation_fitness_benchmark.py)
- [Example input](../fixtures/first_wave/navigation_fitness_benchmark/input) and [historical sample result](../receipts/first_wave/navigation_fitness_benchmark/navigation_fitness_benchmark_result.json)
- [Component JSON record](./navigation_fitness_benchmark.json) and [canonical capsule](../core/paper_module_capsules.json)
- [Supporting implementation](../src/microcosm_core/engine_room/navigation_fitness_benchmark.py)
