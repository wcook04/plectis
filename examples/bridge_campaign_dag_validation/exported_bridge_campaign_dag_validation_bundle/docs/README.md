# Bridge Campaign DAG Validation - exported bundle

This bundle accompanies the `bridge_campaign_dag_validation` organ. The organ surfaces the public `bridge_campaign_dag` engine-room capsule as a first-class runtime.

## What the mechanism does

A bridge campaign is a small directed graph of probe, reducer, and synthesis nodes that fans several parallel reads into a single synthesis. The validator checks a public-safe subset of the macro CR/VR rule families: schema and identity fields, unique node labels, dependency edges that reference existing nodes, acyclicity (DFS cycle detection), exactly one synthesis node that transitively reaches a probe, a barrier that names the synthesis, and a requested worker count within the provider's safe-parallelism ceiling.

## What it does not claim

It validates campaign *structure* only. It does **not** dispatch agents, execute campaigns, prove provider correctness, or authorize release or publication.

## Fixture cases

- `linear_chain_ok.json` - probe -> reducer -> synthesis: a well-formed linear campaign (positive).
- `fan_in_ok.json` - three probes -> one reducer -> one synthesis: a well-formed fan-in (positive).
- `cycle_rejected.json` - reducer and synthesis depend on each other: rejected for a dependency cycle, CR012 (negative).
- `two_synthesis_rejected.json` - two synthesis nodes: rejected for violating the single-synthesis rule, CR013 (negative).

## Run it

```bash
python -m microcosm_core.organs.bridge_campaign_dag_validation run \
  --input fixtures/first_wave/bridge_campaign_dag_validation/input \
  --out receipts/first_wave/bridge_campaign_dag_validation
```
