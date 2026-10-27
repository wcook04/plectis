# Ownership classification core

`OwnershipClassification.dfy` proves that every matching live claim protects
its generated path, regardless of claim order. `Compute` returns a live-owner
classification and no-patch action whenever any generated path has a matching
live claim. `SelectedPrefix` independently specifies the earliest claim with
the highest observed priority: live, unresolved freshness, then stale.
Stale-release advice therefore requires that every matching claim is known
stale. This deliberately repairs the former first-matching-claim policy: an
earlier stale claim must not hide a later live owner.

The iterative `FindOwner` and `Compute` methods establish exact per-path
selection, the row partition, the aggregate priority and its corresponding
action code. Unknown observations receive a separate inspection action.
The first-claim mutant restores the old selection behavior without changing
the specification; a second mutant puts stale aggregate state before live.
Both fail their postconditions. `metadata.json` records the pinned compiler,
proof results, source-linked mutations and generated hashes.

The production generated-surface classifier calls this core through the sealed
component worker. Host normalization retains every supplied session-card and
claim freshness signal, protects any live signal, and treats missing owner
identity or otherwise uncertain freshness as unresolved. Reports retain all
matching claims and conflicting observations, flag distinct live sessions on
the same exact path, and select a live representative for a live handoff.
The closure lens uses that representative; its separate overbroad-scope case
also uses the same core selection policy.

The theorem concerns normalized exact path IDs and supplied freshness states.
Python normalization, representative display and collision diagnostics are
separately tested host operations. It does not prove session liveness,
identity authenticity, parent/child scope overlap, real lock enforcement or
concurrent execution safety. Boolean claim inputs remain compatible (`true`
means live and `false` means known stale); the host uses explicit
`live`/`unknown`/`stale` states. The compiler, Dafny runtime, Boogie/Z3,
adapter, sealed worker and host remain trusted. The worker has a 30-second
timeout and raises on failure without an unverified fallback; mathematical
termination does not establish a wall-clock or memory bound.
