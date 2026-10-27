# Check a research replication record

This validator reads research replay rows describing contributions, rubric, artifacts, metric scripts and rerun evidence. It checks the declared artifact-hash roster against execution artifacts and reports findings alongside a validation receipt. For the supported public `sum_field` metric specification, it hashes the metric and input bodies, computes a sum over the input rows, and compares the output and its hash with the declared artifacts.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.research_replication_rubric_artifact_replay run \
  --input fixtures/first_wave/research_replication_rubric_artifact_replay/input \
  --out .microcosm/component-guides/research_replication_rubric_artifact_replay \
  --acceptance-out .microcosm/component-guides/research_replication_rubric_artifact_replay/acceptance.json
```

Inspect `.microcosm/component-guides/research_replication_rubric_artifact_replay/research_replication_rubric_artifact_replay_result.json` for the result and findings.

The fixture includes deliberate negative cases. A passing run means the expected failures were detected alongside the checks of the supplied replay, not that an external study was independently reproduced.

## What the result means

A replay citing an undeclared artifact hash or relying on a report without the required artifact replay is rejected. The interpreter handles the supported metric specification, not arbitrary metric scripts. It does not independently reproduce an outside paper or establish a benchmark result.

Related reading: [ACM Artifact Review and Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current).

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. There is no component-specific formal proof of the metric interpreter, and the tests do not establish an outside replication.

## Source

[Implementation](../src/microcosm_core/organs/research_replication_rubric_artifact_replay.py) · [input](../fixtures/first_wave/research_replication_rubric_artifact_replay/input) · [tests](../tests/test_research_replication_rubric_artifact_replay.py) · [historical sample result](../receipts/acceptance/first_wave/research_replication_rubric_artifact_replay_fixture_acceptance.json) · [component record](../core/paper_module_capsules.json).
