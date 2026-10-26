// SPDX-License-Identifier: Apache-2.0
// Section sizes are trusted adapter observations. The decision core supports
// negative budgets, matching the existing Python projection.
module BudgetPacking {
  function IncludedTotal(sizes: seq<nat>, decisions: seq<bool>): nat
    requires |sizes| == |decisions|
    decreases |sizes|
  {
    if |sizes| == 0 then 0
    else (IncludedTotal(sizes[..|sizes|-1], decisions[..|decisions|-1]) +
          (if decisions[|decisions|-1] then sizes[|sizes|-1] else 0))
  }

  // Each position belongs to exactly one output subsequence, in input order.
  // The independent specification names the running sum at every position.
  predicate OrderedGreedy(sizes: seq<nat>, budget: int, decisions: seq<bool>) {
    |sizes| == |decisions| &&
    (forall i: int :: 0 <= i < |sizes| ==>
      (decisions[i] <==>
       IncludedTotal(sizes[..i], decisions[..i]) + sizes[i] <= budget))
  }

  method Pack(sizes: seq<nat>, budget: int) returns (decisions: seq<bool>, total: nat)
    ensures OrderedGreedy(sizes, budget, decisions)
    ensures total == IncludedTotal(sizes, decisions)
    ensures budget >= 0 ==> total <= budget
    ensures budget < 0 ==> total == 0
  {
    decisions := [];
    total := 0;
    var i := 0;
    while i < |sizes|
      invariant 0 <= i <= |sizes|
      invariant |decisions| == i
      invariant total == IncludedTotal(sizes[..i], decisions)
      invariant budget >= 0 ==> total <= budget
      invariant budget < 0 ==> total == 0
      invariant forall j: int :: 0 <= j < i ==>
        (decisions[j] <==>
         IncludedTotal(sizes[..j], decisions[..j]) + sizes[j] <= budget)
      decreases |sizes| - i
    {
      ghost var previous := decisions;
      ghost var previousTotal := total;
      var fits := sizes[i] <= budget;
      decisions := decisions + [fits];
      if fits { total := total + sizes[i]; }
      assert decisions[..i] == previous;
      assert sizes[..i+1][..i] == sizes[..i];
      assert IncludedTotal(sizes[..i+1], decisions) ==
        previousTotal + (if fits then sizes[i] else 0);
      forall j: int | 0 <= j < i + 1
        ensures decisions[j] <==>
          IncludedTotal(sizes[..j], decisions[..j]) + sizes[j] <= budget
      {
        if j < i {
          assert decisions[..j] == previous[..j];
        } else {
          assert j == i;
          assert decisions[..j] == previous;
        }
      }
      i := i + 1;
    }
    assert i == |sizes|;
    assert sizes[..i] == sizes;
  }

  // The host may split a large sequence into bounded worker requests. The
  // second request receives the budget remaining after the first result.
  lemma TotalConcat(a: seq<nat>, b: seq<nat>, x: seq<bool>, y: seq<bool>)
    requires |a| == |x| && |b| == |y|
    ensures IncludedTotal(a + b, x + y) == IncludedTotal(a, x) + IncludedTotal(b, y)
    decreases |b|
  {
    if |b| > 0 {
      var n := |b| - 1;
      TotalConcat(a, b[..n], x, y[..n]);
      assert (a + b)[..|a + b|-1] == a + b[..n];
      assert (x + y)[..|x + y|-1] == x + y[..n];
      assert (a + b)[|a + b|-1] == b[n];
      assert (x + y)[|x + y|-1] == y[n];
      calc {
        IncludedTotal(a + b, x + y);
        == IncludedTotal(a + b[..n], x + y[..n]) + (if y[n] then b[n] else 0);
        == IncludedTotal(a, x) + IncludedTotal(b[..n], y[..n]) + (if y[n] then b[n] else 0);
        == IncludedTotal(a, x) + IncludedTotal(b, y);
      }
    } else {
      assert b == [] && y == [];
      assert a + b == a && x + y == x;
      assert IncludedTotal(b, y) == 0;
    }
  }

  lemma GreedyConcat(a: seq<nat>, b: seq<nat>, x: seq<bool>, y: seq<bool>, budget: int)
    requires OrderedGreedy(a, budget, x)
    requires OrderedGreedy(b, budget - IncludedTotal(a, x), y)
    ensures OrderedGreedy(a + b, budget, x + y)
  {
    forall i: int | 0 <= i < |a + b|
      ensures (x + y)[i] <==>
        IncludedTotal((a + b)[..i], (x + y)[..i]) + (a + b)[i] <= budget
    {
      if i < |a| {
        assert (a + b)[..i] == a[..i];
        assert (x + y)[..i] == x[..i];
      } else {
        var k := i - |a|;
        assert (a + b)[..i] == a + b[..k];
        assert (x + y)[..i] == x + y[..k];
        TotalConcat(a, b[..k], x, y[..k]);
      }
    }
  }
}
