# Architecture maintenance

Use the [documentation index](../README.md) to read the system and the
[validation runbook](validation.md) to check a change. This guide identifies
what to edit and which consumers must move with it.

## Keep each document in its role

Authored guides explain mechanisms, assumptions and decisions. Edit that
explanation directly. Generate component inventories, commands, counts and
source identities from their code or JSON owners. Preserve dated experiment
records as history; a saved result does not become current when it is copied.

The root reference paths are intentional public interfaces. Their generators,
package metadata and incoming links already use them. Consolidate their
content and writers before considering a move.

| Surface | Source or builder |
|---|---|
| `ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md`, agent route JSON | [`organ_atlas.py`](../../src/microcosm_core/projections/organ_atlas.py), reading the component registries under `core/`; run `PYTHONPATH=src python3 scripts/build_organ_atlas.py --write`. |
| `FIRST_ACTION.md` | [`build_first_action_demo.py`](../../scripts/build_first_action_demo.py). |
| `RELEASE_REVIEW.md` | [`build_release_review.py`](../../scripts/build_release_review.py), using the result contract in [`release_candidate_proof.py`](../../src/microcosm_core/release_candidate_proof.py). |
| `PRINCIPLES.md`, `ANTI_PRINCIPLES.md`, `AXIOMS.md` | Authored doctrine consumed by [`doctrine_lattice.py`](../../src/microcosm_core/doctrine_lattice.py) and `standards/`. Preserve the authored argument and regenerate its projections. |
| `PROVENANCE.md`, `SOURCE_STATUS.md` | Authored source and attribution explanations governed by the [public boundary](../governance/public-boundary.md). |
| Published source copies and their manifests | [`refresh_source_module_manifest.py`](../../scripts/refresh_source_module_manifest.py) and the [exporter](../../src/microcosm_core/release_export.py). Preserve source attribution, omissions and public replacements. |

Do not rehash changed copies merely to make a check pass. Check their declared
source or the export inventory, and report upstream currentness as unassessed
when those upstream bytes are unavailable. Copy identity, successful execution,
mathematical meaning and publication status answer separate questions.

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
  [`public_repo_profile.py`](../../scripts/public_repo_profile.py) checks the
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
