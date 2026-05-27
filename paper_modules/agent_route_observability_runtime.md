# Agent Route Observability Runtime

This public slice validates synthetic route-feedback fixtures for the agent
observability organ.

It checks actor-axis authority boundaries, route-lease consumption, duplicate
trace ids, hook-shadow advisory status, anti-pattern debt retirement, and
behavior-change evidence gates.

## Purpose

The observability surface is the place where a cold reader should see that a
local run produced a route, work transaction, event trail, evidence ref, and
authority boundary. It should not force that reader to start from raw JSON, and
it should not replace command-backed evidence with motion or dashboard style.

The useful first artifact is therefore a compact causal board: one command,
one selected route, one work/event/evidence chain, one receipt or validator
handle, and one authority ceiling. Browser views, screenshots, and videos are
allowed projections of that board, not separate claims.

## Observable First Artifact Contract

The first observable artifact must fit a single browser or terminal viewport
and preserve this order:

| Slot | Required cue | Boundary |
|---|---|---|
| Local action | Exact command, normally `microcosm hello <project>` or `microcosm tour --card <project>`. | A visual board cannot be the first proof if the command that produced it is hidden. |
| Selected route | `selected_route_id` plus a short reason. | Route explanation stays tied to the local project, not to whole-system capability. |
| Work transaction | Work id, state, and receipt ref when present. | State changes are local substrate events, not source mutation or provider execution. |
| Event and evidence chain | Event ids, evidence class, proof surface, and anti-claim. | Counts remain accounting fields, not progress or release scores. |
| Authority boundary | Authority ceiling beside the positive claim. | The board rejects hosted release, private-data equivalence, provider calls, and whole-system correctness. |
| Structural scale bridge | One line naming the larger substrate surface this run exercises. | Scale is shown as a drilldown path, not as an implied proof upgrade. |

If a renderer cannot show all slots in one viewport, it should show the command,
route, evidence class, receipt ref, and authority ceiling first, then link to
the full route model as drilldown.

## Presentation Boundary

The observatory can be made browser-first or video-friendly only by projecting
the same compact causal board. It may animate route selection, highlight event
edges, or show a receipt reveal, but it must keep the command, receipt/evidence
ref, anti-claim, and authority ceiling visible before any decorative motion.

It must not expose live operator traces, provider payloads, account/session
state, private source bodies, HUD/browser/cockpit internals, or hosted-product
claims. It may point to public fixtures, exported public bundles, generated
receipts, and public-root card emitters.

## Validation Shape

Fixture validation should continue to require actor-axis boundaries,
route-lease consumption, duplicate trace-id detection, hook-shadow advisory
status, anti-pattern debt retirement, and behavior-change evidence gates.
When an observable-first board or endpoint is present, validation should also
prefer fields that prove the compact causal order:

- command ref before visual state;
- selected route before full route graph;
- work/event/evidence refs before explanation prose;
- evidence class and anti-claim beside any counter;
- authority ceiling before hosted, release, provider, or correctness language;
- compact endpoint or board ref before raw JSON drilldown.

Anti-claim: this module does not inspect live operator traces,
prompt/provider bodies, HUD/browser/cockpit state, live Task Ledger rows,
provider payloads, private source bodies, or runtime behavior. It only defines
the public fixture and projection boundary for observable route evidence.
