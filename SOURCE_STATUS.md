# Plectis Source Status

Last updated: 2026-09-12

This repository contains the Plectis Python package, example inputs, saved
results from earlier runs, tests, documentation, and license files. The
[component map](ORGANS.md) lists 88 components, called *organs* in the code and
JSON files. Each has a stated task, input files, a command to run, and limits on
what its results establish. [Understanding Plectis](docs/UNDERSTANDING_PLECTIS.md)
works through one example.

Microcosm is the former public name. It remains only where compatibility or
technical continuity still requires it: the `microcosm_core` import path, the
legacy `microcosm` command alias, `.microcosm/` local state, historical source
paths, fixture names, and previously published links.

## What is public here

- The public source of record is the canonical Plectis
  repository at <https://github.com/wcook04/plectis>.
- You can inspect the source and run the commands below from a fresh clone
  without access to the private development repository.
- The website at <https://wcook04.github.io/plectis/> presents this public source
  and its release documents. If the website and repository
  disagree, the repository files and committed release receipts are the source
  of record.
- The retired `wcook04/microcosm-substrate` repository and old Pages URL are
  historical links, not the current development repository.
- The package is licensed under Apache-2.0; see [LICENSE](LICENSE),
  [NOTICE](NOTICE), and [Provenance](PROVENANCE.md).

## What is not public here

- The larger private working root, private ledgers, operator notes, browser
  state, account material, secrets, recipient-send state, and unpublished
  reference material are outside this repository.
- Private raw video/capture sources are not part of the public source release.
  The [recorded walkthroughs](https://wcook04.github.io/plectis/#demo-videos)
  are hosted separately and linked from the README.
- This repository is not a hosted service, production security product, legal or
  financial advice system, trading system, or whole-system correctness proof.

## Reviewer path

Run these commands from the clone root with Python 3.11 or newer and a shell
such as Bash or Zsh. No package installation or model account is needed.
[Quickstart](QUICKSTART.md#1-first-result) gives the clone command and setup.

First, run the supplied bootstrap example:

```bash
./bootstrap.sh
```

This runs the supplied inputs in
`fixtures/first_wave/pattern_binding_contract/input` and searches selected text
files for tokens listed in the [scan policy](core/private_state_forbidden_classes.json).
The [security runbook](docs/maintainers/security-runbook.md) explains the file
selection and scan limits. A successful run prints `Plectis cold-clone probe passed` and
exits with code 0; a failed run exits with a nonzero code. It writes the summary
to `.microcosm/cold_clone_probe.json` and component output files under
`.microcosm/cold_clone_probe/`. These are results of your local run, separate
from the committed files under [`receipts/`](receipts/).

Then print the stored component descriptions and look up a suggested command:

```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --slice mechanism --format text
PYTHONPATH=src python3 -m microcosm_core comprehend --first-action "evaluate prompt injection defenses" --format text
```

The first command prints one stored description per component, grouped by
family. It selects text from the [paper-module summaries](core/paper_module_capsules.json),
[component descriptions](core/mechanism_sources.json), and
[component map data](core/organ_atlas.json). It does not run the components or
verify those descriptions against their code.

The second command matches words in the question to component names and task
descriptions. For this question, it prints a prompt-injection example command,
input and output paths, and the stated limits. It does not execute that command.
Replace the quoted question with your own; see
[Find a component command](FIRST_ACTION.md) for how to interpret the result and
choose an output directory before running it. Both lookups print to the terminal
without writing result files.

To inspect the local repository and the supplied claim limits:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core authority --card
```

`hello` prints an introduction and suggested commands. `tour` inventories the
local files, proposes tasks from that inventory, and creates a simulated work
record; it does not execute the project's tests. Its files, including
`catalog.json`, `routes.json`, and `work_items.json`, go under `.microcosm/`.
`authority --card` prints the supplied component classifications, result-file
paths, and limits on permitted actions and conclusions. The supplied permission
flags for publication, source changes, and provider calls are false. `hello`
and this authority query print to the terminal without writing result files.

After [installation](QUICKSTART.md#2-install), you can replace
`PYTHONPATH=src python3 -m microcosm_core` with `plectis` in these commands. The
legacy `microcosm` command remains a compatibility alias for existing local
scripts and historical receipts.

[Release review](RELEASE_REVIEW.md) connects the software claims to input files,
commands, and saved results. The [validation guide](docs/maintainers/validation.md)
explains `make smoke` and the other test and package commands, including their
prerequisites and output locations. For the reading order, return to the
[README](README.md) or the [documentation index](docs/README.md).
