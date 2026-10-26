// SPDX-License-Identifier: Apache-2.0
// Exact normalized paths and observed freshness are trusted host inputs.
module OwnershipClassification {
  datatype Freshness = Stale | Unknown | Live
  datatype Path = Path(id: int, generated: bool)
  datatype Claim = Claim(path: int, freshness: Freshness)
  datatype Row = Row(ownerIndex: int, kind: int)

  function Priority(state: Freshness): int {
    if state == Live then 3 else if state == Unknown then 2 else 1
  }

  // Earliest highest-priority match: live > unresolved > stale.
  predicate SelectedPrefix(claims: seq<Claim>, path: int, n: nat, owner: int)
    requires n <= |claims|
  {
    if owner == -1 then (forall j: int :: 0 <= j < n ==> claims[j].path != path)
    else (0 <= owner < n && claims[owner].path == path &&
      (forall j: int :: 0 <= j < n && claims[j].path == path ==>
        Priority(claims[j].freshness) <= Priority(claims[owner].freshness)) &&
      (forall j: int :: 0 <= j < owner && claims[j].path == path ==>
        Priority(claims[j].freshness) < Priority(claims[owner].freshness)))
  }

  predicate HasLive(claims: seq<Claim>, path: int) {
    exists j: int :: 0 <= j < |claims| && claims[j].path == path && claims[j].freshness == Live
  }

  // Kinds: 0 unrelated, 1 unowned, 2 live, 3 stale, 5 unresolved freshness.
  predicate RowSpec(p: Path, claims: seq<Claim>, row: Row) {
    (!p.generated && row == Row(-1, 0)) ||
    (p.generated && SelectedPrefix(claims, p.id, |claims|, row.ownerIndex) &&
      ((row.ownerIndex == -1 && row.kind == 1) ||
       (0 <= row.ownerIndex < |claims| &&
        ((claims[row.ownerIndex].freshness == Live && row.kind == 2) ||
         (claims[row.ownerIndex].freshness == Unknown && row.kind == 5) ||
         (claims[row.ownerIndex].freshness == Stale && row.kind == 3)))))
  }

  lemma LiveRowExact(p: Path, claims: seq<Claim>, row: Row)
    requires RowSpec(p, claims, row)
    ensures row.kind == 2 <==> p.generated && HasLive(claims, p.id)
  {}

  predicate ClassificationSpec(rows: seq<Row>, c: int) {
    var live := exists i: int :: 0 <= i < |rows| && rows[i].kind == 2;
    var unknown := exists i: int :: 0 <= i < |rows| && rows[i].kind == 5;
    var stale := exists i: int :: 0 <= i < |rows| && rows[i].kind == 3;
    var unowned := exists i: int :: 0 <= i < |rows| && rows[i].kind == 1;
    (live && c == 2) || (!live && unknown && c == 5) ||
    (!live && !unknown && stale && c == 3) ||
    (!live && !unknown && !stale && unowned && c == 1) ||
    (!live && !unknown && !stale && !unowned && |rows| > 0 && c == 4) ||
    (|rows| == 0 && c == 0)
  }

  predicate ActionSpec(c: int, action: int) {
    (c == 2 && action == 11) || (c == 5 && action == 16) ||
    (c == 3 && action == 12) || (c == 1 && action == 13) ||
    (c == 4 && action == 14) || (c == 0 && action == 15)
  }

  method FindOwner(claims: seq<Claim>, path: int) returns (owner: int)
    ensures SelectedPrefix(claims, path, |claims|, owner)
  {
    owner := -1;
    var i: nat := 0;
    while i < |claims|
      invariant i <= |claims|
      invariant SelectedPrefix(claims, path, i, owner)
      invariant forall j: int :: 0 <= j < i && claims[j].path == path ==> claims[j].freshness != Live
      decreases |claims| - i
    {
      if claims[i].path == path {
        if claims[i].path == path {
          owner := i;
          return;
        }
        if owner < 0 || Priority(claims[i].freshness) > Priority(claims[owner].freshness) {
          owner := i;
        }
      }
      i := i + 1;
    }
  }

  method Compute(paths: seq<Path>, claims: seq<Claim>)
      returns (rows: seq<Row>, classification: int, action: int)
    ensures |rows| == |paths|
    ensures forall i: int :: 0 <= i < |paths| ==> RowSpec(paths[i], claims, rows[i])
    ensures forall i: int :: 0 <= i < |paths| ==> (rows[i].kind == 2 <==> paths[i].generated && HasLive(claims, paths[i].id))
    ensures ClassificationSpec(rows, classification)
    ensures ActionSpec(classification, action)
    ensures (exists i: int :: 0 <= i < |paths| && paths[i].generated && HasLive(claims, paths[i].id)) ==>
      classification == 2 && action == 11
  {
    rows := [];
    var live, unknown, stale, unowned := false, false, false, false;
    var i: nat := 0;
    while i < |paths|
      invariant i <= |paths| && |rows| == i
      invariant forall j: int :: 0 <= j < i ==> RowSpec(paths[j], claims, rows[j])
      invariant live <==> (exists j: int :: 0 <= j < i && rows[j].kind == 2)
      invariant unknown <==> (exists j: int :: 0 <= j < i && rows[j].kind == 5)
      invariant stale <==> (exists j: int :: 0 <= j < i && rows[j].kind == 3)
      invariant unowned <==> (exists j: int :: 0 <= j < i && rows[j].kind == 1)
      decreases |paths| - i
    {
      var row := Row(-1, 0);
      if paths[i].generated {
        var owner := FindOwner(claims, paths[i].id);
        row := if owner < 0 then Row(-1, 1)
          else if claims[owner].freshness == Live then Row(owner, 2)
          else if claims[owner].freshness == Unknown then Row(owner, 5) else Row(owner, 3);
      }
      assert RowSpec(paths[i], claims, row);
      rows := rows + [row];
      live := live || row.kind == 2;
      unknown := unknown || row.kind == 5;
      stale := stale || row.kind == 3;
      unowned := unowned || row.kind == 1;
      i := i + 1;
    }
    forall j | 0 <= j < |paths| { LiveRowExact(paths[j], claims, rows[j]); }
    classification := if live then 2 else if unknown then 5 else if stale then 3
      else if unowned then 1 else if |rows| > 0 then 4 else 0;
    action := if classification == 2 then 11 else if classification == 5 then 16
      else if classification == 3 then 12 else if classification == 1 then 13
      else if classification == 4 then 14 else 15;
  }
}
