// SPDX-License-Identifier: Apache-2.0
// The host supplies exact, injective integer identities for nonblank strings.
module WalkthroughValidation {
  datatype Step = Step(commands: seq<int>, inspect: seq<int>, evidence: seq<int>)

  // Exact rational minutes; no integer division or rounding at the boundary.
  predicate WithinTenMinutes(numerator: int, denominator: int) {
    0 < denominator && 0 < numerator && numerator <= 10 * denominator
  }

  ghost predicate ExactCommands(xs: seq<Step>, c: set<int>) {
    forall v: int :: v in c <==> (exists i: int :: 0 <= i < |xs| && v in xs[i].commands)
  }
  ghost predicate ExactEvidence(xs: seq<Step>, e: set<int>) {
    forall v: int :: v in e <==> (exists i: int :: 0 <= i < |xs| && v in xs[i].evidence)
  }
  // Independent relation: quantified memberships and requirements per step.
  ghost predicate Declared(xs: seq<Step>, budgetNumerator: int, budgetDenominator: int) {
    0 < budgetDenominator && 0 < budgetNumerator && budgetNumerator <= 10 * budgetDenominator && |xs| >= 5 &&
    (exists c: set<int>, e: set<int> :: ExactCommands(xs, c) && ExactEvidence(xs, e) && |c| >= 4 && |e| >= 4) &&
    (forall i: int :: 0 <= i < |xs| ==> (|xs[i].commands| > 0 &&
      |xs[i].inspect| > 0 && |xs[i].evidence| > 0))
  }

  method Evaluate(xs: seq<Step>, budgetNumerator: int, budgetDenominator: int)
      returns (accepted: bool, commandCount: nat, evidenceCount: nat)
    ensures accepted <==> Declared(xs, budgetNumerator, budgetDenominator)
    ensures accepted ==> 0 < budgetDenominator && 0 < budgetNumerator && budgetNumerator <= 10 * budgetDenominator
    ensures !WithinTenMinutes(budgetNumerator, budgetDenominator) ==> !accepted
    ensures exists c: set<int> :: ExactCommands(xs, c) && commandCount == |c|
    ensures exists e: set<int> :: ExactEvidence(xs, e) && evidenceCount == |e|
  {
    var commands: set<int> := {};
    var evidence: set<int> := {};
    var ready := true;
    var i: nat := 0;
    while i < |xs|
      invariant 0 <= i <= |xs|
      invariant forall v: int :: v in commands <==> (exists j: int :: 0 <= j < i && v in xs[j].commands)
      invariant forall v: int :: v in evidence <==> (exists j: int :: 0 <= j < i && v in xs[j].evidence)
      invariant ready <==> (forall j: int :: 0 <= j < i ==> (|xs[j].commands| > 0 &&
        |xs[j].inspect| > 0 && |xs[j].evidence| > 0))
      decreases |xs| - i
    {
      var step := xs[i];
      commands := commands + (set v | v in step.commands :: v);
      evidence := evidence + (set v | v in step.evidence :: v);
      ready := ready && |step.commands| > 0 && |step.inspect| > 0;
      i := i + 1;
    }
    commandCount := |commands|;
    evidenceCount := |evidence|;
    accepted := WithinTenMinutes(budgetNumerator, budgetDenominator) && |xs| >= 5 && commandCount >= 4 && evidenceCount >= 4 && ready;
    assert ExactCommands(xs, commands);
    assert ExactEvidence(xs, evidence);
    if accepted {
      assert Declared(xs, budgetNumerator, budgetDenominator);
    }
    if Declared(xs, budgetNumerator, budgetDenominator) {
      ghost var c: set<int>, e: set<int> :| ExactCommands(xs, c) && ExactEvidence(xs, e) && |c| >= 4 && |e| >= 4;
      forall v: int
        ensures v in c <==> v in commands
      {
        assert (v in c) <==> (exists j: int :: 0 <= j < |xs| && v in xs[j].commands);
        assert (v in commands) <==> (exists j: int :: 0 <= j < |xs| && v in xs[j].commands);
      }
      forall v: int
        ensures v in e <==> v in evidence
      {
        assert (v in e) <==> (exists j: int :: 0 <= j < |xs| && v in xs[j].evidence);
        assert (v in evidence) <==> (exists j: int :: 0 <= j < |xs| && v in xs[j].evidence);
      }
      assert c == commands;
      assert e == evidence;
      assert accepted;
    }
  }

  lemma OverBudgetCannotBeDeclared(xs: seq<Step>, numerator: int, denominator: int)
    requires 0 < denominator && 10 * denominator < numerator
    ensures !Declared(xs, numerator, denominator)
  {}
}
