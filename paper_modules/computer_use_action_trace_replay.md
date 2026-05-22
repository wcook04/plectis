# Computer-Use Action Trace Replay

`computer_use_action_trace_replay` is a validator-backed claim contract under
`agent_route_observability_runtime`. It asks a narrow eval-harness question:
does a claimed computer-use episode bind visible observations, affordances,
actions, pre-action authority verdicts, state-transition receipts, recovery
receipts, cold replay, falsification fixtures, private-state scan posture, and
an explicit authority ceiling?

Run:

```bash
PYTHONPATH=src python3 -m microcosm_core.cli agent-route-observability-runtime validate-computer-use-bundle --input examples/agent_route_observability_runtime/exported_computer_use_action_trace_bundle --out receipts/runtime_shell/demo_project/organs/agent_route_observability_runtime
```

The fixture rejects live account action, credential entry, external network
mutation, purchase/send without approval, destructive action without review,
hidden screen-state claims, actions without observation and affordance refs, and
benchmark-score claims.

The receipt proves only this public synthetic replay boundary. It does not
control a live browser or desktop, use accounts, enter credentials, mutate
external systems, export raw screenshots, claim benchmark performance, mutate
source, call providers, or authorize release.
