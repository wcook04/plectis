# Changelog

All notable changes to Plectis are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2026-07-26

### Fixed

- The advertised `plectis agent-closeout-faithfulness-audit run` command now
  passes its semantic negative-case evaluator through the command-line
  entrypoint. The v0.3.1 command stopped before exercising its planted
  forgeries even though the library entrypoint wired the evaluator correctly.
  The exact terminal command now exits successfully only after all four
  negative cases are detected by name.
- The dedicated closeout-faithfulness tests now run inside the normal public
  CI floor. Their source-manifest assertions also enforce the public-safe
  substitution omission used by the standalone release, rather than expecting
  the omitted private-near-verbatim body to be present.

## [0.3.1] - 2026-07-20

### Fixed

- A `git clone --depth 1` reported five failures naming worked-example,
  Lean-file-count and receipt-flow "drift". None of them mentioned the clone.
  The paper pins its evidence to a specific commit and the checks read the
  repository as it stood there, so a truncated clone was compared against
  absent data rather than against anything that had changed — inviting a
  reader to doubt the paper's numbers. Absence is now reported as absence:
  the checker names the shallow clone and the fetch that resolves it, and the
  checks that need the pinned commit skip with that reason. A full clone is
  unaffected and nothing skips there.

### Removed

- `.github/workflows/pages.yml`. GitHub Pages serves this site from the
  `gh-pages` branch builder; that workflow deployed the same tree again as an
  artifact to the same environment, so which one won depended on which ran
  last. It had already taken the published site down once, when an earlier
  version copied a hardcoded list of files and left all three papers and
  `.well-known/security.txt` returning 404. It was disabled rather than
  deleted, leaving the second owner one toggle away. A test now asserts no
  workflow deploys Pages while the branch builder owns publication.

## [0.3.0] - 2026-07-20

### Changed

- The public-system paper completed a ninth method-and-scope pass. It now
  identifies the object studied, the component-level unit of analysis, and
  its component trace and collection-wide classification; cites established
  software-engineering case-study reporting guidance; and limits its five
  proposed evidence routes to the dependencies actually analysed rather than
  treating them as a universal ranking.
- The public-system paper completed an eighth scholarly-positioning pass.
  It now places its claim--evidence--limit contract beside assurance cases
  and Claims--Arguments--Evidence notation, cites OMG SACM 2.3, disclaims
  both conformance and any private-system safety claim, distinguishes a
  validator's rule from a full assurance argument, and closes with an
  explicit conclusion and shorter reader test.
- The public-system paper completed a seventh, reader-first clarity pass. Its
  abstract and first section now state the contribution as a concrete
  claim--evidence--limit contract and worked audit; ACM's artifact-review
  policy supplies the nearest computing-specific comparison; dense authorship
  and independence passages are shorter; project-internal appendix terms are
  replaced with literal descriptions; and the paper README now describes the
  five stronger-evidence routes as independent rather than staged.
- The public-system paper completed a sixth release-readiness pass. Five
  primary sources now ground its borrowed claims about reproducibility,
  test oracles, selective publication, independent evaluation, and SHA-256;
  the stronger-evidence figure now presents independent routes rather than
  a false cumulative ladder; and claims about correctness, fingerprints,
  private-root access, authorship, selection, usefulness, and record repair
  are more precisely bounded. A clean Python 3.12.7 reproduction adds a
  second-interpreter check and records both the offline build prerequisite
  and a stale field in the pinned worked-example result. The paper guard now
  reads counts, routes, receipts, and displayed example values from the
  pinned Git snapshot, while separately enforcing current citations and
  argument anchors.
- The public-system paper revised against a referee-grade review and a
  live congruence audit: the hand-equivalence claim about AI authorship is
  now bounded (inference ceilings are authorship-independent; error rates
  are not measured), the borrowed vocabulary is acknowledged against its
  home fields (the oracle problem, publication bias, reproducibility), the
  five distinctions are stated as an open list with the refusal-timing and
  version-drift gaps named as further instances, the reader checklist
  gains commit pinning, group-name discounting, and refusal-history
  checks, and the registry-entry sentence names the fields a reader will
  actually find. Every empirical claim the paper makes about the
  repository was re-verified against the live tree; the worked example
  reruns to the stored values exactly.
- The public-system paper deepened along three lines and given figures. A
  fifth distinction (a validator's rule versus the stated claim) joins the
  original four; a new section, "The author's hand", itemises the
  consequential choices the author still controls and the
  honest-but-misleading presentation they could produce (correlated
  components are not independent witnesses; agreement among one
  maintainer's records is one witness recorded several times; group names
  borrow gravity the fixtures do not earn); and "What stronger evidence
  would look like" gained a record-aging rule (repairs add dated facts and
  do not subtract failures) plus a table of where a test's expected value
  can come from and what agreement then supports. Four figures now carry
  the structure: the component contract with what a stranger can do to
  each part, the publication boundary with its invisible denominator, the
  five inference gaps a matching run does not cross, and stronger evidence
  as a transfer of control. The subtitle no longer says "AI-built" (the
  origin account stays in the body as labelled testimony), the paper's page
  ceiling rose from ten to fourteen, and the claim guard gained anchors for
  the new distinction, caution, and aging sentences.
- The public-system paper (`paper/plectis-public-system.tex`, tracked PDF at
  the repository root) rewritten around one governing question: what a
  stranger may reasonably conclude from curated runnable fragments of a
  private system. The worked example now prints its input arrays so the
  first expected value can be recomputed by hand; four named distinctions
  (public execution vs private provenance, repeatability vs correctness,
  selected cases vs general behaviour, risk reduction vs guarantee) replace
  scattered caveats; the dated operational record moved to an appendix. The
  paper claim-guard (`scripts/check_public_system_paper.py`) gained anchors
  for the distinction sentences and further prohibited overclaims.
- `CONTRIBUTING.md` gained a "Reporting a discrepancy" procedure: what to
  include, where to file, keep the failing output, disputes of pass rules
  welcome.

### Fixed

- `scripts/public_repo_profile.py` root allowlist now classifies `paper/`
  and `plectis-public-system.pdf`, which had left the public repo profile
  check (and with it `make test`) failing since the paper first landed.

## [0.2.0] - 2026-07-11

Public-surface normalisation. No component or runtime behaviour changed; this
release reshapes how a first-time reader meets the project.

### Added

- `CITATION.cff` so the repository is citable ("Cite this repository" on
  GitHub).
- This changelog.
- GitHub issue forms (bug report, documentation problem, question or proposal)
  and a security-route redirect in `.github/ISSUE_TEMPLATE/`.
- A `plectis` import and module façade (`src/plectis/`): `python3 -m plectis`
  runs the same CLI as the installed `plectis` command. The implementation
  package remains `microcosm_core` as a compatibility surface.
- `scripts/public_repo_profile.py`: a versioned public-repository profile
  check with two modes (`python_research_tool`,
  `formalised_mathematics_artifact`), run as part of the public test floor.
- `docs/` tree for maintainer runbooks and deeper documentation, starting with
  the validation and security runbooks and the CLI decomposition plan.

### Changed

- `README.md` rewritten stranger-first: identity sentence, install and first
  command on the first screen, capabilities before taxonomy, one consolidated
  scope section, and related projects moved to the end. All boundary language
  (family ceilings, evidence classes, authority ceilings, claim grammar)
  remains, enforced by the front-door validator as whole-document pins.
- `QUICKSTART.md` reduced to the shortest trustworthy install-and-run path;
  the deep review lanes moved to `CONTRIBUTING.md` and `docs/maintainers/`.
- `CONTRIBUTING.md` and `SECURITY.md` rewritten as concise community
  contracts; their maintainer runbook detail moved under `docs/maintainers/`.
- `pyproject.toml` project description and keywords rewritten in plain
  language; version bumped to 0.2.0.

## [0.1.0] - 2026-06-25

Initial public release of the standalone Plectis repository: the public
executable component corpus (88 components across seven areas), the local
CLI, fixtures, receipts, validators, generated component records, and the
public verification floor (`make ci`).
