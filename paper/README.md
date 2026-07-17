<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis paper

`plectis-public-system.tex` is the source for the public-system paper. The
paper treats Plectis as a case study in bounded public evidence: what a
stranger may reasonably conclude from a curated set of runnable public
fragments of a private system. It defines the minimum technical terms in
ordinary words, examines one component from input to limit, states the four
distinctions that govern interpretation (public execution vs private
provenance, repeatability vs correctness, selected cases vs general
behaviour, risk reduction vs guarantee), describes the four routes by which
private work became public, and keeps the dated operational record
(commands, environment, counts) in an appendix so the body stays with the
argument.

Check live registry counts, the worked-example anchors, the required
cold-reader definitions and evidential-distinction anchors, and prohibited
overclaims before building:

```sh
python3 scripts/check_public_system_paper.py
```

Build it without changing the repository's generated surfaces:

```sh
tectonic --outdir /tmp/plectis-paper paper/plectis-public-system.tex
cp /tmp/plectis-paper/plectis-public-system.pdf plectis-public-system.pdf
```

The tracked root PDF is the reader-facing copy. The paper has a ten-page
ceiling. `README.md` and `ARCHITECTURE.md` remain the live operational entry
surfaces; the PDF is the stable evidence-and-scope explanation.
