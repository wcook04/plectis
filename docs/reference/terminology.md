# Terminology and file map

Use this reference while following a [worked guide](../guides/README.md)
or reading the source. The [documentation index](../README.md) lists the
other explanations and maintenance guides.

## The terms used in the repository

The source keeps some names from the system in which this work developed.
These are the ones you need to follow a component:

| Term in the files | Meaning here |
|---|---|
| Component / organ | An individually named program or group of functions, with input files, output files and pass/fail conditions. `organs/` is the source directory name. |
| Fixture | A prepared input file used in a test. Some fixtures deliberately omit a required field or contain values the program must reject. |
| Replay | Running a program over saved event records. The records may be synthetic; replaying them does not repeat the original actions in a live account. |
| Receipt | A saved result, usually JSON, with the program's status, input/source references and reasons for rejection. In the [prompt-injection walkthrough](../guides/prompt-injection.md) it is `exported_prompt_injection_flow_bundle_validation_result.json`. |
| Evidence class | A registry label identifying how a result was obtained, for example by testing prepared inputs or executing an external tool. |
| Authority ceiling | The limit on what may be concluded or done from that result. In the [prompt-injection walkthrough](../guides/prompt-injection.md), a fixture pass cannot become a claim of general prompt-injection resistance. |
| Route | A stored description of a proposed job. The tour's `readme_onboarding_route`, for example, names README files and the proposed `inspect` action. |
| Projection / drift | A view generated from source data, and a disagreement between that view and the source it should represent. |

You will also see `microcosm` in Python package names and `.microcosm/` in
local output paths. These are retained compatibility names; the command and
public project are Plectis. The README explains the
[name and history](../../README.md#name-and-history).

## Where the files fit

| Location | What it contains | When to open it |
|---|---|---|
| [`src/plectis/`](../../src/plectis/) | The public Python module entry. | To see how `python -m plectis` starts. |
| [`src/microcosm_core/`](../../src/microcosm_core/) | The CLI, shared project runtime, component runners, validators and document builders. | To follow an actual command into implementation. |
| [`core/`](../../core/) | JSON lists of component identifiers, program/input paths, result classifications and permitted operations. | To inspect the data used to generate the architecture and component tables. |
| [`examples/`](../../examples/) and [`fixtures/`](../../fixtures/) | Worked uses and prepared inputs. | To reproduce a component run or understand its test cases. |
| [`tests/`](../../tests/) | Python test functions that run programs with specified inputs and compare their results with expected values. | To inspect the tested inputs, assertions and expected failures. |
| [`receipts/`](../../receipts/) | Committed example results. | To compare a saved output with the input files and Python function named in it. Write your own outputs to the example's stated local output path. |
| [`standards/`](../../standards/) and [`paper_modules/`](../../paper_modules/) | Detailed contracts and component explanations. | After a component links you to the contract it uses. |
| [`atlas/`](../../atlas/) | Generated navigation data. | To trace a route or a displayed relationship back to its registry. |
| [`paper/`](../../paper/) and [`docs/papers/`](../papers/) | Manuscript source, reading guides and searchable paper text. | To read the argument or rebuild a paper. |

For the shared runtime, the next source files are
[`cli.py`](../../src/microcosm_core/cli.py) and
[`project_substrate.py`](../../src/microcosm_core/project_substrate.py).
The [generated architecture](../../ARCHITECTURE.md) lists how the command handlers,
project-state functions and registries are connected; the
[component map](../../ORGANS.md) lists each component's program and saved results.
The repository's build scripts produce these pages from registry data. To
change an entry, edit that data and run its documented build script.

To try the project, continue with [Quickstart](../../QUICKSTART.md). To change it,
start with [Contributing](../../CONTRIBUTING.md). The
[documentation index](../README.md) lists the other explanations and maintenance
guides.
