import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: NavigationMetrics

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def MatchSpec(p, s):
        if ((len(p)) > (0)) and (((p)[(len(p)) - (1)]) == (_dafny.CodePoint('*'))):
            return ((len(s)) >= ((len(p)) - (1))) and ((_dafny.SeqWithoutIsStrInference((s)[:(len(p)) - (1):])) == (_dafny.SeqWithoutIsStrInference((p)[:(len(p)) - (1):])))
        elif True:
            return (p) == (s)

    @staticmethod
    def Match(p, s):
        if ((len(p)) > (0)) and (((p)[(len(p)) - (1)]) == (_dafny.CodePoint('*'))):
            return ((len(s)) >= ((len(p)) - (1))) and ((_dafny.SeqWithoutIsStrInference((s)[:(len(p)) - (1):])) == (_dafny.SeqWithoutIsStrInference((p)[:(len(p)) - (1):])))
        elif True:
            return (p) == (s)

    @staticmethod
    def FoundSpec(p, selected):
        def lambda0_(exists_var_0_):
            d_0_j_: int = exists_var_0_
            return (((0) <= (d_0_j_)) and ((d_0_j_) < (len(selected)))) and (default__.MatchSpec(p, (selected)[d_0_j_]))

        return _dafny.quantifier(_dafny.IntegerRange(0, len(selected)), False, lambda0_)

    @staticmethod
    def RelevantSpec(s, expected):
        def lambda0_(exists_var_0_):
            d_0_j_: int = exists_var_0_
            return (((0) <= (d_0_j_)) and ((d_0_j_) < (len(expected)))) and (default__.MatchSpec((expected)[d_0_j_], s))

        return _dafny.quantifier(_dafny.IntegerRange(0, len(expected)), False, lambda0_)

    @staticmethod
    def Decision(timeout, error, missing, scent, forbidden):
        if timeout:
            return 1
        elif error:
            return 2
        elif missing:
            return 3
        elif scent:
            return 4
        elif forbidden:
            return 5
        elif True:
            return 0

    @staticmethod
    def DecisionSpec(t, e, m, s, f, d):
        return (((((((d) == (1)) == (t)) and (((d) == (2)) == ((not(t)) and (e)))) and (((d) == (3)) == (((not(t)) and (not(e))) and (m)))) and (((d) == (4)) == ((((not(t)) and (not(e))) and (not(m))) and (s)))) and (((d) == (5)) == (((((not(t)) and (not(e))) and (not(m))) and (not(s))) and (f)))) and (((d) == (0)) == (((((not(t)) and (not(e))) and (not(m))) and (not(s))) and (not(f))))

    @staticmethod
    def Latency(timeout, wall, budget):
        if timeout:
            return 2
        elif (wall) <= (budget):
            return 0
        elif True:
            return 1

    @staticmethod
    def HasSelected(p, s):
        hit: bool = False
        d_0_i_: int
        d_0_i_ = 0
        hit = False
        while (d_0_i_) < (len(s)):
            hit = (hit) or (default__.Match(p, (s)[d_0_i_]))
            d_0_i_ = (d_0_i_) + (1)
        return hit

    @staticmethod
    def HasExpected(s, e):
        hit: bool = False
        d_0_i_: int
        d_0_i_ = 0
        hit = False
        while (d_0_i_) < (len(e)):
            hit = (hit) or (default__.Match((e)[d_0_i_], s))
            d_0_i_ = (d_0_i_) + (1)
        return hit

    @staticmethod
    def Compute(e, s, t, err, scent, forbidden, wall, budget):
        flags: _dafny.Seq = _dafny.Seq({})
        found: int = int(0)
        relevant: int = int(0)
        decision: int = int(0)
        latency: int = int(0)
        flags = _dafny.SeqWithoutIsStrInference([])
        found = 0
        relevant = 0
        d_0_i_: int
        d_0_i_ = 0
        while (d_0_i_) < (len(e)):
            d_1_hit_: bool
            out0_: bool
            out0_ = default__.HasSelected((e)[d_0_i_], s)
            d_1_hit_ = out0_
            flags = (flags) + (_dafny.SeqWithoutIsStrInference([d_1_hit_]))
            if d_1_hit_:
                found = (found) + (1)
            d_0_i_ = (d_0_i_) + (1)
        d_2_j_: int
        d_2_j_ = 0
        while (d_2_j_) < (len(s)):
            d_3_hit_: bool
            out1_: bool
            out1_ = default__.HasExpected((s)[d_2_j_], e)
            d_3_hit_ = out1_
            if d_3_hit_:
                relevant = (relevant) + (1)
            d_2_j_ = (d_2_j_) + (1)
        decision = default__.Decision(t, err, (found) < (len(e)), scent, forbidden)
        latency = default__.Latency(t, wall, budget)
        return flags, found, relevant, decision, latency

