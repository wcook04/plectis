<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis paper

Read [the current PDF](../plectis-public-system.pdf) for the argument.
[plectis-public-system.tex](plectis-public-system.tex) is its source.

In the paper, I examine what a stranger can reasonably conclude from running
the published parts of a private system. I trace one component from input to
result and distinguish the observed result from the broader claims a reader
might make about it. The subject is one author-selected software collection.

The argument concerns the relationship between claims, evidence and limits;
the choices I made as the author; and ways an independent evaluator could
test those choices. The figures and worked example explain the component's
required fields, the published material, and the additional evidence needed
for broader claims. The final section gives a review procedure. The appendix
records commands, environment details and counts for the version examined.

The paper does not statistically evaluate the private system or establish
that it is reliable. Its discussion of assurance cases and
Claims–Arguments–Evidence notation does not claim conformance to either.

<a id="check-and-build"></a>
## Compare the manuscript with its recorded evidence

Use Python 3.11 or newer and Git from the clone root, in a macOS/Linux shell or
WSL. The [quickstart](../QUICKSTART.md#1-first-result) gives the clone command.
This command needs no Python package installation:

```sh
python3 scripts/check_public_system_paper.py
```

The script compares manuscript counts and references with files at the Git
commit named in the manuscript. It also compares the saved
[test-run record](public-test-receipt.json), required explanations, bibliography
identifiers and prohibited claims with prescribed values. It prints
`Public-system paper check: pass` followed by the comparison details on success
and exits with status `0`; disagreements produce error messages and status `1`.

These are comparisons of recorded material. The script does not rerun the
recorded tests or Lean proofs, or look up publications to verify their
bibliography entries. For commands that run the current software, use the
[validation guide](../docs/maintainers/validation.md).

A full Git clone provides the historical files used for these comparisons.
If the script reports that the named commit is missing from a shallow clone,
run `git fetch --unshallow` and retry. A ZIP download has no Git history: the
script can compare its local files, but cannot reproduce the comparison with
the historical commit.

## Build a preview PDF

Install [Tectonic](https://tectonic-typesetting.github.io/book/latest/getting-started/install.html)
and confirm that `tectonic --help` runs. Tectonic downloads TeX support files
when they are missing from its cache, so a first build may need network access.
From the clone root, run:

```sh
mkdir -p /tmp/plectis-paper
tectonic --outdir /tmp/plectis-paper paper/plectis-public-system.tex
```

Open `/tmp/plectis-paper/plectis-public-system.pdf` to read the result. This
command writes the preview outside the checkout and leaves the published PDF
unchanged. Rerunning it replaces the previous preview at that path.

## Replace the published PDF

After reviewing the preview, copy it over the tracked PDF if you are preparing
an updated paper for the repository:

```sh
cp /tmp/plectis-paper/plectis-public-system.pdf plectis-public-system.pdf
```

This replaces the PDF linked from the root README. Review that file along with
any manuscript edits before committing them.

The editorial page limit is twenty-two pages. This updates the previous
twenty-one-page limit to retain the already published manuscript, appendix,
authorship disclosure and bibliography at their current type size. Record a
reason here before raising the limit again.

Return to the [README](../README.md) to choose an example, or read
[the code guide](../ARCHITECTURE.md) to find its implementation. The PDF explains
the evidence and conclusions for the recorded version; those guides describe
how to use the current checkout.
