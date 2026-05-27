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

1. `microcosm tour <project>`
2. `microcosm status --card <project>`
3. `microcosm proof-lab --out /tmp/microcosm-proof-lab`
4. `microcosm compile <project>`
5. Read `first_screen.selected_route_id` from tour or `selected_route_id` from compile.
6. `microcosm explain <project> <selected_route_id>`
7. `microcosm serve <project> --host 127.0.0.1 --port 8765`
8. `microcosm spine`
9. `microcosm intake`
10. `microcosm reveal`
11. `microcosm cold-reader-route-map run-route-map-bundle`

## Reader-Specific Evidence Routing

The route map should make the evidence-count frame visible before the reader
chooses a drilldown. Honest counters are not progress badges:

- A safety/evals engineer follows `microcosm status --card`, authority, and
  workingness first. The useful question is whether each claim names its
  evidence class, validator, failure mode, and authority ceiling.
- A hiring reviewer follows the first-screen card and legibility scorecard
  first. The useful question is whether small verified counts are framed as
  honest proof boundaries instead of hidden or inflated.
- A peer developer follows `microcosm tour --card`, `microcosm compile`, and
  `microcosm explain` first. The useful question is whether a fresh clone can
  reproduce the route/work/event/evidence chain locally.

The route map must therefore preserve both the command order and the evidence
interpretation order: command, receipt ref, evidence class, anti-claim,
authority ceiling, then deeper route. Reader-specific branches may hide other
branches, but they may not hide the accounting frame that prevents "1 verified
import" from being read as either failure or marketing.

## One-Screen Handoff Contract

The route map consumes the first-screen card as the handoff, not as another
route row. A cold reader should see this sequence:

1. First-screen card: claim frame, `microcosm hello <project>`, shared proof,
   evidence legend, structural join, reader rail, and exit rule.
2. Route map: the accepted command order, with receipt refs and authority
   ceilings attached to each command.
3. Reader branch: one audience-specific first action, one proof surface, one
   success criterion, and one next drilldown.

The handoff fails when the first screen turns into a complete route inventory,
or when the route map assumes the reader already understands evidence classes.
The first screen should compress; the route map should sequence; the reveal
should demonstrate the path against public receipts.

## Comparison-Backed Route Rows

Each route row should make the unusual discipline visible by naming the normal
failure mode it is avoiding. The route map is not just a command list; it is a
sequence of claim-boundary checks:

| Route row field | Failure avoided | Required reader cue |
|---|---|---|
| `command_ref` | Prose-only claims about what runs. | Show the exact local command before the claim it supports. |
| `receipt_ref` | Trusting generated summaries as source authority. | Point to the receipt or validator that bounds the row. |
| `evidence_class` | Treating all evidence as equal proof. | Label body import, subprocess witness, projection, validator, or fixture evidence. |
| `anti_claim` | Letting a successful demo imply release, production, provider, or proof authority. | State the forbidden read beside the positive claim. |
| `failure_mode_ref` | Governance looking like abstract ceremony. | Name the concrete overclaim or missing-standard case this row catches. |

Rows that omit the comparison cue are still technically navigable, but they
make the rigor invisible to a cold reader. The validator should prefer a
shorter row with command, receipt, class, anti-claim, and failure mode over a
longer row that lists more organs without explaining what each boundary
prevents.

`readme_onboarding_route` is the selected route only for projects with a README;
folders without one still get a route/work/event/evidence path through the
selected route emitted by `tour` and `compile`.

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
