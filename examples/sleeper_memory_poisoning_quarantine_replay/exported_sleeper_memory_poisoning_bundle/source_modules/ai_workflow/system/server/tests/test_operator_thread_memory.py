"""Tests for private Operator Thread Memory event/projection substrate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "meta" / "observability"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import operator_thread_memory as otm  # noqa: E402
import operator_turn_stack_projection as turn_projection  # noqa: E402
import prompt_shelf_chatgpt_observer as obs_mod  # noqa: E402


def _tab(target_id: str = "target-1", url: str = "https://chatgpt.com/c/abc123") -> SimpleNamespace:
    return SimpleNamespace(target_id=target_id, title="ChatGPT", url=url)


def _snapshot(url: str, turns: list[dict[str, str]], title: str = "AI infrastructure thesis") -> SimpleNamespace:
    return SimpleNamespace(url=url, title=title, turns=turns)


def _turn(role: str, text: str, index: int) -> dict[str, object]:
    return {"role": role, "text": text, "message_id": f"m-{index}", "ordinal": index}


def _events() -> list[dict[str, object]]:
    return otm.read_events()


def _event_types() -> list[str]:
    return [str(event.get("event_type")) for event in _events()]


def _configure_private_root(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "state" / "operator_bridge" / "thread_memory"
    monkeypatch.setattr(otm, "THREAD_MEMORY_ROOT", root)
    monkeypatch.setattr(otm, "EVENTS_PATH", root / "events.jsonl")
    monkeypatch.setattr(otm, "INDEX_PATH", root / "index.json")
    monkeypatch.setattr(otm, "THREADS_DIR", root / "threads")
    monkeypatch.setattr(otm, "THREAD_PROGRESS_JSON_PATH", root / "thread_progress.json")
    monkeypatch.setattr(otm, "THREAD_PROGRESS_MARKDOWN_PATH", root / "thread_progress.md")
    return root


def test_thread_memory_creates_event_log_thread_and_metadata_index(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_TRANSCRIPT_TEXT"
    bindings: dict[str, object] = {}
    turns = [
        _turn("user", f"Continue\n\n{private_text}", 0),
        _turn("assistant", "Response stays private.", 1),
    ]

    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/abc123", turns),
        hud_payload={"tab_order": 1, "observer_version": "test"},
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )

    assert meta["thread_memory_id"] == "chatgpt_abc123"
    assert meta["thread_prompt_count"] == 1
    assert "thread_created" in _event_types()
    thread_path = root / "threads" / "chatgpt_abc123.json"
    assert private_text in thread_path.read_text(encoding="utf-8")
    event_text = (root / "events.jsonl").read_text(encoding="utf-8")
    assert private_text not in event_text
    thread_created = next(event for event in _events() if event.get("event_type") == "thread_created")
    assert "thread_snapshot" not in thread_created
    assert thread_created["thread_snapshot_ref"]["payload_policy"] == "compressed_private_snapshot_ref"
    index_text = (root / "index.json").read_text(encoding="utf-8")
    assert private_text not in index_text
    assert json.loads(index_text)["threads"][0]["payload_policy"] == "metadata_only"


def test_unchanged_snapshot_does_not_duplicate_thread_update(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    turns = [_turn("user", "Continue", 0), _turn("assistant", "ok", 1)]
    snapshot = _snapshot("https://chatgpt.com/c/stable", turns)

    otm.update_from_observer_snapshot(tab=_tab(url=snapshot.url), snapshot=snapshot, bindings=bindings, now="2026-05-12T09:00:00+00:00")
    otm.update_from_observer_snapshot(tab=_tab(url=snapshot.url), snapshot=snapshot, bindings=bindings, now="2026-05-12T09:01:00+00:00")

    assert _event_types().count("thread_created") == 1
    assert "thread_updated" not in _event_types()


def test_project_thread_records_resolves_compressed_snapshot_refs(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_REBUILD_TEXT"
    turns = [_turn("user", private_text, 0), _turn("assistant", "ok", 1)]

    otm.update_from_observer_snapshot(
        tab=_tab(url="https://chatgpt.com/c/rebuild"),
        snapshot=_snapshot("https://chatgpt.com/c/rebuild", turns),
        bindings={},
        now="2026-05-12T09:00:00+00:00",
    )
    (root / "threads" / "chatgpt_rebuild.json").unlink()

    otm.project_thread_records()

    rebuilt_text = (root / "threads" / "chatgpt_rebuild.json").read_text(encoding="utf-8")
    index_text = (root / "index.json").read_text(encoding="utf-8")
    assert private_text in rebuilt_text
    assert private_text not in index_text


def test_appended_turns_update_projection(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    first = [_turn("user", "Continue", 0), _turn("assistant", "one", 1)]
    second = first + [_turn("user", "Another question", 2), _turn("assistant", "two", 3)]

    otm.update_from_observer_snapshot(tab=_tab(), snapshot=_snapshot("https://chatgpt.com/c/append", first), bindings=bindings, now="2026-05-12T09:00:00+00:00")
    meta = otm.update_from_observer_snapshot(tab=_tab(), snapshot=_snapshot("https://chatgpt.com/c/append", second), bindings=bindings, now="2026-05-12T09:01:00+00:00")

    assert "thread_updated" in _event_types()
    assert meta["thread_memory_turn_count"] == 4
    record = json.loads((root / "threads" / "chatgpt_append.json").read_text(encoding="utf-8"))
    assert record["user_turn_count"] == 2
    assert record["assistant_turn_count"] == 2


def test_streaming_tail_update_replaces_partial_assistant_turn(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    partial = [
        _turn("user", "Continue", 0),
        {"role": "assistant", "text": "I", "message_id": "partial-assistant", "ordinal": 1},
    ]
    complete = [
        _turn("user", "Continue", 0),
        {
            "role": "assistant",
            "text": "I now have the full packet-only dogfood verdict.",
            "message_id": "complete-assistant",
            "ordinal": 1,
        },
    ]

    otm.update_from_observer_snapshot(
        tab=_tab(url="https://chatgpt.com/c/streaming"),
        snapshot=_snapshot("https://chatgpt.com/c/streaming", partial),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )
    meta = otm.update_from_observer_snapshot(
        tab=_tab(url="https://chatgpt.com/c/streaming"),
        snapshot=_snapshot("https://chatgpt.com/c/streaming", complete),
        bindings=bindings,
        now="2026-05-12T09:01:00+00:00",
    )

    record = json.loads((root / "threads" / "chatgpt_streaming.json").read_text(encoding="utf-8"))
    assert meta["thread_memory_merge_state"] == "observed_updated_streaming_tail"
    assert record["turn_count"] == 2
    assert record["turns"][-1]["text"] == "I now have the full packet-only dogfood verdict."
    assert record["turns"][-1]["message_id"] == "complete-assistant"


def test_visible_tail_snapshot_does_not_shrink_thread_memory(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    full = [
        _turn("user", "First prompt", 0),
        _turn("assistant", "one", 1),
        _turn("user", "Second prompt", 2),
        _turn("assistant", "two", 3),
        _turn("user", "Third prompt", 4),
        _turn("assistant", "three", 5),
    ]
    visible_tail = full[-2:]

    otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/tail", full),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )
    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/tail", visible_tail),
        bindings=bindings,
        now="2026-05-12T09:01:00+00:00",
    )

    record = json.loads((root / "threads" / "chatgpt_tail.json").read_text(encoding="utf-8"))
    assert meta["thread_memory_user_turn_count"] == 3
    assert meta["thread_memory_merge_state"] == "observed_window_within_memory"
    assert record["turn_count"] == 6
    assert record["user_turn_count"] == 3
    assert record["latest_observed_window"]["turn_count"] == 2


def test_provisional_thread_promotes_to_conversation_identity(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    turns = [_turn("user", "Continue", 0), _turn("assistant", "ok", 1)]

    first = otm.update_from_observer_snapshot(
        tab=_tab(url="https://chatgpt.com/"),
        snapshot=_snapshot("https://chatgpt.com/", turns),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )
    promoted = otm.update_from_observer_snapshot(
        tab=_tab(url="https://chatgpt.com/c/promoted"),
        snapshot=_snapshot("https://chatgpt.com/c/promoted", turns),
        bindings=bindings,
        now="2026-05-12T09:01:00+00:00",
    )

    assert str(first["thread_memory_id"]).startswith("provisional_")
    assert promoted["thread_memory_id"] == "chatgpt_promoted"
    assert "thread_alias_promoted" in _event_types()
    record = json.loads((root / "threads" / "chatgpt_promoted.json").read_text(encoding="utf-8"))
    assert first["thread_memory_id"] in record["provisional_ids"]


def test_vanish_reappear_recovers_same_thread(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    tab = _tab(target_id="target-vanish", url="https://chatgpt.com/")
    turns = [_turn("user", "Continue", 0), _turn("assistant", "ok", 1)]

    first = otm.update_from_observer_snapshot(tab=tab, snapshot=_snapshot(tab.url, turns), bindings=bindings, now="2026-05-12T09:00:00+00:00")
    blank = otm.update_from_observer_snapshot(tab=tab, snapshot=_snapshot(tab.url, []), bindings=bindings, now="2026-05-12T09:01:00+00:00")
    recovered = otm.update_from_observer_snapshot(tab=tab, snapshot=_snapshot(tab.url, turns), bindings=bindings, now="2026-05-12T09:02:00+00:00")

    assert blank["thread_memory_status"] == "empty_candidate"
    assert recovered["thread_memory_id"] == first["thread_memory_id"]
    assert "thread_reappeared_after_vanish" in _event_types()


def test_blank_then_different_content_rolls_over_new_thread(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    tab = _tab(target_id="target-roll", url="https://chatgpt.com/")
    old_turns = [_turn("user", "Continue", 0), _turn("assistant", "old", 1)]
    new_turns = [_turn("user", "Start a fresh research thread", 0), _turn("assistant", "new", 1)]

    first = otm.update_from_observer_snapshot(tab=tab, snapshot=_snapshot(tab.url, old_turns), bindings=bindings, now="2026-05-12T09:00:00+00:00")
    otm.update_from_observer_snapshot(tab=tab, snapshot=_snapshot(tab.url, []), bindings=bindings, now="2026-05-12T09:01:00+00:00")
    rolled = otm.update_from_observer_snapshot(tab=tab, snapshot=_snapshot(tab.url, new_turns), bindings=bindings, now="2026-05-12T09:02:00+00:00")

    assert rolled["thread_memory_id"] != first["thread_memory_id"]
    assert "thread_rollover_after_blank" in _event_types()


def test_repeated_prompt_detection_exact_normalized_and_structural(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    turns = [
        _turn("user", "Continue", 0),
        _turn("assistant", "one", 1),
        _turn("user", "Continue", 2),
        _turn("assistant", "two", 3),
        _turn("user", " continue ", 4),
        _turn("assistant", "three", 5),
        _turn("user", "`deliverable_type`: architecture decision\n`authority_boundary`: Type A must verify", 6),
        _turn("assistant", "four", 7),
        _turn("user", "`deliverable_type`: critique\n`authority_boundary`: Type A must verify", 8),
    ]

    otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/repeats", turns),
        hud_payload={"tab_order": 1},
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )

    record = json.loads((root / "threads" / "chatgpt_repeats.json").read_text(encoding="utf-8"))
    catalog = record["thread_prompt_catalog"]
    assert any("exact_repeat" in prompt["repeat_levels"] for prompt in catalog)
    assert any("normalized_repeat" in prompt["repeat_levels"] for prompt in catalog)
    assert any("structural_repeat" in prompt["repeat_levels"] for prompt in catalog)
    assert "type_b_packet_thread" in record["labels"]
    assert "main_shuttle_thread" in record["labels"]


def test_turn_stack_projection_separates_stacked_prompt_and_live_addendum() -> None:
    text = "\n\n".join([
        "# AGENTS.md instructions for /repo\n<INSTRUCTIONS>\nUse the live substrate.\n</INSTRUCTIONS>",
        "PACKET v=3.2\nthread: operator chrome capture\nstate_capsule: read_only\nEND_PACKET",
        "B2.2 semantic carryforward - high-ambition continuation\n\n"
        "Output contract: preserve the next Type A move.\n\n"
        "End with the next Type A move, not a recap.",
        "2:43 PMSo again, there are many more patterns to add; figure out the next move.Show moreShow less",
    ])

    projection = turn_projection.extract_turn_stack(text, include_private_previews=True)
    block_types = [block["block_type"] for block in projection["blocks"]]

    assert "constitutional_receiver_contract" in block_types
    assert "source_packet" in block_types
    assert "prompt_family_invocation" in block_types
    assert "operator_live_addendum" in block_types
    live = [block for block in projection["blocks"] if block["block_type"] == "operator_live_addendum"][0]
    assert "So again" in live["private_preview"]
    assert live["char_start"] > text.index("B2.2 semantic")


def test_turn_stack_projection_classifies_type_a_handoff_trace_and_review_paste() -> None:
    text = """`deliverable_type=continuation delta`; `authority_boundary=Type A must verify`; `integration_target=Operator Thread Memory`.

Worked for 19m 12s
Execution mode: direct_local.
I found a live captured B2.2 run that demonstrated the failure shape.
Edited 2 files
The private rebuild now finishes in about 15 seconds.

Implemented and committed the v1 semantic read model.

Validation:

./repo-pytest system/server/tests/test_operator_thread_memory.py -q => 16 passed
./repo-python -m py_compile tools/meta/observability/operator_turn_stack_projection.py => pass
operator_thread_memory.py --check => ok, metadata-only

Commit: c9ea3260a Add operator turn-stack projections

Scoped code/test paths are clean. Task Ledger files remain dirty from receipt/projection state and ambient ledger dirt.

Edited 3 files
+860
-25
Undo
Review
tools/meta/observability/operator_turn_stack_projection.py
#!/usr/bin/env python3
def sample() -> None:
    pass
system/server/tests/test_operator_thread_memory.py
def test_sample() -> None:
    assert True
3:14 PMShow moreShow less"""

    projection = turn_projection.extract_turn_stack(text, include_private_previews=True)
    block_types = [block["block_type"] for block in projection["blocks"]]

    assert "type_b_grounding_contract" in block_types
    assert "type_a_execution_trace" in block_types
    assert "implementation_summary" in block_types
    assert "validation_receipt" in block_types
    assert "commit_receipt" in block_types
    assert "ambient_dirty_boundary" in block_types
    assert "code_review_diff_projection" in block_types
    assert block_types.count("code_excerpt") == 2
    assert "operator_live_addendum" in block_types

    review = [block for block in projection["blocks"] if block["block_type"] == "code_review_diff_projection"][0]
    excerpt = [block for block in projection["blocks"] if block["block_type"] == "code_excerpt"][0]
    live = [block for block in projection["blocks"] if block["block_type"] == "operator_live_addendum"][0]
    assert review["char_start"] < excerpt["char_start"] < live["char_start"]
    assert review["nested_projection"] is True
    assert "c9ea3260a" in [
        block["private_preview"]
        for block in projection["blocks"]
        if block["block_type"] == "commit_receipt"
    ][0]


def test_turn_stack_projection_classifies_acceptance_trace_receipts() -> None:
    text = """`deliverable_type=continuation delta + acceptance/hardening plan`; `authority_boundary=Type A must verify`.

Worked for 11m 56s
Context automatically compacted
Steered conversation
Using bootstrap and navigation-metabolism for this turn. Execution mode: direct_local.

Explored 5 files
I reloaded the repo entry contract and the two relevant skills.

Explored 1 file, ran 7 commands
The entry packet confirms HEAD is currently c9ea3260a.

WorkItem ownership:

Bound receipt to cap_quick_operator_chrome_multi_tab_lineage_consol_34d5ab381ff9.
Task Ledger event: wie_20260515T143307Z_de33d7a5.
Transaction id: mtx_no_phase_cap_quick_operator_chrome_multi_tab_lineage_cons_63ec3dce_9e56470a.

Validation:

operator_thread_memory.py --check => ok: true, metadata-only

Commit: 5d682878cfa77154cfc85e02d1c32d5ca3f3d2e0

Scoped code/test paths are clean. Task Ledger files remain dirty from the receipt/projection rebuild.

3:33 PMShow moreShow less"""

    projection = turn_projection.extract_turn_stack(text, include_private_previews=True)
    block_types = [block["block_type"] for block in projection["blocks"]]

    assert block_types.count("conversation_control_event") == 2
    assert block_types.count("substrate_progress_receipt") == 2
    assert "workitem_binding_receipt" in block_types
    assert "validation_receipt" in block_types
    assert "commit_receipt" in block_types
    assert "operator_live_addendum" in block_types
    binding = [
        block for block in projection["blocks"]
        if block["block_type"] == "workitem_binding_receipt"
    ][0]
    assert binding["has_cap_ref"] is True
    assert binding["has_task_ledger_event"] is True
    assert binding["has_transaction_id"] is True


def test_turn_stack_projection_classifies_rendered_type_b_handoff_packet() -> None:
    text = """# Operator Thread Type B Handoff Packet

`deliverable_type=continuation delta`; `authority_boundary=Type B reasons from this metadata-only packet`.

## Freshness

- thread_id: `chatgpt_6a0724e0-736c-8397-b715-779e2ffb2410`
- card_fingerprint: `7543f8fbd9d2ff39b0956bac`
- export_profile: `operator_approved_external_type_b_handoff_v0`
- public_release_safe: `False`

## Ownership Refs

- cap_ids: `cap_quick_operator_chrome_multi_tab_lineage_consol_34d5ab381ff9`
- task_ledger_event_ids: `wie_20260515T171458Z_953f4b44`
- transaction_ids: `mtx_09_54_cap_quick_operator_chrome_multi_tab_lineage_cons_91a6b213_17bd2cc6`

## Type B Task

- card_only_sufficiency: `sufficient_for_type_b_next_move`
- expected_next_move: Use the continuation card as the default shuttle evidence object.
- If an exact private fact would change the answer, emit an ASK_TYPE_A handle instead of inventing it.

Continue from this handoff packet. What should Type A do next?"""

    projection = turn_projection.extract_turn_stack(text, include_private_previews=True)
    block_types = [block["block_type"] for block in projection["blocks"]]

    assert "operator_thread_type_b_handoff_packet" in block_types
    assert "workitem_binding_receipt" in block_types
    assert "operator_live_addendum" in block_types
    packet = [
        block for block in projection["blocks"]
        if block["block_type"] == "operator_thread_type_b_handoff_packet"
    ][0]
    live = [block for block in projection["blocks"] if block["block_type"] == "operator_live_addendum"][0]
    assert packet["export_profile_hint"] == "operator_approved_external_type_b_handoff_v0"
    assert live["char_start"] > packet["char_end"]
    assert "Continue from this handoff packet" in live["private_preview"]


def test_response_skeleton_extracts_decision_anatomy() -> None:
    text = """`deliverable_type=semantic carryforward`; `depth_floor=deep`; `authority_boundary=Type A verifies`; `integration_target=thread_memory`.

## Load-Bearing Abstraction

The load-bearing abstraction is turn stack projection.

## Best Composition Root

Use tools/meta/observability/operator_thread_memory.py and ./repo-python kernel.py --context-pack "operator".

## Risks And Anti-Goals

Do not build a new UI first.
"""

    skeleton = turn_projection.extract_response_skeleton(text, include_private_previews=True)

    assert skeleton["contract_fields"]["deliverable_type"] == "semantic carryforward"
    assert skeleton["decision_anatomy"]["has_load_bearing_abstraction"] is True
    assert skeleton["decision_anatomy"]["has_composition_root"] is True
    assert skeleton["decision_anatomy"]["has_risks_or_anti_goals"] is True
    assert skeleton["heading_count"] == 3
    assert any("operator_thread_memory.py" in path for path in skeleton["path_refs"])
    assert any(command.startswith("./repo-python kernel.py") for command in skeleton["command_refs"])


def test_thread_memory_adds_turn_stack_and_response_skeleton_metadata_only(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_TURN_STACK"
    bindings: dict[str, object] = {}
    turns = [
        _turn(
            "user",
            "PACKET v=3.2\nthread: sample\nEND_PACKET\n\n"
            "B2.2 semantic carryforward - high-ambition continuation\n\n"
            f"2:43 PM{private_text} live addendum",
            0,
        ),
        _turn(
            "assistant",
            "`deliverable_type=semantic carryforward`; `authority_boundary=Type A verifies`.\n\n"
            "## Load-Bearing Abstraction\n\n"
            "The load-bearing abstraction is private.\n\n"
            "## Risks And Anti-Goals\n\n"
            "Do not leak raw text.",
            1,
        ),
    ]

    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/semantic", turns),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )

    record = json.loads((root / "threads" / "chatgpt_semantic.json").read_text(encoding="utf-8"))
    assert meta["thread_turn_stack_count"] == 1
    assert meta["thread_response_skeleton_count"] == 1
    assert record["turn_stack_catalog"][0]["block_count"] >= 3
    assert record["response_skeleton_catalog"][0]["heading_count"] == 2
    assert record["thread_semantic_summary"]["turn_stack_count"] == 1

    index_text = (root / "index.json").read_text(encoding="utf-8")
    assert private_text not in index_text
    index = json.loads(index_text)
    row = index["threads"][0]
    assert row["turn_stack_count"] == 1
    assert row["response_skeleton_count"] == 1
    assert row["thread_semantic_summary"]["payload_policy"] == "metadata_only"
    assert "private_preview" not in json.dumps(row, sort_keys=True)


def test_thread_continuation_card_is_metadata_only_consumer(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_CONTINUATION_CARD"
    bindings: dict[str, object] = {}
    turns = [
        _turn(
            "user",
            "`deliverable_type=continuation delta`; `authority_boundary=Type A must verify`.\n\n"
            "Worked for 11m 56s\n"
            "Context automatically compacted\n"
            "Steered conversation\n"
            "Explored 5 files\n"
            f"{private_text}\n\n"
            "WorkItem ownership:\n\n"
            "Bound receipt to cap_quick_operator_chrome_multi_tab_lineage_consol_34d5ab381ff9.\n"
            "Task Ledger event: wie_20260515T143307Z_de33d7a5.\n"
            "Transaction id: mtx_no_phase_cap_quick_operator_chrome_multi_tab_lineage_cons_63ec3dce_9e56470a.\n\n"
            "Commit: 5d682878cfa77154cfc85e02d1c32d5ca3f3d2e0\n\n"
            "3:33 PMShow moreShow less",
            0,
        ),
        _turn(
            "assistant",
            "`deliverable_type=continuation delta`; `authority_boundary=Type A verifies`.\n\n"
            "## Load-Bearing Abstraction\n\n"
            "Use the continuation card projection and WorkItem receipt.",
            1,
        ),
    ]
    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/card", turns),
        bindings=bindings,
        now="2026-05-15T15:00:00+00:00",
    )

    card = otm.build_thread_continuation_card(str(meta["thread_memory_id"]))
    dumped = json.dumps(card, sort_keys=True)

    assert card["schema_version"] == "operator_thread_continuation_card_v0"
    assert card["payload_policy"] == "metadata_only"
    assert card["continuation_use"]["can_continue_without_raw_transcript"] is True
    assert "workitem_binding_receipt" in card["detected_receipt_types"]
    assert "conversation_control_event" in card["detected_receipt_types"]
    assert card["safe_reference_ids"]["cap_ids"] == [
        "cap_quick_operator_chrome_multi_tab_lineage_consol_34d5ab381ff9"
    ]
    assert card["safe_reference_ids"]["task_ledger_event_ids"] == [
        "wie_20260515T143307Z_de33d7a5"
    ]
    assert card["safe_reference_ids"]["transaction_ids"] == [
        "mtx_no_phase_cap_quick_operator_chrome_multi_tab_lineage_cons_63ec3dce_9e56470a"
    ]
    assert '"private_preview":' not in dumped
    assert "private_title" not in dumped
    assert private_text not in dumped


def test_type_b_handoff_packet_is_copyable_metadata_only(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_TYPE_B_HANDOFF_PACKET"
    turns = [
        _turn(
            "user",
            "`deliverable_type=continuation delta`; `authority_boundary=Type A must verify`.\n\n"
            "Context automatically compacted\n"
            "Explored 5 files\n"
            f"{private_text}\n\n"
            "Bound receipt to cap_quick_operator_chrome_multi_tab_lineage_consol_34d5ab381ff9.\n"
            "Task Ledger event: wie_20260515T143307Z_de33d7a5.\n"
            "Transaction id: mtx_no_phase_cap_quick_operator_chrome_multi_tab_lineage_cons_63ec3dce_9e56470a.\n"
            "Commit: 5d682878cfa77154cfc85e02d1c32d5ca3f3d2e0\n",
            0,
        ),
        _turn(
            "assistant",
            "`deliverable_type=continuation delta`; `authority_boundary=Type A verifies`.\n\n"
            "## Reversible Next Wave\n\n"
            "Use the continuation card as the composition root and preserve the WorkItem candidate.",
            1,
        ),
    ]
    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/handoff", turns),
        bindings={},
        now="2026-05-15T15:00:00+00:00",
    )

    packet = otm.build_type_b_handoff_packet(str(meta["thread_memory_id"]))
    markdown = otm.render_type_b_handoff_markdown(packet)
    dumped = json.dumps(packet, sort_keys=True)

    assert packet["schema_version"] == "operator_thread_type_b_handoff_packet_v0"
    assert packet["export_policy"]["metadata_only"] is True
    assert packet["export_policy"]["public_release_safe"] is False
    assert packet["privacy_scan"]["status"] == "clean"
    assert packet["card_only_sufficiency"]["status"] == "sufficient_for_type_b_next_move"
    assert packet["ownership_refs"]["safe_reference_ids"]["cap_ids"] == [
        "cap_quick_operator_chrome_multi_tab_lineage_consol_34d5ab381ff9"
    ]
    assert "workitem_binding_receipt" in packet["card_summary"]["detected_receipt_types"]
    assert "has_reversible_next_wave" in packet["card_summary"]["response_anatomy_flags"]
    assert "Operator Thread Type B Handoff Packet" in markdown
    assert "expected_next_move" in markdown
    assert '"private_preview":' not in dumped
    assert "private_title" not in dumped
    assert "raw_turn_text" not in dumped
    assert private_text not in dumped
    assert private_text not in markdown


def test_thread_progress_pairs_operator_additions_with_assistant_responses(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_THREAD_PROGRESS"
    turns = [
        _turn(
            "user",
            "`deliverable_type=continuation delta`; `authority_boundary=Type A must verify`.\n\n"
            "B2.2 semantic carryforward - high-ambition continuation\n\n"
            f"2:43 PM{private_text} operator adds the live constraint",
            0,
        ),
        _turn(
            "assistant",
            "`deliverable_type=continuation delta`; `authority_boundary=Type A verifies`.\n\n"
            "## Reversible Next Wave\n\n"
            "Build the thread progress projection and keep raw text private.",
            1,
        ),
    ]
    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/progress", turns),
        bindings={},
        now="2026-05-15T15:00:00+00:00",
    )

    progress = otm.build_thread_progress(str(meta["thread_memory_id"]), recent_limit=0)
    dumped = json.dumps(progress, sort_keys=True)
    step = progress["progression"][0]
    operator_row = step["operator_addition"]
    response_row = step["assistant_responses"][0]

    assert progress["schema_version"] == "operator_thread_progress_v0"
    assert progress["payload_policy"] == "metadata_only"
    assert progress["progression_count"] == 1
    assert operator_row["operator_live_addendum"]["detected"] is True
    assert "operator_live_addendum_detected" in step["progress_cues"]
    assert "response:has_reversible_next_wave" in step["progress_cues"]
    assert "has_reversible_next_wave" in response_row["decision_anatomy_true"]
    assert '"private_preview":' not in dumped
    assert private_text not in dumped

    private_progress = otm.build_thread_progress(
        str(meta["thread_memory_id"]),
        recent_limit=0,
        include_private_previews=True,
    )
    assert private_progress["payload_policy"] == "explicit_private_preview"
    assert private_text in json.dumps(private_progress, sort_keys=True)


def test_thread_progress_index_writes_metadata_only_json_and_markdown(tmp_path, monkeypatch) -> None:
    root = _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_PROGRESS_INDEX"
    turns = [
        _turn("user", f"Continue\n\n2:43 PM{private_text}", 0),
        _turn("assistant", "## Reversible Next Wave\n\nKeep the projection metadata-only.", 1),
    ]
    otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/progress-index", turns),
        bindings={},
        now="2026-05-15T15:00:00+00:00",
    )

    payload = otm.build_thread_progress_index(limit=5, recent_limit=3)
    paths = otm.write_thread_progress_projection(payload)
    json_text = (root / "thread_progress.json").read_text(encoding="utf-8")
    markdown_text = (root / "thread_progress.md").read_text(encoding="utf-8")
    check = otm.check_privacy_boundary()

    assert paths["json_path"].endswith("thread_progress.json")
    assert payload["schema_version"] == "operator_thread_progress_index_v0"
    assert payload["thread_count"] == 1
    assert "# Operator Thread Progress" in markdown_text
    assert private_text not in json_text
    assert private_text not in markdown_text
    assert check["ok"] is True
    assert check["private_payload_key_findings"]["thread_progress"] == []


def test_lesson_candidates_are_advisory_only(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    bindings: dict[str, object] = {}
    turns = [_turn("user", "`deliverable_type`: architecture decision\n`authority_boundary`: Type A must verify", 0)]
    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/lesson", turns),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )

    packet = otm.build_lesson_candidate_packet(str(meta["thread_memory_id"]))

    assert packet["status"] == "advisory_only"
    assert packet["mutation_allowed"] is False
    assert "Prompt Ledger" in packet["suggested_routes"]
    assert "WorkItem" in packet["suggested_routes"]
    assert packet["route_contract"]["adoption_event_type"] == "prompt_trace.adoption_state_changed"


def test_lesson_candidates_are_metadata_only_by_default(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_LESSON_CANDIDATE"
    bindings: dict[str, object] = {}
    turns = [
        _turn(
            "user",
            f"`deliverable_type`: architecture decision\n{private_text}\n`authority_boundary`: Type A must verify",
            0,
        )
    ]
    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/private-candidate", turns),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )

    packet = otm.build_lesson_candidate_packet(str(meta["thread_memory_id"]))
    packet_text = json.dumps(packet, sort_keys=True)

    assert private_text not in packet_text
    assert "evidence_private_excerpt" not in packet_text
    candidate = packet["candidates"][0]
    assert candidate["evidence_ref"]["raw_text_stored"] is False
    assert candidate["privacy"]["raw_text_stored"] is False
    assert candidate["privacy"]["private_excerpt_included"] is False
    assert candidate["point_of_use_surface"] == "state/prompt_ledger/views/adoption_posture.json"


def test_lesson_candidate_private_excerpts_require_explicit_opt_in(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_EXPLICIT_EXCERPT"
    bindings: dict[str, object] = {}
    turns = [_turn("user", f"Continue\n{private_text}", 0)]
    meta = otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/private-excerpt", turns),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )

    packet = otm.build_lesson_candidate_packet(
        str(meta["thread_memory_id"]),
        include_private_excerpts=True,
    )

    assert packet["privacy"]["private_excerpt_included"] is True
    assert private_text in json.dumps(packet, sort_keys=True)
    assert packet["candidates"][0]["evidence_private_excerpt"]


def test_lesson_candidate_index_and_check_are_metadata_only(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    private_text = "SENTINEL_" "PRIVATE_INDEX_CHECK"
    bindings: dict[str, object] = {}
    turns = [_turn("user", f"Continue\n{private_text}", 0)]
    otm.update_from_observer_snapshot(
        tab=_tab(),
        snapshot=_snapshot("https://chatgpt.com/c/private-index", turns),
        bindings=bindings,
        now="2026-05-12T09:00:00+00:00",
    )

    index = otm.build_lesson_candidate_index()
    check = otm.check_privacy_boundary()

    assert index["candidate_count"] == 1
    assert private_text not in json.dumps(index, sort_keys=True)
    assert index["payload_policy"] == "metadata_only"
    assert check["ok"] is True
    assert check["lesson_candidate_payload_policy"] == "metadata_only"


def test_observer_full_scan_adds_thread_memory_metadata_without_raw_text(tmp_path, monkeypatch) -> None:
    _configure_private_root(tmp_path, monkeypatch)
    monkeypatch.setattr(obs_mod, "OPERATOR_TAB_OBSERVATION_PATH", tmp_path / "tab_observations.json")
    private_text = "SENTINEL_" "PRIVATE_TRANSCRIPT_TEXT"
    tab = obs_mod.TabInfo(
        target_id="target-observer",
        title="ChatGPT",
        url="https://chatgpt.com/c/observer",
        websocket_path="/devtools/page/target-observer",
    )
    snapshot = obs_mod.TabSnapshot(
        url=tab.url,
        title="ChatGPT",
        generating=False,
        turns=[
            {"role": "user", "text": f"Continue {private_text}", "message_id": "u1", "ordinal": 0},
            {"role": "assistant", "text": "private answer", "message_id": "a1", "ordinal": 1},
        ],
        fetched_at="2026-05-12T09:00:00+00:00",
    )
    monkeypatch.setattr(obs_mod, "snapshot_tab", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(obs_mod, "evaluate_tab", lambda *_args, **_kwargs: (None, None))

    state = obs_mod.ObserverState()
    contexts, errors = obs_mod.collect_hud_contexts(
        [tab],
        [],
        state,
        status="observer_test",
        operator_pages=[{
            "target_id": tab.target_id,
            "title": tab.title,
            "url": tab.url,
            "host": "chatgpt.com",
            "tab_kind": "chatgpt",
            "is_chatgpt": True,
            "tab_order": 1,
            "visual_order_known": True,
        }],
    )

    assert errors == []
    payload = contexts[0]["hud_payload"]
    thread_fields = {
        key: value
        for key, value in payload.items()
        if key.startswith("thread_memory") or key == "thread_prompt_count"
    }
    assert thread_fields["thread_memory_id"] == "chatgpt_observer"
    assert payload["turn_count"] == 1
    assert payload["turn_count_basis"] == "thread_memory_user_turn_count"
    assert payload["operator_size_label"].endswith("1 turn")
    assert private_text not in json.dumps(thread_fields)
    tab_observation = json.loads((tmp_path / "tab_observations.json").read_text(encoding="utf-8"))
    assert tab_observation["current_tabs"][0]["thread_memory_id"] == "chatgpt_observer"
    assert private_text not in json.dumps(tab_observation)
