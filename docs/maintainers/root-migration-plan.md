# Root migration plan

The public root still carries twelve Markdown documents beyond the
conventional set (README, QUICKSTART, CONTRIBUTING, SECURITY, CHANGELOG,
AGENTS, CLAUDE, plus licence and citation files). The goal is a root a
stranger can classify in ten seconds, with the deeper surfaces under `docs/`.
This is the owned plan for the remaining moves; it was deliberately split off
from the 0.2.0 surface normalisation because every one of these files is a
**live runtime input, not passive prose**, and the moves must be one
synchronized owner-coupled change per tier.

## Why this is not a simple `git mv`

A full consumer map (July 2026) found, for the candidate set below:

- Three inclusion registries in `src/microcosm_core/release_export.py`
  (`DEFAULT_INCLUDE_REFS`, `STANDALONE_REQUIRED_PUBLIC_REFS`, the severance
  list) plus special-cased `PROVENANCE.md` refs.
- Exact-equality packaging pins: `MANIFEST.in` and the
  `[tool.setuptools.data-files]` list, both asserted line-by-line by
  `tests/test_package_data_contract.py` and `tests/test_release_export.py`.
- Five files are **generated** and embed each other's names in their output:
  `ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md` (writer:
  `projections/organ_atlas.py`, `*_MD_REL` constants), `FIRST_ACTION.md`
  (writer: `scripts/build_first_action_demo.py`), `RELEASE_REVIEW.md`
  (writer: `scripts/build_release_review.py`, path from
  `release_candidate_proof.py::REVIEW_DOC_REL`).
- Doctrine sources are parity-gated: `doctrine_lattice.py` seeds and checks
  its JSON corpus **from** `PRINCIPLES.md` / `ANTI_PRINCIPLES.md`, emits
  `AXIOMS.md#<axiom_id>` route anchors, and `standards/` carries ~111
  `AXIOMS.md` references; `atlas/` carries ~563 `ORGANS.md#...` anchors that
  regenerate from the builder.
- Validators pin paths and link literals: `public_entry_docs.py`
  (`REQUIRED_DOCS`, `[System map](ORGANS.md)`, `[Release review](RELEASE_REVIEW.md)`,
  `[ORGANS.md#find-your-specialty]` phrases), `axiom_support_cover.py`
  (`PRINCIPLES_REL`), `entry_projection_faithfulness.py` (`ORGANS.md#`
  prefix), `accepted_organ_companion_gate.py`.
- Frozen `receipts/**` embed the names as historical payload strings; drift
  gates compare committed receipts to live regeneration, so renames force
  builder regeneration, never hand edits. The substitution ledger must be
  spliced per-field and canonicalized, never blanket-rewritten.

## Tiers (each tier is one synchronized commit, gated by `make ci`)

### Tier 1: inert prose (lowest coupling)

`PROVENANCE.md`, `SOURCE_STATUS.md`, `RELEASE_DISCIPLINE.md`,
`CONSTITUTION.md` → `docs/`. Touch: release_export lists, MANIFEST,
data-files, `private_state_scan.py` list (CONSTITUTION), the two packaging
tests, `test_readme_front_door._LINKED_SIBLINGS`, README/AGENTS links, and
`core/public_surface_manifest.json` rows (splice + canonicalize).

### Tier 2: generated projections

`ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md`, `FIRST_ACTION.md`,
`RELEASE_REVIEW.md` → `docs/reference/`. Change the five `*_REL` builder
constants, regenerate all five documents (which rewrites their ~600 mutual
anchors), then sweep the validator pins, entry-packet refs, runtime route
strings (`first_screen_composition.py`, `runtime_shell.py`,
`comprehension.py`, `cli.py` help), `skills/cold_start_navigation.md`,
QUICKSTART/README links, packaging lists, and the pinning tests. Keep GitHub
redirect stubs at the old root paths for one release if link breakage
matters.

### Tier 3: doctrine sources (highest coupling)

`AXIOMS.md`, `PRINCIPLES.md`, `ANTI_PRINCIPLES.md` → `docs/governance/`.
Requires the doctrine-lattice REL constants, corpus re-seed and parity
re-check, `axiom_support_cover` and `axiom_organ_routing` updates, the ~111
`standards/` references (mechanical sweep + registry validation), and
substitution-ledger splices.

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
