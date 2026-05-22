# Agent Sandbox Policy-Escape Replay

`agent_sandbox_policy_escape_replay` is a validator-backed claim contract for
synthetic agent sandbox/security claims. It asks a narrow question: does a
public claim have action requests, pre-execution policy verdicts, side-effect
diff receipts, rollback receipts, cold replay, falsification fixtures, and an
explicit authority ceiling?

## Runnable Path

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_sandbox_policy_escape_replay run --input fixtures/first_wave/agent_sandbox_policy_escape_replay/input --out receipts/first_wave/agent_sandbox_policy_escape_replay --acceptance-out receipts/acceptance/first_wave/agent_sandbox_policy_escape_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli agent-sandbox-policy-escape-replay run-sandbox-bundle --input examples/agent_sandbox_policy_escape_replay/exported_sandbox_policy_escape_bundle --out receipts/runtime_shell/demo_project/organs/agent_sandbox_policy_escape_replay
```

## Contract

- Input shape: `projection_protocol`, `sandbox_policy`, `action_requests`,
  `policy_verdicts`, `side_effect_receipts`, `rollback_receipts`, and
  `cold_replay`.
- Positive evidence: six synthetic action requests, six pre-execution policy
  verdicts, six side-effect receipts, two verified rollback receipts, and six
  cold replay rows.
- Negative cases: real secret material, live network access, raw environment
  export, policy after execution, unlogged side effect, tool-output policy
  bypass, executable escape payload, and security benchmark claim.
- Receipt boundary: the validation receipt proves only the synthetic replay
  contract, negative-case coverage, private-state scan, and authority ceiling.
- Authority ceiling: no live sandbox escape, live secret handling, live network
  access, host filesystem mutation, executable payload export, raw environment
  export, provider call, security benchmark claim, source mutation, or release
  authority.

## Projection Protocol

Copied: the public shape of a sandbox policy replay and the idea that
containment must be proven before a security claim is admitted.

Reimplemented: local JSON validators, redacted synthetic fixtures,
pre-execution verdict checks, side-effect diff checks, rollback checks, and
receipt generation.

Cleaned: real secrets, host paths, live network targets, raw environment data,
executable payloads, provider data, and account state.

Omitted: live exploit material, hosted sandbox details, real credentials, raw
tool-output bodies, real filesystem paths, raw environment variables, and
security benchmark score claims.

Public replacement: a synthetic fixture bundle plus generated receipts under
`receipts/first_wave/agent_sandbox_policy_escape_replay/`.

Validation proves the projection boundary for this contract; it does not prove
real sandbox security, live model behavior, benchmark scores, exploit
resistance, or whole-system safety.
