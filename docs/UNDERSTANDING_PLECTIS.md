# Understanding Plectis

Plectis contains working examples of the machinery used in an AI research and
engineering workflow: looking up proof premises, checking an agent's use of
untrusted information, comparing a forecast with its outcome, detecting when
a generated document no longer matches its source, and recording work so it
can be picked up again. You can inspect the code and run the examples locally,
and each example says what its result establishes.

There are two ways into that work. The project commands read a folder and
record a route through it; the component commands exercise individual
mechanisms on their own inputs. The [quickstart](../QUICKSTART.md) begins with
the shared project runtime because it is a small first run. To understand a
particular mechanism, choose a component and run its example as well.

## What you can do with it

If you want to explore a repository, point the tour at that folder and inspect
the route, work and evidence records it creates under `.microcosm/`. That gives
you a local record of the run, without changing the source files it read.

If you build or study AI systems, choose a mechanism close to your question
from the [specialty index](../ORGANS.md#find-your-specialty). Some examples
exercise code directly, some replay prepared cases, and some check the
consistency of a record or an exported bundle. Their evidence differs, so the
component's input, checks and limits matter more than its place in the index.

If you came for mathematics, the
[Lean companion](https://github.com/wcook04/plectis-erdos) contains the problem
papers and proof source. Plectis contains tools and examples concerned with
formal proof workflows; the companion is where to read a theorem statement
and check what has been proved about a particular problem. For the wider
argument about the system, use the [paper guide](papers/README.md).

## One example you can follow

Suppose an AI agent reads a web page containing an instruction to send private
information elsewhere. The page is material the agent was asked to read, but
that does not give the page permission to direct the agent's actions. This is
the kind of distinction the prompt-injection replay checks in a prepared
example.

The example uses synthetic records, with references in place of document and
prompt bodies. In
[`source_documents.json`](../examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle/source_documents.json),
`src_web_page_injection` is labelled `untrusted_web` and has
`instruction_authority: false`. In
[`information_flow_graph.json`](../examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle/information_flow_graph.json),
`flow_block_web_to_email` connects that source to a proposed email action and
records a `block` verdict. The same bundle includes allowed, warned and
review-required flows so it can check more than the single blocked case.

From the clone root, with Python 3.11 or newer and a macOS / Linux shell:

```bash
PYTHONPATH=src python3 -m plectis indirect-prompt-injection-information-flow-policy-replay \
  run-prompt-injection-bundle \
  --input examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle \
  --out .microcosm/examples/prompt-injection
```

The command prints `pass` when the bundle satisfies its checks and writes
`exported_prompt_injection_flow_bundle_validation_result.json` in the output
directory. Open that JSON file to see the verdicts, replay results and
`authority_ceiling`; the output directory is ignored by git.

The [runner](../src/microcosm_core/organs/indirect_prompt_injection_information_flow_policy_replay.py)
checks the source labels, information flows, policy verdicts, sanitised outputs
and replay records. Its
[tests](../tests/test_indirect_prompt_injection_information_flow_policy_replay.py)
also exercise cases that should be rejected. You can follow the prepared
input, the code that checks it and the resulting record without needing
access to an AI provider or a private system.

A passing result establishes that these records satisfy the named policy
checks. It does not establish that a deployed agent resists arbitrary prompt
injection: this run did not ask a model to read a hostile page, send an email
or use a real account. An evaluation of that behaviour would need different
inputs and observations. This is the distinction to look for in each
component, because running code, replaying a case and testing a live system
answer different questions.

## The terms used in the repository

The source keeps some names from the system in which this work developed.
These are the ones you need to follow a component:

| Term in the files | Meaning here |
|---|---|
| Component / organ | A unit with its own inputs, runner, checks and limits. `organs/` is the source directory name. |
| Fixture | A prepared input used to reproduce a check, including examples that should fail. |
| Replay | A run over recorded or prepared events. The component states whether those events are synthetic or came from an observed run. |
| Receipt | A saved result with enough references to inspect what ran and what was checked. It is evidence for those checks. |
| Evidence class | The kind of support behind a result, such as a fixture check or a local tool execution. |
| Authority ceiling | The limit on what may be concluded or done from that result. In the example above, a fixture pass cannot become a claim of general prompt-injection resistance. |
| Route | A suggested sequence of actions, or a selected next action, for a task. A route names relevant tools and files. |
| Projection / drift | A view generated from source data, and a disagreement between that view and the source it should represent. |

You will also see `microcosm` in Python package names and `.microcosm/` in
local output paths. These are retained compatibility names; the command and
public project are Plectis. The README explains the
[name and history](../README.md#name-and-history).

## Where the files fit

| Location | What it contains | When to open it |
|---|---|---|
| [`src/plectis/`](../src/plectis/) | The public Python module entry. | To see how `python -m plectis` starts. |
| [`src/microcosm_core/`](../src/microcosm_core/) | The CLI, shared project runtime, component runners, validators and document builders. | To follow an actual command into implementation. |
| [`core/`](../core/) | JSON registries describing the components, their groupings, evidence and shared runtime. | To inspect the data behind a generated map. |
| [`examples/`](../examples/) and [`fixtures/`](../fixtures/) | Worked uses and prepared inputs. | To reproduce a component run or understand its test cases. |
| [`tests/`](../tests/) | Automated checks. | To see which behaviour is exercised and which failures are expected. |
| [`receipts/`](../receipts/) | Committed example results. | To compare a named result with its inputs and checks. Your own outputs should use the example's stated local output path. |
| [`standards/`](../standards/) and [`paper_modules/`](../paper_modules/) | Detailed contracts and component explanations. | After a component links you to the contract it uses. |
| [`atlas/`](../atlas/) | Generated navigation data. | To trace a route or a displayed relationship back to its registry. |
| [`paper/`](../paper/) and [`docs/papers/`](papers/) | Manuscript source, reading guides and searchable paper text. | To read the argument or rebuild a paper. |

For the shared runtime, the next source files are
[`cli.py`](../src/microcosm_core/cli.py) and
[`project_substrate.py`](../src/microcosm_core/project_substrate.py).
The [generated architecture](../ARCHITECTURE.md) maps the larger relationships;
the [component map](../ORGANS.md) supplies the individual runners and evidence.
Those maps are rebuilt from the registries, so changes to them go through
their owner builders rather than edits to the generated pages.

To try the project, continue with [Quickstart](../QUICKSTART.md). To change it,
start with [Contributing](../CONTRIBUTING.md). The
[documentation index](README.md) keeps the reading, review and maintenance
routes together.
