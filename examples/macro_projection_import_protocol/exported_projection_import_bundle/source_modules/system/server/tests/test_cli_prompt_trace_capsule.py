from tools.meta.observability import cli_prompt_trace as trace
from tools.meta.observability.cli_prompt_trace import (
    ToolEvent,
    Turn,
    merge_full_thread,
    render_thread_closeout_report,
    render_trace_capsule_text,
)


def _event(index: int, cmd: str, exit_code: int, output_text: str = "") -> ToolEvent:
    return ToolEvent(
        index=index,
        name="exec_command",
        input={"cmd": cmd},
        tool_call_id=None,
        started_at=None,
        completed_at=None,
        duration_ms=None,
        is_error=exit_code != 0,
        output_text=output_text,
        output_char_count=len(output_text),
        output_sha256_16="",
        exit_code=exit_code,
    )


def _turn(
    events: list[ToolEvent],
    *,
    turn_index: int = 1,
    prompt_text: str = "test prompt",
    assistant_text: str = "done",
) -> Turn:
    return Turn(
        provider="codex",
        session_id="session-for-test",
        session_file="/tmp/session.jsonl",
        turn_id=f"turn-for-test-{turn_index}",
        turn_index=turn_index,
        cwd=None,
        started_at=None,
        completed_at=f"2026-05-24T00:0{turn_index}:00+00:00",
        prompt_text=prompt_text,
        prompt_char_count=len(prompt_text),
        prompt_sha256_16=f"promptsha{turn_index}",
        tool_events=events,
        assistant_text=assistant_text,
        is_complete=True,
    )


def test_trace_capsule_final_validation_uses_terminal_validation_rows() -> None:
    repeated = "./repo-pytest system/server/tests/test_example.py"
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, repeated, 1),
                _event(2, repeated, 0),
                _event(3, "python -m py_compile tools/example.py", 0),
            ]
        ),
        title="terminal validation test",
    )

    assert "final_validation: passed" in text
    assert "checks: pass=2 fail=1 other=0 total=3" in text
    assert "terminal_checks: pass=2 fail=0 other=0 total=2" in text
    assert meta["terminal_validation_count"] == 2
    assert meta["terminal_validation_fail_count"] == 0


def test_trace_capsule_keeps_needs_review_when_terminal_row_fails() -> None:
    repeated = "./repo-pytest system/server/tests/test_example.py"
    text, meta = render_trace_capsule_text(
        _turn([_event(1, repeated, 0), _event(2, repeated, 1)]),
        title="terminal validation fail test",
    )

    assert "final_validation: needs_review" in text
    assert "checks: pass=1 fail=1 other=0 total=2" in text
    assert "terminal_checks: pass=0 fail=1 other=0 total=1" in text
    assert meta["terminal_validation_fail_count"] == 1


def test_trace_capsule_separates_owner_pass_from_ambient_warnings() -> None:
    task_ledger_warning = (
        '{"validation_status":"valid_with_warnings",'
        '"error_count": 0,'
        '"warning_count": 36,'
        '"warning_classes":["historical_evidence_durability_backlog"]}'
    )
    text, meta = render_trace_capsule_text(
        _turn(
            [
                _event(1, "./repo-pytest system/server/tests/test_root_readme_entry_orientation.py", 0, "3 passed"),
                _event(2, "./repo-python tools/meta/factory/task_ledger_apply.py validate", 1, task_ledger_warning),
            ]
        ),
        title="ambient warning validation test",
    )

    assert "final_validation: pass_with_external_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "ambient_validation: valid_with_warnings" in text
    assert "ambient_warning_class: historical_evidence_durability_backlog" in text
    assert "release_authority: none" in text
    assert meta["final_validation"] == "pass_with_external_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["ambient_warning_classes"] == ["historical_evidence_durability_backlog"]
    assert meta["external_terminal_warning_count"] == 1
    assert meta["blocking_terminal_failure_count"] == 0


def test_trace_capsule_buckets_residual_mentions_by_state(monkeypatch) -> None:
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        "microcosm_dogfood_paper_module_sidecar_claim": {
            "id": "microcosm_dogfood_paper_module_sidecar_claim",
            "state": "captured",
            "title": "Paper-module sidecar claim blocks clean Microcosm dogfood doctrine landing",
            "tags": ["microcosm", "paper_module_index"],
        },
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561": {
            "id": "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561",
            "state": "done",
            "title": "Trace capsule closeout report command leakage test failure",
            "tags": ["trace_capsule", "validation"],
        },
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274": {
            "id": "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274",
            "state": "captured",
            "title": "Focused combined pytest wrapper hung after printing pass",
            "tags": ["validation_process", "pytest_wrapper", "trace_capsule"],
        },
    })
    receipt_text = "\n".join([
        "state/task_ledger/views/cap_cartography.json",
        "microcosm_dogfood_paper_module_sidecar_claim",
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561",
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274",
    ])

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_root_readme_entry_orientation.py", 0, "3 passed"),
            _event(2, "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --subject-id residuals", 0, receipt_text),
        ]),
        title="residual taxonomy test",
    )

    assert "open_product_residuals: microcosm_dogfood_paper_module_sidecar_claim" in text
    assert "open_validation_process_residuals: cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274" in text
    assert "closed_residuals_seen: cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561" in text
    assert "projection_or_view_artifacts_seen: cap_cartography.json" in text
    assert meta["open_product_residuals"] == ["microcosm_dogfood_paper_module_sidecar_claim"]
    assert meta["open_validation_process_residuals"] == [
        "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274"
    ]
    assert meta["closed_residuals_seen"] == [
        "cap_quick_trace_capsule_closeout_report_command_le_b1a9e4e5a561"
    ]
    assert meta["projection_or_view_artifacts_seen"] == ["cap_cartography.json"]


def test_trace_capsule_validation_process_warning_does_not_block_owner_scope(monkeypatch) -> None:
    process_cap = "cap_quick_focused_combined_pytest_wrapper_hung_aft_287a9def8274"
    monkeypatch.setattr(trace, "_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE", {
        process_cap: {
            "id": process_cap,
            "state": "captured",
            "title": "Focused combined pytest wrapper hung after printing pass",
            "tags": ["validation_process", "pytest_wrapper", "trace_capsule"],
        },
    })
    wrapper_output = f"15 passed in 0.66s\nwrapper hung after printing pass\n{process_cap}"

    text, meta = render_trace_capsule_text(
        _turn([
            _event(1, "./repo-pytest system/server/tests/test_cli_prompt_trace_capsule.py", 0, "6 passed"),
            _event(2, "./repo-pytest system/server/tests/test_cli_prompt_trace_capsule.py tests/test_microcosm_cold_entry_dogfood.py", 1, wrapper_output),
        ]),
        title="validation process warning test",
    )

    assert "final_validation: pass_with_validation_process_warnings" in text
    assert "owner_scope_validation: pass" in text
    assert "validation_process=needs_review" in text
    assert meta["final_validation"] == "pass_with_validation_process_warnings"
    assert meta["owner_scope_validation"] == "pass"
    assert meta["blocking_terminal_failure_count"] == 0
    assert meta["validation_process_terminal_warning_count"] == 1
    assert meta["open_validation_process_residuals"] == [process_cap]


def test_thread_closeout_report_omits_tools_and_interns_repeated_prompts() -> None:
    prompt = "same autonomous seed prompt"
    merged = merge_full_thread([
        _turn([_event(1, "./repo-pytest tests/test_one.py", 0)], turn_index=1, prompt_text=prompt, assistant_text="Wave one landed."),
        _turn([_event(1, "./repo-pytest tests/test_two.py", 0)], turn_index=2, prompt_text=prompt, assistant_text="Wave two landed."),
    ])

    text = render_thread_closeout_report(
        merged,
        title="Two autonomous seeds",
        intern_repeated_prompts=True,
    )

    assert "# Two autonomous seeds — Closeout Report" in text
    assert "`prompt_001`" in text
    assert "Wave one landed." in text
    assert "Wave two landed." in text
    assert "Exact closeout message" in text
    assert "./repo-pytest tests/test_one.py" not in text
