# Component index HTTP API

`plectis serve-components` exposes the existing validated public component index
on `127.0.0.1:8766`. It serves JSON for a future website or another local client.
It creates no project state and executes no component, command or prover.
For the client to build, use the [frontend implementation brief](../guides/frontend-implementation.md).

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
| `/api/v1/overview` | One complete map: enriched component summaries, proof views as `kernels`, public receipts, declared wiring and coverage; no query parameters |
| `/api/v1/openapi.json` | Standard OpenAPI 3.1 document, without the data envelope |
| `/api/v1/components` | Component summaries; optional `q`, `family`, `evidence_class`, `real_substrate_disposition`, `truth_accounting_bucket`, `limit`, `cursor` |
| `/api/v1/components/<organ_id>` | Claim, primary guide, declared replay, modeled subclaims, retained proofs, indexed artifacts and evidence state |
| `/api/v1/claims` | Claim records; optional `limit`, `cursor` |
| `/api/v1/claims/<claim_id>` | One stable `claim::<organ_id>` record |
| `/api/v1/proofs` | Retained proof views; optional `limit`, `cursor` |
| `/api/v1/proofs/<proof_id>` | One stable `proof::dafny::<slug>` view |
| `/api/v1/receipts` | Indexed public receipt availability; optional `component`, `limit`, `cursor` |
| `/api/v1/local-runs` | Explicit startup-only local saved-run summaries; disabled by default; no query parameters |
| `/api/v1/cores` | Workflow cores; optional `limit`, `cursor` |
| `/api/v1/cores/<core_id>` | One workflow core |
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

Every successful data response (except the raw OpenAPI document) has `schema_version: plectis_component_http_v1`,
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

The overview is one immutable encoded response compiled at snapshot admission.
Its component rows preserve every component-summary field and add `proof_ids`,
`receipt_refs` (the same artifact records as the receipts route), `wires_to`,
`doctrine_ref_ids` and `route_ids`. `kernels` contains the same proof views as
`/proofs`; `receipts`, `wiring` and `coverage` preserve the corresponding snapshot
records. The complete encoded envelope must fit within 8 MiB or admission fails.
It supports the same HEAD and ETag rules and remains available with a disabled
response cache. Classification labels and descriptions, when supplied by the
validated index's explorer metadata, accompany metadata filter values; the HTTP
layer creates no display-label registry. A supplied source revision remains
separate from the content-derived snapshot revision.

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

## Search and contract changes

`q` is a literal substring of the component ID, canonical title or summary.
Matching ignores case and leading/trailing query whitespace, and combines with
all selected classification filters. Results remain sorted by component ID.
It is neither a regular expression nor relevance ranking. Omit `q` for an
unfiltered text query; blank, whitespace-only and over-160-character values
return `400 invalid_parameters`. An unmatched query returns a normal empty page.
Search text is precomputed in memory with the snapshot, with no filesystem read
per request. The normalized search is part of cursor identity.

Metadata advertises the contract URL/version and search limit. Protocol limits
and the OpenAPI document share the owner
[`component_api_contract.py`](../../src/microcosm_core/component_api_contract.py).
The document can be consumed directly by OpenAPI tools. It specifies supported
client fields while allowing additive response fields. Full index admission
still belongs to `component_index.py`; the public schema is not a replacement
for that stricter validator. Incompatible API changes require a new versioned
route and schema; additive optional queries and fields retain `/api/v1`.

Use a same-origin development proxy for browser requests. The service does not
provide CORS, static frontend assets, authentication, remote execution or hosting.
Keep the default listener on loopback. A successful HTTP read demonstrates
snapshot availability, not the freshness or correctness of its recorded results.

Workflow cores use `/api/v1/cores` (the standard cursor pagination) and
`/api/v1/cores/<core_id>`. Their IDs are `repair`, `compatibility`, `views` and
`replay_admission` when present in the validated index. They remain separate
from component kernels. The overview includes `cores` and the detached
`explorer` extension, including declared doctrine and source provenance.
Older curated indexes can legitimately have no cores or explorer metadata.
Bounded specification excerpts and negative-control changed lines are admitted
only by the index owner's strict hash-binding and size validator; there is no
request-time source-file read or general source-body route.


Explicit local saved-run evidence is opt-in:

```sh
plectis serve-components --fresh-runs .microcosm/component-replays
plectis serve-components --index /path/to/index.json --fresh-runs /path/to/run-directory --evidence-root /path/to/source-checkout
```

`--fresh-runs` names either a `run-*` directory or a directory of direct `run-*`
children. No local directory is discovered when the option is absent.
`--evidence-root` supplies the registry source for startup admission; it defaults
to the package resource root and requires `--fresh-runs`. Its registry bytes and
component universe must match the served index, so an unrelated checkout cannot
supply policy for a curated index. Startup reads at most 32 runs, at most 2 MiB
per file and 16 MiB overall, rejects symlinks and escaping receipt references,
and rechecks saved admission observations against immutable copies. It executes
no component, replay or prover. Invalid selected evidence rejects startup.

`/api/v1/local-runs` returns the immutable allowlisted summary, also present as
`overview.local_runs`; metadata reports its status and run count. It supports
HEAD and ETag and accepts no query parameters. Enabled saved evidence binds the
snapshot revision; default disabled evidence preserves the index-only revision.
`replace_index` drops the local overlay unless explicitly supplied again.
All requests remain free of filesystem reads. The library snapshot constructor
can also accept `local_run_evidence`; its strict pure validator rejects unknown
fields, host paths, invalid hashes and components absent from the index.

The evidence kind is `explicit_local_saved_run`. Rechecked acceptance concerns
saved host observations, whose authenticity is `trusted_local_files_not_authenticated`.
The server records `fresh_execution.status: not_run_by_server`; current source
binding and input freshness remain unknown, and absent recording times remain
unrecorded. This is not a new execution or a freshness claim. Historical records,
index-time binding and requirements review remain separate.

The explorer's typed relations describe lexical Python imports between registered
runner modules, with source line and hash evidence. They do not establish that
a call occurred. Declared `wires_to` edges remain a separate layer. Receipt
summaries expose only allowlisted recorded scalar fields; dates are taken from
recorded `created_at` values, never inferred from filenames or modification
times. Each summary identifies its artifact hash; absent dates remain unrecorded.

The listener admits at most eight concurrent requests. Additional connections
are closed immediately, so saturation cannot block the accept loop or server
shutdown. Each admitted connection has a five-second absolute request-header
deadline as well as socket inactivity timeouts. Sending header bytes slowly
does not renew that deadline. Incomplete timed-out requests are closed; no
partial request text is reflected in an error or log.

Doctrine graph nodes retain their declared IDs and include `title`, `plain`,
`kind` and `source_ref` from the index owner. The graph also traverses the
owner's `rests_on` and `violates` doctrine edges; metadata advertises those
edge kinds. Available receipt summaries are attached as `summary` on receipt
records, consistently across paginated receipts and overview receipt refs.
Component detail exposes requirements-review records and clause coverage as
separate optional fields. Unknown mapped-clause counts remain `null`.

Optional authored annotations come from `core/component_claim_annotations.json`
with `schema_version: plectis_component_annotations_v1`. Review records require
a named reviewer, date, evidence and limits; the outcome is
`adequate_for_stated_requirement`, `requires_revision` or `inconclusive`.
No annotation file is shipped merely to fill an unrecorded state: a real named,
dated review must exist first. Clause mappings bind to the SHA-256 of the exact
UTF-8 `claim_ceiling` text. Mapping every declared clause still leaves whole-claim
coverage unknown; a mapping records evidence association, not a proof of the
full claim or its requirements.
