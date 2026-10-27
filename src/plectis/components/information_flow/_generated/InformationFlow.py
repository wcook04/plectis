import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: InformationFlow

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def Policy(i, verdict):
        return ((((((verdict) == (0)) == (((i).hidden) or ((((i).untrusted) and ((i).privileged)) and (not((i).sanitized))))) and (((verdict) == (1)) == (((not((i).hidden)) and ((i).untrusted)) and ((((i).privileged) and ((i).sanitized)) or ((not((i).privileged)) and (not((i).sanitized))))))) and (((verdict) == (2)) == ((((not((i).hidden)) and ((i).untrusted)) and (not((i).privileged))) and ((i).sanitized)))) and (((verdict) == (3)) == ((not((i).hidden)) and (not((i).untrusted))))) and (((0) <= (verdict)) and ((verdict) < (4)))

    @staticmethod
    def Decide(i):
        verdict: int = int(0)
        if (i).hidden:
            verdict = 0
        elif (((i).untrusted) and ((i).privileged)) and (not((i).sanitized)):
            verdict = 0
        elif (((i).untrusted) and ((i).privileged)) and ((i).sanitized):
            verdict = 1
        elif ((i).untrusted) and ((i).sanitized):
            verdict = 2
        elif (i).untrusted:
            verdict = 1
        elif True:
            verdict = 3
        return verdict

    @staticmethod
    def DecideMany(inputs):
        verdicts: _dafny.Seq = _dafny.Seq({})
        verdicts = _dafny.SeqWithoutIsStrInference([])
        d_0_n_: int
        d_0_n_ = 0
        while (d_0_n_) < (len(inputs)):
            d_1_v_: int
            out0_: int
            out0_ = default__.Decide((inputs)[d_0_n_])
            d_1_v_ = out0_
            verdicts = (verdicts) + (_dafny.SeqWithoutIsStrInference([d_1_v_]))
            d_0_n_ = (d_0_n_) + (1)
        return verdicts

    @staticmethod
    def Vertices(es):
        d_0___accumulator_ = _dafny.Set({})
        while True:
            with _dafny.label():
                if (len(es)) == (0):
                    return (_dafny.Set({})) | (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) | (_dafny.Set({((es)[0]).src, ((es)[0]).dst}))
                    in0_ = _dafny.SeqWithoutIsStrInference((es)[1::])
                    es = in0_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def HiddenDestinations(es):
        d_0___accumulator_ = _dafny.Set({})
        while True:
            with _dafny.label():
                if (len(es)) == (0):
                    return (_dafny.Set({})) | (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) | ((_dafny.Set({((es)[0]).dst}) if ((es)[0]).hidden else _dafny.Set({})))
                    in0_ = _dafny.SeqWithoutIsStrInference((es)[1::])
                    es = in0_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def Expand(es, reached):
        d_0___accumulator_ = _dafny.Set({})
        while True:
            with _dafny.label():
                if (len(es)) == (0):
                    return (_dafny.Set({})) | (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) | ((_dafny.Set({((es)[0]).dst}) if (((es)[0]).src) in (reached) else _dafny.Set({})))
                    in0_ = _dafny.SeqWithoutIsStrInference((es)[1::])
                    in1_ = reached
                    es = in0_
                    reached = in1_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def Closure(es, seeds, hiddenLabel):
        reached: _dafny.Set = _dafny.Set({})
        reached = (seeds) | ((default__.HiddenDestinations(es) if hiddenLabel else _dafny.Set({})))
        with _dafny.label("0"):
            while True:
                with _dafny.c_label("0"):
                    d_0_added_: _dafny.Set
                    d_0_added_ = default__.Expand(es, reached)
                    if (d_0_added_).issubset(reached):
                        raise _dafny.Break("0")
                    reached = (reached) | (d_0_added_)
                    pass
            pass
        return reached


class Input:
    @classmethod
    def default(cls, ):
        return lambda: Input_Input(False, False, False, False)
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Input(self) -> bool:
        return isinstance(self, Input_Input)

class Input_Input(Input, NamedTuple('Input', [('hidden', Any), ('untrusted', Any), ('privileged', Any), ('sanitized', Any)])):
    def __dafnystr__(self) -> str:
        return f'InformationFlow.Input.Input({_dafny.string_of(self.hidden)}, {_dafny.string_of(self.untrusted)}, {_dafny.string_of(self.privileged)}, {_dafny.string_of(self.sanitized)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Input_Input) and self.hidden == __o.hidden and self.untrusted == __o.untrusted and self.privileged == __o.privileged and self.sanitized == __o.sanitized
    def __hash__(self) -> int:
        return super().__hash__()


class FlowEdge:
    @classmethod
    def default(cls, ):
        return lambda: FlowEdge_FlowEdge(int(0), int(0), False)
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_FlowEdge(self) -> bool:
        return isinstance(self, FlowEdge_FlowEdge)

class FlowEdge_FlowEdge(FlowEdge, NamedTuple('FlowEdge', [('src', Any), ('dst', Any), ('hidden', Any)])):
    def __dafnystr__(self) -> str:
        return f'InformationFlow.FlowEdge.FlowEdge({_dafny.string_of(self.src)}, {_dafny.string_of(self.dst)}, {_dafny.string_of(self.hidden)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FlowEdge_FlowEdge) and self.src == __o.src and self.dst == __o.dst and self.hidden == __o.hidden
    def __hash__(self) -> int:
        return super().__hash__()

