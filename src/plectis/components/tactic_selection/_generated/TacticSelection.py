import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: TacticSelection

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def Eligible(c):
        return (((c).known) and ((c).available)) and ((c).allowed)

    @staticmethod
    def Select(ps, cs):
        index: int = int(0)
        preference: int = int(0)
        index = -1
        preference = -1
        d_0_i_: int
        d_0_i_ = 0
        while (d_0_i_) < (len(ps)):
            d_1_j_: int
            d_1_j_ = 0
            while (d_1_j_) < (len(cs)):
                if ((((cs)[d_1_j_]).id_) == ((ps)[d_0_i_])) and (default__.Eligible((cs)[d_1_j_])):
                    index = d_1_j_
                    preference = d_0_i_
                    return index, preference
                d_1_j_ = (d_1_j_) + (1)
            d_0_i_ = (d_0_i_) + (1)
        d_2_j_: int
        d_2_j_ = 0
        while (d_2_j_) < (len(cs)):
            if default__.Eligible((cs)[d_2_j_]):
                index = d_2_j_
                return index, preference
            d_2_j_ = (d_2_j_) + (1)
        return index, preference


class Candidate:
    @classmethod
    def default(cls, ):
        return lambda: Candidate_Candidate(int(0), False, False, False)
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Candidate(self) -> bool:
        return isinstance(self, Candidate_Candidate)

class Candidate_Candidate(Candidate, NamedTuple('Candidate', [('id_', Any), ('known', Any), ('available', Any), ('allowed', Any)])):
    def __dafnystr__(self) -> str:
        return f'TacticSelection.Candidate.Candidate({_dafny.string_of(self.id_)}, {_dafny.string_of(self.known)}, {_dafny.string_of(self.available)}, {_dafny.string_of(self.allowed)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Candidate_Candidate) and self.id_ == __o.id_ and self.known == __o.known and self.available == __o.available and self.allowed == __o.allowed
    def __hash__(self) -> int:
        return super().__hash__()

