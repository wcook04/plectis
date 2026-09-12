# Root migration plan

The documents listed in tiers 1–3 remain at the public root. The proposed
moves would put detailed guides and generated references under `docs/`,
leaving the README and common contribution, installation and security files
easier to find. Tier 4 is complete: the duplicate Codex and Cursor adapters
have been removed.

Packaging lists, generators, validators and some commands refer to these
paths. Moving a document also requires updating the programs and links that
use it. Tiers 1–3 are planned work; this page records the known dependencies
to inspect before making each move.

## Why this is not a simple `git mv`

The known dependencies include:

- In `src/microcosm_core/release_export.py`, `DEFAULT_INCLUDE_REFS` selects
  files to copy, `STANDALONE_REQUIRED_PUBLIC_REFS` lists files required in
  the export, and `LICENSE_NOTICE_REQUIRED_REFS` lists the licensing and
  provenance documents to inspect. The exporter also contains direct
  `PROVENANCE.md` references.
- Exact-equality packaging pins: `MANIFEST.in` and the
  `[tool.setuptools.data-files]` list, both asserted line-by-line by
  `tests/test_package_data_contract.py` and `tests/test_release_export.py`.
- Five files are **generated** and embed each other's names in their output:
  `ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md` (writer:
  `projections/organ_atlas.py`, `*_MD_REL` constants), `FIRST_ACTION.md`
  (writer: `scripts/build_first_action_demo.py`), `RELEASE_REVIEW.md`
  (writer: `scripts/build_release_review.py`, path from
  `release_candidate_proof.py::REVIEW_DOC_REL`).
- `doctrine_lattice.py` generates JSON records from `PRINCIPLES.md` and
  `ANTI_PRINCIPLES.md`, then compares the records with that source text.
  It also emits `AXIOMS.md#<axiom_id>` links. Files in `standards/` refer to
  `AXIOMS.md`, and generated files in `atlas/` refer to `ORGANS.md#...`.
- Validators pin paths and link literals: `public_entry_docs.py`
  (`REQUIRED_DOCS`, `[System map](ORGANS.md)`, `[Release review](RELEASE_REVIEW.md)`,
  `[ORGANS.md#find-your-specialty]` phrases), `axiom_support_cover.py`
  (`PRINCIPLES_REL`), `entry_projection_faithfulness.py` (`ORGANS.md#`
  prefix), `accepted_organ_companion_gate.py`.
- Some `receipts/**` files record the old names as historical payload
  strings. A filename in such a record is not by itself a reason to rewrite
  it. Regenerate current outputs through their builders when their inputs
  change; preserve historical records. Update substitution-ledger fields
  individually and canonicalize the result rather than replacing every
  occurrence of a filename.

## Tiers (each tier is one synchronized commit, gated by `make ci`)

### Tier 1: inert prose (lowest coupling)

Planned; these files have not moved.

`PROVENANCE.md`, `SOURCE_STATUS.md`, `RELEASE_DISCIPLINE.md`,
`CONSTITUTION.md` → `docs/`. Touch: release_export lists, MANIFEST,
data-files, `private_state_scan.py` list (CONSTITUTION), the two packaging
tests, `test_readme_front_door._LINKED_SIBLINGS`, README/AGENTS links, and
`core/public_surface_manifest.json` rows (splice + canonicalize).

### Tier 2: generated projections

Planned destination: `docs/reference/`. These files are still generated at
the root. Their output paths are defined separately from the input paths and
link text used by the generators:

| Generated document | Output-path owner |
| --- | --- |
| `ORGANS.md` | `projections/organ_atlas.py::ORGANS_MD_REL` |
| `ARCHITECTURE.md` | `projections/organ_atlas.py::ARCHITECTURE_MD_REL` |
| `AGENT_ROUTES.md` | `projections/organ_atlas.py::AGENT_ROUTES_MD_REL` |
| `FIRST_ACTION.md` | `scripts/build_first_action_demo.py::DOC_REL` |
| `RELEASE_REVIEW.md` | `release_candidate_proof.py::REVIEW_DOC_REL` |

The module paths without a `scripts/` prefix are under `src/microcosm_core/`.
For the move:

1. Change the output paths in these owners. Update readers separately:
   [`build_release_review.py`](../../scripts/build_release_review.py), for
   example, reads the first-action document through `FIRST_ACTION_DOC_REL`
   to record its size and hash. Changing the first-action writer's `DOC_REL`
   does not change that reader.
2. Update relative links in the generator source before regenerating.
   [`organ_atlas.py`](../../src/microcosm_core/projections/organ_atlas.py)
   uses `_organ_anchor()` to emit `ORGANS.md#...` and also contains literal
   links to the other generated documents. The first-action and release-review
   builders emit links too. Moving their output files does not rewrite those
   strings. Compute each link relative to the document that will contain it;
   keep existing section fragments where possible.
3. Update the other readers and links: validator paths, entry-packet refs,
   command output in `first_screen_composition.py`, `runtime_shell.py`,
   `comprehension.py` and `cli.py`, `skills/cold_start_navigation.md`,
   QUICKSTART/README links, packaging lists and the tests that assert them.
4. Regenerate through the owning builders. Verify that the relocated files
   match their generated output and that their links resolve to the intended
   files and section fragments. Check the updated first-action hash in the
   release-review output as well.

If existing external links need a transition period, leave a short Markdown
page at each old root path linking to its new location. That page is a link,
not an automatic GitHub redirect; remove it in a later release after reviewing
the remaining references.

### Tier 3: doctrine sources (highest coupling)

Planned; these files have not moved.

`AXIOMS.md`, `PRINCIPLES.md`, `ANTI_PRINCIPLES.md` → `docs/governance/`.
Requires updating the doctrine-lattice path constants, regenerating its
corpus and comparing it with the moved source text, updating
`axiom_support_cover` and `axiom_organ_routing`, and revising the references
in `standards/`. Update the relevant substitution-ledger fields and validate
the registry after those changes.

### Tier 4: adapter stubs

`CODEX.md` and `CURSOR.md` have been removed from the public root. Their
commands and limits already appear in `AGENTS.override.md` and `AGENTS.md`;
Codex and Cursor can read the native `AGENTS` files. `CLAUDE.md`, `GEMINI.md`
and `.github/copilot-instructions.md` remain for tools that use those names.

The removal changes the default and required export lists in
`src/microcosm_core/release_export.py`, the root data files in `pyproject.toml`,
`MANIFEST.in`, and the root exceptions in `scripts/public_repo_profile.py`.
The tests that use these files are `test_compact_agent_entry.py`,
`test_agent_entry_bootloader_budget.py`, `test_package_data_contract.py`,
`test_public_entry_docs.py` and `test_release_export.py`. The export test keeps
the old stubs in its input directory and verifies that neither is copied.

The older private export source retains its local adapter files but omits them
from packages and default standalone exports. Its packaging, exporter and
exported tests are updated separately from the public checkout.

`runtime_shell.py` still includes `CODEX.md::Task Ledger capture reflex` in
`source_projection_refs`. That reference names the private source of the
recording rule; the runtime does not open the removed public adapter. It and
the corresponding historical receipt remain unchanged. Other historical
fixtures, copied source modules and release inventories likewise retain the
filenames they recorded.

## Acceptance

- `make ci` green at every tier; `make validate` green at tiers 2-3.
- `scripts/public_repo_profile.py --mode python_research_tool` root-allowlist
  exceptions shrink as each tier lands and reach zero after all four tiers.
- No frozen receipt is hand-edited; regeneration receipts land through their
  owner commands.
