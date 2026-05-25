"""Tests for prompt_shelf_movement_index — sibling pipeline to v3 uppropagation.

Coverage of std_aiw_movement_v1 contract after parser hardening:
- single terminal movement block before final v3 parses with all 10 fields
- multiple terminal movement blocks before final v3 each parse as separate records
- recurrence_key is preserved verbatim (the killer feature for cross-row clustering)
- missing required fields surface as block-level warnings
- nested movement-inside-uppropagation: WARNED + EXCLUDED from records
- unknown block version is warned but record is still produced
- duplicate recurrence_key in the same run is warned

Coverage of NEW terminal-cluster placement rule:
- non-terminal movement blocks (separated from final v3 by prose) are EXCLUDED with advisory warning
- movement blocks AFTER the final v3 footer are EXCLUDED with advisory warning
- movement blocks WITHOUT any v3 anchor are EXCLUDED with advisory warning
- two contiguous movement blocks before v3 are BOTH terminal

Coverage of --validate semantic-mode:
- exits zero on clean terminal placement
- exits nonzero on nested
- exits nonzero on missing required field
- exits nonzero on unknown version
- exits nonzero on duplicate recurrence_key
- does NOT exit nonzero on non-terminal advisory warnings alone
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "meta" / "observability"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import prompt_shelf_movement_index as mv_mod  # noqa: E402


def _patch_roots(monkeypatch, tmp_path: Path) -> Path:
    repo = tmp_path
    raw_root = repo / "obsidian" / "prompt_shelf" / "usage" / "raw_events"
    monkeypatch.setattr(mv_mod, "REPO_ROOT", repo)
    monkeypatch.setattr(mv_mod, "RAW_EVENTS_ROOT", raw_root)
    monkeypatch.setattr(mv_mod, "INDEX_PATH", repo / "state" / "prompt_shelf" / "movement_index.json")
    return raw_root


def _write_event(raw_root: Path, slot_dir: str, run_id: str, assistant_text: str, *, user_text: str = "") -> Path:
    path = raw_root / slot_dir / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "event_kind": "prompt_shelf_run_raw",
        "prompt_run_id": run_id,
        "prompt_slot": run_id.split("--")[1] if "--" in run_id else "B2",
        "prompt_slug": "continue_intelligently",
        "captured_at": "2026-04-27T02:00:00+00:00",
        "conversation_id": "conv-abc",
        "user_message": {
            "raw_text": user_text,
            "sha256": "u" * 64,
        },
        "assistant_message": {
            "raw_text": assistant_text,
            "sha256": "a" * 64,
        },
    }
    path.write_text(json.dumps(payload))
    return path


def _movement_block(
    *,
    source_signal="lesson",
    signal_kind="standard_pressure",
    recurrence_key="example_key",
    owning_plane="standard",
    availability_result="build_new",
    movement="mint_candidate",
    promotion_boundary="candidate_only",
    evidence_anchor="path/to/file.json",
    validation_target="pytest target",
    do_not_do="do not couple movement to v3 lifecycle.",
) -> str:
    return f"""<!-- aiw:movement v=1 -->
source_signal: {source_signal}
signal_kind: {signal_kind}
recurrence_key: {recurrence_key}
owning_plane: {owning_plane}
availability_result: {availability_result}
movement: {movement}
promotion_boundary: {promotion_boundary}
evidence_anchor: {evidence_anchor}
validation_target: {validation_target}
do_not_do: {do_not_do}
<!-- /aiw:movement -->"""


def _v3_footer(slot="B2: continue_intelligently") -> str:
    return f"""<!-- aiw:uppropagation v=3 -->
prompt_received: {slot}
prompt_interpretation: example interpretation
lesson: example lesson
self_prompting_idea: example idea
information_demand: example demand
prompt_friction:
system_friction:
confidence: high
<!-- /aiw:uppropagation -->"""


def _terminal_assistant(movement_blocks: list[str], slot: str = "B2: continue_intelligently") -> str:
    """Build an assistant message where movement_blocks form the terminal cluster
    immediately before the final v3 footer (whitespace-only gaps)."""
    return "\n\n".join(movement_blocks) + "\n\n" + _v3_footer(slot)


# -------- Tests of terminal-cluster parsing --------


def test_parses_one_terminal_movement_block(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root, "B2_continue", "20260427T020000000000--B2--abc12345",
        assistant_text=_terminal_assistant([_movement_block()]),
    )
    index = mv_mod.build_index()
    assert index["__meta"]["movement_blocks_total"] == 1
    assert index["__meta"]["events_with_block"] == 1
    assert len(index["records"]) == 1
    rec = index["records"][0]
    for fname in mv_mod.REQUIRED_FIELDS_V1:
        assert rec["field_status"][fname] == "filled", f"{fname} should be filled"
    assert rec["block_v"] == 1
    assert rec["block_index"] == 0
    assert rec["block_count"] == 1
    assert rec["fields"]["source_signal"] == "lesson"
    assert rec["fields"]["recurrence_key"] == "example_key"
    assert rec["warnings"] == []


def test_two_contiguous_terminal_movement_blocks_both_recorded(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = _terminal_assistant([
        _movement_block(recurrence_key="signal_one", source_signal="lesson"),
        _movement_block(recurrence_key="signal_two", source_signal="self_prompting_idea"),
    ])
    _write_event(
        raw_root, "B2_continue", "20260427T021000000000--B2--ghi11111",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    assert index["__meta"]["movement_blocks_total"] == 2
    assert len(index["records"]) == 2
    keys = sorted(r["fields"]["recurrence_key"] for r in index["records"])
    assert keys == ["signal_one", "signal_two"]


def test_three_contiguous_terminal_movement_blocks_all_recorded(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = _terminal_assistant([
        _movement_block(recurrence_key="signal_one"),
        _movement_block(recurrence_key="signal_two", source_signal="self_prompting_idea"),
        _movement_block(recurrence_key="signal_three", source_signal="information_demand"),
    ])
    _write_event(
        raw_root, "B2_continue", "20260427T022000000000--B2--ggg22222",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    assert index["__meta"]["movement_blocks_total"] == 3
    assert len(index["records"]) == 3
    indexes = [r["block_index"] for r in index["records"]]
    assert indexes == [0, 1, 2]


def test_recurrence_key_preserved_exactly(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    key = "availability_before_invention_axiom_v1"
    _write_event(
        raw_root, "B2_continue", "20260427T023000000000--B2--jkl22222",
        assistant_text=_terminal_assistant([_movement_block(recurrence_key=key)]),
    )
    index = mv_mod.build_index()
    rec = index["records"][0]
    assert rec["fields"]["recurrence_key"] == key
    assert key in index["rollups"]["recurrence_keys"]
    assert index["rollups"]["recurrence_keys"][key] == 1


def test_missing_required_field_produces_block_warning(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    incomplete_block = """<!-- aiw:movement v=1 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: incomplete_block
owning_plane: standard
availability_result: build_new
movement: mint_candidate
promotion_boundary: candidate_only
evidence_anchor: path/to/file.json
<!-- /aiw:movement -->"""  # missing validation_target and do_not_do
    _write_event(
        raw_root, "B2_continue", "20260427T024000000000--B2--mno33333",
        assistant_text=incomplete_block + "\n\n" + _v3_footer(),
    )
    index = mv_mod.build_index()
    rec = index["records"][0]
    missing_fields = [w["field"] for w in rec["warnings"] if w["kind"] == "missing_required_field"]
    assert "validation_target" in missing_fields
    assert "do_not_do" in missing_fields
    assert rec["field_status"]["validation_target"] == "missing"
    assert rec["field_status"]["do_not_do"] == "missing"


def test_nested_movement_inside_uppropagation_warned_and_excluded(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    nested_body = """<!-- aiw:uppropagation v=3 -->
prompt_received: B2: continue_intelligently
prompt_interpretation: nested test
lesson: nested-test lesson
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: high
<!-- aiw:movement v=1 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: forbidden_nested
owning_plane: standard
availability_result: watch
movement: watch
promotion_boundary: observed_only
evidence_anchor: nested test
validation_target: nesting detector test
do_not_do: do not nest movement inside uppropagation.
<!-- /aiw:movement -->
<!-- /aiw:uppropagation -->"""
    _write_event(
        raw_root, "B2_continue", "20260427T025000000000--B2--pqr44444",
        assistant_text=nested_body,
    )
    index = mv_mod.build_index()
    nested_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "nested_movement_inside_uppropagation"
    ]
    assert len(nested_warnings) == 1
    # Nested blocks are EXCLUDED from records (semantic violation).
    assert index["__meta"]["movement_blocks_total"] == 0
    assert index["records"] == []


def test_unknown_version_warned(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    bad_version_block = """<!-- aiw:movement v=2 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: future_version_test
owning_plane: standard
availability_result: build_new
movement: mint_candidate
promotion_boundary: candidate_only
evidence_anchor: future test
validation_target: version detector
do_not_do: do not introduce v2 without a migration plan.
<!-- /aiw:movement -->"""
    _write_event(
        raw_root, "B2_continue", "20260427T026000000000--B2--stu55555",
        assistant_text=bad_version_block + "\n\n" + _v3_footer(),
    )
    index = mv_mod.build_index()
    unknown_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "unknown_version"
    ]
    assert len(unknown_warnings) == 1
    assert unknown_warnings[0]["version"] == 2
    assert unknown_warnings[0]["supported"] == [1]
    # Record is still produced for unknown-version blocks (terminal placement honored).
    assert index["__meta"]["movement_blocks_total"] == 1


def test_duplicate_recurrence_key_in_same_run_warned(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = _terminal_assistant([
        _movement_block(recurrence_key="duplicate_key", source_signal="lesson"),
        _movement_block(recurrence_key="duplicate_key", source_signal="self_prompting_idea"),
    ])
    _write_event(
        raw_root, "B2_continue", "20260427T027000000000--B2--vwx66666",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    dup_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "duplicate_recurrence_key_in_same_run"
    ]
    assert len(dup_warnings) == 1
    assert dup_warnings[0]["recurrence_key"] == "duplicate_key"
    assert dup_warnings[0]["block_indexes"] == [0, 1]
    assert index["__meta"]["movement_blocks_total"] == 2


def test_no_movement_block_skips_record(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root, "B2_continue", "20260427T028000000000--B2--yza77777",
        assistant_text="A response with no movement sidecar.\n\n" + _v3_footer(),
    )
    index = mv_mod.build_index()
    assert index["__meta"]["movement_blocks_total"] == 0
    assert index["records"] == []
    assert index["run_warnings"] == []


# -------- Tests of NEW terminal-cluster placement rule --------


def test_non_terminal_movement_example_in_prose_is_excluded(tmp_path, monkeypatch):
    """Movement blocks separated from final v3 by non-whitespace prose are quoted
    examples / templates, not emitted telemetry. They MUST be excluded from records."""
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = (
        "Here is an example of how to write a movement sidecar:\n\n"
        + _movement_block(recurrence_key="example_template_in_prose")
        + "\n\nNow here is the actual emitted sidecar:\n\n"
        + _movement_block(recurrence_key="actual_terminal_signal")
        + "\n\n"
        + _v3_footer()
    )
    _write_event(
        raw_root, "B2_continue", "20260427T030000000000--B2--abc88888",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    # Only the terminal block is recorded.
    assert index["__meta"]["movement_blocks_total"] == 1
    assert index["records"][0]["fields"]["recurrence_key"] == "actual_terminal_signal"
    # The non-terminal example is reported as advisory warning.
    non_terminal_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "non_terminal_movement_block_ignored"
    ]
    assert len(non_terminal_warnings) == 1


def test_movement_after_final_v3_warned_and_excluded(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = (
        _v3_footer()
        + "\n\nA stray movement block appears after the final v3 footer:\n\n"
        + _movement_block(recurrence_key="post_v3_stray")
    )
    _write_event(
        raw_root, "B2_continue", "20260427T031000000000--B2--cde99999",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    assert index["__meta"]["movement_blocks_total"] == 0
    assert index["records"] == []
    after_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "movement_after_final_uppropagation"
    ]
    assert len(after_warnings) == 1


def test_movement_without_final_v3_warned_and_excluded(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = _movement_block(recurrence_key="orphan_no_v3")
    _write_event(
        raw_root, "B2_continue", "20260427T032000000000--B2--def00000",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    assert index["__meta"]["movement_blocks_total"] == 0
    assert index["records"] == []
    no_anchor_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "movement_without_final_uppropagation"
    ]
    assert len(no_anchor_warnings) == 1


# -------- Tests of --validate semantic-mode --------


def test_validate_zero_on_clean_terminal_placement(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root, "B2_continue", "20260427T033000000000--B2--ghi11000",
        assistant_text=_terminal_assistant([_movement_block()]),
    )
    index = mv_mod.build_index()
    violations = mv_mod.collect_semantic_violations(index)
    assert violations == []


def test_validate_nonzero_on_nested(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    nested_body = """<!-- aiw:uppropagation v=3 -->
prompt_received: B2
lesson: nested
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: high
<!-- aiw:movement v=1 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: nested_violation
owning_plane: standard
availability_result: watch
movement: watch
promotion_boundary: observed_only
evidence_anchor: nested
validation_target: validate_nonzero_on_nested
do_not_do: do not nest.
<!-- /aiw:movement -->
<!-- /aiw:uppropagation -->"""
    _write_event(
        raw_root, "B2_continue", "20260427T034000000000--B2--jkl22000",
        assistant_text=nested_body,
    )
    index = mv_mod.build_index()
    violations = mv_mod.collect_semantic_violations(index)
    nested_count = sum(1 for v in violations if v["kind"] == "nested_movement_inside_uppropagation")
    assert nested_count == 1


def test_validate_nonzero_on_missing_required_field(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    incomplete_block = """<!-- aiw:movement v=1 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: missing_fields_validate
owning_plane: standard
availability_result: build_new
movement: mint_candidate
promotion_boundary: candidate_only
evidence_anchor: path
<!-- /aiw:movement -->"""  # missing validation_target and do_not_do
    _write_event(
        raw_root, "B2_continue", "20260427T035000000000--B2--mno33000",
        assistant_text=incomplete_block + "\n\n" + _v3_footer(),
    )
    index = mv_mod.build_index()
    violations = mv_mod.collect_semantic_violations(index)
    missing_violations = [v for v in violations if v["kind"] == "missing_required_field"]
    assert len(missing_violations) >= 2  # at least validation_target and do_not_do


def test_validate_nonzero_on_unknown_version(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    bad_version_block = """<!-- aiw:movement v=2 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: bad_version_validate
owning_plane: standard
availability_result: build_new
movement: mint_candidate
promotion_boundary: candidate_only
evidence_anchor: future
validation_target: validate_unknown_version
do_not_do: do not introduce v2 without a migration plan.
<!-- /aiw:movement -->"""
    _write_event(
        raw_root, "B2_continue", "20260427T036000000000--B2--pqr44000",
        assistant_text=bad_version_block + "\n\n" + _v3_footer(),
    )
    index = mv_mod.build_index()
    violations = mv_mod.collect_semantic_violations(index)
    assert any(v["kind"] == "unknown_version" for v in violations)


def test_validate_nonzero_on_duplicate_recurrence_key(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = _terminal_assistant([
        _movement_block(recurrence_key="dup_key_validate", source_signal="lesson"),
        _movement_block(recurrence_key="dup_key_validate", source_signal="self_prompting_idea"),
    ])
    _write_event(
        raw_root, "B2_continue", "20260427T037000000000--B2--stu55000",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    violations = mv_mod.collect_semantic_violations(index)
    assert any(v["kind"] == "duplicate_recurrence_key_in_same_run" for v in violations)


def test_validate_zero_on_non_terminal_advisory_only(tmp_path, monkeypatch):
    """Non-terminal blocks are advisory; --validate should NOT fail just because a
    quoted example exists. Only true semantic violations cause --validate to fail."""
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = (
        "Example: \n\n"
        + _movement_block(recurrence_key="non_terminal_example")
        + "\n\nReal one:\n\n"
        + _movement_block(recurrence_key="real_terminal_signal")
        + "\n\n"
        + _v3_footer()
    )
    _write_event(
        raw_root, "B2_continue", "20260427T038000000000--B2--vwx66000",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    # The non-terminal advisory is in run_warnings but NOT a semantic violation.
    non_terminal_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "non_terminal_movement_block_ignored"
    ]
    assert len(non_terminal_warnings) == 1
    # --validate semantic check passes (no nested / missing / unknown / duplicate).
    violations = mv_mod.collect_semantic_violations(index)
    assert violations == []


# -------- Pipeline-independence + drift-check sanity --------


def test_check_mode_returns_clean_after_write(tmp_path, monkeypatch):
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event(
        raw_root, "B2_continue", "20260427T039000000000--B2--bcd88000",
        assistant_text=_terminal_assistant([_movement_block(recurrence_key="check_mode_test")]),
    )
    index = mv_mod.build_index()
    rendered = mv_mod.render_canonical(index)
    mv_mod.INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    mv_mod.INDEX_PATH.write_text(rendered)
    fresh = mv_mod.build_index()
    on_disk = json.loads(mv_mod.INDEX_PATH.read_text())
    on_disk["__meta"].pop("generated_at", None)
    fresh_copy = json.loads(mv_mod.render_canonical(fresh))
    fresh_copy["__meta"].pop("generated_at", None)
    assert json.dumps(on_disk, sort_keys=True) == json.dumps(fresh_copy, sort_keys=True)


# -------- Tests of --validate --since cutover --------


def _write_event_with_captured_at(
    raw_root: Path, slot_dir: str, run_id: str, assistant_text: str, captured_at: str,
) -> Path:
    """Variant of _write_event with explicit captured_at — needed for cutover tests."""
    path = raw_root / slot_dir / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "event_kind": "prompt_shelf_run_raw",
        "prompt_run_id": run_id,
        "prompt_slot": run_id.split("--")[1] if "--" in run_id else "B2",
        "prompt_slug": "continue_intelligently",
        "captured_at": captured_at,
        "conversation_id": "conv-abc",
        "user_message": {"raw_text": "", "sha256": "u" * 64},
        "assistant_message": {"raw_text": assistant_text, "sha256": "a" * 64},
    }
    path.write_text(json.dumps(payload))
    return path


def _nested_movement_body() -> str:
    return """<!-- aiw:uppropagation v=3 -->
prompt_received: B2
lesson: nested
self_prompting_idea:
information_demand:
prompt_friction:
system_friction:
confidence: high
<!-- aiw:movement v=1 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: cutover_test_nested
owning_plane: standard
availability_result: watch
movement: watch
promotion_boundary: observed_only
evidence_anchor: cutover test
validation_target: --since cutover policy
do_not_do: do not nest.
<!-- /aiw:movement -->
<!-- /aiw:uppropagation -->"""


def test_validate_since_after_historical_capture_passes(tmp_path, monkeypatch):
    """Historical violation predates cutoff → --since excludes it; result valid."""
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event_with_captured_at(
        raw_root, "B2_continue", "20260101T000000000000--B2--early0001",
        assistant_text=_nested_movement_body(),
        captured_at="2026-01-01T00:00:00+00:00",
    )
    # Add a clean post-cutoff event so the index is not empty.
    _write_event_with_captured_at(
        raw_root, "B2_continue", "20260601T000000000000--B2--late00001",
        assistant_text=_terminal_assistant([_movement_block(recurrence_key="post_cutoff_clean")]),
        captured_at="2026-06-01T00:00:00+00:00",
    )
    index = mv_mod.build_index()
    # All-history validate fails (historical violation present).
    all_history = mv_mod.collect_semantic_violations(index)
    assert any(v["kind"] == "nested_movement_inside_uppropagation" for v in all_history)
    # Post-cutoff validate passes (since 2026-03-01 excludes the January historical event).
    post_cutoff = mv_mod.collect_semantic_violations(index, since="2026-03-01T00:00:00+00:00")
    assert post_cutoff == [], f"unexpected post-cutoff violations: {post_cutoff}"


def test_validate_since_before_historical_capture_still_fails(tmp_path, monkeypatch):
    """Cutoff predates the violation → --since does NOT exclude it; result invalid."""
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event_with_captured_at(
        raw_root, "B2_continue", "20260601T000000000000--B2--violator1",
        assistant_text=_nested_movement_body(),
        captured_at="2026-06-01T00:00:00+00:00",
    )
    index = mv_mod.build_index()
    # Cutoff in 2025 is before the 2026 violation; violation is at-or-after cutoff,
    # so it remains in the failure set.
    violations = mv_mod.collect_semantic_violations(index, since="2025-01-01T00:00:00+00:00")
    assert any(v["kind"] == "nested_movement_inside_uppropagation" for v in violations)


def test_validate_since_does_not_mask_post_cutoff_missing_required_field(tmp_path, monkeypatch):
    """A new violation (missing required field) AFTER the cutoff must still cause failure."""
    raw_root = _patch_roots(monkeypatch, tmp_path)
    incomplete_block = """<!-- aiw:movement v=1 -->
source_signal: lesson
signal_kind: standard_pressure
recurrence_key: post_cutoff_missing
owning_plane: standard
availability_result: build_new
movement: mint_candidate
promotion_boundary: candidate_only
evidence_anchor: path
<!-- /aiw:movement -->"""  # missing validation_target and do_not_do
    _write_event_with_captured_at(
        raw_root, "B2_continue", "20260701T000000000000--B2--postmiss1",
        assistant_text=incomplete_block + "\n\n" + _v3_footer(),
        captured_at="2026-07-01T00:00:00+00:00",
    )
    index = mv_mod.build_index()
    # Cutoff in March; missing-field event in July is after cutoff and must still fail.
    violations = mv_mod.collect_semantic_violations(index, since="2026-03-01T00:00:00+00:00")
    assert any(v["kind"] == "missing_required_field" for v in violations)


def test_run_warnings_carry_captured_at_for_filtering(tmp_path, monkeypatch):
    """Each run_warning must include captured_at so cutover filtering doesn't re-read files."""
    raw_root = _patch_roots(monkeypatch, tmp_path)
    _write_event_with_captured_at(
        raw_root, "B2_continue", "20260415T000000000000--B2--metadata1",
        assistant_text=_nested_movement_body(),
        captured_at="2026-04-15T00:00:00+00:00",
    )
    index = mv_mod.build_index()
    nested_warnings = [
        w for w in index["run_warnings"]
        if w["kind"] == "nested_movement_inside_uppropagation"
    ]
    assert len(nested_warnings) == 1
    w = nested_warnings[0]
    assert w["captured_at"] == "2026-04-15T00:00:00+00:00"
    assert w["raw_event_path"]
    assert w["prompt_run_id"]


def test_v3_uppropagation_index_unchanged_by_movement_pipeline(tmp_path, monkeypatch):
    """The two pipelines must not interfere. A movement block in an assistant message
    must NOT cause the v3 indexer to misbehave; a v3 block must NOT cause the movement
    indexer to consume it. This test exercises the movement side; the v3 side is
    covered by its own existing test file."""
    raw_root = _patch_roots(monkeypatch, tmp_path)
    body = _terminal_assistant([_movement_block(recurrence_key="independence_test")])
    _write_event(
        raw_root, "B2_continue", "20260427T040000000000--B2--efg99000",
        assistant_text=body,
    )
    index = mv_mod.build_index()
    assert index["__meta"]["movement_blocks_total"] == 1
    rec = index["records"][0]
    assert rec["fields"]["recurrence_key"] == "independence_test"
    assert rec["fields"]["source_signal"] == "lesson"  # field VALUE happens to be 'lesson'
