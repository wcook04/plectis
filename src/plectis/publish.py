# SPDX-License-Identifier: Apache-2.0
# Adapted from research returns p13/artifacts/publish_store.py (generation guard)
# and p11/queue-prototype/publication.py (atomic exact-request replay), 2026-10-23.
# Original SHA-256: p13 02a37aff2197a45a672692dc6959374900f59623dab6a29d1649723d5f2cc797;
# p11 872f8403970d4a39469667c88891543343ebba5567118625ca2a7bcda2422ec0.
"""Conditional publication of byte results in one local SQLite database.

The trusted coordinator issues tickets and controls database access. Tickets
are data, not cryptographic capabilities. A publication checks current identity
and ownership; it does not prove the result correct. See docs/guides/publish.md.
This adapter is tested Python/SQLite code, not a formally verified implementation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Iterator, Literal


MAX_GENERATION = 2**63 - 1
MAX_PAYLOAD_BYTES = 1024 * 1024
MAX_IDENTIFIER_BYTES = 1024


class StaleTicket(Exception):
    """This request has no current publication authority; nothing was changed."""


class IdempotencyConflict(Exception):
    """The operation ID already names a different committed request."""


def _identifier(value: object, name: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    if not value.strip() or "\x00" in value:
        raise ValueError(f"{name} must be nonblank and contain no NUL")
    if len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES:
        raise ValueError(f"{name} exceeds {MAX_IDENTIFIER_BYTES} UTF-8 bytes")


@dataclass(frozen=True, slots=True)
class Ticket:
    """Coordinator-issued resource identity for exactly one generation."""

    key: str
    generation: int
    owner: str
    input_id: str
    contract_id: str

    def __post_init__(self) -> None:
        for name in ("key", "owner", "input_id", "contract_id"):
            _identifier(getattr(self, name), name)
        if type(self.generation) is not int:
            raise TypeError("generation must be an integer, not bool")
        if not 1 <= self.generation <= MAX_GENERATION:
            raise ValueError("generation is outside the supported range")


@dataclass(frozen=True, slots=True)
class PublishedResult:
    """An immutable historical result; its presence does not imply currentness."""

    ticket: Ticket
    operation_id: str
    payload: bytes

    @property
    def key(self) -> str:
        return self.ticket.key

    @property
    def generation(self) -> int:
        return self.ticket.generation


@dataclass(frozen=True, slots=True)
class Publication:
    """A new publication or observation of the identical historical request."""

    status: Literal["published", "replayed"]
    result: PublishedResult


_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS plectis_publish_resources(
    key TEXT PRIMARY KEY NOT NULL,
    input_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    generation INTEGER NOT NULL DEFAULT 0
        CHECK(typeof(generation)='integer' AND generation BETWEEN 0 AND {MAX_GENERATION}),
    owner TEXT,
    active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS plectis_publications(
    operation_id TEXT PRIMARY KEY NOT NULL,
    resource_key TEXT NOT NULL REFERENCES plectis_publish_resources(key),
    generation INTEGER NOT NULL
        CHECK(typeof(generation)='integer' AND generation BETWEEN 1 AND {MAX_GENERATION}),
    owner TEXT NOT NULL,
    input_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    payload BLOB NOT NULL
        CHECK(typeof(payload)='blob' AND length(payload)<={MAX_PAYLOAD_BYTES}),
    UNIQUE(resource_key,generation)
);
"""


class PublishStore:
    """A trusted local store; each method commits its entire change atomically.

    Use a separate instance/connection per thread. The coordinator owns create,
    grant, change_identity and revoke. Workers receive tickets and call publish.
    Direct database access bypasses this cooperative API's authority boundary.
    """

    def __init__(self, database: str | Path):
        self._db = sqlite3.connect(database, isolation_level=None, timeout=5)
        self._db.row_factory = sqlite3.Row
        try:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.executescript("BEGIN IMMEDIATE;" + _SCHEMA + "COMMIT;")
        except BaseException:
            self._db.close()
            raise

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> PublishStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.execute("COMMIT")
        except BaseException:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise

    def _resource(self, key: str) -> sqlite3.Row:
        row = self._db.execute(
            "SELECT * FROM plectis_publish_resources WHERE key=?", (key,)
        ).fetchone()
        if row is None:
            raise KeyError(key)
        return row

    @staticmethod
    def _next_generation(generation: int) -> int:
        if generation >= MAX_GENERATION:
            raise ValueError("exhausted generation space")
        return generation + 1

    @staticmethod
    def _result(row: sqlite3.Row) -> PublishedResult:
        return PublishedResult(
            Ticket(row["resource_key"], row["generation"], row["owner"],
                   row["input_id"], row["contract_id"]),
            row["operation_id"], bytes(row["payload"]),
        )

    def create(self, key: str, input_id: str, contract_id: str) -> None:
        """Register a fresh resource; an existing key raises sqlite3.IntegrityError."""
        for name, value in (("key", key), ("input_id", input_id),
                            ("contract_id", contract_id)):
            _identifier(value, name)
        with self._transaction():
            self._db.execute(
                "INSERT INTO plectis_publish_resources(key,input_id,contract_id) VALUES(?,?,?)",
                (key, input_id, contract_id),
            )

    def grant(self, key: str, owner: str) -> Ticket:
        """Supersede previous work, even when the same owner acquires it again."""
        _identifier(key, "key")
        _identifier(owner, "owner")
        with self._transaction():
            row = self._resource(key)
            generation = self._next_generation(row["generation"])
            self._db.execute(
                """UPDATE plectis_publish_resources
                   SET generation=?,owner=?,active=1 WHERE key=?""",
                (generation, owner, key),
            )
            return Ticket(key, generation, owner, row["input_id"], row["contract_id"])

    def change_identity(self, key: str, input_id: str, contract_id: str) -> None:
        """Advance generation and revoke work on an actual input/contract change."""
        for name, value in (("key", key), ("input_id", input_id),
                            ("contract_id", contract_id)):
            _identifier(value, name)
        with self._transaction():
            row = self._resource(key)
            if (row["input_id"], row["contract_id"]) == (input_id, contract_id):
                return
            generation = self._next_generation(row["generation"])
            self._db.execute(
                """UPDATE plectis_publish_resources
                   SET input_id=?,contract_id=?,generation=?,active=0 WHERE key=?""",
                (input_id, contract_id, generation, key),
            )

    def revoke(self, key: str) -> None:
        """Cancel permission for a new publication; retain committed history."""
        _identifier(key, "key")
        with self._transaction():
            if self._db.execute(
                "UPDATE plectis_publish_resources SET active=0 WHERE key=?", (key,)
            ).rowcount != 1:
                raise KeyError(key)

    def publish(self, ticket: Ticket, operation_id: str, payload: bytes) -> Publication:
        """Publish once, or recover an identical committed request without effects.

        Operation IDs are unique across this store. Replays compare every ticket
        field and the full payload bytes; they do not require the old grant to
        remain current. A stale new request or conflicting replay changes nothing.
        An uncertain/lost response is recovered by submitting the identical request.
        """
        if type(ticket) is not Ticket:
            raise TypeError("ticket must be a Ticket")
        # Revalidate even if a caller bypassed the frozen dataclass constructor.
        ticket.__post_init__()
        _identifier(operation_id, "operation_id")
        if type(payload) is not bytes:
            raise TypeError("payload must be bytes")
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"payload exceeds {MAX_PAYLOAD_BYTES} bytes")
        result = PublishedResult(ticket, operation_id, payload)
        with self._transaction():
            old = self._db.execute(
                "SELECT * FROM plectis_publications WHERE operation_id=?", (operation_id,)
            ).fetchone()
            if old is not None:
                previous = self._result(old)
                if previous != result:
                    raise IdempotencyConflict(operation_id)
                return Publication("replayed", previous)
            changed = self._db.execute(
                """UPDATE plectis_publish_resources SET active=0
                   WHERE key=? AND generation=? AND owner=? AND input_id=?
                     AND contract_id=? AND active=1""",
                (ticket.key, ticket.generation, ticket.owner,
                 ticket.input_id, ticket.contract_id),
            ).rowcount
            if changed != 1:
                raise StaleTicket(ticket.key)
            self._db.execute(
                """INSERT INTO plectis_publications
                   (operation_id,resource_key,generation,owner,input_id,contract_id,payload)
                   VALUES(?,?,?,?,?,?,?)""",
                (operation_id, ticket.key, ticket.generation, ticket.owner,
                 ticket.input_id, ticket.contract_id, payload),
            )
            return Publication("published", result)

    def read_current(self, key: str) -> PublishedResult | None:
        """Read only a result for the current generation and input/contract IDs."""
        _identifier(key, "key")
        row = self._db.execute(
            """SELECT p.* FROM plectis_publications p
               JOIN plectis_publish_resources r ON p.resource_key=r.key
               WHERE r.key=? AND p.generation=r.generation
                 AND p.input_id=r.input_id AND p.contract_id=r.contract_id""", (key,)
        ).fetchone()
        return None if row is None else self._result(row)
