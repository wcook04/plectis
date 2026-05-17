"""Cold-clone bootstrap probe for the public microcosm root."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import run_scan
from microcosm_core.receipts import make_receipt, write_json


EXPECTED_WAVE_1 = [
    {
        "organ_id": "pattern_binding_contract",
        "required_paths": [
            "src/microcosm_core/organs/pattern_binding_contract.py",
            "core/fixture_manifests/pattern_binding_contract.fixture_manifest.json",
        ],
    },
    {
        "organ_id": "executable_doctrine_grammar",
        "required_paths": [
            "src/microcosm_core/organs/executable_doctrine_grammar.py",
            "core/fixture_manifests/executable_doctrine_grammar.fixture_manifest.json",
        ],
    },
    {
        "organ_id": "proof_diagnostic_evidence_spine",
        "required_paths": [
            "src/microcosm_core/organs/proof_diagnostic_evidence_spine.py",
            "core/fixture_manifests/proof_diagnostic_evidence_spine.fixture_manifest.json",
        ],
    },
    {
        "organ_id": "formal_math_lean_proof_organ",
        "required_paths": [
            "src/microcosm_core/organs/formal_math_lean_proof_organ.py",
            "formal_math/lean-toolchain",
        ],
    },
    {
        "organ_id": "navigation_hologram_route_plane",
        "required_paths": [
            "src/microcosm_core/organs/navigation_hologram_route_plane.py",
            "core/fixture_manifests/navigation_hologram_route_plane.fixture_manifest.json",
        ],
    },
    {
        "organ_id": "mission_transaction_work_spine",
        "required_paths": [
            "src/microcosm_core/organs/mission_transaction_work_spine.py",
            "core/fixture_manifests/mission_transaction_work_spine.fixture_manifest.json",
        ],
    },
    {
        "organ_id": "agent_route_observability_runtime",
        "required_paths": [
            "src/microcosm_core/organs/agent_route_observability_runtime.py",
            "core/fixture_manifests/agent_route_observability_runtime.fixture_manifest.json",
        ],
    },
]

ROOT_REQUIRED_PATHS = [
    "README.md",
    "AGENTS.md",
    "CONSTITUTION.md",
    "AXIOMS.md",
    "PRINCIPLES.md",
    "ANTI_PRINCIPLES.md",
    "pyproject.toml",
    "bootstrap.sh",
    "src/microcosm_core/__init__.py",
    "src/microcosm_core/receipts.py",
    "src/microcosm_core/private_state_scan.py",
    "src/microcosm_core/validators/private_state_scan.py",
    "core/private_state_forbidden_classes.json",
    "atlas/entry_packet.json",
]


def missing_paths(root: Path, paths: list[str]) -> list[str]:
    return [path for path in paths if not (root / path).exists()]


def first_missing_wave_1(root: Path) -> dict[str, Any] | None:
    for organ in EXPECTED_WAVE_1:
        missing = missing_paths(root, organ["required_paths"])
        if missing:
            return {
                "organ_id": organ["organ_id"],
                "missing_paths": missing,
                "error_class": "MISSING_WAVE_1_ORGAN",
                "unblock_condition": f"Implement {organ['organ_id']} with its fixture manifest, validator command, negative case, and receipt outputs.",
            }
    return None


def run_probe(suite: str, emit: Path) -> dict[str, Any]:
    root = Path.cwd()
    private_scan_path = root / "receipts/first_wave/private_state_scan.json"
    private_scan = run_scan(root)
    write_json(private_scan_path, private_scan)

    root_missing = missing_paths(root, ROOT_REQUIRED_PATHS)
    first_missing = None if root_missing else first_missing_wave_1(root)

    if private_scan["status"] != "pass":
        status = "fail"
        error_class = "PRIVATE_STATE_SCAN_FAILED"
    elif root_missing:
        status = "blocked"
        error_class = "MISSING_ROOT_FILE"
    elif first_missing:
        status = "blocked"
        error_class = first_missing["error_class"]
    else:
        status = "pass"
        error_class = None

    payload: dict[str, Any] = {
        "suite": suite,
        "root": str(root),
        "private_state_scan": {
            "status": private_scan["status"],
            "receipt_ref": str(private_scan_path.relative_to(root)),
            "forbidden_class_hit_count": len(private_scan.get("forbidden_class_hits", [])),
        },
        "root_required_paths": ROOT_REQUIRED_PATHS,
        "missing_root_paths": root_missing,
        "wave_1_expected_organs": [organ["organ_id"] for organ in EXPECTED_WAVE_1],
        "first_missing_organ_or_validator": first_missing,
        "receipt_refs": [
            str(emit),
            "receipts/first_wave/private_state_scan.json",
        ],
        "anti_claim": "This bootstrap proves the seed root can run and emit typed receipts; it does not prove Wave 1 organ acceptance until missing organs land.",
        "next_best_mission": "Implement pattern_binding_contract as the first Wave 1 organ with synthetic fixtures, expected negative cases, validator output, and receipts.",
    }
    if error_class:
        payload["error_class"] = error_class

    return make_receipt(
        receipt_type="cold_clone_probe",
        status=status,
        command=f"./bootstrap.sh --suite {suite} --emit {emit.as_posix()}",
        payload=payload,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the microcosm cold-clone bootstrap probe.")
    parser.add_argument("--suite", default="first-wave")
    parser.add_argument("--emit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.suite != "first-wave":
        receipt = make_receipt(
            receipt_type="cold_clone_probe",
            status="blocked",
            command=f"./bootstrap.sh --suite {args.suite} --emit {args.emit}",
            payload={
                "error_class": "UNKNOWN_SUITE",
                "suite": args.suite,
                "unblock_condition": "Use --suite first-wave or add a typed acceptance plan for the requested suite.",
            },
        )
        write_json(args.emit, receipt)
        return 1

    receipt = run_probe(args.suite, Path(args.emit))
    write_json(args.emit, receipt)
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

