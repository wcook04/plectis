# Plectis documentation

Plectis publishes tools and worked examples for doing research with AI while
keeping the work understandable and checkable. This directory explains the
project, walks through examples and records how to maintain the software.

<a id="start"></a>

## Start here

1. Read the [project overview](overview.md) to understand why these tools exist
   and how they relate to the mathematics and website.
2. Run the [quickstart](../QUICKSTART.md) from a clone. No package installation
   or model API key is needed for the basic commands.
3. Choose one [worked guide](guides/README.md) and follow its input, code and
   result. You do not need to read the complete catalogue first.

## Human guides

| You need… | Read… |
|---|---|
| An explanation of the project and related approaches | [Project overview](overview.md) |
| A complete example to run and change | [Worked guides](guides/README.md) |
| Help with older names used in source files | [Terminology and file map](reference/terminology.md) |
| A tool for a particular subject | [Component map](../ORGANS.md#find-your-specialty) |
| The research argument and supporting papers | [Paper guide](papers/README.md) |
| Mathematical results, open questions and Lean proofs | [Plectis Erdős](https://github.com/wcook04/plectis-erdos) |

## Reference

The [reference index](reference/README.md) collects the component catalogue,
architecture maps, source records and release information. These answer
specific questions once you have chosen a component. The
[Lean companion reference](reference/lean-companion.md) records which edition
of the mathematics repository this toolkit refers to.

## Contribute and maintain

Start with [Contributing](../CONTRIBUTING.md). The
[maintainer index](maintainers/README.md) points to the implementation map,
test commands, document generators, packaging rules and release instructions.

| Directory | What belongs there |
|---|---|
| [`guides/`](guides/README.md) | Worked examples with runnable commands and an explanation of their results. |
| [`reference/`](reference/README.md) | Lookups, recorded versions and links to generated maps. |
| [`maintainers/`](maintainers/README.md) | Instructions for changing and verifying the software. |
| [`governance/`](governance/public-boundary.md) | Rules about public source, claims and publication. |
| [`papers/`](papers/README.md) | The paper catalogue, PDFs and searchable manuscript text. |

The root README is the short introduction; [overview.md](overview.md) carries
the fuller explanation. Generated reference files keep their established root
paths so existing tools and links continue to work.

## Use your own coding agent

Open a clone in a coding agent that can read files and run shell commands.
Ask it to read `AGENTS.override.md`, then give it a concrete question or change.
The [agent quickstart](../QUICKSTART.md#use-your-own-coding-agent) includes a
sample request and explains where to save results. Record the checkout commit,
commands, inputs, outputs and what the run leaves untested.

For proof search or mathematical contributions, follow the separate
[mathematics agent guide](https://github.com/wcook04/plectis-erdos/blob/main/docs/agents/README.md#start-with-current-public-work).
Its proof evidence belongs to that repository.

## Generated reference and agent instructions

Use the [reference index](reference/README.md) to find generated maps.
[AGENTS.override.md](../AGENTS.override.md) gives agents their first files and
commands; [AGENTS.md](../AGENTS.md) governs edits. The
[architecture maintenance guide](maintainers/architecture.md#keep-each-document-in-its-role)
identifies each generator. Change its source and regenerate the output.

## Troubleshooting

| Symptom | Next step |
|---|---|
| `No module named plectis` | Run from the clone root with `PYTHONPATH=src`, or use the Python interpreter from the environment where you installed Plectis. |
| `plectis: command not found` | Use `.venv/bin/plectis` on macOS/Linux or `.venv\Scripts\plectis.exe` on Windows; activating the environment also puts it on your path. |
| A component reports unavailable dependencies | Read its entry in [ORGANS.md](../ORGANS.md). Individual examples can require external tools. |
| Port 8765 is already in use | Choose another port with `--port`, then open that port in your browser. |
