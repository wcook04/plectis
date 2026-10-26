# Run the Engine Room fixture composition

The Engine Room demo composes bounded fixture checks from several Engine Room modules. Its accepted wrapper runs a controller audit of the configured modules, their fixture exercises and the named capabilities they cover. For example, `bridge_campaign_dag` is one expected capability, called a target in the audit. It writes a result, board and validation receipt, with an optional acceptance receipt.

## Run the example

From the repository root, with Python 3.11 or newer, Git and a Lean executable on `PATH` for the Lean fixture:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.engine_room_demo run \
  --input fixtures/first_wave/engine_room_demo/input \
  --out .microcosm/component-guides/engine_room_demo \
  --acceptance-out .microcosm/component-guides/engine_room_demo/acceptance.json
```

The result compares the positive controller audit and a negative case naming a nonexistent target with their expectations. A passing matrix includes detecting the missing target. The component tests also change a subcomponent fixture and check that the composed result changes.

The wrapper’s acceptance does not by itself admit each individual staged module as an accepted component. Passing this composition describes these public fixtures, not production readiness, complete security or a general theorem prover. [pytest fixtures](https://docs.pytest.org/en/stable/reference/fixtures.html) provide background on composing test setup and checks.

## Verification

The composition includes a Lean exercise for conjunction introduction and disjunction commutativity; it needs Lean on `PATH` and checks the candidate proofs and reported axioms. `make component-replays` also applies the [shared Dafny admission check](../formal/replay/README.md) to the demo’s observed source, input, claim policy and receipt. The direct command above does not invoke that admission check, and neither check proves the demo’s Python composition algorithm.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/engine_room_demo.py) and [composition tests](../tests/test_engine_room_demo.py) and [wrapper tests](../tests/test_engine_room_demo_organ.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_demo/input/); [historical sample result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json).
- [JSON record](../paper_modules/engine_room_demo.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
