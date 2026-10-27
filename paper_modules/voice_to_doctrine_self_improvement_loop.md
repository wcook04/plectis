# Validate a lesson-to-owner record

This validator checks public records that connect a local lesson to an owner surface, validation and closeout. It reads a propagation policy, owner-surface references and lesson rows, and writes a body-free report.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.voice_to_doctrine_self_improvement_loop run \
  --input fixtures/first_wave/voice_to_doctrine_self_improvement_loop/input \
  --out .microcosm/component-guides/voice_to_doctrine_self_improvement_loop \
  --acceptance-out .microcosm/component-guides/voice_to_doctrine_self_improvement_loop/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## Public Mechanics

The checks resolve referenced public paths and anchors and compare each lesson with the declared sequence and allowed outcomes. A record claiming global promotion without owner validation is rejected, as is treating a receipt alone as progress. Tests mutate references to ensure the result follows the actual target rather than a stored expected label.

## Reader Proof Boundary

The validator checks records and references; it does not itself make the changes described by a lesson. It cannot establish that private operator speech or private thread content has been faithfully represented.

## Public-Safe Body Handling

Public records use references rather than exporting raw operator voice or private thread bodies. The validator rejects either body in the public input.

## Shape

A lesson names the pressure, its owner surface, the action or capture, validation and closeout. These fields make the record inspectable; they do not perform the action.

## Anti-Claim

A passing record is evidence of the checked public contract, not permission to promote doctrine or modify a live ledger.

## Verification

Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/voice_to_doctrine_self_improvement_loop.py) · [Example input](../fixtures/first_wave/voice_to_doctrine_self_improvement_loop/input/) · [Tests](../tests/test_voice_to_doctrine_self_improvement_loop.py) · [Historical sample result](../receipts/first_wave/voice_to_doctrine_self_improvement_loop/voice_to_doctrine_self_improvement_loop_result.json) · [JSON record](voice_to_doctrine_self_improvement_loop.json)

Background: [NASA Lessons Learned Information System](https://llis.nasa.gov/).
