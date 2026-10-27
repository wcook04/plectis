// SPDX-License-Identifier: Apache-2.0
// Admission is relative to observed, host-supplied replay evidence. The host,
// hashes, filesystem, runner, JSON decoder, and Dafny toolchain are trusted.
module ReplayAdmission {
  datatype Spec = Spec(component: int, inputRef: int, evidenceClass: int,
                       claim: int, nativeKind: int)
  datatype Observation = Observation(component: int, runnerComponent: int,
    receiptComponent: int, inputRef: int, evidenceClass: int, claim: int,
    sourceBefore: int, sourceAfter: int, inputBefore: int, inputAfter: int,
    runnerPayload: int, receiptPayload: int, receiptDigest: int,
    runnerStatus: int, receiptStatus: int, runnerVerdict: int,
    receiptVerdict: int, runnerNative: int, receiptNative: int,
    receiptPresent: bool)

  // The declarative meaning is deliberately independent of the executable
  // RowDecision below. Positive identity tokens denote supplied observations;
  // 1 is the exact decoded "pass" status/verdict, not a policy oracle.
  predicate RequiredRow(s: Spec, source: int, o: Observation) {
    source > 0 && s.component > 0 && s.inputRef > 0 &&
    s.evidenceClass > 0 && s.claim > 0 && 0 <= s.nativeKind <= 2 &&
    o.component == s.component && o.runnerComponent == s.component &&
    o.receiptComponent == s.component && o.inputRef == s.inputRef &&
    o.evidenceClass == s.evidenceClass && o.claim == s.claim &&
    o.sourceBefore == source && o.sourceAfter == source &&
    o.inputBefore > 0 && o.inputBefore == o.inputAfter &&
    o.runnerPayload > 0 && o.runnerPayload == o.receiptPayload &&
    o.receiptDigest > 0 && o.receiptPresent &&
    o.runnerStatus == 1 && o.receiptStatus == 1 &&
    o.runnerVerdict == 1 && o.receiptVerdict == 1 &&
    0 <= o.runnerNative <= 2 && o.runnerNative == o.receiptNative &&
    o.runnerNative == s.nativeKind
  }

  function RowDecision(s: Spec, source: int, o: Observation): bool {
    source > 0 && s.component > 0 && s.inputRef > 0 &&
    s.evidenceClass > 0 && s.claim > 0 && 0 <= s.nativeKind <= 2 &&
    o.component == s.component && o.runnerComponent == s.component &&
    o.receiptComponent == s.component && o.inputRef == s.inputRef &&
    o.evidenceClass == s.evidenceClass && o.claim == s.claim &&
    o.sourceBefore == source && o.sourceAfter == source &&
    o.inputBefore > 0 && o.inputBefore == o.inputAfter &&
    o.runnerPayload > 0 && o.runnerPayload == o.receiptPayload &&
    o.receiptDigest > 0 && o.receiptPresent &&
    o.runnerStatus == 1 && o.receiptStatus == 1 &&
    o.runnerVerdict == 1 && o.receiptVerdict == 1 &&
    0 <= o.runnerNative <= 2 && o.runnerNative == o.receiptNative &&
    o.runnerNative == s.nativeKind
  }

  function CountSpec(specs: seq<Spec>, id: int): nat
    decreases |specs|
  {
    if |specs| == 0 then 0
    else (if specs[0].component == id then 1 else 0) + CountSpec(specs[1..], id)
  }

  function CountRow(rows: seq<Observation>, id: int): nat
    decreases |rows|
  {
    if |rows| == 0 then 0
    else (if rows[0].component == id then 1 else 0) + CountRow(rows[1..], id)
  }

  function FindGood(rows: seq<Observation>, s: Spec, source: int): bool
    decreases |rows|
  {
    |rows| > 0 && (RowDecision(s, source, rows[0]) ||
                   FindGood(rows[1..], s, source))
  }

  function FindSpec(specs: seq<Spec>, o: Observation, source: int): bool
    decreases |specs|
  {
    |specs| > 0 && (RowDecision(specs[0], source, o) ||
                    FindSpec(specs[1..], o, source))
  }

  function CheckSpecs(pending: seq<Spec>, specs: seq<Spec>,
                      rows: seq<Observation>, source: int): bool
    decreases |pending|
  {
    |pending| == 0 ||
    (CountSpec(specs, pending[0].component) == 1 &&
     CountRow(rows, pending[0].component) == 1 &&
     FindGood(rows, pending[0], source) &&
     CheckSpecs(pending[1..], specs, rows, source))
  }

  function CheckRows(pending: seq<Observation>, specs: seq<Spec>,
                     source: int): bool
    decreases |pending|
  {
    |pending| == 0 ||
    (FindSpec(specs, pending[0], source) &&
     CheckRows(pending[1..], specs, source))
  }

  function Check(specs: seq<Spec>, source: int,
                 rows: seq<Observation>): bool {
    |specs| > 0 && |specs| == |rows| && source > 0 &&
    CheckSpecs(specs, specs, rows, source) && CheckRows(rows, specs, source)
  }

  predicate SpecsSatisfied(pending: seq<Spec>, specs: seq<Spec>,
                           rows: seq<Observation>, source: int) {
    (forall i | 0 <= i < |pending| ::
      CountSpec(specs, pending[i].component) == 1 &&
      CountRow(rows, pending[i].component) == 1 &&
      (exists j | 0 <= j < |rows| :: RequiredRow(pending[i], source, rows[j])))
  }

  predicate RowsSatisfied(pending: seq<Observation>, specs: seq<Spec>,
                          source: int) {
    (forall j | 0 <= j < |pending| ::
      (exists i | 0 <= i < |specs| :: RequiredRow(specs[i], source, pending[j])))
  }

  predicate Admission(specs: seq<Spec>, source: int,
                      rows: seq<Observation>) {
    |specs| > 0 && |specs| == |rows| && source > 0 &&
    SpecsSatisfied(specs, specs, rows, source) &&
    RowsSatisfied(rows, specs, source)
  }

  lemma FindGoodExact(rows: seq<Observation>, s: Spec, source: int)
    ensures FindGood(rows, s, source) ==
      (exists j | 0 <= j < |rows| :: RequiredRow(s, source, rows[j]))
    decreases |rows|
  {
    if |rows| > 0 {
      FindGoodExact(rows[1..], s, source);
      assert RowDecision(s, source, rows[0]) == RequiredRow(s, source, rows[0]);
    }
  }

  lemma FindSpecExact(specs: seq<Spec>, o: Observation, source: int)
    ensures FindSpec(specs, o, source) ==
      (exists i | 0 <= i < |specs| :: RequiredRow(specs[i], source, o))
    decreases |specs|
  {
    if |specs| > 0 {
      FindSpecExact(specs[1..], o, source);
      assert RowDecision(specs[0], source, o) == RequiredRow(specs[0], source, o);
    }
  }

  lemma CheckSpecsExact(pending: seq<Spec>, specs: seq<Spec>,
                        rows: seq<Observation>, source: int)
    ensures CheckSpecs(pending, specs, rows, source) ==
      SpecsSatisfied(pending, specs, rows, source)
    decreases |pending|
  {
    if |pending| > 0 {
      FindGoodExact(rows, pending[0], source);
      CheckSpecsExact(pending[1..], specs, rows, source);
    }
  }

  lemma CheckRowsExact(pending: seq<Observation>, specs: seq<Spec>, source: int)
    ensures CheckRows(pending, specs, source) ==
      RowsSatisfied(pending, specs, source)
    decreases |pending|
  {
    if |pending| > 0 {
      FindSpecExact(specs, pending[0], source);
      CheckRowsExact(pending[1..], specs, source);
    }
  }

  lemma AdmissionExact(specs: seq<Spec>, source: int,
                         rows: seq<Observation>)
    ensures Check(specs, source, rows) == Admission(specs, source, rows)
  {
    CheckSpecsExact(specs, specs, rows, source);
    CheckRowsExact(rows, specs, source);
  }

  function ExampleSpec(): Spec { Spec(1, 2, 3, 4, 0) }

  function ExampleRow(sourceAfter: int, inputAfter: int, claim: int,
                      receiptPayload: int, receiptDigest: int,
                      nativeKind: int): Observation {
    Observation(1, 1, 1, 2, 3, claim, 5, sourceAfter, 6, inputAfter,
                7, receiptPayload, receiptDigest, 1, 1, 1, 1,
                nativeKind, nativeKind, true)
  }

  function OtherRow(): Observation {
    Observation(9, 9, 9, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8,
                1, 1, 1, 1, 0, 0, true)
  }

  function WrongReceiptRow(): Observation {
    Observation(1, 1, 9, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8,
                1, 1, 1, 1, 0, 0, true)
  }

  function FailedStatusRow(): Observation {
    Observation(1, 1, 1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8,
                0, 1, 1, 1, 0, 0, true)
  }

  function AbsentReceiptRow(): Observation {
    Observation(1, 1, 1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8,
                1, 1, 1, 1, 0, 0, false)
  }

  // These controls keep the theorem anchored to an attainable passing row
  // and concrete failures. A bare pass without a receipt digest is rejected.
  lemma UsefulAndAdversarialCases()
    ensures Check([ExampleSpec()], 5, [ExampleRow(5, 6, 4, 7, 8, 0)])
    ensures !Check([], 5, [])
    ensures !Check([ExampleSpec()], 5, [])
    ensures !Check([ExampleSpec()], 5,
      [ExampleRow(5, 6, 4, 7, 8, 0), ExampleRow(5, 6, 4, 7, 8, 0)])
    ensures !Check([ExampleSpec(), ExampleSpec()], 5,
      [ExampleRow(5, 6, 4, 7, 8, 0), ExampleRow(5, 6, 4, 7, 8, 0)])
    ensures !Check([ExampleSpec()], 5, [ExampleRow(5, 6, 4, 7, 0, 0)])
    ensures !Check([ExampleSpec()], 5, [ExampleRow(9, 6, 4, 7, 8, 0)])
    ensures !Check([ExampleSpec()], 5, [ExampleRow(5, 9, 4, 7, 8, 0)])
    ensures !Check([ExampleSpec()], 5, [ExampleRow(5, 6, 9, 7, 8, 0)])
    ensures !Check([ExampleSpec()], 5, [ExampleRow(5, 6, 4, 9, 8, 0)])
    ensures !Check([ExampleSpec()], 5, [ExampleRow(5, 6, 4, 7, 8, 1)])
    ensures !Check([ExampleSpec()], 5, [OtherRow()])
    ensures !Check([ExampleSpec()], 5, [WrongReceiptRow()])
    ensures !Check([ExampleSpec()], 5, [FailedStatusRow()])
    ensures !Check([ExampleSpec()], 5, [AbsentReceiptRow()])
  {}
}
