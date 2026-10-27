import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: BudgetPacking

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def IncludedTotal(sizes, decisions):
        d_0___accumulator_ = 0
        while True:
            with _dafny.label():
                if (len(sizes)) == (0):
                    return (0) + (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (((sizes)[(len(sizes)) - (1)] if (decisions)[(len(decisions)) - (1)] else 0)) + (d_0___accumulator_)
                    in0_ = _dafny.SeqWithoutIsStrInference((sizes)[:(len(sizes)) - (1):])
                    in1_ = _dafny.SeqWithoutIsStrInference((decisions)[:(len(decisions)) - (1):])
                    sizes = in0_
                    decisions = in1_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def OrderedGreedy(sizes, budget, decisions):
        def lambda0_(forall_var_0_):
            d_0_i_: int = forall_var_0_
            return not (((0) <= (d_0_i_)) and ((d_0_i_) < (len(sizes)))) or (((decisions)[d_0_i_]) == (((default__.IncludedTotal(_dafny.SeqWithoutIsStrInference((sizes)[:d_0_i_:]), _dafny.SeqWithoutIsStrInference((decisions)[:d_0_i_:]))) + ((sizes)[d_0_i_])) <= (budget)))

        return ((len(sizes)) == (len(decisions))) and (_dafny.quantifier(_dafny.IntegerRange(0, len(sizes)), True, lambda0_))

    @staticmethod
    def Pack(sizes, budget):
        decisions: _dafny.Seq = _dafny.Seq({})
        total: int = int(0)
        decisions = _dafny.SeqWithoutIsStrInference([])
        total = 0
        d_0_i_: int
        d_0_i_ = 0
        while (d_0_i_) < (len(sizes)):
            d_1_fits_: bool
            d_1_fits_ = ((total) + ((sizes)[d_0_i_])) <= (budget)
            decisions = (decisions) + (_dafny.SeqWithoutIsStrInference([d_1_fits_]))
            if d_1_fits_:
                total = (total) + ((sizes)[d_0_i_])
            d_0_i_ = (d_0_i_) + (1)
        return decisions, total

