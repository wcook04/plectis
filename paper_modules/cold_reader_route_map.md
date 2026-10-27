# Check quickstart commands and their references

`cold_reader_route_map` validates a JSON list of introductory commands. Each route includes documentation links, saved result links and a description of what a reader should see. The validator checks these against public source text and local files so maintainers can find stale quickstart entries.

## Run the example

From the repository root, with Python 3.11 or later:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.cold_reader_route_map run \
  --input fixtures/first_wave/cold_reader_route_map/input \
  --out .microcosm/component-guides/cold_reader_route_map \
  --acceptance-out .microcosm/component-guides/cold_reader_route_map/acceptance.json
```

The command writes result, board and validation JSON. Inspect the source-replay rows for each command's text support, resolved documentation anchors and saved results with passing status.

## What this checks

The validator requires the configured routes and their ordering. It looks for command terms and claimed descriptive signals in the source/documentation corpus, resolves heading links, and reads linked JSON results. An exported-bundle test changes a command to `microcosm hallucinated-import`; validation blocks with `COLD_ROUTE_COMMAND_SOURCE_UNSUPPORTED`. Separate tests change a heading anchor or a linked result's status.

## Limits

Text matching does not execute each route or prove that a command behaves as described. A link to a passing historical result is evidence of that saved run, not a fresh execution. These checks can detect several forms of documentation drift but cannot establish that a newcomer understands the instructions.

## Verification

The direct example does not invoke the shared gate. In `make component-replays`, this component’s registered route passes through the [Dafny replay admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement over host-supplied observations. It does not prove this component’s algorithm.

## Sources

- [Implementation](../src/microcosm_core/organs/cold_reader_route_map.py), [route inputs](../fixtures/first_wave/cold_reader_route_map/input) and [tests](../tests/test_cold_reader_route_map.py).
- [Historical result](../receipts/first_wave/cold_reader_route_map/cold_reader_route_map_result.json) and [canonical description](../core/paper_module_capsules.json).
- [Diátaxis](https://diataxis.fr/) provides a documentation framework, rather than a validation guarantee.
