// SPDX-License-Identifier: Apache-2.0
// IDs are normalized and ranked by the trusted adapter. No claim is made
// about external observations, Python parsing, sorting or row authenticity.
module EvidenceDiff {
  datatype Cell = Cell(labLast: int, oracleLast: int, category: int)

  predicate LastAt(s: seq<int>, key: int, index: int) {
    if index == -1 then key !in s
    else (0 <= index < |s| && s[index] == key &&
      (forall j: int :: index < j < |s| ==> s[j] != key))
  }

  // Independent classification: 0 absent, 1 lab only, 2 oracle only, 3 shared.
  predicate Classified(s: seq<int>, t: seq<int>, key: int, c: Cell) {
    LastAt(s, key, c.labLast) && LastAt(t, key, c.oracleLast) &&
    (c.category == 0 <==> key !in s && key !in t) &&
    (c.category == 1 <==> key in s && key !in t) &&
    (c.category == 2 <==> key !in s && key in t) &&
    (c.category == 3 <==> key in s && key in t) &&
    0 <= c.category <= 3
  }

  method FindLast(s: seq<int>, key: int) returns (index: int)
    ensures LastAt(s, key, index)
  {
    var i := |s|;
    while i > 0
      invariant 0 <= i <= |s|
      invariant forall j: int :: i <= j < |s| ==> s[j] != key
      decreases i
    {
      i := i - 1;
      if s[i] == key {
        index := i;
        return;
      }
    }
    index := -1;
  }

  method Compute(lab: seq<int>, oracle: seq<int>, size: nat) returns (cells: seq<Cell>)
    requires forall i: int :: 0 <= i < |lab| ==> 0 <= lab[i] < size
    requires forall i: int :: 0 <= i < |oracle| ==> 0 <= oracle[i] < size
    ensures |cells| == size
    ensures forall key: int :: 0 <= key < size ==> Classified(lab, oracle, key, cells[key])
  {
    cells := [];
    var key: nat := 0;
    while key < size
      invariant key <= size
      invariant |cells| == key
      invariant forall k: int :: 0 <= k < key ==> Classified(lab, oracle, k, cells[k])
      decreases size - key
    {
      var l := FindLast(lab, key);
      var o := FindLast(oracle, key);
      var kind := if l < 0 then (if o < 0 then 0 else 2) else (if o < 0 then 1 else 3);
      cells := cells + [Cell(l, o, kind)];
      key := key + 1;
    }
  }
}
