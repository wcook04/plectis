# Provider Context Recipe Budget

`provider_context_recipe_budget_policy` is the public Microcosm organ for
turning retrieved proof-support metadata into bounded provider context recipes.

It validates six public recipe shapes: `minimal_4kb`, `premise_16kb`,
`skill_32kb`, `repair_32kb`, `fewshot_64kb`, and
`strategy_classification_4kb`. Each recipe has a fixed byte ceiling, ordered
section fill, a graph role, a reducer deliverable type, and an omitted-sections
manifest when a section cannot fit.

## Authority Boundary

This organ does not call providers, run Lean or Lake, prove a theorem, expose a
proof body, or reveal oracle-only truth-side material. Its output is context
metadata: which sections would be admitted, which sections were omitted, which
deliverable route is allowed, and which authority claims remain false.

The `strategy_classification_4kb` route emits only
`strategy_id_classification`. It is not a proof-body route and cannot carry a
provider answer body.

## Runtime Surfaces

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.provider_context_recipe_budget_policy run --input fixtures/first_wave/provider_context_recipe_budget_policy/input --out receipts/first_wave/provider_context_recipe_budget_policy
PYTHONPATH=src python3 -m microcosm_core.cli provider-context-recipe-budget-policy run-budget-bundle --input examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle --out receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy
```

## Negative Cases

- `budget_overflow_recipe` rejects recipes above the public byte ceiling.
- `truth_side_section` rejects oracle-only section ids.
- `proof_body_leakage` rejects proof and provider body fields.
- `provider_call_authorized` rejects any public fixture that authorizes a provider call.
- `deliverable_type_route_mismatch` rejects a recipe whose reducer output type changed.
- `omitted_sections_suppressed` rejects over-budget context without an omitted-sections manifest.

## Why It Matters

Microcosm needs provider context to look like a small operating substrate, not a
prompt dump. This organ makes the context boundary inspectable: a cold reader
can see the exact byte ceilings, section order, omitted material, and deliverable
routes before any provider or proof authority is even in scope.
