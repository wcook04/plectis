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
| `/api/v1/overview` | Complete overview by default; optional `view=map` selects the smaller initial-map projection |
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
| `/api/v1/doctrine` | All 49 doctrine rules (axioms, principles, failure modes) with citing components and related rule IDs; unpaged; no query parameters |
| `/api/v1/doctrine/<rule_id>` | One rule (`AX-n`, `P-n` or `AP-n`): its source statement, axiom routing and support where present, and each component citation |

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
`doctrine_ref_ids` and `route_ids`. `kernels` contains the proof views with full guide text deferred to
`/proofs/<proof_id>`; `receipts`, `wiring` and `coverage` preserve the corresponding snapshot
records. The complete encoded envelope must fit within 8 MiB or admission fails.
It supports the same HEAD and ETag rules and remains available with a disabled
response cache. Classification labels and descriptions, when supplied by the
validated index's explorer metadata, accompany metadata filter values; the HTTP
layer creates no display-label registry. A supplied source revision remains
separate from the content-derived snapshot revision.

`GET /api/v1/overview?view=map` selects a smaller precomputed initial-map
projection from the same snapshot. The default `/overview` response is unchanged.
The map view omits top-level `receipts` and `wiring`, and the duplicated
`explorer.receipt_summaries`, `explorer.proof_details` and `explorer.cores`.
Each component's `receipt_refs` keeps `ref`, `artifact_id`, `availability`,
`kind`, and `reason` when recorded; its optional summary keeps `created_at`,
`date_status`, `availability_reason`, and the recorded `status`, `fixture_id`
and `case_count`. The top-level `cores` records follow the retained
`explorer.cores` order, which the map reader uses when both lists exist; if that
list is absent, their existing order is preserved. All other overview values
are preserved. Full receipt data remains available through the default
overview and receipt routes.

Only `view=map` is accepted; omitted `view` selects the full response. Empty,
unsupported, repeated, or additional query parameters return `400
invalid_parameters`. Both views have precomputed identity and gzip bytes,
separate representation ETags, and the same snapshot revision. HEAD and
conditional GET select the requested view and encoding without building a
projection, serializing JSON, compressing data, or reading source files.

The map includes each component's authored `plain` introduction and its
`plain_availability`. Component, kernel and workflow-core details carry a
`guide` with bounded Markdown `text`, its source `ref` and SHA-256. Extraction
and source binding happen when the index is built. Requests never reopen guide
files. Older indexes explicitly return unrecorded reader content. The overview
omits the full guide manifest and sets embedded guide text to null; it preserves
plain introductions so hovering needs no network request.

Clients may send `Accept-Encoding: gzip`. Identity and deterministic gzip
representations have distinct strong ETags and `Vary: Accept-Encoding`.
The overview's compressed bytes are prepared once at snapshot admission;
other compressed responses share the bounded response cache. A conditional
request compares the selected representation, and HEAD reports its GET length
without sending a body. If neither gzip nor identity is accepted, the API
returns `406 encoding_not_acceptable`. The explorer proxy preserves these
headers and the original representation length.

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

Doctrine graph nodes retain their declared IDs and carry the index owner's
doctrine node record (see [Doctrine](#doctrine)). The graph also traverses the
owner's `rests_on` and `violates` doctrine edges; metadata advertises those
edge kinds. Available receipt summaries are attached as `summary` on receipt
records, consistently across paginated receipts and overview receipt refs.
Component detail exposes requirements-review records and clause coverage as
separate optional fields. Unknown mapped-clause counts remain `null`.

## Doctrine

The index builder writes `explorer.doctrine` with
`schema_version: plectis_explorer_doctrine_v2`. `sources` lists `AXIOMS.md`,
`PRINCIPLES.md`, `ANTI_PRINCIPLES.md`, `core/axiom_organ_routing.json` and
`core/doctrine_enrichment.json` with the SHA-256 of the bytes read at build time. Each node keeps `id`, `kind`,
`title`, `plain` and `source_ref`, and adds `statement`: the rule's own section
of its source file (for a failure mode, its table row under the table header),
at most 4000 bytes, with `statement_sha256`. A longer section fails the build
rather than being cut.

Every node has `reader`, copied from the hand-authored
`core/doctrine_enrichment.json` (`basis: authored_reader_enrichment`): a plain
reading, an analogy with its mapping and limits, why the rule matters, a likely
misreading, what it governs, requires and refuses, an example with the
components it names, a counterexample, `enforced_in_component_ids` and
`does_not_prove`. This is reader content, not support evidence. In particular
`enforced_in_component_ids` is the enrichment author's statement of where the
rule is applied, not a test result or a checked enforcement. Every named
component must be registered and every rule must have a record, or the build
fails.

Only axiom nodes have `axiom`. Its `formal_clause`, `lineage`, `anti_axiom`
and `routing` come from the authored routing registry
(`routing.basis: authored_routing_registry`). `routing.witness_strength` is a
hand-stamped label, not a computed result. Each obligation keeps its declared
status next to `computed_status`, its witness component IDs, surfaces, negative
case codes and the checker's `witness_gaps` IDs. `support` has
`basis: index_time_computed`: the build ran
`microcosm_core.validators.axiom_support_cover` once and records its `checker_id`,
`verdict`, the hand-stamped strength, whether that stamp can be certified, and
up to 16 reasons that block a strong claim. The verdict was computed when the
index was built; the server does not rerun the checker, so it says nothing
about later source changes. Every witness component ID must be a registered
component and a checker error fails the build.

`/api/v1/doctrine` returns `rules`, `edges`, `sources` and `counts` (`axiom`,
`principle`, `anti_principle`, `citations`). Each rule row has `component_ids`:
the sorted components whose `grounded_in_doctrine` edge names that rule, and
`cited_by_count`. `witness_component_ids` is the routing registry's list for an
axiom and empty otherwise. `rests_on` and `violates` list the axioms a principle
or failure mode names; `principles` and `failure_modes` list, for an axiom, the
rules naming it. `support_verdict` is the axiom's index-time verdict and `null`
for other rules. `reader_plain` and `enforced_in_component_ids` repeat the
node's authored `reader.plain` and `reader.enforced_in_component_ids`.

`/api/v1/doctrine/<rule_id>` returns the full node, the same related lists, and
`citations`. Each citation has `component_id`, `ref_kind` (`axiom` or
`principle`), `basis: authored_atlas_row` and a `source_ref` such as
`core/organ_atlas.json::organs[<organ_id>].axiom_refs`. A citation means the
component's atlas row lists the rule. It is not a check that the component
enforces the rule; metadata states this as
`graph.edge_semantics.grounded_in_doctrine`. A malformed ID returns
`400 invalid_parameters`, an unknown one `404 unknown_id`. Both routes support
HEAD and ETag. Metadata reports `doctrine_count`, and the overview's
`explorer.doctrine` carries the same v2 record.

Optional authored annotations come from `core/component_claim_annotations.json`
with `schema_version: plectis_component_annotations_v1`. Review records require
a named reviewer, date, evidence and limits; the outcome is
`adequate_for_stated_requirement`, `requires_revision` or `inconclusive`.
No annotation file is shipped merely to fill an unrecorded state: a real named,
dated review must exist first. Clause mappings bind to the SHA-256 of the exact
UTF-8 `claim_ceiling` text. Mapping every declared clause still leaves whole-claim
coverage unknown; a mapping records evidence association, not a proof of the
full claim or its requirements.
