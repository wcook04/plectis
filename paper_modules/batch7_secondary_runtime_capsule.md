# Batch 7 Secondary Runtime Capsule

`batch7_secondary_runtime_capsule` imports a second Batch-7 runtime slice into
Microcosm. It exact-copies public-safe runtime view-model, lane-progress,
graph-lens, graph-projection, cartography, stockgrid, and Polymarket source
bodies into a public bundle, runs the bounded witness path, and exercises the
Python market/numeric cores against synthetic public fixtures.

## Imported Macro Bodies

- `system/server/ui/src/components/world/agentTraceViewModel.ts`
- `system/server/ui/src/components/world/laneProgress.ts`
- `system/server/ui/src/components/graph/universalGraphLens.ts`
- `system/server/ui/src/components/graph/graphProjection.ts`
- `system/server/ui/src/lib/capCartographyShadowRender.ts`
- their focused Vitest witnesses where public-safe
- `tools/stockgrid/stockgrid.py`
- `tools/polymarket/clob_snapshot.py`
- `tools/polymarket/score.py`
- `tools/polymarket/models.py`

## Purpose

This module is the reader-facing instrument for the accepted
`batch7_secondary_runtime_capsule` organ. Its source authority is the JSON
capsule row in `core/paper_module_capsules.json`; this Markdown explains what a
cold reader may trust from the public secondary-runtime fixture and what remains
out of scope.

The organ exists to answer one question: do these copied frontend and market
bodies still behave the way their original code claims to, when run in
isolation over synthetic inputs? It copies eight public-safe slices into a
bundle, then exercises each one against a small fixture and re-checks the exact
behaviour the original author relied on. The interesting part is not that the
code runs, but that each engine is paired with a planted regression. The organ
mutates a single token in the copied body, or feeds an adversarial input, and
asserts that the behaviour breaks in the expected way. A check that only passes
on good input proves little; a check that also fails on the right bad input is
evidence the behaviour is real.

Several of these guards encode a concrete bug that was found in production. The
Polymarket order-book reader documents a probe from 2026-05-12: the API can
return bids floor-first and asks ceiling-first, so a naive `bids[0]` / `asks[0]`
reader silently inverts best-bid and best-ask. The body derives best prices by
numeric extrema instead, and the `polymarket_sorted_book_trap` case feeds a
deliberately mis-sorted book to confirm the extrema rule still holds. The
stockgrid momentum primitive refuses an impossible -100% daily change rather
than returning a misleading number. The graph projection drops self-edges so a
collapsed cluster does not draw an arrow to itself. The scope stays narrow on
purpose: this is local body import and synthetic-fixture witness evidence, not
live market access, wallet authority, browser export, or investment advice.

## JSON Capsule Binding

- Source row:
  `core/paper_module_capsules.json::paper_modules[95:paper_module.batch7_secondary_runtime_capsule]`
- `source_authority: json_capsule`
- Subject: `organ:batch7_secondary_runtime_capsule`
- Mechanism validation:
  `mechanism.batch7_secondary_runtime_capsule.validates_public_secondary_runtime_capsule`
- Code locus:
  `src/microcosm_core/organs/batch7_secondary_runtime_capsule.py`
- This Markdown is a reader projection. The generated Mermaid projection and
  generated Atlas projection are navigation surfaces derived from the capsule
  edges. They are not source authority.
- The proof boundary is the Batch-7 secondary runtime public source-body import
  fixture, graph/cartography/market exercises, required-anchor checks, negative
  cases, digest checks, and body-free validation receipts.
- The authority ceiling excludes browser/session export, wallet authority, live
  market data, investment advice, provider dispatch, private-root equivalence,
  source mutation, release approval, publication, semantic truth, and complete
  UI or ranking coverage.

## Shape

```mermaid
flowchart TD
  bundle["Exported bundle\ncopied public-safe bodies\n+ source digest anchors"]
  witness["Vitest witness\nworld/graph/cartography tests"]

  subgraph Engines["Eight fixture engines"]
    ui["Trace view-model\nand lane progress"]
    graph["Graph lens\nand graph projection"]
    carto["Cartography\nobserve-only render"]
    market["Stockgrid + Polymarket\nCLOB and four-lens scoring"]
  end

  subgraph Negatives["Planted regressions"]
    invert["Mis-sorted book\nmust still find extrema"]
    momentum["-100% change\nmust be refused"]
    selfedge["Self-edge\nmust be dropped"]
    resolved["Resolved market\nmust gate NEWSBREAKER"]
  end

  receipts["Body-free receipts\nstatus, digests, anchor checks"]
  ceiling["authority ceiling"]

  bundle --> witness
  witness --> ui
  bundle --> graph
  bundle --> carto
  bundle --> market
  ui --> Negatives
  graph --> Negatives
  carto --> Negatives
  market --> Negatives
  Negatives --> receipts
  receipts --> ceiling
```

## Structured Lattice Bindings

- Subject: `organ:batch7_secondary_runtime_capsule`
- Mechanism validation:
  `mechanism.batch7_secondary_runtime_capsule.validates_public_secondary_runtime_capsule`
- Concept bundle: `concept.import_projection_and_drift_control_bundle`
- Code locus: `src/microcosm_core/organs/batch7_secondary_runtime_capsule.py`
- Governing principles: `P-2`, `P-5`, `P-9`, `P-15`
- Axiom boundaries: `AX-4`, `AX-8`, `AX-10`, `AX-11`

The generated JSON row contributes capsule-derived subject, mechanism,
concept, code-locus, principle, and axiom edges. Future edge changes must come
from `core/paper_module_capsules.json` and builder regeneration, not from
Markdown inference.

## Reader Evidence Routing

Start from the organ source when checking behavior:

- `EXPECTED_ENGINES` names the eight fixture engines for trace view-models,
  lane progress, graph lenses, graph projection, cartography, stockgrid, CLOB
  microstructure, and Polymarket scoring.
- `EXPECTED_NEGATIVE_CASES` names the planted regressions for raw-authority
  omission, unknown lane state, hidden descendants, self edges, observe-only
  cartography, extreme stock momentum, sorted-book traps, and resolved-market
  gating.
- `AUTHORITY_CEILING` keeps release, publication, provider/model dispatch,
  browser or wallet access, source mutation, investment advice, semantic-truth
  authority, and test-completeness proof false.
- `run`, `run_batch7_secondary_bundle`, and `result_card` expose the
  reproducible command and body-free summary.

## What the engines check

Each engine reads a copied body and asserts a specific, checkable behaviour.
The four with the clearest stakes:

- **Polymarket CLOB microstructure.** `compute_best_prices` derives the best
  bid as the maximum bid price and the best ask as the minimum ask price, never
  from the first row of each side. This guards a real failure documented in the
  source: the API can return bids floor-first and asks ceiling-first, which
  inverts a naive `bids[0]` / `asks[0]` reader. The `polymarket_sorted_book_trap`
  case feeds a mis-sorted book and confirms the chosen best bid (0.42) and ask
  (0.53) are not the first entries, then checks the spread and that depth
  imbalance stays in `[-1, 1]`.
- **Stockgrid momentum.** `_daily_log_momentum_bps` converts a percentage
  change into a daily log-return in basis points, but returns nothing when the
  ratio is at or below -0.999999. A claimed -100% daily change has no finite log
  return, so the primitive refuses it rather than emitting a misleading value.
  The `stockgrid_extreme_momentum` case asserts that refusal.
- **Graph projection.** `projectGraphForRender` groups nodes into per-lane,
  per-wave summary clusters and rewrites edges between clusters. It drops any
  edge whose source and target land in the same cluster, so a collapsed cluster
  never draws an arrow to itself. The `graph_projection_self_edge` case removes
  the `sourceId === targetId` guard from the copied body and confirms the
  self-edge would otherwise survive.
- **Polymarket four-lens scoring.** `calculate_lenses` zeroes the NEWSBREAKER
  lens for any market that is resolved, low-volume, low-uncertainty, or an
  outlier in velocity. The fixture scores one open and one resolved synthetic
  market and asserts the resolved one scores zero on NEWSBREAKER while the open
  one does not.

The remaining engines cover the trace view-model trust taxonomy (seven labels
including `missing` and `fallback`, with an explicit "raw provider JSONL is
unavailable" path), lane-progress state normalisation (an unknown state falls
back to `idle`, not an invented status), the graph lens (collapsing a parent
keeps the parent visible but hides its descendants), and the cartography render
(a fixed set of mutating actions stays blocked, so the surface observes without
creating or editing). Each negative case is run by mutating one token in the
copied body or supplying an adversarial input, then checking the engine reports
`blocked`. The receipts record status, digests, and anchor matches only; copied
bodies and command output are never inlined.

## Reader Proof Boundary

This page is a public reader projection over a JSON-capsule-backed Microcosm
paper-module row. The useful proof is intentionally narrow: selected runtime,
graph, cartography, stockgrid, and Polymarket source bodies are copied into a
public bundle, checked by digest and anchors, exercised through synthetic
runtime and market fixtures, and summarized in body-free receipts. It does not
prove browser/session export, wallet authority, live market data, investment
advice, complete UI/ranking coverage, provider access, private-root
equivalence, source mutation authority, release readiness, publication, or
whole-system correctness.

## Public Site Availability Boundary

The public Microcosm site may expose this page as a reader route to the Batch-7
secondary runtime capsule: capsule source refs, digest rows, witness names,
negative-case labels, generated edge counts, focused validation paths, and
authority ceilings are public-safe because they describe the standalone
`microcosm-substrate` artifact and body-free receipts.

The site must not present that exposure as browser/session export, wallet
authority, live market data, investment advice, provider access, complete
UI/ranking coverage, source mutation approval, release approval, private-root
equivalence, or generated-lattice source authority.

## Public-Safe Body Handling

Receipts may expose source refs, digests, witness names, anchor names,
negative-case outcomes, acceptance JSON, generated-row status, and validation
verdicts. They must not inline copied macro source bodies, private macro-root
paths, provider payloads, credential material, browser/session state, wallet or
account state, live market data, raw UI fixture bodies, or raw command-output
bodies. Exact-copy body drift belongs to the source-open refresh lane, not to
Markdown prose.

## Claim Ceiling

This capsule can claim fixture-bound public source-body import evidence and
secondary runtime/market witness receipts. It cannot authorize browser/session
export, wallet authority, live market data, investment advice, provider
dispatch, source mutation, release, publication, private-root equivalence,
semantic truth, complete UI/ranking coverage, or whole-system correctness.

## Prior Art Grounding

The organ borrows from MVVM/read-model UI architecture, graph visualization,
and market-data board patterns: view models shape raw state for views, graph
projections make relationships inspectable, and market rows must preserve
provider identity and missingness. Useful anchors include:

- Microsoft's [MVVM guidance](https://learn.microsoft.com/en-us/dotnet/architecture/maui/mvvm),
  where view models encapsulate presentation state while separating UI from
  underlying model logic.
- [D3 force layouts](https://github.com/d3/d3-force) as a common graph
  visualization family for networks and hierarchies.
- The CFTC's [prediction markets explainer](https://www.cftc.gov/LearnandProtect/PredictionMarkets),
  as a boundary reference for event-market data and consumer caution.

Microcosm borrows the view-model, graph-projection, and market-diagnostic
shapes, but runs them only over synthetic runtime packets and synthetic market
rows. It is not browser/session export, live market data, trading advice, or
proof that frontend projections are complete.

## Validation Receipt Path

Reader-verifiable fixture command, run from `microcosm-substrate/`:

```bash
PYTHONPATH=src ../repo-python -m microcosm_core.organs.batch7_secondary_runtime_capsule run \
  --input fixtures/first_wave/batch7_secondary_runtime_capsule/input \
  --out receipts/first_wave/batch7_secondary_runtime_capsule \
  --acceptance-out receipts/acceptance/first_wave/batch7_secondary_runtime_capsule_fixture_acceptance.json \
  --card
```

Focused test receipt, run from the repository root:

```bash
PYTHONPATH=microcosm-substrate/src ./repo-pytest \
  microcosm-substrate/tests/test_batch7_secondary_runtime_capsule.py \
  -q --basetemp /tmp/microcosm-batch7-secondary-runtime-tests
```

The fixture run writes
`receipts/first_wave/batch7_secondary_runtime_capsule/batch7_secondary_runtime_capsule_result.json`,
`receipts/first_wave/batch7_secondary_runtime_capsule/batch7_secondary_runtime_capsule_validation_receipt.json`,
and
`receipts/first_wave/batch7_secondary_runtime_capsule/batch7_secondary_runtime_capsule_board.json`;
the acceptance file records fixture acceptance. The exported-bundle re-run uses
the `run-batch7-secondary-bundle` action over
`exported_batch7_secondary_runtime_capsule_bundle`.

This receipt path is public fixture evidence only. It does not export browser
or account sessions, fetch live market data, provide investment advice,
complete UI/ranking coverage, authorize release or publication, or aggregate
doctrine-lattice coverage.
