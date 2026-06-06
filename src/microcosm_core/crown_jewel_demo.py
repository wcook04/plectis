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
    "The Crown Jewel demo runs public fixture exercises and runtime-safety "
    "checks only. It does not claim production release, live market data, "
    "investment advice, provider execution, full concurrent-mutation "
    "protection, source mutation authority, or private-root equivalence."
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = MICROCOSM_ROOT / "receipts/first_wave/crown_jewel_demo"


def _sha256_json(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(MICROCOSM_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _organ_card(organ_id: str, result: dict[str, Any]) -> dict[str, Any]:
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
    result = runner(MICROCOSM_ROOT / input_ref, out_dir / "organs" / organ_id)
    return _organ_card(organ_id, result)


def _runtime_safety_checks(out_dir: Path) -> list[dict[str, Any]]:
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
