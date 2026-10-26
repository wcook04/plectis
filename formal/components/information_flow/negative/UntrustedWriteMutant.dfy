// SPDX-License-Identifier: Apache-2.0
// These booleans are host observations. Label parsing, sanitization, and actual
// information flows are outside this decision theorem.
module InformationFlow {
  datatype Input = Input(hidden: bool, untrusted: bool, privileged: bool, sanitized: bool)

  // The independent policy relation partitions all inputs into four outcomes:
  // 0=block, 1=review, 2=warn, 3=allow.
  predicate Policy(i: Input, verdict: int) {
    (verdict == 0 <==> i.hidden || (i.untrusted && i.privileged && !i.sanitized)) &&
    (verdict == 1 <==> (!i.hidden && i.untrusted &&
      ((i.privileged && i.sanitized) || (!i.privileged && !i.sanitized)))) &&
    (verdict == 2 <==> !i.hidden && i.untrusted && !i.privileged && i.sanitized) &&
    (verdict == 3 <==> !i.hidden && !i.untrusted) &&
    0 <= verdict < 4
  }

  method Decide(i: Input) returns (verdict: int)
    ensures Policy(i, verdict)
    ensures i.hidden ==> verdict == 0
    ensures i.untrusted && i.privileged && !i.sanitized ==> verdict == 0
  {
    if i.hidden {
      verdict := 0;
    } else if i.untrusted && i.privileged && !i.sanitized {
      verdict := 1;
    } else if i.untrusted && i.privileged && i.sanitized {
      verdict := 1;
    } else if i.untrusted && i.sanitized {
      verdict := 2;
    } else if i.untrusted {
      verdict := 1;
    } else {
      verdict := 3;
    }
  }

  method DecideMany(inputs: seq<Input>) returns (verdicts: seq<int>)
    ensures |verdicts| == |inputs|
    ensures forall n :: 0 <= n < |inputs| ==> Policy(inputs[n], verdicts[n])
    ensures forall n :: 0 <= n < |inputs| && inputs[n].hidden ==> verdicts[n] == 0
    ensures forall n :: (0 <= n < |inputs| && inputs[n].untrusted &&
      inputs[n].privileged && !inputs[n].sanitized) ==> verdicts[n] == 0
  {
    verdicts := [];
    var n := 0;
    while n < |inputs|
      invariant 0 <= n <= |inputs|
      invariant |verdicts| == n
      invariant forall j :: 0 <= j < n ==> Policy(inputs[j], verdicts[j])
      invariant forall j :: 0 <= j < n && inputs[j].hidden ==> verdicts[j] == 0
      invariant forall j :: (0 <= j < n && inputs[j].untrusted &&
        inputs[j].privileged && !inputs[j].sanitized) ==> verdicts[j] == 0
      decreases |inputs| - n
    {
      var v := Decide(inputs[n]);
      verdicts := verdicts + [v];
      n := n + 1;
    }
  }

  // Finite episode-local graph. The host encodes each (episode, node) pair
  // as a distinct vertex. hidden is the observed instruction-channel or
  // promotion condition for this particular edge.
  datatype FlowEdge = FlowEdge(src: int, dst: int, hidden: bool)

  ghost predicate Link(es: seq<FlowEdge>, u: int, v: int) {
    exists h: bool :: FlowEdge(u, v, h) in es
  }

  ghost predicate SeedNode(es: seq<FlowEdge>, seeds: set<int>, hiddenLabel: bool, v: int) {
    v in seeds || (hiddenLabel && (exists u: int :: FlowEdge(u, v, true) in es))
  }

  ghost predicate Walk(es: seq<FlowEdge>, p: seq<int>) {
    |p| >= 1 && forall i :: 0 <= i < |p|-1 ==> Link(es, p[i], p[i+1])
  }

  ghost predicate Reaches(es: seq<FlowEdge>, seeds: set<int>, hiddenLabel: bool, v: int) {
    exists p: seq<int> :: Walk(es, p) && SeedNode(es, seeds, hiddenLabel, p[0]) && p[|p|-1] == v
  }

  function Vertices(es: seq<FlowEdge>): set<int>
    decreases |es|
  { if |es| == 0 then {} else {es[0].src, es[0].dst} + Vertices(es[1..]) }

  function HiddenDestinations(es: seq<FlowEdge>): set<int>
    decreases |es|
  { if |es| == 0 then {} else
      (if es[0].hidden then {es[0].dst} else {}) + HiddenDestinations(es[1..]) }

  lemma HiddenMembership(es: seq<FlowEdge>, v: int)
    ensures v in HiddenDestinations(es) <==> (exists u: int :: FlowEdge(u, v, true) in es)
    decreases |es|
  { if |es| > 0 { HiddenMembership(es[1..], v); } }

  function Expand(es: seq<FlowEdge>, reached: set<int>): set<int>
    decreases |es|
  { if |es| == 0 then {} else
      (if es[0].src in reached then {es[0].dst} else {}) + Expand(es[1..], reached) }

  lemma ExpandMembership(es: seq<FlowEdge>, reached: set<int>, v: int)
    ensures v in Expand(es, reached) <==> (exists u: int :: u in reached && Link(es, u, v))
    decreases |es|
  { if |es| > 0 { ExpandMembership(es[1..], reached, v); } }

  lemma ExpandBound(es: seq<FlowEdge>, reached: set<int>)
    ensures Expand(es, reached) <= Vertices(es)
    decreases |es|
  { if |es| > 0 { ExpandBound(es[1..], reached); } }

  lemma HiddenBound(es: seq<FlowEdge>)
    ensures HiddenDestinations(es) <= Vertices(es)
    decreases |es|
  { if |es| > 0 { HiddenBound(es[1..]); } }

  lemma Extend(es: seq<FlowEdge>, seeds: set<int>, hiddenLabel: bool, u: int, v: int)
    requires Reaches(es, seeds, hiddenLabel, u) && Link(es, u, v)
    ensures Reaches(es, seeds, hiddenLabel, v)
  {
    var p :| Walk(es,p) && SeedNode(es,seeds,hiddenLabel,p[0]) && p[|p|-1] == u;
    var q := p + [v];
    assert Walk(es,q);
  }

  lemma ClosedWalk(es: seq<FlowEdge>, p: seq<int>, reached: set<int>)
    requires Walk(es,p) && p[0] in reached
    requires forall u,v :: u in reached && Link(es,u,v) ==> v in reached
    ensures p[|p|-1] in reached
    decreases |p|
  {
    if |p| > 1 {
      var q := p[..|p|-1];
      assert Walk(es,q);
      ClosedWalk(es,q,reached);
      assert Link(es,p[|p|-2],p[|p|-1]);
    }
  }

  lemma SubsetCardinality(s: set<int>, t: set<int>)
    requires s <= t
    ensures |s| <= |t|
    decreases |t|
  {
    if t != {} {
      var x :| x in t;
      if x in s {
        SubsetCardinality(s - {x}, t - {x});
      } else {
        SubsetCardinality(s, t - {x});
      }
    }
  }

  lemma ProperSubsetCardinality(s: set<int>, t: set<int>)
    requires s < t
    ensures |s| < |t|
  {
    var x :| x in t && x !in s;
    SubsetCardinality(s, t - {x});
  }

  method Closure(es: seq<FlowEdge>, seeds: set<int>, hiddenLabel: bool) returns (reached: set<int>)
    ensures forall v :: v in reached <==> Reaches(es,seeds,hiddenLabel,v)
    ensures seeds <= reached
    ensures forall u,v :: u in reached && Link(es,u,v) ==> v in reached
  {
    reached := seeds + (if hiddenLabel then HiddenDestinations(es) else {});
    HiddenBound(es);
    forall v | v in reached
      ensures Reaches(es,seeds,hiddenLabel,v)
    {
      HiddenMembership(es,v);
      assert SeedNode(es,seeds,hiddenLabel,v);
      assert Walk(es,[v]);
    }
    forall v | SeedNode(es,seeds,hiddenLabel,v)
      ensures v in reached
    { HiddenMembership(es,v); }
    while true
      invariant seeds <= reached
      invariant reached <= seeds + Vertices(es)
      invariant forall v :: v in reached ==> Reaches(es,seeds,hiddenLabel,v)
      invariant forall v :: SeedNode(es,seeds,hiddenLabel,v) ==> v in reached
      decreases |(seeds + Vertices(es)) - reached|
    {
      var added := Expand(es,reached);
      ExpandBound(es,reached);
      if added <= reached { break; }
      forall v | v in added - reached
        ensures Reaches(es,seeds,hiddenLabel,v)
      {
        ExpandMembership(es,reached,v);
        var u :| u in reached && Link(es,u,v);
        Extend(es,seeds,hiddenLabel,u,v);
      }
      assert reached < reached + added;
      assert (seeds + Vertices(es)) - (reached + added) < (seeds + Vertices(es)) - reached;
      ProperSubsetCardinality((seeds + Vertices(es)) - (reached + added),
                              (seeds + Vertices(es)) - reached);
      reached := reached + added;
    }
    assert forall u,v :: u in reached && Link(es,u,v) ==> v in reached by {
      forall u,v | u in reached && Link(es,u,v)
        ensures v in reached
      { ExpandMembership(es,reached,v); }
    }
    forall v | Reaches(es,seeds,hiddenLabel,v)
      ensures v in reached
    {
      var p :| Walk(es,p) && SeedNode(es,seeds,hiddenLabel,p[0]) && p[|p|-1] == v;
      ClosedWalk(es,p,reached);
    }
  }

  lemma ReachMonotone(es: seq<FlowEdge>, smaller: set<int>, larger: set<int>, hiddenLabel: bool, v: int)
    requires smaller <= larger && Reaches(es,smaller,hiddenLabel,v)
    ensures Reaches(es,larger,hiddenLabel,v)
  {
    var p :| Walk(es,p) && SeedNode(es,smaller,hiddenLabel,p[0]) && p[|p|-1] == v;
    assert SeedNode(es,larger,hiddenLabel,p[0]);
  }

  lemma ReachWithinEpisode(es: seq<FlowEdge>, seeds: set<int>, hiddenLabel: bool, episode: set<int>, v: int)
    requires seeds <= episode
    requires forall e: FlowEdge :: e in es && e.src in episode ==> e.dst in episode
    requires !hiddenLabel || (forall e: FlowEdge :: e in es && e.hidden ==> e.dst in episode)
    requires Reaches(es,seeds,hiddenLabel,v)
    ensures v in episode
  {
    var p :| Walk(es,p) && SeedNode(es,seeds,hiddenLabel,p[0]) && p[|p|-1] == v;
    assert p[0] in episode;
    assert forall u,w :: u in episode && Link(es,u,w) ==> w in episode by {
      forall u,w | u in episode && Link(es,u,w)
        ensures w in episode
      {
        var h :| FlowEdge(u,w,h) in es;
        assert FlowEdge(u,w,h).src == u;
      }
    }
    ClosedWalk(es,p,episode);
  }
}
