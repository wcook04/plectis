# Deciding whether a proof sketch reduced its target or renamed it

A proof either checks or it does not, and a checker says nothing about an
incomplete one.  An agent that leaves `sorry` behind has produced *something* —
the question is whether what remains to prove is easier than what it started
with, or the same problem wearing different notation.  That question is
semantic, it is the one a search loop has to answer thousands of times, and
some instances of it are decidable by the kernel.

This document describes what is decidable, what this repository measured, and
what the evaluator in `scripts/residual_evaluator.py` does and does not settle.

## The reported failure

Google DeepMind's AlphaProof Nexus paper ([arXiv:2605.22763][nexus]) rates
candidate proof sketches with a language model, because formal verification
gives a binary signal and evolutionary search needs a graded one.  Its raters
judge, among other things, "the plausibility of remaining goals".  Its failure
analysis reports:

> the agent frequently offloaded a problem's core difficulty into a single
> `sorry` within a helper lemma that reiterated the target statement in a
> slightly different form

and, of that behaviour:

> Explicitly prompting against this behavior failed to prevent it.

Prompting is the wrong instrument.  Whether a helper lemma reiterates its
target is a relation between two propositions, and a proof assistant can
sometimes settle it outright.

## Where the instrument came from

This repository is a formalisation programme over eight Erdős problem programmes,
and its output is structural: an exact carry normal form equivalent to
irrationality for #68, a complete measure classification of the Mersenne
achievement set for #257, the exact rank `2^e + 1` and an explicit odd-core
basis of the dyadic totient kernel for #249, a first integral of the complex
Newton flow for #1041, exact three-prime prefix-LCM dynamics for #269, and proved no-go
theorems that close named strategies rather than gesture at difficulty.
[RESULTS](../RESULTS.md) states each result and the exact point where it stops.

Holding that line requires deciding, repeatedly, which of a programme's many
reformulations are progress.  The instrument described here was built for that
job, and it was turned inward first.

`ErdosProblems/DemandLedger/Hyp.lean` provides `hypOf%`, a term elaborator that
takes the type of a named hypothesis binder directly from the kernel's
`ConstantInfo` and returns it as a standalone `Prop`.  It does not pretty-print
and reparse: the extracted proposition is the binder type or elaboration fails.
An unresolved mathematical demand, which previously existed only in binder
position, becomes an object that can be named, compared and proved about.

The mechanism is intentionally local. A submitted target and its remaining
obligations are compared as exact propositions, one sketch at a time, against a
bounded proof budget. It does not infer a live corpus census from historical
binder extraction, and it does not turn an authored relation label into a
kernel verdict. Current registered relations are navigated through
`python3 scripts/query_semantic.py`; current problem status and continuation
obligations remain owned by `python3 scripts/query_corpus.py` and
`docs/claims.json`.

## Restatement and reuse use the integrated corpus

The retired two-problem productivity report counted textual references between
Lean declarations and divided a historical sample by an authored
``is_restatement`` label.  That was neither a kernel restatement check nor a
current measurement of the eight public programmes.  Textual fan-in also does
not establish mathematical importance, novelty or significance, so the report
and its standalone builder are no longer public infrastructure.

The current system keeps each responsibility with its existing owner:

- [`docs/claims.json`](../claims.json) records reviewed public status and exact
  Lean addresses for the selected registered claims; it does not assert that
  every mathematical statement in every paper is registered.
- [`docs/semantic_corpus.json.gz`](../semantic_corpus.json.gz), queried with
  `python3 scripts/query_semantic.py`, owns cross-paper statement and relation
  navigation across the current corpus.  Relation labels are navigation and
  do not themselves certify equivalence, novelty or value.
- [`docs/PALOMAR_RESULT_SHOWCASE.json`](../PALOMAR_RESULT_SHOWCASE.json) owns the
  current candidate universe, screening dispositions and reader-facing signal
  order without turning that screening into proof or peer review.
- `scripts/residual_evaluator.py` remains the exact bounded route for asking
  whether a particular proposed reduction leaves its target, an equivalent
  residual or an explicitly stronger obligation.  Its answer is about the
  submitted Lean propositions, not an aggregate score over an old sample.

## What the evaluator decides

`scripts/residual_evaluator.py` asks Lean three bounded questions about a
sketch that targets `P` and leaves residual obligations `R₁ … Rₙ`:

1. **Sufficiency.** Is `R₁ ∧ … ∧ Rₙ → P` provable within the budget?
2. **Restatement.** For each `Rᵢ` separately, are *both* `P → Rᵢ` and
   `Rᵢ → P` provable?
3. **Refutation.** Is the residual demand provably false?

Four outcomes follow, and only two are vetoes:

| Verdict | Meaning |
|---|---|
| `endpoint_equivalent` | Some single residual is provably equivalent to the target. The sketch renamed the problem. |
| `residual_refuted` | The residual demand is provably false. The sketch rests on something untrue. |
| `strict_decomposition_candidate` | The residuals suffice, and no individual residual is provably equivalent to the target. |
| `unknown_relation` | The budget settled nothing. Not progress, not falsity, not separation. |

Two details matter more than they look.

**Restatement is tested per residual and in both directions.**  Testing
`P → ⋀Rᵢ` instead is wrong: a target implies every legitimate consequence, so
that criterion convicts every correct decomposition.  An earlier version of
this evaluator did exactly that and flagged a textbook base-plus-step induction
split as the failure it is the opposite of.

**A false accusation is the expensive error.**  Requiring two kernel proofs on
one residual means a well-disguised restatement can escape into
`unknown_relation`.  That is the intended trade: missing one costs a wasted
search branch, while falsely rejecting a productive change of representation
costs the branch that would have worked.

## ResidualBench

`residualbench/ResidualBench.lean` holds eight labelled sketches over two
elementary targets — the sum of the first `n` odd numbers, and a divisor-count
identity — including deliberate restatement, self-assumption, false-residual
and hallucinated-literature specimens, plus two controls that must **not** be
vetoed.  Labels live in `scripts/residualbench_manifest.json` and are compared
against the run; the evaluator refuses a manifest that tries to author a
verdict rather than declare an expectation.

Under budget `ladder_v3_independent`:

| Sketch | Verdict | |
|---|---|---|
| `A_notation` | `endpoint_equivalent` | veto — notation change only |
| `B_reassociation` | `unknown_relation` | equivalent in fact; budget did not reach it |
| `C_induction` | `strict_decomposition_candidate` | genuine base-plus-step split, correctly not vetoed |
| `D_self_assumption` | `unknown_relation` | residual is a tautology; see below |
| `E_hallucinated` | `residual_refuted` | residual is false |
| `F_strengthening` | `unknown_relation` | **control** — a productive strengthening, not vetoed |
| `G_hyperbola` | `endpoint_equivalent` | veto — representation change only |
| `H_incomparable` | `unknown_relation` | **control** — unrelated true residual, not vetoed |

Three vetoes, both controls clean, and the legitimate decomposition survives.
`docs/residualbench_report.json` is the run: every proposition put to Lean, the
tactic that discharged it, and its axiom budget.  It records this repository's
pinned Mathlib environment only; no cross-pin receipt is registered here, so
this note makes no portability claim about the older Formal Conjectures pins or
other library versions.

Two rows disagree with their labels on budget grounds and are left that way.
`B_reassociation` is an equivalent range reindexing and `F_strengthening`
specialises a general arithmetic-progression formula; the current general
tactic ladder does not close either.  Adding tactics shaped to these fixtures
would turn the benchmark into a transcript of its own tactic list.

`D_self_assumption` is an error by the author of the bench, kept on the record.
Its residual is `OddSum → OddSum`, which is a tautology — equivalent to `True`,
not to the target, because it cannot imply the target back.  It was labelled
`endpoint_equivalent`.  The evaluator was right and the label was wrong.  A
residual provable with no assumptions establishes nothing and deserves its own
verdict; it does not yet have one.

## Running it

Requires a built Mathlib for this toolchain.

```
python3 scripts/lean_fast_build.py ResidualBench
python3 scripts/residual_evaluator.py \
  --manifest scripts/residualbench_manifest.json \
  --lean-root . \
  --no-cross
```

The run emits, per sketch, the propositions it put to Lean, which tactic
discharged each, and the axiom budget of every accepted proof.  A tactic
attempt counts as proved only when `#print axioms` returns a report free of
`sorryAx`; a failed theorem still enters the environment closed by `sorryAx`,
so the presence of a report is not sufficient.  Each run carries two controls —
one trivially provable proposition and one unprovable one — and refuses to
report any verdict if the harness cannot separate them.

## What this does not establish

The evaluator is sound where it speaks and silent elsewhere.  It is not a
proof-difficulty metric: logical strength and proof cost are different
quantities, and a stronger residual may be easier because it has more exploitable
structure.  It is not complete: `unknown_relation` means the budget proved
nothing, never that no relation exists.  It has not been run against a live
proof-search loop, so no claim is made here about search efficiency or solve
rate.  And no priority is claimed for the construction; the relation between
this and existing proof-progress prediction and reward-model work has not been
surveyed.

What it does establish is narrower and checkable: for the specimens listed
above, at the stated budget, in the stated environment, the relation between a
sketch's remaining obligations and its target was decided by the kernel rather
than estimated.

[nexus]: https://arxiv.org/abs/2605.22763
