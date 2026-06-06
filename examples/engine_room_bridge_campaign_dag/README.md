# Engine Room Bridge Campaign DAG

This example is a public-safe source-faithful refactor of the macro bridge
campaign validator. It demonstrates the contract layer only: a valid
probe/reducer/synthesis graph passes, while cycles, dangling synthesis, and
provider over-parallelism fail before any dispatch can happen.

Run from `microcosm-substrate/`:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.bridge_campaign_dag validate-fixtures --input fixtures/first_wave/engine_room_bridge_campaign_dag/input --json
```

Claim ceiling: this is not a dispatcher and does not execute agents.
