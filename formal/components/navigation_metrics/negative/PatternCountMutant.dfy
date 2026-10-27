// SPDX-License-Identifier: Apache-2.0
// Counts and decisions over normalized, duplicate-free expected and selected IDs.
module NavigationMetrics {
  predicate MatchSpec(p: string, s: string) {
    if |p| > 0 && p[|p|-1] == '*' then
      |s| >= |p|-1 && s[..|p|-1] == p[..|p|-1]
    else p == s
  }
  function Match(p: string, s: string): bool {
    if |p| > 0 && p[|p|-1] == '*' then
      |s| >= |p|-1 && s[..|p|-1] == p[..|p|-1]
    else p == s
  }
  predicate FoundSpec(p: string, selected: seq<string>) {
    exists j :: 0 <= j < |selected| && MatchSpec(p, selected[j])
  }
  predicate RelevantSpec(s: string, expected: seq<string>) {
    exists j :: 0 <= j < |expected| && MatchSpec(expected[j], s)
  }
  ghost function AnySelected(p: string, s: seq<string>, n: nat): bool
    requires n <= |s|
    decreases n
  { if n == 0 then false else AnySelected(p,s,n-1) || Match(p,s[n-1]) }
  ghost function AnyExpected(s: string, e: seq<string>, n: nat): bool
    requires n <= |e|
    decreases n
  { if n == 0 then false else AnyExpected(s,e,n-1) || Match(e[n-1],s) }
  lemma AnySelectedExact(p: string, s: seq<string>, n: nat)
    requires n <= |s|
    ensures AnySelected(p,s,n) <==> (exists j :: 0 <= j < n && MatchSpec(p,s[j]))
    decreases n
  { if n > 0 { AnySelectedExact(p,s,n-1); } }
  lemma AnyExpectedExact(s: string, e: seq<string>, n: nat)
    requires n <= |e|
    ensures AnyExpected(s,e,n) <==> (exists j :: 0 <= j < n && MatchSpec(e[j],s))
    decreases n
  { if n > 0 { AnyExpectedExact(s,e,n-1); } }
  ghost function FoundCount(e: seq<string>, s: seq<string>, n: nat): nat
    requires n <= |e|
    decreases n
  { if n == 0 then 0 else FoundCount(e,s,n-1) + (if AnySelected(e[n-1],s,|s|) then 1 else 0) }
  ghost function RelevantCount(e: seq<string>, s: seq<string>, n: nat): nat
    requires n <= |s|
    decreases n
  { if n == 0 then 0 else RelevantCount(e,s,n-1) + (if AnyExpected(s[n-1],e,|e|) then 1 else 0) }
  lemma CountBounds(e: seq<string>, s: seq<string>, a: nat, b: nat)
    requires a <= |e| && b <= |s|
    ensures FoundCount(e,s,a) <= a && RelevantCount(e,s,b) <= b
    decreases a+b
  { if a > 0 { CountBounds(e,s,a-1,b); } else if b > 0 { CountBounds(e,s,a,b-1); } }
  // Independent mathematical sets of positions whose IDs satisfy the relation.
  ghost function FoundIndices(e: seq<string>, s: seq<string>, n: nat): set<nat>
    requires n <= |e|
  { set i: nat | i < n && FoundSpec(e[i],s) }
  ghost function RelevantIndices(e: seq<string>, s: seq<string>, n: nat): set<nat>
    requires n <= |s|
  { set i: nat | i < n && RelevantSpec(s[i],e) }
  lemma CountsAreCardinalities(e: seq<string>, s: seq<string>, a: nat, b: nat)
    requires a <= |e| && b <= |s|
    ensures FoundCount(e,s,a) == |FoundIndices(e,s,a)|
    ensures RelevantCount(e,s,b) == |RelevantIndices(e,s,b)|
    decreases a+b
  {
    if a > 0 {
      CountsAreCardinalities(e,s,a-1,b);
      AnySelectedExact(e[a-1],s,|s|);
      assert FoundIndices(e,s,a) == FoundIndices(e,s,a-1) +
        (if FoundSpec(e[a-1],s) then {a-1} else {});
      assert a-1 !in FoundIndices(e,s,a-1);
    } else if b > 0 {
      CountsAreCardinalities(e,s,a,b-1);
      AnyExpectedExact(s[b-1],e,|e|);
      assert RelevantIndices(e,s,b) == RelevantIndices(e,s,b-1) +
        (if RelevantSpec(s[b-1],e) then {b-1} else {});
      assert b-1 !in RelevantIndices(e,s,b-1);
    }
  }
  // 0 pass, 1 timeout, 2 error, 3 missing, 4 weak scent, 5 forbidden.
  function Decision(timeout: bool, error: bool, missing: bool, scent: bool, forbidden: bool): int {
    if timeout then 1 else if error then 2 else if missing then 3 else if scent then 4 else if forbidden then 5 else 0
  }
  predicate DecisionSpec(t: bool, e: bool, m: bool, s: bool, f: bool, d: int) {
    (d == 1 <==> t) && (d == 2 <==> !t && e) &&
    (d == 3 <==> !t && !e && m) && (d == 4 <==> !t && !e && !m && s) &&
    (d == 5 <==> !t && !e && !m && !s && f) &&
    (d == 0 <==> !t && !e && !m && !s && !f)
  }
  function Latency(timeout: bool, wall: int, budget: int): int {
    if timeout then 2 else if wall <= budget then 0 else 1
  }
  lemma DecisionExact(t: bool,e: bool,m: bool,s: bool,f: bool,wall: int,budget: int)
    ensures DecisionSpec(t,e,m,s,f,Decision(t,e,m,s,f))
    ensures Latency(t,wall,budget) == 2 <==> t
    ensures !t ==> (Latency(t,wall,budget) == 0 <==> wall <= budget)
  {}
  lemma ExactAndBounded(e: seq<string>, s: seq<string>)
    ensures FoundCount(e,s,|e|) <= |e|
    ensures RelevantCount(e,s,|s|) <= |s|
    ensures forall i :: 0 <= i < |e| ==> (AnySelected(e[i],s,|s|) <==> FoundSpec(e[i],s))
    ensures forall i :: 0 <= i < |s| ==> (AnyExpected(s[i],e,|e|) <==> RelevantSpec(s[i],e))
  {
    CountBounds(e,s,|e|,|s|);
    forall i | 0 <= i < |e| { AnySelectedExact(e[i],s,|s|); }
    forall i | 0 <= i < |s| { AnyExpectedExact(s[i],e,|e|); }
  }
  ghost function Result(e: seq<string>, s: seq<string>, t: bool, err: bool, scent: bool, forbidden: bool, wall: int, budget: int): (nat,nat,int,int) {
    var found := FoundCount(e,s,|e|);
    var relevant := RelevantCount(e,s,|s|);
    (found,relevant,Decision(t,err,found < |e|,scent,forbidden),Latency(t,wall,budget))
  }
  lemma ResultContract(e: seq<string>, s: seq<string>, t: bool, err: bool, scent: bool, forbidden: bool, wall: int, budget: int)
    ensures Result(e,s,t,err,scent,forbidden,wall,budget).0 == |FoundIndices(e,s,|e|)|
    ensures Result(e,s,t,err,scent,forbidden,wall,budget).1 == |RelevantIndices(e,s,|s|)|
    ensures Result(e,s,t,err,scent,forbidden,wall,budget).0 <= |e|
    ensures Result(e,s,t,err,scent,forbidden,wall,budget).1 <= |s|
    ensures DecisionSpec(t,err,Result(e,s,t,err,scent,forbidden,wall,budget).0 < |e|,scent,forbidden,Result(e,s,t,err,scent,forbidden,wall,budget).2)
    ensures Result(e,s,t,err,scent,forbidden,wall,budget).3 == 2 <==> t
    ensures !t ==> (Result(e,s,t,err,scent,forbidden,wall,budget).3 == 0 <==> wall <= budget)
  { ExactAndBounded(e,s); CountsAreCardinalities(e,s,|e|,|s|); DecisionExact(t,err,FoundCount(e,s,|e|)<|e|,scent,forbidden,wall,budget); }
  lemma OverlapAndWildcardExamples()
    ensures Result(["x", "*"],["x"],false,false,false,false,0,1).1 == 1
    ensures Result(["skills:*"],["skills:a", "skills:b"],false,false,false,false,0,1).1 == 2
  {}
  // Iterative executable methods avoid recursion limits on long packets.
  method HasSelected(p: string, s: seq<string>) returns (hit: bool)
    ensures hit == AnySelected(p,s,|s|)
  {
    var i: nat := 0;
    hit := false;
    while i < |s|
      invariant i <= |s|
      invariant hit == AnySelected(p,s,i)
      decreases |s|-i
    { hit := hit || Match(p,s[i]); i := i + 1; }
  }
  method HasExpected(s: string, e: seq<string>) returns (hit: bool)
    ensures hit == AnyExpected(s,e,|e|)
  {
    var i: nat := 0;
    hit := false;
    while i < |e|
      invariant i <= |e|
      invariant hit == AnyExpected(s,e,i)
      decreases |e|-i
    { hit := hit || Match(e[i],s); i := i + 1; }
  }
  method Compute(e: seq<string>, s: seq<string>, t: bool, err: bool,
                 scent: bool, forbidden: bool, wall: int, budget: int)
      returns (flags: seq<bool>, found: nat, relevant: nat, decision: int, latency: int)
    ensures |flags| == |e|
    ensures forall i :: 0 <= i < |e| ==> (flags[i] <==> FoundSpec(e[i],s))
    ensures found == |FoundIndices(e,s,|e|)|
    ensures relevant == |RelevantIndices(e,s,|s|)|
    ensures found <= |e| && relevant <= |s|
    ensures DecisionSpec(t,err,found < |e|,scent,forbidden,decision)
    ensures latency == Latency(t,wall,budget)
    ensures latency == 2 <==> t
    ensures !t ==> (latency == 0 <==> wall <= budget)
  {
    flags := []; found := 0; relevant := 0;
    var i: nat := 0;
    while i < |e|
      invariant i <= |e| && |flags| == i
      invariant found == FoundCount(e,s,i)
      invariant forall j :: 0 <= j < i ==> (flags[j] <==> AnySelected(e[j],s,|s|))
      decreases |e|-i
    {
      var hit := HasSelected(e[i],s);
      flags := flags + [hit];
      if hit { found := found + 1; }
      i := i + 1;
    }
    var j: nat := 0;
    while j < |s|
      invariant j <= |s|
      invariant relevant == RelevantCount(e,s,j)
      decreases |s|-j
    {
      var hit := HasExpected(s[j],e);
      if hit { relevant := relevant + 1; }
      j := j + 1;
    }
    ExactAndBounded(e,s);
    CountsAreCardinalities(e,s,|e|,|s|);
    DecisionExact(t,err,found < |e|,scent,forbidden,wall,budget);
    relevant := found;
    decision := Decision(t,err,found < |e|,scent,forbidden);
    latency := Latency(t,wall,budget);
  }

}
