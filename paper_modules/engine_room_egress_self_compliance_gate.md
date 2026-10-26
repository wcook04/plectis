# Check response text for three omissions

This gate scans supplied response text for phrases associated with three cases: a permission request lacking a blocker, an agent’s own error lacking a capture binding, and command displacement without an execution receipt. It returns detector diagnostics and a `green` or `red` status. The matching is based on defined phrases and word boundaries.

## Run the example

From the repository root, with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.egress_self_compliance_gate evaluate-fixtures \
  --input fixtures/first_wave/engine_room_egress_self_compliance_gate/input --json
```

The matrix includes both a permission request with a recognized blocker phrase and one without it. It passes when the expected green and red results occur; a red example is an expected rejection. For one response, use `evaluate --text '...' --json`; that command exits nonzero for red.

A recognized phrase does not establish that a blocker or receipt actually exists. The detector does not understand all meanings or prove that a response is safe. A green result means these particular phrase rules found no violation, not that the message has passed general policy or information-flow analysis. [OPA](https://www.openpolicyagent.org/docs/latest) is related background on explicit policy checks, not the implementation used here.

## Verification

The active gate calls a [Dafny-verified phrase matcher and decision](../formal/components/egress_policy/README.md). The matcher finds exactly the occurrences satisfying its supplied boundary rules; the decision marks a violation when a tripwire matches without its paired legitimizer. Python supplies the normalized text and boundary flags. The proof does not establish that the phrases understand meaning or cover every unsafe response.

This helper has no registered component-replay route of its own; its related audit has a separate replay route.

## Source and evidence

- [Implementation](../src/microcosm_core/engine_room/egress_self_compliance_gate.py) and [focused tests](../tests/test_engine_room_egress_self_compliance_gate.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_egress_self_compliance_gate/input/); [historical Engine Room composition result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) (summary, not a detailed result for this individual fixture).
- [JSON record](../paper_modules/engine_room_egress_self_compliance_gate.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
