"""
[PURPOSE]
- Teleology: Name finance forecast generator variants so historical replay and future optimizers compare stable variants instead of anonymous calculator configs.
- Mechanism: Exposes a small source-owned registry payload; downstream tools may copy the data into replay ledgers but may not mutate calculator weights or live probability mappings from this file alone.
- Hardening: Keeps optimizer permission false until evaluator receipts prove leakage-safe historical replay and shadow calibration gates.
[INTERFACE]
- Exports: `REGISTRY`, `load_registry()`, `resolve_variant()`,
  `assert_variant_known()`, `mutation_gate_for()`, and `registry_payload()`.
- Schema: `finance_generator_variant_registry_v0`.
[CONSTRAINTS]
- This is source authority, not a generated projection.
- No optimizer or probability mutation is admitted by this registry without external replay receipts.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


DATA_SCHEMA_VERSION = "finance_generator_variant_registry_v0"
REGISTRY_REF = "tools/finance/variant_registry.py"
BASELINE_VARIANT_ID = "calculator:calculator.6:default"
SHADOW_TEST_VARIANT_ID = "calculator:calculator.6:shadow_test"
SHADOW_ALT_VARIANT_ID = "calculator:calculator.6:shadow_alt"
SHADOW_PROB_SHRINK_VARIANT_ID = "calculator:calculator.6:shadow_prob_shrink"

REGISTRY: Dict[str, Any] = {
    "schema_version": DATA_SCHEMA_VERSION,
    "status": "active",
    "baseline_variant_id": BASELINE_VARIANT_ID,
    "registry_ref": REGISTRY_REF,
    "purpose": (
        "Versioned registry for finance forecast generator variants so historical "
        "replay and future optimizers compare named variants rather than "
        "anonymous calculator configs."
    ),
    "variants": [
        {
            "generator_variant_id": BASELINE_VARIANT_ID,
            "calculator_schema": "calculator.6",
            "forecast_card_schema": "forecast_claim_card_v0",
            "admission_schema": "finance_forecast_claim_v1",
            "calibrator_id": None,
            "status": "baseline",
            "variant_family": "baseline",
            "evidence_role": "production_baseline_reference",
            "optimizer_permission": False,
            "calculator_mutation_permission": False,
            "mutation_gate": {
                "requires_variant_admission_receipt": True,
                "optimizer_permission": False,
                "calculator_mutation_permission": False,
                "reason": "baseline_variant_not_a_mutation_candidate",
            },
        },
        {
            "generator_variant_id": SHADOW_TEST_VARIANT_ID,
            "calculator_schema": "calculator.6",
            "forecast_card_schema": "forecast_claim_card_v0",
            "admission_schema": "finance_forecast_claim_v1",
            "calibrator_id": None,
            "status": "shadow",
            "variant_family": "geometry",
            "evidence_role": "covariance_aware_geometry_shadow",
            "optimizer_permission": False,
            "calculator_mutation_permission": False,
            "mutation_gate": {
                "requires_variant_admission_receipt": True,
                "optimizer_permission": False,
                "calculator_mutation_permission": False,
                "reason": "shadow_variants_require_variant_admission_gate_before_mutation",
            },
        },
        {
            "generator_variant_id": SHADOW_ALT_VARIANT_ID,
            "calculator_schema": "calculator.6",
            "forecast_card_schema": "forecast_claim_card_v0",
            "admission_schema": "finance_forecast_claim_v1",
            "calibrator_id": None,
            "status": "shadow",
            "variant_family": "selection",
            "evidence_role": "selection_ablation_shadow",
            "optimizer_permission": False,
            "calculator_mutation_permission": False,
            "mutation_gate": {
                "requires_variant_admission_receipt": True,
                "optimizer_permission": False,
                "calculator_mutation_permission": False,
                "reason": "shadow_variants_require_family_model_selection_gate_before_mutation",
            },
        },
        {
            "generator_variant_id": SHADOW_PROB_SHRINK_VARIANT_ID,
            "calculator_schema": "calculator.6",
            "forecast_card_schema": "forecast_claim_card_v0",
            "admission_schema": "finance_forecast_claim_v1",
            "calibrator_id": None,
            "status": "shadow",
            "variant_family": "probability_map",
            "evidence_role": "calibration_prior_benchmark",
            "calibration_policy": {
                "kind": "fixed_probability_shrink_toward_0_5",
                "shrink_factor": 0.7,
                "fitted": False,
                "common_support_preserving": True,
                "live_calibrator": False,
            },
            "optimizer_permission": False,
            "calculator_mutation_permission": False,
            "mutation_gate": {
                "requires_variant_admission_receipt": True,
                "optimizer_permission": False,
                "calculator_mutation_permission": False,
                "reason": "shadow_variants_require_family_model_selection_gate_before_mutation",
            },
            "predeclared_design_note": "Fixed-factor probability shrinkage toward 0.5 (shrink = 0.7, applied to (p-0.5) for non-abstain cards). Preserves event contracts, members, horizon, benchmark, and selected group set so the variant forms a clean common-support family with baseline and shadow_test. NOT a fitted calibrator; the shrink factor is predeclared.",
        }
    ],
    "mutation_gate": {
        "rule": (
            "New variants may be compared by finance_historical_replay, but no "
            "calculator weight, prompt, or live probability mapping mutation is "
            "permitted without a historical replay receipt and shadow calibration gate."
        ),
        "required_receipts": [
            "finance_eval_experiment_ledger_v0",
            "finance_probability_calibrator_v0 when probability mapping changes",
        ],
    },
}


def load_registry() -> Dict[str, Any]:
    return deepcopy(REGISTRY)


def variant_rows() -> List[Dict[str, Any]]:
    return list(load_registry().get("variants", []))


def resolve_variant(variant_id: str) -> Optional[Dict[str, Any]]:
    for row in variant_rows():
        if row.get("generator_variant_id") == variant_id:
            return row
    return None


def assert_variant_known(variant_id: str) -> Dict[str, Any]:
    row = resolve_variant(variant_id)
    if row is None:
        raise KeyError(f"not_admissible_unknown_variant:{variant_id}")
    return row


def mutation_gate_for(variant_id: str) -> Dict[str, Any]:
    row = assert_variant_known(variant_id)
    gate = dict(row.get("mutation_gate") or {})
    gate.setdefault("requires_variant_admission_receipt", True)
    gate.setdefault("optimizer_permission", False)
    gate.setdefault("calculator_mutation_permission", False)
    gate["generator_variant_id"] = variant_id
    gate["variant_status"] = row.get("status", "unknown")
    gate["variant_registry_ref"] = REGISTRY_REF
    return gate


def registry_payload() -> Dict[str, Any]:
    return load_registry()
