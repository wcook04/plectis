# Navigation Rosetta Math

**Projection class:** subsystem
**Subsystem slug:** `navigation_rosetta_math`
**Authored:** 2026-04-24
**Status:** in_progress
**Depends on:** `navigation_hologram_theory`, `holographic_navigation_compression`, `semantic_naming_grammar`, `system_vocabulary_ontology`
**Governing principles:** `pri_049`, `pri_080`, `pri_111`, `pri_118`
**Governing concepts:** `con_001`, `con_024`, `con_028`
**Governing mechanisms:** `mech_028`
**Primary subdomain:** navigation_fidelity
**Secondary subdomains:** `compression_hierarchy`, `authority_projection`, `intermediary_drift`
**Compression atom:** Coverage-first Rosetta navigation math.
**Compression keys:** navigation rosetta math, coverage-first context, option surface math, layer-depth adequacy, relation verb grammar, impact vector navigation, population honesty
**Compression flag:** Formal model for typed option surfaces, native bands/facets, relation verbs, population honesty, and coverage-before-depth context selection.
**Open when:** You need the mathematical contract behind option surfaces, context packets, native bands/facets, relation verbs, impact vectors, or coverage-before-depth navigation.
**Do not open when:** You need ordinary cold-start routing, a concrete paper-module lookup, or the generated hologram runtime; use `--entry`, `paper_modules.cluster_flag`, or `holographic_navigation_compression` instead.
**Safe drilldown:** `./repo-python kernel.py --option-surface paper_modules --band card --ids navigation_rosetta_math`
Search aliases: navigation rosetta math, rosetta math, context compression math, noun verb grammar, impact vector navigation, information density navigation, coverage first context, layer depth math, telescope math, standard owned compression proof, navigation grammar proof

## TLDR (compressed view)

Navigation Rosetta math is the formal bridge between standard-owned navigation contracts and context packets. The system is a typed, currentness-bearing graph: artifact kinds emit native rows, scopes, facets, bands, and edge verbs; a navigator selects a bounded packet by maximizing coverage before depth, then upgrading the rows whose impact-to-cost ratio is highest. The math does not force one ladder onto every file type. A term can earn six lexical bands, a receipt may earn only two transaction bands, and Python needs structural scopes because code compresses through signatures, symbols, bodies, call graph, and source spans rather than prose length. The governing law is: expose every kind cheaply, preserve population honesty and source authority, then selectively telescope only the shard whose noun/verb/edge neighborhood justifies the context cost.

## Intent

This module exists because the system now has a Kind Atlas, option surfaces, navigation contracts, telescope exemplars, and a Rosetta context packet, but the mathematical model still lived mostly inside prose and one runtime packet. The operator pressure is sharper than "better search": agents should not guess keywords; they should read a compressed option surface, select a row, select a band/scope/facet, and uncompress only the shard needed for the current decision.

The model here states that precisely enough to test. It explains why the traversal mechanism can be uniform while the payloads remain artifact-native, why layer count is not universal, why verbs and edge glosses need standards, and why a generated packet is not current authority unless it exposes population mode, source authority, freshness, omissions, and evidence commands.

## Shape

The Rosetta shape has three layers that must stay distinct:

| Layer | Mathematical object | Computer-science object | Philosophical object |
|---|---|---|---|
| Kind | A typed set `K` of artifact families | Kind Atlas row | The system admitting what kinds of things exist before asking for a query |
| Row unit | A valid unit `u` in `U_k` for kind `k` | row, scope, facet, band, edge | A bounded object of attention |
| Packet | A selected subset `X` under cost budget `C` | emitted JSON/context packet | A finite act of care: what is preserved, what is omitted, and why |

For each kind `k`, its governing standard declares a partial product:

```text
U_k subset Scopes_k x Facets_k x Bands_k
```

The product is partial because not every combination is legal. A paper module may have a `gap` facet at module or section scope. A Python function may have a `signature` facet and a `body` facet, but "module gap signature" is not a legal unit. The standard owns those legal combinations.

Rows also live in a typed edge graph:

```text
E subset U x Verb x U
```

Each edge carries `verb`, `reverse_verb`, `forward_gloss`, `reverse_gloss`, `authority_posture`, `evidence_ref`, and `drilldown_ref`. A one-way id link is not enough. The edge must say what flows from both ends: meaning, authority, freshness risk, mutation risk, population, invalidation, or routing.

## Ontology / Types & Invariants

| Name | Kind | Purpose | Symbol / locus |
|---|---|---|---|
| Artifact kind | set element | Governs a family of rows with one standard/profile contract. | `k in K`, `std_kind_atlas.json` |
| Native band | density level | Compresses the same selected object at a kind-owned depth. | `b in B_k`, `navigation_contract.navigable_bands` |
| Scope | structural unit | Selects what unit is being read: module, section, class, function, component, paragraph. | `s in S_k`, `navigation_contract.navigable_scopes` |
| Facet | aspect/section | Selects the aspect of the unit: gap, intent, body, signature, evidence, tests, aliases. | `f in F_k`, `navigation_contract.navigable_facets` |
| Population mode | authority posture | Says who emits the unit: authored, compiled, live_computed, or unpopulated. | `population_policy` |
| Relation verb | typed edge | Names the flow between units and its reverse read. | `std_navigation_rosetta_grammar.relation_verb_shape` |
| Impact vector | scoring input | Estimates semantic flow, authority flow, freshness risk, mutation risk, and coverage value. | `impact_axis_shape.default_axes` |
| Context packet | selected subset | A budgeted set of rows plus omissions and evidence commands. | `navigation_context_rosetta_packet_v0` |

Invariants:

- **Coverage before depth.** A cold packet should show one cheap row for every relevant kind before upgrading any one kind deeply, unless the budget cannot cover the kind set at all.
- **Native payloads, uniform traversal.** The navigator's verbs are stable, but each kind's standard owns its bands, scopes, facets, source authority, and validation probe.
- **Population honesty.** A declared band does not imply emitted content. `unpopulated` must be visible and should reduce utility.
- **Source authority survives compression.** A compressed row can guide action, but evidence authority remains at the source surface named by the row.
- **Edges are bidirectional reads.** If a relation cannot explain "why from here" from both sides, it is not navigable enough for context compression.
- **Layer depth is earned.** A kind gets more layers only when it has enough internal decision distinctions, authority complexity, or entropy to justify the extra cognitive cost.
- **Relation verbs are operational, not decorative.** A verb that cannot name a downstream control consequence is not strong enough for promotion authority. `evidences` supports belief; `audits` checks readiness, correctness, drift, or promotion posture; if a row cannot separate those consequences, the packet should surface an appeal or ontology-smell state instead of forcing a label.

## Code loci

| Path | Role |
|---|---|
| `codex/standards/std_navigation_rosetta_grammar.json` | Machine standard for nouns, relation verbs, impact axes, math model, layer-depth policy, and proof obligations. |
| `codex/standards/std_navigation_contract.json` | Machine standard for native bands, scopes, facets, population policy, source authority, and edge-neighborhood decay. |
| `codex/standards/std_kind_atlas.json` | Rung-0 standard for artifact-kind rows before query. |
| `system/lib/navigation_context_rosetta.py` | Read-only packet builder that implements coverage-first context compression over the current Kind Atlas and contract audit. |
| `system/lib/kind_band_contract_audit.py` | Current audit surface for declared/profile/drafted/missing navigation contracts. |
| `system/lib/standard_option_surface.py` | Current option-surface adapter for standards and paper modules. |

## Mathematical Core

Let:

```text
K       = artifact kinds visible in the Kind Atlas
U_k     = legal row units for kind k
B_k     = native ordered bands for kind k
P(u)    = population mode of emitted unit u
c(u,b)  = estimated context cost of unit u at band b
I(u,b)  = estimated useful information preserved by u at band b
E       = typed edges among units
x(u,b)  = 1 if packet selects unit u at band b, else 0
C       = context budget
```

The budget constraint is:

```text
sum_{u,b} c(u,b) * x(u,b) <= C
```

The coverage term is:

```text
Coverage(X) = |{ k in K : exists u in U_k, b in B_k with x(u,b)=1 }| / |K|
```

The density term is:

```text
Density(X) = sum_{u,b} x(u,b) * I(u,b) / max(1, c(u,b))
```

For an edge `e`, define a task-specific need score:

```text
Need(e,t) =
  dot(task_weights(t), impact_vector(e))
  * authority_factor(e)
  * freshness_factor(e)
  / max(1, cost(edge_band(e)))
```

The selection objective is lexicographic:

```text
1. maximize Coverage(X)
2. subject to 1, maximize Density(X)
3. subject to 1 and 2, minimize unpopulated or stale authority risk
4. subject to 1-3, prefer packets with clearer omission receipts and evidence commands
```

This is deliberately not "best search result wins." Search optimizes ranked relevance to a guessed query. Rosetta navigation optimizes bounded coverage over declared kinds, then spends remaining budget on high-density rows and high-need edges.

## Layer Depth Rule

Layer depth is a function of distinguishable decisions, not taste. A kind earns another band or scope when the extra layer supports a different safe decision.

```text
depth_needed(k) rises with:
  entropy of valid row choices
  number of legal scopes/facets
  authority/freshness complexity
  mutation risk of acting from compressed rows
  evidence fan-out
  reversible edge-neighborhood complexity

depth_needed(k) falls when:
  the row is transaction-like
  the source unit has few legal actions
  deeper bands would repeat the same decision
  no emitter exists yet
```

This explains the current kinds:

| Kind | Natural layer count | Reason |
|---|---:|---|
| `system_terms` | 6 | Lexical compression genuinely steps from word to phrase to flag to card to context to deep. |
| `paper_modules` | 4+facets | Prose modules need TLDR/card/context/evidence plus authored sections such as Gap and Code loci. |
| `python_scopes` | 5 structural bands | Code compresses through module docs, file cards, symbol capsules, graph context, and source spans, not through prose length. |
| `principles` | 5 | A doctrine row needs identity, statement, operating card, edges, and evidence because action depends on applicability and violation predicates. |
| `raw_seed_shards` | 4 | Voice-derived rows need flag/card/context/deep with evidence, reversal, omission, and next-move facets. |
| `receipts` | often 2 | A transaction proof often needs only summary and detail; adding unused context bands would be profile drift. |

The rule generalizes: more layers are not better. Too few layers forces source rereads; too many layers creates fake structure and stale projections.

## Computer Science Interpretation

Rosetta navigation is a typed graph view-materialization problem under budget:

```text
standards define valid row units
builders/authors/live readers populate units
option surfaces enumerate cheap units
the context packet chooses a coverage floor
the scorer upgrades by density and edge need
the navigator follows drilldown/evidence commands
```

The useful abstractions are:

- **Schema:** standards declare which nouns, bands, scopes, facets, population modes, and edges are legal.
- **Index:** option surfaces expose selectable rows without a query.
- **Adapter:** a kind-specific reader emits the native payload for selected ids.
- **Packet:** a budgeted view carries selected rows, edge neighborhoods, omissions, and evidence commands.
- **Validator:** tests and audits check declaration, population, freshness, and route currentness.

The Rosetta grammar normalizes interfaces, not content. A paper-module card and a Python symbol capsule do not have the same payload. They can still expose the same interface questions: what kind is this, what band is selected, who populated it, what edges matter, what is missing, what proves it, and how do I expand?

## Annex Pressure Refinements

The annex corpus sharpens the Rosetta model in one direction: a packet must select **context atoms**, not vague "things." A context atom is a row/scope/facet/band selection plus source authority, population mode, currentness, confidence, extraction mode, cost, utility, evidence command, and omission receipt. This is the local translation of the RIG pattern: structural injection helps only when each injected object is evidence-backed, stable-id-addressable, and validator-readable.

The selector also needs an explicit policy. PageIndex suggests direct structure-first enumeration before text; GitNexus and DocAgent suggest dependency-ordered traversal when changes or documentation obligations flow through a graph; LATTICE suggests calibrated slates when the candidate surface is too wide for exhaustive reading; RAPTOR suggests beam-style tree traversal when hierarchy matters; GitNexus adds the impact-before-mutation discipline. These are not one search algorithm. They are named selector policies with different admissibility conditions.

Edges likewise need instance-level proof fields, not only a vocabulary of verbs. Sourcegraph/SCIP shows why a protocol spine should bind definitions, references, relationships, and diagnostics without pretending to be a universal search engine. Graphiti shows why temporal validity and invalidation belong on edges. PROCONSUL shows why role-prior edges matter: callee summaries, caller summaries, examples, tests, and architecture notes have different prompt value for different tasks. The Rosetta edge row therefore needs confidence, reason, extraction mode, validity, authority flow, same-graph contract, and bidirectional reads.

The computer-science move is:

```text
kind atlas -> option surface -> selected context atoms -> selector policy -> edge proof rows -> source authority
```

The philosophical move is that compression is no longer a summary written by nowhere. A compressed packet is an accountable act of selection: what was selected, by what policy, at what density, under what authority, with what confidence, and with which omitted alternatives still reachable.

## Philosophical Interpretation

The model treats meaning as relational and attention-bound. A file does not become understandable because the agent can search its words. It becomes understandable when the system exposes the smallest sufficient object of attention, the relations that make it matter, the authority that constrains it, and the omitted context that would change the decision.

Names and verbs are not decorative labels. A noun says what can be selected. A verb says what can flow. A band says what has been compressed away. A facet says which aspect of reality is currently being attended to. A source command says where the compressed account stops being authority.

The ethical rule is that compression must not pretend to know more than it carries. Every packet should preserve currentness, omission, and evidence posture because agents act from these surfaces. A beautiful summary that hides stale source, missing population, or one-way authority is worse than a noisy source file.

## Representative File-Kind Reading

Wave 042 and Wave 044 together give a representative read of the current system kinds:

| Kind | Current contract posture | What the smallest useful row should reveal |
|---|---|---|
| `paper_modules` | declared, option surface supported | subsystem slug, TLDR, status/currentness, facets, dependencies, evidence command |
| `standards` | drafted candidate, option surface supported | governed file type, required contract, schema/validator posture, companion/evidence path |
| `python_files` | declared, projection gap | module purpose, top-level signatures, graph/test context, source span command |
| `python_scopes` | declared, projection gap | symbol id, signature/body boundary, call/test edges, source span command |
| `frontend_views` | drafted candidate, legacy command only | route id, purpose, component tree, interaction state, capture/source command |
| `frontend_components` | drafted candidate, projection gap | component id, props/state/children, view ownership, JSX source |
| `skills` | drafted candidate | triggers, transition contract, workflow, anti-patterns, receipts |
| `system_terms` | declared, legacy command only | lexical ladder, aliases, relationships, evidence commands |
| `principles` | declared, projection gap | identity, statement, applies/violates/tests, edges, evidence refs |
| `axiom_candidates` | drafted candidate | formal clause, dense clause, violation predicates, examples, related principles |
| `raw_seed_shards` | profile declared | voice/claim/context/evidence/reversal/omission/next moves |
| `compression_profiles` | drafted candidate | profile id, native bands, band contracts, source ladder, worker tier policy |
| `annex_patterns` | drafted candidate | upstream provenance, local translation, adoption boundary, source fingerprint |

This matrix is not a completion claim. It is the current map of where the grammar is declared, where the population gap remains, and where future Bridge/OpenRouter/NVIDIA workers could safely receive row jobs.

## Proof Sketch

**Theorem 1: Non-keyword discovery.** If every governed kind has a Kind Atlas row and an option surface at its cheapest declared band, a cold agent can discover every kind and every row in scope without guessing a query. Proof sketch: the Kind Atlas enumerates `K`; the selected kind option surface enumerates `U_k` at minimum cost; drilldown commands carry the next expansion step. No step requires lexical search, although search may remain a shortcut.

**Theorem 2: Coverage-first safety.** Under bounded budget, selecting one cheap row for each relevant kind before deepening any one kind reduces hidden-substrate risk. Proof sketch: without a coverage floor, a high-density row can consume the packet while hiding an entire artifact class. With the floor, omissions are class-visible before depth decisions.

**Theorem 3: Population honesty.** A declared but unpopulated unit must not increase authority. Proof sketch: declaration proves a legal slot exists; population proves content exists; validation proves currentness. Collapsing those states lets a packet cite empty adapters as if they were evidence.

**Theorem 4: Bidirectional edge readability.** A relation is navigable only when both endpoints can explain why the other matters. Proof sketch: navigation decisions are local. If `A governs B` has no reverse gloss from `B` back to `A`, an agent starting at `B` cannot know whether opening `A` is authority, evidence, history, or noise.

**Theorem 5: Layer-depth adequacy.** A kind should have the fewest layers that separate its safe decisions. Proof sketch: if two adjacent layers support the same decision, the deeper layer is redundant cost and likely stale projection. If one layer hides two different decisions, the layer underfits and forces source reread.

## Witness Model: State-Axis Derived-Fact Artifact (Wave 09.44)

The state-axis derived-fact artifact (landed and hardening through 2026-05-02) is the first deployed witness model for the formal contours above. It does not extend the math; it instantiates a concrete case where the predicates can be checked. Implementation paths are evidence, not the model.

```text
F          = derived fact rows over (subject_kind, subject_ref, facet, value, tags, family_id, source posture)
Π(F)       = generated state-axis projection (navigation cache)
s(q)       = axis selector ∈ {tag, facet, value, subject_kind, family, mechanism_ref}
M(q)       = matched fact rows for query q
E(q,B)     = emitted rows under context budget B
O(q,B)     = M(q) \ E(q,B)
κ(axis)    = coverage_posture ∈ {complete, proof_family_partial, unsupported}
```

Invariants witnessed by the current artifact (each binds back to a proof obligation in `std_navigation_rosetta_grammar.json` or to an axiom-candidate `formal_model` clause):

- `|E(q,B)| ≤ |M(q)|` and `|O(q,B)| > 0 → omission_receipt(q,B,|O|)` — `axiom_candidate_context_discretionary_capital`.
- `surfaced(claim) ∧ action_influencing(claim) → has_status_posture(claim)` — `axiom_candidate_status_binding`.
- `κ(axis) = proof_family_partial → covered_fact_families ≠ ∅ ∧ missing_known_source_families ≠ ∅` — `axiom_candidate_evolution_proves_in_microcosm`.
- `κ(axis) = unsupported → route(q) := authoritative_surface (System Atlas / context-pack)` — `axiom_candidate_availability_before_invention`.
- `R(P) inspectable from P or its check surface` and `∀ r ∈ R(P) ∃ l ∈ L: route(r) = l` — `axiom_candidate_cybernetic_projection_feedback`.

Witness loci:

| Path | Role |
|---|---|
| `system/lib/derived_fact_hologram.py` | Producer of F and host of `STATE_AXIS_COVERAGE_OVERRIDES`. |
| `codex/standards/std_derived_fact.json` | Standard governing F, including `coverage_posture_policy` and `result_limit_policy`. |
| `codex/hologram/facts/navigation_cache.json` | Π(F) — the compressed state-axis projection. |
| `tools/meta/factory/build_fact_hologram.py` | `--check` surface that exposes residuals R(P). |
| `system/lib/kernel/commands/navigate.py` | Accessor implementing `s(q)`, `M(q)`, `E(q,B)`, `O(q,B)` semantics via `--facts` / `--facts-tag`. |
| `system/server/tests/test_derived_fact_hologram.py` | Validator showing producer/projection/accessor share grammar G. |

This is a witness model, not the source of the axioms. The implementation paths evidence the predicates; the predicates remain substrate-general and would still hold if the file names, builder, or accessor flags changed. No axiom in `system_axiom_candidates.json` is anchored to this implementation as authority.

## Current state

Shipped:

- The Kind Atlas enumerates 13 artifact kinds before keyword query.
- Paper-module and standard option surfaces exist.
- The navigation contract standard distinguishes band, scope, facet, population mode, source authority, currentness, and edge-neighborhood policy.
- The Rosetta context packet emits representative rows for all 13 kinds and upgrades card rows under a bounded budget.
- The Rosetta grammar standard now names the mathematical model, layer-depth rule, and proof obligations.

Not yet shipped:

- Generic `--row KIND:ID --band BAND`.
- Generic `--telescope KIND:ID --scope S --facet F --band B`.
- Production population jobs for unpopulated bands such as Python `symbol_capsule`.
- Full validators that prove every declared unit has live emitted content.
- A machine-checked Lean formalization. The current proof surface is executable tests plus explicit invariants.

## Deliverables (what this subsystem lets a cold agent DO)

- **Understand the math of compression navigation** without reverse-engineering `navigation_context_rosetta.py`.
- **Explain why some kinds have fewer or more layers** using layer-depth adequacy rather than taste.
- **Read verbs and nouns as standardized grammar tokens** with write/read shapes and impact axes.
- **Distinguish coverage, density, population, authority, and currentness** before trusting a packet.
- **Use the current Rosetta packet as a test fixture** for future telescope and population adapters.
- **Challenge fake navigation support** when a kind is declared but unpopulated or unsupported by an adapter.

## Gap (what Will is signaling)

Will is signaling that the system needs an actual Rosetta stone for navigation: a compressed grammar that lets agents move from artifact kinds to rows to selected shards without keyword guessing. The math should not be sterile. It should bind mathematics, computer science, and philosophy: finite context budgets, typed graph selection, standard-owned schemas, attention as a moral resource, and compression as a promise with omissions.

The next missing operation is still selective telescope. This module proves the grammar that telescope should obey; it does not implement the production telescope command.

## What a cold agent should NOT re-derive

- Do not re-collapse band, scope, and facet into one field.
- Do not assume every artifact kind deserves the same band names or the same number of layers.
- Do not trust a declared band unless population mode and validation posture are visible.
- Do not treat a relation verb as authority unless its authority flow says authority moves.
- Do not confuse source evidence with active doctrine, generated projections, or historical receipts.
- Do not spend context on deep rows before the relevant kind set is visible.

## Refresh contract

Refresh this module when:

- `std_navigation_rosetta_grammar.json` changes math model, token shapes, impact axes, layer-depth policy, or proof obligations.
- `std_navigation_contract.json` changes band/scope/facet/population or edge-neighborhood rules.
- `system/lib/navigation_context_rosetta.py` changes selection objective, cost model, utility model, or representative fixtures.
- A generic telescope command lands.
- A population worker starts emitting previously unpopulated bands for Python, frontend, principles, raw seed, or annex patterns.
- A proof-assistant or formal verification surface replaces the current proof-sketch-plus-tests posture.
