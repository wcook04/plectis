// Original p14 round-2 experiment, 23 October 2026.
// Retained words are hints, not retained approval or retained expected outputs.
// The included Plectis checker and its provenance are unchanged.
include "../Compatibility.dfy"

module Replay {
  import C = Compatibility

  datatype Model = Model(next: seq<seq<int>>, output: seq<seq<int>>,
                         initial: int, inputs: int)

  predicate ValidPair(approved: Model, candidate: Model) {
    approved.inputs == candidate.inputs &&
    C.ValidMachine(approved.next, approved.output, approved.initial, approved.inputs) &&
    C.ValidMachine(candidate.next, candidate.output, candidate.initial, approved.inputs)
  }

  function Accepts(approved: Model, candidate: Model, relation: seq<seq<bool>>): bool {
    ValidPair(approved, candidate) &&
    C.Check(approved.next, approved.output, approved.initial,
            candidate.next, candidate.output, candidate.initial,
            approved.inputs, relation)
  }

  // An obsolete/disabled input provides no evidence against today's candidate.
  // A mismatch in an earlier enabled prefix is already a valid counterexample.
  function MismatchFrom(approved: Model, candidate: Model, s: int, t: int,
                        word: seq<int>): bool
    requires ValidPair(approved, candidate)
    requires 0 <= s < |approved.next| && 0 <= t < |candidate.next|
    decreases |word|
  {
    if |word| == 0 then false
    else if word[0] < 0 || approved.inputs <= word[0] || approved.next[s][word[0]] < 0
      then false
    else if candidate.next[t][word[0]] < 0 ||
            approved.output[s][word[0]] != candidate.output[t][word[0]]
      then t == candidate.initial
    else MismatchFrom(approved, candidate, approved.next[s][word[0]],
                       candidate.next[t][word[0]], word[1..])
  }

  function Mismatch(approved: Model, candidate: Model, word: seq<int>): bool
    requires ValidPair(approved, candidate)
  {
    MismatchFrom(approved, candidate, approved.initial, candidate.initial, word)
  }

  function AnyMismatch(approved: Model, candidate: Model, hints: seq<seq<int>>): bool
    requires ValidPair(approved, candidate)
    decreases |hints|
  {
    |hints| > 0 && (Mismatch(approved, candidate, hints[0]) ||
                    AnyMismatch(approved, candidate, hints[1..]))
  }

  function GuardedAccepts(approved: Model, candidate: Model,
                          relation: seq<seq<bool>>, hints: seq<seq<int>>): bool
  {
    ValidPair(approved, candidate) &&
    !AnyMismatch(approved, candidate, hints) && Accepts(approved, candidate, relation)
  }

  lemma RelatedPairsDoNotMismatch(approved: Model, candidate: Model,
                                  relation: seq<seq<bool>>, s: int, t: int,
                                  word: seq<int>)
    requires Accepts(approved, candidate, relation)
    requires 0 <= s < |approved.next| && 0 <= t < |candidate.next| && relation[s][t]
    ensures !MismatchFrom(approved, candidate, s, t, word)
    decreases |word|
  {
    if |word| > 0 && 0 <= word[0] < approved.inputs && 0 <= approved.next[s][word[0]] {
      var a := word[0];
      assert 0 <= candidate.next[t][a];
      assert approved.output[s][a] == candidate.output[t][a];
      assert relation[approved.next[s][a]][candidate.next[t][a]];
      RelatedPairsDoNotMismatch(approved, candidate, relation,
        approved.next[s][a], candidate.next[t][a], word[1..]);
    }
  }

  lemma AcceptedRelationHasNoHintMismatch(approved: Model, candidate: Model,
                                         relation: seq<seq<bool>>,
                                         hints: seq<seq<int>>)
    requires Accepts(approved, candidate, relation)
    ensures !AnyMismatch(approved, candidate, hints)
    decreases |hints|
  {
    if |hints| > 0 {
      RelatedPairsDoNotMismatch(approved, candidate, relation,
        approved.initial, candidate.initial, hints[0]);
      AcceptedRelationHasNoHintMismatch(approved, candidate, relation, hints[1..]);
    }
  }

  // Arbitrary finite models, words and hint collections: no fixed depth bound.
  // This is equivalence to the relation checker, not completeness of Python BFS.
  lemma HintsDoNotChangeAcceptance(approved: Model, candidate: Model,
                                  relation: seq<seq<bool>>, hints: seq<seq<int>>)
    ensures GuardedAccepts(approved, candidate, relation, hints) ==
            Accepts(approved, candidate, relation)
  {
    if Accepts(approved, candidate, relation) {
      AcceptedRelationHasNoHintMismatch(approved, candidate, relation, hints);
    }
  }

  // A passing retained test cannot replace the complete current relation check.
  lemma SilentHintIsNotApproval()
    ensures !Mismatch(Model([[0, 0]], [[0, 1]], 0, 2),
                       Model([[0, 0]], [[0, 2]], 0, 2), [0])
    ensures !Accepts(Model([[0, 0]], [[0, 1]], 0, 2),
                     Model([[0, 0]], [[0, 2]], 0, 2), [[true]])
  {
    var approved := Model([[0, 0]], [[0, 1]], 0, 2);
    var candidate := Model([[0, 0]], [[0, 2]], 0, 2);
    var relation := [[true]];
    if Accepts(approved, candidate, relation) {
      assert relation[0][0] && 0 <= approved.next[0][1];
      assert candidate.output[0][1] == approved.output[0][1];
      assert false;
    }
  }

  // Useful success: arbitrary stale inputs do not reject a self-compatible model.
  lemma ChangedRequirementDoesNotInheritOldOutput()
    ensures !Mismatch(Model([[0, -1]], [[7, 9]], 0, 2),
                       Model([[0, 0]], [[7, 100]], 0, 2), [1])
    ensures GuardedAccepts(Model([[0, -1]], [[7, 9]], 0, 2),
                           Model([[0, 0]], [[7, 100]], 0, 2),
                           [[true]], [[1], [-1], [0, 1]])
  {}

  // Independent meaning of a negative witness: an admitted prefix loses an
  // observation or changes one. This obligation does not use Mismatch in its
  // conclusion and covers words with arbitrary stale suffixes.
  lemma MismatchFromHasBadPrefix(approved: Model, candidate: Model,
                                 s: int, t: int, word: seq<int>)
      returns (length: nat)
    requires ValidPair(approved, candidate)
    requires 0 <= s < |approved.next| && 0 <= t < |candidate.next|
    requires MismatchFrom(approved, candidate, s, t, word)
    ensures 1 <= length <= |word|
    ensures C.Admissible(approved.next, approved.output, approved.inputs,
                         s, word[..length])
    ensures !C.Admissible(candidate.next, candidate.output, candidate.inputs,
                          t, word[..length]) ||
      C.Outputs(approved.next, approved.output, approved.inputs, s, word[..length]) !=
      C.Outputs(candidate.next, candidate.output, candidate.inputs, t, word[..length])
    decreases |word|
  {
    var a := word[0];
    if candidate.next[t][a] < 0 || approved.output[s][a] != candidate.output[t][a] {
      length := 1;
      assert word[..length] == [a];
      if candidate.next[t][a] >= 0 {
        assert C.Outputs(approved.next, approved.output, approved.inputs,
                         s, word[..length]) == [approved.output[s][a]];
        assert C.Outputs(candidate.next, candidate.output, candidate.inputs,
                         t, word[..length]) == [candidate.output[t][a]];
        assert C.Outputs(approved.next, approved.output, approved.inputs, s, word[..length]) !=
               C.Outputs(candidate.next, candidate.output, candidate.inputs, t, word[..length]);
      } else {
        assert !C.Admissible(candidate.next, candidate.output, candidate.inputs,
                             t, word[..length]);
      }
    } else {
      var tailLength := MismatchFromHasBadPrefix(approved, candidate,
        approved.next[s][a], candidate.next[t][a], word[1..]);
      length := tailLength + 1;
      assert word[..length][1..] == word[1..][..tailLength];
      assert C.Admissible(approved.next, approved.output, approved.inputs,
                          s, word[..length]);
      if C.Admissible(candidate.next, candidate.output, candidate.inputs,
                       t, word[..length]) {
        assert C.Admissible(candidate.next, candidate.output, candidate.inputs,
                            candidate.next[t][a], word[1..][..tailLength]);
        assert C.Outputs(approved.next, approved.output, approved.inputs,
                         s, word[..length]) == [approved.output[s][a]] +
          C.Outputs(approved.next, approved.output, approved.inputs,
                     approved.next[s][a], word[1..][..tailLength]);
        assert C.Outputs(candidate.next, candidate.output, candidate.inputs,
                         t, word[..length]) == [candidate.output[t][a]] +
          C.Outputs(candidate.next, candidate.output, candidate.inputs,
                     candidate.next[t][a], word[1..][..tailLength]);
        assert C.Outputs(approved.next, approved.output, approved.inputs,
                         approved.next[s][a], word[1..][..tailLength]) !=
               C.Outputs(candidate.next, candidate.output, candidate.inputs,
                         candidate.next[t][a], word[1..][..tailLength]);
        var oldWhole := C.Outputs(approved.next, approved.output, approved.inputs,
                                   s, word[..length]);
        var newWhole := C.Outputs(candidate.next, candidate.output, candidate.inputs,
                                   t, word[..length]);
        assert oldWhole[1..] == C.Outputs(approved.next, approved.output, approved.inputs,
                                          approved.next[s][a], word[1..][..tailLength]);
        assert newWhole[1..] == C.Outputs(candidate.next, candidate.output, candidate.inputs,
                                          candidate.next[t][a], word[1..][..tailLength]);
        assert C.Outputs(approved.next, approved.output, approved.inputs, s, word[..length]) !=
               C.Outputs(candidate.next, candidate.output, candidate.inputs, t, word[..length]);
      }
    }
  }

  lemma CheckedCounterexampleHasBadPrefix(approved: Model, candidate: Model,
                                          word: seq<int>)
    requires ValidPair(approved, candidate) && Mismatch(approved, candidate, word)
    ensures exists length ::
      1 <= length <= |word| &&
      C.Admissible(approved.next, approved.output, approved.inputs,
                   approved.initial, word[..length]) &&
      (!C.Admissible(candidate.next, candidate.output, candidate.inputs,
                     candidate.initial, word[..length]) ||
       C.Outputs(approved.next, approved.output, approved.inputs,
                  approved.initial, word[..length]) !=
       C.Outputs(candidate.next, candidate.output, candidate.inputs,
                  candidate.initial, word[..length]))
  {
    var length := MismatchFromHasBadPrefix(approved, candidate,
      approved.initial, candidate.initial, word);
  }

  lemma ChangedOutputOrMissingInputHasWitness()
    ensures Mismatch(Model([[0]], [[1]], 0, 1), Model([[0]], [[2]], 0, 1), [0])
    ensures Mismatch(Model([[0]], [[1]], 0, 1), Model([[-1]], [[1]], 0, 1), [0])
  { }
  // Completeness as well as soundness on every finite approved-admissible word.
  // No candidate transition/output discrepancy can be missed by the replay core.
  lemma AdmittedWordMismatchIsExact(approved: Model, candidate: Model,
                                     s: int, t: int, word: seq<int>)
    requires ValidPair(approved, candidate)
    requires 0 <= s < |approved.next| && 0 <= t < |candidate.next|
    requires C.Admissible(approved.next, approved.output, approved.inputs, s, word)
    ensures MismatchFrom(approved, candidate, s, t, word) ==
      (!C.Admissible(candidate.next, candidate.output, candidate.inputs, t, word) ||
       C.Outputs(approved.next, approved.output, approved.inputs, s, word) !=
       C.Outputs(candidate.next, candidate.output, candidate.inputs, t, word))
    decreases |word|
  {
    if |word| > 0 {
      var a := word[0];
      if candidate.next[t][a] >= 0 {
        if approved.output[s][a] == candidate.output[t][a] {
          AdmittedWordMismatchIsExact(approved, candidate,
            approved.next[s][a], candidate.next[t][a], word[1..]);
          if C.Admissible(candidate.next, candidate.output, candidate.inputs, t, word) {
            var oldWhole := C.Outputs(approved.next, approved.output, approved.inputs, s, word);
            var newWhole := C.Outputs(candidate.next, candidate.output, candidate.inputs, t, word);
            var oldTail := C.Outputs(approved.next, approved.output, approved.inputs,
                                     approved.next[s][a], word[1..]);
            var newTail := C.Outputs(candidate.next, candidate.output, candidate.inputs,
                                     candidate.next[t][a], word[1..]);
            assert oldWhole == [approved.output[s][a]] + oldTail;
            assert newWhole == [candidate.output[t][a]] + newTail;
            assert oldWhole[1..] == oldTail && newWhole[1..] == newTail;
            assert (oldWhole == newWhole) == (oldTail == newTail);
          }
        } else if C.Admissible(candidate.next, candidate.output, candidate.inputs, t, word) {
          assert C.Outputs(approved.next, approved.output, approved.inputs, s, word)[0] ==
                 approved.output[s][a];
          assert C.Outputs(candidate.next, candidate.output, candidate.inputs, t, word)[0] ==
                 candidate.output[t][a];
        }
      }
    }
  }

  lemma AdmittedCounterexampleCheckIsExact(approved: Model, candidate: Model,
                                           word: seq<int>)
    requires ValidPair(approved, candidate)
    requires C.Admissible(approved.next, approved.output, approved.inputs,
                          approved.initial, word)
    ensures Mismatch(approved, candidate, word) ==
      (!C.Admissible(candidate.next, candidate.output, candidate.inputs,
                     candidate.initial, word) ||
       C.Outputs(approved.next, approved.output, approved.inputs, approved.initial, word) !=
       C.Outputs(candidate.next, candidate.output, candidate.inputs, candidate.initial, word))
  {
    AdmittedWordMismatchIsExact(approved, candidate,
      approved.initial, candidate.initial, word);
  }

  // Once an admitted prefix differs, an obsolete suffix cannot erase it.
  lemma MismatchFromSurvivesSuffix(approved: Model, candidate: Model,
                                    s: int, t: int, prefix: seq<int>, suffix: seq<int>)
    requires ValidPair(approved, candidate)
    requires 0 <= s < |approved.next| && 0 <= t < |candidate.next|
    requires MismatchFrom(approved, candidate, s, t, prefix)
    ensures MismatchFrom(approved, candidate, s, t, prefix + suffix)
    decreases |prefix|
  {
    var a := prefix[0];
    if candidate.next[t][a] >= 0 &&
       approved.output[s][a] == candidate.output[t][a] {
      MismatchFromSurvivesSuffix(approved, candidate,
        approved.next[s][a], candidate.next[t][a], prefix[1..], suffix);
      assert (prefix + suffix)[1..] == prefix[1..] + suffix;
    }
  }

  // The executable decision is equivalent to an independently stated observable
  // failure, even for words containing out-of-domain or obsolete suffix inputs.
  lemma CounterexampleCheckIsExact(approved: Model, candidate: Model, word: seq<int>)
    requires ValidPair(approved, candidate)
    ensures Mismatch(approved, candidate, word) ==
      (exists length ::
        1 <= length <= |word| &&
        C.Admissible(approved.next, approved.output, approved.inputs,
                     approved.initial, word[..length]) &&
        (!C.Admissible(candidate.next, candidate.output, candidate.inputs,
                       candidate.initial, word[..length]) ||
         C.Outputs(approved.next, approved.output, approved.inputs,
                    approved.initial, word[..length]) !=
         C.Outputs(candidate.next, candidate.output, candidate.inputs,
                    candidate.initial, word[..length])))
  {
    if Mismatch(approved, candidate, word) {
      CheckedCounterexampleHasBadPrefix(approved, candidate, word);
    } else if exists length ::
      1 <= length <= |word| &&
      C.Admissible(approved.next, approved.output, approved.inputs,
                   approved.initial, word[..length]) &&
      (!C.Admissible(candidate.next, candidate.output, candidate.inputs,
                     candidate.initial, word[..length]) ||
       C.Outputs(approved.next, approved.output, approved.inputs,
                  approved.initial, word[..length]) !=
       C.Outputs(candidate.next, candidate.output, candidate.inputs,
                  candidate.initial, word[..length])) {
      var length :|
        1 <= length <= |word| &&
        C.Admissible(approved.next, approved.output, approved.inputs,
                     approved.initial, word[..length]) &&
        (!C.Admissible(candidate.next, candidate.output, candidate.inputs,
                       candidate.initial, word[..length]) ||
         C.Outputs(approved.next, approved.output, approved.inputs,
                    approved.initial, word[..length]) !=
         C.Outputs(candidate.next, candidate.output, candidate.inputs,
                    candidate.initial, word[..length]));
      AdmittedCounterexampleCheckIsExact(approved, candidate, word[..length]);
      MismatchFromSurvivesSuffix(approved, candidate,
        approved.initial, candidate.initial, word[..length], word[length..]);
      assert word[..length] + word[length..] == word;
    }
  }

}
