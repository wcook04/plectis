// SPDX-License-Identifier: Apache-2.0
// Tokenization, split extraction, ID ordering and receipt construction are host observations.
module PremiseRanking {
  datatype Candidate = Candidate(eligible: bool, idRank: nat, counts: seq<nat>, bonus: bool)
  datatype Entry = Entry(index: nat, idRank: nat, score: nat)
  ghost function OverlapSpec(q: seq<nat>, p: seq<nat>): nat
    requires |q| == |p|
    decreases |q|
  {
    if |q| == 0 then 0 else (if q[0] <= p[0] then q[0] else p[0]) + OverlapSpec(q[1..], p[1..])
  }
  ghost function ScoreSpec(q: seq<nat>, c: Candidate): nat
    requires |q| == |c.counts|
  { OverlapSpec(q, c.counts) + (if c.bonus then 1 else 0) }
  function Before(a: Entry, b: Entry): bool {
    a.score > b.score || (a.score == b.score && (a.idRank < b.idRank ||
      (a.idRank == b.idRank && a.index <= b.index)))
  }
  // Independent specification of the intended lexicographic ordering.
  ghost predicate RankBefore(a: Entry, b: Entry) {
    a.score >= b.score && (a.score != b.score ||
      (a.idRank <= b.idRank && (a.idRank != b.idRank || a.index <= b.index)))
  }
  ghost predicate Ordered(s: seq<Entry>) {
    forall i, j :: 0 <= i < j < |s| ==> RankBefore(s[i], s[j])
  }
  ghost function Expected(q: seq<nat>, cs: seq<Candidate>, n: nat): multiset<Entry>
    requires n <= |cs|
    requires forall i :: 0 <= i < |cs| ==> |cs[i].counts| == |q|
    decreases n
  {
    if n == 0 then multiset{} else
      (Expected(q, cs, n-1) +
        (if cs[n-1].eligible then multiset{Entry(n-1, cs[n-1].idRank, ScoreSpec(q, cs[n-1]))} else multiset{}))
  }
  method Score(q: seq<nat>, p: seq<nat>, bonus: bool) returns (v: nat)
    requires |q| == |p|
    ensures v == OverlapSpec(q,p) + (if bonus then 1 else 0)
  {
    var i := |q|;
    v := if bonus then 1 else 0;
    while i > 0
      invariant 0 <= i <= |q|
      invariant v == OverlapSpec(q[i..],p[i..]) + (if bonus then 1 else 0)
      decreases i
    {
      i := i - 1;
      v := v + (if q[i] <= p[i] then q[i] else p[i]);
    }
  }
  method Insert(s: seq<Entry>, x: Entry) returns (t: seq<Entry>)
    requires Ordered(s)
    ensures Ordered(t)
    ensures multiset(t) == multiset(s) + multiset{x}
  {
    var i := 0;
    while i < |s| && !Before(x, s[i])
      invariant 0 <= i <= |s|
      invariant forall j :: 0 <= j < i ==> Before(s[j], x)
      decreases |s| - i
    {
      assert Before(s[i], x);
      i := i + 1;
    }
    t := s[..i] + [x] + s[i..];
    assert s == s[..i] + s[i..];
    assert multiset(t) == multiset(s[..i]) + multiset{x} + multiset(s[i..]);
    assert forall j :: i <= j < |s| ==> Before(x, s[j]) by {
      forall j | i <= j < |s| ensures Before(x, s[j]) {
        if j > i { assert RankBefore(s[i], s[j]); }
      }
    }
    assert Ordered(t) by {
      forall j, k | 0 <= j < k < |t| ensures RankBefore(t[j], t[k]) {
        if k < i {
          assert t[j] == s[j] && t[k] == s[k];
        } else if k == i {
          assert t[j] == s[j] && t[k] == x;
        } else if j == i {
          assert t[j] == x && t[k] == s[k - 1];
        } else if j < i {
          assert t[j] == s[j] && t[k] == s[k - 1];
        } else {
          assert t[j] == s[j - 1] && t[k] == s[k - 1];
        }
      }
    }
  }
  method Compute(q: seq<nat>, cs: seq<Candidate>) returns (out: seq<Entry>)
    requires forall i :: 0 <= i < |cs| ==> |cs[i].counts| == |q|
    ensures Ordered(out)
    ensures multiset(out) == Expected(q,cs,|cs|)
  {
    out := [];
    var i := 0;
    while i < |cs|
      invariant 0 <= i <= |cs|
      invariant Ordered(out)
      invariant multiset(out) == Expected(q,cs,i)
      decreases |cs| - i
    {
      if true {
        var v := Score(q,cs[i].counts,cs[i].bonus);
        out := Insert(out, Entry(i,cs[i].idRank,v));
      }
      i := i + 1;
    }
  }
}
