# Erdős #1049: one numerical certificate, exactly scoped

## The question

For which rational bases is the relevant Lambert-type series irrational? The
base `3/2` is the main unresolved target in this programme.

## What is checked here

Lean proves the concrete inequality

```text
log(2) / log(7) < 1/2 - 1/pi^2.
```

Comparator is configured to check a tiny proof transport from the public
source theorem to a separately declared Mathlib-only statement, with a
deliberately weakened nearby statement as the negative fixture. The checked-in
configuration and workflow are release gates, not terminal replay receipts.

This is useful because the inequality is the numerical input used at the base
`7/2` in the external theorem of [Bundschuh and Väänänen](primary-sources/totient-kernel/bundschuh-vaanenen-1994-source-closure.md). It cleanly separates a
kernel-checked arithmetic certificate from the literature theorem that
consumes it.

## What is not checked here

Lean does not formalise the full Bundschuh-Väänänen theorem, all of its
hypotheses, or its irrationality conclusion. This packet does not advance the
open base `3/2` case.

## Who did what

AI agents helped draft the Lean proof, the statement firewall, and this
exposition. Will Cook directed and reviewed the public release and remains
responsible for its claims. The Lean kernel checks the source proposition.
Comparator is configured to check the transport to the separately declared
statement. A commit-bound terminal replay artifact is required before claiming
that a particular generation passed. The Bundschuh-Väänänen theorem remains a
cited external result.

## Proof handle

- [Public Lean source](../ErdosProblems/Erdos1049/RationalBaseLambert.lean): theorem `sevenHalves_bundschuhVaananen_margin`
- [Separately declared challenge statement](../ExternalVerification1049/Challenge.lean): theorem `comparator_sevenHalves_numericalHeight`
- [Source transport](../ExternalVerification1049/Solution.lean)
- [Deliberate mismatch](../ExternalVerification1049/NegativeSolution.lean)
- [Machine-readable scope](../verification/comparator-1049-numerical-height.metadata.json)

Until a commit-bound terminal replay artifact is attached, the precise badge
is: **Comparator-configured numerical certificate**. It is not an independently
verified irrationality theorem.
