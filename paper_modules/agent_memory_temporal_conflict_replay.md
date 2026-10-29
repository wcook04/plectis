# Replay memory updates and conflicts

> **In plain terms.** A memory-keeping assistant must decide when to add, change or delete an entry, especially when new facts clash with old. This component is given a recorded sequence of example memory changes, the clashes between entries, and a later replay of the sequence. It checks that each later edit or deletion rests on an earlier entry, cited evidence and correct timing, and it examines source trust and priority rather than accepting each change's label alone. The output lists the checks and findings, so someone can see which recorded memory changes were backed by evidence. It works from recorded evidence only, so it says nothing about how well a live memory system remembers or protects private data.

This replay checks a sequence of public memory episodes, their conflict edges and their later replay. It validates ADD, UPDATE, DELETE and NOOP decisions and checks whether a later update or deletion is supported by an earlier write, evidence handles and temporal ordering. The checker also examines priority and source-trust evidence rather than accepting the decision label alone.

A stale preference override without the required downgrade evidence is a rejected case. The paired memory-on and memory-off records let the fixture check its declared answer delta against replay references. This is a check of recorded evidence, not a measurement of how well a live memory system remembers or protects private data. Source digest checks identify the supplied copies; they do not prove the underlying memory algorithm correct.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_memory_temporal_conflict_replay \
  run --input fixtures/first_wave/agent_memory_temporal_conflict_replay/input \
  --out .microcosm/component-guides/agent_memory_temporal_conflict_replay/output \
  --acceptance-out .microcosm/component-guides/agent_memory_temporal_conflict_replay/acceptance.json
```

The result records the replay checks and findings for the memory episodes. It is written under `.microcosm/component-guides/agent_memory_temporal_conflict_replay/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the memory conflict and replay checks; they do not formally prove the memory conflict algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported memory bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/agent_memory_temporal_conflict_replay.py) · [fixture input](../fixtures/first_wave/agent_memory_temporal_conflict_replay/input/) · [tests](../tests/test_agent_memory_temporal_conflict_replay.py) · [sample result (historical)](../receipts/first_wave/agent_memory_temporal_conflict_replay/agent_memory_temporal_conflict_replay_result.json) · [JSON record](agent_memory_temporal_conflict_replay.json).

For background on agent memory, see [Generative Agents](https://arxiv.org/abs/2304.03442) and [MemGPT](https://arxiv.org/abs/2310.08560).
