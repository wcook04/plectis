# Backend requests from the first explorer pass

The component explorer in this directory was built against the implemented
`/api/v1` contract on revision `b1bdeb185bae…` of the component index. This
note lists what the frontend needed and could not get, in priority order. Each
request names the picture it enables, the gap observed while building it, a
suggested shape and its acceptance check. Shapes are suggestions: the owners in
[the implementation map](../docs/maintainers/architecture.md#component-backend-ownership)
decide the final form.

Keep the existing rules. `/api/v1` stays additive; new fields come from the
index builder or `component_index.py`, are declared in
`component_api_contract.py` and checked in `tests/test_component_http.py`.
Requests read the validated snapshot only: no execution, no per-request file
reads, no source bodies beyond bounded, hash-bound excerpts produced when the
index is built. Retained, index-time, fresh and unknown states stay separate
fields.

## Next pass

### 1. One overview response for the map

**Picture.** The evidence map draws all 88 components, the 12 kernels, every
saved record and the declared wiring from one snapshot.

**Gap.** There is no overview route. `frontend/src/data.js` makes about 190
requests: the component list, proofs and coverage, then receipts and a
`wires_to` graph query for every component, then the detail of each
component with a modeled contract. It must check that every response carries
the same revision and restart when one does not.

**Shape.** `GET /api/v1/overview` returning, in one envelope:
`components[]` (ID, title, summary, classification, `formal_subclaim_ids`,
`proof_ids`, receipt refs with availability and reason, declared wiring IDs,
doctrine ref IDs, route IDs), `kernels[]` (proof ID, module, component IDs,
verified task count, negative-control count, binding status, consumer refs),
and the coverage totals. ETag as usual.

**Acceptance.** One request renders the map; the response stays under the
encoded cache limit; a test proves its rows agree with the existing routes for
the same snapshot.

### 2. Proofs name their components

**Gap.** A proof view has no component ID. The proof page walks the graph three
steps (proof, subclaim, claim, component) to link back.

**Shape.** `component_ids` and `claim_ids` on `/proofs` items and
`/proofs/{proof_id}`.

### 3. Display labels for classification values

**Gap.** The brief forbids a second classification registry in the frontend,
but the API returns only machine values (`algorithmic_projection`,
`work_landing_and_continuity`). As a stopgap the explorer carries display
labels in `frontend/src/evidence.js`, copied from the public site's system
map. Those tables should be deleted.

**Shape.** In metadata `component_filters`, each value as
`{value, label, description, component_count}`, from the owners that define
the families, evidence classes and truth-accounting buckets.

### 4. The specification text itself

**Picture.** A proof page that shows the Dafny specification and entry
theorems as typeset statements beside the plain-language statement, in the
manner of the Lean Exposition site's theorem plates. A broken variant shown as
the lines it changes, with the verifier's recorded rejection beside them.

**Gap.** `specification_refs` and `entry_theorem_refs` are
`file.dfy#Symbol` references only. The API serves no source text, so the
explorer cannot show what was specified.

**Shape.** Extracted when the index is built, bounded and bound to the retained
`source_sha256`: `excerpts[]` of `{ref, kind (function, predicate, lemma,
method), name, line_start, line_end, text}` for each referenced declaration,
and for each negative control `{changed_lines: [{line, original, mutated}],
description}`. Fail index generation when an excerpt's hash binding does not
match.

**Acceptance.** Excerpts appear for all 12 kernels; total size stays within the
snapshot limits; the existing source-body guard still rejects anything else.

### 5. Name the verified tasks and the broken variants

**Picture.** On the map each kernel has one petal per verified task. Pointing at
a petal should name the task (`RowExact`, `BatchExact`); each cross should say
what its variant breaks ("restores first-match selection").

**Gap.** Retained verification gives `verified_tasks: 16` as a count. Negative
controls give a file path and an error count. The paper describes the
ownership variants in words; the index does not.

**Shape.** `retained_verification.tasks[]` of `{name, kind}` where the retained
Dafny record has them (`unrecorded` where it does not), and `description` on
each negative control from its metadata.

### 6. Doctrine titles

**Picture.** An outer ring of the rules the components cite (12 axioms, 20
principles, and the failure modes), each lit when a component that cites it is
chosen, as on the site's system map.

**Gap.** `doctrine_ref` graph nodes carry only `AX-3` or `P-16`. Without titles
the rules cannot be shown to a reader. Failure modes (anti-principles) do not
appear at all.

**Shape.** `title`, one-line `plain` text and `kind` on doctrine nodes, from
the `AXIOMS.md`, `PRINCIPLES.md` and `ANTI_PRINCIPLES.md` owners; a principle's
`rests_on` axioms as edges.

### 7. The four workflow cores

**Picture.** The paper's centre has 16 verified computations: 12 component
kernels and four workflow and replay-admission cores. The map can draw only
the 12.

**Gap.** `plectis.repair`, `plectis.compatibility`, `plectis.views` and the
replay-admission core are not in the component index.

**Shape.** A `cores` collection with the proof-view fields (statement,
assumptions, limits, verified tasks, negative controls, generated refs,
binding) and their public callers (the operation APIs). Replay admission
should name the replay routes it admits, so the map can show it as the gate
every saved component run passes.

### 8. The ownership repair as data

**Picture.** On the ownership kernel, the paper's counterexample played out: the
same two claims in both orders, the old first-match decision flipping, the
repaired decision holding. This is the clearest demonstration of why a proof
needs a requirements review, and the strongest story for a technical reader.

**Gap.** The example exists only as a table in the paper.

**Shape.** A structured record in the index: the observations, both orders, the
previous and repaired decisions, and the test refs that exercise them through
the caller.

## Later, or needing a decision

### 9. The source revision behind the index

Metadata could carry the Git commit and repository the index was generated
from (`source_revision`), kept separate from `snapshot_revision`. The brief
allows links only to an explicitly configured, known revision; this would let
every reference become a link to exact source. Today references are text.

### 10. Typed relations between components

`wires_to` is declared, untyped wiring. The site's system map already draws
typed relations read from code (runs, reads saved results of, checks copied
files of) with path and line evidence. Exposing those as edge kinds would let
the map draw relations with meaning, keeping `wires_to` as the declared layer.

### 11. Requirements review records

Every claim and contract reports `requirements_review: unrecorded`. A schema
for a recorded review (requirement text, reviewer, date, outcome, limits) would
let the explorer show reviewed and unreviewed specifications distinctly. The
ownership repair (request 8) would be the first record.

### 12. Saved-record summaries and dates

Bounded public fields from each available record (recorded status, counts,
fixture ID, `created_at`) and dates for all records (38 components have no
date for their last run today). This would colour the record stacks by what
they recorded and allow a timeline of how the evidence accumulated.

### 13. Clause-level claim coverage

Whole-claim coverage is `unknown` for all 88 components. A claim split into
clauses, each linked to the evidence that covers it, would let the explorer
say "3 of 5 clauses mapped" instead of unknown, without implying a score.

### 14. Fresh local runs (needs an authority decision)

The explorer keeps the core's right-hand satellite hollow because no fresh
prover or replay result is recorded. An explicit opt-in, such as
`serve-components --fresh-runs .microcosm/component-replays`, could expose the
admission results of local runs, labelled as fresh local evidence with their
own time basis. The current contract says local receipts are never discovered
automatically, so this needs its own reviewed contract before it is built.
