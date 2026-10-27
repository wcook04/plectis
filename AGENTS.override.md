# Compact cold-clone agent entry

This is the first-contact contract for repository-aware agents. It is deliberately
small. [AGENTS.md](AGENTS.md) remains the deep public mutation and authority
contract; open only the section named by the route you select below.

Plectis publishes runnable mechanisms from a working AI-native research and
engineering runtime: formal proof, agent reliability and safety, research and
forecasting, projection-drift control, validators, work landing, and continuity.
Each names the code it runs, the evidence class its result stands on, and the
authority ceiling where it stops. The local record a run writes is that
accountability layer, not the product — do not describe this repository by it,
and do not treat the nearest component as the whole system. Read counts from the
self-model card below rather than asserting them. The companion
[`plectis-erdos`](https://github.com/wcook04/plectis-erdos)
repository contains the Lean source and papers for eight Erdős problems.
Neither repository gives access to private state or makes claims about it.

## Portable operations and formal verification

For workflow repair, guarded publication, behavior-preserving replacement or
public-only report compilation or component replay admission, start with [the runnable study](docs/guides/verification-study.md)
and [formal sources](formal/README.md). Those guides own the current commands,
importable APIs, and proof/runtime boundaries. The routes below retain the
existing reference toolkit and CLI contracts.

## Route the task before reading broadly

Run commands from this repository root. In a source-only clone, use the
`PYTHONPATH=src python3 -m microcosm_core` forms shown here.

### A concrete Plectis goal

Compile the goal into one graph-backed first action before opening source,
receipts, the organ inventory, or the deep agent contract:

```bash
PYTHONPATH=src python3 -m microcosm_core comprehend \
  --first-action "<your goal>" --format text
```

Follow the returned owner, command, validator, receipt, stop condition, and
do-not-edit boundary. If the result does not fit the goal, rerun with a more
specific sentence or open the bounded packet menu:

```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --packet-atlas
```

### Agent entry, cold-clone navigation, routing, or repository organisation

Use the dedicated agent-entry compiler rather than treating the route-map
fixture as the mutation owner:

```bash
PYTHONPATH=src python3 -m microcosm_core agent-entry-composition \
  --root . --task "<your task>" --viewer type_a_agent --card
```

Read `selected_viewer_entry`, `task_route`, `read_run_order`, and
`organ_discoverability_matrix_route` first. The returned
`whole_system_assessment_route` handles whole-system, paper, and Lean-companion
questions. For a no-install first screen:

```bash
./bootstrap.sh --dry-run
PYTHONPATH=src python3 -m microcosm_core first-screen --card .
```

### Whole-system assessment

Do not infer the system from the nearest component or from file counts:

```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --self-model --format text
PYTHONPATH=src python3 -m microcosm_core comprehend --slice mechanism
```

Use the packet's `answer_contract` for whole-system questions: cover every
family, its mechanisms, evidence boundary, and the Lean companion. Use
`--profile whole_substrate_map` only when every organ essence is needed. Stay
in source-body-free packets unless the selected action is mutation or proof.

### Mathematics, Lean theorem status, or paper claims

Plectis exposes formal-method mechanisms and bounded fixtures, not the companion
repository's proof authority. For theorem status, mathematical progress,
remaining open propositions, Lean declarations, or paper-to-source claims, use
the companion repository's tracked machine route:

```bash
python3 scripts/query_corpus.py --ask "<question>"
```

That command is run inside a clone of `plectis-erdos`, not here.
The same boundary applies to `comprehend --first-action` requests to work on
an Erdős proof: the first step opens the paper guide and points to the
companion. An explicit request for this toolkit's toy Lean proof-search lab
still routes to its local fixture and carries the toy-theorem limit.
For a proposal to improve public infrastructure, `--first-action` opens
`CONTRIBUTING.md`: toolkit ideas use this repository's issue route, while Lean
corpus or proof-workflow ideas use the companion's architecture proposal route.
Reading a proposal guide does not authorize edits or imply acceptance.
Do not infer companion mathematics from Plectis organs, receipts, papers, or
private-system descriptions.

For “which papers should I read?”, “what does each paper establish?”, or a
reading-order request, use the clone-local scholarly guide first:

```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --slice papers --format text
```

The clone-local `docs/papers/corpus.json` owns the paper index;
`docs/papers/README.md` is its human route. Papers are exposition, never proof
or claim-status authority.

## Authority and mutation boundaries

- Machine packets route attention; they do not grant source mutation, release,
  proof-correctness, provider-call, production, financial-advice, or
  private-root-equivalence authority.
- `core/organ_registry.json`, the generated atlas, source modules, standards,
  and named receipts remain the authority behind a route card.
- Do not hand-edit `AGENT_ROUTES.md`, `ORGANS.md`, `ARCHITECTURE.md`, or
  `atlas/agent_task_routes.json`. Use the owner builder named in
  [AGENTS.md](AGENTS.md).
- Respect `runner_custody_basis`. Exact-copy macro bodies are evidence to inspect,
  not default edit targets.
- Preserve unrelated staged and unstaged work. Scoped commits are the normal
  landing lane; broad checkpoints require explicit operator authorization.
- Release, publication, hosting, credentialed provider calls, secret export,
  and source mutation are separate authority decisions. A passing receipt does
  not authorize them.

## Repository organization

For tree changes, read [scripts/README.md](scripts/README.md) and
[the architecture guide](docs/maintainers/architecture.md). Keep maintained
programs in their role directories, regression tests in `tests/`, and paper
text separate from programs. Update callers, package paths and generators
together; stage the intended files and run the CI-bound `make check` layout
gate. If an installed repository-organization skill is available, apply it
with these local owners and validation contracts.

## Validation

Use the smallest check that proves the selected change, then widen:

```bash
PYTHONPATH=src python3 -m pytest tests/test_compact_agent_entry.py
PYTHONPATH=src python3 -m pytest tests/test_agent_entry_composition.py
./bootstrap.sh --dry-run
make check
```

Run `make ci` before treating a standalone clone as fully verified. Generated
surfaces must also pass their owner builder/checker. Missing Black or Ruff is
not a failure unless package metadata has begun providing them.

## When to open the deep contract

First read [AGENTS.md](AGENTS.md) only after the compact route names the relevant
mutation class or authority question:

- `Fast Entry For Cold Agents` and `Default Reflexes` for routing behavior;
- `Accepted Public Runtime Spine` for generated atlas ownership;
- `Concept And Mechanism Entry` for doctrine population;
- `Rules` for source, receipt, import, release, and component-specific work;
- `Receipt Floor` and `Anti-Claim` before changing public evidence.

Do not absorb the full file merely to discover the first action.
