"""Tests for prompt_shelf_uppropagation_digest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "meta" / "observability"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import prompt_shelf_uppropagation_digest as digest_mod  # noqa: E402
import prompt_shelf_uppropagation_index as index_mod  # noqa: E402


def _patch_index_roots(monkeypatch, tmp_path: Path) -> Path:
    raw_root = tmp_path / "obsidian" / "prompt_shelf" / "usage" / "raw_events"
    monkeypatch.setattr(index_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(index_mod, "RAW_EVENTS_ROOT", raw_root)
    monkeypatch.setattr(index_mod, "INDEX_PATH", tmp_path / "state" / "prompt_shelf" / "uppropagation_index.json")
    monkeypatch.setattr(
        digest_mod,
        "PROMPT_LEDGER_ADOPTION_POSTURE_PATH",
        tmp_path / "state" / "prompt_ledger" / "views" / "adoption_posture.json",
    )
    return raw_root


def _write_event(raw_root: Path, slot_dir: str, run_id: str, assistant_text: str, *,
                 conversation_id: str = "conv-abc",
                 conversation_url: str = "https://chatgpt.com/c/conv-abc",
                 captured_at: str = "2026-04-27T02:00:00+00:00") -> None:
    path = raw_root / slot_dir / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "event_kind": "prompt_shelf_run_raw",
        "prompt_run_id": run_id,
        "prompt_slot": run_id.split("--")[1],
        "prompt_slug": "continue_intelligently",
        "captured_at": captured_at,
        "conversation_id": conversation_id,
        "conversation_url": conversation_url,
        "assistant_message": {
            "raw_text": assistant_text,
            "sha256": "a" * 64,
        },
    }
    path.write_text(json.dumps(payload))


def test_v3_run_indexes_into_digest_candidate_rows(tmp_path, monkeypatch):
    raw_root = _patch_index_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--digest1",
        """final
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: Continue recursive prompt-shelf work.
lesson: Repeated evidence demand should become a compact candidate row.
self_prompting_idea: Future B2 should request Type A evidence for exact repo facts.
information_demand: Expose bridge evidence packet standards through a docs-route alias.
prompt_friction:
system_friction:
confidence: high - fixture proves run to index to digest
<!-- /aiw:uppropagation -->
""",
    )

    index = index_mod.build_index()
    digest = digest_mod.finalize_digest(digest_mod.build_digest(index), index)

    latest = digest["latest_v3_by_slot"]["B2"]
    assert latest["self_prompting_idea"].startswith("Future B2")
    assert latest["information_demand"].startswith("Expose bridge")
    rows = digest["candidate_rows"]
    assert {row["source_field"] for row in rows} >= {"lesson", "self_prompting_idea", "information_demand"}
    info_row = next(row for row in rows if row["source_field"] == "information_demand")
    assert info_row["candidate_kind"] == "evidence_affordance"
    assert info_row["status"] == "observed"
    assert info_row["promotion"] == "none_auto_created"
    posture = digest["prompt_adoption_posture"]
    assert posture["owner"] == "codex/standards/std_prompt_ledger.json::adoption_state_machine"
    assert posture["captured_count"] == 1
    assert posture["indexed_count"] == 1
    assert posture["digested_count"] == len(rows)
    assert posture["adopted_count"] == 0
    assert posture["behavior_projection_count"] == 0
    assert "captured != adopted" in posture["known_distinctions"]


def test_repeated_exact_values_are_compacted(tmp_path, monkeypatch):
    raw_root = _patch_index_roots(monkeypatch, tmp_path)
    text = """final
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: Continue.
lesson: Same lesson.
self_prompting_idea: Future B2 should request Type A evidence for exact repo facts.
information_demand: Need compact prompt artifact lint.
prompt_friction:
system_friction:
confidence: medium - repeat fixture
<!-- /aiw:uppropagation -->
"""
    _write_event(raw_root, "B2_continue", "20260427T020000000000--B2--repeat01", text)
    _write_event(raw_root, "B2_continue", "20260427T020100000000--B2--repeat02", text)

    index = index_mod.build_index()
    digest = digest_mod.finalize_digest(digest_mod.build_digest(index), index)
    repeated = digest["repeated_values"]
    assert any(
        row["field"] == "self_prompting_idea"
        and row["count"] == 2
        and row["slots"] == ["B2"]
        for row in repeated
    )


def test_digest_counts_prompt_ledger_adoption_receipts(tmp_path, monkeypatch):
    raw_root = _patch_index_roots(monkeypatch, tmp_path)
    adoption_path = tmp_path / "state" / "prompt_ledger" / "views" / "adoption_posture.json"
    monkeypatch.setattr(digest_mod, "PROMPT_LEDGER_ADOPTION_POSTURE_PATH", adoption_path)
    adoption_path.parent.mkdir(parents=True)
    adoption_path.write_text(
        json.dumps(
            {
                "schema_version": "prompt_ledger_projection_v1",
                "authority": "state/prompt_ledger/events.jsonl",
                "receipt_count": 2,
                "candidate_count": 1,
                "state_counts_semantics": "candidate_milestone_counts",
                "candidate_current_state_counts": {
                    "captured_count": 0,
                    "indexed_count": 0,
                    "digested_count": 0,
                    "selected_for_adoption_count": 0,
                    "bound_to_workitem_count": 0,
                    "mutated_owner_surface_count": 0,
                    "validated_count": 0,
                    "projected_to_entry_count": 0,
                    "observed_in_future_run_count": 1,
                    "explicit_noop_count": 0,
                },
                "candidate_milestone_counts": {
                    "captured_count": 1,
                    "indexed_count": 1,
                    "digested_count": 1,
                    "selected_for_adoption_count": 1,
                    "bound_to_workitem_count": 1,
                    "mutated_owner_surface_count": 1,
                    "validated_count": 1,
                    "projected_to_entry_count": 1,
                    "observed_in_future_run_count": 1,
                    "explicit_noop_count": 0,
                },
                "adopted_count": 1,
                "behavior_projection_count": 1,
                "receipts": [{"receipt_id": "pla_test_cand"}, {"receipt_id": "plo_test_cand"}],
            }
        ),
        encoding="utf-8",
    )
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--adopted1",
        """final
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: Continue recursive prompt-shelf work.
lesson: Memory is not enough; a reusable self-description packet needs adoption proof.
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: high - fixture proves adoption posture merge
<!-- /aiw:uppropagation -->
""",
    )

    index = index_mod.build_index()
    digest = digest_mod.finalize_digest(digest_mod.build_digest(index), index)
    posture = digest["prompt_adoption_posture"]

    assert posture["captured_count"] == 1
    assert posture["digested_count"] == len(digest["candidate_rows"])
    assert posture["state_counts"]["selected_for_adoption_count"] == 1
    assert posture["state_counts"]["bound_to_workitem_count"] == 1
    assert posture["state_counts"]["mutated_owner_surface_count"] == 1
    assert posture["state_counts"]["validated_count"] == 1
    assert posture["state_counts"]["projected_to_entry_count"] == 1
    assert posture["state_counts"]["observed_in_future_run_count"] == 1
    assert posture["prompt_ledger_receipt_count"] == 2
    assert posture["prompt_ledger_candidate_count"] == 1
    assert posture["candidate_current_state_counts"]["projected_to_entry_count"] == 0
    assert posture["candidate_current_state_counts"]["observed_in_future_run_count"] == 1
    assert posture["candidate_milestone_counts"]["selected_for_adoption_count"] == 1
    assert posture["candidate_milestone_counts"]["projected_to_entry_count"] == 1
    assert posture["candidate_milestone_counts"]["observed_in_future_run_count"] == 1
    assert posture["adopted_count"] == 1
    assert posture["behavior_projection_count"] == 1
    assert posture["prompt_ledger_adoption_receipt_count"] == 2
    assert posture["prompt_ledger_receipt_ids"] == ["pla_test_cand", "plo_test_cand"]


def test_conversation_mission_evolution_preserves_thread_timeline(tmp_path, monkeypatch):
    raw_root = _patch_index_roots(monkeypatch, tmp_path)
    first = """final
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
step_word: milestone
step_summary: The next move became a what-if milestone matrix.
prompt_interpretation: Continue a promotion-readiness thread.
lesson: Milestone edits need proof-preserving dry-runs.
self_prompting_idea: Future B2 should ask for a timestamp survival matrix.
information_demand: Type A should return which proofs survive candidate timestamps.
prompt_friction:
system_friction:
confidence: high - fixture starts the mission arc
<!-- /aiw:uppropagation -->
"""
    second = """final
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
step_word: audit
step_summary: The matrix showed the canary proof would survive one candidate timestamp.
prompt_interpretation: Continue the same promotion-readiness thread.
lesson: Promotion prompts should separate run-created evidence from commit-created evidence.
self_prompting_idea: Future B2 should preserve the prior matrix before recommending a registry edit.
information_demand: Type A should return post-edit metrics without mutating the registry.
prompt_friction:
system_friction:
confidence: high - two-step arc proves grouping
<!-- /aiw:uppropagation -->
"""
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--mission01",
        first,
        conversation_id="mission-conv",
        conversation_url="https://chatgpt.com/c/mission-conv",
        captured_at="2026-04-27T02:00:00+00:00",
    )
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T021000000000--B2--mission02",
        second,
        conversation_id="mission-conv",
        conversation_url="https://chatgpt.com/c/mission-conv",
        captured_at="2026-04-27T02:10:00+00:00",
    )

    index = index_mod.build_index()
    digest = digest_mod.finalize_digest(digest_mod.build_digest(index), index)

    mission = digest["mission_evolution"][0]
    assert mission["conversation_id"] == "mission-conv"
    assert mission["run_count"] == 2
    assert mission["latest_step_word"] == "audit"
    assert [event["step_word"] for event in mission["timeline"]] == ["milestone", "audit"]
    assert mission["timeline"][0]["information_demand"].startswith("Type A should return which proofs")
