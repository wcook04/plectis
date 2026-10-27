# Component index HTTP API

`plectis serve-components` exposes the existing validated public component index
on `127.0.0.1:8766`. It serves JSON for a future website or another local client.
It creates no project state and executes no component, command or prover.

The library entrypoint is `microcosm_core.component_http.ComponentApplication`.
Create it from `load_snapshot()` for the packaged index, or from an explicitly
selected curated index file. The WSGI callable can be embedded in a server;
the included CLI is a local listener with eight request threads and five-second
socket timeouts. Public deployment, authentication, execution quotas and cross-origin
access require a separate deployment design.

```sh
plectis serve-components
plectis serve-components --index /path/to/curated-index.json --port 8766
curl http://127.0.0.1:8766/api/v1/components?limit=10
```

Only `GET` and `HEAD` are accepted. All other methods return JSON status `405`
with `Allow: GET, HEAD`. The service has no raw-file or source-body route and no
project root parameter. References in responses identify public repository
material; they do not permit reading those files through this service. Local
`.microcosm` receipts are never discovered or served automatically.

| Route | Result and parameters |
|---|---|
| `/api/v1` | Snapshot metadata, graph semantics, limits and evidence boundaries |
| `/api/v1/components` | Component summaries; optional `family`, `evidence_class`, `real_substrate_disposition`, `truth_accounting_bucket`, `limit`, `cursor` |
| `/api/v1/components/<organ_id>` | Claim, primary guide, declared replay, modeled subclaims, retained proofs, indexed artifacts and evidence state |
| `/api/v1/claims` | Claim records; optional `limit`, `cursor` |
| `/api/v1/claims/<claim_id>` | One stable `claim::<organ_id>` record |
| `/api/v1/proofs` | Retained proof views; optional `limit`, `cursor` |
| `/api/v1/proofs/<proof_id>` | One stable `proof::dafny::<slug>` view |
| `/api/v1/receipts` | Indexed public receipt availability; optional `component`, `limit`, `cursor` |
| `/api/v1/coverage` | Shared index owner's coverage view, with explicit denominators and distinct evidence states |
| `/api/v1/graph` | Typed neighborhood; required `type`, `id`; optional `depth`, `max_edges`, `direction`, `edge_kind` |

Component and claim IDs come from the existing component registry and join
index. This API creates no new registry. Graph type and ID together identify a
node; the same public reference can legitimately occur as both an artifact
and a receipt. Graph terminal command strings remain descriptive metadata.
Component summaries and details include these existing classification labels.
The metadata route lists their available filter values and component counts.
Capabilities remain the recorded claim summary, primary guide, replay
configuration and graph relations; the service adds no separate capability taxonomy.

Every successful response has `schema_version: plectis_component_http_v1`,
`snapshot_revision`, and `data`. The revision is SHA-256 of the canonical JSON
for the complete validated input. List results have `items`, `total`, `limit`
and `next_cursor`. Ordering is deterministic. The default page size is 25 and
the maximum is 100. A cursor is opaque and binds its snapshot revision,
collection, filters and page size. Reusing it with another query returns
`400 invalid_cursor`; replacing its snapshot returns `409 stale_cursor`.

Graph depth defaults to 1 and cannot exceed 3. Edge count defaults to 100 and
cannot exceed 500. `direction` is `in`, `out` or `both`; `both` is the default.
`edge_kind` selects an existing graph edge class. A result with `truncated: true`
reached its edge limit; it makes no completeness claim. No theorem-to-lemma or
tactic graph is inferred where the index records that structure as deferred.

The service preindexes IDs, component views and adjacency once at startup.
Requests perform no filesystem search or current byte checks. Encoded responses
use at most 64 cache entries and 8 MiB in the default cache. Query strings are
limited to 2048 bytes and cursors to 512 characters. Oversized snapshots,
unknown schema fields, invalid relationships, private host paths and source-body
fields fail startup. Startup and request errors do not return filesystem
exception paths or tracebacks.

Successful responses include an `ETag`. `If-None-Match` supports conditional
`304` responses; `HEAD` sends the same representation headers without a body.
Errors have an `error` object with `code` and `message`; unknown IDs return `404`
and malformed or unknown parameters return `400`.

Snapshot replacement is an explicit library operation, `app.replace_index(index)`.
It validates and constructs all derived state before one atomic swap. Existing
requests finish against their captured revision. New requests use the replacement;
the old cache and pagination cursors cannot establish freshness for the new one.
Failed replacement preserves the previously valid snapshot. There is no HTTP
reload endpoint or automatic file watcher.

Retained native verification, hash binding recorded at index generation,
current backend byte checks, requirements review and fresh proof/replay results
are separate fields. Cached index data cannot establish a new proof or replay
pass. Mutation source references do not imply a successful mutation run, and
an available historical receipt does not establish the truth or freshness of
its payload. The coverage view derives from the same shared index fields and
does not collapse these states into an overall correctness percentage.
