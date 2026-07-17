# Changelog

All notable changes to Plectis are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

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
