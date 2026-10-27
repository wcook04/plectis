import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: DependencyReachability

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def Expand(es, frontier):
        out: _dafny.Set = _dafny.Set({})
        out = _dafny.Set({})
        d_0_i_: int
        d_0_i_ = 0
        while (d_0_i_) < (len(es)):
            if (((es)[d_0_i_]).src) in (frontier):
                out = (out) | (_dafny.Set({((es)[d_0_i_]).dst}))
            d_0_i_ = (d_0_i_) + (1)
        return out

    @staticmethod
    def Compute(es, s):
        reached: _dafny.Set = _dafny.Set({})
        out0_: _dafny.Set
        out0_ = default__.Expand(es, _dafny.Set({s}))
        reached = out0_
        d_0_added_: _dafny.Set
        d_0_added_ = _dafny.Set({})
        with _dafny.label("0"):
            while True:
                with _dafny.c_label("0"):
                    out1_: _dafny.Set
                    out1_ = default__.Expand(es, reached)
                    d_0_added_ = out1_
                    if (d_0_added_).issubset(reached):
                        raise _dafny.Break("0")
                    reached = (reached) | (d_0_added_)
                    pass
            pass
        return reached


class Edge:
    @classmethod
    def default(cls, ):
        return lambda: Edge_Edge(int(0), int(0))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Edge(self) -> bool:
        return isinstance(self, Edge_Edge)

class Edge_Edge(Edge, NamedTuple('Edge', [('src', Any), ('dst', Any)])):
    def __dafnystr__(self) -> str:
        return f'DependencyReachability.Edge.Edge({_dafny.string_of(self.src)}, {_dafny.string_of(self.dst)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Edge_Edge) and self.src == __o.src and self.dst == __o.dst
    def __hash__(self) -> int:
        return super().__hash__()

