"""Behavioral checks across Repair, durable Publish and an ordinary caller.

These real local executions test the Python adapters and their composition;
they do not extend the Dafny planner/checker's formal theorem boundary.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event

import pytest

from plectis.publish import IdempotencyConflict, PublishStore, StaleTicket
from plectis.repair import InvalidPlan, RepairSession, StalePlan, Task


EXAMPLE = Path(__file__).resolve().parents[1] / "examples/operations/evaluation.py"
spec = importlib.util.spec_from_file_location("operations_evaluation_example", EXAMPLE)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def session(directory, calls, metric="1", *, include_export=False):
    return RepairSession(evaluation.graph(calls, metric, include_export=include_export),
                         checkpoint=directory / "checkpoint.json",
                         journal=directory / "effects.jsonl")


def test_changed_metric_retains_observations_and_matches_ordinary_cache(tmp_path):
    calls = Counter()
    first = session(tmp_path, calls)
    initial = first.run(first.plan())
    # Expected fixture means, independently calculated from the six observations
    # in each dataset: 34.5, 41.5, 48.5. Version 2 subtracts 0.2*90.5 from a.
    assert initial.outputs["report"] == {"mean": 41.5, "metric_version": "1"}
    assert len(initial.executed) == 11 and initial.settled

    unchanged = session(tmp_path, calls)
    same = unchanged.run(unchanged.plan())
    assert len(same.reused) == 11 and not same.executed and same.settled
    before = calls.copy()

    updated = session(tmp_path, calls, "2")
    plan = updated.plan()
    assert evaluation.ordinary_cache_oracle(plan) == plan.classification()
    result = updated.run(plan)
    assert set(result.executed) == {"score_a", "aggregate", "report"}
    assert len(result.reused) == 8 and result.settled
    assert result.outputs["report"]["mean"] == pytest.approx((16.4 + 41.5 + 48.5) / 3)
    for name in "abc":
        assert calls["observe_" + name] == before["observe_" + name] == 1
    assert result.outputs["observe_a"] == initial.outputs["observe_a"]


def test_restart_rejects_old_worker_and_recovers_exact_historical_request(tmp_path):
    calls = Counter()
    initial = session(tmp_path, calls)
    old_report = initial.run(initial.plan()).outputs["report"]
    old_payload = evaluation.encode(old_report)
    database = tmp_path / "publications.sqlite"
    with PublishStore(database) as coordinator:
        coordinator.create("evaluation", "frozen-input-v1", "metric-v1")
        first_ticket = coordinator.grant("evaluation", "original-worker")
        first = coordinator.publish(first_ticket, "first-operation", old_payload)
        pending_ticket = coordinator.grant("evaluation", "paused-worker")

    # Two real connections and events, without sleeps or mocked transactions.
    started, resume = Event(), Event()

    def late_worker():
        with PublishStore(database) as worker:
            started.set()
            if not resume.wait(timeout=15):
                raise TimeoutError("test did not resume worker")
            return worker.publish(pending_ticket, "obsolete-operation", old_payload)

    with ThreadPoolExecutor(max_workers=1) as executor:
        late = executor.submit(late_worker)
        try:
            assert started.wait(timeout=15)
            changed = session(tmp_path, calls, "2")
            new_report = changed.run(changed.plan()).outputs["report"]
            with PublishStore(database) as coordinator:
                coordinator.change_identity("evaluation", "frozen-input-v1", "metric-v2")
                assert coordinator.read_current("evaluation") is None
                current_ticket = coordinator.grant("evaluation", "current-worker")
                current = coordinator.publish(current_ticket, "current-operation",
                                              evaluation.encode(new_report))
        finally:
            resume.set()
        with pytest.raises(StaleTicket):
            late.result(timeout=15)

    with PublishStore(database) as restarted:
        replay = restarted.publish(first_ticket, "first-operation", old_payload)
        assert replay.status == "replayed" and replay.result == first.result
        assert replay.result != restarted.read_current("evaluation")
        assert restarted.read_current("evaluation") == current.result
        with pytest.raises(IdempotencyConflict):
            restarted.publish(first_ticket, "first-operation", evaluation.encode(new_report))
        # A new operation under the historical grant has no renewed authority.
        with pytest.raises(StaleTicket):
            restarted.publish(first_ticket, "fresh-operation", old_payload)
        assert restarted.read_current("evaluation").payload == evaluation.encode(new_report)


def test_unknown_action_survives_pruning_restart_and_relabeling(tmp_path):
    calls = Counter()
    initial = session(tmp_path, calls, include_export=True)
    first = initial.run(initial.plan())
    assert first.blocked == ("export",)
    attempt = initial.begin_effect("export")
    initial.mark_unknown(attempt, "caller died without an authoritative outcome")

    # Removing the graph node must not erase an obligation from its own journal.
    pruned = session(tmp_path, calls, "2", include_export=False)
    changed = pruned.run(pruned.plan())
    assert not changed.blocked and not changed.settled
    assert [item["task"] for item in changed.unresolved_effects] == ["export"]
    assert changed.outputs["report"]["metric_version"] == "2"

    # Calling the formerly external action "replayable" cannot bypass history.
    tasks = evaluation.graph(calls, "2", include_export=False)
    task_calls = []
    tasks.append(Task("export", code_id="different/export", version="2",
                      deps=("report",), inputs=None, contract="evaluation-json-v1",
                      environment="stdlib-fixture-v1", freshness="frozen-input-v1",
                      replayable=True, fn=lambda inputs, deps: task_calls.append("export")))
    tasks.append(Task("after_export", code_id="after/export", version="1",
                      deps=("export",), inputs=None, contract="evaluation-json-v1",
                      environment="stdlib-fixture-v1", freshness="frozen-input-v1",
                      replayable=True, fn=lambda inputs, deps: task_calls.append("consumer")))
    restored = RepairSession(tasks, checkpoint=tmp_path / "checkpoint.json",
                             journal=tmp_path / "effects.jsonl")
    result = restored.run(restored.plan())
    assert set(result.blocked) == {"export", "after_export"}
    assert not result.settled and not task_calls and calls["export"] == 0
    with pytest.raises(ValueError, match="unsettled"):
        restored.begin_effect("export")


def test_changed_binding_and_effect_barrier_cannot_use_an_old_or_weakened_plan(tmp_path):
    calls = Counter()
    first = session(tmp_path, calls, include_export=True)
    first.run(first.plan())
    plan_before_request = first.plan()
    attempt = first.begin_effect("export")
    first.mark_unknown(attempt, "unacknowledged local action")
    with pytest.raises(StalePlan):
        first.run(plan_before_request)

    restarted = session(tmp_path, calls, "2", include_export=True)
    plan = restarted.plan()
    weakened = replace(plan, blocked=tuple(False for _ in plan.blocked))
    with pytest.raises(InvalidPlan):
        restarted.run(weakened)
    assert calls["export"] == 0


def test_no_argument_example_and_optional_json_output(tmp_path):
    output = tmp_path / "observed.json"
    env = dict(os.environ, PYTHONPATH=str(EXAMPLE.parents[2] / "src"),
               PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", str(EXAMPLE)]
    for arguments in ([], ["--out", str(output)]):
        completed = subprocess.run(command + arguments, cwd=tmp_path, env=env,
                                   capture_output=True, text=True, timeout=45)
        assert completed.returncode == 0, completed.stderr
        observed = json.loads(completed.stdout)
        assert observed["repair"]["metric_change"] == {"reuse": 8, "rerun": 3, "blocked": 1}
        assert observed["repair"]["repair_observation_calls"] == 0
        assert observed["publication"]["old_worker"] == "rejected_stale"
        assert observed["publication"]["historical_retry"] == "replayed"
        assert observed["publication"]["historical_retry_is_current"] is False
        assert observed["publication"]["current_result"]["metric_version"] == "2"
        assert observed["external_action"]["unsettled_after_graph_removal"] == ["export"]
        assert observed["external_action"]["restored_blocked_tasks"] == ["export"]
        assert observed["external_action"]["automatic_export_callbacks"] == 0
        assert observed["external_action"]["settled"] is False
        assert observed["comparison"]["equally_informed_cache_ties"] is True
        assert observed["comparison"]["speed_advantage_claimed"] is False
    assert json.loads(output.read_text()) == observed
    # The default command retained no checkpoint/database/journal beside its
    # invocation; only the explicitly requested summary remains.
    assert [path.name for path in tmp_path.iterdir()] == ["observed.json"]


def test_text_summary_uses_observed_values_instead_of_fixed_success_messages(tmp_path):
    observed = evaluation.run_demo(tmp_path)
    observed["repair"]["metric_change"] = {"reuse": 4, "rerun": 5, "blocked": 2}
    observed["repair"]["rerun_tasks"] = ["rescore_b", "report_b"]
    observed["repair"]["repair_observation_calls"] = 2
    observed["publication"]["old_worker"] = "published"
    observed["publication"]["current_result"]["metric_version"] = "3"
    observed["publication"]["historical_retry"] = "changed_outcome"
    observed["publication"]["historical_retry_is_current"] = True
    observed["external_action"]["unsettled_after_graph_removal"] = ["notify"]
    observed["external_action"]["retry_blocked"] = False
    observed["comparison"]["equally_informed_cache_ties"] = False
    observed["comparison"]["ordinary_cache_decisions"] = {"reuse": 7, "rerun": 4}
    observed["assurance"] = {"proved": "supplied kernel claim",
                             "tested": "supplied adapter claim",
                             "boundary": "supplied boundary"}

    summary = evaluation.render_text(observed)
    assert len(summary.splitlines()) == 10
    assert "4 reused, 5 rerun, 2 blocked" in summary
    assert "Rerun tasks: rescore_b, report_b" in summary
    assert "New observation calls: 2" in summary
    assert "Delayed worker: published; current metric: 3" in summary
    assert "Historical retry: changed_outcome; historical result is current: yes" in summary
    assert "Unresolved after graph removal: notify; retry blocked: no" in summary
    assert "Equally informed cache ties: no (7 reuse, 4 rerun, 0 blocked)" in summary
    for field in observed["assurance"].values():
        assert field in summary


def test_text_cli_keeps_json_file_output(tmp_path):
    output = tmp_path / "observed.json"
    env = dict(os.environ, PYTHONPATH=str(EXAMPLE.parents[2] / "src"),
               PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run([sys.executable, "-B", str(EXAMPLE),
                                "--format", "text", "--out", str(output)],
                               cwd=tmp_path, env=env, capture_output=True,
                               text=True, timeout=45)
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(output.read_text())
    assert completed.stdout == evaluation.render_text(observed)
    assert len(completed.stdout.splitlines()) == 10
    assert observed["repair"]["metric_change"] == {"reuse": 8, "rerun": 3, "blocked": 1}
    assert observed["publication"]["old_worker"] == "rejected_stale"
    assert [path.name for path in tmp_path.iterdir()] == ["observed.json"]
