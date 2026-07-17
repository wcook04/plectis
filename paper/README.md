<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis paper

`plectis-public-system.tex` is the source for the short public-system paper.
It explains Plectis from first principles through one real local run, then
introduces the component corpus, evidence model, and authority boundary.

Build it without changing the repository's generated surfaces:

```sh
tectonic --outdir /tmp/plectis-paper paper/plectis-public-system.tex
cp /tmp/plectis-paper/plectis-public-system.pdf plectis-public-system.pdf
```

The tracked root PDF is the reader-facing copy. The paper has a ten-page
ceiling. `README.md` and `ARCHITECTURE.md` remain the live operational entry
surfaces; the PDF is the stable first-principles explanation.
