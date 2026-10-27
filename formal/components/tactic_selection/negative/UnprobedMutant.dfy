// SPDX-License-Identifier: Apache-2.0
// IDs and membership observations are supplied by the Python caller.
module TacticSelection {
  datatype Candidate = Candidate(id: nat, known: bool, available: bool, allowed: bool)
  predicate Eligible(c: Candidate) { c.known && c.available && c.allowed }
  ghost predicate Match(cs: seq<Candidate>, id: nat) {
    exists j :: 0 <= j < |cs| && cs[j].id == id && Eligible(cs[j])
  }
  ghost predicate AnyPreference(ps: seq<nat>, cs: seq<Candidate>) {
    exists i :: 0 <= i < |ps| && Match(cs, ps[i])
  }
  method Select(ps: seq<nat>, cs: seq<Candidate>) returns (index: int, preference: int)
    ensures -1 <= index < |cs|
    ensures -1 <= preference < |ps|
    ensures index == -1 <==> (forall j :: 0 <= j < |cs| ==> !Eligible(cs[j]))
    ensures index >= 0 ==> Eligible(cs[index])
    ensures preference >= 0 <==> AnyPreference(ps, cs)
    ensures preference >= 0 ==> index >= 0 && cs[index].id == ps[preference]
    ensures preference >= 0 ==> (forall k :: 0 <= k < preference ==> !Match(cs, ps[k]))
    ensures preference >= 0 ==> (forall j :: 0 <= j < index ==> !(cs[j].id == ps[preference] && Eligible(cs[j])))
    ensures preference == -1 && index >= 0 ==> (forall j :: 0 <= j < index ==> !Eligible(cs[j]))
  {
    index := -1;
    preference := -1;
    var i := 0;
    while i < |ps|
      invariant 0 <= i <= |ps|
      invariant index == -1 && preference == -1
      invariant forall k :: 0 <= k < i ==> !Match(cs, ps[k])
      decreases |ps| - i
    {
      var j := 0;
      while j < |cs|
        invariant 0 <= j <= |cs|
        invariant index == -1 && preference == -1
        invariant forall k :: 0 <= k < i ==> !Match(cs, ps[k])
        invariant forall k :: 0 <= k < j ==> !(cs[k].id == ps[i] && Eligible(cs[k]))
        decreases |cs| - j
      {
        if cs[j].id == ps[i] && cs[j].available && cs[j].allowed {
          index := j;
          preference := i;
          return;
        }
        j := j + 1;
      }
      assert !Match(cs, ps[i]);
      i := i + 1;
    }
    var j := 0;
    while j < |cs|
      invariant 0 <= j <= |cs|
      invariant index == -1 && preference == -1
      invariant !AnyPreference(ps, cs)
      invariant forall k :: 0 <= k < j ==> !Eligible(cs[k])
      decreases |cs| - j
    {
      if Eligible(cs[j]) {
        index := j;
        return;
      }
      j := j + 1;
    }
  }
}
