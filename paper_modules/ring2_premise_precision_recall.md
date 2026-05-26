# Ring-2 Premise Precision Recall

`ring2_premise_retrieval_precision_recall_harness` is the public Microcosm
organ for evaluating copied Ring-2 premise retrieval rankings against
after-the-fact labels.

The organ computes precision and recall per problem, then classifies the result
as `retrieval_hit`, `partial_retrieval_miss`, `retrieval_miss`, or
`proof_failure_despite_hit`. That distinction matters because a failed proof
with all needed premises retrieved is a different failure than a missing premise
retrieval path.

## Authority Boundary

This organ does not run Lean or Lake, call providers, emit proof bodies, tune
retrieval on test answers, claim benchmark performance, prove theorem
correctness, or authorize release. Its labels are metric labels only; they are
not allowed to flow into provider context recipes.

## Runtime Surfaces

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.ring2_premise_retrieval_precision_recall_harness run --input fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input --out receipts/first_wave/ring2_premise_retrieval_precision_recall_harness
PYTHONPATH=src python3 -m microcosm_core.cli ring2-premise-retrieval-precision-recall-harness run-precision-recall-bundle --input examples/ring2_premise_retrieval_precision_recall_harness/exported_ring2_precision_recall_bundle --out receipts/runtime_shell/demo_project/organs/ring2_premise_retrieval_precision_recall_harness
```

## Body-Floor Import

The fixture and exported bundle both carry exact copied source artifacts under
`source_artifacts/` for the Ring2 aggregate report, graph-variant run summary,
graph comparison, and problem-source manifest. The validator treats those four
digest-matched files as `source_open_body_imports` with
`body_in_receipt=false`: workingness can count the real macro receipt bodies,
while receipts expose only import ids, target refs, and digest status.

## Negative Cases

- `oracle_labels_in_ranking` rejects oracle-needed premise ids inside rankings.
- `proof_body_leakage` rejects proof, provider, or private body fields.
- `test_split_tuning_attempt` rejects retrieval tuned on test labels.
- `metric_overclaim` rejects proof, benchmark, provider, release, or publication authority claims.
- `missing_adversarial_decoy` rejects a metric harness without a decoy miss case.

## Why It Matters

Premise retrieval should be measurable without becoming theorem authority. This
organ gives Microcosm a compact public harness for asking whether a retrieval
path missed the needed support, hit the support but failed later, or hid a
dangerous truth-side shortcut inside the public runtime.
