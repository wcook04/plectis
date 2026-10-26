# Recorded work landing: check the evidence

This replay checks recorded agent work against a landing policy. It reads claimed paths, validation and commit-attempt references, HEAD before and after, blocker capture, and ledger closeout. It writes result, board, validation and acceptance receipts. It does not perform Git operations.

The fixture includes a landed claim with no HEAD advance and a commit attempt recorded before validation. Both must be detected for the negative-case matrix to pass. The exported bundle also checks copied source-body digests and required anchors; those checks identify the copied material, not the correctness of its algorithms.

## Run the example

From the repository root, with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.durable_agent_work_landing_replay run \
  --input fixtures/first_wave/durable_agent_work_landing_replay/input \
  --out .microcosm/component-guides/durable_agent_work_landing_replay \
  --acceptance-out .microcosm/component-guides/durable_agent_work_landing_replay/acceptance.json
```

The command prints the fixture status and writes receipts in the specified directory. The explicit acceptance path matters: without it, this runner writes its acceptance receipt to the public-root default. A pass reports that the supplied rows and expected failures meet this contract; it does not prove that a real commit landed or authorize one. The provenance ideas are related to [W3C PROV](https://www.w3.org/TR/prov-overview/) and [SLSA](https://slsa.dev/spec/).

## Verification

The focused tests exercise the landing rules and source-digest checks; they do not prove the validator algorithm. `make component-replays` runs the exported landing bundle through the [shared Dafny admission check](../formal/replay/README.md), which checks agreement of the observed source, input, claim policy and receipt. The fixture command above does not itself invoke that check.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/durable_agent_work_landing_replay.py) and [focused tests](../tests/test_durable_agent_work_landing_replay.py).
- [Fixture inputs](../fixtures/first_wave/durable_agent_work_landing_replay/input/); [historical sample result](../receipts/first_wave/durable_agent_work_landing_replay/durable_agent_work_landing_replay_result.json).
- [JSON record](../paper_modules/durable_agent_work_landing_replay.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
