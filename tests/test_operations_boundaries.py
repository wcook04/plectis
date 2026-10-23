"""Independent recovery and composition boundaries; no whole-system proof claim."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from plectis.publish import PublishStore, StaleTicket
from plectis.repair import EffectJournal, RepairSession, Task
from plectis.repair import _host


def external_task(name="send", **changes):
    values = dict(code_id="boundary/" + name, version="1", contract="json-v1",
                  environment="test-sink", freshness="frozen-v1", replayable=False)
    values.update(changes)
    return Task(name, **values)


def test_checkpoint_default_preserves_unknown_after_restart_and_pruning(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    first = RepairSession([external_task()], checkpoint=checkpoint)
    attempt = first.begin_effect("send")
    first.mark_unknown(attempt, "receiver committed; response was lost")
    restarted = RepairSession([], checkpoint=checkpoint)
    result = restarted.run(restarted.plan())
    assert not result.settled
    assert result.unresolved_effects == ({"attempt": attempt, "task": "send", "status": "unknown"},)
    restored = RepairSession([external_task()], checkpoint=checkpoint)
    with pytest.raises(ValueError, match="unsettled"):
        restored.begin_effect("send")


def test_persistent_checkpoint_rejects_explicit_memory_only_journal(tmp_path):
    with pytest.raises(ValueError, match="persistent.*journal"):
        RepairSession([external_task()], checkpoint=tmp_path / "checkpoint.json",
                      journal=EffectJournal())


def test_custom_persistent_journal_and_memory_only_sessions_remain_supported(tmp_path):
    checkpoint, custom = tmp_path / "checkpoint.json", tmp_path / "custom.events"
    original = RepairSession([external_task()], checkpoint=checkpoint, journal=custom)
    attempt = original.begin_effect("send")
    original.mark_unknown(attempt, "outcome unresolved")
    reopened = RepairSession([], checkpoint=checkpoint, journal=EffectJournal(custom))
    assert reopened.run(reopened.plan()).unresolved_effects[0]["attempt"] == attempt
    assert custom.is_file()
    assert not Path(str(checkpoint) + ".effects.jsonl").exists()
    memory = RepairSession([external_task()])
    assert memory.journal.path is None
    memory.begin_effect("send")
    with pytest.raises(ValueError, match="unsettled"):
        memory.begin_effect("send")


def test_unresolved_payload_history_is_not_present_publication_authority(tmp_path):
    database = tmp_path / "results.sqlite"
    pending = json.dumps({"external_status": "unknown", "reserved_units": 2}).encode()
    with PublishStore(database) as first:
        first.create("ledger", "input-v1", "budget-v1")
        original = first.grant("ledger", "worker-A")
        first.publish(original, "original-operation", pending)
    with PublishStore(database) as upgraded:
        upgraded.change_identity("ledger", "input-v2", "budget-v2")
        upgraded.grant("ledger", "worker-B")
        assert upgraded.read_current("ledger") is None
        historical = upgraded.publish(original, "original-operation", pending)
        assert historical.status == "replayed"
        assert json.loads(historical.result.payload)["reserved_units"] == 2
        assert upgraded.read_current("ledger") is None
        with pytest.raises(StaleTicket):
            upgraded.publish(original, "new-operation", pending)


def test_operation_identity_is_scoped_to_one_store(tmp_path):
    # Distinct authorities can both commit the same named business operation.
    # A theorem about this local store must not be advertised as global dedup.
    committed = []
    for filename in ("left.sqlite", "right.sqlite"):
        with PublishStore(tmp_path / filename) as store:
            store.create("business-intent", "input", "contract")
            ticket = store.grant("business-intent", "worker")
            committed.append(store.publish(ticket, "same-business-operation", b"result"))
    assert [item.status for item in committed] == ["published", "published"]


def test_local_refusal_cannot_rollback_or_disprove_an_external_commit(tmp_path):
    # The separate receiver is a real second SQLite transaction domain, not a
    # callback mock. Its first acknowledgement is deliberately discarded.
    remote_path = tmp_path / "receiver.sqlite"
    with sqlite3.connect(remote_path) as receiver:
        receiver.execute("CREATE TABLE effects(operation TEXT PRIMARY KEY, units INTEGER)")
        receiver.execute("INSERT INTO effects VALUES('old-request',2)")
    with PublishStore(tmp_path / "results.sqlite") as local:
        local.create("result", "input-v1", "contract-v1")
        old = local.grant("result", "worker-A")
        local.change_identity("result", "input-v2", "contract-v2")
        replacement = local.grant("result", "worker-B")
        with pytest.raises(StaleTicket):
            local.publish(old, "old-request", b"response lost")
        assert local.read_current("result") is None
        with sqlite3.connect(remote_path) as receiver:
            assert receiver.execute("SELECT SUM(units) FROM effects").fetchone()[0] == 2
            # A naive fresh retry spends again despite the absent local row.
            receiver.execute("INSERT INTO effects VALUES('fresh-request',2)")
        local.publish(replacement, "fresh-request", b"new result")
        with sqlite3.connect(remote_path) as receiver:
            assert receiver.execute("SELECT SUM(units) FROM effects").fetchone()[0] == 4
        assert local.read_current("result").operation_id == "fresh-request"


def test_old_external_resolution_does_not_validate_changed_dependency(tmp_path):
    def graph(value):
        return [Task("input", code_id="boundary/input", version="1", inputs=value,
                     contract="json-v1", environment="local", freshness="frozen",
                     replayable=True, fn=lambda inputs, deps: inputs),
                external_task(deps=("input",))]
    checkpoint, journal = tmp_path / "checkpoint.json", tmp_path / "journal.jsonl"
    old = RepairSession(graph(1), checkpoint=checkpoint, journal=journal)
    old.run(old.plan())
    attempt = old.begin_effect("send")
    old.mark_unknown(attempt, "response lost")
    changed = RepairSession(graph(2), checkpoint=checkpoint, journal=journal)
    changed.resolve_effect(attempt, {"response_for_input": 1})
    result = changed.run(changed.plan())
    assert result.outputs == {"input": 2}
    assert result.blocked == ("send",)
    assert not result.settled
    assert not result.unresolved_effects  # Historical outcome is now known.
    assert changed.plan().classification()["send"] == "blocked"


def test_confirmed_effect_cannot_retry_after_checkpoint_write_failure(tmp_path, monkeypatch):
    checkpoint = tmp_path / "checkpoint.json"
    original = RepairSession([external_task(inputs={"request": 1})], checkpoint=checkpoint)
    attempt = original.begin_effect("send")

    def fail_save():
        raise OSError("injected checkpoint write failure")

    monkeypatch.setattr(original, "_save", fail_save)
    with pytest.raises(OSError, match="injected checkpoint"):
        original.resolve_effect(attempt, {"committed": True})
    assert not checkpoint.exists()

    restarted = RepairSession([external_task(inputs={"request": 1})], checkpoint=checkpoint)
    assert restarted.journal.events[-1]["kind"] == "confirmed"
    assert not restarted.journal.unresolved()
    assert restarted.records == {}
    result = restarted.run(restarted.plan())
    assert result.blocked == ("send",)
    assert not result.settled
    with pytest.raises(ValueError, match="already confirmed"):
        restarted.begin_effect("send")
    assert len(restarted.journal.events) == 2


def test_confirmed_effect_cannot_retry_after_process_exit_before_checkpoint(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    code = """
import os
import sys
sys.path.insert(0, sys.argv[1])
from plectis.repair import RepairSession, Task
task = Task("send", code_id="boundary/send", version="1", inputs={"request": 1},
            contract="json-v1", environment="test-sink", freshness="frozen-v1")
session = RepairSession([task], checkpoint=sys.argv[2])
attempt = session.begin_effect("send")
session._save = lambda: os._exit(73)
session.resolve_effect(attempt, {"committed": True})
"""
    source_root = Path(_host.__file__).resolve().parents[2]
    child = subprocess.run([sys.executable, "-I", "-B", "-c", code,
                            str(source_root), str(checkpoint)], cwd=tmp_path,
                           capture_output=True, text=True, check=False, timeout=30)
    assert child.returncode == 73, child.stderr
    assert not checkpoint.exists()
    restarted = RepairSession([external_task(inputs={"request": 1})], checkpoint=checkpoint)
    assert restarted.journal.events[-1]["kind"] == "confirmed"
    assert not restarted.journal.unresolved()
    with pytest.raises(ValueError, match="already confirmed"):
        restarted.begin_effect("send")
    assert len(restarted.journal.events) == 2


@pytest.mark.parametrize("changed_identity", ["descriptor", "dependency"])
def test_changed_effect_identity_after_confirmed_checkpoint_gap(tmp_path, monkeypatch,
                                                               changed_identity):
    def graph(dependency, request):
        return [Task("input", code_id="boundary/input", version="1", inputs=dependency,
                     contract="json-v1", environment="local", freshness="frozen",
                     replayable=True, fn=lambda inputs, deps: inputs),
                external_task(deps=("input",), inputs={"request": request})]

    checkpoint = tmp_path / "checkpoint.json"
    original = RepairSession(graph(1, 1), checkpoint=checkpoint)
    original.run(original.plan())
    attempt = original.begin_effect("send")

    def fail_save():
        raise OSError("injected checkpoint write failure")

    monkeypatch.setattr(original, "_save", fail_save)
    with pytest.raises(OSError, match="injected checkpoint"):
        original.resolve_effect(attempt, {"response_for": [1, 1]})

    changed = RepairSession(graph(2 if changed_identity == "dependency" else 1,
                                  2 if changed_identity == "descriptor" else 1),
                            checkpoint=checkpoint)
    assert "send" not in changed.records
    result = changed.run(changed.plan())
    assert result.blocked == ("send",)
    assert not result.unresolved_effects
    new_attempt = changed.begin_effect("send")
    assert new_attempt != attempt
    changed.resolve_effect(new_attempt, {"changed_identity": changed_identity})
    assert changed.run(changed.plan()).settled
