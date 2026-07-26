<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis paper

`plectis-public-system.tex` is the source for the public-system paper. The
paper treats Plectis as a case study in bounded public evidence: what a
stranger may reasonably conclude from a curated set of runnable public
fragments of a private system. It defines the minimum technical terms in
ordinary words, positions its claim--evidence--limit contract against
assurance cases and Claims--Arguments--Evidence notation without claiming
conformance, examines one component from input to limit, states the five
distinctions that govern interpretation (public execution vs private
provenance, repeatability vs correctness, a validator's rule vs the stated
claim, selected cases vs general behaviour, risk reduction vs guarantee),
describes the four routes by which private work became public, itemises the
consequential choices that remain with the author and the honest-but-
misleading presentation they could produce, sets out five independent routes
by which particular choices could leave the author's hands, and keeps the
dated operational record (commands, environment, counts) in an appendix so
the body stays with the argument. The final body section states the conclusion
before giving a short first-review procedure. Four figures carry the structural
points: the component contract and what a stranger can do to each part;
the publication boundary and its invisible denominator; the five inference
gaps a matching run does not cross; and five non-cumulative routes to stronger
evidence, each with its remaining limit.

The paper is a descriptive analysis of one public artefact, not a statistical
evaluation of the private system. It states the object studied, the component
as its unit of analysis, its component-level trace and collection-level
classification, and the limit on generalisation explicitly.

Check live registry counts, the worked-example anchors, the required
cold-reader definitions, the contribution, evidential-distinction and
author's-hand anchors, the publisher-checked bibliography keys, and prohibited
overclaims before building:

```sh
python3 scripts/check_public_system_paper.py
```

Build it without changing the repository's generated surfaces:

```sh
tectonic --outdir /tmp/plectis-paper paper/plectis-public-system.tex
cp /tmp/plectis-paper/plectis-public-system.pdf plectis-public-system.pdf
```

The tracked root PDF is the reader-facing copy. The paper has a
twenty-page ceiling (raised from nineteen when the falsifiable hypothesis-
handoff section made the project's prior, alternatives, discriminators, and
expert-return authority path inspectable; raised from ten when the figures and the author's-
hand section landed, from fourteen when the referee-pass revision
added the related-fields grounding, the bounded authorship claim, and the
operational reader checklist, and from fifteen when the paper adopted the
shared house typography: the same body text now sets to a narrower
classical measure with more generous leading, so the page count rose
without a word being added; raise it again only with a reason recorded
here).
`README.md` and `ARCHITECTURE.md` remain the live operational entry
surfaces; the PDF is the stable evidence-and-scope explanation.
