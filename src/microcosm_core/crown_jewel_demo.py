"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.crown_jewel_demo` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, RECEIPT_NAME, ANTI_CLAIM, MICROCOSM_ROOT, DEFAULT_OUT, run, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.macro_tools, microcosm_core.organs, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from microcosm_core.macro_tools import command_output_sidecar, work_landing_control_spine
from microcosm_core.organs import (
    agent_closeout_faithfulness_audit,
    bounded_autonomy_campaign_packet,
    doctrine_fact_claim_audit,
    durable_agent_work_landing_replay,
    finance_forecast_evaluation_spine,
    self_ignorance_coverage_ledger,
)
from microcosm_core.receipts import utc_now, write_json_atomic


SCHEMA_VERSION = "microcosm_crown_jewel_demo_receipt_v1"
RECEIPT_NAME = "crown_jewel_demo_receipt.json"
ANTI_CLAIM = (
    "The component substance demo runs public fixture exercises and runtime-safety "
    "checks only. It does not claim production release, live market data, "
    "investment advice, provider execution, full concurrent-mutation "
    "protection, source mutation authority, or private-root equivalence."
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = MICROCOSM_ROOT / "receipts/first_wave/crown_jewel_demo"


def _sha256_json(payload: object) -> str:
    """
    [ACTION]
    Stable content digest of a JSON-able payload for receipt fingerprinting.

    - Teleology: give each organ/runtime result a deterministic identity in the receipt without inlining its body.
    - Guarantee: returns the hex SHA-256 of the canonically serialized (sort_keys, str-coerced) payload; identical payloads yield identical digests.
    - Fails: never raises for JSON-able input; non-serializable objects fall back to `str()` via `default=str` rather than erroring.
    - Reads: nothing on disk; hashes only the in-memory payload.
    - Non-goal: does not authorize source-body export, public-safe equivalence, release, or whole-system correctness; it is a fingerprint only.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str | None:
    """
    [ACTION]
    Hex SHA-256 of a written artifact, used to fingerprint sidecar output in the receipt.

    - Teleology: bind a receipt row to the exact bytes of an emitted file without copying its contents into the receipt.
    - Guarantee: returns the hex SHA-256 of the file's bytes when `path` is a regular file; returns None when it is missing or not a file.
    - Fails: never raises for the missing-file case; returns None instead. Read errors on an existing file (permissions/IO) propagate as OSError.
    - Reads: the bytes at `path` (a generated sidecar/receipt artifact).
    - Non-goal: does not authorize source-body export, public-safe equivalence, or release; it only fingerprints already-emitted output.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    """
    [ACTION]
    Render a path as a microcosm-root-relative posix ref for portable receipt refs.

    - Teleology: keep receipt path refs root-relative and host-agnostic so they do not leak the absolute private filesystem layout.
    - Guarantee: returns the posix path relative to MICROCOSM_ROOT when `path` is under it; otherwise returns the path's own posix form unchanged.
    - Fails: never raises; the out-of-root case is caught (ValueError) and falls back to `path.as_posix()`.
    - Reads: only the in-memory path plus MICROCOSM_ROOT; no filesystem read (resolve uses strict=False).
    - Non-goal: does not authorize release or guarantee the referenced path exists; it only normalizes the ref string.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    try:
        return path.resolve(strict=False).relative_to(MICROCOSM_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _organ_card(organ_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Compact one organ run's result into a body-free receipt card.

    - Teleology: project a verbose organ result into a fixed-shape, fingerprint-only card for the crown-jewel receipt (no organ body inlined).
    - Guarantee: returns a dict carrying organ_id, the organ's reported status, receipt_refs, a result_digest over (status/exercise/source_module_status/observed_negative_cases), negative-case count, missing_negative_cases, anti_claim, and `body_in_receipt: False`.
    - Fails: never raises; missing keys default via `.get(...)` (status None, empty lists), so a partial result still yields a well-formed card.
    - Reads: only the in-memory `result` dict from the organ runner; no disk read.
    - Escalates-to: the underlying organ runner's own receipt under out_dir/organs/<organ_id> for full-fidelity status and negative cases.
    - Non-goal: does not validate or re-run the organ; it transcribes whatever the runner reported and authorizes no release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    receipt_refs = [str(ref) for ref in result.get("receipt_paths", [])]
    return {
        "organ_id": organ_id,
        "status": result.get("status"),
        "receipt_refs": receipt_refs,
        "result_digest": _sha256_json(
            {
                "status": result.get("status"),
                "exercise": result.get("exercise", {}),
                "source_module_status": (
                    result.get("source_module_manifest", {}).get("status")
                    if isinstance(result.get("source_module_manifest"), dict)
                    else None
                ),
                "observed_negative_cases": result.get("observed_negative_cases", []),
            }
        ),
        "observed_negative_case_count": len(result.get("observed_negative_cases", [])),
        "missing_negative_cases": result.get("missing_negative_cases", []),
        "anti_claim": result.get("anti_claim"),
        "body_in_receipt": False,
    }


def _run_organ(
    *,
    organ_id: str,
    input_ref: str,
    out_dir: Path,
    runner: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    Run one selected organ on its public example bundle and return its receipt card.

    - Teleology: the single per-organ execution seam — resolve the example input under root, invoke the organ's runner into a per-organ out dir, and card the result.
    - Guarantee: invokes `runner(MICROCOSM_ROOT/input_ref, out_dir/organs/organ_id)` and returns its `_organ_card`; the runner writes its own receipts under that out dir.
    - Fails: a missing/invalid bundle or a runner exception propagates from `runner` (this wrapper adds no catch); a non-"pass" organ status surfaces in the returned card's `status`.
    - When-needed: when adding/exercising one organ in the demo or tracing a single organ's status independent of the full run.
    - Escalates-to: `_organ_card` for card shape and the organ runner's receipts under out_dir/organs/<organ_id> for full fidelity.
    - Non-goal: does not aggregate pass/blocked across organs (that is `run`) and authorizes no release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result = runner(MICROCOSM_ROOT / input_ref, out_dir / "organs" / organ_id)
    return _organ_card(organ_id, result)


def _runtime_safety_checks(out_dir: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    Exercise the three runtime-safety containment probes and return their receipt cards.

    - Teleology: prove bounded runtime behavior (durable work-landing replay, command-output sidecar containment, work-landing control validation) alongside the organ set, body-free.
    - Guarantee: returns a 3-element list of body-free check cards (durable_agent_work_landing_replay, command_output_sidecar, work_landing_control_spine), each with status, receipt ref(s), and a digest; the control-spine check captures its redirected stdout digest and flags `known_blocker` when its status != "pass".
    - Fails: never returns partial silently for a card whose probe returns a dict; a probe raising (missing bundle/IO) propagates. The control-spine probe's own non-pass is recorded as a known blocker, not an exception.
    - When-needed: when verifying the demo's runtime-safety surface or diagnosing why the crown-jewel run reports a runtime hard failure vs. a known blocker.
    - Escalates-to: receipts under out_dir/runtime_safety/* and the sidecar workspace under out_dir/sidecar_workspace for each probe's full output.
    - Non-goal: does not prove full concurrent-mutation protection or production safety; each card's anti_claim bounds the proof to the fixture, and it authorizes no release.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    checks: list[dict[str, Any]] = []
    durable_result = durable_agent_work_landing_replay.run_work_landing_bundle(
        MICROCOSM_ROOT
        / "examples/durable_agent_work_landing_replay/exported_work_landing_replay_bundle",
        out_dir / "runtime_safety/durable_agent_work_landing_replay",
        command="microcosm crown-jewel-demo run",
    )
    checks.append(
        {
            "check_id": "durable_agent_work_landing_replay",
            "status": durable_result.get("status"),
            "receipt_refs": durable_result.get("receipt_paths", []),
            "digest": _sha256_json(
                {
                    "status": durable_result.get("status"),
                    "run_count": durable_result.get("run_count"),
                    "source_module_status": durable_result.get("source_module_imports", {}).get("status")
                    if isinstance(durable_result.get("source_module_imports"), dict)
                    else None,
                }
            ),
            "anti_claim": durable_result.get("anti_claim"),
            "body_in_receipt": False,
        }
    )

    sidecar_root = out_dir / "sidecar_workspace"
    sidecar_receipt = command_output_sidecar.maybe_route_to_sidecar(
        {
            "kind": "crown_jewel_demo_runtime_safety_probe",
            "schema_version": "crown_jewel_demo_runtime_safety_probe_v1",
            "summary": {"probe": "sidecar containment", "row_count": 2048},
            "rows": [{"row_id": f"row_{index:04d}", "value": index} for index in range(2048)],
        },
        surface="navigation_metabolism.full",
        repo_root=sidecar_root,
    )
    sidecar_path = (
        sidecar_root / str(sidecar_receipt.get("output_path"))
        if isinstance(sidecar_receipt, dict) and sidecar_receipt.get("output_path")
        else None
    )
    checks.append(
        {
            "check_id": "command_output_sidecar",
            "status": sidecar_receipt.get("status") if isinstance(sidecar_receipt, dict) else "not_written",
            "receipt_ref": _rel(sidecar_path) if sidecar_path else None,
            "digest": _file_digest(sidecar_path) if sidecar_path else None,
            "anti_claim": "Sidecar containment proves bounded output routing for this fixture only.",
            "body_in_receipt": False,
        }
    )

    control_stdout = io.StringIO()
    with contextlib.redirect_stdout(control_stdout):
        control_result = work_landing_control_spine.validate_work_landing_control_bundle(
            MICROCOSM_ROOT
            / "examples/work_landing_control_spine/exported_work_landing_control_bundle",
            out_dir / "runtime_safety/work_landing_control_spine",
            command="microcosm crown-jewel-demo run",
        )
    checks.append(
        {
            "check_id": "work_landing_control_spine",
            "status": control_result.get("status"),
            "receipt_refs": control_result.get("receipt_paths", []),
            "digest": _sha256_json(
                {
                    "status": control_result.get("status"),
                    "error_codes": control_result.get("error_codes", []),
                    "source_manifest_status": control_result.get("source_manifest", {}).get("status")
                    if isinstance(control_result.get("source_manifest"), dict)
                    else None,
                }
            ),
            "stdout_digest": hashlib.sha256(control_stdout.getvalue().encode("utf-8")).hexdigest(),
            "known_blocker": control_result.get("status") != "pass",
            "anti_claim": control_result.get("anti_claim"),
            "body_in_receipt": False,
        }
    )
    return checks


def run(out_dir: str | Path = DEFAULT_OUT, *, command: str = "microcosm crown-jewel-demo run") -> dict[str, Any]:
    """
    [ACTION]
    Execute the full component substance demo: five organs + runtime-safety checks under one receipt.

    - Teleology: the public board-emitter that runs the selected mechanism set end-to-end on public fixtures and writes one top-level pass/blocked receipt.
    - Guarantee: runs five organ runners and the three runtime-safety probes, atomically writes crown_jewel_demo_receipt.json at out_dir, and returns the receipt payload; `status` is "pass" iff no organ failed and no non-excused runtime hard failure occurred, else "blocked".
    - Fails: any organ/runtime probe raising (missing bundle/IO) propagates; otherwise never raises — a failing organ or hard runtime check yields `status: "blocked"` with `organ_failures`/`runtime_hard_failures` populated. The work_landing_control_spine check is excluded from hard failures and recorded as a known blocker.
    - Writes: crown_jewel_demo_receipt.json plus per-organ receipts under out_dir/organs/* and runtime receipts under out_dir/runtime_safety/* and out_dir/sidecar_workspace.
    - When-needed: demonstrating the selected organ set + runtime safety on public fixtures, or producing the receipt the CLI/main prints.
    - Escalates-to: SCHEMA_VERSION `microcosm_crown_jewel_demo_receipt_v1` receipt at receipt_ref; `_run_organ`/`_runtime_safety_checks` and their per-probe receipts for full fidelity.
    - Non-goal: per ANTI_CLAIM, does not claim production release, live market data, provider execution, full concurrent-mutation protection, source-mutation authority, or private-root equivalence.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    organs = [
        _run_organ(
            organ_id="agent_closeout_faithfulness_audit",
            input_ref=(
                "examples/agent_closeout_faithfulness_audit/"
                "exported_agent_closeout_faithfulness_audit_bundle"
            ),
            out_dir=out_path,
            runner=agent_closeout_faithfulness_audit.run_agent_closeout_bundle,
        ),
        _run_organ(
            organ_id="doctrine_fact_claim_audit",
            input_ref="examples/doctrine_fact_claim_audit/exported_doctrine_fact_claim_audit_bundle",
            out_dir=out_path,
            runner=doctrine_fact_claim_audit.run_doctrine_fact_bundle,
        ),
        _run_organ(
            organ_id="self_ignorance_coverage_ledger",
            input_ref=(
                "examples/self_ignorance_coverage_ledger/"
                "exported_self_ignorance_coverage_ledger_bundle"
            ),
            out_dir=out_path,
            runner=self_ignorance_coverage_ledger.run_self_ignorance_bundle,
        ),
        _run_organ(
            organ_id="bounded_autonomy_campaign_packet",
            input_ref=(
                "examples/bounded_autonomy_campaign_packet/"
                "exported_bounded_autonomy_campaign_packet_bundle"
            ),
            out_dir=out_path,
            runner=bounded_autonomy_campaign_packet.run_bounded_autonomy_bundle,
        ),
        _run_organ(
            organ_id="finance_forecast_evaluation_spine",
            input_ref="examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle",
            out_dir=out_path,
            runner=finance_forecast_evaluation_spine.run_finance_forecast_bundle,
        ),
    ]
    runtime_checks = _runtime_safety_checks(out_path)
    organ_failures = [row["organ_id"] for row in organs if row["status"] != "pass"]
    runtime_hard_failures = [
        row["check_id"]
        for row in runtime_checks
        if row["check_id"] != "work_landing_control_spine" and row["status"] != "pass" and row["status"] != "written_to_sidecar"
    ]
    receipt_path = out_path / RECEIPT_NAME
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "command": command,
        "status": "pass" if not organ_failures and not runtime_hard_failures else "blocked",
        "organ_count": len(organs),
        "organ_pass_count": len([row for row in organs if row["status"] == "pass"]),
        "organs": organs,
        "runtime_safety_check_count": len(runtime_checks),
        "runtime_safety_checks": runtime_checks,
        "runtime_safety_known_blocker_count": len(
            [row for row in runtime_checks if row.get("known_blocker")]
        ),
        "organ_failures": organ_failures,
        "runtime_hard_failures": runtime_hard_failures,
        "receipt_ref": _rel(receipt_path),
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }
    write_json_atomic(receipt_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entry for the component substance demo `run` subcommand.

    - Teleology: single public mechanism-set command that exercises five selected organs plus runtime-safety checks under one receipt.
    - Guarantee: on `run`, the demo executes, a receipt is printed, and exit code matches its pass/blocked status.
    - Fails: no/unknown subcommand -> argparse error -> SystemExit(2); any organ or hard runtime check fails -> status blocked -> return 1.
    - Reads: public example bundles under examples/ for each organ and runtime check.
    - Writes: crown_jewel_demo_receipt.json plus per-organ/runtime receipts under `--out` (default receipts/first_wave/crown_jewel_demo).
    - When-needed: demonstrating the curated organ set end-to-end on public fixtures.
    - Escalates-to: run, _runtime_safety_checks, the five organ runners.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """

    parser = argparse.ArgumentParser(prog="microcosm crown-jewel-demo")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    if args.action == "run":
        payload = run(args.out)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("status") == "pass" else 1
    parser.error("expected subcommand: run")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
