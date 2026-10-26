# Architecture maintenance

Use the [documentation index](../README.md) to read the system and the
[validation runbook](validation.md) to check a change. This guide identifies
what to edit and which consumers must move with it.

## Implementation map

The public package contains portable operation modules and the existing
reference toolkit with its shipped data tree. There is no private service to start or model account to configure.
Individual components can invoke optional external tools; their example
instructions state those requirements.

```text
plectis.repair -> Python host -> isolated worker -> generated Dafny planner/checker
plectis.compatibility -> model adapter -> isolated worker -> generated Dafny checker
plectis.views -> report adapter -> isolated worker -> generated Dafny compiler/interpreter
component replay commands -> shared replay host -> plectis.replay -> generated Dafny admission
plectis.publish -> guarded SQLite transactions

plectis / python -m plectis / plectis.cli:main
  -> microcosm_core.cli (shared entry, argument parsing and command dispatch)
       -> runtime_shell + project_substrate (project inventory and local state)
       -> organs/<component>.py (component-specific commands)
       -> projections/ + validators/ (views and checks)

resource_root -> checkout data or installed share/plectis data
receipts + schemas -> JSON output and input validation
```

| Change | Start here | Keep working |
|---|---|---|
| Portable operations and formal claims | [`formal/README.md`](../../formal/README.md), [`verification study`](../guides/verification-study.md) | Small APIs, exact proof/runtime boundary, negative cases and isolated installation. |
| Command arguments, aliases or exit behavior | [`cli.py`](../../src/microcosm_core/cli.py) | Both public and compatibility command names; see the refactoring contract below. |
| Project inventory, proposed tasks or local state | [`project_substrate.py`](../../src/microcosm_core/project_substrate.py), [`runtime_shell.py`](../../src/microcosm_core/runtime_shell.py) | User source stays separate from ignored `.microcosm/` output. |
| One component's behavior | Its module under [`organs/`](../../src/microcosm_core/organs/), selected through `ORGANS.md` | Example inputs, failure cases and the component's stated limits. |
| A generated map or explanation | [`projections/`](../../src/microcosm_core/projections/) and its registry under `core/` | Regenerate the view; do not patch the generated Markdown. |
| Reading/writing result files | [`schemas.py`](../../src/microcosm_core/schemas.py), [`receipts.py`](../../src/microcosm_core/receipts.py) | Strict JSON input, atomic writes and tests that preserve committed results. |
| Installed resources or distributions | [`resource_root.py`](../../src/microcosm_core/resource_root.py), `pyproject.toml`, `MANIFEST.in` | Installed commands must work outside the checkout with their shipped inputs. |
| Local verification or CI | `Makefile`, `.github/workflows/ci.yml` | The same public checks must be reproducible locally. |

`src/plectis/repair`, `src/plectis/compatibility`, `src/plectis/views` and `src/plectis/publish.py`
are independently importable experiments. They use no catalogue, provider or
private-workbench state. Their formal sources live under `formal/`; generated
code is retained with exact hashes and its upstream licence. Keep the model
adapter, proved algorithm and persistence host distinct. The integration example
composes operations explicitly; there is no second orchestration framework.
The shared `_sealed_kernel.py` owns captured-source loading for generated
workers. Update its explicit inventory and manifest pin only after reviewing
and regenerating the corresponding formal core. Public views is an optional
pure report transformation, with no dependency on the workflow or storage APIs.

The command-line aliases in `src/plectis/` still delegate to `microcosm_core`.
Common catalogue behavior belongs there. The shared `component_replay.py` host
owns capture, runner execution and receipt handling for both replay entrypoints.
Its aggregate verdict calls the independently importable `plectis.replay` core.
Keep the domain checker, observation capture and admission decision distinct: an
admitted observation does not prove the runner's own implementation or claim.
New command handlers should call reusable functions in their owning module;
argument parsing should stay separate from computation and file writes.

Reference capsules execute the source copies declared by their bundle
manifests. Keep their imports scoped to that bundle; a sibling private checkout
must not supply missing modules. The Oracle capsule's original pytest witness
uses the selected interpreter and the package's test extras. The Demo Take
Swift witness requires macOS and Swift 6 and builds the copied app without
launching it. Build output stays outside the source tree; set
`PLECTIS_SWIFT_BUILD_ROOT` to choose its cache volume.

Use `make check` for the fast registry/source gate, focused pytest files for
the changed behavior, and `make ci` for the integrated public check. Packaging
changes also need `make package-smoke`: a source import alone cannot show
whether a distribution contains its required files. The
[validation runbook](validation.md) describes the wider release checks.

## Maintenance program placement

The [script guide](../../scripts/README.md) owns the role map: `build`, `check`,
`release`, `inspect` and `papers`. Keep regression suites in `tests/` and paper
text in `docs/papers/`. The [layout policy](repository-layout.json) and its
[checker](../../scripts/check/check_repository_layout.py) reject misplaced
programs and tests in `make check` and CI. Negative fixtures exercise staged
additions, staged deletions and ignored output. This is a placement contract,
not a file-count target. Published source bundles retain their original paths.

## Keep each document in its role

Authored guides explain mechanisms, assumptions and decisions. Edit that
explanation directly. Generate component inventories, commands, counts and
source identities from their code or JSON owners. Preserve dated experiment
records as history; a saved result does not become current when it is copied.

Retire a one-off producer when its experiment is complete and no current
command or validator consumes it. Keep the resulting evidence at its published
path. For example, the saved code-lens spine attestation records a completed
release-wave comparison; its unused writer was removed. Current code-lens
navigation comes from `build_code_lens_join_index.py`, and current review
packets come from `make release-review`.

The shipped doctrine-enrichment health is a saved snapshot. Its full instance
corpora are not distributed here, so its builder permits local inspection but
rejects `--write` and `--check` when a declared source directory is missing.
Restore the source tree before regenerating or checking that snapshot.

The root reference paths are intentional public interfaces. Their generators,
package metadata and incoming links already use them. Consolidate their
content and writers before considering a move.

| Surface | Source or builder |
|---|---|
| `README.md`, `docs/overview.md` | Authored introduction and fuller project explanation. Keep runnable first contact in the README and background in the overview. |
| `docs/guides/`, `docs/reference/`, `docs/maintainers/` | Worked examples, lookup material and maintenance instructions respectively. Each has a README index; add links there when adding a page. |
| `examples/README.md`, `fixtures/README.md`, `receipts/README.md` | Authored directory guides. Explain inputs, test cases and recorded outputs without relocating source copies or historical data. |
| `ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md`, agent route JSON | [`organ_atlas.py`](../../src/microcosm_core/projections/organ_atlas.py), reading the component registries under `core/`; run `PYTHONPATH=src python3 scripts/build/build_organ_atlas.py --write`. |
| `docs/reference/lean-companion.md` snapshot/release bullets | [`check_lean_companion_snapshot.py`](../../scripts/check/check_lean_companion_snapshot.py), using `docs/lean_companion_snapshot.json`. Preserve these managed bullets during reference-page edits; the checker owns refresh and validation. |
| `FIRST_ACTION.md` | [`build_first_action_demo.py`](../../scripts/build/build_first_action_demo.py). |
| `RELEASE_REVIEW.md` | [`build_release_review.py`](../../scripts/build/build_release_review.py), using the result contract in [`release_candidate_proof.py`](../../src/microcosm_core/release_candidate_proof.py). |
| `PRINCIPLES.md`, `ANTI_PRINCIPLES.md`, `AXIOMS.md` | Authored doctrine consumed by [`doctrine_lattice.py`](../../src/microcosm_core/doctrine_lattice.py) and `standards/`. Preserve the authored argument and regenerate its projections. |
| `PROVENANCE.md`, `SOURCE_STATUS.md` | Authored source and attribution explanations governed by the [public boundary](../governance/public-boundary.md). |
| Published source copies and their manifests | [`refresh_source_module_manifest.py`](../../scripts/release/refresh_source_module_manifest.py) and the [exporter](../../src/microcosm_core/release_export.py). Preserve source attribution, omissions and public replacements. |

Do not rehash changed copies merely to make a check pass. Check their declared
source or the export inventory, and report upstream currentness as unassessed
when those upstream bytes are unavailable. Copy identity, successful execution,
mathematical meaning and publication status answer separate questions.

When restoring an omitted snapshot, first match its saved digest. Recover
missing support files from the same source revision when possible; mixing a
recorded module with today's dependencies can change the experiment. Record
new dependency revisions and any public reference normalization in the bundle
manifest, then exercise the surviving public entry point.

## Change producers and consumers together

Before removing or moving a path, check its imports, callers, Markdown links,
JSON references and public API. Update these owners as applicable:

- **Export:** `release_export.py` owns `DEFAULT_INCLUDE_REFS`,
  `STANDALONE_REQUIRED_PUBLIC_REFS` and `LICENSE_NOTICE_REQUIRED_REFS`.
  [`MANIFEST.in`](../../MANIFEST.in) and [`pyproject.toml`](../../pyproject.toml)
  own installed package destinations. The package and export tests check both.
- **Generated links:** change output constants and relative links in each
  generator, then regenerate. A writer's new path does not update a separate
  reader: `build_release_review.py::FIRST_ACTION_DOC_REL`, for example, reads
  and hashes the first-action document.
- **Navigation:** update the command outputs, agent instructions, entry
  validators, atlas links and source-reference fields that consume the path.
  [`public_repo_profile.py`](../../scripts/check/public_repo_profile.py) checks the
  root classification and requires each retained reference's owner to exist.
- **Evidence:** changed input bytes invalidate affected current results.
  Regenerate through the recorded producer. Leave historical receipt payloads
  and immutable published identities intact.

Run the affected checks, `make ci`, and the exported copy's checks after
integration. A new pathname or one passing test does not establish parity.
Use a short compatibility link only when a real incoming reference needs it.

## Preserve the CLI contract during refactoring

The public imports `microcosm_core.cli:main` and `plectis.cli`, console commands
`plectis` and `microcosm`, and package entry points `python3 -m plectis` and
`python3 -m microcosm_core` must continue to work.

Two consumers inspect source syntax as well as Python imports:

- [`organ_surface_contract.py`](../../src/microcosm_core/projections/organ_surface_contract.py)
  extracts command names from literal `subparsers.add_parser(...)` and
  `_add_bundle_parser(...)` calls in `cli.py`. Preserve both forms or update
  the reader to the new registration owner.
- [`public_entry_docs.py`](../../src/microcosm_core/validators/public_entry_docs.py)
  reads the top-level `FIRST_SCREEN_HELP` string assignment. Re-exporting the
  Python constant alone does not preserve this lookup.

For each moved command, compare aliases, accepted arguments, help, exit codes,
output and written files. Run the CLI and component-surface tests, including
commands omitted from short root help. Keep a behavior repair testable before
extracting its implementation; no new command framework is required.
