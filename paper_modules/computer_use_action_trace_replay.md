# Validate a recorded computer-use episode

The computer-use trace validator compares supplied observations, actions and results from an example episode. It checks that actions refer to recorded observations at no earlier step and supply a control reference, that linked permission records declare themselves pre-action, and that claimed transitions agree with those decisions. It does not verify that a control reference appears in the observation or independently establish when the permission decision occurred. This is an offline consistency check for a saved trace.

## Run the example

From the repository root, with Python 3.11 or later:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_route_observability_runtime \
  validate-computer-use-bundle \
  --input examples/agent_route_observability_runtime/exported_computer_use_action_trace_bundle \
  --out .microcosm/guides/computer_use_action_trace
```

The command writes a JSON validation record with episode, observation, action, permission, transition, recovery and replay summaries. It also checks copied source files against their manifest. The sample run passes with four episodes and eight actions; inspect the result JSON for status and findings.

## What this checks

An action recorded as attempted is inconsistent with a linked block or review decision. The fixture tests include an action missing its observation or control reference and a hidden-state claim. The exported bundle run shown above validates the positive records; the fixture tests require each configured negative case to produce its expected error.

## Limits

The validator reads supplied records; it does not observe a desktop, click a control or independently determine whether a screenshot proves success. It provides no account access or permission to send, buy or delete. Passing these examples is not a computer-use benchmark score or evidence that an agent is safe on unfamiliar websites.

## Verification

The linked tests exercise trace validation and negative fixtures; this particular bundle route has no component-specific formal proof. The registered replay for `agent_route_observability_runtime` uses a different observability bundle, so its [shared admission check](../formal/replay/README.md) does not establish that this computer-use bundle was replayed or that its validator is correct.

## Sources

- [Bundle validator](../src/microcosm_core/organs/agent_route_observability_runtime.py), [example bundle](../examples/agent_route_observability_runtime/exported_computer_use_action_trace_bundle) and [tests](../tests/test_agent_route_observability_runtime.py).
- [Historical bundle result](../receipts/first_wave/agent_route_observability_runtime/exported_computer_use_action_trace_bundle_validation_result.json) and [canonical description](../core/paper_module_capsules.json).
- [WebArena](https://arxiv.org/abs/2307.13854) and [OSWorld](https://arxiv.org/abs/2404.07972) describe separate task environments; their results are not results of this fixture.
