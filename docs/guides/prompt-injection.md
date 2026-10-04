# Prompt-injection walkthrough

Follow a prepared example from its input records to the checker and its
result. For broader context, read the [project overview](../overview.md);
the [terminology and file map](../reference/terminology.md) explain names
used in the source.

## One example you can follow

Suppose an AI agent reads a web page containing an instruction to send private
information elsewhere. The user asked the agent to read the page, and did not
authorise the email. The example represents the page, the proposed email and
the decision to block that email as JSON records.

The example uses synthetic records, with references in place of document and
prompt bodies. In
[`source_documents.json`](../../examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle/source_documents.json),
`src_web_page_injection` is labelled `untrusted_web` and has
`instruction_authority: false`. In
[`information_flow_graph.json`](../../examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle/information_flow_graph.json),
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

The [Python module](../../src/microcosm_core/organs/indirect_prompt_injection_information_flow_policy_replay.py)
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

The [tests](../../tests/test_indirect_prompt_injection_information_flow_policy_replay.py)
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
