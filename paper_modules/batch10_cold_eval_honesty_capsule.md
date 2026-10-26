# Run a small route-comparison simulation

This capsule runs a copied `cold_eval.py` over a public synthetic workspace. It compares two sets of navigation documents: a flat entry set and an idea-first packet with an entry packet, atlas and index. For each task, its score combines expected-reference coverage with heuristics for the first file reached, citations, next moves, unsupported claims and step count. The fixture’s three tasks all favour the idea-first packet, but the two sets contain different kinds of documents; the scorecard audit makes that asymmetry visible.

A negative case changes the exercise manifest to permit injection of expected references; the claim-ceiling check rejects that setting. Injecting the expected answers into the material being scored would make the comparison self-fulfilling. A pass means the copied runner and the fixture checks ran under the stated constraints. It does not show that one route wins for real users or establish a neutral benchmark. The source digest verifies the copied file’s identity, not the validity of its scoring method.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch10_cold_eval_honesty_capsule \
  run --input fixtures/first_wave/batch10_cold_eval_honesty_capsule/input \
  --out .microcosm/component-guides/batch10_cold_eval_honesty_capsule/output \
  --acceptance-out .microcosm/component-guides/batch10_cold_eval_honesty_capsule/acceptance.json
```

The result includes the comparison and scorecard audit under `exercise`. It is written under `.microcosm/component-guides/batch10_cold_eval_honesty_capsule/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the scorecard and source-digest checks; they do not formally prove the scoring algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported cold-eval bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/batch10_cold_eval_honesty_capsule.py) · [fixture input](../fixtures/first_wave/batch10_cold_eval_honesty_capsule/input/) · [tests](../tests/test_batch10_cold_eval_honesty_capsule.py) · [sample result (historical)](../receipts/first_wave/batch10_cold_eval_honesty_capsule/batch10_cold_eval_honesty_capsule_result.json) · [JSON record](batch10_cold_eval_honesty_capsule.json).

See [HELM](https://crfm.stanford.edu/helm/index.html) for a broader approach to transparent evaluation.
