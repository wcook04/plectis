import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: EvidenceDiff

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def LastAt(s, key, index):
        if (index) == (-1):
            return (key) not in (s)
        elif True:
            def lambda0_(forall_var_0_):
                d_0_j_: int = forall_var_0_
                return not (((index) < (d_0_j_)) and ((d_0_j_) < (len(s)))) or (((s)[d_0_j_]) != (key))

            return ((((0) <= (index)) and ((index) < (len(s)))) and (((s)[index]) == (key))) and (_dafny.quantifier(_dafny.IntegerRange((index) + (1), len(s)), True, lambda0_))

    @staticmethod
    def Classified(s, t, key, c):
        return ((((((default__.LastAt(s, key, (c).labLast)) and (default__.LastAt(t, key, (c).oracleLast))) and ((((c).category) == (0)) == (((key) not in (s)) and ((key) not in (t))))) and ((((c).category) == (1)) == (((key) in (s)) and ((key) not in (t))))) and ((((c).category) == (2)) == (((key) not in (s)) and ((key) in (t))))) and ((((c).category) == (3)) == (((key) in (s)) and ((key) in (t))))) and (((0) <= ((c).category)) and (((c).category) <= (3)))

    @staticmethod
    def FindLast(s, key):
        index: int = int(0)
        d_0_i_: int
        d_0_i_ = len(s)
        while (d_0_i_) > (0):
            d_0_i_ = (d_0_i_) - (1)
            if ((s)[d_0_i_]) == (key):
                index = d_0_i_
                return index
        index = -1
        return index

    @staticmethod
    def Compute(lab, oracle, size):
        cells: _dafny.Seq = _dafny.Seq({})
        cells = _dafny.SeqWithoutIsStrInference([])
        d_0_key_: int
        d_0_key_ = 0
        while (d_0_key_) < (size):
            d_1_l_: int
            out0_: int
            out0_ = default__.FindLast(lab, d_0_key_)
            d_1_l_ = out0_
            d_2_o_: int
            out1_: int
            out1_ = default__.FindLast(oracle, d_0_key_)
            d_2_o_ = out1_
            d_3_kind_: int
            if (d_1_l_) < (0):
                if (d_2_o_) < (0):
                    d_3_kind_ = 0
                elif True:
                    d_3_kind_ = 2
            elif True:
                if (d_2_o_) < (0):
                    d_3_kind_ = 1
                elif True:
                    d_3_kind_ = 3
            cells = (cells) + (_dafny.SeqWithoutIsStrInference([Cell_Cell(d_1_l_, d_2_o_, d_3_kind_)]))
            d_0_key_ = (d_0_key_) + (1)
        return cells


class Cell:
    @classmethod
    def default(cls, ):
        return lambda: Cell_Cell(int(0), int(0), int(0))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Cell(self) -> bool:
        return isinstance(self, Cell_Cell)

class Cell_Cell(Cell, NamedTuple('Cell', [('labLast', Any), ('oracleLast', Any), ('category', Any)])):
    def __dafnystr__(self) -> str:
        return f'EvidenceDiff.Cell.Cell({_dafny.string_of(self.labLast)}, {_dafny.string_of(self.oracleLast)}, {_dafny.string_of(self.category)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Cell_Cell) and self.labLast == __o.labLast and self.oracleLast == __o.oracleLast and self.category == __o.category
    def __hash__(self) -> int:
        return super().__hash__()

