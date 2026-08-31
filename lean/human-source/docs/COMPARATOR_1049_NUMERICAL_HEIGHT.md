# Erdős #1049: one numerical certificate, exactly scoped

## The question

For which rational bases is the relevant Lambert-type series irrational? The
base `3/2` is the main unresolved target in this programme.

## What is checked here

Lean proves the concrete inequality

```text
log(2) / log(7) < 1/2 - 1/pi^2.
```

Comparator then checks a tiny proof transport from the public source theorem
to a separately declared Mathlib-only statement. A deliberately weakened
nearby statement must be rejected.

This is useful because the inequality is the numerical input used at the base
`7/2` in an external theorem of Bundschuh and Väänänen. It cleanly separates a
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
Comparator checks the transport to the separately declared statement. The
Bundschuh-Väänänen theorem remains a cited external result.

## Proof handle

- [Public Lean source](../ErdosProblems/Erdos1049/RationalBaseLambert.lean): theorem `sevenHalves_bundschuhVaananen_margin`
- [Independent challenge statement](../ExternalVerification1049/Challenge.lean): theorem `comparator_sevenHalves_numericalHeight`
- [Source transport](../ExternalVerification1049/Solution.lean)
- [Deliberate mismatch](../ExternalVerification1049/NegativeSolution.lean)
- [Machine-readable scope](../verification/comparator-1049-numerical-height.metadata.json)

The correct badge is: **Comparator-checked numerical certificate**. It is not
an independently verified irrationality theorem.
