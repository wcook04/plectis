# Agent Monitor Redteam Falsification Replay

This module is the public Microcosm regression drilldown for a
monitor/redteam honesty contract. It is a synthetic replay fixture, not a live
monitor product, control eval, exploit guide, product-spine substrate, or
complete-security claim.

The fixture models three public trajectory cases: a benign control, a suppressed
failure attempt, and a tool-authority boundary attempt. Each case must carry a
trajectory hash, monitor id, suspicious span ref, adversarial probe ref,
verdict, severity, escalation ref, body-omission ref, mitigation ref, and cold
replay ref before the claim is admitted.

## Public Mechanics

- A monitor claim cannot pass unless the observation includes a verdict and the
  probe, escalation, mitigation, body-omission, and replay refs that make the
  verdict rerunnable.
- Coverage labels require adversarial probe refs; benign-only trajectories do
  not authorize coverage language.
- Private reasoning, internal code, exploit-detail, credential, live-traffic,
  product-performance, and coverage-without-probe cases are expected
  falsification fixtures.
- Receipts expose ids, refs, verdict counts, negative cases, `body_in_receipt:
  false`, private-state scan, and authority ceilings only.

## Anti-Claim

This module does not run live agents, call providers, expose private
chain-of-thought, export internal code, provide exploit instructions, include
credentials, import live agent traffic, claim monitor product performance, claim
control-eval scores, mutate source, publish results, or authorize release.
