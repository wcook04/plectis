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
with a zero-instance report from a standalone checkout. Its builder refuses
`--write` and `--check` when a declared source directory is absent; running it
without those flags still reports the available local inputs. Empty source
directories are supported when the full source tree is supplied.
See the [maintenance guide](../docs/maintainers/architecture.md).

## Formal operations

`make verify-operations DAFNY=/path/to/dafny` runs the Repair, Compatibility,
public-view and replay-admission proof checkers in
`check/`, regenerates the executable Python and compares its bytes, and requires
negative variants to fail. Without `--dafny`, those scripts only check
recorded hashes and the generated source inventories. `release/verify_operations_install.py` exercises the APIs from
an installed interpreter in isolated mode; `make package-smoke` includes it.

`make verify-components DAFNY=/path/to/dafny` runs
`check/check_component_kernels.py` to reprove the twelve registered component
kernels, regenerate their Python and check the source-linked mutants. Without
`--dafny`, that checker verifies saved hash bindings rather than rerunning the
prover. The installation smoke check also exercises the component wrappers.

See [formal/README.md](../formal/README.md) and the [component proof index](../formal/components/README.md)
for assumptions and reproduction.

## Component explorer snapshot

Regenerate the backend's single snapshot from the canonical registry, current
registered-runner lens, formal hash records and public source owners:

```bash
PYTHONPATH=src python3 scripts/build/build_code_lens_join_index.py --claim-assurance --registered-runners
```

The builder validates before atomically replacing
`receipts/code_lens/code_lens_join_index_v0.json`. It does not run the prover or
component replays. For an isolated candidate, pass `--out /tmp/component-index.json`.
The build-time collectors live under `src/microcosm_core/projections/`; runtime
admission and the HTTP contract stay under `src/microcosm_core/`. The
[ownership map](../docs/maintainers/architecture.md#component-backend-ownership)
and [HTTP reference](../docs/reference/component-http-api.md) explain those boundaries.

## Earlier command paths

The following maintenance programs moved on 13 October 2026. Historical papers
and saved evidence may quote the former command. Use the current path for new
runs; the program purpose and arguments are unchanged.

| Earlier directory | Current directory | Programs |
|---|---|---|
| `scripts/` | `scripts/build/` | `build_code_lens_join_index.py`, `build_doctrine_enrichment_health.py`, `build_doctrine_projection.py`, `build_first_action_demo.py`, `build_organ_atlas.py`, `build_release_review.py` |
| `scripts/` | `scripts/check/` | `check_artifact_budget.py`, `check_doctrine_formal_soundness.py`, `check_doctrine_reader_ladder.py`, `check_lean_companion_snapshot.py`, `check_lean_proof_trust.py`, `check_markdown_table_render.py`, `check_public_system_paper.py`, `check_smoke_outputs.py`, `public_repo_profile.py`, `public_site_parity.py`, `served_status_smoke.py` |
| `scripts/` | `scripts/release/` | `package_install_smoke.py`, `refresh_source_module_manifest.py`, `release_candidate_proof.py`, `skeptic_flight_recorder.py` |
| `scripts/` | `scripts/inspect/` | `first_screen_composition_card.py`, `workingness_card.py` |
| `docs/papers/` | `scripts/papers/` | `paper_corpus_renderer.py`, `check_paper_corpus.py`, `check_publication_taxonomy.py`, `build_publication_taxonomy.py`, `refresh_paper_corpus.py` |

The former `scripts/build_code_lens_spine_attestation.py` (later moved to
`scripts/build/`) was retired after its release-wave comparison was recorded.
It had no current command or validator consumer. The
[saved attestation](../receipts/code_lens/code_lens_spine_attestation_v1.json)
retains that comparison and its original path references. Use the current
code-lens join builder for navigation data and `make release-review` for a new
review packet; neither rewrites the historical attestation.
