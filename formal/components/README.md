# Verified component computations

Twelve reference-component computations have Dafny specifications and executable
implementations. Their generated Python is called by the corresponding component
path through `plectis.components`. Each guide states the input model, the
property proved, the production hook and the boundary of the claim.

| Computation | Proved property | Component use |
|---|---|---|
| [Budget packing](budget_packing/README.md) | Ordered inclusion fits the remaining byte budget. | Provider context recipes |
| [Dependency reachability](dependency_reachability/README.md) | Exactly the dependents reachable by a nonempty path. | Batch 5 impact exercise |
| [Egress policy](egress_policy/README.md) | Literal phrase matches and tripwire decisions follow the stated edge rules. | Response-text gate |
| [Evidence diff](evidence_diff/README.md) | IDs are partitioned into shared, extra and missing, retaining last occurrences. | Batch 8 evidence comparison |
| [Information flow](information_flow/README.md) | Policy verdicts and finite taint reachability follow their specified rules. | Prompt-injection replay |
| [MCP authority](mcp_authority/README.md) | Required call citations, write authority references and the positive-call batch decision follow the metadata policy. | MCP tool-call replay |
| [Navigation metrics](navigation_metrics/README.md) | Matching counts and decision precedence follow the packet rules. | Route-packet scoring |
| [Ownership classification](ownership_classification/README.md) | Every matching live claim protects its generated path, regardless of claim order. | Concurrent-work classification |
| [Premise ranking](premise_ranking/README.md) | Eligible candidates have the specified scores and ordering. | Formal-math premise retrieval |
| [Sandbox policy](sandbox_policy/README.md) | Six recognized action shapes receive their rules; other shapes fail closed. | Sandbox policy replay |
| [Tactic selection](tactic_selection/README.md) | The first eligible preference or candidate is selected. | Target-shape routing |
| [Walkthrough validation](walkthrough_validation/README.md) | The declared positive budget is at most ten minutes and step and reference counts meet the density rule. | Public reveal walkthrough |

The path from a claim to evidence has distinct stages. A component guide names
its claim and inputs; the linked Dafny source states the specification and
proves its executable computation against it. A Python adapter supplies
normalized observations to generated code, and the component records its
result in a receipt. The separate [replay admission core](../replay/README.md)
checks captured identities, coverage and receipt observations across a run.
Admission does not prove the component algorithm; the component theorem does
not authenticate its inputs or receipt. The 88-component catalogue includes
other computations that do not have one of these proofs.

From the repository root, check saved bindings with `make check`. To re-run the
component proofs, regenerate their Python and check the source-linked mutants,
install Dafny 4.11.0 and run:

```sh
make verify-components DAFNY=/absolute/path/to/dafny
```

The [formal overview](../README.md) describes trusted tools and the separate
workflow proofs. The [validation runbook](../../docs/maintainers/validation.md)
describes fresh replays, package checks and native prerequisites.
