# Benchmark integrity replay

> **In plain terms.** A test score for an artificial intelligence program means little if it saw the answers or the grading was altered. This component is given three example records of test runs, the locked grading rules, and evidence of which files each run opened and whether test material leaked in. It checks that each record names the locked grader and settings, works out whether the run kept to the rules, and rejects any record whose written verdict disagrees. A reader examining how a test claim was recorded can see each verdict, two passes and one set aside in the example. It calculates no score, and the three cases say nothing about how any program does on a real test.

This replay checks whether recorded benchmark runs agree with a locked evaluator policy and their supporting evidence. It reads public case and replay records, checks evaluator IDs and configuration hashes, and recomputes integrity verdicts from file-access and contamination evidence. Its result is useful when examining how a benchmark claim was recorded; it does not calculate a benchmark score.

The supplied fixture has three cases. The regression test expects two integrity passes and one quarantine. A mismatched evaluator hash or a declared verdict that disagrees with the recomputed verdict is rejected. The validator also checks source-artifact references and digests; a matching digest establishes the identity of the copied material, not the correctness of its algorithm.

The records omit private issue and oracle patch bodies. These examples do not establish performance on SWE-bench or any other real benchmark.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay \
  run --input fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input \
  --out .microcosm/component-guides/agent_benchmark_integrity_anti_gaming_replay/output \
  --acceptance-out .microcosm/component-guides/agent_benchmark_integrity_anti_gaming_replay/acceptance.json
```

The result lists the computed integrity verdicts, quarantines and findings. It is written under `.microcosm/component-guides/agent_benchmark_integrity_anti_gaming_replay/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the evaluator and contamination checks; they do not formally prove the benchmark integrity algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported benchmark bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/agent_benchmark_integrity_anti_gaming_replay.py) · [fixture input](../fixtures/first_wave/agent_benchmark_integrity_anti_gaming_replay/input/) · [tests](../tests/test_agent_benchmark_integrity_anti_gaming_replay.py) · [sample result (historical)](../receipts/first_wave/agent_benchmark_integrity_anti_gaming_replay/agent_benchmark_integrity_anti_gaming_replay_result.json) · [JSON record](agent_benchmark_integrity_anti_gaming_replay.json).

[Specification gaming](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/) describes the broader problem; this fixture is not a measurement of it.
