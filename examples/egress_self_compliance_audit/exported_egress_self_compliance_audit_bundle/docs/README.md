# Egress Self-Compliance Audit - exported bundle

This bundle accompanies the `egress_self_compliance_audit` organ. The organ surfaces the public `egress_self_compliance_gate` engine-room capsule as a first-class runtime.

## What the mechanism does

Checks a snippet of an AI agent's own output for three self-policing slips: asking the user "shall I continue?" without naming a real reason to stop, admitting a mistake without saying it was logged, or telling the user to run a command instead of running it. It works by looking for specific giveaway phrases and the phrases that would excuse them — so it is a fast, transparent style check, not a deep understanding of meaning. Reword the slip and it will be missed; that is the honest limit.

## What it does not claim

Command-receipt evidence over bounded public fixtures, not runtime-product completeness. Establishes only that the capsule's phrase-membership detectors reproduce the declared green/red verdicts and diagnostic markers on the authored cases. Does NOT establish coverage of real agent output, semantic correctness, adversarial robustness, or any safety guarantee; does not authorize release, publication, provider calls, or source mutation.

## Fixture cases

permission_gate_with_named_blocker (positive): a permission gate that names a real blast-radius blocker (remote push, publication boundary, irreversible) — the gate returns green, no violation.
self_error_with_capture (positive): a self-corrected mistake bound to a durable capture (cap_quick_..., captured, task ledger) — the gate returns green, no violation.
permission_gate_without_blocker (negative): a bare 'let me know if you want me to continue' with no named blocker — gate returns red with diagnostic permission_gate_without_blocker.
command_displacement_no_receipt (negative): 'you can run make smoke' handed to the operator with no execution receipt — gate returns red with diagnostic command_displacement_to_operator.

## Run it

```bash
python -m microcosm_core.organs.egress_self_compliance_audit run \
  --input fixtures/first_wave/egress_self_compliance_audit/input \
  --out receipts/first_wave/egress_self_compliance_audit
```
