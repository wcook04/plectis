"""
[PURPOSE]
- Teleology: Pin Evolve runner input-readiness behavior around Oracle artifact aliases and feed-health gating.
- Mechanism: Seed compact artifact envelopes under tmp_path and exercise the runner's loading, manifest, and prompt helpers directly.
- Non-goal: Bridge dispatch, dossier patch synthesis, or live version_committer mutation.

[INTERFACE]
- Tests: tools.refinement.run_evolve canonical/legacy artifact loading, feed-health blocking, and delta prompt context injection.

[FLOW]
- Write minimal Oracle quartet artifacts to tmp_path run directories.
- Assert canonical artifact ids are used even when legacy aliases exist.
- Assert BLOCKED feed readiness stops Evolve before bridge dispatch or ledger append.
- Assert the delta prompt exposes the readiness manifest before artifact payloads.
- Assert completed learning-ledger entries retain input-readiness metadata.

[DEPENDENCIES]
- tools.refinement.run_evolve owns the Evolve CLI/runtime helper behavior.

[CONSTRAINTS]
- Tests are isolated to tmp_path and monkeypatch bridge/ledger hooks when using run_evolve().
- When-needed: Open when Evolve input handling changes, especially artifact names, feed-health interpretation, or prompt construction.
- Escalates-to: tools/refinement/run_evolve.py
- Navigation-group: server_backend
"""

from __future__ import annotations

import json
from pathlib import Path

from system.lib.launchable_operations import (
    operation_event_fields_from_operation_output,
    prepare_launch_operation,
)
import tools.oracle.run_quartet as oracle_quartet
import tools.refinement.run_evolve as evolve


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _artifact(data: dict, *, artifact_id: str = "artifact") -> dict:
    return {
        "id": artifact_id,
        "status": "success",
        "metadata": {"status": "success"},
        "data": data,
    }


def _feed_health(status: str, diagnostics: list[str] | None = None) -> dict:
    return {
        "status": status,
        "subject": {"stock_ticker_count": 1, "etf_ticker_count": 0, "stock_price_count": 1, "etf_price_count": 0, "ticker_count": 1},
        "truth": {"stock_ticker_count": 1, "etf_ticker_count": 0, "stock_price_count": 1, "etf_price_count": 0, "ticker_count": 1},
        "common_ticker_count": 1,
        "prediction_target_count": 1,
        "comparable_prediction_targets": ["XOM"] if status != "BLOCKED" else [],
        "missing_subject_price_targets": [],
        "missing_truth_price_targets": [] if status != "BLOCKED" else ["XOM"],
        "diagnostics": diagnostics or [],
    }


def _write_oracle_quartet(truth_run: Path, *, feed_status: str = "READY") -> None:
    _write_json(
        truth_run / "artifacts" / "prediction_reconciliation.json",
        _artifact(
            {
                "status": "AVAILABLE",
                "summary": {"row_count": 1},
                "feed_health": _feed_health(
                    feed_status,
                    ["missing truth prices for targets: XOM"] if feed_status == "BLOCKED" else [],
                ),
            },
            artifact_id="prediction_reconciliation",
        ),
    )
    _write_json(
        truth_run / "artifacts" / "realized_hindsight_brief.json",
        _artifact({"status": "AVAILABLE", "driver_classification": []}, artifact_id="realized_hindsight_brief"),
    )
    _write_json(
        truth_run / "artifacts" / "cp2_critique.json",
        _artifact({"status": "AVAILABLE", "critique_items": []}, artifact_id="cp2_critique"),
    )
    _write_json(
        truth_run / "artifacts" / "ideal_cp2.json",
        _artifact({"predictions_t": []}, artifact_id="ideal_cp2"),
    )


def _write_feed_readiness(run_dir: Path, *, ready: bool, blockers: list[dict] | None = None) -> None:
    blockers = blockers or []
    _write_json(
        run_dir / "artifacts" / "feed_readiness_summary.json",
        {
            "schema_version": "feed_readiness_summary.v1",
            "run_id": run_dir.name,
            "ready": ready,
            "target_count": 7,
            "status_counts": {"success": 6, "failure": 1} if not ready else {"success": 7},
            "blockers": blockers,
        },
    )


def test_evolve_loads_canonical_oracle_artifacts_before_legacy_aliases(tmp_path: Path) -> None:
    truth_run = tmp_path / "truth"
    _write_oracle_quartet(truth_run, feed_status="READY")
    _write_json(
        truth_run / "artifacts" / "oracle_truth_diff_equity.json",
        _artifact(
            {
                "status": "AVAILABLE",
                "marker": "legacy fallback should not win",
                "feed_health": _feed_health("BLOCKED"),
            },
            artifact_id="oracle_truth_diff_equity",
        ),
    )

    artifacts, manifest, readiness = evolve._load_oracle_artifacts(truth_run)

    assert readiness["status"] == "READY"
    assert manifest["missing_artifacts"] == []
    assert manifest["artifacts"][0]["artifact_id"] == "prediction_reconciliation"
    assert manifest["artifacts"][0]["source_artifact_id"] == "prediction_reconciliation"
    assert evolve._artifact_data(artifacts["prediction_reconciliation"])["feed_health"]["status"] == "READY"


def test_evolve_marks_legacy_oracle_alias_inputs_as_degraded(tmp_path: Path) -> None:
    truth_run = tmp_path / "truth"
    _write_oracle_quartet(truth_run, feed_status="READY")
    (truth_run / "artifacts" / "prediction_reconciliation.json").unlink()
    _write_json(
        truth_run / "artifacts" / "oracle_truth_diff_equity.json",
        _artifact(
            {
                "status": "AVAILABLE",
                "feed_health": _feed_health("READY"),
            },
            artifact_id="oracle_truth_diff_equity",
        ),
    )

    _, manifest, readiness = evolve._load_oracle_artifacts(truth_run)

    assert readiness["status"] == "DEGRADED"
    assert manifest["artifacts"][0]["source_artifact_id"] == "oracle_truth_diff_equity"
    assert (
        "prediction_reconciliation loaded from legacy alias oracle_truth_diff_equity; prefer canonical artifact output"
        in readiness["warnings"]
    )


def test_evolve_blocks_when_prediction_reconciliation_feed_health_is_blocked(
    tmp_path: Path,
    monkeypatch,
) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    _write_json(subject_run / "artifacts" / "lab_director.json", _artifact({"predictions_t": []}, artifact_id="lab_director"))
    _write_oracle_quartet(truth_run, feed_status="BLOCKED")

    def _fail_dispatch(*_args, **_kwargs):
        raise AssertionError("bridge dispatch should not run when feed health is blocked")

    def _fail_ledger(*_args, **_kwargs):
        raise AssertionError("learning ledger should not append when feed health is blocked")

    monkeypatch.setattr(evolve, "_dispatch_to_bridge", _fail_dispatch)
    monkeypatch.setattr(evolve, "_append_learning_ledger", _fail_ledger)

    result = evolve.run_evolve(subject_run, truth_run, use_bridge=True)

    assert result["error"] == "evolve_inputs_not_ready"
    assert result["oracle_input_readiness"]["status"] == "BLOCKED"
    assert any("feed_health is BLOCKED" in reason for reason in result["oracle_input_readiness"]["blocking_reasons"])


def test_delta_prompt_includes_oracle_input_readiness_manifest(tmp_path: Path) -> None:
    truth_run = tmp_path / "truth"
    _write_oracle_quartet(truth_run, feed_status="DEGRADED")
    artifacts, manifest, readiness = evolve._load_oracle_artifacts(truth_run)

    prompt = evolve._build_delta_prompt(
        artifacts,
        lab_cp2={"data": {"predictions_t": []}},
        subject_run_id="subject",
        truth_run_id="truth",
        oracle_input_manifest=manifest,
        oracle_input_readiness=readiness,
    )

    assert "=== ORACLE INPUT READINESS ===" in prompt
    assert "=== ORACLE INPUT MANIFEST ===" in prompt
    assert "--- prediction_reconciliation ---" in prompt
    assert '"feed_health"' in prompt
    assert '"status": "DEGRADED"' in prompt


def test_learning_ledger_records_oracle_input_readiness(tmp_path: Path, monkeypatch) -> None:
    ledger_path = tmp_path / "learning_ledger.jsonl"
    monkeypatch.setattr(evolve, "LEARNING_LEDGER", ledger_path)

    evolve._append_learning_ledger(
        {
            "run_pair": {"subject_run_id": "subject", "truth_run_id": "truth"},
            "pattern_summary": {
                "root_failure_mode": "UNKNOWN",
                "error_class_distribution": {},
            },
            "doctrine_flags": [],
            "learning_entries": ["No bridge analysis performed."],
        },
        {"total_applied": 0, "total_skipped": 0},
        {"status": "DEGRADED", "warnings": ["truth ETF target missing"]},
    )

    entry = json.loads(ledger_path.read_text(encoding="utf-8").strip())
    assert entry["oracle_input_readiness"]["status"] == "DEGRADED"
    assert entry["oracle_input_readiness"]["warnings"] == ["truth ETF target missing"]


def test_successful_evolve_run_persists_pair_local_artifacts(tmp_path: Path, monkeypatch) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    _write_json(
        subject_run / "artifacts" / "lab_director.json",
        _artifact({"predictions_t": [{"target_id": "XLK"}]}, artifact_id="lab_director"),
    )
    _write_oracle_quartet(truth_run, feed_status="READY")
    refinement_dir = tmp_path / "tools" / "refinement"
    refinement_dir.mkdir(parents=True)
    delta_node = tmp_path / "delta_analyzer.json"
    _write_json(delta_node, {"instruction": "Analyze paired Oracle outputs."})
    ledger_path = tmp_path / "learning_ledger.jsonl"
    monkeypatch.setattr(evolve, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(evolve, "DELTA_NODE", delta_node)
    monkeypatch.setattr(evolve, "LEARNING_LEDGER", ledger_path)

    result = evolve.run_evolve(subject_run, truth_run, use_bridge=False, dry_run=True)

    assert result["status"] == "completed"
    artifact_paths = result["run_artifact_paths"]
    assert set(artifact_paths) == {
        "evolve_input_readiness",
        "evolve_delta_report",
        "evolve_patch_payload",
    }

    delta_artifact = json.loads(Path(artifact_paths["evolve_delta_report"]).read_text(encoding="utf-8"))
    assert delta_artifact["id"] == "evolve_delta_report"
    assert delta_artifact["metadata"]["subject_run_id"] == "subject"
    assert delta_artifact["metadata"]["truth_run_id"] == "truth"
    assert delta_artifact["metadata"]["bridge"] is False
    assert delta_artifact["data"]["status"] == "AVAILABLE"
    assert delta_artifact["data"]["run_pair"] == {
        "subject_run_id": "subject",
        "truth_run_id": "truth",
    }

    patch_artifact = json.loads(Path(artifact_paths["evolve_patch_payload"]).read_text(encoding="utf-8"))
    assert patch_artifact["id"] == "evolve_patch_payload"
    assert patch_artifact["data"]["summary"] == "No deltas"
    assert patch_artifact["metadata"]["apply_mode"] == "dry-run"
    assert patch_artifact["metadata"]["apply_results"] == {
        "total_applied": 0,
        "total_skipped": 0,
        "lane_statuses": {},
    }

    readiness_artifact = json.loads(Path(artifact_paths["evolve_input_readiness"]).read_text(encoding="utf-8"))
    assert readiness_artifact["id"] == "evolve_input_readiness"
    assert readiness_artifact["data"]["readiness"]["status"] == "READY"
    assert readiness_artifact["data"]["manifest"]["subject_run_id"] == "subject"
    assert ledger_path.exists()


def test_input_readiness_payload_blocks_missing_lab_cp2(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    subject_run.mkdir()
    _write_oracle_quartet(truth_run, feed_status="READY")

    payload = evolve.build_input_readiness_payload(subject_run, truth_run)

    assert payload["kind"] == "evolve_input_readiness"
    assert payload["readiness"]["status"] == "BLOCKED"
    assert payload["manifest"]["lab_cp2"]["status"] == "missing"
    assert "missing required Lab CP2 artifact: lab_director" in payload["readiness"]["blocking_reasons"]


def test_input_readiness_blocks_explicit_feed_readiness_blockers(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    _write_json(
        subject_run / "artifacts" / "lab_director.json",
        _artifact({"predictions_t": []}, artifact_id="lab_director"),
    )
    _write_oracle_quartet(truth_run, feed_status="READY")
    _write_feed_readiness(
        subject_run,
        ready=False,
        blockers=[
            {
                "node_id": "global_macro_feed",
                "status": "failure",
                "reason": "Missing macro API key",
                "dependencies": [],
            }
        ],
    )
    _write_feed_readiness(truth_run, ready=True)

    payload = evolve.build_input_readiness_payload(subject_run, truth_run)
    fields = operation_event_fields_from_operation_output(json.dumps(payload))

    assert payload["readiness"]["status"] == "BLOCKED"
    assert (
        "subject feed_readiness_summary has blockers: global_macro_feed=failure (Missing macro API key)"
        in payload["readiness"]["blocking_reasons"]
    )
    assert fields["evolve_input_readiness"]["subject_feed_readiness_status"] == "BLOCKED"
    assert fields["evolve_input_readiness"]["subject_feed_blocker_count"] == 1
    assert fields["evolve_input_readiness"]["truth_feed_readiness_status"] == "READY"


def test_input_readiness_stdout_publishes_compact_launcher_field(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    subject_run.mkdir()
    _write_oracle_quartet(truth_run, feed_status="READY")

    payload = evolve.build_input_readiness_payload(subject_run, truth_run)
    fields = operation_event_fields_from_operation_output(
        "checking evolve inputs\n" + json.dumps(payload)
    )

    assert fields["evolve_input_readiness"] == {
        "schema_version": "evolve_input_readiness_summary_v1",
        "status": "BLOCKED",
        "subject_run_id": "subject",
        "truth_run_id": "truth",
        "feed_health_status": "READY",
        "lab_cp2_status": "missing",
        "subject_feed_readiness_status": "MISSING",
        "subject_feed_blocker_count": 0,
        "truth_feed_readiness_status": "MISSING",
        "truth_feed_blocker_count": 0,
        "oracle_repair_status": "READY",
        "missing_artifacts": [],
        "blocking_reasons": ["missing required Lab CP2 artifact: lab_director"],
        "warnings": [],
        "oracle_repair_actions": [],
    }


def test_oracle_quartet_repair_plan_materializes_existing_legacy_alias(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    subject_run.mkdir()
    _write_json(
        truth_run / "artifacts" / "oracle_truth_diff_equity.json",
        _artifact(
            {
                "status": "AVAILABLE",
                "feed_health": _feed_health("READY"),
            },
            artifact_id="oracle_truth_diff_equity",
        ),
    )

    plan = oracle_quartet.build_quartet_repair_plan(subject_run, truth_run)

    assert plan["readiness"]["status"] == "BLOCKED"
    assert "prediction_reconciliation" in plan["readiness"]["aliasable_artifacts"]
    assert plan["readiness"]["deepest_missing_target"] == "oracle_cp2_emitter"
    assert any(
        action["action_kind"] == "materialize_alias"
        and action["canonical_artifact_id"] == "prediction_reconciliation"
        for action in plan["repair_actions"]
    )

    receipt = oracle_quartet.materialize_missing_aliases(subject_run, truth_run)

    alias_path = truth_run / "artifacts" / "prediction_reconciliation.json"
    alias_payload = json.loads(alias_path.read_text(encoding="utf-8"))
    assert receipt["written_paths"] == [str(alias_path)]
    assert alias_payload["id"] == "prediction_reconciliation"
    assert alias_payload["metadata"]["artifact_alias_of"] == "oracle_truth_diff_equity"


def test_oracle_quartet_plan_stdout_publishes_compact_launcher_field(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    subject_run.mkdir()
    _write_json(
        truth_run / "artifacts" / "oracle_truth_diff_equity.json",
        _artifact(
            {
                "status": "AVAILABLE",
                "feed_health": _feed_health("READY"),
            },
            artifact_id="oracle_truth_diff_equity",
        ),
    )

    payload = oracle_quartet.build_quartet_repair_plan(subject_run, truth_run)
    fields = operation_event_fields_from_operation_output(
        "planning oracle quartet repair\n" + json.dumps(payload, indent=2)
    )
    summary = fields["oracle_quartet_repair"]

    assert summary["status"] == "BLOCKED"
    assert summary["subject_run_id"] == "subject"
    assert summary["truth_run_id"] == "truth"
    assert summary["result_kind"] == "oracle_quartet_repair_plan"
    assert summary["deepest_missing_target"] == "oracle_cp2_emitter"
    assert summary["missing_canonical_artifacts"] == [
        "prediction_reconciliation",
        "realized_hindsight_brief",
        "cp2_critique",
        "ideal_cp2",
    ]
    assert summary["aliasable_artifacts"] == ["prediction_reconciliation"]
    assert summary["missing_source_nodes"] == [
        "oracle_truth_map",
        "oracle_attribution_map",
        "oracle_cp2_emitter",
    ]
    assert summary["status_counts"]["alias_source_present"] == 1
    assert summary["status_counts"]["missing_source"] == 3
    assert any(
        action["action_kind"] == "materialize_alias"
        and action["canonical_artifact_id"] == "prediction_reconciliation"
        for action in summary["repair_actions"]
    )


def test_evolve_input_check_launchable_operation_renders_station_command() -> None:
    prepared = prepare_launch_operation(
        evolve.REPO_ROOT,
        operation_id="evolve_input_check",
        parameters={
            "subject_run": "state/runs/lab_subject",
            "truth_run": "state/runs/oracle_truth",
        },
    )

    assert prepared.execution_mode == "sync"
    assert prepared.operation["ui_group"] == "lab_oracle_evolve"
    assert prepared.operation["meta_mission_id"] == "lab_oracle_evolve_input_check"
    assert (
        prepared.command
        == './repo-python tools/refinement/run_evolve.py --subject-run "state/runs/lab_subject" --truth-run "state/runs/oracle_truth" --input-check'
    )


def test_evolve_bridge_dry_run_launchable_operation_renders_detached_command() -> None:
    prepared = prepare_launch_operation(
        evolve.REPO_ROOT,
        operation_id="evolve_bridge_dry_run",
        parameters={
            "subject_run": "state/runs/lab_subject",
            "truth_run": "state/runs/oracle_truth",
            "provider": "chatgpt",
        },
    )

    assert prepared.execution_mode == "detached"
    assert prepared.operation["ui_group"] == "lab_oracle_evolve"
    assert prepared.operation["meta_mission_id"] == "lab_oracle_evolve_bridge_dry_run"
    assert (
        prepared.command
        == './repo-python tools/refinement/run_evolve.py --subject-run "state/runs/lab_subject" --truth-run "state/runs/oracle_truth" --bridge --provider chatgpt --dry-run'
    )


def test_overnight_plan_launchable_operation_renders_budget_command() -> None:
    prepared = prepare_launch_operation(
        evolve.REPO_ROOT,
        operation_id="lab_oracle_evolve_overnight_plan",
        parameters={
            "budget_units": "2.5",
            "provider": "chatgpt",
            "max_runs": "4",
        },
    )

    assert prepared.execution_mode == "sync"
    assert prepared.operation["ui_group"] == "lab_oracle_evolve"
    assert prepared.operation["meta_mission_id"] == "lab_oracle_evolve_overnight_ledger"
    assert (
        prepared.command
        == "./repo-python tools/refinement/overnight_ledger.py --budget-units 2.5 --provider chatgpt --max-runs 4 --write-ledger"
    )


def test_overnight_plan_stdout_publishes_compact_launcher_field() -> None:
    payload = {
        "kind": "lab_oracle_evolve_overnight_plan",
        "plan_id": "loe_plan_test",
        "budget": {"provider": "chatgpt", "budget_units": 3},
        "summary": {
            "selected_count": 2,
            "eligible_count": 3,
            "skipped_count": 1,
            "estimated_spend_units": 2.1,
            "remaining_budget_units": 0.9,
        },
        "paths": {
            "plan_path": "state/lab_oracle_evolve/overnight_plan.json",
            "ledger_path": "state/lab_oracle_evolve/overnight_ledger.jsonl",
        },
        "selected_runs": [
            {
                "pair_id": "RUN_SUBJECT->RUN_PAIR",
                "subject_run_id": "RUN_SUBJECT",
                "truth_run_id": "RUN_PAIR",
                "readiness_status": "READY",
                "estimated_cost_units": 1.1,
                "command": "./repo-python tools/refinement/run_evolve.py --bridge --dry-run",
            }
        ],
    }

    fields = operation_event_fields_from_operation_output(json.dumps(payload))
    summary = fields["lab_oracle_evolve_overnight_plan"]

    assert summary["schema_version"] == "lab_oracle_evolve_overnight_plan_summary_v1"
    assert summary["plan_id"] == "loe_plan_test"
    assert summary["selected_count"] == 2
    assert summary["eligible_count"] == 3
    assert summary["estimated_spend_units"] == 2.1
    assert summary["ledger_path"] == "state/lab_oracle_evolve/overnight_ledger.jsonl"
    assert summary["selected_runs"][0]["pair_id"] == "RUN_SUBJECT->RUN_PAIR"


def test_oracle_quartet_launchable_operations_render_safe_commands() -> None:
    plan = prepare_launch_operation(
        evolve.REPO_ROOT,
        operation_id="oracle_quartet_plan",
        parameters={
            "subject_run": "state/runs/lab_subject",
            "truth_run": "state/runs/oracle_truth",
        },
    )
    run_missing = prepare_launch_operation(
        evolve.REPO_ROOT,
        operation_id="oracle_quartet_run_missing",
        parameters={
            "subject_run": "state/runs/lab_subject",
            "truth_run": "state/runs/oracle_truth",
            "target": "oracle_cp2_emitter",
        },
    )

    assert plan.execution_mode == "sync"
    assert plan.operation["ui_group"] == "lab_oracle_evolve"
    assert plan.operation["meta_mission_id"] == "oracle_quartet_repair"
    assert plan.operation["meta_mission_run_source"] == "launcher"
    assert (
        plan.command
        == './repo-python tools/oracle/run_quartet.py --subject-run "state/runs/lab_subject" --truth-run "state/runs/oracle_truth" --plan'
    )
    assert run_missing.execution_mode == "detached"
    assert run_missing.operation["ui_group"] == "lab_oracle_evolve"
    assert run_missing.operation["meta_mission_id"] == "oracle_quartet_repair"
    assert run_missing.operation["meta_mission_run_source"] == "runtime"
    assert (
        run_missing.command
        == './repo-python tools/oracle/run_quartet.py --subject-run "state/runs/lab_subject" --truth-run "state/runs/oracle_truth" --run-missing --target oracle_cp2_emitter'
    )
