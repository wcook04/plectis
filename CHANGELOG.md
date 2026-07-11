# Changelog

All notable changes to Plectis are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
