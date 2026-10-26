# Publish a result from the current worker

`plectis.publish` stores byte results in a local SQLite database. A delayed
worker cannot publish through this API after its ticket has been superseded.
An identical retry recovers its original committed result without publishing
again. The API is independent of Plectis's component catalogue and model tools.

```python
from plectis.publish import PublishStore, StaleTicket

with PublishStore("results.sqlite") as store:
    store.create("analysis", "input-sha256", "contract-v1")
    old = store.grant("analysis", "worker-A")
    current = store.grant("analysis", "worker-B")
    accepted = store.publish(current, "operation-B", b"checked result")
    assert accepted.status == "published"
    assert store.read_current("analysis") == accepted.result

    try:
        store.publish(old, "operation-A", b"obsolete result")
    except StaleTicket:
        pass

    recovered = store.publish(current, "operation-B", b"checked result")
    assert recovered.status == "replayed"
    assert recovered.result.payload == b"checked result"
```

Use a fresh database for that example; `create` rejects an existing resource.
Use one store instance per thread. Each instance owns its connection and closes
it when its context ends. No other package is needed at runtime.

## API and outcomes

| Call | Meaning |
|---|---|
| `create(key, input_id, contract_id)` | Register a resource at generation zero. Duplicate keys raise `sqlite3.IntegrityError`. |
| `grant(key, owner)` | Return an immutable `Ticket` for a new generation and supersede prior work. |
| `change_identity(key, input_id, contract_id)` | Increment generation and revoke work if either identity changes. An exact no-op preserves the grant. |
| `revoke(key)` | Cancel permission for a new publication. Keep already committed results. |
| `publish(ticket, operation_id, payload)` | Commit once or replay an identical historical request. |
| `read_current(key)` | Return the result for the current generation and identities, or `None`. |

A `Ticket` carries `key`, `generation`, `owner`, `input_id` and `contract_id`.
A `Publication` carries `status` (`"published"` or `"replayed"`) and `result`.
The immutable `PublishedResult` carries `ticket`, `operation_id` and `payload`,
with `key` and `generation` convenience properties.

Operation IDs are unique across the database. Reusing a committed ID with a
different ticket field or different payload raises `IdempotencyConflict`.
A new request whose ticket is no longer active raises `StaleTicket`.
These refusals change no state. Invalid types or sizes raise `TypeError` or
`ValueError` before any transaction. Coordinator calls on missing resources
raise `KeyError`; reading a missing resource returns `None`.

Payloads must be `bytes`, at most 1 MiB. Identifiers must be nonblank strings,
contain no NUL and occupy at most 1,024 UTF-8 bytes. Generations are strict
integers from one through `2**63 - 1`; booleans are rejected. Reaching the
maximum prevents another grant or identity change without altering state.
There is no resource deletion or generation reset API.

## Recover a lost response

Keep the exact ticket, operation ID and payload until the outcome is known.
After a process restart, reopen the same database and call `publish` with
those same values. If they already committed, the call returns `"replayed"`
and the original result. If they did not commit and the ticket is still
current, it may publish now. If the ticket lost authority first, it is refused.
Changing the operation ID is a new request and does not recover the old one.

Historical replay remains available after revocation, a new grant or an
identity change. It observes a prior effect and grants no new publication
authority. `read_current` has different semantics: any new grant makes the
previous result unavailable there, even with unchanged input identities.
Restoring input A after an A-to-B change advances generation again, so it
cannot revive an old ticket or current-result label. Revoking a ticket after
publication leaves that already committed result current until generation
or identities change.

## What the boundary establishes

The generation/owner/input/contract guard, ticket consumption, exact result
bytes and operation-history row share one writer transaction. Matching retries
compare all ticket fields and the complete payload bytes. SQLite transaction
and storage semantics are trusted. Operational errors propagate; an open
transaction is rolled back. Response loss still requires the recovery rule.
Tests exercise independent connections, races, reopening and injected SQL
failure. They do not establish arbitrary power-loss durability.

The coordinator controls grants, supplies input and contract identities, and
protects the database from direct worker writes. A ticket is structured data,
not cryptographic authorisation. Host authentication, current read permissions,
and a protected service boundary belong to an integrating application. Direct
database access or a caller able to impersonate the coordinator bypasses this
cooperative API's protection.

Publication does not check whether the result satisfies its named contract.
An integrating host must check the exact immutable input and result bytes
against a separately selected contract, then publish those same bytes under
the corresponding identities. A string saying `"input-sha256"` does not
establish what a worker read. This module performs no remote effect and makes
no claim about exactly-once provider calls, quotas, leases or prompt injection.

## Evidence and next formal obligation

This is a tested Python/SQLite adapter. Its implementation is adapted from the
23 October 2026 p13 research return's guarded store and p11's transaction and
full-request replay mechanism. The source header records exact original hashes;
those return experiments were independently rerun before adaptation. They are
research proposals rather than formally verified dependencies. Plectis's
Apache-2.0 licence covers this adaptation.

The next formal target is a small executable admission function over a
current resource row, ticket and existing operation record. It must distinguish
new admission, exact historical replay, conflicting replay and stale work.
If implemented and checked in Dafny or another suitable tool, its generated
function must actually be called inside this writer transaction on the rows
that will be updated. A separate pleasant model or an uncalled proof would
not verify this adapter. Connecting its decisions to decoding, the SQL update,
history insertion and rollback remains an explicit refinement obligation.

Run the focused tests from the repository root with the test dependencies
installed:

```sh
python -m pytest tests/test_publish.py --basetemp /tmp/plectis-publish-pytest
```
