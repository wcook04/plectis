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

## Delivered in the third pass

- The doctrine as its own routes: `GET /api/v1/doctrine` (every rule with the
  components that list it, its ties and its support verdict) and
  `GET /api/v1/doctrine/{rule_id}` (one rule, with each citation and its basis,
  `authored_atlas_row`). `grounded_in_doctrine` is described in the graph's
  edge semantics: a citation, not a check.
- Doctrine v2 in the overview: each rule's own section of its source file,
  hash-bound; for each axiom its formal clause, the routing registry's
  witnesses (named by hand), its obligations with the status the support
  checker computed when the index was built, and that checker's verdict, which
  is never a pass; and for every rule the hand-written reader content of
  `core/doctrine_enrichment.json` (plain words, an analogy and where it stops,
  why it matters, an example and a counterexample, a likely misreading, and what
  it does not prove), served as reader content, not as evidence.

The map draws all of it: the halo, the comb, the lit citations, the arcs of an
axiom's obligations, and the rule cards in the panel. An index without doctrine
v2 still draws the halo from the v1 rules and says that the reader wording is
missing. Contract 1.3.0; the doctrine's five sources (the three rule files,
`core/axiom_organ_routing.json` and `core/doctrine_enrichment.json`) are listed
with their SHA-256 hashes, and the build fails on an unknown witness, example or
enforced-in component, a rule without reader content, or a raising support
checker.

Two things to know after this pass. An index built from a worktree with
uncommitted changes records `exact_source_links: false`, so source links do not
appear until it is rebuilt from a clean commit. And
`receipts/release/release_export_receipt.json` pins an older index hash (it was
already stale before this pass); refreshing it is a release decision.

## Delivered: snapshot write-ups and plain descriptions

The API retains each component and core write-up, and each kernel's formal
README, at index build time. Overview component rows expose `plain` and
`plain_availability`. Component, core and proof detail exposes
`guide.ref`, `guide.sha256`, `guide.text` and `guide.availability`; the
snapshot's `explorer.guides` manifest retains the bound guide content. The
overview omits that manifest and full guide bodies.

The browser uses the plain lead already in the snapshot for hover and loads
full text only on selection or a detail page. It makes no `/guides` request
and no all-component prefetch. The development server retains its old guide
routes for compatibility. An old index without the new text fields stays
explicitly unrecorded; it does not acquire current file contents during an
HTTP request. Bodies from a different snapshot are withheld.

This delivers the earlier requests for snapshot write-ups, plain leads and
kernel write-ups. The map now introduces the subject and a real selectable
example before the visual key, and keeps compact previews clear of the full
selected-item reading panel.

## Delivered: compact transport and repeat-visit caching

`GET /api/v1/overview?view=map` supplies the map's complete model with redundant
records and unused receipt fields removed. It preserves core order and every
reader-facing model field. The unqualified overview remains unchanged. Both
representations are prepared once per snapshot with separate identity/gzip ETags.
Full guides remain on the existing detail routes. The frontend's HTTP/1.1 proxy
allows browsers to revalidate API responses and reuse unchanged bodies; static
code, styles and fonts also have ETags and bounded server-side caching.

## Next pass

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
