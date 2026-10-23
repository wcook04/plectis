import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: Compatibility

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def ValidTable(next_, output, inputs):
        def lambda0_(forall_var_0_):
            def lambda1_(forall_var_1_):
                d_1_a_: int = forall_var_1_
                return (not (((0) <= (d_1_a_)) and ((d_1_a_) < (inputs))) or ((-1) <= (((next_)[d_0_s_])[d_1_a_]))) and (not (((0) <= (d_1_a_)) and ((d_1_a_) < (inputs))) or ((((next_)[d_0_s_])[d_1_a_]) < (len(next_))))

            d_0_s_: int = forall_var_0_
            return not (((0) <= (d_0_s_)) and ((d_0_s_) < (len(next_)))) or ((((len((next_)[d_0_s_])) == (inputs)) and ((len((output)[d_0_s_])) == (inputs))) and (_dafny.quantifier(_dafny.IntegerRange(0, inputs), True, lambda1_)))

        return ((((0) <= (inputs)) and ((len(next_)) > (0))) and ((len(output)) == (len(next_)))) and (_dafny.quantifier(_dafny.IntegerRange(0, len(next_)), True, lambda0_))

    @staticmethod
    def ValidMachine(next_, output, initial, inputs):
        return (default__.ValidTable(next_, output, inputs)) and (((0) <= (initial)) and ((initial) < (len(next_))))

    @staticmethod
    def ValidRelation(relation, oldStates, newStates):
        def lambda0_(forall_var_0_):
            d_0_s_: int = forall_var_0_
            return not (((0) <= (d_0_s_)) and ((d_0_s_) < (len(relation)))) or ((len((relation)[d_0_s_])) == (newStates))

        return ((len(relation)) == (oldStates)) and (_dafny.quantifier(_dafny.IntegerRange(0, len(relation)), True, lambda0_))

    @staticmethod
    def Check(oldNext, oldOutput, oldInitial, newNext, newOutput, newInitial, inputs, relation):
        def lambda0_(forall_var_0_):
            def lambda1_(forall_var_1_):
                def lambda2_(forall_var_2_):
                    d_2_a_: int = forall_var_2_
                    return not (((((((0) <= (d_0_s_)) and ((d_0_s_) < (len(oldNext)))) and (((0) <= (d_1_t_)) and ((d_1_t_) < (len(newNext))))) and (((0) <= (d_2_a_)) and ((d_2_a_) < (inputs)))) and (((relation)[d_0_s_])[d_1_t_])) and ((0) <= (((oldNext)[d_0_s_])[d_2_a_]))) or ((((0) <= (((newNext)[d_1_t_])[d_2_a_])) and ((((newOutput)[d_1_t_])[d_2_a_]) == (((oldOutput)[d_0_s_])[d_2_a_]))) and (((relation)[((oldNext)[d_0_s_])[d_2_a_]])[((newNext)[d_1_t_])[d_2_a_]]))

                d_1_t_: int = forall_var_1_
                return _dafny.quantifier(_dafny.IntegerRange(0, inputs), True, lambda2_)

            d_0_s_: int = forall_var_0_
            return _dafny.quantifier(_dafny.IntegerRange(0, len(newNext)), True, lambda1_)

        return ((((default__.ValidMachine(oldNext, oldOutput, oldInitial, inputs)) and (default__.ValidMachine(newNext, newOutput, newInitial, inputs))) and (default__.ValidRelation(relation, len(oldNext), len(newNext)))) and (((relation)[oldInitial])[newInitial])) and (_dafny.quantifier(_dafny.IntegerRange(0, len(oldNext)), True, lambda0_))

    @staticmethod
    def IdentityRelation(states):
        return _dafny.SeqWithoutIsStrInference([_dafny.SeqWithoutIsStrInference([(d_0_s_) == (d_1_t_) for d_1_t_ in range(states)]) for d_0_s_ in range(states)])

