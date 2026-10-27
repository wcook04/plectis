# Validate a campaign dependency graph

This validator checks a campaign plan expressed as JSON. In the example plan, probe nodes represent individual checks; a reducer depends on those probes, and a synthesis node depends on the reducer. The barrier names that synthesis node, while the continuation describes the next action. The validator checks these relationships and the provider worker limit and returns rule-by-rule decisions before any dispatch. Labels must be unique, dependencies must exist and form an acyclic graph, and synthesis must reach a probe through its dependencies.

## Run the example

From the repository root, with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.bridge_campaign_dag validate-fixtures \
  --input fixtures/first_wave/engine_room_bridge_campaign_dag/input --json
```

The matrix includes a valid plan and plans with a cycle, excessive worker count or dangling synthesis. The matrix passes when each actual verdict matches its expectation; the cyclic plan is rejected. The command validates plans; it does not execute a campaign or call a provider. The default single-plan command does not check whether the referenced plan file exists; the Python validator exposes that optional check.

[DAGs in Airflow](https://airflow.apache.org/docs/apache-airflow/2.4.3/core-concepts/dags.html) offer useful background on task dependencies, but this fixture validator is not an Airflow scheduler.

## Verification

The focused tests check specific graph and worker-limit failures. This helper has no registered component replay route and no component-specific formal proof in this repository. Passing the fixture matrix does not prove the validator correct for every campaign.

## Source and evidence

- [Implementation](../src/microcosm_core/engine_room/bridge_campaign_dag.py) and [focused tests](../tests/test_engine_room_bridge_campaign_dag.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_bridge_campaign_dag/input/); [historical Engine Room composition result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) (summary, not a detailed result for this individual fixture).
- [JSON record](../paper_modules/engine_room_bridge_campaign_dag.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
