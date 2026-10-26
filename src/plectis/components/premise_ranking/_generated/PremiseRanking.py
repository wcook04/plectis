import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: PremiseRanking

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def Before(a, b):
        return (((a).score) > ((b).score)) or ((((a).score) == ((b).score)) and ((((a).idRank) < ((b).idRank)) or ((((a).idRank) == ((b).idRank)) and (((a).index) <= ((b).index)))))

    @staticmethod
    def Score(q, p, bonus):
        v: int = int(0)
        d_0_i_: int
        d_0_i_ = len(q)
        if bonus:
            v = 1
        elif True:
            v = 0
        while (d_0_i_) > (0):
            d_0_i_ = (d_0_i_) - (1)
            v = (v) + (((q)[d_0_i_] if ((q)[d_0_i_]) <= ((p)[d_0_i_]) else (p)[d_0_i_]))
        return v

    @staticmethod
    def Insert(s, x):
        t: _dafny.Seq = _dafny.Seq({})
        d_0_i_: int
        d_0_i_ = 0
        while ((d_0_i_) < (len(s))) and (not(default__.Before(x, (s)[d_0_i_]))):
            d_0_i_ = (d_0_i_) + (1)
        t = ((_dafny.SeqWithoutIsStrInference((s)[:d_0_i_:])) + (_dafny.SeqWithoutIsStrInference([x]))) + (_dafny.SeqWithoutIsStrInference((s)[d_0_i_::]))
        return t

    @staticmethod
    def Compute(q, cs):
        out: _dafny.Seq = _dafny.Seq({})
        out = _dafny.SeqWithoutIsStrInference([])
        d_0_i_: int
        d_0_i_ = 0
        while (d_0_i_) < (len(cs)):
            if ((cs)[d_0_i_]).eligible:
                d_1_v_: int
                out0_: int
                out0_ = default__.Score(q, ((cs)[d_0_i_]).counts, ((cs)[d_0_i_]).bonus)
                d_1_v_ = out0_
                out1_: _dafny.Seq
                out1_ = default__.Insert(out, Entry_Entry(d_0_i_, ((cs)[d_0_i_]).idRank, d_1_v_))
                out = out1_
            d_0_i_ = (d_0_i_) + (1)
        return out


class Candidate:
    @classmethod
    def default(cls, ):
        return lambda: Candidate_Candidate(False, int(0), _dafny.Seq({}), False)
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Candidate(self) -> bool:
        return isinstance(self, Candidate_Candidate)

class Candidate_Candidate(Candidate, NamedTuple('Candidate', [('eligible', Any), ('idRank', Any), ('counts', Any), ('bonus', Any)])):
    def __dafnystr__(self) -> str:
        return f'PremiseRanking.Candidate.Candidate({_dafny.string_of(self.eligible)}, {_dafny.string_of(self.idRank)}, {_dafny.string_of(self.counts)}, {_dafny.string_of(self.bonus)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Candidate_Candidate) and self.eligible == __o.eligible and self.idRank == __o.idRank and self.counts == __o.counts and self.bonus == __o.bonus
    def __hash__(self) -> int:
        return super().__hash__()


class Entry:
    @classmethod
    def default(cls, ):
        return lambda: Entry_Entry(int(0), int(0), int(0))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Entry(self) -> bool:
        return isinstance(self, Entry_Entry)

class Entry_Entry(Entry, NamedTuple('Entry', [('index', Any), ('idRank', Any), ('score', Any)])):
    def __dafnystr__(self) -> str:
        return f'PremiseRanking.Entry.Entry({_dafny.string_of(self.index)}, {_dafny.string_of(self.idRank)}, {_dafny.string_of(self.score)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Entry_Entry) and self.index == __o.index and self.idRank == __o.idRank and self.score == __o.score
    def __hash__(self) -> int:
        return super().__hash__()

