# Doctrine Population Loop

Projection class: subsystem
Depends on: raw_seed_metabolism, raw_seed_shard_assimilation, local_to_general_propagation
Authored: 2026-05-11
Governing principles: `pri_014`, `pri_016`, `pri_088`, `pri_111`, `pri_115`, `pri_125`, `pri_152`
Governing concepts: `con_002`, `con_017`, `con_024`, `con_030`, `con_038`
Governing mechanisms: `mech_005`, `mech_016`, `mech_017`, `mech_019`, `mech_028`
Primary subdomain: doctrine_authoring
Search aliases: doctrine population, doctrine derivation, raw seed to doctrine, concepts mechanisms principles paper modules, autonomous seed doctrine, self uppropagate doctrine
Related operator surface: `cogop_operator_accretion_governor`
Compression atom: Doctrine plane selector
Compression keys: doctrine population, plane selection, doctrine operator boundary, crystallization gate, split before package, raw seed evidence, principle, concept, mechanism, paper module, skill, cap, local to general propagation
Compression flag: Route raw-seed pressure to the smallest doctrine plane; apply `pri_152` before packaging; hand reusable thinking-mode pressure to `cogop_operator_accretion_governor`.
Open when: A broad doctrine request asks to populate concepts, mechanisms, principles, paper modules, or skills; an autonomous-seed prompt asks for a durable new thought; or evidence is ambiguous between cap, principle, concept, mechanism, paper module, skill, or standard.
Do not open when: The target plane is already selected and a narrower curator skill owns the mutation, or the task is only raw-seed distillation with no durable doctrine change.
Safe drilldown: ./repo-python kernel.py --option-surface paper_modules --band card --ids doctrine_population_loop

## TLDR (compressed view)

The doctrine population loop is the governed route from raw-seed pressure into principles, concepts, mechanisms, paper modules, skills, standards, and closeout propagation. It is not a permission slip to hand-edit doctrine nodes or rewrite raw seed; it is a lane selector that starts from a bounded evidence packet, classifies the pressure shape, mutates only through the owning curator or apply lane, refreshes discoverability, and deposits the reusable lesson back into the general substrate. The entry skill is `doctrine_derivation` and the published agent surface is `doctrine-population`; the operational core is raw-seed shard retrieval, alchemy planning, apply-gated doctrine mutation, and paper-module or skill follow-through when the cold-agent gap is actually discoverability. The correct default for concept/mechanism/principle population is refine-existing first, mint-new only after the nearest nodes and routes have been checked. A pass is closed only when the changed source artifacts validate, generated projections are refreshed, and the local-to-general propagation question has been answered.

## Intent

Will's recurring pressure is not merely "add more rows." The pressure is that the system should be able to improve its own concepts, mechanisms, principles, and paper modules from raw seed without each agent rediscovering the population route from scratch. This module makes that loop cold-readable.

The skill `doctrine_derivation` already carries the runnable workflow. This paper module names the subsystem shape around it: what counts as evidence, which artifact class owns each mutation, where controller gates begin, and when the right answer is a paper module or skill route rather than a new doctrine node.

## Shape

```text
operator / raw-seed pressure
  -> kernel entry + context pack
  -> bounded evidence packet
       shard group | orphan cluster | candidate card | explicit par_* / atom_* set
  -> classify target shape
       voice atomization | principle | concept | mechanism | paper module | skill | standard
  -> use owning lane
       raw_seed_pipeline | raw_seed_apply_loop | curation skill | paper_module_authoring | skill_authoring
  -> refresh projections
       paper module index | skill catalog | doctrine/routing/bootstrap sidecars as needed
  -> close through local-to-general propagation
       refine an upstream artifact or record nothing_to_refine
```

The loop has two boundaries:

| Boundary | Rule |
|---|---|
| Voice boundary | `raw_seed.md` is not edited by agents. Operator voice is captured through raw-seed lanes; agent synthesis belongs in agent seed or authored doctrine surfaces with attribution. |
| Mutation boundary | `pri_*`, `con_*`, and `mech_*` rows mutate through their standards, curation skills, and apply lanes. Markdown prose can explain the loop, but it does not smuggle doctrine-node edits around the graph. |

## Ontology / Types & Invariants

| Name | Kind | One-line purpose | Symbol id or file |
|---|---|---|---|
| Doctrine population pass | operation | One bounded movement from evidence packet to durable doctrine/source artifact plus refreshed projections | `doctrine_derivation` |
| Evidence packet | packet | The smallest source set sufficient to classify the pressure without treating all raw seed as scope | `shard_batch_packet`, `idea_group_id`, `par_*`, `atom_*` |
| Population target | classification | Artifact class selected by pressure shape: voice, principle, concept, mechanism, paper module, skill, or standard | Population Targets table in `doctrine_derivation` |
| Doctrine triple | review bundle | Alchemy slot plan for principle/concept/mechanism population before controller apply | `raw_seed_alchemy_review.json` |
| Apply gate | controller boundary | The lane that turns reviewed raw-seed evidence into doctrine-node mutation | `raw_seed_apply_loop.py` |
| Paper-module follow-through | discoverability repair | Authored/refreshed module when the real gap is that agents keep re-deriving a subsystem | `paper_module_authoring` |
| Skill route follow-through | capability repair | Registry/frontmatter/projection refinement when the right lane was hard to find | `skill_authoring` or `doctrine_derivation` |
| Doctrine/operator boundary | handoff | The test that a "durable new thought" is doctrine content rather than a reusable thinking operator | `cogop_operator_accretion_governor` |
| Local-to-general closeout | propagation reflex | The final check that the reusable lesson landed upstream or explicitly had nothing to refine | `local_to_general_propagation` |
| Crystallization gate | selection discipline | The pre-authoring test that a proposed doctrine object reduces future cognitive work, has bounded evidence, and belongs on the smallest correct authority plane | `doctrine_derivation` |
| Plane-selection ambiguity | signal | Evidence that could honestly become more than one artifact kind, requiring classification before authoring | `par_phase_09_raw_seed__cleaned_restatement_010`, `con_038` |
| Split-before-package gate | invariant | If candidate ideas generalize differently, split them before choosing names, planes, or mutation lanes | `pri_152`, `par_phase_09_raw_seed__cleaned_restatement_011` |

Named invariants:

- Bound evidence before authoring. "Read all raw seed" is not a population unit.
- Classify before mutating. Principle-shaped, concept-shaped, mechanism-shaped, and paper-module-shaped pressure have different owners.
- Plane ambiguity is a signal, not a blocker. If an idea looks like a cap, principle, concept, mechanism, paper module, skill, or standard, name the uncertainty and run the crystallization gate.
- Doctrine/operator boundary. If the missing intelligence is a reusable thinking move with activation, receipt, validation, and task-selection semantics, route to `cognitive_operators` and run `cogop_operator_accretion_governor` before authoring another operator row.
- Split before packaging (`pri_152`). If two candidate ideas generalize differently, separate them before naming the artifact or selecting the owning lane.
- Existing doctrine nodes win the first comparison. New rows require evidence that the nearest row cannot honestly absorb the pressure.
- Apply gates are not optional for doctrine nodes. Paper modules and skills can be edited as source artifacts; generated projections cannot.
- Discoverability is part of the deliverable. A row or module that cannot be found from the operator phrase has not really joined the system.
- Closeout is part of the loop. The pass either refines a general artifact or records `nothing_to_refine`.

## Code loci

| Role | Loci | What it owns |
|---|---|---|
| Entry skill and published surface | `codex/doctrine/skills/doctrine/doctrine_derivation.md`, `.agents/skills/doctrine-population/SKILL.md` | The runnable capability and external agent-skill entry for broad doctrine population requests |
| Bounded shard and alchemy lanes | `tools/meta/factory/raw_seed_pipeline.py`, `tools/meta/factory/raw_seed_apply_loop.py` | Backlog-safe planning, alchemy review bundles, and controller-gated doctrine apply |
| Raw-seed and family authority | `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/family_charter.json`, `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.json`, `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json` | Operator-voice substrate, family charter, and principle authority that population must preserve |
| Curator skills and standards | `codex/doctrine/skills/doctrine/principles_curation.md`, `codex/doctrine/skills/doctrine/concept_mechanism_curation.md`, `codex/doctrine/skills/doctrine/paper_module_authoring.md`, `codex/standards/principles/std_raw_seed_principles.json`, `codex/standards/principles/std_concept.json`, `codex/standards/principles/std_mechanism.json`, `codex/standards/std_paper_module.json` | Artifact-specific mutation rules for principles, concepts, mechanisms, and paper modules |
| Discoverability projections | `codex/doctrine/skills/skill_registry.json`, `tools/meta/factory/build_skill_catalog_projection.py`, `tools/meta/factory/build_paper_module_index.py`, `codex/doctrine/paper_modules/_index.json`, `codex/doctrine/paper_modules/_validation_report.json` | Registry, generated skill surfaces, paper-module lookup, and validation queues |
| Propagation roof | `codex/doctrine/skills/doctrine/local_to_general_propagation.md`, `codex/doctrine/paper_modules/local_to_general_propagation.md` | Closeout deposit discipline and "self-uppropagate" macro |

## Current state

Snapshot: 2026-05-11.

**Shipped:**

- `doctrine_derivation` is the source skill for broad doctrine population and has a generated `doctrine-population` agent-skill surface.
- This module is now the paper-module roof for that skill: it names the loop boundary, owning lanes, projection refreshes, and propagation closeout in one cold-readable place.
- The loop now names a crystallization gate for "autonomous seed doctrine authorship" prompts: choose a principle/concept/mechanism/paper module/skill/cap only after proving the object eliminates future rediscovery and fits the smallest correct authority plane.
- The option-surface compression fields now expose this module as the doctrine plane selector before agents open the full markdown.
- The loop now treats split-before-package as a principle-backed invariant (`pri_152`): one raw paragraph can carry multiple candidate doctrine objects when those ideas generalize differently.
- The generated `doctrine-population` skill facade now inherits split-before-package language from `skill_registry.json`, so the executable route says the same thing as the paper roof.
- `shard_cluster_assimilation` is the bounded shard-to-doctrine lift skill for alchemy-plan / alchemy-run / apply-alchemy work.
- Raw-seed metabolism already separates backlog-safe planning from controller-gated mutation.
- Principle, concept, mechanism, and paper-module curator skills exist and point at their governing standards.
- Kernel entry/context-pack routes now find the doctrine-population lane from phrases like "concepts mechanisms principles paper modules" and "autonomous seed doctrine population."
- The doctrine/operator boundary is explicit: broad "durable new thought" prompts stay in this lane only when the missing object is doctrine; reusable thinking-mode pressure routes to the cognitive-operator plane and its accretion governor.

**In progress / partial:**

- Doctrine-node population remains mostly manual/controller-gated. That is intentional, but it means the most reliable near-term improvement is better selection, routing, evidence packets, and follow-through surfaces.
- Concept/mechanism/principle rows are queryable, but their population debt is uneven; not every candidate pressure deserves a new row.
- Paper-module freshness diagnostics still surface non-blocking debt elsewhere in the plane. A population pass should treat that as scoped context, not as permission to widen the wave indefinitely.

**Missing / NOT YET BUILT:**

- No global validator can prove every doctrine population pass refreshed all affected projections.
- No single UI pane shows "raw-seed pressure -> target classification -> owning lane -> projection refresh -> propagation closeout."
- No automatic promotion decides when a recurring operator phrase becomes a new principle/concept/mechanism; candidates still require the curator/apply disciplines.

## Deliverables (what this subsystem lets a cold agent DO)

- **Select the right doctrine population lane** via `./repo-python kernel.py --entry "<task>" --context-budget 12000` and the `doctrine_derivation` card.
- **Bound raw-seed evidence** through shard groups, alchemy plans, explicit `par_*` / `atom_*` handles, or candidate cards before opening broad substrate.
- **Classify target shape** so durable commitments route to `principles_curation`, abstract patterns to `concept_mechanism_curation`, operational/code patterns to mechanism apply lanes, and recurring rediscovery to `paper_module_authoring`.
- **Resolve plane ambiguity** by applying `pri_152`: split divergent ideas before packaging and select the smallest honest authority plane for each one.
- **Route thinking-mode pressure out of doctrine** by opening `cogop_operator_accretion_governor` when the missing intelligence is an operator with activation, receipts, validation, and task-selection hooks.
- **Run alchemy follow-through** from a shard group into a review bundle, then apply only after the dry-run shows coherent slots and nearest-node checks.
- **Repair discoverability** by updating skill registry rows, generated agent-skill surfaces, paper-module indexes, and bootstrap/routing projections when the population route itself changed.
- **Close the loop** by invoking local-to-general propagation and naming the refined artifact or `nothing_to_refine`.

## Gap (what Will is signaling)

Will's current request says to better populate "concepts mechanisms principles paper modules," grants broad authority, asks for a skill, and names "self-uppropagate" / "autonomous seed." The durable signal is not "invent doctrine freely"; it is "make the system's own population route strong enough that agents can author from raw seed with common sense and without losing the governance lanes."

That matches existing raw-seed doctrine: `pri_014` says principles carry a curation discipline; `pri_016` says extraction must never replace raw seed; `pri_088` says each compression layer rereads its substrate; `pri_111` says paper modules preempt re-derivation; `pri_115` says principles should reactivate cognition in context; and `pri_125` says low-cost enabling substrate work should take priority because it multiplies downstream work. The local-to-general raw-seed anchors also name the closing move: local use should improve the generalized skill or artifact rather than dying in the session.

The gap this module closes is that the skill existed as an operation but the paper-module roof did not. A future cold agent could find `doctrine-population`, but it still had to infer the subsystem boundaries across raw-seed metabolism, alchemy, curator skills, paper-module authoring, and propagation. This module is the map for that loop.

A second, smaller gap surfaced while dogfooding the operator's "autonomous seed doctrine authorship" prompt: the words "autonomous seed" and "dogfood" were strong enough to pull entry toward navigation repair even when the durable intent was doctrine population. The crystallization gate is the repair: broad seed language must first ask what intelligence is missing, what future cognitive work the object removes, and which authority plane owns it. Navigation repair remains valid when the object is route behavior; doctrine population owns the prompt when the object is raw-seed-grounded doctrine authorship.

The newest raw-seed pressure sharpened the same gap instead of creating a separate lore object: `par_phase_09_raw_seed__cleaned_restatement_010` shows the operator deciding whether an object is a cap, principle, or imagination surface, while `par_phase_09_raw_seed__cleaned_restatement_011` warns not to package two differently generalizing ideas as one. The repair is now held by `pri_152` and belongs here as a plane-selection and split-before-package discipline, then routes out to the relevant curator only after classification.

The next repeated-seed pressure exposed a neighboring boundary rather than another doctrine node: the system already has `cognitive_operators` with dogfood receipts and a validator, including `cogop_operator_accretion_governor`. The live decision is therefore merge/extend, not mint-new: this doctrine lane now names when a "durable new thought" is actually a reusable thinking operator, and hands it to the operator plane before doctrine population creates concepts, mechanisms, principles, or paper modules.

## What a cold agent should NOT re-derive

- Do not re-derive the artifact-class table. Use `doctrine_derivation` to classify pressure into distillation, principle, concept, mechanism, paper module, skill, standard, or propagation.
- Do not treat "maybe cap, maybe principle, maybe concept/mechanism/skill" as indecision. It is the signal to run the crystallization gate.
- Do not package two ideas together just because they appear in one raw paragraph; `pri_152` requires splitting and routing them separately when they generalize differently.
- Do not treat broad authority as license to bypass raw-seed provenance, nearest-node checks, or apply gates.
- Do not hand-edit `raw_seed.md`, generated regions, or doctrine-node JSON when the owning lane is an apply loop.
- Do not mint new concepts or mechanisms before checking `con_002`, `con_017`, `con_024`, `con_030`, `mech_016`, `mech_017`, `mech_019`, and `mech_028` for absorbable overlap.
- Do not bury reusable thinking-mode work in doctrine nodes. If the object needs activation triggers, dogfood receipts, validation fields, and task-selection hooks, open `cognitive_operators` and the accretion governor.
- Do not stop at a concept/mechanism/principle triple when the actual user pain is that future agents cannot find the route or paper-module explanation.
- Do not leave the pass consume-only. If the local situation taught a reusable rule, refine the owner; otherwise record `nothing_to_refine`.
- Do not let "autonomous seed" or "dogfood" wording override the doctrine plane when the requested object is a grounded doctrine crystallization rather than a navigation-control repair.

## Refresh contract

Refresh when:

- `doctrine_derivation`, `shard_cluster_assimilation`, `principles_curation`, `concept_mechanism_curation`, `paper_module_authoring`, or `local_to_general_propagation` changes its workflow, triggers, target table, or closeout rule.
- `raw_seed_pipeline.py` adds or removes population subcommands, especially alchemy, contextual-compression, or candidate-selection commands.
- `raw_seed_apply_loop.py` changes doctrine-node apply semantics, edge validation, or dry-run/commit behavior.
- `std_raw_seed_principles.json`, `std_concept.json`, `std_mechanism.json`, or `std_paper_module.json` changes the required evidence, edge, or validation contract.
- A new concept/mechanism/principle/paper-module population surface ships and should become part of the loop.
- Cognitive-operator standards or the accretion governor change the handoff rule for reusable thinking-mode pressure.
- Kernel entry/context-pack no longer selects `doctrine_derivation` for broad "populate concepts mechanisms principles paper modules" phrasing.

Stale signals:

- This module cites a path that no longer resolves.
- A generated `doctrine-population` skill surface exists but no longer points back to `doctrine_derivation`.
- A doctrine population pass changes source artifacts but skips the relevant projection builder or check.
- Operators keep repeating the population request because future agents still cannot find the lane from the phrase.
