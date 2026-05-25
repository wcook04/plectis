import json
from pathlib import Path


def _write_view(root: Path, name: str, items: list[dict]) -> None:
    views_dir = root / "state" / "task_ledger" / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    (views_dir / name).write_text(json.dumps({"items": items}), encoding="utf-8")


def _row(
    row_id: str,
    *,
    rank: int | None,
    state: str = "shaping",
    schedulable: bool = True,
    waiting_edges: int = 0,
    unsatisfied_per_edge: int = 0,
    unsatisfied_deps: int = 0,
) -> dict:
    edges = []
    for index in range(waiting_edges):
        edges.append(
            {
                "id": f"{row_id}_downstream_{index}",
                "title": f"{row_id} downstream {index}",
                "state": "captured",
                "waiting_on_this": True,
                "downstream_schedulable": False,
                "downstream_unsatisfied_dep_ids": [
                    f"{row_id}_missing_{index}_{missing}"
                    for missing in range(unsatisfied_per_edge)
                ],
                "unlock_status": "waiting_on_this",
            }
        )
    return {
        "id": row_id,
        "title": row_id.replace("_", " ").title(),
        "rank": rank,
        "state": state,
        "work_item_type": "capture",
        "dependency_status": {
            "schedulable": schedulable,
            "hard_dep_count": unsatisfied_deps,
            "unsatisfied_dep_ids": [f"{row_id}_dep_{i}" for i in range(unsatisfied_deps)],
            "downstream_unlock_ids": [edge["id"] for edge in edges],
            "downstream_unlock_edges": edges,
        },
    }


def test_priority_constellation_keeps_scheduler_lanes_separate(tmp_path: Path) -> None:
    from system.lib.task_ledger_priority import priority_constellation

    terminal = _row(
        "cap_terminal_pressure",
        rank=1,
        state="done",
        waiting_edges=8,
        unsatisfied_per_edge=8,
    )
    high_rank_low_pressure = _row(
        "cap_high_rank_low_pressure",
        rank=2,
        waiting_edges=1,
        unsatisfied_per_edge=1,
    )
    lower_rank_high_pressure = _row(
        "cap_lower_rank_high_pressure",
        rank=30,
        waiting_edges=3,
        unsatisfied_per_edge=6,
    )
    global_hidden_pressure = _row(
        "cap_global_hidden_pressure",
        rank=None,
        schedulable=False,
        waiting_edges=5,
        unsatisfied_per_edge=8,
        unsatisfied_deps=1,
    )
    blocked = _row(
        "cap_blocked_important",
        rank=8,
        schedulable=False,
        waiting_edges=1,
        unsatisfied_per_edge=2,
        unsatisfied_deps=2,
    )

    _write_view(
        tmp_path,
        "execution_menu_schedulable.json",
        [terminal, high_rank_low_pressure, lower_rank_high_pressure],
    )
    _write_view(tmp_path, "schedulable_by_rank.json", [])
    _write_view(tmp_path, "ready_by_rank.json", [])
    _write_view(tmp_path, "dependency_blocked.json", [blocked])
    _write_view(
        tmp_path,
        "unlocks_by_rank.json",
        [terminal, global_hidden_pressure, lower_rank_high_pressure, high_rank_low_pressure],
    )

    payload = priority_constellation(tmp_path)

    assert payload["top_schedulable_workitem"]["id"] == "cap_high_rank_low_pressure"
    assert (
        payload["top_schedulable_unlock_pressure_workitems"][0]["id"]
        == "cap_lower_rank_high_pressure"
    )
    assert (
        payload["top_global_unlock_pressure_workitems"][0]["id"]
        == "cap_global_hidden_pressure"
    )
    assert payload["top_dependency_blocked_workitem"]["id"] == "cap_blocked_important"
    assert payload["selector_explanation"]["terminal_policy"].startswith("Terminal states")

    lane_ids = {
        row["id"]
        for lane_name in (
            "top_schedulable_unlock_pressure_workitems",
            "top_global_unlock_pressure_workitems",
        )
        for row in payload[lane_name]
    }
    assert "cap_terminal_pressure" not in lane_ids

    signal = payload["top_schedulable_unlock_pressure_workitems"][0]["priority_signal"]
    assert signal["pressure_basis"] == "dependency_status.downstream_unlock_edges"
    assert signal["schedulable"] is True
    assert signal["score_components"]["downstream_unsatisfied_dep_total"] == 18


def test_active_execution_entry_admission_preserves_scheduler_lanes_under_budget() -> None:
    from system.lib.kernel.commands.comprehension_snapshot import (
        ENTRY_PACKET_INLINE_TARGET_BYTES,
        _apply_entry_payload_admission,
    )

    pressure_row = {
        "id": "cap_pressure",
        "rank": 7,
        "state": "shaping",
        "schedulable": True,
        "pressure": {"score": 900, "waiting": 2, "downstream_unsatisfied": 30},
        "title": "Pressure row",
    }
    packet = {
        "kind": "kernel.entry_packet",
        "selected_lane": {"lane_id": "active_execution_constellation"},
        "active_execution_constellation": {
            "kind": "active_execution_constellation",
            "schema_version": "active_execution_constellation_v0",
            "declared_anchor": {
                "phase_id": "09_54",
                "runtime_state": "no_active_runtime_phase",
                "status": "declared_anchor_runtime_dormant",
            },
            "projection_freshness": {"status": "fresh"},
            "work_priority": {
                "schema_version": "task_ledger_priority_constellation_v1",
                "view_counts": {
                    "execution_menu_schedulable": 1,
                    "dependency_blocked": 1,
                    "unlocks_by_rank": 3,
                    "unlock_pressure": 2,
                },
                "lane_contract": {
                    "schedulable_now": "executable feasibility lane",
                    "schedulable_unlock_pressure": "executable pressure lane",
                    "global_unlock_pressure": "hidden pressure, not necessarily executable",
                    "dependency_blocked": "blocked queue",
                },
                "lanes": [
                    {
                        "lane_id": "schedulable_now",
                        "label": "schedulable now",
                        "executable_now": True,
                        "blocked": False,
                        "rows": [pressure_row],
                    },
                    {
                        "lane_id": "schedulable_unlock_pressure",
                        "label": "highest schedulable unlock pressure",
                        "executable_now": True,
                        "blocked": False,
                        "rows": [pressure_row],
                    },
                    {
                        "lane_id": "global_unlock_pressure",
                        "label": "hidden/global unlock pressure, not necessarily schedulable",
                        "executable_now": False,
                        "blocked": False,
                        "rows": [pressure_row],
                    },
                    {
                        "lane_id": "dependency_blocked",
                        "label": "blocked but important",
                        "executable_now": False,
                        "blocked": True,
                        "rows": [pressure_row],
                    },
                ],
                "drilldowns": {
                    "task_ledger_cluster": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag"
                },
            },
            "live_sessions": {
                "counts": {"active_claims": 5},
                "sessions": [
                    {
                        "session_id": f"session_{index}",
                        "paths": [f"path_{i}" for i in range(200)],
                    }
                    for index in range(10)
                ],
            },
            "demotion_guard": {
                "status": "blocked",
                "closeable": False,
                "blocker_count": 3,
                "blocker_topology": {"buckets": [{"claim_refs": list(range(1000))}]},
            },
        },
    }

    result = _apply_entry_payload_admission(packet, context_budget=12000)

    assert result["entry_payload_admission"]["status"] == "trimmed"
    assert result["entry_payload_admission"]["output_bytes"] <= ENTRY_PACKET_INLINE_TARGET_BYTES
    active_execution = result["active_execution_constellation"]
    assert active_execution["view_profile"] == "entry_admission_hard_compact"
    lane_ids = {
        lane["lane_id"] for lane in active_execution["work_priority"]["lanes"]
    }
    assert {
        "schedulable_now",
        "schedulable_unlock_pressure",
        "global_unlock_pressure",
        "dependency_blocked",
    } <= lane_ids
