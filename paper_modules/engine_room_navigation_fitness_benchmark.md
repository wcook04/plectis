# Score navigation packets against fixture expectations

A route packet records the artifacts selected for a task, the first command and timing. Task fixtures specify the stable artifact IDs that should be selected. This evaluator compares saved route packets with those expectations. It matches selected artifact IDs against expected IDs, measures recall and precision, checks forbidden first routes and required words that indicate a useful route description, and records latency against a budget. Latency and sufficiency are separate: a correct packet can be slow, and a fast packet can miss a required ID.

The fixture suite includes missing-ID and forbidden-route failures. A benchmark result of `pass` means it contained tasks, not that every task passed: inspect its sufficiency and latency counts and the tasks marked for follow-up. The fixture evaluator instead checks that cases produce their expected outcomes.

The inputs are curated packets, not live private-kernel calls. Their scores do not establish general navigation or embedding performance.

## Run the example

Python 3.11 or later is required. From the repository root, run the public fixture matrix. JSON is printed to standard output.

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.navigation_fitness_benchmark evaluate-fixtures --input fixtures/first_wave/engine_room_navigation_fitness_benchmark/input --json
```

## Verification

`evaluate_task` calls the [proved navigation-metrics core](../formal/components/navigation_metrics/README.md). For normalized IDs, it counts matched expected patterns and relevant selected IDs in their respective units, and applies the stated failure and latency priorities. Python supplies the observations and computes the ratios and rounding. This helper has no separate registered component replay.

## Source

[Implementation](../src/microcosm_core/engine_room/navigation_fitness_benchmark.py) · [Input](../fixtures/first_wave/engine_room_navigation_fitness_benchmark/input) · [Tests](../tests/test_engine_room_navigation_fitness_benchmark.py) · [Historical sample](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) · [JSON record](engine_room_navigation_fitness_benchmark.json) (the sample is the composed Engine Room result)

[TREC](https://trec.nist.gov/) provides background on retrieval evaluation; this fixture is not a TREC benchmark.
