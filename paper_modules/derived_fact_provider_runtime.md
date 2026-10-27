# Resolve facts from a fixture registry

> **In plain terms.** Answering questions about files, such as how many there are, takes a repeatable recipe, and one missing file should not stop the other answers. This component is given a short list of fact recipes and a temporary example folder of files. Each recipe reads one value from a data file, counts files whose names match a pattern, or counts the files a version-tracking tool follows. The output lists each value found, shows a missing file as an error entry instead of stopping, and rejects an unknown kind of recipe. A value found this way describes only those files and that recipe, and says nothing about whether a claim built on it is true.

`derived_fact_provider_runtime` evaluates small registries of facts against temporary fixture roots. A fact can read a JSON value by pointer, count files by glob, or call a named Git-index counter. The result reports values and provider errors as data, so a missing source does not crash the entire ledger.

## Run the example

From the repository root, with Python 3.11 or later and Git on `PATH`:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.derived_fact_provider_runtime run \
  --input fixtures/first_wave/derived_fact_provider_runtime/input \
  --out .microcosm/component-guides/derived_fact_provider_runtime \
  --acceptance-out .microcosm/component-guides/derived_fact_provider_runtime/acceptance.json
```

The runner creates temporary case roots, evaluates the registries and writes result, board, validation and acceptance JSON. The positive pointer-and-glob case expects a count of seven from a JSON document and two Markdown files. The callable case uses a temporary Git index; it counts tracked files, not untracked ones.

## What this checks

The engine implements JSON Pointer escaping and list indices, glob exclusions and named callable lookup. In the missing-source case it returns a `FileNotFoundError` row and a degraded provider receipt; an unknown provider type is also rejected. The runner recomputes the cases and checks the expected values and error classes.

## Limits

A resolved value is a fact about the supplied files and registry recipe. It does not establish that a prose claim based on that value is true, or validate a complete external fact registry. Git is needed for the callable fixture.

## Verification

The direct example does not invoke the shared gate. In `make component-replays`, this component’s registered route passes through the [Dafny replay admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement over host-supplied observations. It does not prove this component’s algorithm.

## Sources

- [Runner](../src/microcosm_core/organs/derived_fact_provider_runtime.py), [provider engine](../src/microcosm_core/engine_room/derived_fact_provider_engine.py), [fixture cases](../fixtures/first_wave/derived_fact_provider_runtime/input) and [engine tests](../tests/test_engine_room_derived_fact_provider_engine.py).
- [Historical result](../receipts/first_wave/derived_fact_provider_runtime/derived_fact_provider_runtime_result.json) and [component record](../core/paper_module_capsules.json).
- [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901) specifies JSON Pointer.
