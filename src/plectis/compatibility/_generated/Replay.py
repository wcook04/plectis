import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_
import Compatibility as Compatibility

# Module: Replay

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def ValidPair(approved, candidate):
        return ((((approved).inputs) == ((candidate).inputs)) and (Compatibility.default__.ValidMachine((approved).next_, (approved).output, (approved).initial, (approved).inputs))) and (Compatibility.default__.ValidMachine((candidate).next_, (candidate).output, (candidate).initial, (approved).inputs))

    @staticmethod
    def Accepts(approved, candidate, relation):
        return (default__.ValidPair(approved, candidate)) and (Compatibility.default__.Check((approved).next_, (approved).output, (approved).initial, (candidate).next_, (candidate).output, (candidate).initial, (approved).inputs, relation))

    @staticmethod
    def MismatchFrom(approved, candidate, s, t, word):
        while True:
            with _dafny.label():
                if (len(word)) == (0):
                    return False
                elif ((((word)[0]) < (0)) or (((approved).inputs) <= ((word)[0]))) or (((((approved).next_)[s])[(word)[0]]) < (0)):
                    return False
                elif (((((candidate).next_)[t])[(word)[0]]) < (0)) or (((((approved).output)[s])[(word)[0]]) != ((((candidate).output)[t])[(word)[0]])):
                    return True
                elif True:
                    in0_ = approved
                    in1_ = candidate
                    in2_ = (((approved).next_)[s])[(word)[0]]
                    in3_ = (((candidate).next_)[t])[(word)[0]]
                    in4_ = _dafny.SeqWithoutIsStrInference((word)[1::])
                    approved = in0_
                    candidate = in1_
                    s = in2_
                    t = in3_
                    word = in4_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def Mismatch(approved, candidate, word):
        return default__.MismatchFrom(approved, candidate, (approved).initial, (candidate).initial, word)

    @staticmethod
    def AnyMismatch(approved, candidate, hints):
        return ((len(hints)) > (0)) and ((default__.Mismatch(approved, candidate, (hints)[0])) or (default__.AnyMismatch(approved, candidate, _dafny.SeqWithoutIsStrInference((hints)[1::]))))

    @staticmethod
    def GuardedAccepts(approved, candidate, relation, hints):
        return ((default__.ValidPair(approved, candidate)) and (not(default__.AnyMismatch(approved, candidate, hints)))) and (default__.Accepts(approved, candidate, relation))


class Model:
    @classmethod
    def default(cls, ):
        return lambda: Model_Model(_dafny.Seq({}), _dafny.Seq({}), int(0), int(0))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Model(self) -> bool:
        return isinstance(self, Model_Model)

class Model_Model(Model, NamedTuple('Model', [('next_', Any), ('output', Any), ('initial', Any), ('inputs', Any)])):
    def __dafnystr__(self) -> str:
        return f'Replay.Model.Model({_dafny.string_of(self.next_)}, {_dafny.string_of(self.output)}, {_dafny.string_of(self.initial)}, {_dafny.string_of(self.inputs)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Model_Model) and self.next_ == __o.next_ and self.output == __o.output and self.initial == __o.initial and self.inputs == __o.inputs
    def __hash__(self) -> int:
        return super().__hash__()

