// SPDX-License-Identifier: Apache-2.0
// The host supplies normalized Unicode code points and the phrase-edge flags.
// Its Python str/lower/isalnum operations and semantic policy are not proved.
module EgressPolicy {
  predicate AsciiWord(c: int) {
    (48 <= c <= 57) || (97 <= c <= 122)
  }

  predicate Occurrence(t: seq<int>, p: seq<int>, left: bool, right: bool, i: int) {
    0 <= i && i + |p| <= |t| && t[i..i + |p|] == p &&
    (!left || i == 0 || !AsciiWord(t[i-1])) &&
    (!right || i + |p| == |t| || !AsciiWord(t[i + |p|]))
  }

  ghost predicate HasOccurrence(t: seq<int>, p: seq<int>, left: bool, right: bool) {
    exists i: int :: Occurrence(t, p, left, right, i)
  }

  // Exhaustively scan every possible start, including the empty phrase at the end.
  method Find(t: seq<int>, p: seq<int>, left: bool, right: bool) returns (found: bool)
    ensures found <==> HasOccurrence(t, p, left, right)
  {
    var i: int := 0;
    while i + |p| <= |t|
      invariant 0 <= i <= |t| + 1
      invariant forall j: int | 0 <= j < i && j + |p| <= |t| :: !Occurrence(t,p,left,right,j)
      decreases |t| + 1 - i
    {
      if t[i..i + |p|] == p &&
         (!left || i == 0 || !AsciiWord(t[i-1])) &&
         (!right || i + |p| == |t| || !AsciiWord(t[i + |p|])) {
        assert Occurrence(t, p, left, right, i);
        assert HasOccurrence(t, p, left, right) by {
          assert exists j: int :: Occurrence(t, p, left, right, j);
        }
        return true;
      }
      assert !Occurrence(t,p,left,right,i);
      i := i + 1;
    }
    return false;
  }

  // Every adjacent pair consists of tripwire-match and legitimizer-match.
  function Violations(flags: seq<bool>): seq<bool>
    requires |flags| % 2 == 0
    decreases |flags|
  {
    if |flags| == 0 then []
    else [flags[0] && !flags[1]] + Violations(flags[2..])
  }

  ghost function IsRed(flags: seq<bool>): bool
    requires |flags| % 2 == 0
    decreases |flags|
  {
    |flags| > 0 && ((flags[0] && !flags[1]) || IsRed(flags[2..]))
  }

  lemma PolicyExact(flags: seq<bool>)
    requires |flags| % 2 == 0
    ensures |Violations(flags)| * 2 == |flags|
    ensures forall i: int | 0 <= i < |Violations(flags)| ::
      Violations(flags)[i] == (flags[2*i] && !flags[2*i+1])
    ensures IsRed(flags) <==> (exists i: int | 0 <= i < |flags| / 2 :: flags[2*i] && !flags[2*i+1])
    decreases |flags|
  {
    if |flags| > 0 {
      PolicyExact(flags[2..]);
      if IsRed(flags) {
        if flags[0] && !flags[1] {
          assert exists i: int | 0 <= i < |flags| / 2 :: flags[2*i] && !flags[2*i+1] by {
            assert 0 < |flags| / 2;
            assert flags[2*0] && !flags[2*0+1];
          }
        } else {
          assert IsRed(flags[2..]);
          var j: int :| 0 <= j < |flags[2..]| / 2 && flags[2..][2*j] && !flags[2..][2*j+1];
          assert 0 <= j+1 < |flags| / 2;
          assert flags[2*(j+1)] && !flags[2*(j+1)+1];
        }
      }
      if exists i: int | 0 <= i < |flags| / 2 :: flags[2*i] && !flags[2*i+1] {
        var i: int :| 0 <= i < |flags| / 2 && flags[2*i] && !flags[2*i+1];
        if i > 0 {
          assert 0 <= i-1 < |flags[2..]| / 2;
          assert flags[2..][2*(i-1)] && !flags[2..][2*(i-1)+1];
          assert IsRed(flags[2..]);
        }
        assert IsRed(flags);
      }
    }
  }

  // Compute both public outputs without using the host's recursion stack.
  method EvaluatePolicy(flags: seq<bool>) returns (violations: seq<bool>, red: bool)
    requires |flags| % 2 == 0
    ensures violations == Violations(flags)
    ensures red == IsRed(flags)
    ensures |violations| * 2 == |flags|
    ensures forall j: int | 0 <= j < |violations| ::
      violations[j] == (flags[2*j] && !flags[2*j+1])
    ensures red <==> (exists j: int | 0 <= j < |flags| / 2 :: flags[2*j] && !flags[2*j+1])
  {
    violations := [];
    red := false;
    var i: nat := 0;
    while i < |flags| / 2
      invariant 0 <= i <= |flags| / 2
      invariant |violations| == i
      invariant forall j: int | 0 <= j < i ::
        violations[j] == (flags[2*j] && !flags[2*j+1])
      invariant red <==> (exists j: int | 0 <= j < i :: flags[2*j] && !flags[2*j+1])
      decreases |flags| / 2 - i
    {
      var violation := flags[2*i];
      violations := violations + [violation];
      red := red || violation;
      i := i + 1;
    }
    PolicyExact(flags);
    assert violations == Violations(flags);
  }
}
