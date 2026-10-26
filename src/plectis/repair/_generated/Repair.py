import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: Repair

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def ValidDeps(deps):
        def lambda0_(forall_var_0_):
            def lambda1_(forall_var_1_):
                d_1_j_: int = forall_var_1_
                return not ((((0) <= (d_0_i_)) and ((d_0_i_) < (len(deps)))) and (((0) <= (d_1_j_)) and ((d_1_j_) < (len((deps)[d_0_i_]))))) or (((0) <= (((deps)[d_0_i_])[d_1_j_])) and ((((deps)[d_0_i_])[d_1_j_]) < (d_0_i_)))

            d_0_i_: int = forall_var_0_
            return _dafny.quantifier(_dafny.IntegerRange(0, len((deps)[d_0_i_])), True, lambda1_)

        return _dafny.quantifier(_dafny.IntegerRange(0, len(deps)), True, lambda0_)

    @staticmethod
    def ValidInputs(deps, roots, effects):
        return (((len(deps)) == (len(roots))) and ((len(deps)) == (len(effects)))) and (default__.ValidDeps(deps))

    @staticmethod
    def AnyDep(flags, parents):
        def lambda0_(exists_var_0_):
            d_0_j_: int = exists_var_0_
            return (((0) <= (d_0_j_)) and ((d_0_j_) < (len(parents)))) and ((flags)[(parents)[d_0_j_]])

        return _dafny.quantifier(_dafny.IntegerRange(0, len(parents)), False, lambda0_)

    @staticmethod
    def EffectRoots(dirty, effects):
        return _dafny.SeqWithoutIsStrInference([((dirty)[d_0_i_]) and ((effects)[d_0_i_]) for d_0_i_ in range(len(dirty))])

    @staticmethod
    def Recurrence(deps, seeds, flags):
        def lambda0_(forall_var_0_):
            d_0_i_: int = forall_var_0_
            return not (((0) <= (d_0_i_)) and ((d_0_i_) < (len(deps)))) or (((flags)[d_0_i_]) == (((seeds)[d_0_i_]) or (default__.AnyDep(flags, (deps)[d_0_i_]))))

        return (((default__.ValidDeps(deps)) and ((len(seeds)) == (len(deps)))) and ((len(flags)) == (len(deps)))) and (_dafny.quantifier(_dafny.IntegerRange(0, len(deps)), True, lambda0_))

    @staticmethod
    def CheckPlan(deps, roots, effects, dirty, blocked):
        return ((((default__.ValidInputs(deps, roots, effects)) and ((len(dirty)) == (len(deps)))) and ((len(blocked)) == (len(deps)))) and (default__.Recurrence(deps, roots, dirty))) and (default__.Recurrence(deps, default__.EffectRoots(dirty, effects), blocked))

    @staticmethod
    def Close(deps, seeds):
        flags: _dafny.Seq = _dafny.Seq({})
        flags = _dafny.SeqWithoutIsStrInference([])
        while (len(flags)) < (len(deps)):
            flags = (flags) + (_dafny.SeqWithoutIsStrInference([((seeds)[len(flags)]) or (default__.AnyDep(flags, (deps)[len(flags)]))]))
        return flags

    @staticmethod
    def MakePlan(deps, roots, effects):
        dirty: _dafny.Seq = _dafny.Seq({})
        blocked: _dafny.Seq = _dafny.Seq({})
        out0_: _dafny.Seq
        out0_ = default__.Close(deps, roots)
        dirty = out0_
        d_0_blockedSeeds_: _dafny.Seq
        d_0_blockedSeeds_ = default__.EffectRoots(dirty, effects)
        out1_: _dafny.Seq
        out1_ = default__.Close(deps, d_0_blockedSeeds_)
        blocked = out1_
        return dirty, blocked

