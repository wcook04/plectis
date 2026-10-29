# Measure premise retrieval against labelled examples

> **In plain terms.** A tool that suggests facts for a proof can be scored on how well its suggestions match what the proof needed. This component is given, for each problem, the tool's ranked suggestions, with a fixed number of places, and a separate list of the facts needed. It counts the needed facts found, then computes precision, the share of places holding a needed fact, and recall, the share of needed facts found. It reports both for each problem and overall, so the tool can be judged, and rejects any row that admits using the answer key.

This harness compares retrieved premise rankings with separately supplied needed-premise labels. It recomputes hits, precision and recall from the public examples and reports aggregate metrics. For each row, precision is the number of unique hits divided by its declared top-k slots; recall is hits divided by needed premises. Aggregate precision uses total hits divided by total declared top-k slots, while aggregate recall uses total hits divided by total needed premises.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.ring2_premise_retrieval_precision_recall_harness run \
  --input fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input \
  --out .microcosm/component-guides/ring2_premise_retrieval_precision_recall_harness \
  --acceptance-out .microcosm/component-guides/ring2_premise_retrieval_precision_recall_harness/acceptance.json
```

Inspect `.microcosm/component-guides/ring2_premise_retrieval_precision_recall_harness/ring2_precision_recall_result.json` for the result and findings.

The checker consumes supplied rankings and labels; it does not perform retrieval. It checks the declared separation of labels from rankings, and reports per-row metrics alongside the aggregate.

## What the result means

Oracle labels must not enter the ranking inputs. A row declaring that they did is rejected; the check cannot prove how the rankings were produced. These fixture metrics describe the supplied examples and do not prove a theorem or establish general retrieval performance.

Related reading: [TREC evaluation measures](https://trec.nist.gov/pubs/trec20/appendices/measures.pdf), [precision/recall metric API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html), [Sledgehammer](https://isabelle.in.tum.de/doc/sledgehammer.pdf).

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. There is no component-specific formal proof of this metric computation; the tests do not prove retrieval correctness or label validity.

## Source

[Implementation](../src/microcosm_core/organs/ring2_premise_retrieval_precision_recall_harness.py) · [input](../fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input) · [tests](../tests/test_ring2_premise_retrieval_precision_recall_harness.py) · [historical sample result](../receipts/acceptance/first_wave/ring2_premise_retrieval_precision_recall_harness_fixture_acceptance.json) · [component record](../core/paper_module_capsules.json).
