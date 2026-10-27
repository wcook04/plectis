// SPDX-License-Identifier: Apache-2.0
// The host supplies normalized strings, exact flag tests and key observations.
module McpAuthority {
  datatype Call = Call(declared: bool, scope: string, broad: bool,
    credential: bool, forbiddenKey: bool, untrustedInstruction: bool,
    live: bool, finalOnly: bool, effect: string, approval: string,
    ledger: string, rollback: string, bodySafe: bool, privateSafe: bool,
    fieldsPresent: bool, toolClass: string, argumentHash: string,
    sourceCapsule: string, instructionSplit: string, coldReplay: string)

  predicate CompleteCitations(c: Call) {
    c.scope != "" && c.argumentHash != "" && c.sourceCapsule != "" &&
    c.instructionSplit != "" && c.coldReplay != ""
  }

  predicate Allowed(c: Call) {
    c.declared && !c.broad && c.scope != "*" && c.scope != "all_tools" &&
    c.scope != "workspace_admin" && c.scope != "account_full_access" &&
    !c.credential && !c.forbiddenKey && !c.untrustedInstruction &&
    !c.live && !c.finalOnly && c.bodySafe && c.privateSafe && c.fieldsPresent &&
    CompleteCitations(c) &&
    ((c.effect != "write" && c.effect != "external_mutation") ||
      (c.approval != "" && c.approval != "not_required" &&
       c.approval != "missing" && c.ledger != "" && c.rollback != ""))
  }
  predicate QualifyingWrite(c: Call) {
    c.effect == "write" && c.approval != "" && c.approval != "not_required" &&
    c.approval != "missing" && c.ledger != "" && c.rollback != ""
  }

  // Each numbered diagnostic has an independent declarative meaning.
  predicate FaultSpec(c: Call, i: int) {
    if i == 0 then !c.declared
    else if i == 1 then c.broad || c.scope == "*" || c.scope == "all_tools" ||
      c.scope == "workspace_admin" || c.scope == "account_full_access"
    else if i == 2 then c.credential || c.forbiddenKey
    else if i == 3 then c.untrustedInstruction
    else if i == 4 then c.live
    else if i == 5 then c.finalOnly
    else if i == 6 then (c.effect == "write" || c.effect == "external_mutation") &&
      (c.approval == "" || c.approval == "not_required" || c.approval == "missing" || c.ledger == "")
    else if i == 7 then (c.effect == "write" || c.effect == "external_mutation") && c.rollback == ""
    else if i == 8 then !c.bodySafe || !c.privateSafe
    else if i == 9 then !c.fieldsPresent || !CompleteCitations(c)
    else false
  }

  // Fault positions preserve the Python host's existing diagnostic order.
  function Faults(c: Call): seq<bool> {
    [!c.declared,
     c.broad || c.scope == "*" || c.scope == "all_tools" ||
       c.scope == "workspace_admin" || c.scope == "account_full_access",
     c.credential || c.forbiddenKey,
     c.untrustedInstruction, c.live, c.finalOnly,
     (c.effect == "write" || c.effect == "external_mutation") &&
       (c.approval == "" || c.approval == "not_required" || c.approval == "missing" || c.ledger == ""),
     (c.effect == "write" || c.effect == "external_mutation") && c.rollback == "",
     !c.bodySafe || !c.privateSafe,
     !c.fieldsPresent || c.argumentHash == "" || // MUTANT: an empty scope is admitted
       c.sourceCapsule == "" || c.instructionSplit == "" || c.coldReplay == ""]
  }
  function Accepted(c: Call): bool { Faults(c) == [false,false,false,false,false,false,false,false,false,false] }
  function CountWrites(rows: seq<Call>): nat
    decreases |rows|
  { if |rows| == 0 then 0 else (if QualifyingWrite(rows[0]) then 1 else 0) + CountWrites(rows[1..]) }
  function CountUntrusted(rows: seq<Call>): nat
    decreases |rows|
  { if |rows| == 0 then 0 else (if rows[0].toolClass == "untrusted_result" then 1 else 0) + CountUntrusted(rows[1..]) }
  function AllAccepted(rows: seq<Call>): bool
    decreases |rows|
  { |rows| == 0 || (Accepted(rows[0]) && AllAccepted(rows[1..])) }
  function Check(rows: seq<Call>): bool {
    |rows| == 3 && CountWrites(rows) == 1 && CountUntrusted(rows) == 1 && AllAccepted(rows)
  }

  // Iteration avoids a Python call-stack limit for long input sequences.
  method Batch(rows: seq<Call>) returns (writes: nat, untrusted: nat, accepted: bool)
    ensures writes == CountWrites(rows)
    ensures untrusted == CountUntrusted(rows)
    ensures accepted == Check(rows)
    ensures accepted ==> (forall i: int | 0 <= i < |rows| ::
      rows[i].fieldsPresent && CompleteCitations(rows[i]))
  {
    var i: nat := 0;
    writes := 0;
    untrusted := 0;
    var ok := true;
    while i < |rows|
      invariant i <= |rows|
      invariant writes + CountWrites(rows[i..]) == CountWrites(rows)
      invariant untrusted + CountUntrusted(rows[i..]) == CountUntrusted(rows)
      invariant (ok && AllAccepted(rows[i..])) == AllAccepted(rows)
      decreases |rows| - i
    {
      assert rows[i..][0] == rows[i];
      assert rows[i..][1..] == rows[i+1..];
      if QualifyingWrite(rows[i]) { writes := writes + 1; }
      if rows[i].toolClass == "untrusted_result" { untrusted := untrusted + 1; }
      ok := ok && Accepted(rows[i]);
      i := i + 1;
    }
    accepted := |rows| == 3 && writes == 1 && untrusted == 1 && ok;
    BatchExact(rows);
  }

  lemma RowExact(c: Call)
    ensures |Faults(c)| == 10
    ensures forall i: int | 0 <= i < 10 :: Faults(c)[i] <==> FaultSpec(c, i)
    ensures Accepted(c) <==> Allowed(c)
    ensures Accepted(c) ==> c.fieldsPresent && CompleteCitations(c)
    ensures Allowed(c) && (c.effect == "write" || c.effect == "external_mutation") ==>
      c.approval != "" && c.approval != "not_required" && c.approval != "missing" && c.ledger != "" && c.rollback != ""
  { }

  predicate ExactlyOneWrite(rows: seq<Call>) {
    |rows| == 3 &&
      ((QualifyingWrite(rows[0]) && !QualifyingWrite(rows[1]) && !QualifyingWrite(rows[2])) ||
       (!QualifyingWrite(rows[0]) && QualifyingWrite(rows[1]) && !QualifyingWrite(rows[2])) ||
       (!QualifyingWrite(rows[0]) && !QualifyingWrite(rows[1]) && QualifyingWrite(rows[2])))
  }
  predicate ExactlyOneUntrusted(rows: seq<Call>) {
    |rows| == 3 &&
      ((rows[0].toolClass == "untrusted_result" && rows[1].toolClass != "untrusted_result" && rows[2].toolClass != "untrusted_result") ||
       (rows[0].toolClass != "untrusted_result" && rows[1].toolClass == "untrusted_result" && rows[2].toolClass != "untrusted_result") ||
       (rows[0].toolClass != "untrusted_result" && rows[1].toolClass != "untrusted_result" && rows[2].toolClass == "untrusted_result"))
  }
  predicate BatchSpec(rows: seq<Call>) {
    |rows| == 3 && ExactlyOneWrite(rows) && ExactlyOneUntrusted(rows) &&
      (forall i: int | 0 <= i < |rows| :: Allowed(rows[i]))
  }
  lemma UntrustedStep(rows: seq<Call>)
    requires |rows| > 0
    ensures CountUntrusted(rows) ==
      (if rows[0].toolClass == "untrusted_result" then 1 else 0) + CountUntrusted(rows[1..])
  { }
  lemma {:fuel 5} BatchExact(rows: seq<Call>)
    ensures Check(rows) <==> BatchSpec(rows)
    ensures Check(rows) ==> (forall i: int | 0 <= i < |rows| ::
      rows[i].fieldsPresent && CompleteCitations(rows[i]))
  {
    if |rows| == 3 {
      RowExact(rows[0]); RowExact(rows[1]); RowExact(rows[2]);
      assert rows == [rows[0], rows[1], rows[2]];
      assert rows[1..] == [rows[1], rows[2]];
      assert rows[2..] == [rows[2]];
      assert rows[3..] == [];
      assert CountWrites(rows) == (if QualifyingWrite(rows[0]) then 1 else 0) + CountWrites(rows[1..]);
      assert CountWrites(rows[1..]) == (if QualifyingWrite(rows[1]) then 1 else 0) + CountWrites(rows[2..]);
      assert CountWrites(rows[2..]) == (if QualifyingWrite(rows[2]) then 1 else 0) + CountWrites(rows[3..]);
      assert CountWrites(rows[3..]) == 0;
      UntrustedStep(rows); UntrustedStep(rows[1..]); UntrustedStep(rows[2..]);
      assert CountUntrusted(rows) == (if rows[0].toolClass == "untrusted_result" then 1 else 0) + CountUntrusted(rows[1..]);
      assert CountUntrusted(rows[1..]) == (if rows[1].toolClass == "untrusted_result" then 1 else 0) + CountUntrusted(rows[2..]);
      assert CountUntrusted(rows[2..]) == (if rows[2].toolClass == "untrusted_result" then 1 else 0) + CountUntrusted(rows[3..]);
      assert CountUntrusted(rows[3..]) == 0;
      assert AllAccepted(rows) == (Accepted(rows[0]) && AllAccepted(rows[1..]));
      assert AllAccepted(rows[1..]) == (Accepted(rows[1]) && AllAccepted(rows[2..]));
      assert AllAccepted(rows[2..]) == (Accepted(rows[2]) && AllAccepted(rows[3..]));
      assert AllAccepted(rows[3..]);
      assert CountWrites(rows) ==
        (if QualifyingWrite(rows[0]) then 1 else 0) +
        (if QualifyingWrite(rows[1]) then 1 else 0) +
        (if QualifyingWrite(rows[2]) then 1 else 0);
      assert CountUntrusted(rows) ==
        (if rows[0].toolClass == "untrusted_result" then 1 else 0) +
        (if rows[1].toolClass == "untrusted_result" then 1 else 0) +
        (if rows[2].toolClass == "untrusted_result" then 1 else 0);
      assert (CountWrites(rows) == 1) <==> ExactlyOneWrite(rows);
      assert (CountUntrusted(rows) == 1) <==> ExactlyOneUntrusted(rows);
      assert AllAccepted(rows) <==> (Allowed(rows[0]) && Allowed(rows[1]) && Allowed(rows[2]));
      assert (forall i: int | 0 <= i < |rows| :: Allowed(rows[i])) <==>
        (Allowed(rows[0]) && Allowed(rows[1]) && Allowed(rows[2]));
    }
  }

  function Example(scope: string, effect: string, toolClass: string, rollback: string): Call {
    Call(true, scope, false, false, false, false, false, false,
      effect, "approval", "ledger", rollback, true, true, true, toolClass,
      "hash", "source", "split", "cold")
  }
  lemma ConcreteBoundary()
    ensures Check([Example("scope/write", "write", "write_side_effect", "rollback"),
                   Example("scope/read", "none", "readonly_lookup", ""),
                   Example("scope/untrusted", "none", "untrusted_result", "")])
    ensures !Accepted(Example("scope/write", "write", "write_side_effect", ""))
    ensures Faults(Example("scope/write", "write", "write_side_effect", ""))[7]
    ensures !Accepted(Example("", "write", "write_side_effect", "rollback"))
    ensures Faults(Example("", "write", "write_side_effect", "rollback"))[9]
  { }
}
