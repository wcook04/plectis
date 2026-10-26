// Original research prototype, 23 October 2026.
// A graph-level repair planner. It makes no claim about dependency discovery,
// fingerprint truth, the runtime filesystem, or the replayability of effects.

module Repair {
  predicate ValidDeps(deps: seq<seq<int>>) {
    forall i, j :: 0 <= i < |deps| && 0 <= j < |deps[i]| ==>
      0 <= deps[i][j] < i
  }

  predicate ValidInputs(deps: seq<seq<int>>, roots: seq<bool>, effects: seq<bool>) {
    |deps| == |roots| && |deps| == |effects| && ValidDeps(deps)
  }

  function AnyDep(flags: seq<bool>, parents: seq<int>): bool
    requires forall j :: 0 <= j < |parents| ==> 0 <= parents[j] < |flags|
  {
    exists j :: 0 <= j < |parents| && flags[parents[j]]
  }

  function EffectRoots(dirty: seq<bool>, effects: seq<bool>): seq<bool>
    requires |dirty| == |effects|
  {
    seq(|dirty|, i requires 0 <= i < |dirty| => dirty[i] && effects[i])
  }

  predicate Recurrence(deps: seq<seq<int>>, seeds: seq<bool>, flags: seq<bool>) {
    ValidDeps(deps) && |seeds| == |deps| && |flags| == |deps| &&
    forall i :: 0 <= i < |deps| ==>
      flags[i] == (seeds[i] || AnyDep(flags, deps[i]))
  }

  // Total executable checker: malformed shapes/indices are rejected.
  function CheckPlan(deps: seq<seq<int>>, roots: seq<bool>, effects: seq<bool>,
                     dirty: seq<bool>, blocked: seq<bool>): bool {
    ValidInputs(deps, roots, effects) &&
    |dirty| == |deps| && |blocked| == |deps| &&
    Recurrence(deps, roots, dirty) &&
    Recurrence(deps, EffectRoots(dirty, effects), blocked)
  }

  ghost predicate PrefixRecurrence(deps: seq<seq<int>>, seeds: seq<bool>, flags: seq<bool>) {
    ValidDeps(deps) && |seeds| == |deps| && |flags| <= |deps| &&
    forall i :: 0 <= i < |flags| ==>
      flags[i] == (seeds[i] || AnyDep(flags, deps[i]))
  }

  lemma AnyDepAppend(flags: seq<bool>, parents: seq<int>, value: bool)
    requires forall j :: 0 <= j < |parents| ==> 0 <= parents[j] < |flags|
    ensures AnyDep(flags + [value], parents) == AnyDep(flags, parents)
  {
  }

  lemma ExtendPrefix(deps: seq<seq<int>>, seeds: seq<bool>, flags: seq<bool>)
    requires PrefixRecurrence(deps, seeds, flags)
    requires |flags| < |deps|
    ensures PrefixRecurrence(deps, seeds,
      flags + [seeds[|flags|] || AnyDep(flags, deps[|flags|])])
  {
    var i := |flags|;
    var value := seeds[i] || AnyDep(flags, deps[i]);
    var next := flags + [value];
    forall k | 0 <= k < |next|
      ensures next[k] == (seeds[k] || AnyDep(next, deps[k]))
    {
      AnyDepAppend(flags, deps[k], value);
      if k < i {
        assert flags[k] == (seeds[k] || AnyDep(flags, deps[k]));
      } else {
        assert k == i;
      }
    }
  }

  method Close(deps: seq<seq<int>>, seeds: seq<bool>) returns (flags: seq<bool>)
    requires ValidDeps(deps) && |seeds| == |deps|
    ensures Recurrence(deps, seeds, flags)
  {
    flags := [];
    while |flags| < |deps|
      invariant PrefixRecurrence(deps, seeds, flags)
      decreases |deps| - |flags|
    {
      ExtendPrefix(deps, seeds, flags);
      flags := flags + [seeds[|flags|] || AnyDep(flags, deps[|flags|])];
    }
  }

  method MakePlan(deps: seq<seq<int>>, roots: seq<bool>, effects: seq<bool>)
      returns (dirty: seq<bool>, blocked: seq<bool>)
    requires ValidInputs(deps, roots, effects)
    ensures CheckPlan(deps, roots, effects, dirty, blocked)
  {
    dirty := Close(deps, roots);
    var blockedSeeds := EffectRoots(dirty, effects);
    blocked := Close(deps, blockedSeeds);
  }

  ghost predicate Closed(deps: seq<seq<int>>, seeds: seq<bool>, flags: seq<bool>) {
    ValidDeps(deps) && |seeds| == |deps| && |flags| == |deps| &&
    (forall i :: 0 <= i < |deps| && seeds[i] ==> flags[i]) &&
    (forall i, j :: (0 <= i < |deps| && 0 <= j < |deps[i]| &&
       flags[deps[i][j]]) ==> flags[i])
  }

  ghost predicate Subset(left: seq<bool>, right: seq<bool>) {
    |left| == |right| && forall i :: 0 <= i < |left| && left[i] ==> right[i]
  }

  ghost predicate LeastClosure(deps: seq<seq<int>>, seeds: seq<bool>, flags: seq<bool>) {
    Closed(deps, seeds, flags) &&
    forall other: seq<bool> :: Closed(deps, seeds, other) ==> Subset(flags, other)
  }

  lemma RecurrenceIsClosed(deps: seq<seq<int>>, seeds: seq<bool>, flags: seq<bool>)
    requires Recurrence(deps, seeds, flags)
    ensures Closed(deps, seeds, flags)
  {
    forall i, j | 0 <= i < |deps| && 0 <= j < |deps[i]| && flags[deps[i][j]]
      ensures flags[i]
    {
      assert AnyDep(flags, deps[i]);
    }
  }

  lemma RecurrenceIsBelowClosed(deps: seq<seq<int>>, seeds: seq<bool>,
                               flags: seq<bool>, other: seq<bool>)
    requires Recurrence(deps, seeds, flags)
    requires Closed(deps, seeds, other)
    ensures Subset(flags, other)
  {
    var i := 0;
    while i < |deps|
      invariant 0 <= i <= |deps|
      invariant forall k :: 0 <= k < i && flags[k] ==> other[k]
      decreases |deps| - i
    {
      if flags[i] && !seeds[i] {
        assert AnyDep(flags, deps[i]);
        var j :| 0 <= j < |deps[i]| && flags[deps[i][j]];
        assert other[deps[i][j]];
        assert other[i];
      }
      i := i + 1;
    }
  }

  lemma RecurrenceIsLeast(deps: seq<seq<int>>, seeds: seq<bool>, flags: seq<bool>)
    requires Recurrence(deps, seeds, flags)
    ensures LeastClosure(deps, seeds, flags)
  {
    RecurrenceIsClosed(deps, seeds, flags);
    forall other: seq<bool> | Closed(deps, seeds, other)
      ensures Subset(flags, other)
    {
      RecurrenceIsBelowClosed(deps, seeds, flags, other);
    }
  }

  lemma RecurrenceUnique(deps: seq<seq<int>>, seeds: seq<bool>,
                         left: seq<bool>, right: seq<bool>)
    requires Recurrence(deps, seeds, left) && Recurrence(deps, seeds, right)
    ensures left == right
  {
    RecurrenceIsClosed(deps, seeds, left);
    RecurrenceIsClosed(deps, seeds, right);
    RecurrenceIsBelowClosed(deps, seeds, left, right);
    RecurrenceIsBelowClosed(deps, seeds, right, left);
    assert forall i :: 0 <= i < |left| ==> left[i] == right[i];
  }

  // This is the checker soundness theorem, for all finite valid DAG inputs.
  lemma AcceptedPlanIsLeast(deps: seq<seq<int>>, roots: seq<bool>, effects: seq<bool>,
                           dirty: seq<bool>, blocked: seq<bool>)
    requires CheckPlan(deps, roots, effects, dirty, blocked)
    ensures LeastClosure(deps, roots, dirty)
    ensures LeastClosure(deps, EffectRoots(dirty, effects), blocked)
    ensures Subset(blocked, dirty)
    ensures forall i :: 0 <= i < |deps| && dirty[i] && !blocked[i] ==> !effects[i]
    // Exactly one classification: reuse, automatic rerun, or blocked.
    ensures forall i :: 0 <= i < |deps| ==>
      (if !dirty[i] then 1 else 0) +
      (if dirty[i] && !blocked[i] then 1 else 0) +
      (if blocked[i] then 1 else 0) == 1
  {
    var blockedSeeds := EffectRoots(dirty, effects);
    RecurrenceIsLeast(deps, roots, dirty);
    RecurrenceIsLeast(deps, blockedSeeds, blocked);
    assert Closed(deps, blockedSeeds, dirty);
    RecurrenceIsBelowClosed(deps, blockedSeeds, blocked, dirty);
  }

  lemma AcceptedPlansAreUnique(deps: seq<seq<int>>, roots: seq<bool>, effects: seq<bool>,
                               d1: seq<bool>, b1: seq<bool>, d2: seq<bool>, b2: seq<bool>)
    requires CheckPlan(deps, roots, effects, d1, b1)
    requires CheckPlan(deps, roots, effects, d2, b2)
    ensures d1 == d2 && b1 == b2
  {
    RecurrenceUnique(deps, roots, d1, d2);
    RecurrenceUnique(deps, EffectRoots(d1, effects), b1, b2);
  }
}
