<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# A reader's way in

This repository follows eight unsolved problems of Paul Erdős. For each one it
holds a short paper, a longer research record, Lean proofs of selected
statements, finite computations, and a written account of the approaches that
stopped and why. You do not need Lean or any knowledge of the folder layout to
read the papers.

All eight problems remain open. The work proves intermediate theorems, writes
out proofs of results that were stated but not printed in the literature,
checks exact finite cases, and records obstructions to tempting shortcuts.
None of it becomes a solution because a proof assistant accepted it or because
a computation reached a large number.

## What is here

The [front page](../README.md) lists the eight problems with a short paper and
a longer paper for each. The short paper is the first read. The longer record
keeps failed routes, finite experiments, and the exact obligations that
survive. The [paper catalogue](../paper/README.md) groups the manuscripts and
their sources by problem, with three further papers on how the project is run.

The [results guide](RESULTS.md) states the strongest checked result for each
problem next to what still blocks its endpoint. [Prior work](PRIOR_ART.md)
records earlier arguments and attribution. [Scope](SCOPE.md) lists the claims
the project does not make. The [architecture guide](ARCHITECTURE.md) explains
the checks and generated indexes; it is not needed for the mathematics.

## What formalisation adds

Lean checks a precise statement against a precise proof. That forces
assumptions, quantifiers, and dependencies into the open. It does not decide
whether a theorem is new, important, or the right way to attack an open
problem, and it does not turn a conditional result into an unconditional one.
Many results here are ordinary mathematical arguments with no Lean proof; each
paper says which is which.

## The eight problems in brief

Problem 68 asks whether the sum of the reciprocals of n!−1 is irrational. The
paper proves a lower bound on the growth of the least common multiple of those
denominators, so clearing each summand separately cannot produce a small
positive tail. It also shows by example that cancellation after addition does
happen, and gives an exact congruence criterion for irrationality. The
congruence failures that criterion needs remain unproved.

Problem 243 concerns reciprocal sums of integers growing roughly like squares.
The paper shows that if the sum is rational and the upward steps of a certain
integer numerator are bounded, the sequence must eventually follow the
Sylvester recurrence. The numerator itself is not assumed bounded. A separate
theorem proves irrationality under a specific rate of growth. The original
problem is not settled.

Problem 249 asks about the binary series of Euler's totient. The paper proves
that reducing the totient modulo any m at least 3 gives an irrational series,
and classifies the rational cases for powers of two. It also determines the
exact rank of the dyadic totient kernel and proves several conditional routes
to the original series. The missing input for each route is stated. The
original, unreduced series is not settled.

Problem 251 is the dyadic series of the primes. The paper builds a sparse
change to the prime gaps that makes the sum rational while keeping the prime
growth scale, every fixed eventual congruence, and the same short block
statistics in the limit. This rules out a class of weaker hypotheses and says
nothing against the conditional results already on the problem page.

Problem 257 is the clearest place to start. For every infinite set of
exponents whose reciprocals have a finite sum, the paper writes out an
averaging proof that the Mersenne series is irrational at every integer base.
Erdős stated that result without printing the proof. Lean separately checks
the classical full-support case, the pairwise-coprime case, and a measure
theorem for the achievement set. The universal question, over every infinite
support, and the two proposed values discussed in the paper remain open.

Problem 269 is the running least common multiple of three primes. Building on
Steve Fan's two-prime work on the problem page, the paper shows that one
binary carry makes a chosen minor of the kernel matrix nonzero at every order,
so no finite sum of separated kernel terms can represent it. This is a Lean
theorem. Three-prime irrationality is not proved.

Problem 1041 asks whether two roots of a polynomial can always be joined by a
short path inside the set where the polynomial is small. The paper gives an
explicit family, monic trinomials with roots in the open unit disc, where a
straight segment from each root to the origin works, so any two roots join
with length below 2. It also proves a sharp estimate on critical values. The
general path problem is open.

Problem 1049 is the Lambert-type series at a rational base. Specialising a
construction of Zudilin, the paper gives an explicit cutoff on the ratio of
logarithms below which the series is irrational, and applies it to the base 31
over 4 and its integer powers. The base 3 over 2 lies outside that region and
remains open.

## How to read the evidence

The project keeps kinds of evidence apart. A Lean proof tells you a formal
statement was checked. A claim record tells you how that statement may be
described in public and what remains open. A paper supplies motivation and an
argument a mathematician can read. A finite calculation covers only the range
it reached.

Comparator gives selected statements a second, independently declared formal
interface under a fixed set of assumptions, and reports whether the two agree.
It exposes mismatches between formal surfaces. It is not peer review and does
not establish novelty. Palomar registration of selected statements is planned
and not done; a ranking file in the checkout is a working aid and confers no
acceptance.

This repository is a self-contained public record. It is not an entrypoint
into any private development system. The number of files, declarations, or
computed cases does not measure the importance of a result.

## Reviewing one result

Pick one statement in a short paper. Read its assumptions and the step that
does the work, then open the longer record if you want the attempts that led
there. If a hard step is compressed, a routine step gets too much space, or
you cannot tell where an idea came from, that is useful feedback. A checked
proof still needs an explanation a mathematician can understand and reuse.

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
