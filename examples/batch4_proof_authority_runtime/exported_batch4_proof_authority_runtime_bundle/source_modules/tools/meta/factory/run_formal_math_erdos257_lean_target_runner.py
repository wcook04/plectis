#!/usr/bin/env python3
"""Run an exact Lean target check for the Erdos257 period-noncollapse project."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import run_formal_math_erdos257_period_noncollapse_strike as strike


SCHEMA_VERSION = "formal_math_erdos257_lean_target_runner_receipt_v1"
CHECK_SCHEMA_VERSION = "formal_math_erdos257_lean_target_runner_check_v0"
OWNER_ID = "formal_math_erdos257_lean_target_runner"
DEFAULT_TIMEOUT_SECONDS = 400
CLAIM_BOUNDARY = (
    "named_lean_target_typecheck_and_axiom_audit_including_unconditional_finite_theorem_rat_den_bridge_infinite_support_instances_full_support_lambert_bridge_divisor_block_certificate_interface_weighted_consumer_first_block_progression_middle_window_average_selection_bounded_crt_frame_certificate_existence_full_support_irrationality_generic_coefficient_certificate_engine_one_sided_near_integer_witnesses_weighted_lambert_transform_support_coefficient_calculus_multiples_support_instances_carry_aware_certificates_finite_prefix_calculus_rational_prefix_composition_stray_divisor_calculus_omega_bigomega_coefficient_bridge_pairwise_coprime_support_theorem_eventually_periodic_support_theorem_via_periodic_divisor_orbit_sieve_with_residue_class_and_odd_support_instances_and_weighted_periodic_coefficient_calculus_with_layer_cake_orbit_sieve_linear_growth_engine_one_extra_orbit_defect_nat_weight_lambert_bridge_and_nonnegative_rational_eventually_periodic_coefficient_theorem_and_signed_coefficient_calculus_with_arbitrary_modulus_one_extra_orbit_transport_protected_residue_seed_witnesses_signed_protected_block_certificate_consumer_and_conditional_signed_lambert_socket"
)
ALLOWED_FOUNDATIONAL_AXIOMS = ("Classical.choice", "Quot.sound", "propext")
RECEIPT_PATH = strike.LEAN_TARGET_RUNNER_RECEIPT_PATH
CERTIFICATE_KERNEL_RECEIPT_PATH = strike.CERTIFICATE_KERNEL_TARGET_RUNNER_RECEIPT_PATH
FRONTIER_CONVEYOR_RECEIPT_PATH = strike.FRONTIER_CONVEYOR_RECEIPT_PATH
GENERATED_CERTIFICATE_SHARD_MANIFEST_PATH = (
    strike.GENERATED_CERTIFICATE_SHARD_MANIFEST_PATH
)
PUBLIC_PACKET_PATH = Path(
    "docs/formal_math/generated_erdos257_period_noncollapse_reproducibility_packet.md"
)
CERTIFICATE_KERNEL_PUBLIC_PACKET_PATH = Path(
    "docs/formal_math/generated_erdos257_certificate_kernel_reproducibility_packet.md"
)
GENERATED_MODULE_IMPORT = "Erdos257PeriodNoncollapse.GeneratedCertificates"
CERTIFICATE_KERNEL_MODULE_IMPORT = "Erdos257PeriodNoncollapse.CertificateKernel"
NAMESPACE = "Erdos257PeriodNoncollapse"
ACTIVE_GENERATED_SHARD_AUDIT_MODE = "active_generated_certificate_shard_targets"
CERTIFICATE_KERNEL_AUDIT_MODE = "certificate_kernel_named_targets"
CERTIFICATE_KERNEL_TARGETS = (
    "valuation_deficit_blocks_dvd",
    "valuation_witnesses_imply_no_prime_drop",
    "collapse_divisor_core",
    "gcd_denominator_factor",
    "collapse_divisor_from_gcd_denominator",
    "period_witness_dvd_component",
    "collapse_divisor_from_period_witness",
    "modEq_certificate_implies_no_prime_drop",
    "exists_lcm_factorization_le_row",
    "exists_canonical_witness_selector_row",
    "exactOrderPrimePowerWitness_of_orderOf",
    "exactOrderPrimePowerWitness_of_orderOf_prime",
    "exact_order_witness_supplies_PrimeComponentWitness",
    "finite_period_noncollapse_from_exact_order_witness_supply",
    "orderOf_two_unit_mod_nine_eq_six",
    "orderOf_b2_mod63_eq_6_from_exact_order_witness_route",
    "orderOf_isRoot_cyclotomic_zmod_pow_mul",
    "exists_exactOrderPrimePowerWitness",
    "coprime_base_reducedDenominator",
    "finite_period_noncollapse",
    "finiteErdosSum_eq_commonNumerator_div_commonDenominator",
    "den_natCast_div_natCast_of_coprime",
    "den_natCast_div_natCast",
    "finiteErdosSum_den_eq_reducedDenominator",
    "coprime_base_den_finiteErdosSum",
    "finite_period_noncollapse_concrete",
    "finite_period_noncollapse_rat_den",
    "lcm_lt_den_finiteErdosSum",
    "lcm_Icc_lt_den_erdosPartialSum",
    "one_div_den_mul_den_le_abs_sub",
    "irrational_of_den_mul_abs_sub_tendsto_zero",
    "den_finiteErdosSum_dvd",
    "summable_erdos_term",
    "irrational_erdosSum_of_lcm_gap",
    "irrational_erdosSum_factorial_support",
    "irrational_erdosSum_two_pow_support",
    "erdos257_family_factorial_instance",
    "erdos257_family_two_pow_instance",
    "irrational_of_int_mul_near_int",
    "irrational_of_pow_mul_near_int",
    "summable_divisor_count_term",
    "erdosSum_full_support_eq_tsum_divisor_count",
    "erdosBorwein_constant_lambert_identity",
    "irrational_erdosSum_full_support_of_near_int",
    "lcm_gap_hypothesis_fails_full_support",
    "summable_divisor_count_shift_tail",
    "bpow_mul_divisor_count_series_eq_int_add_tail",
    "summable_const_add_mul_geometric",
    "tsum_const_add_mul_geometric_le",
    "divisor_count_far_tail_le",
    "bpow_dvd_card_divisors_of_exact_prime_block",
    "near_int_witness_of_divisor_block_certificate",
    "irrational_erdosSum_full_support_of_block_certificates",
    "geom_sum_range_le_pow",
    "weighted_middle_bound_of_pointwise",
    "weighted_block_certificate_of_pointwise",
    "near_int_witness_of_weighted_divisor_block_certificate",
    "irrational_erdosSum_full_support_of_weighted_block_certificates",
    "factorization_eq_of_modEq_prod_pow",
    "exists_prime_finset_card_gt",
    "exists_exact_valuation_progression",
    "exists_first_block_divisibility_progression",
    "exists_exact_valuation_progression_with_support",
    "coprime_middle_of_first_block_support",
    "card_filter_dvd_progression_le",
    "card_divisors_le_two_mul_card_small_divisors",
    "sum_card_divisors_progression_le",
    "sum_pow_weight_middle_window_le",
    "sum_weighted_middle_window_le",
    "exists_le_div_of_sum_le",
    "exists_first_block_progression_with_selected_weighted_middle",
    "param_linear_le_two_pow",
    "harmonic_div_sum_core",
    "harmonic_div_sum_le",
    "exists_bertrand_prime_block",
    "exists_bounded_disjoint_prime_blocks",
    "exists_bounded_crt_residue",
    "exists_bounded_first_block_frame",
    "selected_weighted_middle_of_supported_frame",
    "certificate_param_arithmetic",
    "exists_weighted_block_certificates",
    "irrational_erdosSum_full_support",
    "irrational_erdosBorwein_series",
    "summable_coeff_term",
    "summable_coeff_shift_tail",
    "bpow_mul_coeff_series_eq_int_add_tail",
    "coeff_far_tail_le",
    "near_int_witness_of_weighted_coeff_block_certificate",
    "irrational_coeff_series_of_weighted_coeff_block_certificates",
    "irrational_erdosSum_full_support_via_coeff_engine",
    "near_int_witnesses_erdosSum_full_support",
    "zero_block_witnesses_erdosSum_full_support",
    "tsum_prod_weight_mul_pow_eq_tsum_divisor_weight_sum",
    "weighted_lambert_series_identity",
    "supportCoeff_le_card_divisors",
    "supportCoeff_le_self",
    "supportCoeff_univ_eq_card_divisors",
    "supportCoeff_cast_eq_sum_indicator",
    "summable_erdosSupport_indicator",
    "erdosSupportSeries_univ_eq_erdosSum_full_support",
    "erdosSupportSeries_eq_tsum_supportCoeff",
    "irrational_erdosSupportSeries_of_weighted_coeff_certificates",
    "irrational_erdosSupportSeries_univ",
    "erdosSupportSeries_multiples_eq_pow_base_full_support",
    "irrational_erdosSupportSeries_multiples",
    "irrational_erdosSum_multiples_support",
    "carry_block_dvd_of_digitwise_blocks",
    "near_int_witness_of_weighted_coeff_carry_block_certificate",
    "irrational_coeff_series_of_weighted_coeff_carry_block_certificates",
    "irrational_coeff_series_of_digitwise_via_carry",
    "irrational_erdosSupportSeries_of_weighted_coeff_carry_certificates",
    "indicator_support_split_at_cut",
    "erdosSupportSeries_eq_prefix_add_tail",
    "prefix_sum_eq_rat_cast",
    "irrational_erdosSupportSeries_of_tail",
    "irrational_erdosSupportSeries_tail_of_irrational",
    "irrational_of_rat_prefix_tail_near_int_witnesses",
    "supportCoeff_eq_card_filter",
    "supportCoeff_eq_inter_add_diff",
    "supportCoeff_eq_card_of_forced_of_no_strays",
    "card_le_mul_sum_inv",
    "sum_div_add_one_cast_le",
    "exists_tail_bound_of_summable",
    "supportCoeff_primes_eq_card_primeFactors",
    "supportCoeff_primePowers_eq_sum_factorization",
    "erdosSupportSeries_primes_eq_tsum_omega",
    "erdosSupportSeries_primePowers_eq_tsum_bigOmega",
    "exists_linear_lt_pow",
    "supportCoeff_pos_of_mem_dvd",
    "sum_pow_weight_window_hits_le",
    "coprime_prod_prod_of_pairwise_disjoint",
    "coprime_prod_of_pairwise_notMem",
    "exists_disjoint_support_blocks",
    "exists_weighted_coeff_certificates_supportCoeff_pairwise_coprime",
    "irrational_erdosSupportSeries_pairwise_coprime",
    "periodic_pred_add_mul",
    "periodic_pred_iff_of_modEq",
    "card_filter_range_mul_of_periodic",
    "card_filter_divisors_prime_pow_mul_eq_sum",
    "bpow_dvd_card_filter_divisors_of_periodic_block",
    "bpow_dvd_supportCoeff_of_periodic_exact_block",
    "exists_bounded_exact_valuation_frame",
    "certificate_param_arithmetic_periodic",
    "exists_weighted_coeff_certificates_supportCoeff_periodic",
    "irrational_erdosSupportSeries_periodic",
    "irrational_erdosSupportSeries_eventuallyPeriodic",
    "irrational_erdosSupportSeries_residueClass",
    "irrational_erdosSupportSeries_odd",
    "irrational_erdosSupportSeries_multiples_via_periodic",
    "weightedCoeff_le_mul_card_divisors",
    "weightedCoeff_le_mul_self",
    "weight_le_weightedCoeff",
    "weightedCoeff_indicator_eq_supportCoeff",
    "eventually_periodic_add_mul",
    "eventually_periodic_fold",
    "eventually_periodic_weight_bound",
    "weightedCoeff_eq_sum_card_filter",
    "bpow_dvd_weightedCoeff_of_periodic_exact_block",
    "card_filter_range_mul_succ_of_periodic",
    "card_filter_divisors_modEq_of_periodic_extra_orbit",
    "weightedCoeff_modEq_of_periodic_extra_orbit",
    "summable_coeff_term_linear",
    "summable_coeff_shift_tail_linear",
    "bpow_mul_coeff_series_eq_int_add_tail_linear",
    "coeff_far_tail_le_linear",
    "near_int_witness_of_weighted_coeff_block_certificate_linear",
    "irrational_coeff_series_of_weighted_coeff_block_certificates_linear",
    "summable_weightedErdos_term",
    "weightedErdosSeries_eq_tsum_weightedCoeff",
    "exists_weighted_coeff_certificates_weightedCoeff_periodic",
    "irrational_weightedErdosSeries_periodic",
    "irrational_weightedErdosSeries_eventuallyPeriodic",
    "irrational_ratWeightSeries_eventuallyPeriodic",
    "irrational_weightedErdosSeries_mod",
    "intWeightedCoeff_natCast",
    "intWeightedCoeff_eq_weightedCoeff_sub",
    "natAbs_sum_le_sum_natAbs",
    "natAbs_intWeightedCoeff_le_mul_card_divisors",
    "natAbs_intWeightedCoeff_le_mul_self",
    "bpow_dvd_intWeightedCoeff_of_periodic_exact_block",
    "int_modEq_of_nat_modEq",
    "intWeightedCoeff_modEq_of_periodic_extra_orbit",
    "intWeightedCoeff_modEq_of_periodic_extra_orbit_bpow",
    "intWeightedCoeff_eq_weight_of_zero_below",
    "exists_pos_intWeightedCoeff_not_dvd",
    "exists_pos_intWeightedCoeff_ne_zero",
    "exists_intWeightedCoeff_extra_orbit_witness_not_dvd",
    "summable_int_coeff_term",
    "summable_int_coeff_shift_tail",
    "bpow_mul_int_coeff_series_eq_int_add_tail",
    "int_coeff_far_tail_abs_le",
    "int_cast_div_real",
    "near_int_witness_of_int_coeff_protected_block_certificate",
    "irrational_int_coeff_series_of_protected_block_certificates",
    "summable_intWeightedErdos_term",
    "intWeightedErdosSeries_eq_tsum_intWeightedCoeff",
    "irrational_intWeightedErdosSeries_of_protected_block_certificates",
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _rel(path: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str | None:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "args": list(args),
            "cwd": _rel(cwd),
            "returncode": 124,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
        }
    return {
        "args": list(args),
        "cwd": _rel(cwd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "timed_out": False,
        "timeout_seconds": timeout_seconds,
    }


def _process_status(result: Mapping[str, Any]) -> str:
    if result.get("timed_out"):
        return "TIMEOUT"
    return "PASS" if result.get("returncode") == 0 else "FAIL"


def _strike_state(repo_root: Path) -> dict[str, Any]:
    return _read_json(_repo_path(strike.STRIKE_PATH, repo_root=repo_root))


def _lean_microkernel(strike_state: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = strike_state.get("lean_microkernel")
    if isinstance(direct, Mapping):
        return direct
    proof_kernel = strike_state.get("proof_kernel_split")
    if isinstance(proof_kernel, Mapping) and isinstance(
        proof_kernel.get("lean_microkernel"), Mapping
    ):
        return proof_kernel["lean_microkernel"]
    return {}


def _latest_target(strike_state: Mapping[str, Any]) -> str:
    microkernel = _lean_microkernel(strike_state)
    latest = microkernel.get("latest_real_target_binding")
    if isinstance(latest, Mapping) and latest.get("target_id"):
        return str(latest["target_id"])
    residual = microkernel.get("explicit_target_runner_residual")
    if isinstance(residual, Mapping) and residual.get("latest_real_target_binding"):
        return str(residual["latest_real_target_binding"])
    raise ValueError("could not resolve latest real target binding")


def _namespaced(theorem: str) -> str:
    return theorem if theorem.startswith(f"{NAMESPACE}.") else f"{NAMESPACE}.{theorem}"


def _unnamespaced(theorem: str) -> str:
    return theorem.split(".")[-1]


def _target_source(theorem: str, *, module_import: str = GENERATED_MODULE_IMPORT) -> str:
    return _targets_source([theorem], module_import=module_import)


def _targets_source(
    theorems: Sequence[str], *, module_import: str = GENERATED_MODULE_IMPORT
) -> str:
    lines = [f"import {module_import}", ""]
    for theorem in theorems:
        namespaced = _namespaced(theorem)
        lines.extend(
            [
                f"#check {namespaced}",
                f"#print axioms {namespaced}",
                "",
            ]
        )
    return "\n".join(lines)


def _split_axiom_dependencies(body: str) -> list[str]:
    return [
        item.strip()
        for item in body.replace("\n", " ").split(",")
        if item.strip()
    ]


def _parse_axiom_dependencies(stdout: str) -> list[str]:
    if "does not depend on any axioms" in stdout:
        return []
    match = re.search(r"depends on axioms:\s*\[(?P<body>.*?)\]", stdout, re.S)
    if not match:
        return []
    return _split_axiom_dependencies(match.group("body"))


def _parse_target_axiom_dependencies(stdout: str, namespaced: str) -> list[str]:
    pattern = re.compile(
        rf"'?{re.escape(namespaced)}'?\s+"
        r"(?P<result>does not depend on any axioms|depends on axioms:\s*\[(?P<body>.*?)\])",
        re.S,
    )
    match = pattern.search(stdout)
    if not match:
        return _parse_axiom_dependencies(stdout)
    if "does not depend on any axioms" in match.group("result"):
        return []
    return _split_axiom_dependencies(match.group("body") or "")


def _target_print_axioms_seen(stdout: str, namespaced: str) -> bool:
    return bool(
        re.search(
            rf"'?{re.escape(namespaced)}'?\s+"
            r"(does not depend on any axioms|depends on axioms:\s*\[)",
            stdout,
        )
    )


def _source_scan(repo_root: Path) -> dict[str, Any]:
    pattern = re.compile(r"\b(sorry|admit|axiom)\b")
    hits: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for source_ref in strike.LEAN_MICROKERNEL_SOURCE_FILES:
        path = _repo_path(source_ref, repo_root=repo_root)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        file_hits = [
            {
                "source_ref": source_ref.as_posix(),
                "line": line_number,
                "token": match.group(1),
            }
            for line_number, line in enumerate(text.splitlines(), start=1)
            for match in pattern.finditer(line)
        ]
        hits.extend(file_hits)
        rows.append(
            {
                "source_ref": source_ref.as_posix(),
                "present": path.is_file(),
                "sha256": _sha256_file(path),
                "banned_token_hit_count": len(file_hits),
            }
        )
    return {
        "status": "PASS" if not hits and all(row["present"] for row in rows) else "FAIL",
        "banned_token_hit_count": len(hits),
        "hits": hits,
        "source_files": rows,
    }


def _target_line(repo_root: Path, theorem: str) -> int | None:
    pattern = re.compile(rf"^theorem\s+{re.escape(_unnamespaced(theorem))}(\s|$)")
    for source_ref in strike.LEAN_MICROKERNEL_SOURCE_FILES:
        path = _repo_path(source_ref, repo_root=repo_root)
        if not path.is_file():
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if pattern.match(line):
                return line_number
    return None


def _targets_from_frontier_conveyor_receipt(
    *, repo_root: Path = REPO_ROOT
) -> list[str]:
    receipt = _read_json(_repo_path(FRONTIER_CONVEYOR_RECEIPT_PATH, repo_root=repo_root))
    targets: list[str] = []
    for action in receipt.get("applied_actions", []):
        if not isinstance(action, Mapping):
            continue
        if action.get("action_class") != "bind_semantic_spec":
            continue
        target = action.get("expected_period_target")
        if isinstance(target, str) and target:
            targets.append(_unnamespaced(target))
    if not targets:
        raise ValueError(
            "frontier conveyor receipt has no bind_semantic_spec actions with "
            "expected_period_target"
        )
    return targets


def _targets_from_generated_certificate_shard_manifest(
    *, repo_root: Path = REPO_ROOT
) -> tuple[list[str], dict[str, Any]]:
    manifest = _read_json(
        _repo_path(GENERATED_CERTIFICATE_SHARD_MANIFEST_PATH, repo_root=repo_root)
    )
    candidate = manifest.get("candidate")
    if not isinstance(candidate, str) or not candidate:
        raise ValueError("generated certificate shard manifest has no candidate")
    shard_specs = strike._direct_prime_generated_certificate_shard_manifest_specs(
        repo_root=repo_root
    )
    specs = shard_specs.get(candidate) or []
    if not specs:
        raise ValueError(
            f"generated certificate shard manifest has no renderable spec: {candidate}"
        )
    spec = specs[0]
    targets = strike._direct_prime_certificate_target_ids(spec)
    expected = int(
        (manifest.get("target_delta_bound") or {}).get("expected_new_target_count")
        or 0
    )
    if expected and len(targets) != expected:
        raise ValueError(
            "generated certificate shard manifest target count mismatch: "
            f"expected {expected}, resolved {len(targets)}"
        )
    return targets, {
        "candidate": candidate,
        "expected_new_target_count": expected,
        "module_path": str(spec.get("lean_module_path") or ""),
        "manifest_ref": GENERATED_CERTIFICATE_SHARD_MANIFEST_PATH.as_posix(),
    }


def _targets_from_active_generated_certificate_shards(
    *, repo_root: Path = REPO_ROOT
) -> tuple[list[str], dict[str, Any]]:
    registry = strike._direct_prime_active_generated_shard_registry(
        repo_root=repo_root
    )
    active_shards = [
        row
        for row in registry.get("active_shards", [])
        if isinstance(row, Mapping)
    ]
    targets: list[str] = []
    for row in active_shards:
        targets.extend(
            str(target)
            for target in row.get("target_ids", [])
            if isinstance(target, str) and target
        )
    duplicate_targets = sorted(
        target for target in set(targets) if targets.count(target) > 1
    )
    if not active_shards:
        raise ValueError("active generated shard registry has no active shards")
    if duplicate_targets:
        raise ValueError(
            "active generated shard registry has duplicate targets: "
            + ", ".join(duplicate_targets)
        )
    return targets, {
        "active_shard_count": len(active_shards),
        "active_shards": [
            {
                "spec_id": str(row.get("spec_id") or ""),
                "module_path": str(row.get("module_path") or ""),
                "target_ids": [
                    str(target)
                    for target in row.get("target_ids", [])
                    if isinstance(target, str) and target
                ],
                "target_count": int(row.get("target_count") or 0),
                "row_signature_id": row.get("row_signature_id"),
            }
            for row in active_shards
        ],
        "expected_target_count": len(targets),
        "registry_status": registry.get("status"),
        "manifest_ref": GENERATED_CERTIFICATE_SHARD_MANIFEST_PATH.as_posix(),
    }


def _git_value(args: Sequence[str], repo_root: Path) -> str | None:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def _skipped_module_build_result(
    project_root: Path,
    repo_root: Path,
    *,
    module_import: str = GENERATED_MODULE_IMPORT,
) -> dict[str, Any]:
    return {
        "args": ["lake", "build", module_import],
        "cwd": _rel(project_root, repo_root=repo_root),
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "skipped": True,
        "timed_out": False,
        "timeout_seconds": None,
    }


def _run_module_build(
    *,
    repo_root: Path,
    timeout_seconds: int,
    module_import: str = GENERATED_MODULE_IMPORT,
) -> dict[str, Any]:
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    return _run(
        ["lake", "build", module_import],
        cwd=project_root,
        timeout_seconds=timeout_seconds,
    )


def _module_build_receipt(
    build_result: Mapping[str, Any],
    *,
    module_import: str = GENERATED_MODULE_IMPORT,
) -> dict[str, Any]:
    return {
        "status": _process_status(build_result),
        "command": (
            "cd formal_math/erdos257_period_noncollapse && lake build "
            f"{module_import}"
        ),
        "returncode": build_result["returncode"],
        "timed_out": bool(build_result.get("timed_out")),
        "timeout_seconds": build_result.get("timeout_seconds"),
        "stdout_sha256": _sha256_text(str(build_result["stdout"])),
        "stderr_sha256": _sha256_text(str(build_result["stderr"])),
    }


def _target_receipt_from_lean_result(
    *,
    target: str,
    lean_result: Mapping[str, Any],
    lean_source: str,
    build_result: Mapping[str, Any],
    source_scan: Mapping[str, Any],
    repo_root: Path,
    module_import: str,
    batch_target_count: int = 1,
) -> dict[str, Any]:
    namespaced = _namespaced(target)
    stdout = str(lean_result["stdout"])
    axiom_dependencies = _parse_target_axiom_dependencies(stdout, namespaced)
    allowed = set(ALLOWED_FOUNDATIONAL_AXIOMS)
    custom_axioms = [dep for dep in axiom_dependencies if dep not in allowed]
    sorry_like = any(dep in {"sorryAx", "Lean.sorryAx"} for dep in axiom_dependencies)
    target_check_status = (
        "TIMEOUT"
        if lean_result.get("timed_out")
        else "PASS"
        if lean_result["returncode"] == 0 and namespaced in stdout
        else "FAIL"
    )
    print_axioms_status = (
        "TIMEOUT"
        if lean_result.get("timed_out")
        else "PASS"
        if lean_result["returncode"] == 0
        and _target_print_axioms_seen(stdout, namespaced)
        else "FAIL"
    )
    axiom_dependency_class = (
        "none"
        if not axiom_dependencies
        else "foundational_axioms_only"
        if not custom_axioms and not sorry_like
        else "custom_or_sorry_axiom_dependency"
    )
    status = (
        "PASS"
        if build_result["returncode"] == 0
        and lean_result["returncode"] == 0
        and target_check_status == "PASS"
        and print_axioms_status == "PASS"
        and axiom_dependency_class in {"none", "foundational_axioms_only"}
        and source_scan["status"] == "PASS"
        else "FAIL"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "owner_id": OWNER_ID,
        "generated_at": _utc_now(),
        "status": status,
        "audit_mode": "single_target",
        "target_count": 1,
        "target_theorem": _unnamespaced(target),
        "namespaced_target_theorem": namespaced,
        "target_line": _target_line(repo_root, target),
        "target_check_status": target_check_status,
        "print_axioms_status": print_axioms_status,
        "axiom_dependency_class": axiom_dependency_class,
        "axiom_dependencies": axiom_dependencies,
        "allowed_foundational_axioms": list(ALLOWED_FOUNDATIONAL_AXIOMS),
        "custom_axiom_dependencies": custom_axioms,
        "sorry_like_axiom_dependency_detected": sorry_like,
        "module_import": module_import,
        "lean_source_sha256": _sha256_text(lean_source),
        "module_build": _module_build_receipt(
            build_result,
            module_import=module_import,
        ),
        "target_runner": {
            "status": _process_status(lean_result),
            "command": (
                "cd formal_math/erdos257_period_noncollapse && "
                "lake env lean <generated-target-runner-temp-file>"
            ),
            "returncode": lean_result["returncode"],
            "timed_out": bool(lean_result.get("timed_out")),
            "timeout_seconds": lean_result.get("timeout_seconds"),
            "batch_target_count": batch_target_count,
            "stdout": stdout,
            "stderr": lean_result["stderr"],
            "stdout_sha256": _sha256_text(stdout),
            "stderr_sha256": _sha256_text(str(lean_result["stderr"])),
        },
        "static_placeholder_scan": dict(source_scan),
        "source_refs": {
            "strike_json": strike.STRIKE_PATH.as_posix(),
            "generated_certificates": strike.DIRECT_PRIME_GENERATED_LEAN_MODULE.as_posix(),
            "generated_certificate_modules": [
                path.as_posix()
                for path in strike.LEAN_MICROKERNEL_SOURCE_FILES
                if "GeneratedCertificates" in path.as_posix()
            ],
            "receipt": RECEIPT_PATH.as_posix(),
            "public_packet": PUBLIC_PACKET_PATH.as_posix(),
        },
        "git": {
            "head": _git_value(["rev-parse", "HEAD"], repo_root),
            "origin_main": _git_value(["rev-parse", "origin/main"], repo_root),
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "non_claims": [
            "not_arbitrary_infinite_support_irrationality_theorem",
            "not_arbitrary_support_certificate_existence",
            "not_prime_or_prime_power_support_irrationality_theorem",
            "not_signed_rational_periodic_coefficient_lambert_theorem",
            "not_protected_certificate_supply_for_periodic_int_weights",
            "not_primitive_divisor_existence",
            "not_arbitrary_generated_row_existence",
            "not_erdos_257_solution",
            "not_publication_authority",
        ],
    }


def build_receipt(
    *,
    target_theorem: str | None,
    skip_build: bool,
    timeout_seconds: int,
    repo_root: Path = REPO_ROOT,
    module_import: str = GENERATED_MODULE_IMPORT,
) -> dict[str, Any]:
    strike_state = _strike_state(repo_root)
    target = target_theorem or _latest_target(strike_state)
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)

    build_result = (
        _skipped_module_build_result(
            project_root,
            repo_root,
            module_import=module_import,
        )
        if skip_build
        else _run_module_build(
            repo_root=repo_root,
            timeout_seconds=timeout_seconds,
            module_import=module_import,
        )
    )

    lean_source = _target_source(target, module_import=module_import)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="erdos257_target_runner_",
        suffix=".lean",
        delete=False,
    ) as handle:
        handle.write(lean_source)
        temp_path = Path(handle.name)
    try:
        lean_result = _run(
            ["lake", "env", "lean", temp_path.as_posix()],
            cwd=project_root,
            timeout_seconds=timeout_seconds,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    source_scan = _source_scan(repo_root)
    return _target_receipt_from_lean_result(
        target=target,
        lean_result=lean_result,
        lean_source=lean_source,
        build_result=build_result,
        source_scan=source_scan,
        repo_root=repo_root,
        module_import=module_import,
    )


def _build_batched_target_receipts(
    targets: Sequence[str],
    *,
    timeout_seconds: int,
    repo_root: Path,
    module_import: str = GENERATED_MODULE_IMPORT,
) -> list[dict[str, Any]]:
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    lean_source = _targets_source(targets, module_import=module_import)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="erdos257_target_runner_",
        suffix=".lean",
        delete=False,
    ) as handle:
        handle.write(lean_source)
        temp_path = Path(handle.name)
    try:
        lean_result = _run(
            ["lake", "env", "lean", temp_path.as_posix()],
            cwd=project_root,
            timeout_seconds=timeout_seconds,
        )
    finally:
        temp_path.unlink(missing_ok=True)
    source_scan = _source_scan(repo_root)
    build_result = _skipped_module_build_result(
        project_root,
        repo_root,
        module_import=module_import,
    )
    return [
        _target_receipt_from_lean_result(
            target=target,
            lean_result=lean_result,
            lean_source=lean_source,
            build_result=build_result,
            source_scan=source_scan,
            repo_root=repo_root,
            module_import=module_import,
            batch_target_count=len(targets),
        )
        for target in targets
    ]


def _target_audit_row(receipt: Mapping[str, Any]) -> dict[str, Any]:
    target_runner = receipt.get("target_runner")
    target_runner_status = (
        target_runner.get("status") if isinstance(target_runner, Mapping) else None
    )
    target_runner_timed_out = (
        bool(target_runner.get("timed_out")) if isinstance(target_runner, Mapping) else False
    )
    target_runner_timeout_seconds = (
        target_runner.get("timeout_seconds") if isinstance(target_runner, Mapping) else None
    )
    return {
        "target_theorem": receipt.get("target_theorem"),
        "namespaced_target_theorem": receipt.get("namespaced_target_theorem"),
        "target_line": receipt.get("target_line"),
        "target_check_status": receipt.get("target_check_status"),
        "print_axioms_status": receipt.get("print_axioms_status"),
        "axiom_dependency_class": receipt.get("axiom_dependency_class"),
        "axiom_dependencies": receipt.get("axiom_dependencies", []),
        "custom_axiom_dependencies": receipt.get("custom_axiom_dependencies", []),
        "sorry_like_axiom_dependency_detected": receipt.get(
            "sorry_like_axiom_dependency_detected"
        ),
        "target_runner_status": target_runner_status,
        "target_runner_timed_out": target_runner_timed_out,
        "target_runner_timeout_seconds": target_runner_timeout_seconds,
        "status": receipt.get("status"),
    }


def build_receipt_from_frontier_conveyor_receipt(
    *,
    skip_build: bool,
    timeout_seconds: int,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    targets = _targets_from_frontier_conveyor_receipt(repo_root=repo_root)
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    build_result = (
        _skipped_module_build_result(project_root, repo_root)
        if skip_build
        else _run_module_build(repo_root=repo_root, timeout_seconds=timeout_seconds)
    )
    target_receipts = _build_batched_target_receipts(
        targets,
        timeout_seconds=timeout_seconds,
        repo_root=repo_root,
    )
    target_rows = [_target_audit_row(receipt) for receipt in target_receipts]
    primary = dict(target_receipts[-1])
    all_targets_foundational_or_none = all(
        row.get("status") == "PASS"
        and row.get("target_check_status") == "PASS"
        and row.get("print_axioms_status") == "PASS"
        and row.get("axiom_dependency_class") in {"none", "foundational_axioms_only"}
        and not row.get("custom_axiom_dependencies")
        and not row.get("sorry_like_axiom_dependency_detected")
        for row in target_rows
    )
    primary.update(
        {
            "audit_mode": "frontier_conveyor_applied_direct_targets",
            "target_count": len(target_rows),
            "targets": target_rows,
            "all_targets_foundational_or_none": all_targets_foundational_or_none,
            "frontier_conveyor_receipt_ref": FRONTIER_CONVEYOR_RECEIPT_PATH.as_posix(),
            "module_build": _module_build_receipt(build_result),
            "status": (
                "PASS"
                if build_result["returncode"] == 0
                and primary.get("status") == "PASS"
                and all_targets_foundational_or_none
                else "FAIL"
            ),
        }
    )
    return primary


def build_receipt_from_generated_certificate_shard_manifest(
    *,
    skip_build: bool,
    timeout_seconds: int,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    targets, manifest_context = _targets_from_generated_certificate_shard_manifest(
        repo_root=repo_root
    )
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    build_result = (
        _skipped_module_build_result(project_root, repo_root)
        if skip_build
        else _run_module_build(repo_root=repo_root, timeout_seconds=timeout_seconds)
    )
    target_receipts = _build_batched_target_receipts(
        targets,
        timeout_seconds=timeout_seconds,
        repo_root=repo_root,
    )
    target_rows = [_target_audit_row(receipt) for receipt in target_receipts]
    primary = dict(target_receipts[-1])
    all_targets_foundational_or_none = all(
        row.get("status") == "PASS"
        and row.get("target_check_status") == "PASS"
        and row.get("print_axioms_status") == "PASS"
        and row.get("axiom_dependency_class") in {"none", "foundational_axioms_only"}
        and not row.get("custom_axiom_dependencies")
        and not row.get("sorry_like_axiom_dependency_detected")
        for row in target_rows
    )
    target_count_matches_manifest = len(target_rows) == int(
        manifest_context.get("expected_new_target_count") or 0
    )
    primary.update(
        {
            "audit_mode": "generated_certificate_shard_manifest_targets",
            "target_count": len(target_rows),
            "targets": target_rows,
            "all_targets_foundational_or_none": all_targets_foundational_or_none,
            "generated_certificate_shard_manifest_ref": manifest_context[
                "manifest_ref"
            ],
            "generated_certificate_shard_candidate": manifest_context["candidate"],
            "generated_certificate_shard_module_path": manifest_context[
                "module_path"
            ],
            "expected_new_target_count": manifest_context[
                "expected_new_target_count"
            ],
            "target_count_matches_manifest": target_count_matches_manifest,
            "module_build": _module_build_receipt(build_result),
            "status": (
                "PASS"
                if build_result["returncode"] == 0
                and primary.get("status") == "PASS"
                and all_targets_foundational_or_none
                and target_count_matches_manifest
                else "FAIL"
            ),
        }
    )
    return primary


def build_receipt_from_active_generated_certificate_shards(
    *,
    skip_build: bool,
    timeout_seconds: int,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    targets, registry_context = _targets_from_active_generated_certificate_shards(
        repo_root=repo_root
    )
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    build_result = (
        _skipped_module_build_result(project_root, repo_root)
        if skip_build
        else _run_module_build(repo_root=repo_root, timeout_seconds=timeout_seconds)
    )
    target_receipts = _build_batched_target_receipts(
        targets,
        timeout_seconds=timeout_seconds,
        repo_root=repo_root,
    )
    target_rows = [_target_audit_row(receipt) for receipt in target_receipts]
    primary = dict(target_receipts[-1])
    all_targets_foundational_or_none = all(
        row.get("status") == "PASS"
        and row.get("target_check_status") == "PASS"
        and row.get("print_axioms_status") == "PASS"
        and row.get("axiom_dependency_class") in {"none", "foundational_axioms_only"}
        and not row.get("custom_axiom_dependencies")
        and not row.get("sorry_like_axiom_dependency_detected")
        for row in target_rows
    )
    target_count_matches_active_shards = len(target_rows) == int(
        registry_context.get("expected_target_count") or 0
    )
    primary.update(
        {
            "audit_mode": ACTIVE_GENERATED_SHARD_AUDIT_MODE,
            "target_count": len(target_rows),
            "targets": target_rows,
            "all_targets_foundational_or_none": all_targets_foundational_or_none,
            "generated_certificate_shard_manifest_ref": registry_context[
                "manifest_ref"
            ],
            "active_shard_count": registry_context["active_shard_count"],
            "active_shards": registry_context["active_shards"],
            "expected_active_shard_target_count": registry_context[
                "expected_target_count"
            ],
            "target_count_matches_active_shards": (
                target_count_matches_active_shards
            ),
            "module_build": _module_build_receipt(build_result),
            "status": (
                "PASS"
                if build_result["returncode"] == 0
                and primary.get("status") == "PASS"
                and all_targets_foundational_or_none
                and target_count_matches_active_shards
                else "FAIL"
            ),
        }
    )
    return primary


def build_receipt_from_certificate_kernel_targets(
    *,
    skip_build: bool,
    timeout_seconds: int,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    targets = list(CERTIFICATE_KERNEL_TARGETS)
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    build_result = (
        _skipped_module_build_result(
            project_root,
            repo_root,
            module_import=CERTIFICATE_KERNEL_MODULE_IMPORT,
        )
        if skip_build
        else _run_module_build(
            repo_root=repo_root,
            timeout_seconds=timeout_seconds,
            module_import=CERTIFICATE_KERNEL_MODULE_IMPORT,
        )
    )
    target_receipts = _build_batched_target_receipts(
        targets,
        timeout_seconds=timeout_seconds,
        repo_root=repo_root,
        module_import=CERTIFICATE_KERNEL_MODULE_IMPORT,
    )
    target_rows = [_target_audit_row(receipt) for receipt in target_receipts]
    primary = dict(target_receipts[-1])
    all_targets_foundational_or_none = all(
        row.get("status") == "PASS"
        and row.get("target_check_status") == "PASS"
        and row.get("print_axioms_status") == "PASS"
        and row.get("axiom_dependency_class") in {"none", "foundational_axioms_only"}
        and not row.get("custom_axiom_dependencies")
        and not row.get("sorry_like_axiom_dependency_detected")
        for row in target_rows
    )
    target_count_matches_kernel_list = len(target_rows) == len(CERTIFICATE_KERNEL_TARGETS)
    primary.update(
        {
            "audit_mode": CERTIFICATE_KERNEL_AUDIT_MODE,
            "module_import": CERTIFICATE_KERNEL_MODULE_IMPORT,
            "target_count": len(target_rows),
            "targets": target_rows,
            "certificate_kernel_targets": targets,
            "all_targets_foundational_or_none": all_targets_foundational_or_none,
            "target_count_matches_certificate_kernel_list": (
                target_count_matches_kernel_list
            ),
            "module_build": _module_build_receipt(
                build_result,
                module_import=CERTIFICATE_KERNEL_MODULE_IMPORT,
            ),
            "status": (
                "PASS"
                if build_result["returncode"] == 0
                and primary.get("status") == "PASS"
                and all_targets_foundational_or_none
                and target_count_matches_kernel_list
                else "FAIL"
            ),
        }
    )
    return primary


def _target_runner_receipt_summary(
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(receipt, Mapping):
        return None
    target_rows = [
        row for row in receipt.get("targets", []) if isinstance(row, Mapping)
    ]
    target_theorems = [
        str(row["target_theorem"])
        for row in target_rows
        if isinstance(row.get("target_theorem"), str)
    ]
    if not target_theorems and isinstance(receipt.get("target_theorem"), str):
        target_theorems = [str(receipt["target_theorem"])]
    return {
        "schema_version": receipt.get("schema_version"),
        "generated_at": receipt.get("generated_at"),
        "status": receipt.get("status"),
        "audit_mode": receipt.get("audit_mode"),
        "target_count": receipt.get("target_count"),
        "target_theorem": receipt.get("target_theorem"),
        "target_theorems": target_theorems,
        "target_check_status": receipt.get("target_check_status"),
        "print_axioms_status": receipt.get("print_axioms_status"),
        "axiom_dependency_class": receipt.get("axiom_dependency_class"),
        "all_targets_foundational_or_none": receipt.get(
            "all_targets_foundational_or_none"
        ),
        "frontier_conveyor_receipt_ref": receipt.get(
            "frontier_conveyor_receipt_ref"
        ),
        "generated_certificate_shard_manifest_ref": receipt.get(
            "generated_certificate_shard_manifest_ref"
        ),
        "generated_certificate_shard_candidate": receipt.get(
            "generated_certificate_shard_candidate"
        ),
        "generated_certificate_shard_module_path": receipt.get(
            "generated_certificate_shard_module_path"
        ),
        "target_count_matches_manifest": receipt.get("target_count_matches_manifest"),
        "active_shard_count": receipt.get("active_shard_count"),
        "active_shards": receipt.get("active_shards"),
        "expected_active_shard_target_count": receipt.get(
            "expected_active_shard_target_count"
        ),
        "target_count_matches_active_shards": receipt.get(
            "target_count_matches_active_shards"
        ),
        "certificate_kernel_targets": receipt.get("certificate_kernel_targets"),
        "target_count_matches_certificate_kernel_list": receipt.get(
            "target_count_matches_certificate_kernel_list"
        ),
        "claim_boundary": receipt.get("claim_boundary"),
    }


def _with_receipt_lineage(
    receipt: Mapping[str, Any],
    existing: Mapping[str, Any] | None,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    enriched = dict(receipt)
    lineage: list[dict[str, Any]] = []
    summary = _target_runner_receipt_summary(existing)
    if summary:
        lineage.append(summary)
    if isinstance(existing, Mapping):
        for row in existing.get("recent_target_runner_receipt_lineage", []):
            if isinstance(row, Mapping):
                lineage.append(dict(row))
            if len(lineage) >= limit:
                break
    enriched["previous_target_runner_receipt_summary"] = (
        lineage[0] if lineage else None
    )
    enriched["recent_target_runner_receipt_lineage"] = lineage[:limit]
    return enriched


def _markdown_list(items: Sequence[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "`none`"


def build_public_packet(
    receipt: Mapping[str, Any],
    *,
    receipt_path: Path = RECEIPT_PATH,
) -> str:
    target = str(receipt["target_theorem"])
    axiom_dependencies = [str(item) for item in receipt.get("axiom_dependencies", [])]
    custom_axioms = [str(item) for item in receipt.get("custom_axiom_dependencies", [])]
    target_rows = [
        row
        for row in receipt.get("targets", [])
        if isinstance(row, Mapping)
    ]
    tranche_section: list[str] = []
    if target_rows:
        audit_heading = (
            "## Generated-Shard Manifest Target Audit"
            if receipt.get("audit_mode") == "generated_certificate_shard_manifest_targets"
            else "## Active Generated-Shard Target Audit"
            if receipt.get("audit_mode") == ACTIVE_GENERATED_SHARD_AUDIT_MODE
            else "## CertificateKernel Named Target Audit"
            if receipt.get("audit_mode") == CERTIFICATE_KERNEL_AUDIT_MODE
            else "## Conveyor-Applied Direct Target Audit"
        )
        source_ref = (
            receipt.get("generated_certificate_shard_manifest_ref")
            if receipt.get("audit_mode")
            in {
                "generated_certificate_shard_manifest_targets",
                ACTIVE_GENERATED_SHARD_AUDIT_MODE,
            }
            else strike.LEAN_MICROKERNEL_FILE.as_posix()
            if receipt.get("audit_mode") == CERTIFICATE_KERNEL_AUDIT_MODE
            else receipt.get("frontier_conveyor_receipt_ref")
        )
        source_label = (
            "Generated shard manifest"
            if receipt.get("audit_mode")
            in {
                "generated_certificate_shard_manifest_targets",
                ACTIVE_GENERATED_SHARD_AUDIT_MODE,
            }
            else "CertificateKernel module"
            if receipt.get("audit_mode") == CERTIFICATE_KERNEL_AUDIT_MODE
            else "Frontier conveyor receipt"
        )
        tranche_section = [
            audit_heading,
            "",
            f"- Audit mode: `{receipt.get('audit_mode')}`",
            f"- Target count: `{receipt.get('target_count')}`",
            f"- All targets foundational-or-none: `{receipt.get('all_targets_foundational_or_none')}`",
            f"- {source_label}: `{source_ref}`",
            "",
        ]
        if receipt.get("audit_mode") == "generated_certificate_shard_manifest_targets":
            tranche_section.extend(
                [
                    f"- Generated shard candidate: `{receipt.get('generated_certificate_shard_candidate')}`",
                    f"- Generated shard module: `{receipt.get('generated_certificate_shard_module_path')}`",
                    f"- Target count matches manifest: `{receipt.get('target_count_matches_manifest')}`",
                    "",
                ]
            )
        if receipt.get("audit_mode") == ACTIVE_GENERATED_SHARD_AUDIT_MODE:
            tranche_section.extend(
                [
                    f"- Active shard count: `{receipt.get('active_shard_count')}`",
                    f"- Target count matches active shards: `{receipt.get('target_count_matches_active_shards')}`",
                    "",
                ]
            )
            for shard in receipt.get("active_shards", []):
                if not isinstance(shard, Mapping):
                    continue
                tranche_section.extend(
                    [
                        f"- Active shard `{shard.get('spec_id')}`: `{shard.get('target_count')}` targets, module `{shard.get('module_path')}`, row signature `{shard.get('row_signature_id')}`",
                    ]
                )
            tranche_section.append("")
        if receipt.get("audit_mode") == CERTIFICATE_KERNEL_AUDIT_MODE:
            tranche_section.extend(
                [
                    f"- Target count matches CertificateKernel list: `{receipt.get('target_count_matches_certificate_kernel_list')}`",
                    "",
                ]
            )
        for row in target_rows:
            row_axioms = [str(item) for item in row.get("axiom_dependencies", [])]
            tranche_section.extend(
                [
                    f"- `{row.get('target_theorem')}`: `#check` `{row.get('target_check_status')}`, `#print axioms` `{row.get('print_axioms_status')}`, axiom class `{row.get('axiom_dependency_class')}`, dependencies {_markdown_list(row_axioms)}",
                ]
            )
        tranche_section.append("")

    lineage_rows = [
        row
        for row in receipt.get("recent_target_runner_receipt_lineage", [])
        if isinstance(row, Mapping)
    ]
    lineage_section: list[str] = []
    if lineage_rows:
        lineage_section = [
            "## Recent Target-Runner Audit Lineage",
            "",
            "These rows summarize prior receipt-applied audits before the current live receipt was refreshed. They are provenance rows, not proof authority.",
            "",
        ]
        for row in lineage_rows:
            row_targets = [
                str(item)
                for item in row.get("target_theorems", [])
                if isinstance(item, str)
            ]
            lineage_section.extend(
                [
                    f"- `{row.get('generated_at')}`: audit `{row.get('audit_mode')}`, status `{row.get('status')}`, target count `{row.get('target_count')}`, targets {_markdown_list(row_targets)}",
                ]
            )
        lineage_section.append("")

    if receipt.get("audit_mode") == "frontier_conveyor_applied_direct_targets":
        runner_command = (
            "./repo-python tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py "
            "--from-frontier-conveyor-receipt --check"
        )
    elif receipt.get("audit_mode") == "generated_certificate_shard_manifest_targets":
        runner_command = (
            "./repo-python tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py "
            "--from-generated-certificate-shard-manifest --check"
        )
    elif receipt.get("audit_mode") == ACTIVE_GENERATED_SHARD_AUDIT_MODE:
        runner_command = (
            "./repo-python tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py "
            "--from-active-generated-shards --check"
        )
    elif receipt.get("audit_mode") == CERTIFICATE_KERNEL_AUDIT_MODE:
        runner_command = (
            "./repo-python tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py "
            "--from-certificate-kernel-targets --check"
        )
    else:
        runner_command = (
            "./repo-python tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py "
            f"--target {target} --check"
        )
    return "\n".join(
        [
            "# Lean-Backed Period-Noncollapse Certificate Engine",
            "",
            "_Generated by `tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py`. Do not edit by hand._",
            "",
            "This packet is a public-safe reproducibility surface for exact concrete Lean targets in the Erdos257 period-noncollapse pilot. It is intentionally scoped to generated certificate-table targets and explicit non-claims.",
            "",
            "## Exact Target Runner",
            "",
            f"- Target theorem: `{target}`",
            f"- Namespaced theorem: `{receipt['namespaced_target_theorem']}`",
            f"- Target line: `{receipt.get('target_line')}`",
            f"- `#check`: `{receipt.get('target_check_status')}`",
            f"- `#print axioms`: `{receipt.get('print_axioms_status')}`",
            f"- Axiom dependency class: `{receipt.get('axiom_dependency_class')}`",
            f"- Axiom dependencies: {_markdown_list(axiom_dependencies)}",
            f"- Custom axiom dependencies: {_markdown_list(custom_axioms)}",
            f"- Static placeholder scan: `{receipt.get('static_placeholder_scan', {}).get('status')}`",
            "",
            *tranche_section,
            *lineage_section,
            "## Reproduction Commands",
            "",
            "```bash",
            "./repo-python tools/meta/factory/run_formal_math_erdos257_period_noncollapse_strike.py --check",
            "cd formal_math/erdos257_period_noncollapse && lake build Erdos257PeriodNoncollapse.GeneratedCertificates",
            "cd ../../..",
            runner_command,
            "./repo-pytest system/server/tests/test_formal_math_erdos257_lean_target_runner.py system/server/tests/test_formal_math_erdos257_period_noncollapse_strike.py",
            "```",
            "",
            "## Proof Boundary",
            "",
            "- Verified concrete certificate-table period targets are Lean-checked generated instances.",
            "- The generated consumer layer depends on the hand-written certificate kernel.",
            "- The frontier/scout layer recommends concrete factory actions; it is not proof authority.",
            "- Canonical-selector existence, the exact-order witness-supply reduction, and witness supply itself are Lean-checked: `exists_exactOrderPrimePowerWitness` constructs an exact-order prime-power witness for every `b >= 2, n >= 2` via the cyclotomic route (no Zsigmondy input needed), so `finite_period_noncollapse` holds unconditionally for every finite nonempty positive support and integer base `b >= 2`. Paper/referee closure remains open.",
            "- The rational-denominator bridge is Lean-checked: `finiteErdosSum_den_eq_reducedDenominator` identifies the audited reduced denominator with `Rat.den` of the literal rational partial sum, `finite_period_noncollapse_rat_den` restates the unconditional theorem over that `Rat.den`, and `lcm_Icc_lt_den_erdosPartialSum` proves strict denominator growth `lcm(1..N) < den` for the classical partial sums in pure Mathlib vocabulary.",
            "- The infinite bridge is Lean-checked: `irrational_of_den_mul_abs_sub_tendsto_zero` proves the Dirichlet-gap irrationality criterion over `Rat.den`, and `irrational_erdosSum_of_lcm_gap` derives irrationality of the infinite series `sum 1 / (b^(a k) - 1)` for every base `b >= 2` whenever the support outruns the lcm of its own prefix. Instances `irrational_erdosSum_factorial_support` and `irrational_erdosSum_two_pow_support` are the first Lean-checked infinite-series irrationality theorems in this lane; `erdos257_family_factorial_instance` and `erdos257_family_two_pow_instance` are the literal base-2 members of the Erdos #257 statement family for the infinite supports `A = {n!}` and `A = {2^n}`. These are classical-style lacunary results formalised through the kernel's own denominator authority, not new mathematics.",
            "- The full-support lane is Lean-checked up to its final step: `irrational_of_int_mul_near_int` proves the integer-dilation near-integer irrationality criterion (a second engine alongside the denominator-gap criterion), `erdosSum_full_support_eq_tsum_divisor_count` proves the Lambert bridge `sum_{n>=1} 1 / (b^n - 1) = sum_{m>=1} tau(m) / b^m` for every base `b >= 2` (`erdosBorwein_constant_lambert_identity` is the literal base-2 Erdos-Borwein form), and `irrational_erdosSum_full_support_of_near_int` reduces full-support irrationality to producing near-integer witnesses for the divisor-count series — the exact obligation Erdos's 1948 congruence construction discharges, now formalised in the certificate-existence entry below. `lcm_gap_hypothesis_fails_full_support` machine-checks that the lcm-gap criterion cannot fire at full support, so the near-integer route is necessary, not optional.",
            "- The near-integer witness obligation is now certificate-shaped: `bpow_mul_divisor_count_series_eq_int_add_tail` proves the base-`b` shifted-tail decomposition (dilating the divisor-count series by `b^N` splits off an integer plus the tail `sum_r tau(N+r+1) / b^(r+1)`), `bpow_dvd_card_divisors_of_exact_prime_block` proves the multiplicativity hinge `b^|P| | tau(n)` when every prime in `P` carries exact valuation `b - 1` (the many-small-exact-valuations shape of Erdos's 1948 congruence construction), `near_int_witness_of_divisor_block_certificate` consumes one finite divisor block certificate `(N, K, L, B)` — first-block divisibility `b^r | tau(N+r)` for `1 <= r <= K`, middle window `tau(N+r) <= B` for `K < r <= L`, and the single Nat-arithmetic inequality `q * (B * b^(L-K) + (N+L+2)) < b^L` — into a near-integer witness, and `irrational_erdosSum_full_support_of_block_certificates` closes the loop: certificates at every precision `q` give full-support irrationality. That finite-arithmetic obligation — certificate existence for every `q` — is discharged in the certificate-existence entry below.",
            "- The certificate interface is now weighted and its first block is constructible: `near_int_witness_of_weighted_divisor_block_certificate` consumes the sharper weighted certificate `(N, K, L, C)` whose middle hypothesis is the exact weighted sum `sum_{K<r<=L} tau(N+r) * b^(L-r) <= C` — the quantity the near-integer argument actually pays for — with the closing inequality `q * (C + (N+L+2)) < b^L`; `weighted_block_certificate_of_pointwise` proves pointwise `(N, K, L, B)` data always supplies it with `C = B * b^(L-K)`, so the weighted interface strictly subsumes the pointwise one, and `irrational_erdosSum_full_support_of_weighted_block_certificates` closes the loop through weighted certificates. On the existence side, `exists_first_block_divisibility_progression` proves the first-block half of certificate existence: for every `b >= 2`, window length `K`, and prime floor `L` there are `x` and a positive modulus `A` with `b^r | tau(x + y*A + r)` for every `y` and every `1 <= r <= K` — Erdos's 1948 CRT/exact-valuation construction, built one fresh prime block at a time (`exists_exact_valuation_progression` glues one congruence per block by binary CRT; `factorization_eq_of_modEq_prod_pow` extracts exact valuation `b - 1` from each product congruence). The middle-window selection itself is Lean-checked in the next entry; size control of the CRT frame and the final parameter closure are discharged in the certificate-existence entry after it.",
            "- The middle-window average and selection are now Lean-checked: `exists_exact_valuation_progression_with_support` re-runs the CRT ladder exposing the modulus frame (every prime of `A` lies above `L` and divides `x + r` for some first-block slot `r <= K`), `coprime_middle_of_first_block_support` turns that frame into middle-window coprimality `gcd(A, x+s) = 1` for `K < s <= L` (a common prime would divide `s - r`, positive and below `L < p`), `card_filter_dvd_progression_le` counts at most `Y/d + 1` window members divisible by any `d` coprime to the step, `card_divisors_le_two_mul_card_small_divisors` is the divisor-pairing bound `tau(n) <= 2 * #{d <= sqrt(X) : d | n}`, `sum_card_divisors_progression_le` combines them into the PNT-free progression average `sum_{y<Y} tau(A*y+c) <= 2 * sum_{d<=sqrt(X)} (Y/d + 1)`, `sum_pow_weight_middle_window_le` bounds the geometric window weight, `sum_weighted_middle_window_le` bounds the whole weighted middle total along the progression, `exists_le_div_of_sum_le` is the pigeonhole selector, and `exists_first_block_progression_with_selected_weighted_middle` composes everything: unconditionally, for every `b >= 2`, window shape `(K, L)`, and `Y > 0`, the CRT progression carries first-block divisibility and some member `y < Y` whose weighted middle sum is at most the elementary divisor-pair average `(b^(L-K) * 2 * sum_{d<=sqrt(x+Y*A+L)} (Y/d + 1)) / Y` — the divisor-average-in-progressions half of Erdos 1948, in certificate shape. Size control and parameter closure are discharged in the next entry.",
            "- Certificate existence and full-support irrationality are now Lean-checked: `exists_bertrand_prime_block` chains Bertrand's postulate (`Nat.exists_prime_lt_and_le_two_mul`, no prime-counting input) into `r` distinct primes in `(m, 2^r * m]`, `exists_bounded_disjoint_prime_blocks` stacks those intervals into a triangular family of pairwise disjoint prime blocks below the explicit ceiling `2^(K(K+1)) * (L+1)`, `exists_bounded_crt_residue` is the normalised simultaneous CRT — the residue stays below the product of the moduli, and old congruences transfer by divisibility instead of by growing the representative — and `exists_bounded_first_block_frame` composes them into the height-aware frame: `x < A`, `L + 1 <= A`, exposed modulus support, first-block divisibility along the whole progression, and the explicit bound `A <= (2^(K(K+1)) * (L+1))^(b*K^2)`. Disjoint Bertrand blocks replace `fresh prime above the accumulated modulus`, which is exactly what makes the far-tail term `N + L + 2` controllable. `harmonic_div_sum_core` and `harmonic_div_sum_le` compress the raw divisor-pair average to `sum_{d<=S} (Y/d + 1) <= Y*(J+1) + S` for `S <= 2^J` by dyadic buckets, `selected_weighted_middle_of_supported_frame` frees the middle-window selector to consume any externally supplied supported frame, `param_linear_le_two_pow` and `certificate_param_arithmetic` close the parameters at `K = 9*(q+b+100)` and `L = 2^kappa` (everything reduces to `n < 2^n` plus exponent bookkeeping — no logarithms, no analytic input), and `exists_weighted_block_certificates` produces, for every base `b >= 2` and every precision `q > 0`, a weighted divisor block certificate `(N, K, L, C)` with first-block divisibility, weighted middle sum at most `C`, and `q * (C + (N+L+2)) < b^L`. Composing through the landed weighted closure, `irrational_erdosSum_full_support` proves that for every `b >= 2` the series `sum_{n>=1} 1/(b^n - 1)` is irrational — Erdos's 1948 full-support theorem, machine-checked end to end — and `irrational_erdosBorwein_series` is the literal base-2 instance: the Erdos-Borwein constant is irrational.",
            "",
            "## Explicit Non-Claims",
            "",
            "- This is not a primitive-divisor (Zsigmondy) existence proof: witnesses are prime powers, never guaranteed primitive primes.",
            "- This is not arbitrary generated-row existence.",
            "- This is not a solution of Erdos #257.",
            "- This is not an arbitrary-support irrationality theorem: the Lean-checked series cover the full support `A = N` (every base `b >= 2`) and specific lacunary supports (factorial and geometric); the universal Erdos #257 question over every infinite support remains open.",
            "- This is not publication authority.",
            "",
            "## Receipt Refs",
            "",
            f"- Target-runner receipt: `{receipt_path.as_posix()}`",
            f"- Strike state: `{strike.STRIKE_PATH.as_posix()}`",
            f"- Generated certificates: `{strike.DIRECT_PRIME_GENERATED_LEAN_MODULE.as_posix()}`",
            f"- Claim boundary: `{receipt.get('claim_boundary')}`",
            "",
        ]
    )


def _receipt_current(existing: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    keys = [
        "status",
        "audit_mode",
        "target_count",
        "target_theorem",
        "target_check_status",
        "print_axioms_status",
        "axiom_dependency_class",
        "axiom_dependencies",
        "custom_axiom_dependencies",
        "sorry_like_axiom_dependency_detected",
        "all_targets_foundational_or_none",
        "targets",
        "generated_certificate_shard_manifest_ref",
        "generated_certificate_shard_candidate",
        "generated_certificate_shard_module_path",
        "expected_new_target_count",
        "target_count_matches_manifest",
        "active_shard_count",
        "active_shards",
        "expected_active_shard_target_count",
        "target_count_matches_active_shards",
        "certificate_kernel_targets",
        "target_count_matches_certificate_kernel_list",
    ]
    return all(existing.get(key) == current.get(key) for key in keys)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=None)
    parser.add_argument(
        "--from-frontier-conveyor-receipt",
        action="store_true",
        help=(
            "Audit every bind_semantic_spec period theorem named by the latest "
            "frontier conveyor receipt."
        ),
    )
    parser.add_argument(
        "--from-generated-certificate-shard-manifest",
        action="store_true",
        help=(
            "Audit every declaration emitted by the generated-certificate "
            "shard manifest."
        ),
    )
    parser.add_argument(
        "--from-active-generated-shards",
        action="store_true",
        help=(
            "Audit every declaration emitted by every active generated "
            "certificate shard imported by the aggregate module."
        ),
    )
    parser.add_argument(
        "--from-certificate-kernel-targets",
        action="store_true",
        help="Audit the explicit hand-written CertificateKernel theorem target set.",
    )
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)

    from_frontier_conveyor_receipt = bool(args.from_frontier_conveyor_receipt)
    from_generated_certificate_shard_manifest = bool(
        args.from_generated_certificate_shard_manifest
    )
    from_active_generated_shards = bool(args.from_active_generated_shards)
    from_certificate_kernel_targets = bool(args.from_certificate_kernel_targets)
    selected_receipt_ref = (
        CERTIFICATE_KERNEL_RECEIPT_PATH
        if from_certificate_kernel_targets
        else RECEIPT_PATH
    )
    selected_packet_ref = (
        CERTIFICATE_KERNEL_PUBLIC_PACKET_PATH
        if from_certificate_kernel_targets
        else PUBLIC_PACKET_PATH
    )
    receipt_path = _repo_path(selected_receipt_ref)
    packet_path = _repo_path(selected_packet_ref)
    existing = _read_json(receipt_path) if receipt_path.exists() else {}
    if (
        args.check
        and not args.target
        and not from_generated_certificate_shard_manifest
        and not from_active_generated_shards
        and not from_certificate_kernel_targets
        and existing.get("audit_mode") == "frontier_conveyor_applied_direct_targets"
    ):
        from_frontier_conveyor_receipt = True
    if (
        args.check
        and not args.target
        and not from_frontier_conveyor_receipt
        and not from_active_generated_shards
        and not from_certificate_kernel_targets
        and existing.get("audit_mode")
        == "generated_certificate_shard_manifest_targets"
    ):
        from_generated_certificate_shard_manifest = True
    if (
        args.check
        and not args.target
        and not from_frontier_conveyor_receipt
        and not from_generated_certificate_shard_manifest
        and not from_certificate_kernel_targets
        and existing.get("audit_mode") == ACTIVE_GENERATED_SHARD_AUDIT_MODE
    ):
        from_active_generated_shards = True
    if (
        args.check
        and not args.target
        and not from_frontier_conveyor_receipt
        and not from_generated_certificate_shard_manifest
        and not from_active_generated_shards
        and existing.get("audit_mode") == CERTIFICATE_KERNEL_AUDIT_MODE
    ):
        from_certificate_kernel_targets = True
    receipt = (
        build_receipt_from_frontier_conveyor_receipt(
            skip_build=args.skip_build,
            timeout_seconds=args.timeout_seconds,
        )
        if from_frontier_conveyor_receipt
        else build_receipt_from_active_generated_certificate_shards(
            skip_build=args.skip_build,
            timeout_seconds=args.timeout_seconds,
        )
        if from_active_generated_shards
        else build_receipt_from_certificate_kernel_targets(
            skip_build=args.skip_build,
            timeout_seconds=args.timeout_seconds,
        )
        if from_certificate_kernel_targets
        else build_receipt_from_generated_certificate_shard_manifest(
            skip_build=args.skip_build,
            timeout_seconds=args.timeout_seconds,
        )
        if from_generated_certificate_shard_manifest
        else build_receipt(
            target_theorem=args.target,
            skip_build=args.skip_build,
            timeout_seconds=args.timeout_seconds,
        )
    )
    receipt_current = _receipt_current(existing, receipt) if existing else False
    check_payload = {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if receipt["status"] == "PASS" and (not args.check or receipt_current) else "FAIL",
        "receipt_status": receipt["status"],
        "receipt_current": receipt_current,
        "audit_mode": receipt.get("audit_mode"),
        "target_count": receipt.get("target_count"),
        "all_targets_foundational_or_none": receipt.get(
            "all_targets_foundational_or_none"
        ),
        "target_count_matches_manifest": receipt.get("target_count_matches_manifest"),
        "target_count_matches_active_shards": receipt.get(
            "target_count_matches_active_shards"
        ),
        "active_shard_count": receipt.get("active_shard_count"),
        "target_count_matches_certificate_kernel_list": receipt.get(
            "target_count_matches_certificate_kernel_list"
        ),
        "timeout_seconds": args.timeout_seconds,
        "generated_certificate_shard_candidate": receipt.get(
            "generated_certificate_shard_candidate"
        ),
        "target_theorem": receipt["target_theorem"],
        "receipt_ref": selected_receipt_ref.as_posix(),
        "public_packet_ref": selected_packet_ref.as_posix(),
        "claim_boundary": CLAIM_BOUNDARY,
    }

    if args.write:
        receipt = _with_receipt_lineage(receipt, existing)
        _write_json(receipt_path, receipt)
        _write_text(packet_path, build_public_packet(receipt, receipt_path=selected_receipt_ref))
        check_payload["status"] = "PASS" if receipt["status"] == "PASS" else "FAIL"
        check_payload["receipt_current"] = True

    output = check_payload if args.check else receipt
    if args.json or args.check:
        print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(f"{output['status']} {receipt['target_theorem']}")
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
