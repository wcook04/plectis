# Anti-Principles

These are the failure modes Microcosm is built to catch. Each row names the
axioms the failure breaks. A row describes a mistake to look for, and its
authority comes entirely from those axioms.

| ID | Violated axioms | Rejected failure shape |
| --- | --- | --- |
| AP-1 Fixture-label echo | AX-1, AX-12 | Repeating a fixture verdict, registry label, markdown claim or model answer without recomputing it from the lower-level evidence. |
| AP-2 Producer trust | AX-2, AX-3 | Trusting a producer, persona, route, credential or past success where a checker, proof, policy or checked capability should decide. |
| AP-3 Rank-as-product-score | AX-5, AX-12 | Reading counts, handles, passing validators or evidence classes as a measure of product maturity, release readiness or whole-system correctness. |
| AP-4 Cache-across-drift | AX-4, AX-10 | Reusing a cached result looked up by name, path, route, display label or producer after the content it was computed from has changed. |
| AP-5 Unknown-unknown exhaustiveness | AX-6 | Reading missing evidence as evidence of absence outside a declared domain in which every case was checked. |
| AP-6 Inadmissible number emission | AX-7 | Returning a number or conclusion from a computation whose preconditions failed, where a typed refusal was required. |
| AP-7 Public/private membrane breach | AX-8 | Letting untrusted, private, provider, prompt, credential or raw-voice material reach a privileged or public destination without an origin label and a sanitizing transform. |
| AP-8 Blind irreversible mutation | AX-9 | Making an irreversible change without an undo step, a rollback record, a compare-and-swap or world-version guard, or an explicit declaration that it cannot be undone. |
| AP-9 Frozen live fact | AX-10 | Writing a live fact into prose without its `as_of` date, the inputs it came from and a way to recompute it. |
| AP-10 Prose-as-executable-authority | AX-11 | Giving doctrine prose the authority of an executable rule before it passes the grammar and lists the result records it must produce. |
| AP-11 Meta-artifact exemption | AX-12 | Exempting Microcosm's own result records, docs, releases, generated pages or validators from the evidence checks Microcosm applies to everything else. |
| AP-12 Synthetic substrate substitution | AX-1, AX-4, AX-8 | Using synthetic fixtures in place of real material that is available and safe to publish. |
| AP-13 Generated-receipt source inversion | AX-4, AX-11 | Treating generated result records as if a person had written them as source. |
| AP-14 Public-authority inflation | AX-5, AX-8, AX-12 | Letting public docs imply a hosted service, access to an external service, changes to source files, financial or trading decisions, production readiness, an affiliation or endorsement, or equivalence with the private system, when no valid witness supports it. |
| AP-15 Mechanism theater | AX-1, AX-2, AX-12 | Using field terms such as proof, verifier, information flow, world model or benchmark integrity for a public mechanism that only checks the shape of a result record or generated page. |
| AP-16 Receiver inflation | AX-8, AX-12 | Displaying a declared, inferred or generated downstream target as an effect observed at runtime, with no evidence that the effect happened. |
| AP-17 Projection-as-source | AX-4, AX-11 | Letting a markdown page, generated card, atlas row or short result summary override the executable contract it summarizes. |
