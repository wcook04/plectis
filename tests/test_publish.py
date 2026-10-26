from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3
from threading import Barrier

import pytest

from plectis.publish import (
    IdempotencyConflict,
    MAX_GENERATION,
    MAX_IDENTIFIER_BYTES,
    MAX_PAYLOAD_BYTES,
    PublishStore,
    StaleTicket,
    Ticket,
)


def snapshot(database: Path) -> tuple:
    with sqlite3.connect(database) as connection:
        return tuple(
            tuple(connection.execute(f"SELECT * FROM {table} ORDER BY 1"))
            for table in ("plectis_publish_resources", "plectis_publications")
        )


@pytest.fixture
def store(tmp_path: Path):
    with PublishStore(tmp_path / "results.sqlite") as opened:
        opened.create("analysis", "input-v1", "contract-v1")
        yield opened


def test_publish_records_exact_bytes_and_consumes_ticket(store: PublishStore) -> None:
    ticket = store.grant("analysis", "worker")
    accepted = store.publish(ticket, "operation", b"checked result\x00\xff")
    assert accepted.status == "published"
    assert accepted.result.ticket == ticket
    assert accepted.result.payload == b"checked result\x00\xff"
    assert accepted.result.generation == ticket.generation
    assert accepted.result.key == "analysis"
    assert store.read_current("analysis") == accepted.result
    with pytest.raises(StaleTicket):
        store.publish(ticket, "another operation", b"other result")
    assert store.read_current("analysis") == accepted.result


def test_replay_is_historical_and_does_not_restore_currentness(store: PublishStore) -> None:
    old = store.grant("analysis", "worker-A")
    first = store.publish(old, "old-operation", b"old result")
    new = store.grant("analysis", "worker-B")
    assert store.read_current("analysis") is None
    replay = store.publish(old, "old-operation", b"old result")
    assert replay.status == "replayed"
    assert replay.result == first.result
    assert store.read_current("analysis") is None
    current = store.publish(new, "new-operation", b"new result")
    assert store.publish(old, "old-operation", b"old result").result == first.result
    assert store.read_current("analysis") == current.result


def test_lost_ack_replay_after_reopen_and_identity_change(tmp_path: Path) -> None:
    database = tmp_path / "results.sqlite"
    with PublishStore(database) as first:
        first.create("analysis", "input-v1", "contract-v1")
        ticket = first.grant("analysis", "worker-A")
        # The committed response is discarded, as if the caller lost it.
        first.publish(ticket, "operation", b"result")
    with PublishStore(database) as reopened:
        reopened.change_identity("analysis", "input-v2", "contract-v2")
        replacement = reopened.grant("analysis", "worker-B")
        before = snapshot(database)
        recovered = reopened.publish(ticket, "operation", b"result")
        assert recovered.status == "replayed"
        assert recovered.result.payload == b"result"
        assert recovered.result.ticket == ticket
        assert snapshot(database) == before
        assert reopened.read_current("analysis") is None
        current = reopened.publish(replacement, "replacement-operation", b"new result")
        assert reopened.read_current("analysis") == current.result


@pytest.mark.parametrize("changed", [
    {"key": "other resource"}, {"generation": 2}, {"owner": "other worker"},
    {"input_id": "other input"}, {"contract_id": "other contract"},
])
def test_replay_conflicts_on_every_ticket_field(
    store: PublishStore, tmp_path: Path, changed: dict,
) -> None:
    ticket = store.grant("analysis", "worker")
    store.publish(ticket, "operation", b"result")
    before = snapshot(tmp_path / "results.sqlite")
    with pytest.raises(IdempotencyConflict):
        store.publish(replace(ticket, **changed), "operation", b"result")
    assert snapshot(tmp_path / "results.sqlite") == before


def test_replay_conflicts_on_changed_full_payload(store: PublishStore, tmp_path: Path) -> None:
    ticket = store.grant("analysis", "worker")
    first = store.publish(ticket, "operation", b"result")
    before = snapshot(tmp_path / "results.sqlite")
    with pytest.raises(IdempotencyConflict):
        store.publish(ticket, "operation", b"result\x00")
    assert snapshot(tmp_path / "results.sqlite") == before
    assert store.read_current("analysis") == first.result


@pytest.mark.parametrize("changed", [
    {"key": "missing"}, {"generation": 2}, {"owner": "other worker"},
    {"input_id": "other input"}, {"contract_id": "other contract"},
])
def test_stale_new_request_does_not_consume_current_grant(
    store: PublishStore, tmp_path: Path, changed: dict,
) -> None:
    ticket = store.grant("analysis", "worker")
    before = snapshot(tmp_path / "results.sqlite")
    with pytest.raises(StaleTicket):
        store.publish(replace(ticket, **changed), "invalid request", b"wrong")
    assert snapshot(tmp_path / "results.sqlite") == before
    assert store.publish(ticket, "valid request", b"right").status == "published"


def test_identity_A_B_A_cannot_revive_old_ticket(store: PublishStore) -> None:
    old = store.grant("analysis", "worker")
    store.change_identity("analysis", "input-v2", "contract-v2")
    store.change_identity("analysis", "input-v1", "contract-v1")
    with pytest.raises(StaleTicket):
        store.publish(old, "obsolete", b"old")
    current = store.grant("analysis", "worker")
    assert current.generation == old.generation + 3
    assert store.publish(current, "current", b"new").status == "published"


def test_unchanged_identity_retains_current_ticket(store: PublishStore) -> None:
    ticket = store.grant("analysis", "worker")
    store.change_identity("analysis", "input-v1", "contract-v1")
    assert store.publish(ticket, "operation", b"result").status == "published"


def test_same_owner_reacquisition_still_supersedes_ticket(store: PublishStore) -> None:
    old = store.grant("analysis", "worker")
    new = store.grant("analysis", "worker")
    assert new.generation == old.generation + 1
    with pytest.raises(StaleTicket):
        store.publish(old, "old", b"old")
    assert store.publish(new, "new", b"new").status == "published"


def test_revoke_prevents_new_effect_but_keeps_history(store: PublishStore) -> None:
    revoked = store.grant("analysis", "worker")
    store.revoke("analysis")
    with pytest.raises(StaleTicket):
        store.publish(revoked, "revoked", b"result")
    current = store.grant("analysis", "worker")
    original = store.publish(current, "operation", b"result")
    store.revoke("analysis")
    assert store.publish(current, "operation", b"result").status == "replayed"
    assert store.read_current("analysis") == original.result


def race_publish(database: Path, ticket: Ticket, requests: list[tuple[str, bytes]]) -> list:
    barrier = Barrier(len(requests))

    def run(request: tuple[str, bytes]):
        with PublishStore(database) as connection:
            barrier.wait(timeout=5)
            try:
                return connection.publish(ticket, *request).status
            except (StaleTicket, IdempotencyConflict) as error:
                return type(error).__name__

    with ThreadPoolExecutor(max_workers=len(requests)) as workers:
        return list(workers.map(run, requests))


def test_two_connections_racing_identical_request_publish_once(
    store: PublishStore, tmp_path: Path,
) -> None:
    ticket = store.grant("analysis", "worker")
    statuses = race_publish(tmp_path / "results.sqlite", ticket,
                            [("operation", b"result"), ("operation", b"result")])
    assert sorted(statuses) == ["published", "replayed"]
    resources, publications = snapshot(tmp_path / "results.sqlite")
    assert len(publications) == 1
    assert resources[0][-1] == 0


def test_two_connections_cannot_consume_ticket_twice(store: PublishStore, tmp_path: Path) -> None:
    ticket = store.grant("analysis", "worker")
    statuses = race_publish(tmp_path / "results.sqlite", ticket,
                            [("operation-A", b"A"), ("operation-B", b"B")])
    assert sorted(statuses) == ["StaleTicket", "published"]
    assert len(snapshot(tmp_path / "results.sqlite")[1]) == 1
    assert store.read_current("analysis").payload in (b"A", b"B")


def test_two_connections_conflicting_operation_id_choose_one(
    store: PublishStore, tmp_path: Path,
) -> None:
    ticket = store.grant("analysis", "worker")
    statuses = race_publish(tmp_path / "results.sqlite", ticket,
                            [("operation", b"A"), ("operation", b"B")])
    assert sorted(statuses) == ["IdempotencyConflict", "published"]
    assert len(snapshot(tmp_path / "results.sqlite")[1]) == 1


def test_concurrent_coordinators_issue_distinct_monotone_generations(
    store: PublishStore, tmp_path: Path,
) -> None:
    barrier = Barrier(2)

    def claim(owner: str):
        with PublishStore(tmp_path / "results.sqlite") as connection:
            barrier.wait(timeout=5)
            return connection.grant("analysis", owner)

    with ThreadPoolExecutor(max_workers=2) as workers:
        tickets = sorted(workers.map(claim, ("A", "B")), key=lambda t: t.generation)
    assert [t.generation for t in tickets] == [1, 2]
    with pytest.raises(StaleTicket):
        store.publish(tickets[0], "stale", b"old")
    assert store.publish(tickets[1], "current", b"new").status == "published"


def test_mid_transaction_failure_rolls_back_ticket_and_history(
    store: PublishStore, tmp_path: Path,
) -> None:
    database = tmp_path / "results.sqlite"
    ticket = store.grant("analysis", "worker")
    with sqlite3.connect(database) as connection:
        connection.execute("""CREATE TRIGGER fail_history AFTER INSERT ON plectis_publications
                              BEGIN SELECT RAISE(ABORT,'injected storage error'); END""")
    before = snapshot(database)
    with pytest.raises(sqlite3.IntegrityError, match="injected storage error"):
        store.publish(ticket, "operation", b"result")
    assert snapshot(database) == before
    assert store.read_current("analysis") is None
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TRIGGER fail_history")
    assert store.publish(ticket, "operation", b"result").status == "published"


def test_generation_exhaustion_fails_without_changing_state(
    store: PublishStore, tmp_path: Path,
) -> None:
    database = tmp_path / "results.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE plectis_publish_resources SET generation=?", (MAX_GENERATION,))
    before = snapshot(database)
    with pytest.raises(ValueError, match="exhausted"):
        store.grant("analysis", "worker")
    with pytest.raises(ValueError, match="exhausted"):
        store.change_identity("analysis", "input-v2", "contract-v1")
    assert snapshot(database) == before
    # An identity no-op and cancellation do not require another generation.
    store.change_identity("analysis", "input-v1", "contract-v1")
    store.revoke("analysis")
    assert snapshot(database) == before


@pytest.mark.parametrize("generation", [True, False, 1.0, "1", 0, -1, MAX_GENERATION + 1])
def test_ticket_rejects_invalid_generation(generation: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        Ticket("analysis", generation, "worker", "input", "contract")


@pytest.mark.parametrize("bad", [None, 1, "", " \n", "bad\x00id", "é" * 513])
def test_identifiers_are_strict_before_mutation(
    store: PublishStore, tmp_path: Path, bad: object,
) -> None:
    before = snapshot(tmp_path / "results.sqlite")
    with pytest.raises((TypeError, ValueError)):
        store.grant("analysis", bad)
    with pytest.raises((TypeError, ValueError)):
        store.create(bad, "input", "contract")
    assert snapshot(tmp_path / "results.sqlite") == before


def test_ticket_revalidated_if_frozen_construction_is_bypassed(
    store: PublishStore, tmp_path: Path,
) -> None:
    ticket = store.grant("analysis", "worker")
    object.__setattr__(ticket, "generation", True)
    before = snapshot(tmp_path / "results.sqlite")
    with pytest.raises(TypeError):
        store.publish(ticket, "operation", b"result")
    assert snapshot(tmp_path / "results.sqlite") == before


@pytest.mark.parametrize("payload", [None, "text", 1, bytearray(b"result"), memoryview(b"result")])
def test_payload_requires_bytes_without_consuming_ticket(
    store: PublishStore, tmp_path: Path, payload: object,
) -> None:
    ticket = store.grant("analysis", "worker")
    before = snapshot(tmp_path / "results.sqlite")
    with pytest.raises(TypeError):
        store.publish(ticket, "operation", payload)
    assert snapshot(tmp_path / "results.sqlite") == before


def test_payload_and_identifier_size_boundaries(store: PublishStore) -> None:
    ticket = store.grant("analysis", "worker")
    with pytest.raises(ValueError, match="payload exceeds"):
        store.publish(ticket, "operation", b"x" * (MAX_PAYLOAD_BYTES + 1))
    result = store.publish(ticket, "é" * (MAX_IDENTIFIER_BYTES // 2), b"x" * MAX_PAYLOAD_BYTES)
    assert result.result.payload == b"x" * MAX_PAYLOAD_BYTES
    store.create("empty", "input", "contract")
    empty = store.publish(store.grant("empty", "worker"), "empty", b"")
    assert empty.result.payload == b""


def test_missing_and_duplicate_resources_are_explicit(store: PublishStore) -> None:
    with pytest.raises(KeyError):
        store.grant("missing", "worker")
    with pytest.raises(KeyError):
        store.change_identity("missing", "input", "contract")
    with pytest.raises(KeyError):
        store.revoke("missing")
    with pytest.raises(sqlite3.IntegrityError):
        store.create("analysis", "new input", "new contract")
    assert store.read_current("missing") is None
