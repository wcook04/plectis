# Engine Room Egress Self-Compliance Gate

This example is a public-safe source-faithful refactor of the macro egress
policy checks. It evaluates agent-output text for permission ceremony without a
real blocker, self-error language without a durable capture, and command
displacement to the operator without an execution receipt.

Run from `microcosm-substrate/`:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.egress_self_compliance_gate evaluate-fixtures --input fixtures/first_wave/engine_room_egress_self_compliance_gate/input --json
```

Claim ceiling: phrase-membership egress policy only; not taint analysis,
prompt-injection defense, sandboxing, or information-flow control.
