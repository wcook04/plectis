# Cold-Reader Route Map

`cold_reader_route_map` makes Microcosm's first ten minutes executable. It
validates a public route map whose rows bind the first-run sequence to runnable
commands, docs refs, receipt refs, and authority ceilings.

## Purpose

A cold technical reader should not have to infer the product path from a long
README or raw receipt tree. The route map answers one question: what should I
run first, and what evidence proves that path is wired?
The evidence contract is source-open by default: public route cards, route
receipt bindings, route policy, exported bundle refs, and generated receipts
carry the substrate, while `secret_exclusion_scan` excludes only private source
bodies, provider payloads, account/session material, secrets, and
credential-equivalent live-access data. Receipt bodies are not inlined; they
are represented by `body_in_receipt: false` plus public runtime refs.

The accepted path is:

1. `microcosm compile <project>`
2. `microcosm explain <project> readme_onboarding_route`
3. `microcosm serve <project> --host 127.0.0.1 --port 8765`
4. `microcosm spine`
5. `microcosm intake`
6. `microcosm reveal`
7. `microcosm cold-reader-route-map run-route-map-bundle`

Each route card must include a command and public docs refs. Each route id must
also resolve to at least one receipt ref. The sequence must be ordinal sorted
so the public entry does not drift into a bag of impressive but unordered
organs.

## Validation

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.cold_reader_route_map run --input fixtures/first_wave/cold_reader_route_map/input --out receipts/first_wave/cold_reader_route_map --acceptance-out receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli cold-reader-route-map run-route-map-bundle --input examples/cold_reader_route_map/exported_cold_reader_route_map_bundle --out receipts/runtime_shell/demo_project/organs/cold_reader_route_map
```

The fixture observes negative cases for missing command refs, missing receipt
refs, route sequence gaps, release/provider overclaims, and private source body
fields. The exported bundle omits negative cases and validates the real runtime
shape used by `microcosm run`, with synthetic receipt stand-ins explicitly
disallowed as product evidence.

## Authority Ceiling

This organ is projection-only metadata. It is not route-registry authority, it
does not mutate source projects, it does not call providers, and it does not
authorize release, publication, trading or financial advice, private-data
equivalence, or whole-system correctness claims.
