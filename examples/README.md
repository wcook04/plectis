# Runnable examples

This folder contains prepared input bundles and small sample projects. Start
with a question below, follow its guide, and run the commands from the
repository root. The guides explain prerequisites and what to look for in the
result; browsing a bundle alone does not execute it.

## Choose an example

| What you want to try | Start here | Example files |
| --- | --- | --- |
| Check an agent's claim that it committed work and ran a test | [Checking agent completion](../docs/guides/checking-agent-completion.md) | [Claims, ledger and tiny test project](agent_closeout_faithfulness_audit/exported_agent_closeout_faithfulness_audit_bundle/) |
| Give untrusted text instruction authority and see the check reject it | [Prompt-injection walkthrough](../docs/guides/prompt-injection.md) | [Source documents and flow records](indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle/) |
| Turn a tentative answer into a question an expert can evaluate | [Hypothesis handoffs](../docs/guides/hypothesis-handoffs.md) | [An independent-evaluation question](hypothesis_handoff/independent_evaluation.json) |
| Inspect how Plectis records a local project | [Quickstart](../QUICKSTART.md#1-first-result) | [A small sample project](runtime_shell/demo_project/) |

The completion example runs Git and pytest in a temporary project. The
prompt-injection example checks supplied source documents and flow records.
The hypothesis example checks a question's structure. Read each guide to see
what its result establishes.

## A short example with no installation

With Python 3.11 or newer, run this from the clone root:

```sh
PYTHONPATH=src python3 -m plectis hypothesis-handoff \
  --input examples/hypothesis_handoff/independent_evaluation.json \
  --format text
```

It prints the proposed question, alternatives and distinguishing observations.
It does not contact an expert or change the input file. The
[guide](../docs/guides/hypothesis-handoffs.md) explains the checks and how to
prepare your own handoff.

## Find another component

The [component map](../ORGANS.md#find-your-specialty) groups the corpus by
subject. If you have a specific goal, ask for a suggested first action:

```sh
PYTHONPATH=src python3 -m plectis comprehend \
  --first-action "Replay a prompt injection example" --format text
```

That command prints a route; it does not run the suggested action. Read its
input path and output path before continuing.

## Keep your runs separate

- Examples are prepared demonstrations; [fixtures](../fixtures/README.md)
  supply test cases, including deliberate failures.
- [Recorded outputs](../receipts/README.md) describe earlier runs. Save your own
  outputs under the ignored `.microcosm/` directory, as the guides show.
- For an input experiment, use the guide's temporary copy so the checked-in
  bundle remains available for comparison.
- Some bundles contain `source_modules/` copies of imported code. Find the
  implementation owner and its checks in the [architecture guide](../docs/maintainers/architecture.md)
  before changing code; an exported copy is not the default edit target.

Return to the [documentation index](../docs/README.md) for setup and other guides.
