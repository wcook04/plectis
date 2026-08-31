<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# How this repository works

This is a public Lean project about eight unsolved problems in mathematics. It
contains formal source code, papers and summaries for readers, and a set of
checks that keep those different descriptions aligned. The reviewed claim
registry covers #249 and #257; a problem-owned expansion library covers #68,
#243, #251, #269, #1041, and #1049 without silently promoting their
declarations into that reviewed record.

All eight mathematical problems remain open. The repository proves
intermediate results, exact reformulations, and bounded examples around them.
It does not claim a solution to any of them.

You do not need to know Lean, the project history, or any internal naming
scheme to use this guide.

## What this repository is

The repository has two jobs.

1. It stores mathematical statements and proofs in Lean. Lean is a proof
   assistant: a program that checks whether a formal proof establishes the
   precise formal statement written above it.
2. It publishes human-readable descriptions of that work. Those descriptions
   include the README, papers, scope statements, source maps, and data files
   used by other programs.

These jobs need separate checks. Lean checks the formal mathematics. It does
not read the English sentences in a paper or README. A separate release
program checks that selected public descriptions still agree with the
project's reviewed record of what has and has not been proved.

This is also the boundary of the project. It is a self-contained public
release, not an interface to a private agent system. No public claim depends
on private files or unpublished work.

## The architecture in one page

```text
                          human mathematical review
                                      |
                                      v
Lean source -----------------> reviewed claim record
Erdos249257/*.lean              docs/claims.json
       |                              |
       | lake build                   | describes what public pages may say
       v                              v
formal proof check         README, SCOPE, papers, source maps
                                      |
                                      | builders create indexes and summaries
                                      v
                            generated navigation files

Lean source + claim record + public documents + generated files
                                      |
                                      v
                         scripts/check_release.py
                                      |
                                      v
                             pass or stop release
```

There are three different decisions in this picture:

- Lean decides whether a formal proof has the formal statement claimed for it.
- A mathematician decides whether the public wording accurately describes that
  formal statement and whether the wording is important enough to protect.
- The release program decides whether the files still satisfy the relationships
  that were explicitly recorded.

The last decision cannot replace the first two.

## Which file is authoritative for what

Different questions have different source files. There is deliberately no
single file that is authoritative for everything.

| Question | Authoritative source | What it controls |
|---|---|---|
| What has been formally checked? | [`Erdos249257.lean`](Erdos249257.lean), [`ErdosProblems.lean`](ErdosProblems.lean), and the Lean modules they import | Formal statements and proofs; kernel checking alone does not create a reviewed public claim |
| What may the project publicly say about a result? | [`docs/claims.json`](docs/claims.json) | Claim wording, status, supporting Lean names, bounded ranges, and the exact questions that remain open |
| What evidence and review are required when a claim changes? | [`docs/methodology.json`](docs/methodology.json) | Change classes and review requirements |
| What does a reader see? | [`README.md`](README.md), [`SCOPE.md`](SCOPE.md), and authored papers such as [`paper/erdos249-257-main-paper.tex`](paper/erdos249-257-main-paper.tex) | Human explanation; these files must stay within the claim record |
| Which manuscripts are shipped? | [`docs/publication_contract.json`](docs/publication_contract.json) | Paper inventory, file identities, entry routes, and evidence boundaries |
| What evidence supports the historical checker example? | [`docs/publication_evidence.json`](docs/publication_evidence.json) | The recorded exercise and its limitations |
| How are releases blocked? | [`scripts/check_release.py`](scripts/check_release.py) and [`.github/workflows/lean.yml`](.github/workflows/lean.yml) | Local release checks and continuous integration |

The first row refers to those files at the fixed source version named in
[`docs/claims.json`](docs/claims.json).

Some other files are generated views. For example,
[`docs/ORIENTATION.md`](docs/ORIENTATION.md),
[`docs/orientation.json`](docs/orientation.json),
[`docs/declaration_atlas.json`](docs/declaration_atlas.json), and
[`docs/corpus_descriptor.json`](docs/corpus_descriptor.json) reorganise
information from the formal source and the reviewed records for a particular
reader. They are useful indexes, but they do not create new mathematical
authority. Their builder scripts say when they should be regenerated.

## Repository map

```text
Erdos249257.lean                 reviewed #249/#257 root import
Erdos249257/                     reviewed #249/#257 definitions, theorems, and certificates
ErdosProblems.lean               problem-owned expansion root import
ErdosProblems/Erdos<N>/          formal work grouped by actual Erdős problem number
examples/                        a small downstream Lean user of the library

docs/claims.json                 reviewed record of public mathematical claims
docs/methodology.json            rules for changing those claims
docs/publication_contract.json   inventory of shipped papers
docs/publication_evidence.json   evidence and limits for a historical checker exercise
docs/problems.json               generated index of the problem-owned expansion library
docs/problem_index_source.json   the authored source that index is built from
docs/ORIENTATION.md              generated human reading map
docs/SOURCE_MAP.md               routes from mathematical questions to Lean files

README.md                        front page and short result summary
SCOPE.md                         short statement of what remains unproved
paper/                           authored paper sources and rendered PDFs

scripts/                         builders, release checks, queries, and tests
experiments/                     reproducible test changes for the release checker
.github/workflows/lean.yml       the checks run by GitHub on pushes and pull requests
```

The hundreds of Lean files are implementation detail at first contact. Start
from a mathematical question or a claim, then follow the source map or the
read-only query tool to the few relevant modules.

### Two libraries, two levels of claim

The repository holds two Lean roots and they are not interchangeable.

`Erdos249257.lean` is the reviewed corpus. Every public mathematical claim made
about it has a row in `docs/claims.json`, a status, declaration coordinates, and
a place in the gateway paper.

`ErdosProblems.lean` is the problem-owned expansion library, currently covering
Erdős problems 68, 243, 251, 269, 1041, and 1049, plus unpromoted expansion
lanes for the two reviewed problems. Its declarations are checked by the same
kernel, and they are **not** reviewed public claims: the claim registry has no
row for them. Building that root proves that its propositions elaborate; it does
not say that they are the interesting propositions, that they are new, or that
any of those six problems is closer to being solved. Each of the six has a
short paper of its own, an Erdős Problem Note in `paper/`, which states its
checked results and, in the same voice, the obligation that survives them.
`docs/problems.json` is the machine-readable form of the same thing.

The split exists so that adding formal material about a new problem cannot
quietly inflate the repository's claim record. Promotion out of the expansion
library into the reviewed corpus is a separate, human-reviewed change, governed
by `docs/methodology.json`.

## A complete example

One public claim says that Lean has checked successful finite calculations at
every scale up to 82, together with eight small periods and separate shards.

In ordinary language, the record says:

```text
claim id: certified_kill_instances
public statement: Lean checked the listed finite cases.
status: verified finite instance
bounded range: eight small periods, every scale value up to 82, and the shard parameters, all named in the record. Nothing is asserted at 83.
formal evidence: six named Lean declarations.
still open: prove that successful cases exist beyond every fixed cutoff.
```

The range is contiguous rather than a sampled list: the scale quantity changes
only at prime powers and is constant between them, so the earlier deposits
through 64 already covered every value up to 66. Each scale is nevertheless an
independent construction — the two supporting modules share no prime — so the
band buys reach, not leverage.

The phrase *verified finite instance* is not a score or a project-specific
milestone. It means only that Lean checked a stated finite set of inputs. The
open problem requires cases beyond every fixed cutoff, so the finite list does
not settle it. The development also proves an exact equivalence: a supply of
cases beyond every fixed cutoff would settle the open problem itself. An edit
that erased this boundary would therefore be a false mathematical
announcement, not a small wording change.

This one record connects the layers:

1. The named declarations in the Lean files are the formal evidence.
2. [`docs/claims.json`](docs/claims.json) records the public sentence, the
   finite range, the Lean declaration names, and the question still open.
3. The README and mathematical paper explain the result to readers.
4. Generated indexes provide links and source locations.
5. The release program checks that the declaration names still exist, the
   recorded locations remain accurate, the bounded range is present, the
   public limitation has not disappeared, and the generated files are current.

A mathematician is still responsible for judging that the English sentence is
a faithful description of the Lean statement. The software preserves that
reviewed relationship after it has been recorded.

## What happens when a change is made

### A mathematical statement or proof changes

1. Edit the relevant file under `Erdos249257/`.
2. Run `lake build`. This is the proof check.
3. Review whether the formal statement, assumptions, or intended meaning
   changed. [`docs/methodology.json`](docs/methodology.json) states the minimum
   evidence and review required for each kind of change.
4. If the public meaning changed, update [`docs/claims.json`](docs/claims.json).
5. Update the authored README, scope statement, or paper where readers see the
   claim.
6. Run the relevant builders to refresh generated indexes and source
   coordinates.
7. Run `python3 scripts/check_release.py`. Any failed relationship stops the
   release.

The order matters. A generated summary cannot author a stronger claim, and an
English edit cannot change what Lean proved.

### Only explanatory prose changes

The Lean build is normally unchanged, but the public boundary still matters.
Run the release check. If the edit changes the mathematical meaning of a
claim, it also requires mathematical review and a matching claim-record update.

### A generated file is out of date

Do not repair it by hand. Run the builder named in that file or in
[`AGENTS.md`](AGENTS.md), review the change, and rerun the release check.

## How the checks run

GitHub runs two independent jobs on every push and pull request.

- The Lean job installs the pinned Lean and Mathlib environment, checks the
  dependency lock, builds the formal library, and builds a small downstream
  example.
- The release-surface job runs Python checks over claim records, source links,
  generated files, paper identities, licences, query routes, and deliberately
  invalid test inputs.

The main local commands are:

```sh
# Fast check of the newcomer guide itself
python3 scripts/check_architecture_guide.py

# Fast check of the committed first-reading surfaces; no Lean build
python3 scripts/check_cold_clone_comprehension.py --quick

# Full check of public claims, documents, generated files, and release rules
python3 scripts/check_release.py

# Formal proof check
lake build
```

The Python release check confirms the identity of the Lean source but does not
run Lean. The two commands answer different questions and both are required
after a mathematical change.

## What the checks do not prove

A passing build means that Lean accepted the formal statements and proofs in
the imported source. It does not prove that the author chose the intended
formal statement.

A passing release check means that every recorded comparison succeeded. It
does not mean that a program understood every sentence in the repository. It
also does not prove that every important sentence was selected for checking.

Human mathematical review therefore remains part of the architecture. The
software makes reviewed decisions repeatable; it does not make those decisions
on its own.

The printable
[`claim-faithful-publication-systems-paper.pdf`](claim-faithful-publication-systems-paper.pdf)
expands this guide into a paper: it shows the real file map, release flow,
trust boundary, and one claim from Lean source to public page. A short
historical checker example appears only after that architecture and illustrates
the limit of explicitly recorded checks.

## Where to start

- **You want the basic mathematical result and its limits:** read
  [`README.md`](README.md), then [`SCOPE.md`](SCOPE.md).
- **You want the mathematical argument:** read the
  [mathematics paper](erdos249-257-main-paper.pdf).
- **You want to find the Lean behind one claim:** use
  [`docs/SOURCE_MAP.md`](docs/SOURCE_MAP.md), or run
  `python3 scripts/query_corpus.py --claim <claim_id>`.
- **You want to change the repository:** read [`AGENTS.md`](AGENTS.md) and
  [`CONTRIBUTING.md`](CONTRIBUTING.md), then run the checks for the files you
  touched.
- **You want to inspect the historical release-checking exercise:** read
  [`docs/publication_evidence.json`](docs/publication_evidence.json) and the
  reproducibility appendix of the systems paper.

The shortest accurate summary is this: Lean checks the formal proofs, people
review what the project says about them, and the release machinery keeps those
two layers from drifting apart where the relationship has been explicitly
recorded.
