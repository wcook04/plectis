<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis paper

`plectis-public-system.tex` is the source for the short public-system paper.
It describes the 88 public components, defines the minimum technical terms,
shows one component from input to result, and separates public execution
evidence from the reported history of the private AI-built system.

Check live registry counts, the worked-example anchors, required cold-reader
definitions, and prohibited overclaims before building:

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
