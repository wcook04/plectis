// Reverse reachability on a finite, normalized directed graph. Edges go from a
// dependency to its dependent. A start appears in the result only on a cycle.
module DependencyReachability {
  datatype Edge = Edge(src: int, dst: int)

  ghost function Vertices(es: seq<Edge>): set<int>
    decreases |es|
  {
    if |es| == 0 then {} else {es[0].src, es[0].dst} + Vertices(es[1..])
  }

  ghost predicate Walk(es: seq<Edge>, p: seq<int>) {
    |p| >= 2 && forall i :: 0 <= i < |p|-1 ==> Edge(p[i], p[i+1]) in es
  }

  ghost predicate Reach(es: seq<Edge>, s: int, v: int) {
    exists p: seq<int> :: Walk(es,p) && p[0] == s && p[|p|-1] == v
  }

  lemma VertexAt(es: seq<Edge>, i: nat)
    requires i < |es|
    ensures es[i].src in Vertices(es) && es[i].dst in Vertices(es)
    decreases i
  {
    if i > 0 { VertexAt(es[1..], i-1); }
  }

  method Expand(es: seq<Edge>, frontier: set<int>) returns (out: set<int>)
    ensures out <= Vertices(es)
    ensures forall v :: v in out <==> (exists u :: u in frontier && Edge(u,v) in es)
  {
    out := {};
    var i := 0;
    while i < |es|
      invariant 0 <= i <= |es|
      invariant out <= Vertices(es)
      invariant forall v :: v in out <==> (exists u :: u in frontier && Edge(u,v) in es[..i])
      decreases |es|-i
    {
      VertexAt(es,i);
      if es[i].src in frontier { out := out + {es[i].dst}; }
      i := i + 1;
    }
  }

  lemma PathExtension(es: seq<Edge>, s: int, u: int, v: int)
    requires Reach(es,s,u) && Edge(u,v) in es
    ensures Reach(es,s,v)
  {
    var p :| Walk(es,p) && p[0] == s && p[|p|-1] == u;
    var q := p + [v];
    assert Walk(es,q);
  }

  lemma ClosedWalk(es: seq<Edge>, p: seq<int>, reached: set<int>)
    requires Walk(es,p)
    requires forall v :: Edge(p[0],v) in es ==> v in reached
    requires forall u,v :: u in reached && Edge(u,v) in es ==> v in reached
    ensures p[|p|-1] in reached
    decreases |p|
  {
    if |p| == 2 {
      assert Edge(p[0],p[1]) in es;
    } else {
      var q := p[..|p|-1];
      assert Walk(es,q);
      ClosedWalk(es,q,reached);
      assert Edge(p[|p|-2],p[|p|-1]) in es;
    }
  }

  method Compute(es: seq<Edge>, s: int) returns (reached: set<int>)
    ensures forall v :: v in reached <==> Reach(es,s,v)
  {
    reached := Expand(es,{s});
    forall v | v in reached
      ensures Reach(es,s,v)
    {
      assert Edge(s,v) in es;
      assert Walk(es,[s,v]);
    }
    var added: set<int> := {};
    while true
      invariant reached <= Vertices(es)
      invariant forall v :: v in reached ==> Reach(es,s,v)
      invariant forall v :: Edge(s,v) in es ==> v in reached
      decreases Vertices(es) - reached
    {
      added := Expand(es,reached);
      if added <= reached { break; }
      forall v | v in added - reached
        ensures Reach(es,s,v)
      {
        var u :| u in reached && Edge(u,v) in es;
        PathExtension(es,s,u,v);
      }
      assert reached < reached + added;
      assert Vertices(es) - (reached + added) < Vertices(es) - reached;
      reached := reached + added;
    }
    assert forall u,v :: u in reached && Edge(u,v) in es ==> v in reached by {
      forall u,v | u in reached && Edge(u,v) in es
        ensures v in reached
      { assert v in added; }
    }
    forall v | Reach(es,s,v)
      ensures v in reached
    {
      var p :| Walk(es,p) && p[0] == s && p[|p|-1] == v;
      ClosedWalk(es,p,reached);
    }
  }
}
