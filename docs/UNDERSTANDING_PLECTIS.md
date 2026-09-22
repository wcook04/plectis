# Understanding Plectis

Plectis contains Python programs and prepared input files for tasks in AI
research and engineering. The examples include searching an index of Lean
declarations, comparing forecasts with recorded outcomes, comparing generated
files with their source data, and rejecting inconsistent records of an agent's
proposed actions. You can read those inputs, run the example commands and
inspect the output files.

The project commands list a folder's files and write proposed jobs and simulated
work records under `.microcosm/`. The component commands run a named Python
routine on a particular set of inputs. The [quickstart](../QUICKSTART.md) begins
with the file inventory; the prompt-injection example below shows a component
program comparing fields in prepared JSON records.

## What you can do with it

If you point the tour at a folder, it groups files by their names and extensions
in `.microcosm/catalog.json`. If it finds a README, it proposes the task
`readme_onboarding_route` in `.microcosm/routes.json`, then writes a simulated
task result in `.microcosm/work_items.json`. You can inspect how these records
refer to each other. The tour does not run your project's tests or complete
the proposed task on your behalf.

For other programs, use the [specialty index](../ORGANS.md#find-your-specialty).
Each entry lists source files, example commands and saved results. Before using
a result, inspect what the input contains and which operation the Python code
performs: calculating a value from input data and comparing two already-recorded
values establish different facts.

If you came for mathematics, the
[Lean companion](https://github.com/wcook04/plectis-erdos) contains the problem
papers and proof source. Plectis contains tools and examples concerned with
formal proof workflows; the companion is where to read a theorem statement
and its Lean proof. For the wider
argument about the system, use the [paper guide](papers/README.md).

## One example you can follow

Suppose an AI agent reads a web page containing an instruction to send private
information elsewhere. The user asked the agent to read the page, and did not
authorise the email. The example represents the page, the proposed email and
the decision to block that email as JSON records.

The example uses synthetic records, with references in place of document and
prompt bodies. In
[`source_documents.json`](../examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle/source_documents.json),
`src_web_page_injection` is labelled `untrusted_web` and has
`instruction_authority: false`. In
[`information_flow_graph.json`](../examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle/information_flow_graph.json),
`flow_block_web_to_email` connects that source to a proposed email action and
records a `block` verdict. Other rows contain `allow`, `warn` and `review`
verdicts. These labels are supplied in the input files; the program does not
read a hostile page and decide from its text whether it contains an attack.

From the clone root, with Python 3.11 or newer and a macOS / Linux shell:

```bash
PYTHONPATH=src python3 -m plectis indirect-prompt-injection-information-flow-policy-replay \
  run-prompt-injection-bundle \
  --input examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle \
  --out .microcosm/examples/prompt-injection
```

With the supplied inputs, the command prints `pass` and writes
`exported_prompt_injection_flow_bundle_validation_result.json` in the output
directory. Open that JSON file to see the verdicts, replay results and
`authority_ceiling`; the output directory is ignored by git.

The [Python module](../src/microcosm_core/organs/indirect_prompt_injection_information_flow_policy_replay.py)
contains the following functions, among others:

- `validate_source_documents` requires `instruction_authority: false` when
  a source's `trust_label` is untrusted. Giving the web-page row instruction
  authority causes `PROMPT_INJECTION_UNTRUSTED_SOURCE_AUTHORITY`.
- `validate_information_flow_graph` requires each `from_source_id` to name an
  existing source row and its `source_trust_label` to equal that source's
  `trust_label`. This joins the two files by identifier and compares their labels.
- `validate_policy_verdicts` requires a verdict in `policy_verdicts.json` to
  equal the verdict for the same `flow_id` in the information-flow rows, and
  requires `pre_action: true`.

The [tests](../tests/test_indirect_prompt_injection_information_flow_policy_replay.py)
include altered inputs that these functions must reject. A `pass` on the
supplied input means the program accepted those records under its implemented
rules. It does not mean an AI model resisted an attack: no model read a web
page or used an account during this command. To evaluate a deployed agent,
you would also need to observe the actions that agent actually took.

Try changing one field in a disposable copy. Before running this, predict what
the checker should say if an untrusted web page is given authority to issue
instructions.

```bash
exercise_dir=$(mktemp -d /tmp/plectis-prompt-injection.XXXXXX)
git archive HEAD | tar -x -C "$exercise_dir"
cd "$exercise_dir"
python3 - <<'PY'
import json
from pathlib import Path

path = Path(
    "examples/indirect_prompt_injection_information_flow_policy_replay/"
    "exported_prompt_injection_flow_bundle/source_documents.json"
)
data = json.loads(path.read_text())
source = next(
    row
    for row in data["source_documents"]
    if row["source_id"] == "src_web_page_injection"
)
source["instruction_authority"] = True
path.write_text(json.dumps(data, indent=2) + "\n")
PY
PYTHONPATH=src python3 -m plectis indirect-prompt-injection-information-flow-policy-replay \
  run-prompt-injection-bundle \
  --input examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle \
  --out "$exercise_dir/output"
```

The command should exit with status 1 and print `blocked`. In
`output/exported_prompt_injection_flow_bundle_validation_result.json`, the
finding `PROMPT_INJECTION_UNTRUSTED_SOURCE_AUTHORITY` should name
`src_web_page_injection`. That result checks one stated invariant: text labelled
as untrusted cannot carry instruction authority in this bundle. It still says
nothing about whether a live agent would recognise or resist every prompt
injection attack.

## The terms used in the repository

The source keeps some names from the system in which this work developed.
These are the ones you need to follow a component:

| Term in the files | Meaning here |
|---|---|
| Component / organ | An individually named program or group of functions, with input files, output files and pass/fail conditions. `organs/` is the source directory name. |
| Fixture | A prepared input file used in a test. Some fixtures deliberately omit a required field or contain values the program must reject. |
| Replay | Running a program over saved event records. The records may be synthetic; replaying them does not repeat the original actions in a live account. |
| Receipt | A saved result, usually JSON, with the program's status, input/source references and reasons for rejection. In this example it is `exported_prompt_injection_flow_bundle_validation_result.json`. |
| Evidence class | A registry label identifying how a result was obtained, for example by testing prepared inputs or executing an external tool. |
| Authority ceiling | The limit on what may be concluded or done from that result. In the example above, a fixture pass cannot become a claim of general prompt-injection resistance. |
| Route | A stored description of a proposed job. The tour's `readme_onboarding_route`, for example, names README files and the proposed `inspect` action. |
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
| [`core/`](../core/) | JSON lists of component identifiers, program/input paths, result classifications and permitted operations. | To inspect the data used to generate the architecture and component tables. |
| [`examples/`](../examples/) and [`fixtures/`](../fixtures/) | Worked uses and prepared inputs. | To reproduce a component run or understand its test cases. |
| [`tests/`](../tests/) | Python test functions that run programs with specified inputs and compare their results with expected values. | To inspect the tested inputs, assertions and expected failures. |
| [`receipts/`](../receipts/) | Committed example results. | To compare a saved output with the input files and Python function named in it. Write your own outputs to the example's stated local output path. |
| [`standards/`](../standards/) and [`paper_modules/`](../paper_modules/) | Detailed contracts and component explanations. | After a component links you to the contract it uses. |
| [`atlas/`](../atlas/) | Generated navigation data. | To trace a route or a displayed relationship back to its registry. |
| [`paper/`](../paper/) and [`docs/papers/`](papers/) | Manuscript source, reading guides and searchable paper text. | To read the argument or rebuild a paper. |

For the shared runtime, the next source files are
[`cli.py`](../src/microcosm_core/cli.py) and
[`project_substrate.py`](../src/microcosm_core/project_substrate.py).
The [generated architecture](../ARCHITECTURE.md) lists how the command handlers,
project-state functions and registries are connected; the
[component map](../ORGANS.md) lists each component's program and saved results.
The repository's build scripts produce these pages from registry data. To
change an entry, edit that data and run its documented build script.

To try the project, continue with [Quickstart](../QUICKSTART.md). To change it,
start with [Contributing](../CONTRIBUTING.md). The
[documentation index](README.md) lists the other explanations and maintenance
guides.
