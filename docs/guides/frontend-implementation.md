# Build a component explorer

This is the implementation brief for a frontend developer or coding agent,
including Claude. Build a local interface that lets a reader find a Plectis
component, understand its claim, inspect the evidence and follow the source.
The backend described here is implemented. The screens below are the frontend
to build; this guide does not claim that they already exist.

Start from the current repository's [README](../../README.md), then read the
[HTTP reference](../reference/component-http-api.md). Use the existing website's
components and visual conventions when integrating there. Keep the client
separate from Python computation, proof tooling and the generated catalogue.

## Start the backend and obtain its contract

From a clone with Python 3.11 or newer, no package installation is needed:

```sh
PYTHONPATH=src python3 -m plectis serve-components --port 8766
```

The server prints its address and snapshot revision. In another terminal:

```sh
curl http://127.0.0.1:8766/api/v1
curl http://127.0.0.1:8766/api/v1/openapi.json
curl 'http://127.0.0.1:8766/api/v1/components?q=ownership&limit=25'
```

The OpenAPI 3.1 document is ordinary OpenAPI JSON, without the API response
envelope. It describes supported client fields, query parameters, headers and
errors. Its Python owner is
[`component_api_contract.py`](../../src/microcosm_core/component_api_contract.py).
Do not maintain a second route or classification registry in the frontend.
Generate client types from this document or implement the same types explicitly.
Nested evidence records permit additional fields; preserve unknown states and
show them as unrecognised values until the client understands them.

Configure the frontend development server to proxy `/api/v1` to
`http://127.0.0.1:8766`, preserving the path and response headers. Use relative
fetch URLs in the browser. The Python listener accepts IPv4 loopback only and
does not send CORS headers. A browser page on another port needs this same-origin
proxy. Binding to a public interface, authentication and hosted deployment are
separate work; this brief requires a local application.

## Reader tasks and screens

| Screen | Data | Acceptance condition |
|---|---|---|
| Component catalogue | Metadata, then `/components` | Search ID, title and summary; combine advertised classification filters; show matching total and load further pages. Search and filters survive reload through URL query state. |
| Component detail | `/components/{organ_id}` and `/receipts?component=…` | Explain the claim and limit first, then guide, declared replay, modeled subclaims, proofs and saved records. A direct URL opens this component without first visiting the catalogue. |
| Proof detail | `/proofs/{proof_id}` | Show the modeled statement, assumptions, limits, generated-code and caller references, retained verification and fresh-check state separately. |
| Coverage | `/coverage` | Label each measure with its denominator and meaning. Keep overlapping presence measures separate. Show whole-claim coverage as unknown when the API does. |
| Related records | `/graph?type=organ&id=…` | Start at the selected component and one hop. Identify nodes by both type and ID; label edge kinds. Offer a plain list alongside any graph. Show truncation and bounds. |

Use the component ID as the route key and the returned title as display text.
The list uses `organ_id`; the detail uses `component_id`. These refer to the
same registry identity. Claim and proof IDs contain colons: encode each full ID
as one URL path segment. Do not derive IDs from titles.

The detail's `claim.card` supplies the title, summary, guide reference and
`assurance_facets`. `claim.claim_ceiling` is the stated limit. `guide.ref`
locates the reading guide. `replay` describes an invocation; it is not an
instruction to execute it. `proofs` contains proof views, while `subclaims`
contains modeled contracts. `artifacts` and receipt lists describe availability.
The HTTP API serves neither their bodies nor an arbitrary repository file.

## Loading and revision rules

Every data response has `schema_version`, `snapshot_revision` and `data`.
Check the schema identifier before rendering. The revision is a digest of
the input index, **not a Git commit, timestamp or proof certificate**.

1. Read metadata first. Populate filter choices from `component_filters`,
   limits from `limits`, and graph options from `graph`.
2. Debounce search input and cancel superseded requests. Also associate each
   response with the request that created it, so an older response cannot
   replace newer search results. Omit `q` when the input is blank.
3. Use an unchanged filter/search/page-size tuple with each opaque cursor.
   Append results only when their revision matches the visible collection.
   When the query changes, discard the cursor and start at page one.
4. Keep detail, proof, receipt and graph data together only when their
   revisions agree. On a mismatch, discard the combined view and reload it.
   A changing server must produce an explicit reload state, not an endless loop.
5. On `409 stale_cursor`, discard the collection and offer or perform one
   restart from metadata. If it changes again, show a retry action.
6. Cache by full request URL and revision. If using `If-None-Match`, retain
   the matching body: `304` has none. A normal fetch without explicit ETag
   handling is also valid. `HEAD` has headers and no JSON body.

Show loading, empty results, unknown component, network failure and incompatible
schema as distinct states. A `400` is a request problem; show its bounded error
message and let the user reset filters. A `404` must not become an empty success.
Do not retry `400` or `404` continuously. On a failed refresh, label any retained
view as previously loaded. Use keyboard-operable controls, visible focus,
associated input labels and an announced loading/error state. Keep the reading
order usable at a narrow viewport without requiring a graph.

## Evidence language

| Returned fact | Display meaning | Do not infer |
|---|---|---|
| `formal_contract.status = partial` | A selected modeled computation has a contract | The whole component or application is formally proved |
| `whole_claim.status = unknown` | Whole-claim coverage has not been established | Zero defects, zero coverage, or a pass |
| Retained proof metadata | A recorded verification result tied to its recorded source | The prover ran during this request |
| `current_backend_binding.status = not_checked` | This HTTP read did not compare current source bytes | Current code matches retained evidence |
| `fresh_prover` / `fresh_replay` not recorded | No fresh result supplied by this view | Failure or success |
| Artifact `availability = available` | The index records an available public artifact | Its contents prove the claim or are current |
| Artifact `availability = unavailable` | The referenced record is absent from this snapshot | An empty or fabricated document |

Do not collapse these facts into a green “verified component” badge or a single
confidence score. Keep the modeled assumptions and limits accessible beside
the proof. Display a declared command as copyable text only; the API has no
run, publish, model-call, file-edit or prover endpoint. If execution is added
later it needs its own reviewed interaction and backend contract.

References are repository-relative source identifiers. A deployed frontend may
link them to an explicitly configured, known repository revision. Do not use
the snapshot digest as that revision or label a mutable `main` link as exact
evidence. Keep unavailable artifacts as plain text without a link. Render
recorded text as text, never as HTML; do not interpret commands or local paths.

## Delivery and checks

Deliver the frontend source, a short start command, proxy configuration and
tests against this API. Retain the backend's public import names, CLI and data
owners. Read the [implementation map](../maintainers/architecture.md) before
changing a response or adding a backend feature.

The frontend acceptance run must demonstrate:

- A real search with multiple pages, combined filters and an empty result.
- Direct detail links for `mcp_tool_authority_replay` (modeled proof present)
  and `pattern_assimilation_step` (including unavailable historical receipts).
- An unavailable record displayed without a fabricated link, and an unknown ID
  displayed as a missing resource.
- A stale pagination cursor and a cross-request revision change, without mixing
  snapshots. Use controlled mock responses for these state transitions.
- A slow earlier search that finishes after a later one without overwriting it.
- A truncated graph and an accessible list of the same returned relationships.
- Network failure, schema mismatch, keyboard navigation and narrow-screen use.

Run backend contract tests with the repository's test dependencies installed:

```sh
PYTHONPATH=src python3 -m pytest tests/test_component_http.py
```

Those tests check real HTTP responses against the published schemas. They do
not replace the frontend interaction checks or a visual review of the completed
interface. A screenshot, mock-only app or passing build alone is not acceptance.
