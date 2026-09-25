<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# A reader's way in

This repository studies eight Erdős problem programmes through short papers,
longer research records, Lean proofs of selected statements, finite
computations, and accounts of approaches that stopped. Plectis keeps the work
open to further insight. The website brings the collection together; you do
not need Lean to read it.

Start with the [#257 paper](../paper/257/erdos-257-mersenne-support-subseries.pdf):
its checked finite-prime weighted criterion proves irrationality for some
infinite supports with divergent reciprocal sum, while arbitrary infinite
support remains open. Then read [#1049](../paper/1049/erdos-1049-rational-base-lambert.pdf):
irrationality holds in the stated region, including powers of `31/4`; `3/2`
remains open. The [#1041 paper](../paper/1041/erdos-1041-lemniscate-newton-flow.pdf)
examines ani's counterexample.

Using the degree-seven polynomial constructed by the erdosproblems.com
contributor ani, Lean proves that every preconnected strict-lemniscate set
containing two distinct roots has one-dimensional Hausdorff measure greater
than two. This refutes the exact Formal Conjectures path-image-length
statement; the separate total-variation bound is also checked. The other
seven targets remain open. Independent human review of correspondence with
the 1958 wording has not been recorded. Comparator checks only selected exact
statements, axioms and kernel acceptance; it does not assess novelty or
historical correspondence.

## Two ways to begin

You can follow one question or read across the corpus: a failed method in one
programme can suggest a different theorem in another. The
[reading edition](reading-edition/README.md) gives a short research instruction
and the opening of each short paper in one file. For #257, follow the weighted
theorem, its averaging proof, the long record and Lean source. Then try the
[changed-base exercise](../research/experiments/weighted_support_transfer/README.md):
the failed sufficient test proves no rationality claim, and the universal
question remains open.

## What is here

The [front page](../README.md) lists the eight problems with a short paper and
a longer paper for each. The short paper is the main exposition: it introduces
the question, states the strongest results and explains the ideas behind the
arguments for a mathematical reader. The longer record keeps technical detail,
failed routes, finite experiments, and the exact obligations that
survive. The other seven target problems are not resolved here; those papers
make their surviving questions explicit. The [paper catalogue](../paper/README.md)
includes *Problem-Sized Lean Worlds* on proof and claim boundaries and
*From Spare Compute to Cumulative Mathematics* on contribution and credit.

The [results guide](RESULTS.md) states the strongest checked result for each
problem next to what still blocks its endpoint. [Prior work](PRIOR_ART.md)
records earlier arguments and attribution. [Scope](SCOPE.md) states the project's
limits; the [architecture guide](ARCHITECTURE.md) explains its machinery.

## What formalisation adds

Lean checks a precise statement against a precise proof, exposing assumptions,
quantifiers and dependencies. It does not establish novelty or importance,
or turn a conditional result into an unconditional one.
Each paper distinguishes ordinary mathematical arguments, formalised results
and remaining gaps. Follow a statement's source link and verification record
to see what has been checked; a build alone does not establish that every
argument in a paper has been formalised.
Independent human review of correspondence with the historical curve-length
formulation has not been recorded.

## The eight problems in brief

Choose a question below to open its short paper. The
[problem-by-problem results guide](RESULTS.md#problem-by-problem-guide) explains
the main arguments, their formalisation and the questions left open. Keeping
those assessments in one place avoids conflicting summaries.

<!-- BEGIN problem_programme_card -->
[Problem 68](../paper/68/erdos-68-factorial-denominator-irrationality.pdf). Is the series sum_{n >= 2} 1/(n! - 1) irrational? [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-68).

[Problem 243](../paper/243/erdos-243-reciprocal-tail-rigidity.pdf). Under a rapid-growth hypothesis on an integer sequence, does rationality of its reciprocal sum force the sequence to satisfy the Sylvester recurrence eventually? [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-243).

[Problem 249](../paper/249/erdos-249-binary-totient-series.pdf). Is the binary Lambert series sum phi(n)/2^n irrational? [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-249).

[Problem 251](../paper/251/erdos-251-prime-gap-dyadic-series.pdf). Is the dyadic series of consecutive primes irrational? Equivalently, is the corresponding consecutive-prime-gap dyadic series irrational? [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-251).

[Problem 257](../paper/257/erdos-257-mersenne-support-subseries.pdf). Is the sum of 1/(2^n-1) over every infinite set of positive exponents irrational? [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-257).

[Problem 269](../paper/269/erdos-269-three-prime-running-lcm.pdf). For a finite set of at least two primes, is the sum of reciprocals of the running least common multiples of the smooth numbers irrational? This library treats the three-prime case. [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-269).

[Problem 1041](../paper/1041/erdos-1041-lemniscate-newton-flow.pdf). Must two roots of a monic polynomial in the open unit disc be joined by a sub-two-length curve inside its unit lemniscate? Ani’s degree-seven example refutes the exact Formal Conjectures statement; correspondence with the 1958 wording awaits human review. [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-1041).

[Problem 1049](../paper/1049/erdos-1049-rational-base-lambert.pdf). For which rational bases is the corresponding series irrational? The first resistant explicit base is three halves. [Work on this paper](CONTRIBUTE_BY_PAPER.md#problem-1049).
<!-- END problem_programme_card -->

The [cross-problem paper, Reading Eight Erdős Problems Together](../paper/synthesis/optimal-sparse-perturbations.pdf)
joins the capacity criterion, Lambert subsums across bases, method
limits, exact computations and unsuccessful approaches in one account. This
is a central use of the collection: read the papers and Lean corpus together,
find constructions or obstructions that survive in a more general setting,
and develop the mathematics they suggest. The
[synthesis guide](../paper/synthesis/README.md) gives ways to begin.

## How to read the evidence

A Lean proof checks a formal statement; a claim record gives its public status
and limits. A paper supplies motivation and a readable argument. A finite
calculation covers only the range it reached.

Comparator compares selected statements with independently declared formal
interfaces under fixed assumptions. It is not peer review and does not
establish novelty. The [Palomar guide](verification/PALOMAR_QUALIFICATION.md)
distinguishes local packaging from recorded service submission or acceptance.

This is a self-contained public record, not an entrypoint into any private
development system. File, declaration and computation counts do not measure
mathematical importance.

## Reviewing one result

Pick a statement in a short paper, read its assumptions and the step that does
the work, then follow the longer record. Missing motivation, compressed hard
steps and unclear attribution are useful feedback: a checked proof still needs
an explanation others can understand and reuse.

## Contributing

AI tools did much of the research, code, and drafting under my direction. I am
responsible for the claims, the sources, and the release. Nothing here has had
independent mathematical review.

The most useful contribution is a mathematical one: a proof correction, a
clearer explanation of a hard step, an attribution correction, a counterexample
to an intermediate claim, or an earlier reference. The
[contributor guide](../CONTRIBUTING.md) explains how to send that back with its
evidence and credit intact. If this work helps you solve one of the eight, the
solution and the credit are yours.

An insight is welcome before it has a formal proof. Will can work with you to
develop the argument and formalise it, with the originating insight credited
separately from subsequent exposition and proof work. Clearer understanding,
reusable methods and new questions across the corpus also count as
contributions; they need not close an original problem.
