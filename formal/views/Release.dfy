// Original executable release calculus, 23 October 2026.
// The proof concerns this total finite AST and its public string trace.
// No callbacks, arbitrary code, declassification, clocks or external I/O.
module Release {
  datatype Ty = TextTy | FlagTy
  datatype Value = Text(text: string) | Flag(flag: bool)
  datatype Event = Emission(isPublic: bool, text: string)
  datatype Expr = Literal(value: Value) | Input(slot: int)
                | Concat(left: Expr, right: Expr)
                | Equals(left: Expr, right: Expr)
  datatype Cmd = Skip | Emit(public: bool, value: Expr)
               | Then(first: Cmd, second: Cmd)
               | Branch(condition: Expr, yes: Cmd, no: Cmd)

  function ValueType(v: Value): Ty {
    if v.Text? then TextTy else FlagTy
  }

  // Total defensive type projection. WellTypedExpr rules out invalid Input.
  function ExprType(e: Expr, types: seq<Ty>): Ty {
    match e
    case Literal(v) => ValueType(v)
    case Input(i) => if 0 <= i < |types| then types[i] else TextTy
    case Concat(a, b) => TextTy
    case Equals(a, b) => FlagTy
  }

  predicate WellTypedExpr(e: Expr, types: seq<Ty>) {
    match e
    case Literal(v) => true
    case Input(i) => 0 <= i < |types|
    case Concat(a, b) => WellTypedExpr(a, types) && WellTypedExpr(b, types) &&
                         ExprType(a, types) == TextTy && ExprType(b, types) == TextTy
    case Equals(a, b) => WellTypedExpr(a, types) && WellTypedExpr(b, types) &&
                         ExprType(a, types) == ExprType(b, types)
  }

  function Sensitive(e: Expr, high: seq<bool>): bool {
    match e
    case Literal(v) => false
    case Input(i) => !(0 <= i < |high|) || high[i]
    case Concat(a, b) => Sensitive(a, high) || Sensitive(b, high)
    case Equals(a, b) => Sensitive(a, high) || Sensitive(b, high)
  }

  predicate ValidEnvironment(types: seq<Ty>, values: seq<Value>) {
    |types| == |values| &&
    forall i :: 0 <= i < |types| ==> ValueType(values[i]) == types[i]
  }

  predicate LowEquivalent(high: seq<bool>, left: seq<Value>, right: seq<Value>) {
    |left| == |high| && |right| == |high| &&
    forall i :: 0 <= i < |high| && !high[i] ==> left[i] == right[i]
  }

  // Eval is total even for rejected ASTs; accepted ASTs never use the defaults.
  function Eval(e: Expr, values: seq<Value>): Value {
    match e
    case Literal(v) => v
    case Input(i) => if 0 <= i < |values| then values[i] else Text("")
    case Concat(a, b) =>
      var av := Eval(a, values);
      var bv := Eval(b, values);
      if av.Text? && bv.Text? then Text(av.text + bv.text) else Text("")
    case Equals(a, b) => Flag(Eval(a, values) == Eval(b, values))
  }

  // pc records whether reaching this statement may depend on private data.
  predicate Checked(c: Cmd, types: seq<Ty>, high: seq<bool>, pc: bool) {
    |types| == |high| &&
    match c
    case Skip => true
    case Emit(isPublic, e) =>
      WellTypedExpr(e, types) && ExprType(e, types) == TextTy &&
      (!isPublic || (!pc && !Sensitive(e, high)))
    case Then(a, b) => Checked(a, types, high, pc) && Checked(b, types, high, pc)
    case Branch(e, a, b) =>
      WellTypedExpr(e, types) && ExprType(e, types) == FlagTy &&
      Checked(a, types, high, pc || Sensitive(e, high)) &&
      Checked(b, types, high, pc || Sensitive(e, high))
  }

  // The complete public observation: ordered strings, including occurrence/count.
  // Internal Emit is an interpreter operation whose public observation is empty.
  function Run(c: Cmd, values: seq<Value>): seq<string> {
    match c
    case Skip => []
    case Emit(isPublic, e) =>
      var v := Eval(e, values);
      if isPublic && v.Text? then [v.text] else []
    case Then(a, b) => Run(a, values) + Run(b, values)
    case Branch(e, a, b) =>
      var v := Eval(e, values);
      if v.Flag? && v.flag then Run(a, values) else Run(b, values)
  }

  // Reference execution for an authorised internal caller. Public API uses
  // CheckAndRun and never exposes these mixed events.
  function RunAll(c: Cmd, values: seq<Value>): seq<Event> {
    match c
    case Skip => []
    case Emit(isPublic, e) =>
      var v := Eval(e, values);
      if v.Text? then [Emission(isPublic, v.text)] else []
    case Then(a, b) => RunAll(a, values) + RunAll(b, values)
    case Branch(e, a, b) =>
      var v := Eval(e, values);
      if v.Flag? && v.flag then RunAll(a, values) else RunAll(b, values)
  }

  function PublicProjection(events: seq<Event>): seq<string>
    decreases |events|
  {
    if |events| == 0 then [] else
      (if events[0].isPublic then [events[0].text] else []) + PublicProjection(events[1..])
  }

  lemma ProjectionConcat(left: seq<Event>, right: seq<Event>)
    ensures PublicProjection(left + right) == PublicProjection(left) + PublicProjection(right)
    decreases |left|
  {
    if |left| > 0 {
      ProjectionConcat(left[1..], right);
      assert (left + right)[1..] == left[1..] + right;
      assert (left + right)[0] == left[0];
      var head := if left[0].isPublic then [left[0].text] else [];
      calc {
        PublicProjection(left + right);
        == head + PublicProjection(left[1..] + right);
        == head + (PublicProjection(left[1..]) + PublicProjection(right));
        == (head + PublicProjection(left[1..])) + PublicProjection(right);
        == PublicProjection(left) + PublicProjection(right);
      }
    } else {
      assert left == [];
      assert left + right == right;
      assert PublicProjection(left) == [];
    }
  }

  lemma FullExecutionPublicProjection(c: Cmd, values: seq<Value>)
    ensures PublicProjection(RunAll(c, values)) == Run(c, values)
  {
    match c
    case Skip =>
    case Emit(isPublic, e) =>
    case Then(a, b) =>
      FullExecutionPublicProjection(a, values);
      FullExecutionPublicProjection(b, values);
      ProjectionConcat(RunAll(a, values), RunAll(b, values));
    case Branch(e, a, b) =>
      FullExecutionPublicProjection(a, values);
      FullExecutionPublicProjection(b, values);
  }

  lemma EvalHasType(e: Expr, types: seq<Ty>, values: seq<Value>)
    requires WellTypedExpr(e, types)
    requires ValidEnvironment(types, values)
    ensures ValueType(Eval(e, values)) == ExprType(e, types)
  {
    match e
    case Literal(v) =>
    case Input(i) =>
    case Concat(a, b) =>
      EvalHasType(a, types, values);
      EvalHasType(b, types, values);
    case Equals(a, b) =>
  }

  lemma LowExprEqual(e: Expr, high: seq<bool>, left: seq<Value>, right: seq<Value>)
    requires LowEquivalent(high, left, right)
    requires !Sensitive(e, high)
    ensures Eval(e, left) == Eval(e, right)
  {
    match e
    case Literal(v) =>
    case Input(i) =>
    case Concat(a, b) =>
      LowExprEqual(a, high, left, right);
      LowExprEqual(b, high, left, right);
    case Equals(a, b) =>
      LowExprEqual(a, high, left, right);
      LowExprEqual(b, high, left, right);
  }

  lemma HighContextHasNoPublicTrace(c: Cmd, types: seq<Ty>, high: seq<bool>, values: seq<Value>)
    requires Checked(c, types, high, true)
    ensures Run(c, values) == []
  {
    match c
    case Skip =>
    case Emit(isPublic, e) =>
    case Then(a, b) =>
      HighContextHasNoPublicTrace(a, types, high, values);
      HighContextHasNoPublicTrace(b, types, high, values);
    case Branch(e, a, b) =>
      HighContextHasNoPublicTrace(a, types, high, values);
      HighContextHasNoPublicTrace(b, types, high, values);
  }

  lemma CheckedNoninterference(c: Cmd, types: seq<Ty>, high: seq<bool>, left: seq<Value>, right: seq<Value>)
    requires Checked(c, types, high, false)
    requires LowEquivalent(high, left, right)
    ensures Run(c, left) == Run(c, right)
  {
    match c
    case Skip =>
    case Emit(isPublic, e) =>
      if isPublic { LowExprEqual(e, high, left, right); }
    case Then(a, b) =>
      CheckedNoninterference(a, types, high, left, right);
      CheckedNoninterference(b, types, high, left, right);
    case Branch(e, a, b) =>
      if Sensitive(e, high) {
        HighContextHasNoPublicTrace(a, types, high, left);
        HighContextHasNoPublicTrace(b, types, high, left);
        HighContextHasNoPublicTrace(a, types, high, right);
        HighContextHasNoPublicTrace(b, types, high, right);
      } else {
        LowExprEqual(e, high, left, right);
        CheckedNoninterference(a, types, high, left, right);
        CheckedNoninterference(b, types, high, left, right);
      }
  }

  function PublicSlice(c: Cmd, high: seq<bool>): Cmd {
    match c
    case Skip => Skip
    case Emit(isPublic, e) => if isPublic then Emit(true, e) else Skip
    case Then(a, b) => Then(PublicSlice(a, high), PublicSlice(b, high))
    case Branch(e, a, b) =>
      if Sensitive(e, high) then Skip
      else Branch(e, PublicSlice(a, high), PublicSlice(b, high))
  }

  predicate PublicOnly(c: Cmd, high: seq<bool>) {
    match c
    case Skip => true
    case Emit(isPublic, e) => isPublic && !Sensitive(e, high)
    case Then(a, b) => PublicOnly(a, high) && PublicOnly(b, high)
    case Branch(e, a, b) => !Sensitive(e, high) && PublicOnly(a, high) && PublicOnly(b, high)
  }

  function ExprReads(e: Expr): set<int> {
    match e
    case Literal(v) => {}
    case Input(i) => {i}
    case Concat(a, b) => ExprReads(a) + ExprReads(b)
    case Equals(a, b) => ExprReads(a) + ExprReads(b)
  }

  function CmdReads(c: Cmd): set<int> {
    match c
    case Skip => {}
    case Emit(isPublic, e) => ExprReads(e)
    case Then(a, b) => CmdReads(a) + CmdReads(b)
    case Branch(e, a, b) => ExprReads(e) + CmdReads(a) + CmdReads(b)
  }

  lemma NonSensitiveReadsAreLow(e: Expr, high: seq<bool>)
    requires !Sensitive(e, high)
    ensures forall i :: i in ExprReads(e) ==> 0 <= i < |high| && !high[i]
  {
    match e
    case Literal(v) =>
    case Input(i) =>
    case Concat(a, b) =>
      NonSensitiveReadsAreLow(a, high);
      NonSensitiveReadsAreLow(b, high);
    case Equals(a, b) =>
      NonSensitiveReadsAreLow(a, high);
      NonSensitiveReadsAreLow(b, high);
  }

  lemma PublicOnlyReadsAreLow(c: Cmd, high: seq<bool>)
    requires PublicOnly(c, high)
    ensures forall i :: i in CmdReads(c) ==> 0 <= i < |high| && !high[i]
  {
    match c
    case Skip =>
    case Emit(isPublic, e) =>
      NonSensitiveReadsAreLow(e, high);
    case Then(a, b) =>
      PublicOnlyReadsAreLow(a, high);
      PublicOnlyReadsAreLow(b, high);
    case Branch(e, a, b) =>
      NonSensitiveReadsAreLow(e, high);
      PublicOnlyReadsAreLow(a, high);
      PublicOnlyReadsAreLow(b, high);
  }

  lemma SliceIsPublicOnly(c: Cmd, types: seq<Ty>, high: seq<bool>)
    requires Checked(c, types, high, false)
    ensures PublicOnly(PublicSlice(c, high), high)
  {
    match c
    case Skip =>
    case Emit(isPublic, e) =>
    case Then(a, b) =>
      SliceIsPublicOnly(a, types, high);
      SliceIsPublicOnly(b, types, high);
    case Branch(e, a, b) =>
      if !Sensitive(e, high) {
        SliceIsPublicOnly(a, types, high);
        SliceIsPublicOnly(b, types, high);
      }
  }

  lemma SlicePreservesTrace(c: Cmd, types: seq<Ty>, high: seq<bool>, values: seq<Value>)
    requires Checked(c, types, high, false)
    ensures Run(PublicSlice(c, high), values) == Run(c, values)
  {
    match c
    case Skip =>
    case Emit(isPublic, e) =>
    case Then(a, b) =>
      SlicePreservesTrace(a, types, high, values);
      SlicePreservesTrace(b, types, high, values);
    case Branch(e, a, b) =>
      if Sensitive(e, high) {
        HighContextHasNoPublicTrace(a, types, high, values);
        HighContextHasNoPublicTrace(b, types, high, values);
      } else {
        SlicePreservesTrace(a, types, high, values);
        SlicePreservesTrace(b, types, high, values);
      }
  }

  lemma SliceStaysChecked(c: Cmd, types: seq<Ty>, high: seq<bool>)
    requires Checked(c, types, high, false)
    ensures Checked(PublicSlice(c, high), types, high, false)
  {
    match c
    case Skip =>
    case Emit(isPublic, e) =>
    case Then(a, b) =>
      SliceStaysChecked(a, types, high);
      SliceStaysChecked(b, types, high);
    case Branch(e, a, b) =>
      if !Sensitive(e, high) {
        SliceStaysChecked(a, types, high);
        SliceStaysChecked(b, types, high);
      }
  }

  // Adopters pass placeholders for unavailable private inputs. Their actual
  // values never need to be loaded by the public runner.
  method CheckAndRun(types: seq<Ty>, high: seq<bool>, values: seq<Value>, program: Cmd)
      returns (accepted: bool, trace: seq<string>)
    ensures accepted == (Checked(program, types, high, false) && ValidEnvironment(types, values))
    ensures accepted ==> trace == Run(program, values)
    ensures !accepted ==> trace == []
  {
    accepted := Checked(program, types, high, false) && ValidEnvironment(types, values);
    trace := [];
    if accepted {
      SlicePreservesTrace(program, types, high, values);
      trace := Run(PublicSlice(program, high), values);
    }
  }

  method CheckAndSlice(types: seq<Ty>, high: seq<bool>, program: Cmd)
      returns (accepted: bool, sliced: Cmd)
    ensures accepted == Checked(program, types, high, false)
    ensures accepted ==> sliced == PublicSlice(program, high)
    ensures accepted ==> PublicOnly(sliced, high)
    ensures accepted ==> (forall i :: i in CmdReads(sliced) ==> 0 <= i < |high| && !high[i])
    ensures accepted ==> Checked(sliced, types, high, false)
    ensures !accepted ==> sliced == Skip
  {
    accepted := Checked(program, types, high, false);
    sliced := Skip;
    if accepted {
      SliceIsPublicOnly(program, types, high);
      SliceStaysChecked(program, types, high);
      sliced := PublicSlice(program, high);
      PublicOnlyReadsAreLow(sliced, high);
    }
  }
}
