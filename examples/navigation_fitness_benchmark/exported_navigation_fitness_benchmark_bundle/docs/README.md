# Navigation Fitness Benchmark - exported bundle

This bundle accompanies the `navigation_fitness_benchmark` organ. The organ surfaces the public `navigation_fitness_benchmark` engine-room capsule as a first-class runtime.

## What the mechanism does

A scorer for how well a navigation system found the right thing. Each test case is a "task" (what someone was looking for, which exact items count as the right answer, which shortcut routes are off-limits, and how fast it should be) paired with a "route packet" (what the system actually returned and how long it took). The tool re-checks the answer: did it find the expected items (recall), how much of what it returned was on-target (precision), did it take a banned first step, did it mention the right cue words, and did it stay under the time budget. It then flags any "debt" — places that missed the mark or ran slow. It judges curated public examples only; it does not run the real private system, does not test the underlying search/embeddings, and does not claim to be a general-purpose navigation score.

## What it does not claim

Command-receipt evidence over bounded public fixtures, not runtime-product completeness. A pass means the curated route-packet cases recomputed as expected (positives accepted, negatives rejected by recomputation with the expected markers); it does NOT establish live private-kernel navigation quality, embedding quality, universal benchmark authority, production readiness, or release/publication authorization. Receipts are body-free command evidence, not proof of substrate correctness.

## Fixture cases

clean_fanout_pass (positive): two context-pack tasks where the router selected exactly the expected stable ids, took no forbidden first route, covered the scent terms, and stayed under budget; recomputed benchmark matches the planted all-pass expectation, so the case is accepted.
latency_debt_pass (positive): a task whose route is sufficient (right id, scent covered) but exceeds its 100ms budget at 830ms; the planted expectation honestly anticipates sufficiency_status=pass with latency_status=fail and one debt candidate, so the recomputation matches and the case is accepted — showing the organ accepts truthful debt-bearing packets.
missing_stable_id_rejected (negative): the packet returns skills:navigation_metabolism instead of the expected skills:agent_session_diagnostics, so the capsule recomputes sufficiency_status=fail (missing_id); the fixture's planted expectation falsely claims the task passed, so expectation_met=False and the case is rejected with the missing_id marker firing.
forbidden_first_route_rejected (negative): the first-contact command is '--paper-module ...', which hits the task's forbidden_first_routes list, so the capsule recomputes sufficiency_status=fail (forbidden_route); the fixture's planted expectation falsely claims a clean pass, so expectation_met=False and the case is rejected with the forbidden_route marker firing.

## Run it

```bash
python -m microcosm_core.organs.navigation_fitness_benchmark run \
  --input fixtures/first_wave/navigation_fitness_benchmark/input \
  --out receipts/first_wave/navigation_fitness_benchmark
```
