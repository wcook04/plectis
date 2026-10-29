# Validate a campaign dependency graph

> **In plain terms.** A job split into dependent tasks can be planned badly, for example with tasks waiting on each other in a circle. This component is given a plan listing evidence-gathering steps, optional steps that combine results, and one final step that pulls everything together. It checks that labels are unique, every dependency exists, no chain of dependencies leads back to itself, and a single final step traces back to an evidence-gathering step. It accepts or rejects the plan before any work starts, recalculating from the plan itself rather than trusting a declared status.

This validator checks a campaign plan before execution. The plan names probe nodes that gather evidence, optional reducers, and a synthesis node that depends on them. The validator requires the synthesis to reach at least one probe through its dependencies. A barrier names the synthesis that must finish before continuation; a provider-specific worker ceiling bounds requested parallelism.

The validator also checks identity and unique node labels, that dependencies exist, and that the graph is acyclic.

The fixture includes a linear chain and a three-way fan-in. It rejects a cycle with `CR012` and two synthesis nodes with `CR013`. These decisions are recomputed from the campaign rather than inferred from a declared status.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.bridge_campaign_dag_validation run \
  --input fixtures/first_wave/bridge_campaign_dag_validation/input \
  --out .microcosm/component-guides/bridge_campaign_dag_validation \
  --acceptance-out .microcosm/component-guides/bridge_campaign_dag_validation/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

The graph fixtures test selected cases; they do not formally prove the validator algorithm. Separately, `make component-replays` runs this component’s registered fixture route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

Checks a campaign plan's dependencies, cycles, barrier alignment, worker ceiling and the single synthesis that reaches a probe, rejecting a cycle or a second synthesis.

## Sources

[src/microcosm_core/organs/bridge_campaign_dag_validation.py](../src/microcosm_core/organs/bridge_campaign_dag_validation.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/bridge_campaign_dag_validation/input/), [tests](../tests/test_engine_room_bridge_campaign_dag.py), [historical sample acceptance result](../receipts/acceptance/first_wave/bridge_campaign_dag_validation_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). The graph rules are in [bridge_campaign_dag.py](../src/microcosm_core/engine_room/bridge_campaign_dag.py).
