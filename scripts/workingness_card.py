#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = MICROCOSM_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from microcosm_core.runtime_shell import RuntimeShell  # noqa: E402


SURFACE_COUNT_KEYS = (
    "mapped_organ_count",
    "adapter_backed_organ_count",
    "demoted_drilldown_count",
    "rows_with_failure_modes",
    "rows_with_future_work_targets",
    "rows_with_source_body_imports",
    "source_open_body_material_count",
    "missing_standard_count",
    "missing_failure_modes_count",
)


def workingness_card(root: Path = MICROCOSM_ROOT) -> dict[str, Any]:
    workingness = RuntimeShell(root).workingness_map(persist_receipt=False)
    surface_counts = (
        workingness.get("surface_counts", {})
        if isinstance(workingness.get("surface_counts"), dict)
        else {}
    )
    map_policy = (
        workingness.get("map_policy", {})
        if isinstance(workingness.get("map_policy"), dict)
        else {}
    )
    authority_ceiling = (
        workingness.get("authority_ceiling", {})
        if isinstance(workingness.get("authority_ceiling"), dict)
        else {}
    )
    return {
        "schema_version": "microcosm_workingness_command_speed_card_v1",
        "status": workingness.get("map_generation_status", workingness.get("status")),
        "card_status": workingness.get("failure_envelope_status"),
        "command": "microcosm-substrate/scripts/workingness_card.py",
        "source_command": workingness.get("command"),
        "drilldown_command": "microcosm workingness",
        "endpoint": workingness.get("endpoint"),
        "workingness_map_ref": workingness.get("workingness_map_ref"),
        "completeness_status": workingness.get("completeness_status"),
        "top_level_status_rule": workingness.get("top_level_status_rule"),
        "surface_counts": {
            key: surface_counts.get(key)
            for key in SURFACE_COUNT_KEYS
            if key in surface_counts
        },
        "gap_preview": workingness.get("gap_preview"),
        "output_economy": {
            "default_full_command_preserved": True,
            "thing_failure_map_exported": False,
            "known_failure_mode_rows_exported": False,
            "receipt_persisted": False,
            "compact_route_for_first_screen": True,
        },
        "map_policy": {
            "not_a_scorecard": map_policy.get("not_a_scorecard"),
            "accepted_status_is_not_evidence_strength": map_policy.get(
                "accepted_status_is_not_evidence_strength"
            ),
        },
        "authority_ceiling": {
            "release_authorized": authority_ceiling.get("release_authorized"),
            "score_based_progress_authority": authority_ceiling.get(
                "score_based_progress_authority"
            ),
            "whole_system_correctness_claim": authority_ceiling.get(
                "whole_system_correctness_claim"
            ),
        },
        "reader_action": (
            "Use this compact card for first-screen command selection; run "
            "microcosm workingness only when per-organ failure rows are needed."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workingness_card",
        description="Emit a compact first-screen card for Microcosm workingness.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=MICROCOSM_ROOT,
        help="Microcosm public root; defaults to the script's parent tree.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = workingness_card(args.root)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
