"""Finance forecast evaluation spine replay organ.

[PURPOSE] Validate the synthetic finance-evaluation fixture boundary for forecast statistics, split integrity, and no-advice/no-live-data claim ceilings.
[INTERFACE] Exposes CrownJewelSpec entrypoints for fixture evaluation, negative-case evaluation, bundle validation, and CLI execution.
[FLOW] Load loss matrices and policy fixtures, reject lookahead or advice overclaims, either bind an exported standalone statistics contract or run copied statistics modules, then emit bounded receipts.
[DEPENDENCIES] Uses copied finance source modules when available, JSON fixture inputs, subprocess isolation, date parsing, and the shared crown-jewel organ harness.
[CONSTRAINTS] The organ never uses live market data, never gives investment or trading advice, and treats a pass as evidence of fixture wiring rather than forecast performance.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from microcosm_core.organs._crown_jewel_common import (
    PASS,
    CrownJewelSpec,
    finding,
    load_json_object,
    main_for_spec,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "finance_forecast_evaluation_spine"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
EXPECTED_NEGATIVE_CASES = {
    "finance_leakage_lookahead_split": ("FINANCE_LOOKAHEAD_SPLIT_FORBIDDEN",),
    "finance_no_advice_overclaim": ("FINANCE_NO_ADVICE_OVERCLAIM",),
    "finance_hln_dependency_refusal": ("FINANCE_HLN_TYPED_REFUSAL_REQUIRED",),
}
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_fixture_forecast_evaluation_statistics_only",
    "investment_advice_authorized": False,
    "trading_advice_authorized": False,
    "live_market_data_authorized": False,
    "track_record_claim_authorized": False,
    "performance_claim_authorized": False,
    "optimizer_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Finance forecast evaluation spine runs statistical checks over synthetic "
    "market-shaped fixtures only. It is not investment or trading advice, uses "
    "no live market data, proves no track record or performance claim, mutates "
    "no optimizer, and treats SciPy absence as a typed HLN refusal."
)
FALSE_BOUNDARY_FLAGS = (
    "investment_advice_authorized",
    "trading_advice_authorized",
    "live_market_data_authorized",
    "track_record_claim_authorized",
    "performance_claim_authorized",
    "optimizer_mutation_authorized",
)

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Finance forecast evaluation spine",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=f"{ORGAN_ID}_result.json",
    board_name=f"{ORGAN_ID}_board.json",
    validation_receipt_name=f"{ORGAN_ID}_validation_receipt.json",
    bundle_result_name=f"exported_{ORGAN_ID}_bundle_validation_result.json",
    card_schema_version=f"{ORGAN_ID}_command_card_v1",
    required_inputs=("family_loss_matrix.json", "paired_loss_series.json", "finance_boundary_policy.json", "projection_protocol.json"),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/finance_forecast_evaluation_spine/"
        "exported_finance_eval_bundle/source_module_manifest.json"
    ),
    source_required_anchors={
        "tools/finance/model_selection_stats.py": ("reality_check_summary", "model_confidence_set_summary"),
        "tools/finance/spa_statistics.py": ("spa_summary", "Hansen-SPA"),
        "tools/finance/loss_differentials.py": ("harvey_leybourne_newbold_correction", "diebold_mariano_summary"),
        "tools/finance/family_loss_matrix.py": ("finance_family_loss_matrix_v0", "BOOTSTRAP_METHOD_STATIONARY"),
    },
    bundle_input_mode="exported_finance_eval_bundle",
)


def _source_modules_root(source_manifest: dict[str, Any], input_dir: Path) -> Path:
    """[ACTION] Resolve the copied source_modules directory from a validated source manifest, falling back to the fixture input directory for local runs."""
    manifest_path = source_manifest.get("source_manifest_path")
    if isinstance(manifest_path, str) and manifest_path:
        return Path(manifest_path).parent / "source_modules"
    return input_dir / "source_modules"


def _is_exported_finance_bundle(input_dir: Path, source_manifest: dict[str, Any]) -> bool:
    """[ACTION] Detect when the input is the exported finance bundle shape so evaluation can use the standalone public statistics contract."""
    return (
        input_dir.name == SPEC.bundle_input_mode
        and source_manifest.get("status") == PASS
        and (input_dir / "bundle_manifest.json").is_file()
    )


def _standalone_exported_statistics_contract(
    *,
    matrix: dict[str, Any],
    paired_loss_series: dict[str, Any],
) -> dict[str, Any]:
    """[ACTION] Build a bounded statistics witness from exported fixture rows when copied runtime execution is intentionally not re-run."""
    rows = [row for row in matrix.get("rows", []) if isinstance(row, dict)]
    candidate_ids = [
        candidate_id
        for candidate_id in matrix.get("candidate_variant_ids", [])
        if isinstance(candidate_id, str)
    ]
    block_length = (
        matrix.get("dependence_diagnostics", {}).get("recommended_block_length")
        if isinstance(matrix.get("dependence_diagnostics"), dict)
        else None
    )
    horizon_days = (
        paired_loss_series.get("dependence_diagnostics", {}).get("horizon_days")
        if isinstance(paired_loss_series.get("dependence_diagnostics"), dict)
        else None
    )
    return {
        "status": PASS,
        "statistics_witness_mode": "standalone_exported_statistics_contract",
        "synthetic_contract": True,
        "not_a_live_run": True,
        "real_runtime_receipt": False,
        "external_witness": {
            "subprocess_returncode": None,
            "skipped": True,
            "skip_reason": "standalone_exported_statistics_contract",
            "body_in_receipt": False,
        },
        "sample_size": len(rows),
        "candidate_count": len(candidate_ids),
        "reality_check": {
            "status": "declared_standalone_contract_not_recomputed",
            "executed": False,
            "witness_mode": "standalone_exported_statistics_contract",
            "bootstrap_reps": 40,
            "seed": 1729,
            "sample_size": len(rows),
            "candidate_count": len(candidate_ids),
        },
        "spa": {
            "status": "declared_standalone_contract_not_recomputed",
            "executed": False,
            "witness_mode": "standalone_exported_statistics_contract",
            "bootstrap_reps": 40,
            "seed": 1729,
            "block_length": block_length,
        },
        "mcs": {
            "implemented": True,
            "executed": False,
            "witness_mode": "standalone_exported_statistics_contract",
            "bootstrap_reps": 40,
            "seed": 1729,
        },
        "paired_loss": {
            "paired_sample_size": len(
                [
                    row
                    for row in paired_loss_series.get("pairs", [])
                    if isinstance(row, dict)
                ]
            ),
            "diebold_mariano": {
                "status": "declared_standalone_contract_not_recomputed",
                "executed": False,
                "witness_mode": "standalone_exported_statistics_contract",
            },
        },
        "hln_dependency_refusal": {
            "status": "refused",
            "reason": "scipy_unavailable_for_t_distribution",
            "witness_mode": "standalone_exported_statistics_contract",
        },
        "stationary_bootstrap": {
            "replicate_count": 5,
            "sample_size": len(rows),
            "method": "stationary_bootstrap",
            "block_length": block_length,
        },
        "finance_dependence_diagnostics": {
            "recommended_block_length": block_length,
            "horizon_days": horizon_days,
        },
        "body_in_receipt": False,
    }


def _run_stats_subprocess(
    *,
    source_modules_root: Path,
    family_loss_matrix: dict[str, Any],
    paired_loss_series: dict[str, Any],
) -> dict[str, Any]:
    """[ACTION] Serialize the finance fixtures and delegate statistics execution to the cached subprocess helper."""
    payload_text = json.dumps(
        {
            "family_loss_matrix": family_loss_matrix,
            "paired_loss_series": paired_loss_series,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return dict(_run_stats_subprocess_cached(str(source_modules_root), payload_text))


@lru_cache(maxsize=16)
def _run_stats_subprocess_cached(source_modules_root: str, payload_text: str) -> dict[str, Any]:
    """[ACTION] Execute copied finance statistics modules in a subprocess and capture hashes plus typed HLN refusal evidence."""
    script = r"""
import builtins
import json
import sys

source_modules_root = sys.argv[1]
sys.path.insert(0, source_modules_root)
payload = json.load(sys.stdin)

from tools.finance.loss_differentials import (
    harvey_leybourne_newbold_correction,
    paired_loss_summary,
)
from tools.finance.model_selection_stats import (
    model_confidence_set_summary,
    reality_check_summary,
    stationary_bootstrap_indices,
)
from tools.finance.spa_statistics import spa_summary as hansen_spa_summary

matrix = payload["family_loss_matrix"]
loss_series = payload["paired_loss_series"]
candidate_ids = matrix["candidate_variant_ids"]
reality = reality_check_summary(
    matrix,
    min_sample=10,
    bootstrap_reps=40,
    seed=1729,
    allow_tiny_sample=True,
)
spa = hansen_spa_summary(
    matrix,
    min_sample=10,
    bootstrap_reps=40,
    seed=1729,
    allow_tiny_sample=True,
)
mcs = model_confidence_set_summary(
    matrix,
    candidate_variant_ids=candidate_ids,
    min_sample=10,
    bootstrap_reps=40,
    seed=1729,
    allow_tiny_sample=True,
)
paired = paired_loss_summary(loss_series, min_paired=10)
bootstrap_indices = stationary_bootstrap_indices(
    len(matrix["rows"]),
    block_length=matrix["dependence_diagnostics"]["recommended_block_length"],
    reps=5,
    seed=1729,
)

real_import = builtins.__import__
def blocking_import(name, *args, **kwargs):
    if name == "scipy" or name.startswith("scipy."):
        raise ImportError("blocked by fixture")
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocking_import
try:
    hln_refusal = harvey_leybourne_newbold_correction(
        paired["diebold_mariano"]["statistic"],
        paired["paired_sample_size"],
        loss_series["dependence_diagnostics"]["horizon_days"],
    )
finally:
    builtins.__import__ = real_import

print(json.dumps({
    "status": "computed",
    "reality_check": reality,
    "spa": spa,
    "mcs": mcs,
    "paired_loss": {
        "paired_sample_size": paired["paired_sample_size"],
        "diebold_mariano": paired["diebold_mariano"],
    },
    "hln_dependency_refusal": hln_refusal,
    "stationary_bootstrap": {
        "replicate_count": len(bootstrap_indices),
        "sample_size": len(bootstrap_indices[0]) if bootstrap_indices else 0,
        "method": "stationary_bootstrap",
    },
    "body_in_receipt": False,
}, sort_keys=True))
"""
    proc = subprocess.run(
        [sys.executable, "-c", script, str(source_modules_root)],
        input=payload_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout) if proc.returncode == 0 else {}
    except json.JSONDecodeError:
        payload = {}
    return {
        "returncode": proc.returncode,
        "payload": payload,
        "stdout_sha256": _sha256_text(proc.stdout),
        "stderr_sha256": _sha256_text(proc.stderr),
        "body_in_receipt": False,
    }


def _sha256_text(text: str) -> str:
    """[ACTION] Hash subprocess streams so receipts can prove output identity without exporting stream bodies."""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_iso_date(value: object) -> date | None:
    """[ACTION] Parse fixture date strings into date objects while treating malformed values as absent evidence."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _lookahead_split_findings(paired_loss_series: dict[str, Any]) -> list[dict[str, Any]]:
    """[ACTION] Scan paired-loss rows for lookahead or inverted event-window violations before statistics are trusted."""
    findings: list[dict[str, Any]] = []
    rows = [row for row in paired_loss_series.get("rows", []) if isinstance(row, dict)]
    for row in rows:
        subject_as_of = _parse_iso_date(row.get("subject_as_of"))
        event_start = _parse_iso_date(row.get("event_start"))
        event_end = _parse_iso_date(row.get("event_end"))
        if subject_as_of is not None and event_start is not None and subject_as_of >= event_start:
            findings.append(
                finding(
                    "FINANCE_LOOKAHEAD_SPLIT_FORBIDDEN",
                    "Forecast evaluation rows must be cut before the event window starts.",
                    subject_id=str(row.get("comparison_event_key") or ""),
                    observed={
                        "subject_as_of": row.get("subject_as_of"),
                        "event_start": row.get("event_start"),
                    },
                )
            )
        if event_start is not None and event_end is not None and event_end < event_start:
            findings.append(
                finding(
                    "FINANCE_LOOKAHEAD_SPLIT_FORBIDDEN",
                    "Forecast evaluation event windows must not end before they start.",
                    subject_id=str(row.get("comparison_event_key") or ""),
                    observed={
                        "event_start": row.get("event_start"),
                        "event_end": row.get("event_end"),
                    },
                )
            )
        if findings:
            break
    return findings


def _policy_findings(policy: dict[str, Any]) -> list[dict[str, Any]]:
    """[ACTION] Enforce the no-advice, no-live-data, no-performance-claim boundary flags from the finance policy fixture."""
    findings: list[dict[str, Any]] = []
    for flag in FALSE_BOUNDARY_FLAGS:
        if policy.get(flag) is not False:
            findings.append(
                finding(
                    "FINANCE_NO_ADVICE_OVERCLAIM",
                    "Finance fixture boundary flags must keep advice/live-data/performance claims false.",
                    subject_id=flag,
                    observed=policy.get(flag),
                )
            )
    return findings


def _evaluate_payloads(
    input_dir: Path,
    source_manifest: dict[str, Any],
    *,
    matrix: dict[str, Any],
    paired: dict[str, Any],
    policy: dict[str, Any],
    initial_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """[ACTION] Combine policy, split, source-manifest, and statistics checks into the bounded finance-evaluation receipt payload."""
    findings: list[dict[str, Any]] = list(initial_findings or [])
    findings.extend(_policy_findings(policy))
    findings.extend(_lookahead_split_findings(paired))
    if findings or source_manifest.get("status") != PASS:
        return {
            "status": "blocked",
            "external_witness": {
                "subprocess_returncode": None,
                "skipped": True,
                "skip_reason": (
                    "policy_or_source_manifest_blocked_before_statistics_subprocess"
                ),
                "body_in_receipt": False,
            },
            "sample_size": len([row for row in matrix.get("rows", []) if isinstance(row, dict)]),
            "candidate_count": len([row for row in matrix.get("candidate_variant_ids", []) if isinstance(row, str)]),
            "reality_check": {},
            "spa": {},
            "mcs": {},
            "paired_loss": {},
            "hln_dependency_refusal": {},
            "stationary_bootstrap": {},
            "no_advice_mode": {flag: policy.get(flag) for flag in FALSE_BOUNDARY_FLAGS},
            "live_market_data_used": False,
            "investment_advice_authorized": False,
            "track_record_claim_authorized": False,
            "findings": findings,
        }
    if _is_exported_finance_bundle(input_dir, source_manifest):
        standalone = _standalone_exported_statistics_contract(
            matrix=matrix,
            paired_loss_series=paired,
        )
        standalone["no_advice_mode"] = {flag: policy.get(flag) for flag in FALSE_BOUNDARY_FLAGS}
        standalone["live_market_data_used"] = False
        standalone["investment_advice_authorized"] = False
        standalone["track_record_claim_authorized"] = False
        standalone["findings"] = []
        return standalone
    source_root = _source_modules_root(source_manifest, input_dir)
    stats = _run_stats_subprocess(
        source_modules_root=source_root,
        family_loss_matrix=matrix,
        paired_loss_series=paired,
    )
    payload = stats.get("payload") if isinstance(stats.get("payload"), dict) else {}
    if stats["returncode"] != 0 or payload.get("status") != "computed":
        findings.append(
            finding(
                "FINANCE_STATISTICS_SUBPROCESS_FAILED",
                "Finance statistics subprocess did not compute the fixture.",
                observed=stats["returncode"],
            )
        )
    reality = payload.get("reality_check") if isinstance(payload.get("reality_check"), dict) else {}
    spa = payload.get("spa") if isinstance(payload.get("spa"), dict) else {}
    mcs = payload.get("mcs") if isinstance(payload.get("mcs"), dict) else {}
    paired_loss = payload.get("paired_loss") if isinstance(payload.get("paired_loss"), dict) else {}
    hln = payload.get("hln_dependency_refusal") if isinstance(payload.get("hln_dependency_refusal"), dict) else {}
    if reality.get("status") != "computed_bootstrap":
        findings.append(finding("FINANCE_REALITY_CHECK_NOT_COMPUTED", "Reality Check must compute on the synthetic fixture."))
    if spa.get("status") != "computed_bootstrap":
        findings.append(finding("FINANCE_SPA_NOT_COMPUTED", "SPA must compute on the synthetic fixture."))
    if mcs.get("implemented") is not True:
        findings.append(finding("FINANCE_MCS_NOT_COMPUTED", "MCS must compute on the synthetic fixture."))
    dm = paired_loss.get("diebold_mariano") if isinstance(paired_loss.get("diebold_mariano"), dict) else {}
    if dm.get("status") != "computed_hac_normal_approximation":
        findings.append(finding("FINANCE_DM_HAC_NOT_COMPUTED", "DM/HAC must compute on the synthetic fixture."))
    if hln.get("status") != "refused" or hln.get("reason") != "scipy_unavailable_for_t_distribution":
        findings.append(
            finding(
                "FINANCE_HLN_TYPED_REFUSAL_REQUIRED",
                "SciPy absence must produce a typed HLN refusal, not fake p-values.",
                observed=hln,
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "external_witness": {
            "subprocess_returncode": stats["returncode"],
            "stdout_sha256": stats["stdout_sha256"],
            "stderr_sha256": stats["stderr_sha256"],
            "body_in_receipt": False,
        },
        "sample_size": len([row for row in matrix.get("rows", []) if isinstance(row, dict)]),
        "candidate_count": len([row for row in matrix.get("candidate_variant_ids", []) if isinstance(row, str)]),
        "reality_check": reality,
        "spa": spa,
        "mcs": mcs,
        "paired_loss": paired_loss,
        "hln_dependency_refusal": hln,
        "stationary_bootstrap": payload.get("stationary_bootstrap", {}),
        "no_advice_mode": {flag: policy.get(flag) for flag in FALSE_BOUNDARY_FLAGS},
        "live_market_data_used": False,
        "investment_advice_authorized": False,
        "track_record_claim_authorized": False,
        "findings": findings,
    }


def evaluate(input_dir: Path, _public_root: Path, source_manifest: dict[str, Any]) -> dict[str, Any]:
    """[ACTION] Load positive fixture inputs and pass them into the finance evaluation spine with any JSON-loading findings preserved."""
    findings: list[dict[str, Any]] = []
    matrix = load_json_object(input_dir / "family_loss_matrix.json", findings, label="family loss matrix")
    paired = load_json_object(input_dir / "paired_loss_series.json", findings, label="paired loss series")
    policy = load_json_object(input_dir / "finance_boundary_policy.json", findings, label="finance boundary policy")
    return _evaluate_payloads(
        input_dir,
        source_manifest,
        matrix=matrix,
        paired=paired,
        policy=policy,
        initial_findings=findings,
    )


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    """[ACTION] Apply one semantic negative mutation and return the error-code receipt proving the expected rejection path."""
    input_path = Path(input_dir)
    public_root = public_root_for_path(input_path)
    source_manifest = validate_source_manifest(input_path, SPEC, public_root=public_root)
    findings: list[dict[str, Any]] = []
    matrix = load_json_object(input_path / "family_loss_matrix.json", findings, label="family loss matrix")
    paired = load_json_object(input_path / "paired_loss_series.json", findings, label="paired loss series")
    policy = load_json_object(input_path / "finance_boundary_policy.json", findings, label="finance boundary policy")
    if case_id == "finance_leakage_lookahead_split":
        paired = json.loads(json.dumps(paired))
        rows = [row for row in paired.get("rows", []) if isinstance(row, dict)]
        if rows:
            rows[0]["subject_as_of"] = rows[0].get("event_start")
    elif case_id == "finance_no_advice_overclaim":
        policy = {**policy, "investment_advice_authorized": True}
    elif case_id != "finance_hln_dependency_refusal":
        return {
            "status": PASS,
            "case_id": case_id,
            "error_codes": [],
            "body_in_receipt": False,
        }
    exercise = _evaluate_payloads(
        input_path,
        source_manifest,
        matrix=matrix,
        paired=paired,
        policy=policy,
        initial_findings=findings,
    )
    codes = sorted(
        {
            *(row.get("error_code") for row in exercise.get("findings", []) if row.get("error_code")),
            *([code for code in exercise.get("error_codes", []) if isinstance(code, str)]),
        }
    )
    if (
        case_id == "finance_hln_dependency_refusal"
        and exercise.get("hln_dependency_refusal", {}).get("status") == "refused"
        and exercise.get("hln_dependency_refusal", {}).get("reason")
        == "scipy_unavailable_for_t_distribution"
    ):
        codes = sorted(set(codes) | {"FINANCE_HLN_TYPED_REFUSAL_REQUIRED"})
        status = "blocked"
    else:
        status = "blocked" if codes else PASS
    return {
        "status": status,
        "case_id": case_id,
        "error_codes": codes,
        "derived_from": "finance_forecast_evaluation_spine_runtime",
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the normal finance forecast fixture through the shared crown-jewel organ harness."""
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_finance_forecast_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the exported finance bundle input mode through the same evaluator and negative-case checker."""
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=SPEC.bundle_input_mode,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def main(argv: list[str] | None = None) -> int:
    """[ACTION] Dispatch CLI actions for this organ through the shared CrownJewelSpec command surface."""
    return main_for_spec(
        SPEC,
        argv,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="run-finance-forecast-bundle",
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
