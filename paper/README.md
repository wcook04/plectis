<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis paper

`plectis-public-system.tex` is the source for the short public-system paper.
It explains Plectis from first principles as what it is: the public slice of
a private AI-built system, published as source code and runnable fixtures.
It covers what is in the slice, one real run, how the slice was cut from the
private repository, and what a passing check does and does not show.

Build it without changing the repository's generated surfaces:

```sh
tectonic --outdir /tmp/plectis-paper paper/plectis-public-system.tex
cp /tmp/plectis-paper/plectis-public-system.pdf plectis-public-system.pdf
```

The tracked root PDF is the reader-facing copy. The paper has a ten-page
ceiling. `README.md` and `ARCHITECTURE.md` remain the live operational entry
surfaces; the PDF is the stable first-principles explanation.
