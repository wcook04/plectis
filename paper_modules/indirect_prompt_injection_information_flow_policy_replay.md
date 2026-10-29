# Indirect Prompt-Injection Information-Flow Replay

> **In plain terms.** Instructions hidden in a document or tool result can trick an automated assistant into obeying them. This component is given made-up records of information moving from documents and tool outputs to actions or answers, with trust labels and verdicts noted. It follows each chain, works out the trust labels carried along it (called taint) and compares them with the recorded labels and verdicts. It rejects untrusted output promoted to an instruction, or flowing unchecked into an action needing special permission. One small decision step, tracing untrusted material and deciding whether to block, is checked by a mathematical proof against written rules.

This replay checks synthetic records of information moving from documents and tool output to actions or answers. It tracks data from each source through a chain to an action or answer. It derives the trust labels carried along that chain, called taint, and compares them with recorded labels and policy verdicts. It also checks sanitized output and replay evidence. The result is a validation receipt over the supplied trace metadata.

A fixture that promotes untrusted tool output to an instruction is rejected; an ungated flow into a privileged action is another negative case. The tests also change declared taint and verdicts to check that the validator recomputes them. These are simulated cases, not a live attack against an account or a measurement of general prompt-injection resistance.

## Run the example

From the repository root with Python 3.11 or newer, run the supplied fixture into ignored local output:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.indirect_prompt_injection_information_flow_policy_replay run \
  --input fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input \
  --out .microcosm/component-guides/indirect_prompt_injection_information_flow_policy_replay/out \
  --acceptance-out .microcosm/component-guides/indirect_prompt_injection_information_flow_policy_replay/acceptance.json
```

The supplied fixture reports `pass` when the positive trace and expected refusals satisfy the validator.

See [AgentDojo](https://arxiv.org/abs/2406.13352) and [information-flow analysis for language models](https://arxiv.org/abs/2410.03055) for related research.

## Verification

The replay calls a [Dafny-verified information-flow core](../formal/components/information_flow/README.md). It computes exactly the finite graph nodes reachable from supplied taint seeds, including hidden-policy seeds at marked edges, and proves the decision blocks hidden-policy claims and unsanitized untrusted flows to privileged sinks. Python constructs the episode graphs and witness paths; their fidelity and live resistance to injection are not proved.

The direct fixture calls this core. `make component-replays` separately applies the [shared admission check](../formal/replay/README.md) to the component replay’s captured observations.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/indirect_prompt_injection_information_flow_policy_replay.py) and [fixture inputs](../fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input/).
- [Tests](../tests/test_indirect_prompt_injection_information_flow_policy_replay.py).
- [Saved example result](../receipts/first_wave/indirect_prompt_injection_information_flow_policy_replay/indirect_prompt_injection_information_flow_policy_replay_result.json) (historical, not a fresh run).
- [Component JSON record](./indirect_prompt_injection_information_flow_policy_replay.json) and [canonical capsule](../core/paper_module_capsules.json).
