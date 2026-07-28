# Compact cold-clone agent entry

This is the first-contact contract for repository-aware agents. It is deliberately
small. [AGENTS.md](AGENTS.md) remains the deep public mutation and authority
contract; open only the section named by the route you select below.

Plectis is the runnable machinery demonstration. The companion
[`plectis-lean-erdos249-257`](https://github.com/wcook04/plectis-lean-erdos249-257)
repository is the machine-checked mathematics demonstration. Neither repository
is an entrypoint into private state.

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
`organ_discoverability_matrix_route` first. They distinguish the safe first
read, the selected task route, its evidence, and the source owner. For a
no-install first screen:

```bash
./bootstrap.sh --dry-run
PYTHONPATH=src python3 -m microcosm_core first-screen --card .
```

### Whole-system assessment

Do not infer the system from the nearest component or from file counts:

```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --self-model
PYTHONPATH=src python3 -m microcosm_core comprehend --slice mechanism
```

Use `--profile whole_substrate_map` only when every organ essence is genuinely
needed. Stay in source-body-free packets unless the selected action is mutation
or proof.

### Mathematics, Lean theorem status, or paper claims

Plectis exposes formal-method mechanisms and bounded fixtures, not the companion
repository's proof authority. For theorem status, mathematical progress,
remaining open propositions, Lean declarations, or paper-to-source claims, use
the companion repository's tracked machine route:

```bash
python3 scripts/query_corpus.py --ask "<question>"
```

That command is run inside a clone of `plectis-lean-erdos249-257`, not here.
Do not infer companion mathematics from Plectis organs, receipts, papers, or
private-system descriptions.

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
