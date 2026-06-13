# Microcosm Axiom Substrate

The Microcosm axiom substrate routes a reader from axiom doctrine to a read-only
evaluator that measures how much on-disk evidence actually backs each axiom, and
reports where that evidence runs out.

## Purpose

A doctrine file can assert that a system holds twelve axioms. The harder question
is whether anything checkable stands behind each one. This module answers a single
question: for each piloted axiom, how strong is the support that already exists on
disk, and exactly where does it stop short of proof?

The unusual part is what the evaluator refuses to do. The routing source hand-stamps
eleven of the twelve axioms as `strong` and labels each with the anti-axiom it is
meant to reject, for example AX-1 against `asserted_label_is_truth` or AX-5 against
`silent_default_pass`. The evaluator reads those labels and declines to ratify them.
It recomputes support from the witness organs, checker surfaces, receipts, and
negative cases each obligation actually cites, and for every axiom it returns a
`strongest_allowed_claim` that is capped below `strong`. No node ever reports
`strong_certified: true`. The honesty contract is turned on the evaluator itself:
because the evaluator is also a Microcosm artifact, AX-12 (`meta_artifact_exemption`)
forbids it from treating its own generated output as evidence for itself.

The reason support cannot reach `strong` is made explicit rather than hidden. The
routing defines `strong` as computing the property and rejecting the named anti-axiom
with a negative case. Today the evaluator can confirm that a witness organ's receipt
records a complete negative-case suite, but it will not map that endpoint coverage onto
a particular obligation's anti-axiom slice. That mapping stays `mapping_verified: false`
unless a source-owned row declares an exact or subsuming rejection. The gap is reported
as pressure to do more witness work, never closed by relabelling.

## Teleology

Microcosm axioms compress the public substrate's recurring formal commitments
into checkable clauses. The goal is not philosophical decoration; the goal is a
routing layer where each axiom expands into principles, organs, receipts,
negative cases, witness surfaces, and layer debt.

## Governing Standard

This paper module is governed by `executable_doctrine_grammar` and the
Microcosm axiom/principle surfaces:

- `AXIOMS.md`
- `PRINCIPLES.md`
- `ANTI_PRINCIPLES.md`
- `RELEASE_DISCIPLINE.md`
- `core/axiom_organ_routing.json`
- `core/organ_evidence_classes.json`
- `standards/std_microcosm_axiom.json`
- `src/microcosm_core/validators/axiom_support_cover.py`

## Executable Support Surface

`validator.microcosm.axiom_support_cover` is the read-only executable surface for
the piloted axioms in `core/axiom_organ_routing.json`, currently AX-1 through AX-12.
It compiles `support_cases`, `support_frontiers`, `principle_support_index`,
`anti_axiom_rejection_mappings`, and `strong_gate_summary` from source routing,
standard grammar, receipts, witness surfaces, and evidence-class registries. Its
output is a projection below source authority: it may expose pressure and
bounded overlap, but it does not mutate axioms, certify `strong`, or authorize
release.

## Shape

```mermaid
flowchart TD
    Routing["Routing rows<br/>core/axiom_organ_routing.json<br/>axiom, anti-axiom, obligations,<br/>hand-stamped witness_strength"]
    Bind["Per-obligation binding<br/>witness organs, checker surfaces,<br/>receipts, negative-case codes"]
    Resolve{"Does the binding<br/>resolve on disk?"}
    Capped["Capped support<br/>blocked or layer_debt"]
    Ceiling["Eight-component ceiling vector<br/>evidence_class, checker_scope,<br/>provenance, freshness, domain,<br/>negative_case, authority, projection"]
    Reject["Anti-axiom rejection mapping<br/>tier + mapping_relation;<br/>mapping_verified stays false<br/>without a source-owned row"]
    Meet["Bilattice meet<br/>support status AND rejection status"]
    Claim["Node claim ceiling<br/>strongest_allowed_claim<br/>strong_certified: false"]
    Pressure["Candidate-axiom pressure<br/>witness debt, rejection-mapping debt,<br/>sharpen the over-stamped row"]

    Routing --> Bind --> Resolve
    Resolve -- "no" --> Capped --> Meet
    Resolve -- "yes" --> Ceiling --> Meet
    Bind --> Reject --> Meet
    Meet --> Claim
    Claim --> Pressure
```

The shape makes the axiom substrate inspectable without converting pressure
into proof. Doctrine refs, routing JSON, the axiom standard, validator output,
and focused tests can show support/frontier structure; the capsule makes that
route walkable through a mechanism and code locus, but it cannot certify a
strong gate, promote candidate law, or authorize release.

## How support is computed

Each routing row names an axiom, the anti-axiom it should reject, and a list of
obligations. Each obligation carries a binding: the witness organs, checker
surfaces, receipts, and negative-case codes that are meant to back it. The
evaluator first checks that every cited piece of material actually resolves. A
witness organ must exist in `core/organ_registry.json`, a witness surface must
exist on disk or match a glob, and a negative-case code must be declared on the
row. Any unresolved reference caps the obligation at `blocked_binding_unresolved`
rather than letting it pass silently. An obligation the routing marks as
`layer_debt` is recorded as partial witness debt that caps the axiom without
weakening it.

For obligations whose bindings resolve, the evaluator computes a ceiling vector
across eight named components: `evidence_class`, `checker_scope`, `provenance_class`,
`freshness_state`, `domain_scope`, `negative_case_status`, `authority_scope`, and
`projection_scope`. Each component is read off the bound material, not asserted.
`evidence_class`, for instance, is the strongest evidence rank among the witness
organs and never exceeds it. `freshness_state` is pinned to its honest floor,
`unknown_live_freshness_no_refresh_contract`, because a deterministic basis digest
proves reproducibility but not that the inputs are current. Two components,
`authority_scope` and `projection_scope`, carry an explicit non-laundering note:
read-only validator output and generated projections cannot be read back as source
evidence.

The axiom-level verdict is the meet of two separate judgements. One is positive
support, folded from the obligations' resolution states. The other is the
anti-axiom rejection mapping, tracked apart from support so that organ-level
negative-case coverage can never quietly stand in for a per-obligation rejection.
Because rejection mapping is almost never verified, the meet caps every axiom below
`strong`, and the receipt records the precise blocking reason. Where an obligation
is unresolved, in layer debt, or has an unverified rejection mapping, the evaluator
emits candidate-axiom pressure: witness debt, rejection-mapping debt, or a sharpen
signal against a row whose hand-stamped `strong` it cannot certify. The forbidden
move is always the same, recorded on the pressure itself: do not lower the axiom bar
to make coverage look green.

Support for principles is derived, not measured directly. The evaluator parses each
principle's `Obligation grounding:` line in `PRINCIPLES.md` and inherits support from
the grounding obligations, so a principle is never stronger than the obligations it
rests on. As a separate guard it flags any binding that tries to cite a principle as
a witness, since a principle leaning on an axiom cannot also serve as that axiom's
evidence.

## Anti-Axiom Rejection Mapping

`std_microcosm_axiom.json::axiom_payload_contract.anti_axiom_rejection_contract`
separates positive support from rejection of a named anti-axiom. A first-wave
organ receipt with complete negative-case coverage is admissible evidence
material, not a per-obligation rejection by itself. The evaluator therefore maps
receipt-observed negative families to each obligation slice with a
`mapping_relation` such as `unmapped`, `illustrative_only`, or
`partial_overlap`, while keeping `mapping_verified: false` unless a
source-owned mapping row declares exact or subsuming rejection.

The current AX-8 mapping is intentionally non-uniform: O1 remains `unmapped`
because endpoint/organ receipt coverage does not prove general
source->transform->sink propagation; O2 is only `partial_overlap` against
sink-policy evidence; O3 is only `illustrative_only` until endpoint-label
assertion rejection is declared against that obligation. This is the
no-laundering floor: `organ_receipt_coverage_present` can never be promoted
directly into `exact_obligation_rejection`.

Those AX-8 relations live as source-owned, non-certifying rows in
`core/axiom_organ_routing.json::rows[AX-8].anti_axiom_rejection_mappings[]`.
The evaluator consumes those rows before any legacy inferred fallback and still
recomputes receipt material from disk. The rows close hidden-code-schema drift;
they do not close rejection, remove layer debt, or upgrade any obligation to
`strong`.

## Reader Proof Boundary

Read this page as a public reader projection over the JSON capsule row
`core/paper_module_capsules.json::paper_module.microcosm_axiom_substrate`.
The generated JSON row reports
`paper_module_payload.source_authority: json_capsule`, and the capsule names the
read-only axiom support-cover mechanism as its resolving subject. The generated
Mermaid projection is available from capsule edges. The generated Atlas
projection remains bounded to the capsule/organ-atlas boundary because no
accepted `microcosm_axiom_substrate` organ exists. The proof boundary is still
narrow: the capsule creates a walkable source edge to a validator mechanism and
code locus, not axiom proof, strong-gate certification, or release authority.

## JSON Capsule Binding

`paper_module.microcosm_axiom_substrate` is source-bound by
`core/paper_module_capsules.json::paper_module.microcosm_axiom_substrate`.
The generated row source ref is
`core/paper_module_capsules.json::paper_modules[97:paper_module.microcosm_axiom_substrate]`.
The checked-in `paper_modules/microcosm_axiom_substrate.json` row is regenerated
from that capsule and keeps `paper_module_payload.source_authority:
json_capsule`. Its resolving subject is
`mechanism.microcosm_axiom_substrate.validates_public_axiom_support_boundary`,
and its resolved code locus is
`src/microcosm_core/validators/axiom_support_cover.py`.

This Markdown is a reader projection over that capsule. It may explain the
generated Mermaid projection, generated Atlas projection boundary, authority
ceiling, and proof boundary, but it cannot create stronger source authority by
prose.

## Structured Lattice Bindings

- Generated paper-module row:
  `paper_modules/microcosm_axiom_substrate.json` is regenerated from the JSON
  capsule row with `source_authority: json_capsule`, one mechanism subject, and
  a resolved validator code-locus edge.
- Axiom doctrine surfaces:
  `AXIOMS.md`, `PRINCIPLES.md`, `ANTI_PRINCIPLES.md`, and
  `RELEASE_DISCIPLINE.md` are reader-facing doctrine references for the axiom
  proof boundary. They do not become paper-module edges without a capsule row.
- Axiom routing source:
  `core/axiom_organ_routing.json` owns support/frontier rows for axiom evidence
  and anti-axiom rejection mappings.
- Evidence classes:
  `core/organ_evidence_classes.json` is the evidence-strength vocabulary used
  by the support-cover reader frame.
- Governing standard:
  `standards/std_microcosm_axiom.json` is the contract for axiom payloads,
  support claims, anti-axiom rejection mappings, and strong-gate pressure.
- Validator locus:
  `src/microcosm_core/validators/axiom_support_cover.py` is the capsule
  `code_loci` edge and remains a read-only evaluator that projects support cases
  and strong-gate pressure.

The generated sidecar binds the mechanism subject, concept, principle, axiom,
dependency, and code-locus edges that the capsule names. The mechanism's runtime
host edge is intentionally planned until a separate organ-atlas owner admits a
real `microcosm_axiom_substrate` organ or remaps the validator to an accepted
runtime host. That planned host edge is frontier pressure, not a paper-module
required-subject gap.

## JSON Capsule Boundary

This paper module is JSON-capsule-backed in the generated paper-module corpus,
with Markdown retained as the authored reader projection.

- Current authority: `paper_module_payload.source_authority` is
  `json_capsule`, and the source row is
  `core/paper_module_capsules.json::paper_module.microcosm_axiom_substrate`.
- Current proof: axiom routing rows, the support-cover validator, and focused
  tests make the substrate inspectable to readers. They do not certify axioms,
  prove strong-gate closure, or authorize release.
- Regeneration: `scripts/build_doctrine_projection.py
  --write-paper-module-corpus` and aggregate doctrine-lattice builders own the
  generated JSON/Mermaid/Atlas projection updates.

This Markdown explains the proof boundary and authority ceiling. It does not
source axiom promotion, strong-gate certification, release claims, source
mutation authority, runtime correctness, or aggregate doctrine-lattice
completion claims.

## Public Site Availability Boundary

This module is public-safe to expose as a reader route because it describes
axiom-routing doctrine, standards, validator paths, routing JSON refs, tests,
support-frontier status, and authority ceilings without promoting candidate law
or certifying a strong gate. Website availability should come from the existing
Microcosm site builder reading this source page and generated Microcosm data;
generated site HTML, object maps, search indexes, and content graphs are
projections, not source authority.

## Public-Safe Body Handling

This page may name axiom/principle docs, routing JSON paths, evidence-class
registries, standards, validator loci, focused tests, receipt commands,
support-frontier fields, anti-axiom mapping statuses, and authority ceilings.
It must not embed private source bodies, raw operator voice, provider payloads,
secret-bearing evidence, private workspace state, generated proof artifacts
outside their receipt refs, or prose that promotes candidate law, proves axioms
in Lean, certifies a strong gate, or authorizes release.

Reader cards, receipts, generated site projections, and this Markdown should
represent axiom evidence by refs, mapping statuses, booleans, summaries,
negative-case names, and explicit ceilings rather than by duplicating private
payloads or laundering evidence pressure into proof authority.

## Reader Evidence Routing

- A doctrine reader starts with `AXIOMS.md`, `PRINCIPLES.md`,
  `ANTI_PRINCIPLES.md`, and `core/axiom_organ_routing.json`. The useful
  question is which source rows claim support, frontier pressure, and
  anti-axiom mapping status, not whether this page proves the axioms.
- A validator reader runs `microcosm_core.validators.axiom_support_cover` and
  opens `tests/test_axiom_organ_routing.py` plus
  `tests/test_axiom_support_cover.py`. The useful question is whether support
  cases, support frontiers, negative-case evidence, and AX-8 rejection mapping
  readback are computed from public source.
- A release-boundary reader starts with the Authority Ceiling and anti-claim
  text before reading generated docs or site cards. The useful question is
  whether candidate law, Lean proof, strong-gate certification, release
  authority, and aggregate lattice coverage stay outside this Markdown.

Generated projections may summarize axiom evidence only by source refs, mapping
statuses, booleans, summaries, and receipt paths. Any stronger claim belongs in
source-owner rows plus validator receipts, not in this reader projection.

## Proof-Consumer Readback

This module's proof-consumer value is a narrow evidence-accounting readback:
named validators and tests consume public source refs, fixture-visible routing
rows, counts, verdict fields, and anti-claims so a reader can see where axiom
support is computed and where it is capped. These consumers do not expand the
authority ceiling, certify `strong`, promote candidate law, prove axioms in
Lean, authorize release, or mutate source authority.

- `validator.microcosm.axiom_support_cover` consumes
  `core/axiom_organ_routing.json`, `core/organ_evidence_classes.json`,
  `core/organ_registry.json`, and `standards/std_microcosm_axiom.json`, then
  emits `support_cases`, `support_frontiers`,
  `anti_axiom_rejection_mappings`, `strong_gate_summary`,
  `truth_calculus_summary`, `principle_support_index`, and
  `candidate_axiom_pressure`. Its own `authority_posture` remains
  `read_only_evaluator_projection_not_source_of_record`.
- `tests/test_axiom_organ_routing.py` consumes the routing registry plus
  `AXIOMS.md`, `PRINCIPLES.md`, `ANTI_PRINCIPLES.md`,
  `core/organ_registry.json`, and public source text to check that routed
  axioms, principles, anti-principles, witness refs, negative-case codes, and
  source-owned anti-axiom rejection mappings resolve without laundering organ
  receipt coverage into exact obligation rejection.
- `tests/test_axiom_support_cover.py` consumes the evaluator output and checks
  the proof-consumer floor: AX-1's hand-stamped `strong` label is not echoed,
  AX-8 stays capped by layer debt, principles inherit bounded support without
  becoming witnesses, candidate pressure routes to sharpening or witness debt,
  and rejection-mapping debt routes to receipt-level per-obligation evidence.
- `src/microcosm_core/doctrine_lattice.py::build_axiom_instance_from_routing_row`
  consumes routing rows into public axiom JSON instances with a
  `microcosm_axiom_substrate_reciprocity_v1` contract. That readback names how
  law constrains substrate and how substrate can refine support-frontier
  evidence, while explicitly keeping witness organs and negative cases as
  support-calculation inputs rather than support claims.
- `tests/test_doctrine_lattice_runtime.py` consumes generated axiom instances
  only to verify that reciprocity contract and routing-derived fields survive
  projection. It does not treat generated graph, health, Markdown, or Atlas
  output as source evidence.
- `tests/test_microcosm_paper_module_coverage_contract.py` consumes this
  Markdown as a capsule-backed reader lane by requiring the source capsule,
  axiom-support validator locus, generated projection boundary, and authority
  ceiling to stay in sync with generated paper-module coverage.

The readback condition is intentionally modest: if those consumers still derive
bounded support, negative-case and rejection-mapping pressure, source-ref
resolution, and authority ceilings from public source, this page remains useful
reader evidence. If a consumer starts treating generated projection output as
source evidence, or treats coverage pressure as proof correctness, the correct
repair is in the source owner or validator lane, not in stronger prose here.

## Subject Admission Audit

The live subject audit is split:

- `core/paper_module_capsules.json` contains the source-authority row for
  `paper_module.microcosm_axiom_substrate`.
- `core/mechanism_sources.json::mechanisms` contains
  `mechanism.microcosm_axiom_substrate.validates_public_axiom_support_boundary`.
- `src/microcosm_core/validators/axiom_support_cover.py` resolves as the
  capsule and mechanism code locus.
- `core/organ_registry.json::implemented_organs` does not contain an accepted
  `microcosm_axiom_substrate` organ, so the mechanism runtime-host edge and
  Atlas card remain explicitly bounded until an organ-atlas owner admits or
  remaps that host.

That is why this page routes readers to the public axiom docs, routing JSON,
validator, standard, tests, and generated paper-module sidecar without raising
the capsule into proof, release, runtime-correctness, or publication authority.

## Source Authority Re-entry Guard

The closure sequence for this module is source-first:

1. the mechanism registry admits
   `mechanism.microcosm_axiom_substrate.validates_public_axiom_support_boundary`
   as a read-only validator mechanism;
2. the paper-module capsule names that mechanism as its resolving subject,
   names the resolved validator `code_loci`, and retains existing
   axiom/principle/concept refs plus the same anti-claim ceiling;
3. owner builders regenerate the mechanism corpus, paper-module corpus, and
   aggregate doctrine-lattice surfaces from source authority;
4. readiness evidence must prove `required_subject_gap_ids` no longer includes
   this module and that Mermaid moved to `available_from_capsule_edges` because
   the source row exists.

This Markdown remains a public-safe reader route over axiom support evidence,
not source authority for claims beyond the capsule edge. Generated site
availability follows the same source-coupling boundary: the website may expose
this source page through the existing builder, but generated site files should
only be regenerated and committed after all dirty source inputs are clean or
owned and the public-site builder plus secret scan pass under claim.

## Capsule Re-entry Packet

- current source authority: generated JSON reports
  `paper_module_payload.source_authority: json_capsule`.
- generated row source ref:
  `core/paper_module_capsules.json::paper_modules[97:paper_module.microcosm_axiom_substrate]`.
- current generated projection status: Mermaid `available_from_capsule_edges`;
  Atlas `blocked_until_organ_atlas_owner_lane_binds_edges`.
- resolved code locus:
  `src/microcosm_core/validators/axiom_support_cover.py`.
- resolving authority edge:
  `mechanism.microcosm_axiom_substrate.validates_public_axiom_support_boundary`.
- regeneration route: after source edits, run
  `scripts/build_doctrine_projection.py --write-mechanism-corpus`,
  `scripts/build_doctrine_projection.py --write-paper-module-corpus`, and the
  aggregate surface builder, then verify the readiness audit.
- authority ceiling: this Markdown and its generated projections provide reader
  evidence only; they do not source axiom promotion, strong-gate certification,
  release claims, source mutation authority, runtime correctness, or aggregate
  doctrine-lattice completion.

## Claim Ceiling

This module proves only that the axiom-support boundary is inspectable through
public doctrine refs, routing rows, evidence-class vocabulary, validator loci,
support-frontier receipts, and anti-axiom mapping statuses. A diagram view and
navigation-atlas card for this module are not yet generated because the module
has not been admitted through the standard subject-resolution path; it does not
create capsule authority, promote candidate law, prove axioms in Lean, certify
the support-cover strong gate, close rejection obligations, authorize publication
or release, mutate source authority, or stand alone as a complete coverage
claim.

## Authority Ceiling

This module is a reader instrument for a staged paper-module boundary. It does
not generate diagram views or navigation-atlas cards, create or amend
`core/paper_module_capsules.json`, certify the support-cover strong gate,
promote candidate law, prove axioms in Lean, authorize publication or release,
mutate source authority, or stand alone as a complete coverage claim.
Those effects require source-owner rows, builder regeneration, and
their own validation receipts.

## Receipt Expectations

A valid update should provide:

- a paper-module structural read coverage receipt,
- JSON validation for `core/axiom_organ_routing.json`,
- route parity between `AXIOMS.md`, `PRINCIPLES.md`, `ANTI_PRINCIPLES.md`, and
  the routing registry,
- parity between `anti_principle.guards.axiom` lattice intent and
  `core/axiom_organ_routing.json::rows[].anti_principle_ids`,
- existence checks for every witness organ and non-organ witness surface named,
- evidence that every negative-case code named in the routing registry exists in
  public source, fixtures, tests, or standards,
- focused tests for the axiom routing registry,
- focused tests for `validator.microcosm.axiom_support_cover`,
- evaluator readback showing `anti_axiom_rejection_mappings` and
  `strong_gate_summary` for AX-8,
- confirmation that generated docs/projections were regenerated or deliberately
  left untouched with a re-entry condition.

## Validation Receipt Path

Reader-verifiable evaluator command, run from the `microcosm-substrate/`
public root:

```bash
PYTHONPATH=src ../repo-python \
  -m microcosm_core.validators.axiom_support_cover \
  --root . \
  --out /tmp/microcosm-axiom-support-cover-vrp.json
```

Focused test receipt, run from the repository root:

```bash
PYTHONPATH=microcosm-substrate/src ./repo-pytest \
  microcosm-substrate/tests/test_axiom_organ_routing.py \
  microcosm-substrate/tests/test_axiom_support_cover.py \
  -q --basetemp /tmp/microcosm-axiom-substrate-tests
```

The evaluator command writes a read-only support-cover receipt that reports
support cases, support frontiers, anti-axiom rejection mappings, principle
support inheritance, and strong-gate pressure without mutating law. The focused
tests verify routing-schema parity, witness refs, negative-case evidence,
AX-8 rejection mapping readback, and the rule that receipt coverage is not
laundered into exact obligation rejection.

This receipt path is reader-verifiable evidence only. It does not prove axioms
in Lean, certify a strong gate, promote candidate law, authorize release, or
mutate source authority.

## Prior Art Grounding

The axiom substrate draws from two older patterns: formal assumptions should be
inspectable, and machine-readable schemas should make support claims testable.
Lean's proof environment gives the immediate formal-methods analogue through
its axiom-audit practice: a theorem can be checked, then separately inspected
for assumptions through commands such as `#print axioms`. Microcosm adapts
that spirit to doctrine by making each axiom expand into witness surfaces,
negative cases, routing rows, and support-frontier status instead of treating
the axiom prose as self-certifying.

The JSON-controlled side of the module is grounded in
[JSON Schema](https://json-schema.org/), which frames schemas as a way to
define validation rules, document shared structure, and improve
interoperability. The provenance side is adjacent to
[W3C PROV](https://www.w3.org/TR/prov-overview/): support rows, witness refs,
and anti-axiom mappings are evidence links with bounded meaning, not proof of
whole-system completeness.

## Anti-Claim

This module does not prove the axioms in Lean, does not claim whole-system
completeness, does not claim all paper modules were semantically exhausted by
the first write, and does not grant release authority. It is a routing and
derivation surface whose claims are bounded by the witness strengths recorded in
`core/axiom_organ_routing.json`.
