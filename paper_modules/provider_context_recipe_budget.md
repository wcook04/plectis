# Pack context sections within a byte budget

> **In plain terms.** An assistant program can take in only so much text at once, so what it is given must be chosen to fit. This component is given ordered recipes listing sections of material, each with its text or a stated size, and a size limit. It goes down each list adding a section only if it fits in the space left, and skips any that do not. The result lists included and left-out sections with sizes but not text, so a reader can see what was dropped. One small decision step, whether a section fits, is checked by a mathematical proof against written rules, but the rest is outside that proof, and no real model is called.

This validator takes ordered context recipes and section material, measures available section bodies, falling back to a declared byte size when a body is unavailable, and includes each section if it fits the remaining byte budget. Its result lists included and omitted sections with sizes, while redacting their bodies. The token count is a rough estimate of one token per four bytes.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.provider_context_recipe_budget_policy run-budget-bundle \
  --input examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle \
  --out .microcosm/component-guides/provider_context_recipe_budget_policy
```

Inspect `.microcosm/component-guides/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle_validation_result.json` for the result and findings.

The recipes fill sections in the declared order, skipping a section that does not fit. The omission list lets a reader see what was left out; it is not a transcript of material sent to a model.

## What the result means

A recipe that suppresses its omitted-sections manifest or permits proof bodies is rejected. This checks recipe accounting and policy, not a provider call or model performance.

Related reading: [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401), [Command Line Interface Guidelines](https://clig.dev/).

## Verification

The [Dafny-verified packing core](../formal/components/budget_packing/README.md) used by this projection includes each nonnegative-sized section exactly when it fits after earlier inclusions. It proves the included total stays within a nonnegative budget, including across batches. Python measures and normalizes the sizes and assembles the batches; those steps and any provider behavior remain outside the proof.

The direct command above calls the packing core. Separately, `make component-replays` applies the [shared admission check](../formal/replay/README.md) to observed replay identities and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/provider_context_recipe_budget_policy.py) · [input](../examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle) · [tests](../tests/test_provider_context_recipe_budget_policy.py) · [historical sample result](../receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle_validation_result.json) · [component record](../core/paper_module_capsules.json).
