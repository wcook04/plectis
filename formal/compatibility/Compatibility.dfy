// Original executable refinement checker, Plectis, 23 October 2026.
// Tables describe deterministic partial synchronous machines. No claim about
// an implementation-to-model bridge, specification adequacy or real effects.
module Compatibility {
  predicate ValidTable(next: seq<seq<int>>, output: seq<seq<int>>, inputs: int) {
    0 <= inputs && |next| > 0 && |output| == |next| &&
    forall s :: 0 <= s < |next| ==>
      |next[s]| == inputs && |output[s]| == inputs &&
      forall a :: 0 <= a < inputs ==> -1 <= next[s][a] < |next|
  }

  predicate ValidMachine(next: seq<seq<int>>, output: seq<seq<int>>,
                         initial: int, inputs: int) {
    ValidTable(next, output, inputs) && 0 <= initial < |next|
  }

  predicate ValidRelation(relation: seq<seq<bool>>, oldStates: int, newStates: int) {
    |relation| == oldStates &&
    forall s :: 0 <= s < |relation| ==> |relation[s]| == newStates
  }

  // -1 means an inadmissible input. An error/unknown outcome is an ordinary
  // output value on an enabled transition, never absence of an obligation.
  function Check(oldNext: seq<seq<int>>, oldOutput: seq<seq<int>>, oldInitial: int,
                 newNext: seq<seq<int>>, newOutput: seq<seq<int>>, newInitial: int,
                 inputs: int, relation: seq<seq<bool>>): bool {
    ValidMachine(oldNext, oldOutput, oldInitial, inputs) &&
    ValidMachine(newNext, newOutput, newInitial, inputs) &&
    ValidRelation(relation, |oldNext|, |newNext|) &&
    relation[oldInitial][newInitial] &&
    forall s, t, a ::
      0 <= s < |oldNext| && 0 <= t < |newNext| && 0 <= a < inputs &&
      relation[s][t] && 0 <= oldNext[s][a] ==>
        0 <= newNext[t][a] &&
        newOutput[t][a] == oldOutput[s][a] &&
        relation[oldNext[s][a]][newNext[t][a]]
  }

  ghost predicate Admissible(next: seq<seq<int>>, output: seq<seq<int>>,
                             inputs: int, state: int, word: seq<int>)
    requires ValidMachine(next, output, state, inputs)
    decreases |word|
  {
    |word| == 0 ||
      (0 <= word[0] < inputs && 0 <= next[state][word[0]] &&
       Admissible(next, output, inputs, next[state][word[0]], word[1..]))
  }

  ghost function Outputs(next: seq<seq<int>>, output: seq<seq<int>>,
                          inputs: int, state: int, word: seq<int>): seq<int>
    requires ValidMachine(next, output, state, inputs)
    requires Admissible(next, output, inputs, state, word)
    decreases |word|
  {
    if |word| == 0 then [] else
      [output[state][word[0]]] +
        Outputs(next, output, inputs, next[state][word[0]], word[1..])
  }

  ghost function EndState(next: seq<seq<int>>, output: seq<seq<int>>,
                           inputs: int, state: int, word: seq<int>): (result: int)
    requires ValidMachine(next, output, state, inputs)
    requires Admissible(next, output, inputs, state, word)
    ensures 0 <= result < |next|
    decreases |word|
  {
    if |word| == 0 then state else
      EndState(next, output, inputs, next[state][word[0]], word[1..])
  }

  lemma RelatedTracePreserved(
      oldNext: seq<seq<int>>, oldOutput: seq<seq<int>>, oldInitial: int,
      newNext: seq<seq<int>>, newOutput: seq<seq<int>>, newInitial: int,
      inputs: int, relation: seq<seq<bool>>, s: int, t: int, word: seq<int>)
    requires Check(oldNext, oldOutput, oldInitial, newNext, newOutput, newInitial,
                   inputs, relation)
    requires 0 <= s < |oldNext| && 0 <= t < |newNext| && relation[s][t]
    requires Admissible(oldNext, oldOutput, inputs, s, word)
    ensures Admissible(newNext, newOutput, inputs, t, word)
    ensures Outputs(oldNext, oldOutput, inputs, s, word) ==
            Outputs(newNext, newOutput, inputs, t, word)
    ensures relation[EndState(oldNext, oldOutput, inputs, s, word)]
                    [EndState(newNext, newOutput, inputs, t, word)]
    decreases |word|
  {
    if |word| > 0 {
      var a := word[0];
      assert 0 <= a < inputs && 0 <= oldNext[s][a];
      assert 0 <= newNext[t][a];
      assert newOutput[t][a] == oldOutput[s][a];
      assert relation[oldNext[s][a]][newNext[t][a]];
      RelatedTracePreserved(oldNext, oldOutput, oldInitial,
        newNext, newOutput, newInitial, inputs, relation,
        oldNext[s][a], newNext[t][a], word[1..]);
    }
  }

  // Every finite old-admissible word, with no fixed depth or state-count bound.
  lemma AcceptedRelationPreservesAllFiniteTraces(
      oldNext: seq<seq<int>>, oldOutput: seq<seq<int>>, oldInitial: int,
      newNext: seq<seq<int>>, newOutput: seq<seq<int>>, newInitial: int,
      inputs: int, relation: seq<seq<bool>>, word: seq<int>)
    requires Check(oldNext, oldOutput, oldInitial, newNext, newOutput, newInitial,
                   inputs, relation)
    requires Admissible(oldNext, oldOutput, inputs, oldInitial, word)
    ensures Admissible(newNext, newOutput, inputs, newInitial, word)
    ensures Outputs(oldNext, oldOutput, inputs, oldInitial, word) ==
            Outputs(newNext, newOutput, inputs, newInitial, word)
    ensures relation[EndState(oldNext, oldOutput, inputs, oldInitial, word)]
                    [EndState(newNext, newOutput, inputs, newInitial, word)]
  {
    RelatedTracePreserved(oldNext, oldOutput, oldInitial,
      newNext, newOutput, newInitial, inputs, relation, oldInitial, newInitial, word);
  }

  function IdentityRelation(states: int): seq<seq<bool>>
    requires 0 <= states
  {
    seq(states, s requires 0 <= s < states =>
      seq(states, t requires 0 <= t < states => s == t))
  }

  lemma IdentityAccepted(next: seq<seq<int>>, output: seq<seq<int>>,
                         initial: int, inputs: int)
    requires ValidMachine(next, output, initial, inputs)
    ensures Check(next, output, initial, next, output, initial,
                   inputs, IdentityRelation(|next|))
  {
    var relation := IdentityRelation(|next|);
    forall s, t, a |
      0 <= s < |next| && 0 <= t < |next| && 0 <= a < inputs &&
      relation[s][t] && 0 <= next[s][a]
      ensures 0 <= next[t][a] && output[t][a] == output[s][a] &&
              relation[next[s][a]][next[t][a]]
    {
      assert s == t;
    }
  }

  lemma UsefulSelfLoopAccepted()
    ensures Check([[0]], [[7]], 0, [[0]], [[7]], 0, 1, [[true]])
  {
    IdentityAccepted([[0]], [[7]], 0, 1);
  }
}
