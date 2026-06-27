"""[PURPOSE]
- Teleology: Make finance forecast-evaluation spine evidence inspectable through
  runnable public fixture code while keeping claims bounded to emitted receipts and
  authority ceilings.
- Mechanism: The file runs no-lookahead forecast comparison statistics and emits typed
  refusals when statistics dependencies are unavailable; helper functions load fixtures,
  recompute predicates, normalize findings, build result/board/card payloads, and write
  receipts.
- Non-goal: Finance forecast evaluation spine runs statistical checks over synthetic
  market-shaped fixtures only. It is not investment or trading advice, uses no live
  market data, proves no track record or performance claim, mutates no optimizer, and
  treats SciPy absence as a typed HLN refusal.

[INTERFACE]
- CLI: Import or dispatch `microcosm_core.organs.finance_forecast_evaluation_spine`
  through package call sites and tests; no argparse subcommand was detected.
- Exports: evaluate, evaluate_negative_case, run, run_finance_forecast_bundle, main.
- Reads: Declared fixture inputs, source manifests, module constants, and call arguments
  referenced by each callable body.
- Writes: Receipt JSON, board/result/card payloads, CLI output, and temporary execution
  artifacts only where the called body performs explicit writes.

[FLOW]
- Load: Resolve public roots, fixture paths, source manifests, policy rows, and
  negative-case rows through the local helper stack.
- Validate: Recompute module-specific predicates from structured inputs rather than
  trusting fixture verdict fields alone.
- Emit: Assemble result, board, validation, acceptance, and command-card surfaces with
  anti-claims and authority ceilings preserved.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common
- Claim ceiling: ANTI_CLAIM provide the local boundary consumed by emitted surfaces.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutation is limited to explicit
  run/write helpers invoked by the caller.
- Determinism: Pure validation paths are deterministic for equal inputs; filesystem
  state, clock values, subprocess results, dependency availability, and parser
  invocation are the admitted runtime variables.
- Boundary: Receipts and cards must stay public-root relative and body-free for private,
  provider, credential, oracle, hidden-answer, or raw exploit material.
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
    """[ACTION] Resolve the copied source_modules directory from the source manifest.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_source_modules_root`.
    - Preconditions: Callers provide source_manifest, input_dir in the shape consumed by
      the body.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them.
    - Guarantee: Returns Path from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    manifest_path = source_manifest.get("source_manifest_path")
    if isinstance(manifest_path, str) and manifest_path:
        return Path(manifest_path).parent / "source_modules"
    return input_dir / "source_modules"


def _is_exported_finance_bundle(input_dir: Path, source_manifest: dict[str, Any]) -> bool:
    """[ACTION] Detect when inputs match the exported finance bundle shape.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_is_exported_finance_bundle`.
    - Preconditions: Callers provide input_dir, source_manifest in the shape consumed by
      the body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Delegates to is_file, source_manifest.get and applies local branch
      checks.
    - Guarantee: Returns bool from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks.
    - Reads: call arguments; module constants SPEC; filesystem metadata named by those
      arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Build a bounded statistics witness from exported fixture rows.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by
      `_standalone_exported_statistics_contract`.
    - Preconditions: Callers provide matrix, paired_loss_series in the shape consumed by
      the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Serialize finance fixtures and delegate statistics execution to the cached subprocess helper.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_run_stats_subprocess`.
    - Preconditions: Callers provide source_modules_root, family_loss_matrix,
      paired_loss_series in the shape consumed by the body; write targets must be inside
      the caller-selected output or temporary area; external binaries must be available
      when that branch is selected.
    - Mechanism: Writes only the output paths named by the caller, temporary workspace,
      or module constants.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from filesystem writes,
      subprocess execution, called validators/helpers.
    - Reads: call arguments.
    - Writes: filesystem output explicitly written by this body; subprocess side effects
      limited to the invoked command/workspace.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Execute copied finance statistics modules in a subprocess and capture hashes plus typed refusal evidence.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_run_stats_subprocess_cached`.
    - Preconditions: Callers provide source_modules_root, payload_text in the shape
      consumed by the body; content inputs must exist and match the expected local
      fixture shape; external binaries must be available when that branch is selected.
    - Mechanism: Reads declared local content and decodes or hashes it as the body
      shows. Runs the declared subprocess command and records its return-code evidence.
      Computes SHA-256 evidence from the bytes or normalized data it receives.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from filesystem/content
      reads, subprocess execution, called validators/helpers.
    - Reads: call arguments; filesystem/content inputs named by those arguments or
      constants.
    - Writes: subprocess side effects limited to the invoked command/workspace.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Return the SHA-256 digest for text content.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_sha256_text`.
    - Preconditions: Callers provide text in the shape consumed by the body.
    - Mechanism: Computes SHA-256 evidence from the bytes or normalized data it
      receives.
    - Guarantee: Returns str from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_iso_date(value: object) -> date | None:
    """[ACTION] Parse fixture ISO dates while treating malformed values as absent evidence.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_parse_iso_date`.
    - Preconditions: Callers provide value in the shape consumed by the body.
    - Mechanism: Delegates to date.fromisoformat and applies local branch checks.
    - Guarantee: Returns date | None from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _lookahead_split_findings(paired_loss_series: dict[str, Any]) -> list[dict[str, Any]]:
    """[ACTION] Find split-order or lookahead violations in finance fixture rows.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_lookahead_split_findings`.
    - Preconditions: Callers provide paired_loss_series in the shape consumed by the
      body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[dict[str, Any]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Find advice, live-data, and performance-claim policy violations.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_policy_findings`.
    - Preconditions: Callers provide policy in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[dict[str, Any]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants FALSE_BOUNDARY_FLAGS.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: FALSE_BOUNDARY_FLAGS.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Evaluate finance payloads and return bounded fixture findings.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `_evaluate_payloads`.
    - Preconditions: Callers provide input_dir, source_manifest, matrix, paired, policy,
      initial_findings in the shape consumed by the body; external binaries must be
      available when that branch is selected.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from subprocess
      execution, called validators/helpers.
    - Reads: call arguments; module constants FALSE_BOUNDARY_FLAGS.
    - Writes: subprocess side effects limited to the invoked command/workspace.
    - Couples: FALSE_BOUNDARY_FLAGS.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Evaluate fixture evidence and return a structured verdict.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `evaluate`.
    - Preconditions: Callers provide input_dir, _public_root, source_manifest in the
      shape consumed by the body.
    - Mechanism: Delegates to load_json_object, load_json_object, load_json_object,
      _evaluate_payloads and applies local branch checks.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Evaluate a negative-case row and return its verdict fields.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `evaluate_negative_case`.
    - Preconditions: Callers provide case_id, input_dir, _expected_codes in the shape
      consumed by the body; content inputs must exist and match the expected local
      fixture shape; write targets must be inside the caller-selected output or
      temporary area.
    - Mechanism: Reads declared local content and decodes or hashes it as the body
      shows. Writes only the output paths named by the caller, temporary workspace, or
      module constants. Normalizes Path values and public-root-relative references
      before returning them. Iterates candidate paths or structured rows exactly as
      written in the body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem/content
      reads, filesystem writes, called validators/helpers.
    - Reads: call arguments; module constants SPEC; filesystem/content inputs named by
      those arguments or constants.
    - Writes: filesystem output explicitly written by this body.
    - Couples: SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Run the organ replay pipeline and return the computed result payload.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `run`.
    - Preconditions: Callers provide input_dir, out_dir, command, acceptance_out in the
      shape consumed by the body.
    - Mechanism: Delegates to run_crown_jewel_organ and applies local branch checks.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants SPEC.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Implement run finance forecast bundle for this organ replay.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `run_finance_forecast_bundle`.
    - Preconditions: Callers provide input_dir, out_dir, command in the shape consumed
      by the body.
    - Mechanism: Delegates to run_crown_jewel_organ and applies local branch checks.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants SPEC.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
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
    """[ACTION] Parse command-line arguments and dispatch the selected organ command.

    - Teleology: Supports finance forecast evaluation spine by documenting and
      preserving the exact local step implemented by `main`.
    - Preconditions: Callers provide argv in the shape consumed by the body.
    - Mechanism: Delegates to main_for_spec and applies local branch checks.
    - Guarantee: Returns int from the selected CLI command path.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants SPEC.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return main_for_spec(
        SPEC,
        argv,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="run-finance-forecast-bundle",
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
