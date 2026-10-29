# Audit example agent responses

> **In plain terms.** Automated assistants can leave out things a careful reply needs, such as the reason they stop to ask permission. This component is given example assistant replies, each marked with its expected verdict. It scans each reply for set trigger phrases and marks it red, meaning a violation, when one appears without the phrase that would justify it. It writes a summary, without copying the replies, showing whether good examples pass and bad ones are caught. One small decision step, spotting the phrases and making the red or green call, is checked by a mathematical proof against written rules.

This fixture runner checks example agent responses for three kinds of omission: asking for permission without a named blocker, describing the agent’s own error without a capture binding, and moving a command to the operator without an execution receipt. It applies the phrase-based [egress gate](engine_room_egress_self_compliance_gate.md), compares each result with the fixture expectation, and writes a summary without the response bodies.

## Run the example

From the repository root, with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.egress_self_compliance_audit run \
  --input fixtures/first_wave/egress_self_compliance_audit/input \
  --out .microcosm/component-guides/egress_self_compliance_audit \
  --acceptance-out .microcosm/component-guides/egress_self_compliance_audit/acceptance.json
```

The status is `pass` when positive cases are clean, the required negative cases are detected, and the expected diagnostic IDs match. For example, a permission request without a recognized blocker phrase is a negative case; the matrix passes when the gate flags it, not when it approves that response.

These are literal detectors over supplied text. A recognized phrase does not establish that a blocker or receipt actually exists. A green result is not a semantic compliance review or proof that every unsafe or inappropriate response will be detected.

## Verification

The gate used by this audit calls a [Dafny-verified phrase matcher and decision](../formal/components/egress_policy/README.md): it finds matches under the supplied boundary rules and flags a matched tripwire without its paired legitimizer. Python’s text normalization and the audit’s fixture comparisons are outside that proof; the phrase rules do not establish semantic compliance.

The fixture command above calls the gate. Separately, `make component-replays` applies the [shared admission check](../formal/replay/README.md) to the audit’s recorded observations.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/egress_self_compliance_audit.py) and [focused tests](../tests/test_engine_room_egress_self_compliance_gate.py).
- [Fixture inputs](../fixtures/first_wave/egress_self_compliance_audit/input/); [historical sample result](../receipts/first_wave/egress_self_compliance_audit/egress_self_compliance_audit_result.json).
- [JSON record](../paper_modules/egress_self_compliance_audit.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
