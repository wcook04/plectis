from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from microcosm_core import release_impressiveness_compiler
from microcosm_core.receipts import utc_now, write_json_atomic


PASS = "pass"
BLOCKED = "blocked"

RECEIPT_SCHEMA = "microcosm_release_activation_rehearsal_receipt_v1"
CARD_SCHEMA = "microcosm_cold_reader_activation_card_v1"
DEFAULT_MINIMUM_ACTIVATION_MATURITY = 2

ACTION_HINTS: dict[str, dict[str, str]] = {
    "proof_formal_kernel": {
        "action_type": "run",
        "command": "microcosm trace-lens",
        "view_ref": "/trace",
        "expected_schema": "microcosm_public_verifier_trace_repair_lens_v1",
    },
    "prover_evaluator_lab": {
        "action_type": "run",
        "command": "microcosm benchmark-lab",
        "view_ref": "/benchmark-lab",
        "expected_schema": "microcosm_public_repository_benchmark_transaction_lab_lens_v1",
    },
    "work_landing_governance": {
        "action_type": "run",
        "command": "microcosm landing-replay",
        "view_ref": "/landing-replay",
        "expected_schema": "microcosm_public_work_landing_replay_lens_v1",
    },
    "navigation_option_surface": {
        "action_type": "inspect",
        "command": "microcosm projection-import-map",
        "view_ref": "/projection-import-map",
        "expected_schema": "microcosm_public_projection_import_map_lens_v1",
    },
    "pattern_doctrine_compiler": {
        "action_type": "inspect",
        "command": "microcosm standards-control",
        "view_ref": "/standards-control",
        "expected_schema": "microcosm_public_standards_control_lens_v1",
    },
    "observatory_provenance_diagnostics": {
        "action_type": "tour",
        "command": "microcosm reveal",
        "view_ref": "/reveal",
        "expected_schema": "microcosm_public_reveal_view_v1",
    },
}

MATURITY_LABELS = {
    0: "M0 described",
    1: "M1 inspectable",
    2: "M2 runnable fixture",
    3: "M3 imported-real evidence",
    4: "M4 severed runnable",
    5: "M5 cold-reader loop",
}


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _first(values: list[str]) -> str:
    return values[0] if values else ""


def _first_receipt_ref(card: dict[str, Any]) -> str:
    release_refs = _strings(card.get("release_artifact_refs"))
    receipt_refs = [ref for ref in release_refs if ref.startswith("receipts/")]
    return _first(receipt_refs) or _first(release_refs)


def _first_runtime_command(card: dict[str, Any]) -> str:
    runtime_refs = _strings(card.get("runtime_surface_refs"))
    if not runtime_refs:
        return ""
    lane_id = str(card.get("lane_id") or "")
    hint = ACTION_HINTS.get(lane_id, {})
    if hint.get("command"):
        return str(hint["command"])
    for ref in runtime_refs:
        if ref.startswith("microcosm "):
            return ref
    return ""


def _action_hint(card: dict[str, Any]) -> dict[str, str]:
    lane_id = str(card.get("lane_id") or "")
    hint = dict(ACTION_HINTS.get(lane_id, {})) if _strings(card.get("runtime_surface_refs")) else {}
    command = _first_runtime_command(card)
    if command and "command" not in hint:
        hint["command"] = command
    if "action_type" not in hint:
        hint["action_type"] = "run" if command else "inspect"
    if "view_ref" not in hint and command.startswith("microcosm "):
        hint["view_ref"] = "/" + command.removeprefix("microcosm ").split()[0]
    return hint


def _maturity_level(
    card: dict[str, Any],
    compiler_receipt: dict[str, Any],
    command: str,
    output_probe: dict[str, Any],
) -> int:
    level = 0
    if _strings(card.get("release_artifact_refs")):
        level = 1
    if command.startswith("microcosm "):
        level = 2
    imported_real_refs = bool(
        _strings(card.get("macro_origin_refs"))
        or _strings(card.get("public_safe_body_material_ids"))
    )
    if level >= 2 and card.get("transfer_status") == PASS and imported_real_refs:
        level = 3
    if (
        level >= 3
        and compiler_receipt.get("dependency_preflight_gate_status") == PASS
        and compiler_receipt.get("status") == PASS
    ):
        level = 4
    if (
        level >= 4
        and _strings(card.get("linked_claim_card_ids"))
        and card.get("claim_ceiling")
        and output_probe
    ):
        level = 5
    return level


def _activation_card(
    card: dict[str, Any],
    compiler_receipt: dict[str, Any],
    *,
    minimum_maturity: int,
) -> dict[str, Any]:
    hint = _action_hint(card)
    command = str(hint.get("command") or "")
    receipt_ref = _first_receipt_ref(card)
    provenance_ref = _first(_strings(card.get("macro_origin_refs"))) or str(
        compiler_receipt.get("flagship_tranche_ref") or ""
    )
    output_probe = {
        "probe_type": "json_status_and_schema",
        "command": command,
        "expected_status": PASS,
        "required_fields": ["status", "schema_version"],
        "expected_schema_version": str(hint.get("expected_schema") or ""),
    }
    maturity = _maturity_level(card, compiler_receipt, command, output_probe)
    blockers = list(card.get("blockers", [])) if isinstance(card.get("blockers"), list) else []
    if not command:
        blockers.append(
            {
                "error_code": "CAPABILITY_ACTIVATION_ACTION_MISSING",
                "subject_id": str(card.get("capability_id") or card.get("lane_id") or ""),
                "subject_kind": "activation_card",
                "message": "Capability transfer card has no runnable or inspectable cold-reader command.",
                "body_redacted": True,
            }
        )
    if maturity < minimum_maturity:
        blockers.append(
            {
                "error_code": "CAPABILITY_ACTIVATION_MATURITY_TOO_LOW",
                "subject_id": str(card.get("capability_id") or card.get("lane_id") or ""),
                "subject_kind": "activation_card",
                "message": (
                    f"Activation maturity {maturity} is below required floor "
                    f"{minimum_maturity}."
                ),
                "body_redacted": True,
            }
        )
    if compiler_receipt.get("dependency_preflight_gate_status") != PASS:
        blockers.append(
            {
                "error_code": "CAPABILITY_ACTIVATION_PREFLIGHT_BLOCKED",
                "subject_id": str(card.get("capability_id") or card.get("lane_id") or ""),
                "subject_kind": "activation_card",
                "message": "Dependency preflight must pass before a cold-reader action is release-severed.",
                "body_redacted": True,
            }
        )
    activation_status = PASS if not blockers else BLOCKED
    return {
        "schema_version": CARD_SCHEMA,
        "activation_id": f"activation::{card.get('lane_id')}",
        "capability_id": str(card.get("capability_id") or ""),
        "lane_id": str(card.get("lane_id") or ""),
        "lane_label": str(card.get("lane_label") or ""),
        "visible_value": str(card.get("visible_value") or ""),
        "activation_status": activation_status,
        "cold_reader_action_type": str(hint.get("action_type") or "inspect"),
        "entry_surface_ref": str(hint.get("view_ref") or command),
        "command_or_view_ref": command,
        "expected_output_probe": output_probe,
        "receipt_ref": receipt_ref,
        "provenance_ref": provenance_ref,
        "claim_card_refs": _strings(card.get("linked_claim_card_ids")),
        "evidence_class": _first(_strings(card.get("claim_evidence_classes"))),
        "activation_maturity": {
            "level": maturity,
            "label": MATURITY_LABELS[maturity],
        },
        "standalone_severance_status": (
            PASS if compiler_receipt.get("dependency_preflight_gate_status") == PASS else BLOCKED
        ),
        "private_runtime_dependency_status": PASS,
        "claim_ceiling": str(card.get("claim_ceiling") or ""),
        "anti_claim": (
            "This activation proves only the local action, receipt/provenance links, "
            "and stated claim ceiling. It does not authorize release or claim private-root "
            "equivalence."
        ),
        "fallback_if_blocked": (
            "Demote to inspectable capability-transfer evidence and open the compiler "
            "card until the missing action, receipt, or preflight blocker is resolved."
        ),
        "demotion_rule": str(card.get("demotion_rule") or ""),
        "body_redacted": bool(card.get("body_redacted", True)),
        "blockers": blockers,
    }


def _showcase_mode(activation_cards: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "mode": "showcase",
        "command": "microcosm release-activation --root .",
        "activation_count": len(activation_cards),
        "lane_ids": [card["lane_id"] for card in activation_cards],
        "summary": "Show the strongest cold-reader actions backed by capability-transfer cards.",
    }


def _microscope_mode(activation_cards: list[dict[str, Any]]) -> dict[str, Any]:
    selected = next(
        (
            card
            for card in activation_cards
            if card["activation_maturity"]["level"] >= 5
        ),
        activation_cards[0] if activation_cards else {},
    )
    return {
        "mode": "microscope",
        "activation_id": selected.get("activation_id", ""),
        "command": selected.get("command_or_view_ref", ""),
        "inspect_refs": [
            selected.get("receipt_ref", ""),
            selected.get("provenance_ref", ""),
            *selected.get("claim_card_refs", []),
        ],
        "summary": "Open one lane and inspect its command, receipt, provenance, and claim ceiling.",
    }


def _falsification_mode() -> dict[str, Any]:
    return {
        "mode": "falsification",
        "fixture_mutation": "remove runtime_surface_refs from one copied flagship tranche lane",
        "expected_blocker": "CAPABILITY_ACTIVATION_ACTION_MISSING",
        "summary": (
            "A capability with no action must demote instead of rendering as a "
            "first-run activation."
        ),
    }


def _first_five_minute_path(activation_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first = activation_cards[0] if activation_cards else {}
    second = activation_cards[1] if len(activation_cards) > 1 else first
    return [
        {
            "step_id": "showcase",
            "action": "run",
            "command": "microcosm release-activation --root .",
            "why": "show the six-lane activation map before drilling into one lane",
        },
        {
            "step_id": "run_first_lane",
            "action": first.get("cold_reader_action_type", "inspect"),
            "command": first.get("command_or_view_ref", ""),
            "why": "prove one imported capability has a local action",
        },
        {
            "step_id": "inspect_second_lane",
            "action": second.get("cold_reader_action_type", "inspect"),
            "command": second.get("command_or_view_ref", ""),
            "why": "show breadth beyond a single formal/proof specimen",
        },
        {
            "step_id": "open_receipt",
            "action": "inspect",
            "ref": first.get("receipt_ref", ""),
            "why": "connect visible output to standalone release evidence",
        },
        {
            "step_id": "read_claim_ceiling",
            "action": "inspect",
            "refs": first.get("claim_card_refs", []),
            "why": "show what is not claimed before any release copy is written",
        },
    ]


def build_rehearsal(
    root: str | Path,
    *,
    require_claim_card_coverage: bool = True,
    minimum_maturity: int = DEFAULT_MINIMUM_ACTIVATION_MATURITY,
) -> dict[str, Any]:
    compiler_receipt = release_impressiveness_compiler.build_receipt(
        root,
        require_claim_card_coverage=require_claim_card_coverage,
    )
    activation_cards = [
        _activation_card(
            card,
            compiler_receipt,
            minimum_maturity=minimum_maturity,
        )
        for card in compiler_receipt.get("capability_transfer_cards", [])
        if isinstance(card, dict)
    ]
    blockers = [
        blocker
        for card in activation_cards
        for blocker in card.get("blockers", [])
        if isinstance(blocker, dict)
    ]
    maturity_counts = Counter(
        card["activation_maturity"]["label"] for card in activation_cards
    )
    maturity_levels = [
        int(card["activation_maturity"]["level"]) for card in activation_cards
    ]
    cold_reader_loop_status = (
        PASS
        if len(activation_cards) >= 5
        and not blockers
        and maturity_levels
        and min(maturity_levels) >= minimum_maturity
        and max(maturity_levels) >= 4
        else BLOCKED
    )
    status = (
        PASS
        if compiler_receipt.get("status") == PASS and cold_reader_loop_status == PASS
        else BLOCKED
    )
    return {
        "schema_version": RECEIPT_SCHEMA,
        "activation_surface_id": "release_activation_rehearsal",
        "created_at": utc_now(),
        "status": status,
        "cold_reader_loop_status": cold_reader_loop_status,
        "compiler_status": compiler_receipt.get("status"),
        "compiler_receipt_schema": compiler_receipt.get("schema_version"),
        "capability_transfer_card_count": compiler_receipt.get(
            "capability_transfer_card_count"
        ),
        "selected_pattern_count": compiler_receipt.get("selected_pattern_count"),
        "activation_card_count": len(activation_cards),
        "minimum_maturity_level": minimum_maturity,
        "activation_maturity_counts": dict(sorted(maturity_counts.items())),
        "activation_cards": activation_cards,
        "showcase_mode": _showcase_mode(activation_cards),
        "microscope_mode": _microscope_mode(activation_cards),
        "falsification_mode": _falsification_mode(),
        "first_five_minute_path": _first_five_minute_path(activation_cards),
        "blocking_codes": sorted(
            {
                str(blocker.get("error_code"))
                for blocker in blockers
                if blocker.get("error_code")
            }
            | set(compiler_receipt.get("blocking_codes", []))
        ),
        "authority_ceiling": compiler_receipt.get("authority_ceiling", {}),
        "anti_claim": (
            "Release activation rehearsals turn capability-transfer evidence into "
            "local first-run actions. They do not authorize publication, provider calls, "
            "private-root equivalence, or benchmark performance claims."
        ),
        "source_refs": {
            "compiler": "microcosm_core.release_impressiveness_compiler",
            "flagship_tranche": compiler_receipt.get("flagship_tranche_ref"),
            "claim_cards": compiler_receipt.get("claim_card_registry_ref"),
            "dependency_preflight": "receipts/preflight/dependency_preflight.json",
        },
        "receipt_paths": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m microcosm_core.release_activation_rehearsal"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    parser.add_argument("--require-claim-card-coverage", action="store_true")
    parser.add_argument(
        "--minimum-maturity",
        type=int,
        default=DEFAULT_MINIMUM_ACTIVATION_MATURITY,
    )
    args = parser.parse_args(argv)
    receipt = build_rehearsal(
        args.root,
        require_claim_card_coverage=args.require_claim_card_coverage,
        minimum_maturity=args.minimum_maturity,
    )
    if args.out:
        out_path = release_impressiveness_compiler.public_root_for(args.root) / args.out
        receipt["receipt_paths"] = [str(Path(args.out))]
        write_json_atomic(out_path, receipt)
    else:
        print(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
