"""Tests for prompt_shelf_uppropagation_index."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "meta" / "observability"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import prompt_shelf_uppropagation_index as up_mod  # noqa: E402


def _patch_roots(monkeypatch, tmp_path: Path) -> Path:
    repo = tmp_path
    raw_root = repo / "obsidian" / "prompt_shelf" / "usage" / "raw_events"
    monkeypatch.setattr(up_mod, "REPO_ROOT", repo)
    monkeypatch.setattr(up_mod, "RAW_EVENTS_ROOT", raw_root)
    monkeypatch.setattr(up_mod, "INDEX_PATH", repo / "state" / "prompt_shelf" / "uppropagation_index.json")
    return raw_root


def _write_event(raw_root: Path, slot_dir: str, run_id: str, assistant_text: str, *, user_text: str = "",
                 extra: dict | None = None) -> Path:
    path = raw_root / slot_dir / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "event_kind": "prompt_shelf_run_raw",
        "prompt_run_id": run_id,
        "prompt_slot": run_id.split("--")[1],
        "prompt_slug": "continue_intelligently",
        "captured_at": "2026-04-27T02:00:00+00:00",
        "conversation_id": "conv-abc",
        "conversation_url": "https://chatgpt.com/c/conv-abc",
        "user_turn_index": 2,
        "assistant_turn_index": 3,
        "user_message": {
            "raw_text": user_text,
            "sha256": "u" * 64,
        },
        "assistant_message": {
            "raw_text": assistant_text,
            "sha256": "a" * 64,
        },
        "extra": extra or {},
    }
    path.write_text(json.dumps(payload))
    return path


def test_v1_block_parses_for_backward_compatibility(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--v1record",
        """done
<!-- aiw:uppropagation v=1 -->
surprised: Evidence request telemetry is doctrine pressure.
prompt_friction:
system_friction: The prompt had no information_demand field yet.
deferred: v3 migration left for the next turn.
confidence: high - parser should keep v1 alive
<!-- /aiw:uppropagation -->
""",
    )

    index = up_mod.build_index()
    assert index["__meta"]["events_with_block"] == 1
    rec = index["records"][0]
    assert rec["block_v"] == 1
    assert rec["block_schema_version"] == "v1"
    assert rec["fields"]["surprised"].startswith("Evidence request")
    assert rec["field_status"]["prompt_friction"] == "empty"
    assert rec["confidence_label"] == "high"


def test_v3_block_parses_new_fields_and_rollups(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--v3record",
        """final
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: Continue from a pasted doctrine trace.
lesson: Repeated evidence requests should route to the owning affordance.
self_prompting_idea: Future B2 should emit ASK_TYPE_A for exact repo facts.
information_demand: Need the standard path for bridge info requests.
prompt_friction:
system_friction: The extractor only handled v1 before this change.
confidence: medium - one more real capture would improve confidence
step_word: guard
step_summary: Partial captures are guarded.
next_move: Add timeline and model telemetry.
<!-- /aiw:uppropagation -->
""",
    )

    index = up_mod.build_index()
    rec = index["records"][0]
    assert rec["block_v"] == 3
    assert rec["fields"]["prompt_received"] == "B2: continue_intelligently"
    assert rec["fields"]["self_prompting_idea"].startswith("Future B2")
    assert rec["fields"]["information_demand"].startswith("Need the standard")
    assert rec["field_status"]["prompt_friction"] == "empty"
    assert rec["confidence_label"] == "medium"
    assert rec["assistant_message_sha256"] == "a" * 64
    assert rec["assistant_message_sha16"] == "a" * 16
    assert len(rec["uppropagation_block_sha256"]) == 64
    assert rec["uppropagation_block_sha16"] == rec["uppropagation_block_sha256"][:16]
    assert rec["display_fields"]["step_word"] == "guard"
    assert rec["display_fields"]["step_summary"] == "Partial captures are guarded."
    assert rec["step_word"] == "guard"
    assert rec["step_summary"] == "Partial captures are guarded."
    assert rec["state_word"] == "guard"
    rollups = index["rollups"]["filled_field_counts_by_slot"]
    assert rollups["self_prompting_idea"]["B2"] == 1
    assert rollups["information_demand"]["B2"] == 1


def test_multiple_blocks_last_block_wins(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "A0_explore",
        "20260427T020000000000--A0--multiblk",
        """Quoted prompt:
<!-- aiw:uppropagation v=1 -->
surprised: quoted prompt block
prompt_friction:
system_friction:
deferred:
confidence: low - not emitted
<!-- /aiw:uppropagation -->

Actual footer:
<!-- aiw:uppropagation v=3 -->
prompt_received: A0: surface_exploration
prompt_interpretation: Explore the bridge evidence protocol.
lesson: Last emitted block is the only record.
self_prompting_idea:
information_demand: Bridge-ready evidence should carry negative searches.
prompt_friction:
system_friction:
confidence: high - last block parsed
<!-- /aiw:uppropagation -->
""",
    )

    rec = up_mod.build_index()["records"][0]
    assert rec["block_count"] == 2
    assert rec["block_v"] == 3
    assert rec["fields"]["prompt_received"] == "A0: surface_exploration"
    assert "surprised" not in rec["fields"]
    assert rec["confidence_label"] == "high"
    assert rec["uppropagation_capture_eligible"] is True
    assert rec["uppropagation_selection"] == "top_level_final_assistant_block"


def test_final_quoted_code_block_is_not_indexed(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--quoted",
        """Here is an example, not my emitted packet:
```text
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: quoted example
lesson: should not index
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: low - quoted
<!-- /aiw:uppropagation -->
```""",
    )

    index = up_mod.build_index()
    assert index["records"] == []
    assert index["__meta"]["events_with_block"] == 0


def test_nonfinal_assistant_block_is_not_indexed(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--nonfinal",
        """<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: non-final block
lesson: should not index
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: medium - nonfinal
<!-- /aiw:uppropagation -->

More assistant prose after the block.""",
    )

    assert up_mod.build_index()["records"] == []


def test_raw_event_provenance_can_refuse_indexing(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--embeddedmeta",
        """<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: metadata says embedded
lesson: should not index
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: medium - embedded metadata
<!-- /aiw:uppropagation -->""",
        extra={
            "uppropagation_provenance": "assistant_quoted_or_code",
            "uppropagation_capture_eligible": False,
        },
    )

    assert up_mod.build_index()["records"] == []


def test_user_side_only_block_does_not_count(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B1_instantiation",
        "20260427T020000000000--B1--useronly",
        "assistant has no machine block",
        user_text="""User quoted:
<!-- aiw:uppropagation v=3 -->
prompt_received: B1: instantiation
prompt_interpretation: user-side prompt template
lesson:
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: low - should not count
<!-- /aiw:uppropagation -->
""",
    )

    index = up_mod.build_index()
    assert index["__meta"]["events_with_block"] == 0
    assert index["__meta"]["events_without_block"] == 1
    assert index["records"] == []


def test_quarantined_raw_event_does_not_count(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    path = _write_event(
        raw_root,
        "B2_continue",
        "20260427T020000000000--B2--badcap",
        """assistant
<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: bad capture
lesson: should not count
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: low - quarantined
<!-- /aiw:uppropagation -->
""",
    )
    data = json.loads(path.read_text())
    data["invalidation"] = {
        "status": "quarantined",
        "reason": "pre_guard_partial_b_lane_capture",
    }
    path.write_text(json.dumps(data))

    index = up_mod.build_index()

    assert index["__meta"]["events_with_block"] == 0
    assert index["records"] == []


def test_v2_transition_block_parses_expected_fields(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root,
        "B3_compact",
        "20260427T020000000000--B3--v2record",
        """packet
<!-- aiw:uppropagation v=2 -->
prompt_received: B3: context_compaction
prompt_interpretation: Compact a doctrine trace.
lesson: Deferred belongs outside up-propagation.
prompt_friction:
system_friction:
confidence: low - v2 compatibility is synthetic
<!-- /aiw:uppropagation -->
""",
    )

    rec = up_mod.build_index()["records"][0]
    assert rec["block_v"] == 2
    assert rec["fields"]["lesson"] == "Deferred belongs outside up-propagation."
    assert "self_prompting_idea" not in rec["fields"]
    assert rec["field_status"]["system_friction"] == "empty"
    assert rec["confidence_label"] == "low"
