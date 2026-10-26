import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: WalkthroughValidation

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def WithinTenMinutes(numerator, denominator):
        return (((0) < (denominator)) and ((0) < (numerator))) and ((numerator) <= ((10) * (denominator)))

    @staticmethod
    def Evaluate(xs, budgetNumerator, budgetDenominator):
        accepted: bool = False
        commandCount: int = int(0)
        evidenceCount: int = int(0)
        d_0_commands_: _dafny.Set
        d_0_commands_ = _dafny.Set({})
        d_1_evidence_: _dafny.Set
        d_1_evidence_ = _dafny.Set({})
        d_2_ready_: bool
        d_2_ready_ = True
        d_3_i_: int
        d_3_i_ = 0
        while (d_3_i_) < (len(xs)):
            d_4_step_: Step
            d_4_step_ = (xs)[d_3_i_]
            def iife0_():
                coll0_ = _dafny.Set()
                compr_0_: int
                for compr_0_ in ((d_4_step_).commands).Elements:
                    d_5_v_: int = compr_0_
                    if (d_5_v_) in ((d_4_step_).commands):
                        coll0_ = coll0_.union(_dafny.Set([d_5_v_]))
                return _dafny.Set(coll0_)
            d_0_commands_ = (d_0_commands_) | (iife0_()
            )
            def iife1_():
                coll1_ = _dafny.Set()
                compr_1_: int
                for compr_1_ in ((d_4_step_).evidence).Elements:
                    d_6_v_: int = compr_1_
                    if (d_6_v_) in ((d_4_step_).evidence):
                        coll1_ = coll1_.union(_dafny.Set([d_6_v_]))
                return _dafny.Set(coll1_)
            d_1_evidence_ = (d_1_evidence_) | (iife1_()
            )
            d_2_ready_ = (((d_2_ready_) and ((len((d_4_step_).commands)) > (0))) and ((len((d_4_step_).inspect)) > (0))) and ((len((d_4_step_).evidence)) > (0))
            d_3_i_ = (d_3_i_) + (1)
        commandCount = len(d_0_commands_)
        evidenceCount = len(d_1_evidence_)
        accepted = ((((default__.WithinTenMinutes(budgetNumerator, budgetDenominator)) and ((len(xs)) >= (5))) and ((commandCount) >= (4))) and ((evidenceCount) >= (4))) and (d_2_ready_)
        return accepted, commandCount, evidenceCount


class Step:
    @classmethod
    def default(cls, ):
        return lambda: Step_Step(_dafny.Seq({}), _dafny.Seq({}), _dafny.Seq({}))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Step(self) -> bool:
        return isinstance(self, Step_Step)

class Step_Step(Step, NamedTuple('Step', [('commands', Any), ('inspect', Any), ('evidence', Any)])):
    def __dafnystr__(self) -> str:
        return f'WalkthroughValidation.Step.Step({_dafny.string_of(self.commands)}, {_dafny.string_of(self.inspect)}, {_dafny.string_of(self.evidence)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Step_Step) and self.commands == __o.commands and self.inspect == __o.inspect and self.evidence == __o.evidence
    def __hash__(self) -> int:
        return super().__hash__()

