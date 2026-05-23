# Indirect Prompt-Injection Information-Flow Policy Replay

This validator-backed claim contract admits one narrow public claim: a
source-faithful public trace refactor separated trusted instructions from
untrusted web/tool/browser text before any privileged action or answer claim was
accepted.

The runnable contract requires source trust labels, taint labels, source-to-sink
flow rows, pre-action policy verdicts, sanitized-output receipts, cold replay,
secret-exclusion scan, negative cases, a public agent-execution trace, and an
explicit authority ceiling.

## Cold-Reader Path

```bash
microcosm indirect-prompt-injection-information-flow-policy-replay run-prompt-injection-bundle \
  --input examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle \
  --out receipts/runtime_shell/demo_project/organs/indirect_prompt_injection_information_flow_policy_replay
```

Primary receipt:
`receipts/runtime_shell/demo_project/organs/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle_validation_result.json`

First-wave fixture receipt:
`receipts/first_wave/indirect_prompt_injection_information_flow_policy_replay/indirect_prompt_injection_information_flow_policy_replay_validation_receipt.json`

## Input Contract

- `projection_protocol.json`: source-available projection statement and omitted private material.
- `injection_policy.json`: required source, flow, verdict, and output fields plus authority denials.
- `source_documents.json`: synthetic trusted and untrusted sources with trust labels and taint labels.
- `information_flow_graph.json`: source-to-sink flow rows before claim admission.
- `policy_verdicts.json`: allow, warn, block, and review verdicts before synthetic action.
- `sanitized_outputs.json`: output refs proving no trusted context disclosure and no untrusted instruction obedience.
- `cold_replay.json`: rerunnable command and receipt refs that reproduce verdicts and sanitized state.

## Public Trace Refactor

The product evidence is no longer the fixture verdict fields alone. The organ
uses `microcosm_core.macro_tools.agent_execution_trace::build_public_prompt_injection_trace`
to emit body-free spans over the public source, flow, verdict, output, and replay
refs. That builder is a Microcosm refactor of the macro
`system/lib/agent_execution_trace.py` span model, so the accepted receipt can
show sequence, authority, audit, coverage, and digest mechanics without copying
real accounts, prompt bodies, provider payloads, or live tool material.

## Negative Cases

The validator rejects real account material, secret or trusted-context
exfiltration, raw prompt body export, untrusted tool output treated as
instruction authority, hidden system-message promotion, credential exfiltration,
final-answer-only success, and ungated untrusted flow into a privileged sink.

These are falsification fixtures. They are part of the contract, not examples of
live exploit traffic.

## Authority Ceiling

Passing receipts prove only that this public trace refactor satisfies the named
prompt-injection information-flow contract over body-free rows. They do not
prove general prompt-injection robustness, benchmark performance, live account
safety, provider behavior, tool behavior, hidden-message handling in a real
system, source mutation authority, publication authority, or release operations.
