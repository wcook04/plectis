# Contributing

Contributions and error reports are welcome. You do not need to understand the
whole toolkit to improve one example, challenge a check or explain a component
more clearly. Useful contributions include:

- fixing a command, adding a test case or making an example easier to run;
- improving an explanation or a route through the documentation;
- showing where a passing check fails to support the claim made for it;
- adding a working mechanism with its source history, runnable example,
  tests and an explicit account of what the result establishes.

If you are still choosing where to start, [Understanding Plectis](docs/UNDERSTANDING_PLECTIS.md)
follows one component through its inputs, code and checks. The README's
[Choose a route](README.md#choose-a-route) table helps you find another area.
Pick one concrete discrepancy or improvement and keep the change focused on it.

## Reporting a discrepancy

If a run does not match its stored receipt, a validator's pass rule does not
seem to bear on the component's stated claim, or a generated document
disagrees with the records it is built from, that is a finding worth
reporting, not noise. Open a GitHub issue at
<https://github.com/wcook04/plectis/issues> with:

- the commit you ran (`git rev-parse HEAD`);
- the exact command and the operating system and Python version;
- what you expected, with the receipt path where one applies;
- what you observed, with the failing output pasted or attached.

Keep the original failing output rather than substituting a component or
input that happens to pass. Reports that dispute a pass rule or an expected
value are as welcome as reports of failing runs: the success criteria are
part of what is published for challenge, and so is the unit of counting:
report it if two components look like one mechanism, or if a boundary
excludes the difficult part of a task.

## Development setup

Clone the repository, check that its prepared examples work, then install the
development tools. These commands use a macOS or Linux shell (or WSL):

```bash
git clone https://github.com/wcook04/plectis && cd plectis
./bootstrap.sh
VENV=/tmp/plectis-dev-venv make install
```

`./bootstrap.sh` runs the clone's prepared example and boundary checks, and
writes ignored `.microcosm/cold_clone_probe.json` evidence. Use
`./bootstrap.sh --dry-run` to preview the command first.

`make install` creates a checkout-keyed temporary venv and installs the
`[test]` extra there (pytest, requests, NumPy, pandas), so a clean clone does
not need pytest preinstalled. Set `VENV` explicitly (as above) when you want a
stable interpreter path such as `/tmp/plectis-dev-venv/bin/plectis hello .`.

## Tests and validation

```bash
make check      # registry and proof-trust preflight
make test       # public entry and safety tests
make ci         # the GitHub Actions floor: test + smoke + package-smoke
make validate   # ci plus the doctrine-lattice drift check (maintainer gate)
```

Run the focused tests for the surface you touched first, for example:

```bash
PYTHONPATH=src /tmp/plectis-dev-venv/bin/python -m pytest tests/test_public_entry_docs.py --basetemp=/tmp/plectis-bt
```

Two rules the Makefile enforces that direct pytest runs must respect:

- **One basetemp per process.** If you run separate pytest subsets at the same
  time, pass a unique `--basetemp` to each; parallel direct invocations can
  race while copying fixture trees if they share one.
- **Tracked receipts are read-only under pytest.** Generated output that needs
  to change belongs in its owner lane (a builder or an explicit
  `MICROCOSM_TRACKED_RECEIPT_WRITES=1` opt-in), never a hand edit.

The full review lanes (complete smoke card set, the `make test-all` drift
suite, flight recorder, release-candidate proof, standalone export and its
exported-clone validation) are documented in
[docs/maintainers/validation.md](docs/maintainers/validation.md).

## Generated files

`ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md`, `FIRST_ACTION.md`,
`RELEASE_REVIEW.md`, and the atlas/registry JSON records are builder-owned.
Do not hand-edit them; change the source and regenerate (for the atlas:
`PYTHONPATH=src python3 scripts/build_organ_atlas.py --write`). Tests compare
committed output to live regeneration and fail on drift.

## Documentation changes

The [documentation hub](docs/README.md) separates explanations, runnable
guides and reference. Give a new page a clear reader and purpose, link it from
the relevant guide, and include a next step. Define unfamiliar project terms
where a reader first needs them; [the short terminology guide](docs/UNDERSTANDING_PLECTIS.md#the-terms-used-in-the-repository)
is there for reference.

Run the commands you add as a reader would, from a clone without an activated
development environment. Check relative links and section anchors. Keep the
author's meaning and qualifications when editing prose, and check any changed
claim against the code and evidence it describes. The existing first-contact
tests are a useful starting point:

```bash
PYTHONPATH=src /tmp/plectis-dev-venv/bin/python -m pytest tests/test_documented_first_contact_commands.py tests/test_public_entry_docs.py
```

## Pull requests

Use `.github/PULL_REQUEST_TEMPLATE.md` as the inline checklist for validation
evidence, public/private payload exclusions, claim boundaries, and standalone
source inventory. The template is a guardrail, not a release approval surface.
State which tests you ran; `make ci` or an explained narrower lane is the
floor.

## Hard boundaries

Do not contribute secrets, credentials, sessions, provider payload bodies, raw
operator voice, private personal material, live account data, live external
target details, hidden rubric bodies, or unsafe exploit steps.

Do not add source-mutation, provider-call, hosted-release, recipient-send,
financial-advice, product-readiness, proof-correctness, or production-security
authority unless the surface is explicitly a negative fixture proving that the
authority is rejected. Nothing in a contribution changes the release
boundary: export receipts keep `release_authorized=false` until a separate
operator decision exists.
