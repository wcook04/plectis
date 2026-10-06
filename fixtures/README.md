# Test inputs and deliberate failures

Fixtures give a check a known input and let its tests compare the result with
what should happen. Some are valid examples; others deliberately contain a
false claim, missing file or broken rule. A rejected fixture can therefore be
the expected successful outcome of a test.

For a first run, use the [runnable examples](../examples/README.md) and their
guides. This folder is most useful when you want to understand or change what a
component accepts and rejects.

## Follow a check from input to result

| Question | Inputs to inspect | Guide or test |
| --- | --- | --- |
| What evidence backs a completion claim? | [Completion claims and false claims](first_wave/agent_closeout_faithfulness_audit/input/) | [Worked guide](../docs/guides/checking-agent-completion.md) and [tests](../tests/test_agent_closeout_faithfulness_audit.py) |
| Does the checker distinguish trusted instructions from untrusted text? | [Prompt-injection inputs](first_wave/indirect_prompt_injection_information_flow_policy_replay/input/) | [Walkthrough](../docs/guides/prompt-injection.md) and [tests](../tests/test_indirect_prompt_injection_information_flow_policy_replay.py) |
| Does a generated file still match its declared source? | [Clean, altered and missing-file cases](first_wave/engine_room_generated_projection_drift_gate/input/) | [Implementation tests](../tests/test_engine_room_generated_projection_drift_gate.py) |
| Should a duplicate command reuse its previous result? | [Repeated commands and changed-state cases](first_wave/semantic_singleflight_dedup_runtime/input/) | [Implementation tests](../tests/test_semantic_singleflight_dedup_runtime.py) |

The `first_wave/` and `second_wave/` names group imported fixtures. They are not
a ranking of component quality or a suggested reading order.

## Run one fixture set

The [completion guide](../docs/guides/checking-agent-completion.md#run-the-example)
shows how to prepare an environment with pytest and Git. From the clone root,
run its supplied fixture set with output kept outside the recorded results:

```sh
PYTHONPATH=src python -m plectis agent-closeout-faithfulness-audit run \
  --input fixtures/first_wave/agent_closeout_faithfulness_audit/input \
  --out .microcosm/examples/agent-completion
```

Read `agent_closeout_faithfulness_audit_result.json` in that output directory.
The overall run should pass when the valid claims verify and the deliberately
incorrect claims are rejected. The guide explains why expected rejection codes
can appear in a passing result.

## Change a case safely

Read the input, the function that checks it, and the corresponding test together.
Predict the result of your change before running it. The
[prompt-injection walkthrough](../docs/guides/prompt-injection.md)
demonstrates this with a disposable repository copy.

If you are contributing a new case, make its expected result explicit and run
the component's focused tests. The [validation guide](../docs/maintainers/validation.md)
explains the repository checks and isolated test directories; the
[architecture guide](../docs/maintainers/architecture.md) helps locate the code
owner. Copied `source_modules/` files preserve imported versions and should not
be edited as a substitute for changing the owning implementation.

## Where the output belongs

Keep personal runs under `.microcosm/` or a temporary directory. Files in
[receipts](../receipts/README.md) are checked-in records produced by runners;
changing fixture data does not update those records automatically.
Regenerate an owned record with its runner when making a deliberate contribution,
rather than editing the saved result by hand.

Passing these cases establishes the tested behavior on these inputs. It does
not establish how an agent, dataset or external tool will behave in every other
setting. Use the [component map](../ORGANS.md#find-your-specialty) to find another
subject, or return to the [documentation index](../docs/README.md).
