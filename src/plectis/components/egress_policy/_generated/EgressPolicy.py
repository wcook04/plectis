import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: EgressPolicy

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def AsciiWord(c):
        return (((48) <= (c)) and ((c) <= (57))) or (((97) <= (c)) and ((c) <= (122)))

    @staticmethod
    def Occurrence(t, p, left, right, i):
        return (((((0) <= (i)) and (((i) + (len(p))) <= (len(t)))) and ((_dafny.SeqWithoutIsStrInference((t)[i:(i) + (len(p)):])) == (p))) and (((not(left)) or ((i) == (0))) or (not(default__.AsciiWord((t)[(i) - (1)]))))) and (((not(right)) or (((i) + (len(p))) == (len(t)))) or (not(default__.AsciiWord((t)[(i) + (len(p))]))))

    @staticmethod
    def Find(t, p, left, right):
        found: bool = False
        d_0_i_: int
        d_0_i_ = 0
        while ((d_0_i_) + (len(p))) <= (len(t)):
            if (((_dafny.SeqWithoutIsStrInference((t)[d_0_i_:(d_0_i_) + (len(p)):])) == (p)) and (((not(left)) or ((d_0_i_) == (0))) or (not(default__.AsciiWord((t)[(d_0_i_) - (1)]))))) and (((not(right)) or (((d_0_i_) + (len(p))) == (len(t)))) or (not(default__.AsciiWord((t)[(d_0_i_) + (len(p))])))):
                found = True
                return found
            d_0_i_ = (d_0_i_) + (1)
        found = False
        return found
        return found

    @staticmethod
    def Violations(flags):
        d_0___accumulator_ = _dafny.SeqWithoutIsStrInference([])
        while True:
            with _dafny.label():
                if (len(flags)) == (0):
                    return (d_0___accumulator_) + (_dafny.SeqWithoutIsStrInference([]))
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) + (_dafny.SeqWithoutIsStrInference([((flags)[0]) and (not((flags)[1]))]))
                    in0_ = _dafny.SeqWithoutIsStrInference((flags)[2::])
                    flags = in0_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def EvaluatePolicy(flags):
        violations: _dafny.Seq = _dafny.Seq({})
        red: bool = False
        violations = _dafny.SeqWithoutIsStrInference([])
        red = False
        d_0_i_: int
        d_0_i_ = 0
        while (d_0_i_) < (_dafny.euclidian_division(len(flags), 2)):
            d_1_violation_: bool
            d_1_violation_ = ((flags)[(2) * (d_0_i_)]) and (not((flags)[((2) * (d_0_i_)) + (1)]))
            violations = (violations) + (_dafny.SeqWithoutIsStrInference([d_1_violation_]))
            red = (red) or (d_1_violation_)
            d_0_i_ = (d_0_i_) + (1)
        return violations, red

