<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis paper

Read [the current PDF](../plectis-public-system.pdf) for the argument.
[plectis-public-system.tex](plectis-public-system.tex) is its source.

The paper asks what a stranger can reasonably conclude from runnable public
fragments of a private system. It follows one component from input to result,
then examines what that result can establish. It is a descriptive analysis
of one public artefact, with the component as its unit of analysis.

The argument covers the relationship between claims, evidence and limits;
the choices that remain with the author; and ways to submit those choices
to independent scrutiny. Four figures explain the component contract,
the publication boundary, the gaps between a matching run and a broader
claim, and the routes to stronger evidence. The body ends with a short
review procedure. Commands, environment details and counts live in an appendix.

The paper does not statistically evaluate the private system or establish
that it is reliable. Its discussion of assurance cases and
Claims–Arguments–Evidence notation does not claim conformance to either.

## Check and build

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

The tracked root PDF is the reader-facing copy. The paper has a twenty-one-page
ceiling. It rose from ten as the figures and author's-hand section landed,
from fourteen after the referee pass, from fifteen when the shared house
typography changed the measure, and from nineteen when the falsifiable
hypothesis handoff made the prior, alternatives, discriminators, and
expert-return path inspectable. The twenty-first page accommodates the merged
public evidence corpus and hypothesis-handoff discussion without shrinking the
type or suppressing limitations. Raise it again only with a reason recorded
here.
`README.md` and `ARCHITECTURE.md` remain the live operational entry
surfaces; the PDF is the stable evidence-and-scope explanation.
