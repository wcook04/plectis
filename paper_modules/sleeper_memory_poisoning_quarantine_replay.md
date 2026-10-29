# Check a memory quarantine and rollback record

> **In plain terms.** An assistant with long-term memory can save a poisoned note that does harm when retrieved later. This component is given made-up records, holding references rather than the notes themselves, of a poisoned write, its quarantine, a later retrieval and a rollback, meaning removal. It checks where the memory came from and the links between the quarantined note, the retrieval check, the quarantine decision record and the re-run record. The output lists findings, and a retrieval that admits a quarantined note or fails to cite that decision record is rejected. These invented records test the policy checks only, not what happens in a real session or whether a live memory system is secure.

This replay examines public metadata for a poisoned memory write, quarantine, later retrieval and rollback. It checks provenance and links between the quarantined memory, retrieval gate, audit reference and cold-rerun record. Results contain references and findings rather than memory bodies.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.sleeper_memory_poisoning_quarantine_replay run \
  --input fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay/input \
  --out .microcosm/component-guides/sleeper_memory_poisoning_quarantine_replay \
  --acceptance-out .microcosm/component-guides/sleeper_memory_poisoning_quarantine_replay/acceptance.json
```

Inspect `.microcosm/component-guides/sleeper_memory_poisoning_quarantine_replay/sleeper_memory_poisoning_quarantine_replay_result.json` for the result and findings.

The fixture contains intentionally bad records as well as the example chain. A passing run records that the expected bad cases were detected; it does not establish what happened in a real user session.

## What the result means

A retrieval that admits a quarantined memory or fails to cite its quarantine audit is rejected. These synthetic records test the policy checks; they do not demonstrate security of a live memory system.

Related reading: [Sleeper Agents](https://arxiv.org/abs/2401.05566), [AgentPoison](https://arxiv.org/abs/2407.12784), [MemoryGraft](https://arxiv.org/abs/2512.16962), [Hidden in Memory](https://arxiv.org/abs/2605.15338).

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. There is no component-specific formal proof of the quarantine checks; the fixture does not establish live memory security.

## Source

[Implementation](../src/microcosm_core/organs/sleeper_memory_poisoning_quarantine_replay.py) · [input](../fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay/input) · [tests](../tests/test_sleeper_memory_poisoning_quarantine_replay.py) · [historical sample result](../receipts/acceptance/first_wave/sleeper_memory_poisoning_quarantine_replay_fixture_acceptance.json) · [component record](../core/paper_module_capsules.json).
