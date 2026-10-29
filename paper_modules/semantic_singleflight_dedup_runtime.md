# Deduplicate matching local command runs

> **In plain terms.** Running the same command again and again wastes time when nothing it depends on has changed. This component is given a command runner and temporary example commands to run through it as local processes. For each request it builds a label from the command, its folder, the project's state, the contents of the files that matter and a few settings, so requests with the same label can share one run. The output is a saved result showing which requester ran the command and which reused its answer, and a change to one of those files gives a new label.

The fixture exercises a command runner that builds a key from command arguments, working directory, repository state, scoped file content, resource class, and the `PYTHONPATH` and `PYTEST_ADDOPTS` environment values. Matching runs can share or reuse a result; the fixture also checks that a scoped file change changes the key. It writes a result, board and validation receipt.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.semantic_singleflight_dedup_runtime run \
  --input fixtures/first_wave/semantic_singleflight_dedup_runtime/input \
  --out .microcosm/component-guides/semantic_singleflight_dedup_runtime \
  --acceptance-out .microcosm/component-guides/semantic_singleflight_dedup_runtime/acceptance.json
```

Inspect `.microcosm/component-guides/semantic_singleflight_dedup_runtime/semantic_singleflight_dedup_runtime_result.json` for the result and findings.

The runner stores local run state and distinguishes the process that executes the command from callers that reuse its result. The fixture checks those roles with temporary commands; inspect the individual cases in the result.

## What the result means

An empty command is rejected, and changed scoped content must not reuse the old key. Other environment values are not part of the key, so callers must account for changes that could affect a command. The tests use local processes and temporary state; they do not establish a distributed lock or cross-host correctness.

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. There is no component-specific formal proof of the deduplication algorithm; local tests do not establish cross-host behavior.

## Source

[Implementation](../src/microcosm_core/organs/semantic_singleflight_dedup_runtime.py) · [command runner](../src/microcosm_core/engine_room/command_run_singleflight.py) · [input](../fixtures/first_wave/semantic_singleflight_dedup_runtime/input) · [tests](../tests/test_semantic_singleflight_dedup_runtime.py) · [historical sample result](../receipts/acceptance/first_wave/semantic_singleflight_dedup_runtime_fixture_acceptance.json) · [component record](../core/paper_module_capsules.json).
