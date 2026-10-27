# Backend requests from the component explorer

The explorer in this directory reads the `/api/v1` contract. This note records
what it needed from the backend, what the second backend pass delivered, and
what the next pass should add, in priority order. Shapes are suggestions: the
owners in [the implementation map](../docs/maintainers/architecture.md#component-backend-ownership)
decide the final form.

Keep the existing rules. `/api/v1` stays additive; new fields come from the
index builder or `component_index.py`, are declared in
`component_api_contract.py` and checked in `tests/test_component_http.py`.
Requests read the validated snapshot only: no execution, no per-request file
reads, no source bodies beyond bounded, hash-bound text produced when the
index is built. Retained, index-time, fresh and unknown states stay separate
fields.

## Delivered in the second pass

The explorer now uses all of these:

- `GET /api/v1/overview`: one request draws the whole map (it replaced about
  190 requests and the revision checks between them).
- `component_ids` and `claim_ids` on proof views.
- Labels and descriptions for classification values in `component_filters`;
  the explorer's own label tables are gone.
- Hash-bound Dafny excerpts and each broken variant's changed lines, shown on
  the proof pages and in the map's kernel cards.
- The four workflow cores, with replay admission's admitted routes, drawn at
  the centre of the map with a spoke to every component.
- Doctrine titles, receipt summaries with recorded dates and statuses,
  lexical import relations and the ownership repair as a structured record
  (played through as an interactive figure).
- `source_revision`, so references open the exact commit on GitHub.

## Next pass

### 1. Write-up text and the plain lead in the snapshot

**Picture.** Hovering a component shows a five-sentence plain description in
the panel; choosing it shows the rendered write-up.

**Gap.** The API names each write-up (`guide.ref`) and records its SHA-256,
but serves no text. As a stopgap, `frontend/serve.py` reads the file from the
checkout after checking that hash (`/guides/component/<id>`), and the map
fetches all 88 write-ups to show the plain lead on hover.

**Shape.** At index build, extract each write-up's bounded text (the
component's `paper_modules/*.md`, each core's formal README) and its opening
"In plain terms" block quote. Serve `plain` on overview component rows and the
full text as `guide.text` on component and core detail, bound to the recorded
SHA-256. Fail the build when a write-up has no plain lead.

**Acceptance.** The explorer needs no file read and no request per component;
the `/guides` route in `serve.py` can be deleted.

### 2. Kernel write-ups

Each component kernel has a formal README (`formal/components/<slug>/README.md`)
that its component's write-up links to. Name it on the proof view as `guide`
with its SHA-256, like the cores, so the proof page can show it.

### 3. Excerpts for the four workflow cores

`proof_details` covers the twelve component kernels only. The cores' proof
pages list their specification by name because no excerpt is retained.
Extract the same bounded excerpts and changed lines for `repair`,
`compatibility`, `views` and `replay_admission`.

### 4. Names for the verified tasks

Each flower on the map has one petal per verified task, and the retained
metadata records only a count (`tasks_availability: unrecorded`). Recording
task names when Dafny runs (from its verification log) would let a petal say
what it checked.

### 5. Local runs on the map

`serve-components --fresh-runs` now admits saved local runs at startup. The
map can show an admitted local run by lighting that component's spoke and
replay cell in red, kept distinct from the historical records. This needs one
documented example run directory the explorer's acceptance test can start the
server with.

## Later, or needing a decision

### 6. Requirements reviews and clause coverage

The schemas for a named, dated requirements review and for clause-level claim
coverage exist, and both lists are empty. The ownership repair is the natural
first review record. With real records, the map's outer ring could say "3 of 5
clauses mapped" instead of unknown, still without a score.

### 7. Typed relations beyond imports

The ten lexical imports are the only typed relations. Relations read from code
(runs, reads saved results of, checks copied files of) with path and line
evidence would let the map draw what one component actually does to another,
keeping declared wiring as its own layer.
