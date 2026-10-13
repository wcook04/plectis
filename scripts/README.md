# Maintenance programs

Run these from the repository root. Runtime commands live in `src/`; regression
suites live in `tests/`. This directory contains the programs that maintain and
inspect the repository itself.

| Directory | Purpose | Example |
|---|---|---|
| [build/](build/) | Regenerate documentation and maps | `PYTHONPATH=src python3 scripts/build/build_organ_atlas.py --write` |
| [check/](check/) | Check source, projections and public boundaries | `python3 scripts/check/check_repository_layout.py` |
| [release/](release/) | Package, export and verify distributions | `make package-smoke` |
| [inspect/](inspect/) | Print compact inspection cards | `python3 scripts/inspect/workingness_card.py --help` |
| [papers/](papers/) | Refresh and check publication indexes | `python3 scripts/papers/check_paper_corpus.py` |

`make check` and CI enforce the [placement policy](../docs/maintainers/repository-layout.json).
The checker reads Git's index, including staged additions and deletions, so ignored
build output does not become a repository-layout error. Stage new maintained files
before checking. Source distributions use their shipped inventory instead.

When moving a program, update its root discovery, imports, callers, package-data
destination and generated navigation. Preserve copied evidence and its provenance. In particular, the shipped
`core/doctrine_enrichment_health.json` is a saved health snapshot whose full
instance inputs are not included in this distribution; do not overwrite it
with a zero-instance report from a standalone checkout.
See the [maintenance guide](../docs/maintainers/architecture.md).

## Earlier command paths

The following maintenance programs moved on 13 October 2026. Historical papers
and saved evidence may quote the former command. Use the current path for new
runs; the program purpose and arguments are unchanged.

| Earlier directory | Current directory | Programs |
|---|---|---|
| `scripts/` | `scripts/build/` | `build_code_lens_join_index.py`, `build_code_lens_spine_attestation.py`, `build_doctrine_enrichment_health.py`, `build_doctrine_projection.py`, `build_first_action_demo.py`, `build_organ_atlas.py`, `build_release_review.py` |
| `scripts/` | `scripts/check/` | `check_artifact_budget.py`, `check_doctrine_formal_soundness.py`, `check_doctrine_reader_ladder.py`, `check_lean_companion_snapshot.py`, `check_lean_proof_trust.py`, `check_markdown_table_render.py`, `check_public_system_paper.py`, `check_smoke_outputs.py`, `public_repo_profile.py`, `public_site_parity.py`, `served_status_smoke.py` |
| `scripts/` | `scripts/release/` | `package_install_smoke.py`, `refresh_source_module_manifest.py`, `release_candidate_proof.py`, `skeptic_flight_recorder.py` |
| `scripts/` | `scripts/inspect/` | `first_screen_composition_card.py`, `workingness_card.py` |
| `docs/papers/` | `scripts/papers/` | `paper_corpus_renderer.py`, `check_paper_corpus.py`, `check_publication_taxonomy.py`, `build_publication_taxonomy.py`, `refresh_paper_corpus.py` |
